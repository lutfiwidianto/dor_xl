import json
import os
import random
import time
from pathlib import Path
from typing import Any

import requests

BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = BASE_DIR / "firebase.config.json"


class TelegramOTP:
    def __init__(self):
        self._config = self._load_config()
        self._bot_token = self._config.get("telegram_bot_token", "").strip()
        self._bot_username = self._config.get("telegram_bot_username", "").strip().lstrip("@")
        self._pending: dict[str, dict[str, Any]] = {}

    def _load_config(self) -> dict:
        config = {}
        env_token = os.getenv("DORXL_TG_BOT_TOKEN", "").strip()
        env_username = os.getenv("DORXL_TG_BOT_USERNAME", "").strip()
        if DEFAULT_CONFIG.exists():
            try:
                file_config = json.loads(DEFAULT_CONFIG.read_text(encoding="utf-8"))
            except Exception:
                file_config = {}
            config = {**file_config, **config}
        if env_token:
            config["telegram_bot_token"] = env_token
        if env_username:
            config["telegram_bot_username"] = env_username
        return config

    def _ensure_config(self):
        if not self._bot_token:
            raise RuntimeError(
                "Telegram bot token missing. Set telegram_bot_token in firebase.config.json."
            )
<<<<<<< HEAD
=======

    def bot_username(self) -> str:
        return self._bot_username or ""

    def bot_link(self) -> str:
        if self._bot_username:
            return f"https://t.me/{self._bot_username}"
        return "https://t.me"
>>>>>>> e5b31fbea10b3024584b4db308a75752ea9d2854

    def _api_url(self, method: str) -> str:
        return f"https://api.telegram.org/bot{self._bot_token}/{method}"

    def _get_updates(self) -> list[dict]:
        url = self._api_url("getUpdates")
        resp = requests.get(url, timeout=15)
        if resp.status_code != 200:
            raise RuntimeError(f"Telegram error: {resp.status_code} {resp.text}")
        data = resp.json()
        if not data.get("ok"):
            raise RuntimeError("Telegram getUpdates failed.")
        return data.get("result", [])

    def _find_chat_id_by_username(self, username: str) -> int | None:
        updates = self._get_updates()
        for update in reversed(updates):
            message = update.get("message", {})
            chat = message.get("chat", {})
            from_user = message.get("from", {})
            handle = (from_user.get("username") or "").lower()
            if handle == username.lower():
                return int(chat.get("id"))
        return None

    def _send_message(self, chat_id: int, text: str) -> None:
        url = self._api_url("sendMessage")
        payload = {"chat_id": chat_id, "text": text}
        resp = requests.post(url, json=payload, timeout=15)
        if resp.status_code != 200:
            raise RuntimeError(f"Telegram error: {resp.status_code} {resp.text}")

    def request_otp(self, username: str) -> None:
        self._ensure_config()
        username = username.strip().lstrip("@")
        if not username:
            raise RuntimeError("Telegram username kosong.")
        chat_id = self._find_chat_id_by_username(username)
        if not chat_id:
            bot_hint = f"@{self._bot_username}" if self._bot_username else "bot Anda"
            raise RuntimeError(
                f"Chat ID tidak ditemukan. Buka Telegram, cari {bot_hint}, lalu kirim /start."
            )
        code = f"{random.randint(0, 999999):06d}"
        expires_at = int(time.time()) + 300
        self._pending[username.lower()] = {
            "code": code,
            "expires_at": expires_at,
        }
        self._send_message(chat_id, f"Kode OTP Anda: {code}")

    def verify_otp(self, username: str, code: str) -> bool:
        username = username.strip().lstrip("@").lower()
        entry = self._pending.get(username)
        if not entry:
            return False
        if int(time.time()) > int(entry.get("expires_at", 0)):
            return False
        return str(entry.get("code", "")) == str(code).strip()


TelegramOTPInstance = TelegramOTP()
