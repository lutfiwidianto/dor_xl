import subprocess
import sys
import os
import shutil
import json
import time
import re
from datetime import datetime

# Pastikan output UTF-8 (Windows friendly)
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass


# Fallback ASCII output when terminal is not UTF-8
_EMOJI_MAP = {
    "🔥": "[HOT]",
    "🔄": "[REFRESH]",
    "📦": "[PKG]",
    "📋": "[MENU]",
    "📱": "[PHONE]",
    "📝": "[NOTE]",
    "📊": "[STAT]",
    "📞": "[CALL]",
    "💬": "[CHAT]",
    "🎁": "[GIFT]",
    "🎉": "[BONUS]",
    "🚀": "[GO]",
    "🔍": "[CHECK]",
    "🔐": "[LOCK]",
    "🚨": "[ALERT]",
    "👋": "[BYE]",
    "💰": "[PAY]",
    "💳": "[CARD]",
    "🎯": "[TARGET]",
    "🤑": "[RICH]",
    "🤫": "[HUSH]",
    "📨": "[MSG]",
}

_ORIG_PRINT = print
_ORIG_INPUT = input


def _replace_emoji(text: str) -> str:
    out = text
    for key, val in _EMOJI_MAP.items():
        out = out.replace(key, val)
    return out


def _wrap_print(*args, **kwargs):
    enc = (sys.stdout.encoding or "").lower()
    if "utf-8" not in enc:
        args = tuple(_replace_emoji(str(a)) for a in args)
    return _ORIG_PRINT(*args, **kwargs)


def _wrap_input(prompt: str = ""):
    enc = (sys.stdout.encoding or "").lower()
    if "utf-8" not in enc:
        prompt = _replace_emoji(str(prompt))
    return _ORIG_INPUT(prompt)


print = _wrap_print
input = _wrap_input
if os.name == "nt":
    try:
        os.system("chcp 65001 >nul")
        os.environ.setdefault("PYTHONUTF8", "1")
        os.environ.setdefault("PYTHONIOENCODING", "utf-8")
        import ctypes
        ctypes.windll.kernel32.SetConsoleOutputCP(65001)
        ctypes.windll.kernel32.SetConsoleCP(65001)
    except Exception:
        pass

# =========================================================================
# 1. LOGIKA PEMULIHAN DARURAT & AUTO UPDATE
# =========================================================================

def emergency_repair():
    """Fungsi ini berjalan jika folder 'app' atau 'git.py' hilang."""
    print("\n" + "!"*50)
    print("🚨 ERROR: SISTEM RUSAK ATAU FILE HILANG!")
    print("Mencoba melakukan pemulihan otomatis dari GitHub...")
    print("!"*50 + "\n")
    try:
        # Memaksa git untuk menarik kembali semua file yang hilang
        subprocess.run(["git", "fetch", "origin", "main"], check=True, capture_output=True)
        subprocess.run(["git", "reset", "--hard", "origin/main"], check=True)
        print("\nâœ… Sistem berhasil dipulihkan! Menjalankan ulang aplikasi...")
        # Restart script
        os.execv(sys.executable, [sys.executable] + sys.argv)
    except Exception as e:
        print(f"âŒ Gagal memulihkan sistem secara otomatis: {e}")
        print("Saran: Pastikan Git terinstal dan jalankan 'git clone' ulang.")
        sys.exit(1)

# Auto update dipindahkan ke menu utama (manual).

# =========================================================================
# 2. IMPORT MODUL INTERNAL (SETELAH DIPASTIKAN FILE LENGKAP)
# =========================================================================
try:
    from dotenv import load_dotenv
    load_dotenv()
    from app.menus.util import clear_screen, pause
    from app.menus import banner 
    from app.client.myxl_api import get_balance, get_tiering_info
    from app.client.famplan import validate_msisdn
    from app.menus.payment import show_transaction_history
    from app.service.auth import AuthInstance
    from app.menus.bookmark import show_bookmark_menu
    from app.menus.account import show_account_menu
    from app.menus.package import fetch_my_packages, get_packages_by_family, show_package_details
    from app.menus.hot import show_hot_menu, show_hot_menu2
    from app.service.sentry import enter_sentry_mode
    from app.menus.purchase import purchase_by_family
    from app.menus.famplan import show_family_info
    from app.menus.circle import show_circle_info
    from app.menus.notification import show_notification_menu
    from app.menus.firebase import show_firebase_menu
    from app.menus.store.segments import show_store_segments_menu
    from app.menus.store.search import show_family_list_menu, show_store_packages_menu
    from app.menus.store.redemables import show_redeemables_menu
    from app.menus.store.scanner import show_active_family_code_scanner
    from app.menus.store.scanner import show_store_purchase_from_scan
    from app.menus.store.scanner import show_store_search_by_keyword
    from app.client.registration import dukcapil
    from app.menus.sharing import show_balance_allotment_menu
    from app.service.app_user_auth import AppUserAuthInstance
    from app.menus.app_auth import show_app_auth_menu
    from app.menus.admin import show_admin_menu
except ImportError as e:
    print(f"âŒ Error saat memuat modul: {e}")
    emergency_repair()

# =========================================================================
# 3. FUNGSI TAMPILAN MENU
# =========================================================================
def show_main_menu(profile, *, is_admin: bool = False):
    try:
        columns, _ = os.get_terminal_size()
        WIDTH = columns - 2
    except:
        WIDTH = 45
    
    clear_screen()
    C, G, Y, R, M, W, B, RESET = "\033[36m", "\033[32m", "\033[33m", "\033[31m", "\033[35m", "\033[97m", "\033[1m", "\033[0m"
    banner.load("", globals(), width=WIDTH)

    def print_line(content):
        print(f"  {content}{RESET}")

    ansi_re = re.compile(r"\x1b\[[0-9;]*m")

    def _w(s: str) -> int:
        return len(ansi_re.sub("", str(s)))

    def _pad(s: str, width: int) -> str:
        return f"{s}{' ' * max(0, width - _w(s))}"

    def print_two_col(left: str, right: str = "") -> None:
        content_w = max(10, WIDTH - 2)
        col_w = max(10, (content_w - 3) // 2)
        line = f"{_pad(left, col_w)} | {_pad(right, col_w)}"
        print_line(line)

    # Format Tanggal & Saldo
    expired_at_dt = datetime.fromtimestamp(profile["balance_expired_at"]).strftime("%Y-%m-%d")
    try:
        balance_fmt = f"{int(profile['balance']):,}".replace(",", ".")
    except:
        balance_fmt = profile['balance']

    print(f"{C}" + "─" * WIDTH + f"{RESET}")
    number_str = str(profile.get("number", ""))
    masked = f"{'*' * max(len(number_str) - 3, 0)}{number_str[-3:]}" if number_str else ""
    name = str(profile.get("name", "")).strip()
    left_user = f"Nama  : {W}{name}{RESET}" if name else "Nama  : -"
    right_type = f"Type : {M}{profile['subscription_type']}{RESET}"
    print_two_col(left_user, right_type)
    print_two_col(
        f"Nomor  : {Y}{masked}{RESET}",
        f"Exp  : {R}{expired_at_dt}{RESET}",
    )
    print_two_col(
        f"Pulsa  : {G}Rp {balance_fmt}{RESET}",
        f"Points : {profile['point_info']}",
    )
    print(f"{C}" + "─" * WIDTH + f"{RESET}")
    print(f"  {W}{B}MAIN MENU{RESET}")
    print(f"{C}" + "─" * WIDTH + f"{RESET}")

    menus = [
        ("1", "Daftar Nomor (XL)"), ("2", "Lihat Paket Saya"),
        ("3", "Beli Paket 🔥 HOT 🔥"), ("4", "Beli Paket 🔥 HOT-2 🔥"),
        ("5", "Beli Paket (Option Code)"), ("6", "Beli Paket (Family Code)"),
        ("7", "Beli Paket Family (Loop)"), ("8", "Riwayat Transaksi"),
        ("9", "Family Plan / Akrab"), ("10", "Circle Info"),
        ("11", "Store Segments"), ("12", "Store Family List"),
        ("13", "Store Packages"), ("14", "Redeemables"),
        ("15", "Scan Family Code Aktif"),
        ("16", "Beli Paket Store (Hasil Scan)"),
        ("17", "Cari Paket (Keyword)"),
        ("BA", "Balance Allotment"), ("R", "Register (Dukcapil)"),
        ("N", "Notifikasi"), ("V", "Validate MSISDN"),
        ("00", "Bookmark Paket"), ("F", "Sync Data (Admin)"), ("L", "Logout Akun Aplikasi"), ("U", "Update Aplikasi (Git Pull)"), ("99", "Tutup Aplikasi")
    ]
    if is_admin:
        menus.append(("A", "Admin User"))

    for code, label in menus:
        color = Y if code.isdigit() else G
        if code == "99": color = R
        print_line(f"[{color}{code:>2}{RESET}] {label}")

    print(f"{C}" + "─" * WIDTH + f"{RESET}")
    print(f"{B} Pilih menu: {RESET}", end="")


def show_unlinked_menu() -> None:
    try:
        columns, _ = os.get_terminal_size()
        width = columns - 2
    except Exception:
        width = 45

    clear_screen()
    C, G, Y, R, W, B, RESET = "[36m", "[32m", "[33m", "[31m", "[97m", "[1m", "[0m"
    banner.load("", globals(), width=width)

    print(f"{C}" + "?" * width + f"{RESET}")
    print(f"  {W}{B}MENU UTAMA{RESET}")
    print(f"{C}" + "?" * width + f"{RESET}")
    print(f"  [{Y} 1{RESET}] Daftar Nomor (Akun XL)")
    print(f"  [{G} L{RESET}] Logout Akun Aplikasi")
    print(f"  [{R}99{RESET}] Tutup Aplikasi")
    print(f"{C}" + "?" * width + f"{RESET}")
    print(f"{B} Pilih menu: {RESET}", end="")

# =========================================================================
# 4. LOGIKA UTAMA (WHILE LOOP)
# =========================================================================
_BALANCE_CACHE = {"ts": 0, "balance": None, "tier": None}


def _get_cached_balance(api_key: str, tokens: dict, subscription_type: str, ttl_sec: int = 60):
    now = int(time.time())
    if _BALANCE_CACHE["balance"] is not None and (now - _BALANCE_CACHE["ts"]) < ttl_sec:
        return _BALANCE_CACHE["balance"], _BALANCE_CACHE["tier"]

    balance = get_balance(api_key, tokens["id_token"])
    if not isinstance(balance, dict):
        balance = {"remaining": 0, "expired_at": 0}

    tier_info = None
    if subscription_type == "PREPAID":
        tier_info = get_tiering_info(api_key, tokens) or {}

    _BALANCE_CACHE["ts"] = now
    _BALANCE_CACHE["balance"] = balance
    _BALANCE_CACHE["tier"] = tier_info
    return balance, tier_info


def main():
    while True:
        try:
            logged_in = AppUserAuthInstance.is_logged_in()
        except Exception as exc:
            print(f"Konfigurasi Firebase belum lengkap: {exc}")
            print("Silakan isi firebase.config.json atau env vars, lalu coba lagi.")
            sys.exit(1)
        if not logged_in:
            ok = show_app_auth_menu()
            if not ok:
                print("Terima kasih telah menggunakan aplikasi.")
                sys.exit(0)
            AuthInstance.reload_after_login()

        active_user = AuthInstance.get_active_user()
        
        if active_user is not None:
            # Cache balance & tiering supaya tidak hit API setiap kembali ke menu
            balance, tiering_data = _get_cached_balance(
                AuthInstance.api_key,
                active_user["tokens"],
                active_user["subscription_type"],
                ttl_sec=60,
            )
            balance_remaining = balance.get("remaining", 0)
            balance_expired_at = balance.get("expired_at", 0)
            
            point_info = "N/A | Tier: N/A"
            if active_user["subscription_type"] == "PREPAID" and isinstance(tiering_data, dict):
                tier = tiering_data.get("tier", "N/A")
                current_point = tiering_data.get("current_point", 0)
                point_info = f"{current_point} | Tier: {tier}"
            
            app_profile = AppUserAuthInstance.get_profile()
            name = (app_profile or {}).get("name", "")
            profile = {
                "number": active_user["number"],
                "balance": balance_remaining,
                "balance_expired_at": balance_expired_at,
                "subscription_type": active_user["subscription_type"],
                "point_info": point_info,
                "name": name,
            }

            is_admin = AppUserAuthInstance.is_admin()
            show_main_menu(profile, is_admin=is_admin)
            choice = input().lower()

            # --- EKSEKUSI PILIHAN MENU ---
            if choice == "1":
                selected = show_account_menu()
                if selected: AuthInstance.set_active_user(selected)
            elif choice == "2":
                fetch_my_packages()
            elif choice == "3":
                show_hot_menu()
            elif choice == "4":
                show_hot_menu2()
            elif choice == "5":
                code = input("Masukkan Option Code: ")
                show_package_details(AuthInstance.api_key, active_user["tokens"], code, False)
            elif choice == "6":
                code = input("Masukkan Family Code: ")
                get_packages_by_family(code)
            elif choice == "7":
                f_code = input("Family Code: ")
                purchase_by_family(f_code, False)
            elif choice == "8":
                show_transaction_history(AuthInstance.api_key, active_user["tokens"])
            elif choice == "9":
                show_family_info(AuthInstance.api_key, active_user["tokens"])
            elif choice == "10":
                show_circle_info(AuthInstance.api_key, active_user["tokens"])
            elif choice == "11":
                show_store_segments_menu(False)
            elif choice == "12":
                show_family_list_menu(profile['subscription_type'], False)
            elif choice == "13":
                show_store_packages_menu(profile['subscription_type'], False)
            elif choice == "14":
                show_redeemables_menu(False)
            elif choice == "15":
                show_active_family_code_scanner(profile['subscription_type'], False)
            elif choice == "16":
                show_store_purchase_from_scan(profile['subscription_type'], False)
            elif choice == "17":
                show_store_search_by_keyword(profile['subscription_type'], False)
            elif choice == "ba":
                show_balance_allotment_menu()
            elif choice == "r":
                m = input("MSISDN: "); k = input("KK: "); n = input("NIK: ")
                res = dukcapil(AuthInstance.api_key, m, k, n)
                print(json.dumps(res, indent=2)); pause()
            elif choice == "n":
                show_notification_menu()
            elif choice == "v":
                m = input("MSISDN to Validate: ")
                res = validate_msisdn(AuthInstance.api_key, active_user["tokens"], m)
                print(json.dumps(res, indent=2)); pause()
            elif choice == "00":
                show_bookmark_menu()
            elif choice == "f":
                show_firebase_menu()
            elif choice == "a" and AppUserAuthInstance.is_admin():
                show_admin_menu()
            elif choice == "u":
                try:
                    from app.service.git import auto_update
                    auto_update()
                    pause()
                except Exception as e:
                    print(f"Gagal update aplikasi: {e}")
                    pause()
            elif choice == "l":
                AppUserAuthInstance.logout()
                print("Logout berhasil.")
                pause()
            elif choice == "s":
                enter_sentry_mode()
            elif choice == "99":
                print("Terima kasih telah menggunakan aplikasi."); sys.exit(0)
            else:
                print("âŒ Pilihan tidak valid!"); pause()
        else:
            show_unlinked_menu()
            choice = input().lower()
            if choice == "1":
                selected = show_account_menu()
                if selected:
                    AuthInstance.set_active_user(selected)
            elif choice == "l":
                AppUserAuthInstance.logout()
                print("Logout berhasil.")
                pause()
            elif choice == "99":
                print("Terima kasih telah menggunakan aplikasi.")
                sys.exit(0)
            else:
                print("Pilihan tidak valid.")
                pause()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Keluar dari aplikasi.")
    except Exception as e:
        print(f"âŒ Terjadi kesalahan sistem: {e}")
