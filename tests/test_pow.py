"""Invisible proof-of-work gate (#244): challenge issuance, adaptive
difficulty, single-use verification, and the build-endpoint integration.
"""

import hashlib
import unittest
from unittest import mock

from fastapi.testclient import TestClient

from server import config, main, pow as pow_gate


def _solve(challenge: str, bits: int, cap: int = 4_000_000) -> str:
    """Brute-force a nonce with the required leading zero bits (test helper)."""
    for i in range(cap):
        sol = str(i)
        digest = hashlib.sha256(f"{challenge}:{sol}".encode()).digest()
        if pow_gate._leading_zero_bits(digest) >= bits:
            return sol
    raise AssertionError("no solution found within cap")


class PowModuleTests(unittest.TestCase):
    def setUp(self):
        # Fresh spent-set so replay state doesn't leak across tests.
        with pow_gate._spent_lock:
            pow_gate._spent.clear()

    def test_issue_and_verify_roundtrip(self):
        with mock.patch.object(config, "pow_base_bits", return_value=8), \
             mock.patch.object(config, "pow_max_bits", return_value=10):
            challenge = pow_gate.issue()
            self.assertEqual(challenge["bits"], 8)
            sol = _solve(challenge["challenge"], challenge["bits"])
            self.assertTrue(pow_gate.verify(challenge["challenge"], sol))

    def test_replay_is_rejected(self):
        with mock.patch.object(config, "pow_base_bits", return_value=8), \
             mock.patch.object(config, "pow_max_bits", return_value=10):
            challenge = pow_gate.issue()
            sol = _solve(challenge["challenge"], challenge["bits"])
            self.assertTrue(pow_gate.verify(challenge["challenge"], sol))
            self.assertFalse(pow_gate.verify(challenge["challenge"], sol))

    def test_wrong_solution_rejected(self):
        with mock.patch.object(config, "pow_base_bits", return_value=8), \
             mock.patch.object(config, "pow_max_bits", return_value=10):
            challenge = pow_gate.issue()
            self.assertFalse(pow_gate.verify(challenge["challenge"], "definitely-wrong"))

    def test_tampered_challenge_rejected(self):
        with mock.patch.object(config, "pow_base_bits", return_value=8), \
             mock.patch.object(config, "pow_max_bits", return_value=10):
            challenge = pow_gate.issue()
            sol = _solve(challenge["challenge"], challenge["bits"])
            # Flip the difficulty field — HMAC must fail.
            parts = challenge["challenge"].split(":")
            parts[2] = "9"
            self.assertFalse(pow_gate.verify(":".join(parts), sol))

    def test_expired_challenge_rejected(self):
        with mock.patch.object(config, "pow_base_bits", return_value=8), \
             mock.patch.object(config, "pow_max_bits", return_value=10):
            challenge = pow_gate.issue()
            sol = _solve(challenge["challenge"], challenge["bits"])
            with mock.patch.object(pow_gate.time, "time", return_value=challenge["expires"] + 1):
                self.assertFalse(pow_gate.verify(challenge["challenge"], sol))

    def test_difficulty_adapts_to_load(self):
        with mock.patch.object(config, "pow_base_bits", return_value=16), \
             mock.patch.object(config, "pow_max_bits", return_value=22):
            self.assertEqual(pow_gate.adaptive_bits(0, 0), 16)
            self.assertEqual(pow_gate.adaptive_bits(4, 20), 20)  # 4//2 + 20//10 = 4
            self.assertEqual(pow_gate.adaptive_bits(8, 40), 22)  # 4 + 4 = 8 -> capped
            self.assertEqual(pow_gate.adaptive_bits(100, 1000), 22)  # capped

    def test_leading_zero_bits_counter(self):
        self.assertEqual(pow_gate._leading_zero_bits(b"\x00\x00\x80"), 16)
        self.assertEqual(pow_gate._leading_zero_bits(b"\x00\x01"), 15)
        self.assertEqual(pow_gate._leading_zero_bits(b"\x0f"), 4)
        self.assertEqual(pow_gate._leading_zero_bits(b"\x80"), 0)


class PowEndpointTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(main.app)
        with pow_gate._spent_lock:
            pow_gate._spent.clear()
        main.distill_rate_limiter._buckets.clear()
        main.global_build_budget._buckets.clear()
        main.ip_daily_build_limiter._buckets.clear()
        main.url_daily_build_limiter._buckets.clear()

    def test_challenge_endpoint_issues_valid_challenge(self):
        resp = self.client.get("/api/pow/challenge")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertIn("challenge", body)
        self.assertIn("bits", body)
        self.assertEqual(len(body["challenge"].split(":")), 4)

    def test_build_without_pow_returns_428(self):
        with mock.patch.object(config, "pow_enabled", return_value=True):
            resp = self.client.post("/api/distill", json={"url": "https://example.com"})
        self.assertEqual(resp.status_code, 428)
        self.assertEqual(resp.json()["detail"]["code"], "pow.required")

    def test_build_with_valid_pow_accepted(self):
        with mock.patch.object(config, "pow_enabled", return_value=True), \
             mock.patch.object(config, "pow_base_bits", return_value=8), \
             mock.patch.object(config, "pow_max_bits", return_value=10):
            challenge = self.client.get("/api/pow/challenge").json()
            sol = _solve(challenge["challenge"], challenge["bits"])
            resp = self.client.post("/api/distill", json={
                "url": "https://example.com",
                "pow_challenge": challenge["challenge"],
                "pow_solution": sol,
            })
        self.assertEqual(resp.status_code, 202)

    def test_build_with_replayed_pow_rejected(self):
        with mock.patch.object(config, "pow_enabled", return_value=True), \
             mock.patch.object(config, "pow_base_bits", return_value=8), \
             mock.patch.object(config, "pow_max_bits", return_value=10):
            challenge = self.client.get("/api/pow/challenge").json()
            sol = _solve(challenge["challenge"], challenge["bits"])
            payload = {
                "url": "https://example.com",
                "pow_challenge": challenge["challenge"],
                "pow_solution": sol,
            }
            self.assertEqual(self.client.post("/api/distill", json=payload).status_code, 202)
            # Same challenge+solution again -> replay rejected.
            self.assertEqual(self.client.post("/api/distill", json=payload).status_code, 428)


if __name__ == "__main__":
    unittest.main()