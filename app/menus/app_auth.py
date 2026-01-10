import sys

from app.menus.util import clear_screen, pause
from app.menus.util_box import get_terminal_width
from app.service.app_user_auth import AppUserAuthInstance
from app.service.telegram_otp import TelegramOTPInstance


def _validate_phone(phone: str) -> bool:
    return phone.startswith("628") and 10 <= len(phone) <= 14 and phone.isdigit()


def _title_case_name(name: str) -> str:
    parts = [p for p in name.strip().split() if p]
    return " ".join(p[:1].upper() + p[1:].lower() for p in parts)

def _print_ascii_header(title: str, *, width: int) -> None:
    inner = width - 2
    print(f"+{'-' * inner}+")
    print(f"|{title.center(inner)}|")
    print(f"+{'-' * inner}+")


def _print_ascii_menu(title: str, options: list[str], *, width: int) -> None:
    inner = width - 2
    print(f"+{'-' * inner}+")
    print(f"| {title.ljust(inner - 1)}|")
    print(f"+{'-' * inner}+")
    for opt in options:
        line = opt[: inner - 1]
        print(f"| {line.ljust(inner - 1)}|")
    print(f"+{'-' * inner}+")


def _print_ascii_card(title: str, lines: list[str], *, width: int) -> None:
    inner = width - 2
    print(f"+{'-' * inner}+")
    print(f"|{title.center(inner)}|")
    print(f"+{'-' * inner}+")
    for line in lines:
        safe = line[: inner - 1]
        print(f"| {safe.ljust(inner - 1)}|")
    print(f"+{'-' * inner}+")


def _input_full_box(prompt: str, *, width: int) -> str:
    inner = width - 2
    print(f"\n+{'-' * inner}+")
    value = input(f" > {prompt} ").strip()
    print(f"+{'-' * inner}+")
    return value

def show_app_auth_menu() -> bool:
    while True:
        clear_screen()
        width = get_terminal_width()
        _print_ascii_header("Login Aplikasi", width=width)
        _print_ascii_menu(
            "Menu",
            [
                "1. Login",
                "2. Register",
                "99. Tutup aplikasi",
            ],
            width=width,
        )
        choice = _input_full_box("Pilihan:", width=width).strip().lower()

        if choice == "99":
            return False
        if choice == "1":
            username = _input_full_box("Username Login Dor:", width=width).strip()
            password = _input_full_box("Password Login Dor:", width=width).strip()
            try:
                ok, err = AppUserAuthInstance.login(username, password)
            except Exception as exc:
                _print_ascii_card("Error", [f"Gagal login: {exc}"], width=width)
                pause()
                continue
            if not ok:
                _print_ascii_card("Gagal", [err], width=width)
                pause()
                continue
            _print_ascii_card("Sukses", ["Login berhasil."], width=width)
            pause()
            return True
        if choice == "2":
            bot_link = TelegramOTPInstance.bot_link()
            _print_ascii_card(
                "Info",
                [
                    "Sebelum register, buka bot Telegram:",
                    bot_link,
                    "Kirim /start, lalu kembali ke aplikasi.",
                ],
                width=width,
            )
            input("Tekan Enter untuk lanjut...")
            name = _input_full_box("Nama:", width=width).strip()
            phone = _input_full_box("Nomor WhatsApp (628...):", width=width).strip()
            tg_username = _input_full_box("Telegram Username (@username):", width=width).strip()

            if not name:
                _print_ascii_card("Info", ["Nama wajib diisi."], width=width)
                pause()
                continue
            if not _validate_phone(phone):
                _print_ascii_card(
                    "Info",
                    ["Nomor WhatsApp tidak valid. Pastikan diawali '628' dan panjang benar."],
                    width=width,
                )
                pause()
                continue
            if "t.me/" in tg_username:
                tg_username = tg_username.split("t.me/")[-1]
            tg_username = tg_username.strip().lstrip("@")
            if not tg_username:
                _print_ascii_card("Info", ["Telegram username wajib diisi."], width=width)
                pause()
                continue
            name = _title_case_name(name)

            send_attempts = 0
            otp_sent = False
            while send_attempts < 3:
                try:
                    TelegramOTPInstance.request_otp(tg_username)
                    otp_sent = True
                    break
                except Exception as exc:
                    msg = str(exc)
                    if "Chat ID tidak ditemukan" in msg:
                        _print_ascii_card(
                            "Info",
                            [
                                "Chat ID tidak ditemukan.",
                                "Buka Telegram dan chat bot berikut:",
                                bot_link,
                                "Kirim /start, lalu tekan Enter.",
                                "Data Anda tidak perlu diinput ulang.",
                            ],
                            width=width,
                        )
                        input("Tekan Enter untuk coba lagi...")
                        send_attempts += 1
                        continue
                    _print_ascii_card("Error", [f"Gagal kirim OTP Telegram: {msg}"], width=width)
                    retry = input("Tekan Enter untuk coba lagi, ketik 0 untuk batal: ").strip()
                    if retry == "0":
                        break
                    send_attempts += 1
            if not otp_sent:
                continue

            _print_ascii_card(
                "Info",
                ["OTP sudah dikirim ke Telegram.", "Silakan cek bot Anda."],
                width=width,
            )
            verified = False
            for _ in range(3):
                otp = _input_full_box("Masukkan OTP Telegram:", width=width).strip()
                if TelegramOTPInstance.verify_otp(tg_username, otp):
                    verified = True
                    break
                _print_ascii_card("Gagal", ["OTP Telegram salah/expired."], width=width)
            if not verified:
                retry = input("Ketik r untuk kirim ulang OTP, lainnya batal: ").strip().lower()
                if retry == "r":
                    continue
                continue

            while True:
                username = _input_full_box("Username Login Dor:", width=width).strip()
                password = _input_full_box("Password Login Dor:", width=width).strip()
                confirm = _input_full_box("Konfirmasi Password:", width=width).strip()
                if password != confirm:
                    _print_ascii_card("Info", ["Password tidak sama."], width=width)
                    continue
                try:
                    ok, err = AppUserAuthInstance.register(name, phone, username, password, tg_username)
                except Exception as exc:
                    _print_ascii_card("Error", [f"Gagal registrasi: {exc}"], width=width)
                    action = _input_full_box("Ketik X untuk keluar, Enter untuk coba lagi:", width=width)
                    if action.strip().lower() == "x":
                        sys.exit(0)
                    continue
                if not ok:
                    if "Username" in err:
                        _print_ascii_card("Gagal", [err, "Coba username lain."], width=width)
                        action = _input_full_box("Ketik X untuk keluar, Enter untuk coba lagi:", width=width)
                        if action.strip().lower() == "x":
                            sys.exit(0)
                        continue
                    _print_ascii_card("Gagal", [err], width=width)
                    action = _input_full_box("Ketik X untuk keluar, Enter untuk coba lagi:", width=width)
                    if action.strip().lower() == "x":
                        sys.exit(0)
                    continue
                _print_ascii_card("Sukses", ["Registrasi berhasil."], width=width)
                pause()
                return True
        _print_ascii_card("Error", ["Pilihan tidak valid."], width=width)
        pause()
