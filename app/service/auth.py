import json
import time
from pathlib import Path
from app.client.ciam import get_new_token
from app.client.myxl_api import get_profile
from app.util import ensure_api_key
from app.service.firebase_store import FirebaseStore
from app.service.app_user_auth import AppUserAuthInstance

class Auth:
    _instance_ = None
    _initialized_ = False

    api_key = ""

    refresh_tokens = []
    # Format of refresh_tokens:
    # [
        # {
            # "number": int,
            # "subscriber_id": str,
            # "subscription_type": str,
            # "refresh_token": str
        # }
    # ]

    active_user = None
    # {
    #     "number": int,
    #     "subscriber_id": str,
    #     "subscription_type": str,
    #     "tokens": {
    #         "refresh_token": str,
    #         "access_token": str,
    #         "id_token": str
	#     }
    # }
    
    last_refresh_time = None
    _cached_tokens_path = Path(__file__).resolve().parents[1] / "data" / "active_tokens.json"
    
    def __new__(cls, *args, **kwargs):
        if not cls._instance_:
            cls._instance_ = super().__new__(cls)
        return cls._instance_
    
    def __init__(self):
        if not self._initialized_:
            self.api_key = ensure_api_key()
            self.store = FirebaseStore(auth_provider=AppUserAuthInstance.get_auth)
            try:
                self.load_tokens()
                # Select active user from file if available
                self.load_active_number()
            except Exception:
                # App user login bisa belum dilakukan saat startup
                pass
            self.last_refresh_time = int(time.time())

            self._initialized_ = True
            
    def load_tokens(self):
        try:
            refresh_tokens = self.store.get_refresh_tokens()
        except Exception:
            self.refresh_tokens = []
            return
        if len(refresh_tokens) != 0:
            self.refresh_tokens = []
        # Validate and load tokens
        for rt in refresh_tokens:
            if "number" in rt and "refresh_token" in rt:
                self.refresh_tokens.append(rt)
            else:
                print(f"Invalid token entry: {rt}")

    def add_refresh_token(self, number: int, refresh_token: str):
        # Check if number already exist, if yes, replace it, if not append
        existing = next((rt for rt in self.refresh_tokens if rt["number"] == number), None)
        if existing:
            existing["refresh_token"] = refresh_token
        else:
            tokens = get_new_token(self.api_key, refresh_token, "")
            profile_data = get_profile(self.api_key, tokens["access_token"], tokens["id_token"])
            sub_id = profile_data["profile"]["subscriber_id"]
            sub_type = profile_data["profile"]["subscription_type"]

            self.refresh_tokens.append({
                "number": int(number),
                "subscriber_id": sub_id,
                "subscription_type": sub_type,
                "refresh_token": refresh_token
            })
        
        # Save to Firebase
        self.write_tokens_to_file()

        # Set active user to newly added
        self.set_active_user(number)
            
    def _save_cached_tokens(self) -> None:
        if not self.active_user:
            return
        payload = {
            "number": self.active_user.get("number"),
            "subscriber_id": self.active_user.get("subscriber_id", ""),
            "subscription_type": self.active_user.get("subscription_type", ""),
            "tokens": self.active_user.get("tokens", {}),
            "expires_at": self.active_user.get("tokens", {}).get("expires_at", 0),
        }
        self._cached_tokens_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._cached_tokens_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
        except Exception:
            pass

    def _load_cached_tokens(self) -> dict | None:
        if not self._cached_tokens_path.exists():
            return None
        try:
            data = json.loads(self._cached_tokens_path.read_text(encoding="utf-8"))
        except Exception:
            return None
        if not isinstance(data, dict):
            return None
        tokens = data.get("tokens", {})
        if not isinstance(tokens, dict):
            return None
        expires_at = int(tokens.get("expires_at") or data.get("expires_at") or 0)
        if expires_at <= int(time.time()):
            return None
        return data

    def remove_refresh_token(self, number: int):
        self.refresh_tokens = [rt for rt in self.refresh_tokens if rt["number"] != number]
        
        # Save to Firebase
        self.write_tokens_to_file()
        
        # If the removed user was the active user, select a new active user if available
        if self.active_user and self.active_user["number"] == number:
            # Select the first user as active user by default
            if len(self.refresh_tokens) != 0:
                first_rt = self.refresh_tokens[0]
                tokens = get_new_token(self.api_key, first_rt["refresh_token"], first_rt.get("subscriber_id", ""))
                if tokens:
                    self.set_active_user(first_rt["number"])
            else:
                input("No users left. Press Enter to continue...")
                self.active_user = None

    def set_active_user(self, number: int):
        # Get refresh token for the number from refresh_tokens
        rt_entry = next((rt for rt in self.refresh_tokens if rt["number"] == number), None)
        if not rt_entry:
            print(f"No refresh token found for number: {number}")
            input("Press Enter to continue...")
            return False

        tokens = get_new_token(self.api_key, rt_entry["refresh_token"], rt_entry.get("subscriber_id", ""))
        if not tokens:
            print(f"Failed to get tokens for number: {number}. The refresh token might be invalid or expired.")
            input("Press Enter to continue...")
            return False
        expires_in = int(tokens.get("expires_in") or tokens.get("expiresIn") or 3600)
        tokens["expires_at"] = int(time.time()) + max(60, expires_in - 60)

        profile_data = get_profile(self.api_key, tokens["access_token"], tokens["id_token"])
        subscriber_id = profile_data["profile"]["subscriber_id"]
        subscription_type = profile_data["profile"]["subscription_type"]

        self.active_user = {
            "number": int(number),
            "subscriber_id": subscriber_id,
            "subscription_type": subscription_type,
            "tokens": tokens
        }
        
        # Update refresh token entry with subscriber_id and subscription_type
        rt_entry["subscriber_id"] = subscriber_id
        rt_entry["subscription_type"] = subscription_type
        
        # Update refresh token. The real client app do this, not sure why cz refresh token should still be valid
        rt_entry["refresh_token"] = tokens["refresh_token"]
        self.write_tokens_to_file()
        
        self.last_refresh_time = int(time.time())
        
        # Simpan cache lokal untuk menghindari refresh berulang saat startup
        self._save_cached_tokens()

        # Save active number to file
        self.write_active_number()

    def renew_active_user_token(self):
        if self.active_user:
            tokens = get_new_token(self.api_key, self.active_user["tokens"]["refresh_token"], self.active_user["subscriber_id"])
            if tokens:
                expires_in = int(tokens.get("expires_in") or tokens.get("expiresIn") or 3600)
                tokens["expires_at"] = int(time.time()) + max(60, expires_in - 60)
                self.active_user["tokens"] = tokens
                self.last_refresh_time = int(time.time())
                self.add_refresh_token(self.active_user["number"], self.active_user["tokens"]["refresh_token"])
                self._save_cached_tokens()
                
                print("Active user token renewed successfully.")
                return True
            else:
                print("Failed to renew active user token.")
                input("Press Enter to continue...")
        else:
            print("No active user set or missing refresh token.")
            input("Press Enter to continue...")
        return False
    
    def get_active_user(self):
        if not self.active_user:
            cached = self._load_cached_tokens()
            if cached:
                tokens = cached.get("tokens", {})
                self.active_user = {
                    "number": int(cached.get("number", 0)),
                    "subscriber_id": cached.get("subscriber_id", ""),
                    "subscription_type": cached.get("subscription_type", ""),
                    "tokens": tokens,
                }
                rt = tokens.get("refresh_token")
                if rt:
                    existing = next((rtx for rtx in self.refresh_tokens if rtx["number"] == self.active_user["number"]), None)
                    if not existing:
                        self.refresh_tokens.append({
                            "number": self.active_user["number"],
                            "subscriber_id": self.active_user["subscriber_id"],
                            "subscription_type": self.active_user["subscription_type"],
                            "refresh_token": rt,
                        })
                return self.active_user
            # Choose the first user if available
            if len(self.refresh_tokens) != 0:
                first_rt = self.refresh_tokens[0]
                tokens = get_new_token(self.api_key, first_rt["refresh_token"], first_rt.get("subscriber_id", ""))
                if tokens:
                    self.set_active_user(first_rt["number"])
            return None

        expires_at = int(self.active_user.get("tokens", {}).get("expires_at") or 0)
        if expires_at and int(time.time()) < (expires_at - 60):
            return self.active_user

        if self.last_refresh_time is None or (int(time.time()) - self.last_refresh_time) > 300:
            self.renew_active_user_token()
            self.last_refresh_time = time.time()

        return self.active_user

    def get_active_tokens(self) -> dict | None:
        active_user = self.get_active_user()
        return active_user["tokens"] if active_user else None
    
    def write_tokens_to_file(self):
        try:
            self.store.replace_refresh_tokens(self.refresh_tokens)
        except Exception:
            return
    
    def write_active_number(self):
        if self.active_user:
            try:
                self.store.set_active_number(self.active_user["number"])
            except Exception:
                return
        else:
            try:
                self.store.set_active_number("")
            except Exception:
                return
    
    def load_active_number(self):
        try:
            number_str = self.store.get_active_number()
        except Exception:
            return
        if number_str and str(number_str).isdigit():
            number = int(number_str)
            cached = self._load_cached_tokens()
            if cached and int(cached.get("number", 0)) == number:
                tokens = cached.get("tokens", {})
                self.active_user = {
                    "number": number,
                    "subscriber_id": cached.get("subscriber_id", ""),
                    "subscription_type": cached.get("subscription_type", ""),
                    "tokens": tokens,
                }
                return
            self.set_active_user(number)

    def reload_after_login(self):
        self.load_tokens()
        self.load_active_number()

AuthInstance = Auth()
