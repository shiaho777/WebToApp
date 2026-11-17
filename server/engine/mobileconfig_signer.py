"""
iOS Configuration Profile (.mobileconfig) CMS signer.

Signs a raw XML plist with an SSL certificate so iOS shows the signer's domain
instead of the red "未签名 / Unsigned" warning. This is the technical basis
of what Chinese distributors call "苹果免签" — it's really just a properly
signed WebClip payload.

iOS verifies signatures against the public root CA store, so any cert from a
public CA (Let's Encrypt, Sectigo, DigiCert, ...) works. Self-signed certs
won't — they'll be accepted as unsigned, the same as no signing at all.

Signing is implemented by shelling out to `openssl cms`, which is present on
every macOS/Linux server and avoids pulling in the pyca/cryptography dependency.
If openssl or cert files are missing, signing is skipped gracefully and the
unsigned payload is returned — every iOS version still accepts it.
"""

import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Tuple

from server import config


class SigningUnavailable(Exception):
    """Raised when signing was requested but prerequisites are missing."""


def can_sign() -> bool:
    """Fast check: is signing possible right now?"""
    return config.ios_signing_available() and shutil.which("openssl") is not None


def sign(unsigned_xml: bytes) -> bytes:
    """CMS-sign a mobileconfig XML payload. Returns DER-encoded signed bytes.

    Raises SigningUnavailable if cert/key/openssl are not configured.
    Output is a detached-less (nodetach) CMS SignedData blob in DER form, which
    is what iOS expects as a .mobileconfig file on disk.
    """
    cert = config.ios_cert_file()
    key = config.ios_key_file()
    chain = config.ios_chain_file()
    openssl = shutil.which("openssl")

    if not (cert and key and openssl):
        raise SigningUnavailable(
            "openssl/cert/key missing — set IOS_CERT_FILE and IOS_KEY_FILE "
            "(or drop certs/ios-cert.pem and certs/ios-key.pem)."
        )

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        in_path = tmp_dir / "in.mobileconfig"
        out_path = tmp_dir / "out.mobileconfig"
        in_path.write_bytes(unsigned_xml)

        cmd = [
            openssl, "cms", "-sign",
            "-signer", cert,
            "-inkey", key,
            "-nodetach",          # embed payload inside the signature
            "-outform", "DER",    # iOS expects DER-encoded CMS
            "-in", str(in_path),
            "-out", str(out_path),
        ]
        if chain:
            cmd += ["-certfile", chain]

        result = subprocess.run(cmd, capture_output=True, timeout=config.tool_timeout_seconds())
        if result.returncode != 0:
            raise SigningUnavailable(
                f"openssl cms failed (exit={result.returncode}): "
                f"{result.stderr.decode('utf-8', 'ignore').strip()}"
            )
        return out_path.read_bytes()


def sign_or_passthrough(unsigned_xml: bytes) -> Tuple[bytes, bool]:
    """Best-effort: sign if possible, otherwise return the unsigned payload.

    Returns (bytes, is_signed). Never raises — failures fall back silently so
    one-off cert issues can't break the whole app generation pipeline.
    """
    if not can_sign():
        return unsigned_xml, False
    try:
        return sign(unsigned_xml), True
    except SigningUnavailable as e:
        print(f"[Signer] {e} — falling back to unsigned")
        return unsigned_xml, False
