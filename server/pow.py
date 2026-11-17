"""Invisible proof-of-work gate for build submissions (#244).

Free builds cost US cpu; submitting costs an attacker nothing. Throughput
budgets (#242) cap total load, but a determined attacker can still fill the
budget with junk and crowd out real users. PoW mirrors the cost back: every
submission must carry a nonce whose sha256(challenge:nonce) has ``bits``
leading zero bits. The browser solves it in a Web Worker (sub-second when
idle); the server verifies with ONE hash + HMAC check.

No captcha, no account, no interaction. Difficulty adapts to queue depth and
recent submission rate, so under attack the attacker's throughput is
physically capped while legitimate users just wait a little longer.

Challenges are HMAC-signed (no server-side issuance state), short-lived, and
single-use (a bounded in-memory spent set prevents replay).
"""

import hashlib
import hmac
import secrets
import threading
import time
from collections import OrderedDict
from typing import Optional

from server import config

# HMAC key for signing challenges. Process-lifetime random by default (a
# restart invalidates outstanding challenges — clients just fetch a new one);
# set POW_SECRET for stability across restarts / multi-worker deploys.
_secret: Optional[bytes] = None
_secret_lock = threading.Lock()

CHALLENGE_TTL_SECONDS = 300
_SPENT_MAX = 8192
_spent: "OrderedDict[str, float]" = OrderedDict()
_spent_lock = threading.Lock()


def _get_secret() -> bytes:
    global _secret
    with _secret_lock:
        if _secret is None:
            configured = config.pow_secret()
            _secret = configured.encode("utf-8") if configured else secrets.token_bytes(32)
        return _secret


def adaptive_bits(pending: int, recent_submissions: int) -> int:
    """Difficulty scales with load: idle ~16 bits (<1s in a Worker), busy
    climbs toward 22 bits (~minutes of attacker cpu per submission)."""
    base = config.pow_base_bits()
    ceiling = config.pow_max_bits()
    pressure = max(0, int(pending)) // 2 + max(0, int(recent_submissions)) // 10
    return max(base, min(ceiling, base + pressure))


def issue(pending: int = 0, recent_submissions: int = 0) -> dict:
    bits = adaptive_bits(pending, recent_submissions)
    expires = int(time.time()) + CHALLENGE_TTL_SECONDS
    nonce = secrets.token_hex(8)
    payload = f"{nonce}:{expires}:{bits}"
    sig = hmac.new(_get_secret(), payload.encode("utf-8"), hashlib.sha256).hexdigest()[:32]
    return {"challenge": f"{payload}:{sig}", "bits": bits, "expires": expires}


def _leading_zero_bits(digest: bytes) -> int:
    count = 0
    for byte in digest:
        if byte == 0:
            count += 8
            continue
        # count leading zeros of this byte
        for shift in (7, 6, 5, 4, 3, 2, 1, 0):
            if byte & (1 << shift):
                return count
            count += 1
        return count
    return count


def _mark_spent(challenge: str) -> bool:
    """True if this challenge was already used (replay). Bounded LRU."""
    now = time.time()
    with _spent_lock:
        if challenge in _spent:
            return True
        _spent[challenge] = now
        _spent.move_to_end(challenge)
        while len(_spent) > _SPENT_MAX:
            _spent.popitem(last=False)
    return False


def verify(challenge: str, solution: str) -> bool:
    """Validate signature, freshness, difficulty and the hash puzzle, then
    burn the challenge (single-use). Constant-time HMAC comparison."""
    if not challenge or not solution:
        return False
    parts = str(challenge).split(":")
    if len(parts) != 4:
        return False
    nonce, expires_s, bits_s, sig = parts
    try:
        expires = int(expires_s)
        bits = int(bits_s)
    except ValueError:
        return False
    if not (config.pow_base_bits() <= bits <= config.pow_max_bits()):
        return False
    if time.time() > expires:
        return False
    payload = f"{nonce}:{expires_s}:{bits_s}"
    expected = hmac.new(_get_secret(), payload.encode("utf-8"), hashlib.sha256).hexdigest()[:32]
    if not hmac.compare_digest(sig, expected):
        return False
    if len(str(solution)) > 64:
        return False
    digest = hashlib.sha256(f"{challenge}:{solution}".encode("utf-8")).digest()
    if _leading_zero_bits(digest) < bits:
        return False
    if _mark_spent(challenge):
        return False
    return True