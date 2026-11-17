"""Shared test fixtures.

The invisible PoW gate (#244) is ON by default in production. Most endpoint
tests exercise other concerns (quotas, validation, storage), so the gate is
disabled suite-wide here; dedicated PoW tests re-enable it explicitly via
mock.patch.object(config, "pow_enabled", return_value=True).
"""

import pytest

from server import config


@pytest.fixture(autouse=True)
def _pow_disabled_by_default(monkeypatch):
    monkeypatch.setattr(config, "pow_enabled", lambda: False)