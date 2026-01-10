import json
import os
import time
from pathlib import Path

import requests

BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = BASE_DIR / "firebase.config.json"
DEFAULT_AUTH_FILE = BASE_DIR / "data" / "firebase_auth.json"
DEFAULT_LOCAL_STORE = BASE_DIR / "data" / "local_store.json"


class FirebaseStore:
    def __init__(self, auth_provider=None):
        self._config = self._load_config()
        self._auth_provider = auth_provider
        self._auth = None

    def _load_config(self) -> dict:
        if not DEFAULT_CONFIG.exists():
            return {}
        try:
            return json.loads(DEFAULT_CONFIG.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _save_config(self) -> None:
        payload = {
            'database_url': self._config.get('database_url', ''),
            'api_key': self._config.get('api_key', ''),
        }
        DEFAULT_CONFIG.write_text(
            json.dumps(payload, ensure_ascii=True, indent=2), encoding='utf-8'
        )

    def _save_auth(self, payload: dict):
        auth_path = self._get_auth_path()
        auth_path.parent.mkdir(parents=True, exist_ok=True)
        auth_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")

    def _get_auth_path(self) -> Path:
        return Path(os.getenv("DORXL_FIREBASE_AUTH_PATH", str(DEFAULT_AUTH_FILE)))

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

    def _is_configured(self) -> bool:
        return bool(self._api_key() and self._db_url())

    def _ensure_config(self):
        if not self._is_configured():
            raise RuntimeError("Firebase config missing (database_url/api_key). Set in firebase.config.json.")

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

    def _ensure_auth(self, prompt: bool = False) -> dict | None:
        if self._auth_provider:
            auth = self._auth_provider()
            if auth:
                self._auth = auth
            return auth
        if not self._is_configured():
            if prompt:
                self._ensure_config()
            return None
        if self._auth:
            if self._auth.get("expiresAt", 0) > int(time.time()):
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
        if not prompt:
            return None
        print("Login Firebase diperlukan untuk sinkronisasi data (bukan login user).")
        email = input("Email Firebase: ").strip()
        password = input("Password Firebase: ").strip()
        signed_in = self._sign_in(email, password)
        if not signed_in:
            create = input("Akun belum ada. Buat baru? (y/n): ").strip().lower()
            if create == "y":
                signed_in = self._sign_up(email, password)
        if not signed_in:
            raise RuntimeError("Gagal login Firebase.")
        self._save_auth(signed_in)
        self._auth = signed_in
        return self._auth

    def _request(self, method: str, path: str, payload: dict | None = None):
        self._ensure_config()
        auth = self._ensure_auth(prompt=False)
        if not auth:
            raise RuntimeError("Auth Firebase belum tersedia. Login aplikasi atau gunakan menu Sync.")
        url = f"{self._db_url().rstrip('/')}/{path}.json"
        params = {"auth": auth["idToken"]}
        resp = None
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

        if resp.status_code == 401:
            # Token invalid, force re-login and retry once
            auth_path = self._get_auth_path()
            if auth_path.exists():
                try:
                    auth_path.unlink()
                except Exception:
                    pass
            self._auth = None
            auth = self._ensure_auth(prompt=False)
            if not auth:
                raise RuntimeError("Auth Firebase belum tersedia. Login aplikasi atau gunakan menu Sync.")
            params = {"auth": auth["idToken"]}
            if method == "GET":
                resp = requests.get(url, params=params, timeout=15)
            elif method == "PUT":
                resp = requests.put(url, params=params, json=payload, timeout=15)
            elif method == "PATCH":
                resp = requests.patch(url, params=params, json=payload, timeout=15)
            elif method == "POST":
                resp = requests.post(url, params=params, json=payload, timeout=15)

        if resp.status_code >= 400:
            raise RuntimeError(f"Firebase error: {resp.status_code} {resp.text}")
        return resp.json()

    def _user_path(self) -> str:
        auth = self._ensure_auth(prompt=False)
        if not auth:
            raise RuntimeError("Auth Firebase belum tersedia. Login aplikasi atau gunakan menu Sync.")
        return f"users/{auth['localId']}"

    def _local_read(self) -> dict:
        if not DEFAULT_LOCAL_STORE.exists():
            return {}
        try:
            return json.loads(DEFAULT_LOCAL_STORE.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _local_write(self, payload: dict) -> None:
        DEFAULT_LOCAL_STORE.parent.mkdir(parents=True, exist_ok=True)
        DEFAULT_LOCAL_STORE.write_text(
            json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8"
        )

    def _use_local_store(self) -> bool:
        return os.getenv("DORXL_ALLOW_LOCAL_STORE", "").strip() == "1"

    def get_refresh_tokens(self) -> list[dict]:
        if self._use_local_store():
            data = self._local_read()
            tokens = data.get("refresh_tokens", [])
            return tokens if isinstance(tokens, list) else []
        data = self._request("GET", f"{self._user_path()}/refresh_tokens")
        if not data:
            return []
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            try:
                return [data[k] for k in sorted(data, key=lambda x: int(x))]
            except Exception:
                return list(data.values())
        return []

    def replace_refresh_tokens(self, refresh_tokens: list[dict]):
        if self._use_local_store():
            data = self._local_read()
            data["refresh_tokens"] = refresh_tokens
            self._local_write(data)
            return
        self._request("PUT", f"{self._user_path()}/refresh_tokens", refresh_tokens)

    def set_active_number(self, number: int | str):
        if self._use_local_store():
            data = self._local_read()
            data["active_number"] = str(number)
            self._local_write(data)
            return
        self._request("PUT", f"{self._user_path()}/active_number", str(number))

    def get_active_number(self) -> str | None:
        if self._use_local_store():
            data = self._local_read()
            number = data.get("active_number")
            return str(number) if number else None
        data = self._request("GET", f"{self._user_path()}/active_number")
        return data if data else None

    def set_last_scan(self, rows: list[dict]) -> None:
        if self._use_local_store():
            data = self._local_read()
            data["last_scan"] = rows
            self._local_write(data)
            return
        self._request("PUT", f"{self._user_path()}/last_scan", rows)

    def get_last_scan(self) -> list[dict]:
        if self._use_local_store():
            data = self._local_read()
            rows = data.get("last_scan", [])
            return rows if isinstance(rows, list) else []
        data = self._request("GET", f"{self._user_path()}/last_scan")
        return data if isinstance(data, list) else []

    def push_transaction(self, payload: dict) -> tuple[bool, str]:
        try:
            self._request("POST", f"transactions/{self._user_path().split('/',1)[1]}", payload)
            return True, ""
        except Exception as exc:
            return False, str(exc)

    def ensure_login(self) -> bool:
        auth = self._ensure_auth(prompt=True)
        if not auth:
            raise RuntimeError("Auth Firebase belum tersedia. Login aplikasi atau gunakan menu Sync.")
        return True

    def set_api_key(self, api_key: str) -> None:
        self._config['api_key'] = api_key.strip()
        self._save_config()

    def migrate_legacy_tokens(self):
        legacy_path = Path("refresh-tokens.json")
        if not legacy_path.exists():
            return
        try:
            legacy_data = json.loads(legacy_path.read_text(encoding="utf-8"))
        except Exception:
            return
        existing = self.get_refresh_tokens()
        if existing:
            return
        if legacy_data:
            self.replace_refresh_tokens(legacy_data)
        active_path = Path("active.number")
        if active_path.exists():
            try:
                active_number = active_path.read_text(encoding="utf-8").strip()
            except Exception:
                active_number = ""
            if active_number:
                self.set_active_number(active_number)
