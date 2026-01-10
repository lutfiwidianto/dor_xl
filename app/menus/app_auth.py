from app.menus.util import clear_screen, pause
from app.menus.util_box import (
    print_header,
    print_card,
    print_menu_box,
    get_terminal_width,
    C,
    G,
    Y,
    R,
    W,
    B,
    RESET,
    TL,
    TR,
    BL,
    BR,
    H,
)
from app.service.app_user_auth import AppUserAuthInstance
from app.service.telegram_otp import TelegramOTPInstance


def _validate_phone(phone: str) -> bool:
    return phone.startswith("628") and 10 <= len(phone) <= 14 and phone.isdigit()


def _title_case_name(name: str) -> str:
    parts = [p for p in name.strip().split() if p]
    return " ".join(p[:1].upper() + p[1:].lower() for p in parts)


def _input_full_box(prompt: str, *, width: int) -> str:
    inner = width - 2
    print(f"\n{W}{TL}{H * inner}{TR}{RESET}")
    value = input(f" {B}{C}> {W}{prompt}{RESET} ").strip()
    print(f"{W}{BL}{H * inner}{BR}{RESET}")
    return value


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
        choice = _input_full_box("Pilihan:", width=width).strip().lower()

        if choice == "99":
            return False
        if choice == "1":
            username = _input_full_box("Username:", width=width).strip()
            password = _input_full_box("Password:", width=width).strip()
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
            name = _input_full_box("Nama:", width=width).strip()
            phone = _input_full_box("Nomor WhatsApp (628...):", width=width).strip()
            tg_username = _input_full_box(
                "Telegram Username (@contoh @username):",
                width=width,
            ).strip()
            username = _input_full_box("Username:", width=width).strip()
            password = _input_full_box("Password:", width=width).strip()
            confirm = _input_full_box("Konfirmasi Password:", width=width).strip()

            if not name:
                print_card(["Nama wajib diisi."], "Info", width=width, color=Y)
                pause()
                continue
            if not _validate_phone(phone):
                print_card(
                    ["Nomor WhatsApp tidak valid. Pastikan diawali '628' dan panjang benar."],
                    "Info",
                    width=width,
                    color=Y,
                )
                pause()
                continue
            if "t.me/" in tg_username:
                tg_username = tg_username.split("t.me/")[-1]
            tg_username = tg_username.strip().lstrip("@")
            if not tg_username:
                print_card(["Telegram username wajib diisi."], "Info", width=width, color=Y)
                pause()
                continue
            name = _title_case_name(name)
            if password != confirm:
                print_card(["Password tidak sama."], "Info", width=width, color=Y)
                pause()
                continue

            try:
                TelegramOTPInstance.request_otp(tg_username)
            except Exception as exc:
                print_card([f"Gagal kirim OTP Telegram: {exc}"], "Error", width=width, color=R)
                pause()
                continue
            otp = _input_full_box("Masukkan OTP Telegram:", width=width).strip()
            if not TelegramOTPInstance.verify_otp(tg_username, otp):
                print_card(["OTP Telegram salah/expired."], "Gagal", width=width, color=R)
                pause()
                continue
            try:
                ok, err = AppUserAuthInstance.register(name, phone, username, password, tg_username)
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
