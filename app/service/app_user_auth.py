import json
import os
import re
import time
from pathlib import Path

import requests

BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = BASE_DIR / "firebase.config.json"
DEFAULT_AUTH_FILE = BASE_DIR / "data" / "app_user_auth.json"


class AppUserAuth:
    def __init__(self):
        self._config = self._load_config()
        self._auth = None

    def _load_config(self) -> dict:
        config = {}
        env_db_url = os.getenv("DORXL_FIREBASE_DB_URL", "").strip()
        env_api_key = os.getenv("DORXL_FIREBASE_API_KEY", "").strip()
        if env_db_url:
            config["database_url"] = env_db_url
        if env_api_key:
            config["api_key"] = env_api_key
        if DEFAULT_CONFIG.exists():
            try:
                file_config = json.loads(DEFAULT_CONFIG.read_text(encoding="utf-8"))
            except Exception:
                file_config = {}
            config = {**file_config, **config}
        return config

    def _save_auth(self, payload: dict) -> None:
        auth_path = self._get_auth_path()
        auth_path.parent.mkdir(parents=True, exist_ok=True)
        auth_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")

    def _get_auth_path(self) -> Path:
        return Path(os.getenv("DORXL_APP_AUTH_PATH", str(DEFAULT_AUTH_FILE)))

    def _load_auth(self) -> dict | None:
        auth_path = self._get_auth_path()
        if not auth_path.exists():
            return None
        try:
            return json.loads(auth_path.read_text(encoding="utf-8"))
        except Exception:
            return None

    def _api_key(self) -> str:
        return self._config.get("api_key", "").strip()

    def _db_url(self) -> str:
        return self._config.get("database_url", "").strip().rstrip("/")

    def _ensure_config(self) -> None:
        if not self._api_key() or not self._db_url():
            raise RuntimeError(
                "Firebase config missing (database_url/api_key). Set via firebase.config.json or env vars."
            )

    def _refresh_id_token(self, refresh_token: str) -> dict | None:
        api_key = self._api_key()
        url = f"https://securetoken.googleapis.com/v1/token?key={api_key}"
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }
        resp = requests.post(url, data=payload, timeout=15)
        if resp.status_code != 200:
            return None
        data = resp.json()
        expires_in = int(data.get("expires_in", "3600"))
        return {
            "idToken": data.get("id_token"),
            "refreshToken": data.get("refresh_token"),
            "localId": data.get("user_id"),
            "expiresAt": int(time.time()) + max(60, expires_in - 60),
        }

    def _sign_in(self, email: str, password: str) -> dict | None:
        api_key = self._api_key()
        url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={api_key}"
        payload = {
            "email": email,
            "password": password,
            "returnSecureToken": True,
        }
        resp = requests.post(url, json=payload, timeout=15)
        if resp.status_code != 200:
            return None
        data = resp.json()
        expires_in = int(data.get("expiresIn", "3600"))
        return {
            "idToken": data.get("idToken"),
            "refreshToken": data.get("refreshToken"),
            "localId": data.get("localId"),
            "email": email,
            "expiresAt": int(time.time()) + max(60, expires_in - 60),
        }

    def _sign_up(self, email: str, password: str) -> dict | None:
        api_key = self._api_key()
        url = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={api_key}"
        payload = {
            "email": email,
            "password": password,
            "returnSecureToken": True,
        }
        resp = requests.post(url, json=payload, timeout=15)
        if resp.status_code != 200:
            return None
        data = resp.json()
        expires_in = int(data.get("expiresIn", "3600"))
        return {
            "idToken": data.get("idToken"),
            "refreshToken": data.get("refreshToken"),
            "localId": data.get("localId"),
            "email": email,
            "expiresAt": int(time.time()) + max(60, expires_in - 60),
        }

    def _request(self, method: str, path: str, payload: dict | None, auth: dict):
        url = f"{self._db_url().rstrip('/')}/{path}.json"
        params = {"auth": auth["idToken"]}
        if method == "GET":
            resp = requests.get(url, params=params, timeout=15)
        elif method == "PUT":
            resp = requests.put(url, params=params, json=payload, timeout=15)
        elif method == "PATCH":
            resp = requests.patch(url, params=params, json=payload, timeout=15)
        elif method == "POST":
            resp = requests.post(url, params=params, json=payload, timeout=15)
        else:
            raise ValueError("Unsupported method")
        if resp.status_code >= 400:
            raise RuntimeError(f"Firebase error: {resp.status_code} {resp.text}")
        return resp.json()

    def _normalize_username(self, username: str) -> str | None:
        normalized = username.strip().lower()
        if not re.fullmatch(r"[a-z0-9._]{4,20}", normalized):
            return None
        return normalized

    def _email_for_username(self, username: str) -> str:
        return f"{username}@dorxl.local"

    def get_auth(self) -> dict | None:
        self._ensure_config()
        if self._auth and self._auth.get("expiresAt", 0) > int(time.time()):
            return self._auth
        auth = self._load_auth()
        if auth and auth.get("expiresAt", 0) > int(time.time()):
            self._auth = auth
            return auth
        if auth and auth.get("refreshToken"):
            refreshed = self._refresh_id_token(auth["refreshToken"])
            if refreshed:
                self._save_auth({**auth, **refreshed})
                self._auth = {**auth, **refreshed}
                return self._auth
        return None

    def is_logged_in(self) -> bool:
        return self.get_auth() is not None

    def login(self, username: str, password: str) -> tuple[bool, str]:
        self._ensure_config()
        normalized = self._normalize_username(username)
        if not normalized:
            return False, "Username tidak valid. Gunakan 4-20 karakter: a-z, 0-9, titik, underscore."
        email = self._email_for_username(normalized)
        signed_in = self._sign_in(email, password)
        if not signed_in:
            return False, "Login gagal. Username atau password salah."
        self._save_auth(signed_in)
        self._auth = signed_in
        try:
            self._request(
                "PATCH",
                f"app_users/{signed_in['localId']}",
                {"last_login_at": int(time.time())},
                signed_in,
            )
        except Exception:
            pass
        return True, ""

    def register(
        self, name: str, phone: str, username: str, password: str, telegram_username: str
    ) -> tuple[bool, str]:
        self._ensure_config()
        normalized = self._normalize_username(username)
        if not normalized:
            return False, "Username tidak valid. Gunakan 4-20 karakter: a-z, 0-9, titik, underscore."
        email = self._email_for_username(normalized)
        signed_up = self._sign_up(email, password)
        if not signed_up:
            return False, "Registrasi gagal. Username mungkin sudah dipakai."
        profile = {
            "username": normalized,
            "name": name.strip(),
            "whatsapp_number": phone.strip(),
            "telegram_username": telegram_username.strip().lstrip("@").lower(),
            "telegram_verified": True,
            "created_at": int(time.time()),
            "last_login_at": int(time.time()),
        }
        try:
            self._request("PUT", f"app_users/{signed_up['localId']}", profile, signed_up)
        except Exception as exc:
            return False, f"Gagal menyimpan profil: {exc}"
        self._save_auth(signed_up)
        self._auth = signed_up
        return True, ""

    def logout(self) -> None:
        auth_path = self._get_auth_path()
        if auth_path.exists():
            try:
                auth_path.unlink()
            except Exception:
                pass
        self._auth = None


AppUserAuthInstance = AppUserAuth()
