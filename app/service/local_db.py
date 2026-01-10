import json
import os
import sqlite3
import time
from pathlib import Path

try:
    from cryptography.fernet import Fernet, InvalidToken
except ImportError:  # pragma: no cover - handled at runtime
    Fernet = None
    InvalidToken = Exception

BASE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = os.getenv("DORXL_DB_PATH", str(BASE_DIR / "data" / "local.db"))
KEY_FILE = os.getenv("DORXL_DB_KEY_FILE", str(BASE_DIR / ".secrets" / "db.key"))
KEY_ENV = "DORXL_DB_KEY"


class LocalDB:
    def __init__(self):
        self._cipher = None
        self._conn = None
        self._init_db()

    def _init_db(self):
        self._ensure_paths()
        self._conn = sqlite3.connect(DB_PATH)
        self._conn.row_factory = sqlite3.Row
        self._ensure_schema()
        self._migrate_legacy()

    def _ensure_paths(self):
        db_dir = os.path.dirname(DB_PATH)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        key_dir = os.path.dirname(KEY_FILE)
        if key_dir:
            os.makedirs(key_dir, exist_ok=True)

    def _get_cipher(self):
        if self._cipher is not None:
            return self._cipher
        if Fernet is None:
            raise RuntimeError(
                "Missing dependency: cryptography. Install it to enable encrypted storage."
            )
        key = os.getenv(KEY_ENV, "").strip()
        if not key and os.path.exists(KEY_FILE):
            with open(KEY_FILE, "r", encoding="utf-8") as f:
                key = f.read().strip()
        if not key:
            key = Fernet.generate_key().decode("ascii")
            with open(KEY_FILE, "w", encoding="utf-8") as f:
                f.write(key)
        self._cipher = Fernet(key.encode("ascii"))
        return self._cipher

    def _encrypt(self, value: str) -> str:
        if value is None or value == "":
            return ""
        cipher = self._get_cipher()
        return cipher.encrypt(value.encode("utf-8")).decode("ascii")

    def _decrypt(self, value: str) -> str:
        if value is None or value == "":
            return ""
        cipher = self._get_cipher()
        try:
            return cipher.decrypt(value.encode("ascii")).decode("utf-8")
        except InvalidToken:
            return ""

    def _ensure_schema(self):
        cur = self._conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                number TEXT PRIMARY KEY,
                subscriber_id TEXT,
                subscription_type TEXT,
                refresh_token_enc TEXT,
                access_token_enc TEXT,
                id_token_enc TEXT,
                created_at INTEGER,
                updated_at INTEGER,
                last_active INTEGER
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS meta (
                key TEXT PRIMARY KEY,
                value TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_number TEXT,
                package_code TEXT,
                package_name TEXT,
                method TEXT,
                amount INTEGER,
                status TEXT,
                error_code TEXT,
                error_message TEXT,
                response_json TEXT,
                created_at INTEGER,
                synced INTEGER DEFAULT 0,
                sync_error TEXT,
                sync_at INTEGER
            )
            """
        )
        self._conn.commit()

    def _migrate_legacy(self):
        legacy_path = Path("refresh-tokens.json")
        if not legacy_path.exists():
            return
        if self._has_users():
            return
        try:
            data = json.loads(legacy_path.read_text(encoding="utf-8"))
        except Exception:
            return
        now = int(time.time())
        for entry in data:
            number = str(entry.get("number", "")).strip()
            refresh_token = entry.get("refresh_token", "")
            subscriber_id = entry.get("subscriber_id", "")
            subscription_type = entry.get("subscription_type", "")
            if not number or not refresh_token:
                continue
            self._upsert_user_raw(
                number=number,
                subscriber_id=subscriber_id,
                subscription_type=subscription_type,
                refresh_token=refresh_token,
                access_token="",
                id_token="",
                created_at=now,
                updated_at=now,
                last_active=None,
            )
        active_path = Path("active.number")
        if active_path.exists():
            try:
                active_number = active_path.read_text(encoding="utf-8").strip()
            except Exception:
                active_number = ""
            if active_number:
                self.set_active_number(active_number)

    def _has_users(self) -> bool:
        cur = self._conn.cursor()
        cur.execute("SELECT COUNT(1) AS cnt FROM users")
        row = cur.fetchone()
        return bool(row and row["cnt"] > 0)

    def _upsert_user_raw(
        self,
        number: str,
        subscriber_id: str,
        subscription_type: str,
        refresh_token: str,
        access_token: str,
        id_token: str,
        created_at: int,
        updated_at: int,
        last_active: int | None,
    ):
        cur = self._conn.cursor()
        cur.execute(
            """
            INSERT INTO users (
                number, subscriber_id, subscription_type,
                refresh_token_enc, access_token_enc, id_token_enc,
                created_at, updated_at, last_active
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(number) DO UPDATE SET
                subscriber_id=excluded.subscriber_id,
                subscription_type=excluded.subscription_type,
                refresh_token_enc=excluded.refresh_token_enc,
                access_token_enc=excluded.access_token_enc,
                id_token_enc=excluded.id_token_enc,
                updated_at=excluded.updated_at,
                last_active=COALESCE(excluded.last_active, users.last_active)
            """,
            (
                str(number),
                subscriber_id,
                subscription_type,
                self._encrypt(refresh_token),
                self._encrypt(access_token),
                self._encrypt(id_token),
                created_at,
                updated_at,
                last_active,
            ),
        )
        self._conn.commit()

    def get_refresh_tokens(self) -> list[dict]:
        cur = self._conn.cursor()
        cur.execute(
            """
            SELECT number, subscriber_id, subscription_type, refresh_token_enc
            FROM users
            ORDER BY number ASC
            """
        )
        rows = cur.fetchall()
        results = []
        for row in rows:
            refresh_token = self._decrypt(row["refresh_token_enc"])
            if not refresh_token:
                continue
            results.append(
                {
                    "number": int(row["number"]),
                    "subscriber_id": row["subscriber_id"],
                    "subscription_type": row["subscription_type"],
                    "refresh_token": refresh_token,
                }
            )
        return results

    def replace_refresh_tokens(self, refresh_tokens: list[dict]):
        keep_numbers = set()
        now = int(time.time())
        for rt in refresh_tokens:
            number = str(rt.get("number", "")).strip()
            refresh_token = rt.get("refresh_token", "")
            if not number or not refresh_token:
                continue
            keep_numbers.add(number)
            cur = self._conn.cursor()
            cur.execute("SELECT number FROM users WHERE number = ?", (number,))
            row = cur.fetchone()
            if row:
                cur.execute(
                    """
                    UPDATE users
                    SET subscriber_id = ?, subscription_type = ?,
                        refresh_token_enc = ?, updated_at = ?
                    WHERE number = ?
                    """,
                    (
                        rt.get("subscriber_id", ""),
                        rt.get("subscription_type", ""),
                        self._encrypt(refresh_token),
                        now,
                        number,
                    ),
                )
                self._conn.commit()
            else:
                self._upsert_user_raw(
                    number=number,
                    subscriber_id=rt.get("subscriber_id", ""),
                    subscription_type=rt.get("subscription_type", ""),
                    refresh_token=refresh_token,
                    access_token=rt.get("access_token", ""),
                    id_token=rt.get("id_token", ""),
                    created_at=now,
                    updated_at=now,
                    last_active=None,
                )
        cur = self._conn.cursor()
        if keep_numbers:
            placeholders = ",".join("?" for _ in keep_numbers)
            cur.execute(
                f"DELETE FROM users WHERE number NOT IN ({placeholders})",
                tuple(keep_numbers),
            )
        else:
            cur.execute("DELETE FROM users")
        self._conn.commit()

    def delete_user(self, number: int):
        cur = self._conn.cursor()
        cur.execute("DELETE FROM users WHERE number = ?", (str(number),))
        self._conn.commit()

    def update_tokens(
        self,
        number: int,
        refresh_token: str | None = None,
        access_token: str | None = None,
        id_token: str | None = None,
    ):
        cur = self._conn.cursor()
        fields = []
        values = []
        if refresh_token is not None:
            fields.append("refresh_token_enc = ?")
            values.append(self._encrypt(refresh_token))
        if access_token is not None:
            fields.append("access_token_enc = ?")
            values.append(self._encrypt(access_token))
        if id_token is not None:
            fields.append("id_token_enc = ?")
            values.append(self._encrypt(id_token))
        if not fields:
            return
        fields.append("updated_at = ?")
        values.append(int(time.time()))
        values.append(str(number))
        cur.execute(
            f"UPDATE users SET {', '.join(fields)} WHERE number = ?",
            tuple(values),
        )
        self._conn.commit()

    def set_active_number(self, number: int | str):
        number_str = str(number)
        cur = self._conn.cursor()
        cur.execute(
            "INSERT INTO meta(key, value) VALUES(?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            ("active_number", number_str),
        )
        cur.execute(
            "UPDATE users SET last_active = ? WHERE number = ?",
            (int(time.time()), number_str),
        )
        self._conn.commit()

    def get_active_number(self) -> str | None:
        cur = self._conn.cursor()
        cur.execute("SELECT value FROM meta WHERE key = ?", ("active_number",))
        row = cur.fetchone()
        return row["value"] if row else None

    def log_transaction(
        self,
        user_number: str,
        package_code: str,
        package_name: str,
        method: str,
        amount: int,
        status: str,
        error_code: str,
        error_message: str,
        response_json: dict | str | None,
    ) -> int:
        created_at = int(time.time())
        response_text = ""
        if isinstance(response_json, (dict, list)):
            response_text = json.dumps(response_json, ensure_ascii=True)
        elif isinstance(response_json, str):
            response_text = response_json
        cur = self._conn.cursor()
        cur.execute(
            """
            INSERT INTO transactions (
                user_number, package_code, package_name, method, amount,
                status, error_code, error_message, response_json, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_number,
                package_code,
                package_name,
                method,
                amount,
                status,
                error_code,
                error_message,
                response_text,
                created_at,
            ),
        )
        self._conn.commit()
        return int(cur.lastrowid)

    def mark_synced(self, transaction_id: int, sync_error: str | None = None):
        cur = self._conn.cursor()
        cur.execute(
            """
            UPDATE transactions
            SET synced = ?, sync_error = ?, sync_at = ?
            WHERE id = ?
            """,
            (
                0 if sync_error else 1,
                sync_error or "",
                int(time.time()),
                transaction_id,
            ),
        )
        self._conn.commit()
