"""Community layer: fingerprint-keyed user profiles, per-app creator
attribution, comments and 1-5 ratings.

There is no signup — the persistent device fingerprint (``webtoapp_device_
fingerprint`` cookie, minted client-side on first visit) is the identity.
Every fingerprint gets a sequential public ``user_num`` on first sight, in
first-seen order. Users may then set a unique display name, a Markdown bio
and an avatar.

Own SQLite file next to ``_history.sqlite3`` so this module stays
independent of the history store's schema.
"""

import json
import re
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

# Display name: letters, digits, CJK, underscore, hyphen — 2..20 chars.
NAME_PATTERN = re.compile(r"^[A-Za-z0-9_\-一-鿿]{2,20}$")

MAX_BIO_LEN = 2000
MAX_COMMENT_LEN = 2000


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class CommunityStore:
    def __init__(self, path: Path):
        self.path = Path(path)
        self._lock = threading.RLock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.path), check_same_thread=False, isolation_level=None)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._init_schema()

    def _init_schema(self) -> None:
        with self._lock:
            self._conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS profiles (
                    fp TEXT PRIMARY KEY,
                    user_num INTEGER NOT NULL UNIQUE,
                    name TEXT COLLATE NOCASE UNIQUE,
                    bio_md TEXT NOT NULL DEFAULT '',
                    avatar INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS app_creators (
                    app_id TEXT PRIMARY KEY,
                    fp TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS comments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    app_id TEXT NOT NULL,
                    fp TEXT NOT NULL,
                    body TEXT NOT NULL,
                    rating INTEGER,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_comments_app ON comments(app_id);
                CREATE TABLE IF NOT EXISTS app_reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    app_id TEXT NOT NULL,
                    fp TEXT NOT NULL DEFAULT '',
                    reason TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'open',
                    created_at TEXT NOT NULL,
                    resolved_at TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_reports_app ON app_reports(app_id);
                CREATE INDEX IF NOT EXISTS idx_reports_status ON app_reports(status);
                """
            )

    # ---------- profiles ----------

    def _profile_row_to_dict(self, row) -> dict:
        return {
            "user_num": row["user_num"],
            "name": row["name"] or "",
            "bio_md": row["bio_md"] or "",
            "avatar_url": f"/u/{row['user_num']}/avatar.png?v={row['avatar']}" if row["avatar"] else None,
            "created_at": row["created_at"],
        }

    def ensure_user(self, fp: str) -> dict:
        """Get or create the profile for a device fingerprint. New profiles
        take the next sequential user_num."""
        fp = str(fp or "").strip()
        if not fp:
            return {}
        with self._lock:
            row = self._conn.execute("SELECT * FROM profiles WHERE fp = ?", (fp,)).fetchone()
            if row:
                return self._profile_row_to_dict(row)
            now = _utc_now()
            next_num = (self._conn.execute("SELECT COALESCE(MAX(user_num), 0) + 1 FROM profiles").fetchone())[0]
            self._conn.execute(
                "INSERT INTO profiles(fp, user_num, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (fp, next_num, now, now),
            )
            return {"user_num": next_num, "name": "", "bio_md": "", "avatar_url": None, "created_at": now}

    def profile_by_fp(self, fp: Optional[str]) -> Optional[dict]:
        if not fp:
            return None
        with self._lock:
            row = self._conn.execute("SELECT * FROM profiles WHERE fp = ?", (fp,)).fetchone()
            return self._profile_row_to_dict(row) if row else None

    def profile_by_num(self, user_num) -> Optional[dict]:
        with self._lock:
            row = self._conn.execute("SELECT * FROM profiles WHERE user_num = ?", (int(user_num),)).fetchone()
            return self._profile_row_to_dict(row) if row else None

    def fp_by_num(self, user_num) -> Optional[str]:
        with self._lock:
            row = self._conn.execute("SELECT fp FROM profiles WHERE user_num = ?", (int(user_num),)).fetchone()
            return row["fp"] if row else None

    def update_profile(self, fp: str, name: str, bio_md: str) -> dict:
        """Set display name + bio. Raises ValueError on invalid/taken name."""
        name = str(name or "").strip()
        bio_md = str(bio_md or "")[:MAX_BIO_LEN]
        self.ensure_user(fp)
        with self._lock:
            if name:
                if not NAME_PATTERN.fullmatch(name):
                    raise ValueError("invalid_name")
                clash = self._conn.execute(
                    "SELECT fp FROM profiles WHERE name = ? AND fp <> ?", (name, fp)
                ).fetchone()
                if clash:
                    raise ValueError("name_taken")
            now = _utc_now()
            self._conn.execute(
                "UPDATE profiles SET name = ?, bio_md = ?, updated_at = ? WHERE fp = ?",
                (name or None, bio_md, now, fp),
            )
            return self._profile_row_to_dict(
                self._conn.execute("SELECT * FROM profiles WHERE fp = ?", (fp,)).fetchone()
            )

    def bump_avatar(self, fp: str) -> int:
        self.ensure_user(fp)
        with self._lock:
            self._conn.execute(
                "UPDATE profiles SET avatar = avatar + 1, updated_at = ? WHERE fp = ?",
                (_utc_now(), fp),
            )
            row = self._conn.execute("SELECT avatar FROM profiles WHERE fp = ?", (fp,)).fetchone()
            return int(row["avatar"]) if row else 0

    # ---------- creator attribution ----------

    def set_creator(self, app_id: str, fp: str) -> None:
        """Record the app builder — first claimant wins (attach must not
        reattribute ownership)."""
        app_id = str(app_id or "").strip()
        if not app_id or not fp:
            return
        with self._lock:
            self._conn.execute(
                "INSERT OR IGNORE INTO app_creators(app_id, fp, created_at) VALUES (?, ?, ?)",
                (app_id, fp, _utc_now()),
            )

    def creator_of(self, app_id: str) -> Optional[str]:
        with self._lock:
            row = self._conn.execute("SELECT fp FROM app_creators WHERE app_id = ?", (app_id,)).fetchone()
            return row["fp"] if row else None

    def creator_nums_map(self, app_ids) -> dict:
        """app_id -> creator profile dict, for market decoration."""
        ids = [str(a) for a in app_ids if a]
        if not ids:
            return {}
        placeholders = ",".join("?" for _ in ids)
        with self._lock:
            rows = self._conn.execute(
                f"""SELECT c.app_id, p.* FROM app_creators c
                    JOIN profiles p ON p.fp = c.fp
                    WHERE c.app_id IN ({placeholders})""",
                ids,
            ).fetchall()
            return {r["app_id"]: self._profile_row_to_dict(r) for r in rows}

    def apps_by_creator(self, fp: str) -> List[str]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT app_id FROM app_creators WHERE fp = ? ORDER BY created_at DESC", (fp,)
            ).fetchall()
            return [r["app_id"] for r in rows]

    def creator_fingerprints(self) -> List[str]:
        with self._lock:
            rows = self._conn.execute("SELECT DISTINCT fp FROM app_creators").fetchall()
            return [r["fp"] for r in rows if r["fp"]]

    # ---------- comments & ratings ----------

    def add_comment(self, app_id: str, fp: str, body: str, rating: Optional[int]) -> dict:
        body = str(body or "").strip()
        if not body:
            raise ValueError("empty_body")
        body = body[:MAX_COMMENT_LEN]
        if rating is not None and not (1 <= int(rating) <= 5):
            raise ValueError("bad_rating")
        self.ensure_user(fp)
        now = _utc_now()
        with self._lock:
            # One rating per person per app. A later score replaces the
            # earlier one instead of stacking another 5-star on the average.
            if rating is not None:
                rating = int(rating)
                existing = self._conn.execute(
                    """SELECT id FROM comments
                       WHERE app_id = ? AND fp = ? AND rating IS NOT NULL
                       ORDER BY id DESC""",
                    (app_id, fp),
                ).fetchall()
                if existing:
                    keep_id = existing[0]["id"]
                    self._conn.execute(
                        "UPDATE comments SET body = ?, rating = ?, created_at = ? WHERE id = ?",
                        (body, rating, now, keep_id),
                    )
                    extras = [(row["id"],) for row in existing[1:]]
                    if extras:
                        self._conn.executemany("DELETE FROM comments WHERE id = ?", extras)
                    return self.comment_by_id(keep_id, viewer_fp=fp)
            cur = self._conn.execute(
                "INSERT INTO comments(app_id, fp, body, rating, created_at) VALUES (?, ?, ?, ?, ?)",
                (app_id, fp, body, rating, now),
            )
            return self.comment_by_id(cur.lastrowid, viewer_fp=fp)

    def collapse_duplicate_ratings(self) -> int:
        """Delete older ratings so each person has one score per app.

        Keeps the row with the latest ``created_at`` (then the highest id).
        Comments that carry no rating are left alone.
        """
        with self._lock:
            rows = self._conn.execute(
                "SELECT id, app_id, fp, created_at FROM comments WHERE rating IS NOT NULL"
            ).fetchall()
            best = {}
            for row in rows:
                key = (row["app_id"], row["fp"])
                rank = (row["created_at"] or "", int(row["id"]))
                current = best.get(key)
                if current is None or rank > current[0]:
                    best[key] = (rank, row["id"])
            keep = {item[1] for item in best.values()}
            drop = [(row["id"],) for row in rows if row["id"] not in keep]
            if drop:
                self._conn.executemany("DELETE FROM comments WHERE id = ?", drop)
            return len(drop)

    def _comment_row_to_dict(self, row, viewer_fp: Optional[str]) -> dict:
        return {
            "id": row["id"],
            "app_id": row["app_id"],
            "body": row["body"],
            "rating": row["rating"],
            "created_at": row["created_at"],
            "user_num": row["user_num"],
            "name": row["name"] or "",
            "avatar_url": f"/u/{row['user_num']}/avatar.png?v={row['avatar']}" if row["avatar"] else None,
            "mine": bool(viewer_fp) and row["fp"] == viewer_fp,
        }

    def comment_by_id(self, comment_id: int, viewer_fp: Optional[str] = None) -> dict:
        with self._lock:
            row = self._conn.execute(
                """SELECT c.*, p.user_num, p.name, p.avatar FROM comments c
                   LEFT JOIN profiles p ON p.fp = c.fp WHERE c.id = ?""",
                (comment_id,),
            ).fetchone()
            return self._comment_row_to_dict(row, viewer_fp) if row else {}

    def list_comments(self, app_id: str, viewer_fp: Optional[str] = None, limit: int = 200) -> List[dict]:
        with self._lock:
            rows = self._conn.execute(
                """SELECT c.*, p.user_num, p.name, p.avatar FROM comments c
                   LEFT JOIN profiles p ON p.fp = c.fp
                   WHERE c.app_id = ? ORDER BY c.id DESC LIMIT ?""",
                (app_id, limit),
            ).fetchall()
            return [self._comment_row_to_dict(r, viewer_fp) for r in rows]

    def delete_comment(self, comment_id: int, fp: Optional[str] = None, admin: bool = False) -> str:
        """Returns 'deleted' | 'not_found' | 'forbidden'."""
        with self._lock:
            row = self._conn.execute("SELECT fp FROM comments WHERE id = ?", (comment_id,)).fetchone()
            if not row:
                return "not_found"
            if not admin and row["fp"] != fp:
                return "forbidden"
            self._conn.execute("DELETE FROM comments WHERE id = ?", (comment_id,))
            return "deleted"

    def purge_apps(self, app_ids) -> int:
        """Drop comments and creator links for apps being fully deleted."""
        ids = [str(a or "") for a in app_ids if str(a or "")]
        if not ids:
            return 0
        placeholders = ",".join("?" for _ in ids)
        with self._lock:
            cur = self._conn.execute(
                f"DELETE FROM comments WHERE app_id IN ({placeholders})", ids)
            self._conn.execute(
                f"DELETE FROM app_creators WHERE app_id IN ({placeholders})", ids)
            return cur.rowcount

    def rating_stats(self, app_id: str) -> dict:
        return self.rating_stats_map([app_id]).get(app_id, {"avg": None, "count": 0})

    def rating_stats_map(self, app_ids) -> dict:
        ids = [str(a) for a in app_ids if a]
        if not ids:
            return {}
        placeholders = ",".join("?" for _ in ids)
        with self._lock:
            rows = self._conn.execute(
                f"""SELECT app_id, AVG(rating) AS avg_r, COUNT(rating) AS cnt
                    FROM comments WHERE app_id IN ({placeholders}) AND rating IS NOT NULL
                    GROUP BY app_id""",
                ids,
            ).fetchall()
            return {r["app_id"]: {"avg": round(float(r["avg_r"]), 2), "count": int(r["cnt"])} for r in rows}

    # ---------- abuse reports (#240) ----------

    MAX_REPORT_LEN = 1000

    def add_report(self, app_id: str, fp: str, reason: str) -> dict:
        """Record an abuse report. Anyone may report; the fingerprint is
        stored for dedup/audit but never exposed publicly."""
        app_id = str(app_id or "").strip()
        reason = str(reason or "").strip()[: self.MAX_REPORT_LEN]
        if not app_id or not reason:
            raise ValueError("app_id and reason are required")
        now = _utc_now()
        with self._lock:
            cur = self._conn.execute(
                "INSERT INTO app_reports(app_id, fp, reason, status, created_at) VALUES (?, ?, ?, 'open', ?)",
                (app_id, str(fp or ""), reason, now),
            )
            return {"id": cur.lastrowid, "app_id": app_id, "created_at": now}

    def list_reports(self, status: Optional[str] = "open", limit: int = 200) -> List[dict]:
        """Admin view: newest reports first, with the public app name."""
        with self._lock:
            if status:
                rows = self._conn.execute(
                    "SELECT * FROM app_reports WHERE status = ? ORDER BY id DESC LIMIT ?",
                    (status, int(limit)),
                ).fetchall()
            else:
                rows = self._conn.execute(
                    "SELECT * FROM app_reports ORDER BY id DESC LIMIT ?", (int(limit),)
                ).fetchall()
            return [
                {
                    "id": r["id"],
                    "app_id": r["app_id"],
                    "reason": r["reason"],
                    "status": r["status"],
                    "created_at": r["created_at"],
                    "resolved_at": r["resolved_at"],
                }
                for r in rows
            ]

    def resolve_reports(self, app_id: str) -> int:
        """Mark every open report for an app resolved (after takedown)."""
        app_id = str(app_id or "").strip()
        if not app_id:
            return 0
        with self._lock:
            cur = self._conn.execute(
                "UPDATE app_reports SET status = 'resolved', resolved_at = ? WHERE app_id = ? AND status = 'open'",
                (_utc_now(), app_id),
            )
            return cur.rowcount

    # ---------- backfill ----------

    def backfill_devices(self, device_rows) -> int:
        """One-time import of existing device fingerprints in first-seen
        order so long-time users get the lowest user_nums, plus creator
        attribution for apps they already hold (earliest holder wins)."""
        with self._lock:
            if self._conn.execute("SELECT 1 FROM meta WHERE key = 'backfilled_v1'").fetchone():
                return 0
            count = 0
            for fp, _created_at, app_ids in device_rows:
                fp = str(fp or "").strip()
                if not fp:
                    continue
                self.ensure_user(fp)
                count += 1
                for app_id in app_ids or []:
                    self.set_creator(str(app_id), fp)
            self._conn.execute(
                "INSERT OR REPLACE INTO meta(key, value) VALUES ('backfilled_v1', ?)", (_utc_now(),)
            )
            return count
