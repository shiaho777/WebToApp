"""One-off backfill: classify existing apps by language.

Reads every ``generated/*/recipe.json`` and the SQLite ``apps`` table, infers a
primary language (plus multilingual when the text contains several scripts),
and writes ``languages`` back to both places. Idempotent: apps that already
have a ``languages`` list are left alone unless ``--force`` is passed.

Run on the server:

    venv/bin/python -m server.scripts.classify_app_languages --dry-run
    venv/bin/python -m server.scripts.classify_app_languages

Unknown/ambiguous apps become ``["und"]`` (Unspecified) and stay visible in
the market under that filter.
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from server.languages import language_category, normalize_languages

APPS_DIR = ROOT / "generated"
DB_PATH = APPS_DIR / "_history.sqlite3"

SCRIPT_PATTERNS = (
    ("ko", re.compile(r"[\uac00-\ud7af]")),
    ("ja", re.compile(r"[\u3040-\u30ff]")),
    ("ar", re.compile(r"[\u0600-\u06ff]")),
    ("ru", re.compile(r"[\u0400-\u04ff]")),
    ("zh", re.compile(r"[\u4e00-\u9fff]")),
)

# Common function words. Short marketing copy is often too sparse for a
# statistical detector, but these still separate the Latin-script languages
# well enough for a market filter.
LATIN_STOPWORDS = {
    "en": set("the and with for you your this that from app apps website online free best home news shop store more about".split()),
    "es": set("el la los las de del para con una un por que y en tu tus aplicacion aplicación tienda noticias juegos comprar mejor".split()),
    "pt": set("o a os as de do da para com uma um por que e em seu sua aplicativo aplicação loja notícias jogos comprar melhor".split()),
    "fr": set("le la les de des du pour avec une un par que et en votre vos application boutique actualités jeux acheter meilleur".split()),
    "de": set("der die das und mit für eine ein von zu den dem app website shop nachrichten spiele kaufen besser".split()),
}

TLD_LANGUAGE = {
    "cn": "zh", "jp": "ja", "kr": "ko", "ru": "ru", "su": "ru",
    "es": "es", "mx": "es", "ar": "es", "cl": "es", "pe": "es",
    "uy": "es", "ve": "es", "br": "pt", "pt": "pt", "fr": "fr",
    "de": "de", "at": "de", "ch": "de", "be": "fr", "ca": "fr",
}


def _text_of(recipe: dict) -> str:
    about = recipe.get("about") if isinstance(recipe.get("about"), dict) else {}
    parts = [
        recipe.get("name"),
        recipe.get("description"),
        about.get("text"),
    ]
    return " ".join(str(part or "") for part in parts).strip()


def _host_tld(url: str) -> str:
    host = str(url or "").split("//")[-1].split("/")[0].split(":")[0].lower()
    return host.rsplit(".", 1)[-1] if "." in host else ""


def _latin_scores(text: str) -> Counter:
    words = re.findall(r"[a-zà-ÿ]+", text.lower())
    scores = Counter()
    for lang, stopwords in LATIN_STOPWORDS.items():
        scores[lang] = sum(1 for word in words if word in stopwords)
    return scores


def infer_languages(recipe: dict) -> list[str]:
    text = _text_of(recipe)
    found = []
    for code, pattern in SCRIPT_PATTERNS:
        if pattern.search(text):
            found.append(code)
    if found:
        # Prefer the first script in the priority list (Korean, Japanese,
        # Arabic, Cyrillic, Chinese). Additional non-Latin scripts make the
        # app multilingual; Latin brand names alone do not.
        primary = found[0]
        others = [code for code in found[1:] if code != primary]
        # Japanese/Korean text normally contains Han characters too; that does
        # not make the app Chinese as well.
        if primary in ("ja", "ko") and "zh" in others:
            others.remove("zh")
        return normalize_languages([primary] + others)

    scores = _latin_scores(text)
    best = max(scores, key=scores.get) if scores else "en"
    best_score = scores.get(best, 0) if scores else 0
    tld = _host_tld(recipe.get("url"))
    hinted = TLD_LANGUAGE.get(tld)
    if best_score >= 2:
        return [best]
    if hinted:
        return [hinted]
    if len(re.findall(r"[A-Za-z]", text)) >= 3:
        return ["en"]
    return ["und"]


def _backup_db() -> Path:
    stamp = time.strftime("%Y%m%d-%H%M%S")
    backup = DB_PATH.with_name(f"{DB_PATH.name}.lang-backup-{stamp}")
    source = sqlite3.connect(DB_PATH)
    target = sqlite3.connect(backup)
    with target:
        source.backup(target)
    target.close()
    source.close()
    return backup


def main() -> int:
    parser = argparse.ArgumentParser(description="Classify existing apps by language.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true", help="Overwrite existing languages lists.")
    args = parser.parse_args()

    if not APPS_DIR.exists():
        print("generated/ not found", file=sys.stderr)
        return 1

    recipes: dict[str, tuple[Path, dict]] = {}
    for recipe_path in sorted(APPS_DIR.glob("*/recipe.json")):
        try:
            recipes[recipe_path.parent.name] = (recipe_path, json.loads(recipe_path.read_text()))
        except Exception as exc:
            print(f"skip {recipe_path.parent.name}: {exc}", file=sys.stderr)

    db_recipes: dict[str, dict] = {}
    if DB_PATH.exists():
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        try:
            for row in conn.execute("SELECT app_id, recipe_json FROM apps").fetchall():
                try:
                    db_recipes[row["app_id"]] = json.loads(row["recipe_json"] or "{}")
                except Exception:
                    db_recipes[row["app_id"]] = {}
        finally:
            conn.close()

    decisions: dict[str, list[str]] = {}
    for app_id, (_path, recipe) in recipes.items():
        existing = recipe.get("languages")
        if existing and not args.force:
            decisions[app_id] = normalize_languages(existing)
        else:
            decisions[app_id] = infer_languages(recipe)
    for app_id, recipe in db_recipes.items():
        if app_id in decisions:
            continue
        existing = recipe.get("languages")
        decisions[app_id] = normalize_languages(existing) if existing and not args.force else infer_languages(recipe)

    counts = Counter(language_category(langs) for langs in decisions.values())
    print(f"apps={len(decisions)} buckets={dict(sorted(counts.items()))}")
    if args.dry_run:
        for app_id, langs in list(decisions.items())[:20]:
            print(f"  {app_id}: {langs}")
        return 0

    backup = _backup_db() if DB_PATH.exists() else None
    if backup:
        print(f"backup={backup}")

    if DB_PATH.exists():
        conn = sqlite3.connect(DB_PATH)
        try:
            with conn:
                for app_id, recipe in db_recipes.items():
                    recipe["languages"] = decisions[app_id]
                    conn.execute(
                        "UPDATE apps SET recipe_json = ? WHERE app_id = ?",
                        (json.dumps(recipe, ensure_ascii=False), app_id),
                    )
        finally:
            conn.close()

    written = 0
    for app_id, (path, recipe) in recipes.items():
        recipe["languages"] = decisions[app_id]
        path.write_text(json.dumps(recipe, ensure_ascii=False, indent=2))
        written += 1
    print(f"updated disk={written} db={len(db_recipes)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
