import hashlib
import runpy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from server.engine import storage


def _response(status_code=200, text=""):
    return SimpleNamespace(status_code=status_code, text=text)


def test_content_types_uri_encoding_and_query_canonicalization():
    assert storage._guess_content_type(Path("bundle.TAR.GZ")) == "application/gzip"
    assert storage._guess_content_type(Path("payload.unknown")) == "application/octet-stream"
    assert storage._uri_encode("folder/a b", True) == "folder/a%20b"
    assert storage._uri_encode("folder/a b", False) == "folder%2Fa%20b"
    assert storage._canonical_query_string(None) == ""
    assert storage._canonical_query_string({"z key": "a/b", "a": 2}) == "a=2&z%20key=a%2Fb"


def test_sigv4_helpers_match_the_published_s3_vector():
    assert storage._hmac(b"key", "message") == __import__("hmac").new(
        b"key", b"message", hashlib.sha256
    ).digest()
    assert len(storage._signing_key("secret", "20240102", "auto", "s3")) == 32

    headers = storage._sign_request(
        method="get",
        path="/test.txt",
        headers={"Host": "examplebucket.s3.amazonaws.com", "Range": " bytes=0-9 "},
        payload_hash=storage._EMPTY_PAYLOAD_SHA256,
        access_key="AKIAIOSFODNN7EXAMPLE",
        secret_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        amz_date="20130524T000000Z",
        datestamp="20130524",
        region="us-east-1",
        service="s3",
    )

    assert headers["range"] == "bytes=0-9"
    assert "SignedHeaders=host;range;x-amz-content-sha256;x-amz-date" in headers["Authorization"]
    assert "Signature=f0e8bdb87c964420e857bd35b5d6ed310bd44f0170aba48dd91039c6036bdb41" in headers["Authorization"]


def test_configured_endpoint_and_lazy_http_client(monkeypatch):
    client = storage.R2Storage()

    monkeypatch.setattr(storage.config, "r2_configured", lambda: False)
    assert client.configured is False
    monkeypatch.setattr(storage.config, "r2_configured", lambda: True)
    assert client.configured is True

    monkeypatch.setattr(storage.config, "r2_endpoint_url", lambda: None)
    with pytest.raises(RuntimeError, match="R2 endpoint is not configured"):
        client._endpoint()
    monkeypatch.setattr(storage.config, "r2_endpoint_url", lambda: "https://account.example///")
    assert client._endpoint() == "https://account.example"

    fake_http = Mock()
    constructor = Mock(return_value=fake_http)
    monkeypatch.setattr(storage.httpx, "Client", constructor)
    assert client._http() is fake_http
    assert client._http() is fake_http
    constructor.assert_called_once()
    assert constructor.call_args.kwargs["follow_redirects"] is False
    assert constructor.call_args.kwargs["timeout"].connect == 10.0


def test_request_encodes_signs_and_sends_without_real_http(monkeypatch):
    monkeypatch.setattr(storage.config, "r2_endpoint_url", lambda: "https://account.example/")
    monkeypatch.setattr(storage.config, "r2_bucket", lambda: "bucket")
    monkeypatch.setattr(storage.config, "r2_access_key_id", lambda: "access")
    monkeypatch.setattr(storage.config, "r2_secret_access_key", lambda: "secret")

    client = storage.R2Storage()
    fake_http = Mock()
    first_response = object()
    second_response = object()
    fake_http.request.side_effect = [first_response, second_response]
    client._client = fake_http

    query = {"x": "a b"}
    assert client._request(
        "PUT", "folder/a b/雪", body=b"payload", content_type="text/plain", query_params=query
    ) is first_response
    assert client._request("GET", "") is second_response

    first = fake_http.request.call_args_list[0]
    assert first.args == ("PUT", "https://account.example/bucket/folder/a%20b/%E9%9B%AA")
    assert first.kwargs["params"] == query
    assert first.kwargs["content"] == b"payload"
    assert "host" not in first.kwargs["headers"]
    assert first.kwargs["headers"]["content-type"] == "text/plain"
    assert first.kwargs["headers"]["x-amz-content-sha256"] == hashlib.sha256(b"payload").hexdigest()
    assert first.kwargs["headers"]["Authorization"].startswith("AWS4-HMAC-SHA256 Credential=access/")

    second = fake_http.request.call_args_list[1]
    assert second.args == ("GET", "https://account.example/bucket")
    assert second.kwargs["params"] is None
    assert second.kwargs["content"] == b""
    assert "content-type" not in second.kwargs["headers"]
    assert second.kwargs["headers"]["x-amz-content-sha256"] == storage._EMPTY_PAYLOAD_SHA256


def test_public_url_variants(monkeypatch):
    client = storage.R2Storage()
    monkeypatch.setattr(storage.config, "r2_public_base_url", lambda: None)
    assert client.public_url("a/file.apk") is None
    monkeypatch.setattr(storage.config, "r2_public_base_url", lambda: "https://cdn.example")
    assert client.public_url("/a/file.apk") == "https://cdn.example/a/file.apk"


def test_upload_file_noops_for_unconfigured_or_missing(monkeypatch, tmp_path):
    client = storage.R2Storage()
    path = tmp_path / "missing.apk"

    monkeypatch.setattr(storage.config, "r2_configured", lambda: False)
    assert client.upload_file(path, "app/file.apk") is None

    monkeypatch.setattr(storage.config, "r2_configured", lambda: True)
    assert client.upload_file(path, "app/file.apk") is None


def test_upload_file_success_default_and_explicit_content_types(monkeypatch, tmp_path):
    client = storage.R2Storage()
    monkeypatch.setattr(storage.config, "r2_configured", lambda: True)
    monkeypatch.setattr(storage.config, "r2_public_base_url", lambda: "https://cdn.example")
    request = Mock(side_effect=[_response(200), _response(201)])
    monkeypatch.setattr(client, "_request", request)

    apk = tmp_path / "one.apk"
    apk.write_bytes(b"apk")
    blob = tmp_path / "two.bin"
    blob.write_bytes(b"blob")

    assert client.upload_file(apk, "id/one.apk") == "https://cdn.example/id/one.apk"
    assert client.upload_file(blob, "id/two.bin", "application/custom") == "https://cdn.example/id/two.bin"
    assert request.call_args_list[0].kwargs == {
        "body": b"apk",
        "content_type": "application/vnd.android.package-archive",
    }
    assert request.call_args_list[1].kwargs == {
        "body": b"blob",
        "content_type": "application/custom",
    }


def test_upload_file_raises_on_http_failure(monkeypatch, tmp_path):
    client = storage.R2Storage()
    monkeypatch.setattr(storage.config, "r2_configured", lambda: True)
    monkeypatch.setattr(client, "_request", Mock(return_value=_response(503, "x" * 250)))
    path = tmp_path / "file.zip"
    path.write_bytes(b"zip")

    with pytest.raises(RuntimeError, match=r"R2 PUT key failed: HTTP 503") as exc:
        client.upload_file(path, "key")
    assert len(str(exc.value).rsplit(" ", 1)[-1]) == 200


def test_upload_app_downloads_noops_and_filters_entries(monkeypatch, tmp_path):
    client = storage.R2Storage()
    existing = tmp_path / "downloads"
    existing.mkdir()

    monkeypatch.setattr(storage.config, "r2_configured", lambda: False)
    assert client.upload_app_downloads("id", existing) == {}

    monkeypatch.setattr(storage.config, "r2_configured", lambda: True)
    assert client.upload_app_downloads("id", tmp_path / "absent") == {}

    (existing / "nested").mkdir()
    (existing / "a.apk").write_bytes(b"a")
    (existing / "b.zip").write_bytes(b"b")

    # Uploads run in a thread pool (#242), so call order is not guaranteed.
    # Key the mock by filename instead of a positional side_effect list, and
    # assert the set of keys rather than their order.
    def upload_by_name(path, key, content_type=None):
        return "https://cdn/a.apk" if path.name == "a.apk" else None

    upload = Mock(side_effect=upload_by_name)
    monkeypatch.setattr(client, "upload_file", upload)

    assert client.upload_app_downloads("id", existing) == {"a.apk": "https://cdn/a.apk"}
    assert {call.args[1] for call in upload.call_args_list} == {
        "id/downloads/a.apk",
        "id/downloads/b.zip",
    }


def test_delete_app_noops_and_counts_successes(monkeypatch):
    client = storage.R2Storage()
    monkeypatch.setattr(storage.config, "r2_configured", lambda: False)
    assert client.delete_app("id") == 0

    monkeypatch.setattr(storage.config, "r2_configured", lambda: True)
    assert client.delete_app("") == 0

    list_keys = Mock(return_value=iter(["id/a", "id/b"]))
    delete_key = Mock(side_effect=[True, False])
    monkeypatch.setattr(client, "_list_keys", list_keys)
    monkeypatch.setattr(client, "_delete_key", delete_key)
    assert client.delete_app("id") == 1
    list_keys.assert_called_once_with("id/")


def test_list_keys_paginates_and_uses_continuation_token(monkeypatch):
    client = storage.R2Storage()
    first_xml = """\
<ListBucketResult xmlns="urn:test">
  <Contents><Key>id/a</Key></Contents>
  <NextContinuationToken>next token</NextContinuationToken>
  <IsTruncated>true</IsTruncated>
</ListBucketResult>"""
    second_xml = """\
<ListBucketResult><Contents><Key>id/b</Key></Contents><IsTruncated>false</IsTruncated></ListBucketResult>"""
    request = Mock(side_effect=[_response(200, first_xml), _response(200, second_xml)])
    monkeypatch.setattr(client, "_request", request)

    assert list(client._list_keys("id/")) == ["id/a", "id/b"]
    assert request.call_args_list[0].kwargs["query_params"] == {
        "list-type": "2",
        "prefix": "id/",
        "max-keys": "1000",
    }
    assert request.call_args_list[1].kwargs["query_params"]["continuation-token"] == "next token"


def test_list_keys_raises_on_http_failure(monkeypatch):
    client = storage.R2Storage()
    monkeypatch.setattr(client, "_request", Mock(return_value=_response(500, "failure")))
    with pytest.raises(RuntimeError, match="R2 ListObjectsV2 failed: HTTP 500 failure"):
        list(client._list_keys("id/"))


def test_parse_list_response_handles_invalid_optional_and_namespaced_xml():
    assert storage.R2Storage._parse_list_response("not xml") == ([], None)

    xml = """\
<ListBucketResult xmlns="urn:test">
  <Contents><Key>one</Key><Other>ignored</Other><Key /></Contents>
  <NextContinuationToken> token </NextContinuationToken>
  <IsTruncated>TrUe</IsTruncated>
  <Unknown>ignored</Unknown>
</ListBucketResult>"""
    assert storage.R2Storage._parse_list_response(xml) == (["one"], "token")
    assert storage.R2Storage._parse_list_response(
        "<R><NextContinuationToken /><IsTruncated>true</IsTruncated></R>"
    ) == ([], None)
    assert storage.R2Storage._parse_list_response(
        "<R><NextContinuationToken>unused</NextContinuationToken><IsTruncated>FALSE</IsTruncated></R>"
    ) == ([], None)


def test_delete_key_success_and_failure(monkeypatch):
    client = storage.R2Storage()
    request = Mock(side_effect=[_response(200), _response(204), _response(403, "denied")])
    monkeypatch.setattr(client, "_request", request)

    assert client._delete_key("a") is True
    assert client._delete_key("b") is True
    with pytest.raises(RuntimeError, match="R2 DELETE c failed: HTTP 403 denied"):
        client._delete_key("c")


def test_module_self_test_and_main_entrypoint(capsys):
    storage._self_test()
    runpy.run_path(storage.__file__, run_name="__main__")
    output = capsys.readouterr().out
    assert output.count("SigV4 S3 GET Object vector OK") == 2
