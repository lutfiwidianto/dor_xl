import json
import os
from pathlib import Path

try:
    import firebase_admin
    from firebase_admin import credentials, db
except ImportError:  # pragma: no cover - handled at runtime
    firebase_admin = None
    credentials = None
    db = None

BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = BASE_DIR / "firebase.config.json"


class FirebaseSync:
    _initialized = False
    _enabled = False

    @classmethod
    def _load_config(cls) -> dict:
        config = {}
        env_db_url = os.getenv("DORXL_FIREBASE_DB_URL", "").strip()
        env_cred_path = os.getenv("DORXL_FIREBASE_CRED_PATH", "").strip()
        if env_db_url and env_cred_path:
            config["database_url"] = env_db_url
            config["service_account_path"] = env_cred_path
            return config
        if DEFAULT_CONFIG.exists():
            try:
                config = json.loads(DEFAULT_CONFIG.read_text(encoding="utf-8"))
            except Exception:
                config = {}
        return config

    @classmethod
    def _init_app(cls) -> bool:
        if cls._initialized:
            return cls._enabled
        cls._initialized = True
        if firebase_admin is None:
            return False
        config = cls._load_config()
        db_url = config.get("database_url", "").strip()
        cred_path = config.get("service_account_path", "").strip()
        if not db_url or not cred_path or not os.path.exists(cred_path):
            return False
        if not firebase_admin._apps:
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred, {"databaseURL": db_url})
        cls._enabled = True
        return True

    @classmethod
    def push_transaction(cls, payload: dict) -> tuple[bool, str]:
        if not cls._init_app():
            return False, "firebase_not_configured"
        try:
            ref = db.reference("transactions")
            ref.push(payload)
            return True, ""
        except Exception as exc:
            return False, str(exc)
