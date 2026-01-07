import subprocess
import sys
import os
import shutil
import json
from datetime import datetime

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
        print("\n✅ Sistem berhasil dipulihkan! Menjalankan ulang aplikasi...")
        # Restart script
        os.execv(sys.executable, [sys.executable] + sys.argv)
    except Exception as e:
        print(f"❌ Gagal memulihkan sistem secara otomatis: {e}")
        print("Saran: Pastikan Git terinstal dan jalankan 'git clone' ulang.")
        sys.exit(1)

# Mencoba memanggil fungsi update dari file terpisah (app/service/git.py)
try:
    from app.service.git import auto_update
    auto_update()
except (ImportError, ModuleNotFoundError):
    # Jika file git.py tidak ditemukan, langsung lari ke pemulihan
    emergency_repair()

# =========================================================================
# 2. IMPORT MODUL INTERNAL (SETELAH DIPASTIKAN FILE LENGKAP)
# =========================================================================
try:
    from dotenv import load_dotenv
    from app.menus.util import clear_screen, pause
    from app.menus import banner 
    from app.client.engsel import get_balance, get_tiering_info
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
    from app.menus.store.segments import show_store_segments_menu
    from app.menus.store.search import show_family_list_menu, show_store_packages_menu
    from app.menus.store.redemables import show_redeemables_menu
    from app.client.registration import dukcapil
    from app.menus.sharing import show_balance_allotment_menu
except ImportError as e:
    print(f"❌ Error saat memuat modul: {e}")
    emergency_repair()

load_dotenv()

# =========================================================================
# 3. FUNGSI TAMPILAN MENU
# =========================================================================
def show_main_menu(profile):
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

    # Format Tanggal & Saldo
    expired_at_dt = datetime.fromtimestamp(profile["balance_expired_at"]).strftime("%Y-%m-%d")
    try:
        balance_fmt = f"{int(profile['balance']):,}".replace(",", ".")
    except:
        balance_fmt = profile['balance']

    print(f"{C}" + "─" * WIDTH + f"{RESET}")
    print_line(f"Nomor  : {Y}{profile['number']}{RESET} | Type : {M}{profile['subscription_type']}{RESET}")
    print_line(f"Pulsa  : {G}Rp {balance_fmt}{RESET} | Exp  : {R}{expired_at_dt}{RESET}")
    print_line(f"{profile['point_info']}")
    print(f"{C}" + "─" * WIDTH + f"{RESET}")
    print(f"  {W}{B}MAIN MENU{RESET}")
    print(f"{C}" + "─" * WIDTH + f"{RESET}")

    menus = [
        ("1", "Login / Ganti Akun"), ("2", "Lihat Paket Saya"),
        ("3", "Beli Paket 🔥 HOT 🔥"), ("4", "Beli Paket 🔥 HOT-2 🔥"),
        ("5", "Beli Paket (Option Code)"), ("6", "Beli Paket (Family Code)"),
        ("7", "Beli Paket Family (Loop)"), ("8", "Riwayat Transaksi"),
        ("9", "Family Plan / Akrab"), ("10", "Circle Info"),
        ("11", "Store Segments"), ("12", "Store Family List"),
        ("13", "Store Packages"), ("14", "Redeemables"),
        ("BA", "Balance Allotment"), ("R", "Register (Dukcapil)"),
        ("N", "Notifikasi"), ("V", "Validate MSISDN"),
        ("00", "Bookmark Paket"), ("99", "Tutup Aplikasi")
    ]

    for code, label in menus:
        color = Y if code.isdigit() else G
        if code == "99": color = R
        print_line(f"[{color}{code:>2}{RESET}] {label}")

    print(f"{C}" + "─" * WIDTH + f"{RESET}")
    print(f"{B} Pilih menu: {RESET}", end="")

# =========================================================================
# 4. LOGIKA UTAMA (WHILE LOOP)
# =========================================================================
def main():
    while True:
        active_user = AuthInstance.get_active_user()
        
        if active_user is not None:
            # Mengambil data terbaru setiap refresh menu
            balance = get_balance(AuthInstance.api_key, active_user["tokens"]["id_token"])
            balance_remaining = balance.get("remaining", 0)
            balance_expired_at = balance.get("expired_at", 0)
            
            point_info = "Points: N/A | Tier: N/A"
            if active_user["subscription_type"] == "PREPAID":
                tiering_data = get_tiering_info(AuthInstance.api_key, active_user["tokens"])
                tier = tiering_data.get("tier", "N/A")
                current_point = tiering_data.get("current_point", 0)
                point_info = f"Points: {current_point} | Tier: {tier}"
            
            profile = {
                "number": active_user["number"],
                "balance": balance_remaining,
                "balance_expired_at": balance_expired_at,
                "subscription_type": active_user["subscription_type"],
                "point_info": point_info
            }

            show_main_menu(profile)
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
            elif choice == "s":
                enter_sentry_mode()
            elif choice == "99":
                print("Terima kasih telah menggunakan aplikasi."); sys.exit(0)
            else:
                print("❌ Pilihan tidak valid!"); pause()
        else:
            # Jika belum login
            selected = show_account_menu()
            if selected: AuthInstance.set_active_user(selected)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Keluar dari aplikasi.")
    except Exception as e:
        print(f"❌ Terjadi kesalahan sistem: {e}")