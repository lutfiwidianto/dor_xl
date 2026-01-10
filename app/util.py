import os
import sys

from app.config import load_config, update_config

# Load API key from text file named api.key
def load_api_key() -> str:
    config = load_config()
    api_key = str(config.get("xl_api_key", "")).strip()
    if api_key:
        print("API key loaded successfully.")
        return api_key

    if os.path.exists("api.key"):
        with open("api.key", "r", encoding="utf8") as f:
            api_key = f.read().strip()
        if api_key:
            print("API key loaded successfully (migrated from api.key).")
            update_config({"xl_api_key": api_key})
            return api_key
        print("API key file is empty.")
        return ""

    print("API key not found in firebase.config.json.")
    return ""


def save_api_key(api_key: str):
    update_config({"xl_api_key": api_key})
    print("API key saved successfully.")


def delete_api_key():
    config = load_config()
    if "xl_api_key" in config:
        config["xl_api_key"] = ""
        update_config(config)
        print("API key cleared from firebase.config.json.")
    else:
        print("API key not found in firebase.config.json.")


def verify_api_key(api_key: str) -> bool:
    return True


def ensure_api_key() -> str:
    """
    Load api.key if present; otherwise prompt the user.
    Loads the key and saves it without external verification.
    Exits the program if empty.
    """
    current = load_api_key()
    if current:
        return current

    # Prompt user if missing or invalid
    api_key = input("Masukkan API key: ").strip()
    if not api_key:
        print("API key tidak boleh kosong. Menutup aplikasi.")
        sys.exit(1)

    save_api_key(api_key)
    return api_key
