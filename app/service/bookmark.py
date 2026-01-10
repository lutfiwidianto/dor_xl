import os
import json
from typing import List, Dict

from app.service.app_user_auth import AppUserAuthInstance

class Bookmark:
    _instance = None
    _initialized = False

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self.packages: List[Dict] = []
            self.filepath = "bookmark.json"

            if os.path.exists(self.filepath):
                self.load_bookmark()
            else:
                self._save([])  # create empty file

            self._initialized = True

    def _save(self, data: List[Dict]):
        """Helper to write JSON safely."""
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    def _ensure_schema(self):
        """Ensure all bookmarks have the latest schema fields."""
        updated = False
        for p in self.packages:
            if "family_name" not in p:  # add missing field
                p["family_name"] = ""
                updated = True
            if "order" not in p:
                p["order"] = 0
                updated = True
        if updated:
            self.save_bookmark()  # persist schema upgrade

    def load_bookmark(self):
        """Load bookmarks from Firebase (per user), fallback to local file."""
        try:
            remote = AppUserAuthInstance.get_bookmarks()
            if isinstance(remote, list):
                self.packages = remote
                self._ensure_schema()
                return
        except Exception:
            pass
        with open(self.filepath, "r", encoding="utf-8") as f:
            self.packages = json.load(f)
        self._ensure_schema()

    def save_bookmark(self):
        """Save current bookmarks to Firebase (per user), fallback to local file."""
        try:
            AppUserAuthInstance.replace_bookmarks(self.packages)
            return
        except Exception:
            pass
        self._save(self.packages)

    def add_bookmark(
        self,
        family_code: str,
        family_name: str,
        is_enterprise: bool,
        variant_name: str,
        option_name: str,
        order: int,
    ) -> bool:
        """Add a bookmark if it does not already exist."""
        self.load_bookmark()
        key = (family_code, variant_name, order)

        if any(
            (p["family_code"], p["variant_name"], p["order"]) == key
            for p in self.packages
        ):
            print("Bookmark already exists.")
            return False

        self.packages.append(
            {
                "family_name": family_name,  # required field
                "family_code": family_code,
                "is_enterprise": is_enterprise,
                "variant_name": variant_name,
                "option_name": option_name,
                "order": order,
            }
        )
        self.save_bookmark()
        print("Bookmark added.")
        return True

    def remove_bookmark(
        self,
        family_code: str,
        is_enterprise: bool,
        variant_name: str,
        order: int,
    ) -> bool:
        """Remove a bookmark if it exists. Returns True if removed."""
        self.load_bookmark()
        for i, p in enumerate(self.packages):
            if (
                p["family_code"] == family_code
                and p["is_enterprise"] == is_enterprise
                and p["variant_name"] == variant_name
                and p["order"] == order
            ):
                del self.packages[i]
                self.save_bookmark()
                print("Bookmark removed.")
                return True
        print("Bookmark not found.")
        return False

    def get_bookmarks(self) -> List[Dict]:
        """Return all bookmarks."""
        self.load_bookmark()
        return self.packages.copy()

BookmarkInstance = Bookmark()
