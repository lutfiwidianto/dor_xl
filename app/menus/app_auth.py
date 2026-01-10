from app.menus.util import clear_screen, pause
from app.menus.util_box import (
    print_header,
    print_card,
    print_menu_box,
    input_box,
    get_terminal_width,
    C,
    G,
    Y,
    R,
)
from app.service.app_user_auth import AppUserAuthInstance


def _validate_phone(phone: str) -> bool:
    return phone.startswith("628") and 10 <= len(phone) <= 14 and phone.isdigit()


def show_app_auth_menu() -> bool:
    while True:
        clear_screen()
        width = get_terminal_width()
        print_header("Login Aplikasi", width)
        print_menu_box(
            "Menu",
            [
                "1. Login",
                "2. Register",
                "99. Tutup aplikasi",
            ],
            width=width,
            color=C,
        )
        choice = input_box("Pilihan:", width=width).strip().lower()

        if choice == "99":
            return False
        if choice == "1":
            username = input_box("Username:", width=width).strip()
            password = input_box("Password:", width=width).strip()
            try:
                ok, err = AppUserAuthInstance.login(username, password)
            except Exception as exc:
                print_card([f"Gagal login: {exc}"], "Error", width=width, color=R)
                pause()
                continue
            if not ok:
                print_card([err], "Gagal", width=width, color=R)
                pause()
                continue
            print_card(["Login berhasil."], "Sukses", width=width, color=G)
            pause()
            return True
        if choice == "2":
            name = input_box("Nama:", width=width).strip()
            phone = input_box("Nomor Telepon (628...):", width=width).strip()
            username = input_box("Username:", width=width).strip()
            password = input_box("Password:", width=width).strip()
            confirm = input_box("Konfirmasi Password:", width=width).strip()

            if not name:
                print_card(["Nama wajib diisi."], "Info", width=width, color=Y)
                pause()
                continue
            if not _validate_phone(phone):
                print_card(
                    ["Nomor tidak valid. Pastikan diawali '628' dan panjang benar."],
                    "Info",
                    width=width,
                    color=Y,
                )
                pause()
                continue
            if password != confirm:
                print_card(["Password tidak sama."], "Info", width=width, color=Y)
                pause()
                continue
            try:
                ok, err = AppUserAuthInstance.register(name, phone, username, password)
            except Exception as exc:
                print_card([f"Gagal registrasi: {exc}"], "Error", width=width, color=R)
                pause()
                continue
            if not ok:
                print_card([err], "Gagal", width=width, color=R)
                pause()
                continue
            print_card(["Registrasi berhasil."], "Sukses", width=width, color=G)
            pause()
            return True

        print_card(["Pilihan tidak valid."], "Error", width=width, color=R)
        pause()
