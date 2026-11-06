"""App language metadata.

The app's language list is stored in recipe.json as ``languages``. The first
entry is the primary language; additional entries mark a multilingual app.
Market buckets are the ten UI languages plus ``mul`` (multilingual),
``other`` (a language outside the ten) and ``und`` (not specified).
"""

from __future__ import annotations

from typing import Iterable

LANGUAGE_CODES = ("en", "zh", "ja", "ko", "ar", "ru", "es", "pt", "fr", "de")
LANGUAGE_NAMES = {
    "en": "English",
    "zh": "中文",
    "ja": "日本語",
    "ko": "한국어",
    "ar": "العربية",
    "ru": "Русский",
    "es": "Español",
    "pt": "Português",
    "fr": "Français",
    "de": "Deutsch",
}
SPECIAL_CODES = ("mul", "other", "und")
MARKET_LANGUAGE_CODES = LANGUAGE_CODES + SPECIAL_CODES
_ALLOWED = set(LANGUAGE_CODES) | {"other", "und"}


def normalize_languages(value: Iterable | str | None) -> list[str]:
    """Return a clean, ordered language list; first item is the primary."""
    if isinstance(value, str):
        raw = [value]
    elif isinstance(value, (list, tuple, set)):
        raw = list(value)
    else:
        raw = []
    cleaned: list[str] = []
    for item in raw:
        code = str(item or "").strip().lower()
        if code not in _ALLOWED or code in cleaned:
            continue
        cleaned.append(code)
    # A known language makes "und" redundant; "mul" is derived, never stored.
    if "und" in cleaned and any(code in LANGUAGE_CODES for code in cleaned):
        cleaned = [code for code in cleaned if code != "und"]
    if not cleaned:
        return ["und"]
    return cleaned[: len(LANGUAGE_CODES)]


def language_category(value: Iterable | str | None) -> str:
    """Collapse a language list into one market bucket."""
    languages = normalize_languages(value)
    specific = [code for code in languages if code in LANGUAGE_CODES]
    has_other = "other" in languages
    if len(specific) >= 2:
        return "mul"
    if specific and has_other:
        return "mul"
    if specific:
        return specific[0]
    if has_other:
        return "other"
    return "und"
