import os
import sys

# Load API key from text file named api.key
def load_api_key() -> str:
    if os.path.exists("api.key"):
        with open("api.key", "r", encoding="utf8") as f:
            api_key = f.read().strip()
        if api_key:
            print("API key loaded successfully.")
            return api_key
        else:
            print("API key file is empty.")
            return ""
    else:
        print("API key file not found.")
        return ""
    
def save_api_key(api_key: str):
    with open("api.key", "w", encoding="utf8") as f:
        f.write(api_key)
    print("API key saved successfully.")
    
def delete_api_key():
    if os.path.exists("api.key"):
        os.remove("api.key")
        print("API key file deleted.")
    else:
        print("API key file does not exist.")

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
