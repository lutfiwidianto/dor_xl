from app.menus.util_box import (
    print_menu_box,
    input_box,
    print_card,
    get_terminal_width,
    C, G, Y, R, W, RESET,
)
from app.service.firebase_store import FirebaseStore


def show_firebase_menu():
    width = get_terminal_width()
    store = FirebaseStore()

    while True:
        options = [
            f"{C}[{W}1{C}] {W}Login Firebase (Sync Admin){RESET}",
            f"{C}[{W}2{C}] {W}Test Sync (kirim data contoh){RESET}",
            f"{C}[{W}3{C}] {W}Set Firebase API Key{RESET}",
            f"{C}[{R}00{C}] {W}Kembali{RESET}",
        ]
        print_menu_box("SYNC DATA (ADMIN)", options, width=width, color=C)
        choice = input_box("Pilihan:", width=width).strip().lower()

        if choice == "00":
            return
        if choice == "1":
            try:
                store.ensure_login()
                print_card(
                    f"{G}Login Firebase berhasil (untuk sync data).{RESET}",
                    "INFO",
                    width=width,
                    color=G,
                )
            except Exception as exc:
                print_card(f"{R}Gagal login: {exc}{RESET}", "ERROR", width=width, color=R)
            input(f"\n{W}Tekan Enter untuk kembali...{RESET}")
            continue
        if choice == "2":
            payload = {
                "timestamp": 0,
                "package_code": "TEST",
                "package_name": "Test Sync",
                "method": "TEST",
                "amount": 0,
                "status": "SUCCESS",
                "error_code": "",
                "error_message": "",
                "user_number_masked": "00****00",
            }
            ok, err = store.push_transaction(payload)
            if ok:
                print_card(f"{G}Test sync berhasil terkirim.{RESET}", "INFO", width=width, color=G)
            else:
                print_card(f"{R}Test sync gagal: {err}{RESET}", "ERROR", width=width, color=R)
            input(f"\n{W}Tekan Enter untuk kembali...{RESET}")
            continue
        if choice == "3":
            api_key = input("Masukkan Firebase API Key: ").strip()
            if not api_key:
                print_card(f"{Y}API key kosong.{RESET}", "INFO", width=width, color=Y)
                input(f"\n{W}Tekan Enter untuk kembali...{RESET}")
                continue
            store.set_api_key(api_key)
            print_card(f"{G}API key tersimpan.{RESET}", "INFO", width=width, color=G)
            input(f"\n{W}Tekan Enter untuk kembali...{RESET}")
            continue

        print_card(f"{R}Pilihan tidak valid!{RESET}", "ERROR", width=width // 2, color=R)
        input(f"\n{W}Tekan Enter untuk kembali...{RESET}")
