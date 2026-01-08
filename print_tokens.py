import json
import os
import sys

from dotenv import load_dotenv

load_dotenv()

from app.client.ciam import get_new_token


def _load_api_key() -> str:
    if os.path.exists("api.key"):
        with open("api.key", "r", encoding="utf-8") as f:
            return f.read().strip()
    return ""


def _load_refresh_tokens() -> list[dict]:
    if not os.path.exists("refresh-tokens.json"):
        print("File refresh-tokens.json tidak ditemukan.")
        return []
    try:
        with open("refresh-tokens.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
    except Exception as e:
        print(f"Gagal membaca refresh-tokens.json: {e}")
    return []


def _load_active_number() -> str:
    if os.path.exists("active.number"):
        with open("active.number", "r", encoding="utf-8") as f:
            return f.read().strip()
    return ""


def _pick_refresh_token(tokens: list[dict], active_number: str) -> dict | None:
    if not tokens:
        return None

    if active_number.isdigit():
        for item in tokens:
            if str(item.get("number")) == active_number:
                return item

    if len(tokens) == 1:
        return tokens[0]

    print("Pilih akun:")
    for idx, item in enumerate(tokens, start=1):
        number = item.get("number", "")
        sub_type = item.get("subscription_type", "")
        print(f"{idx}. {number} ({sub_type})")
    choice = input("Nomor pilihan: ").strip()
    if choice.isdigit():
        idx = int(choice)
        if 1 <= idx <= len(tokens):
            return tokens[idx - 1]
    return None


def main() -> int:
    api_key = _load_api_key()
    if not api_key:
        api_key = input("Masukkan API key: ").strip()
        if not api_key:
            print("API key kosong.")
            return 1

    tokens = _load_refresh_tokens()
    if not tokens:
        print("Tidak ada refresh token.")
        return 1

    active_number = _load_active_number()
    selected = _pick_refresh_token(tokens, active_number)
    if not selected:
        print("Akun tidak ditemukan.")
        return 1

    refresh_token = selected.get("refresh_token", "")
    subscriber_id = selected.get("subscriber_id", "")
    if not refresh_token:
        print("Refresh token tidak ditemukan.")
        return 1

    try:
        new_tokens = get_new_token(api_key, refresh_token, subscriber_id)
    except Exception as e:
        print(f"Gagal mengambil token: {e}")
        return 1

    if not isinstance(new_tokens, dict):
        print("Format token tidak valid.")
        return 1

    print("")
    print("access_token:")
    print(new_tokens.get("access_token", ""))
    print("")
    print("id_token:")
    print(new_tokens.get("id_token", ""))
    print("")
    print("refresh_token:")
    print(new_tokens.get("refresh_token", ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
