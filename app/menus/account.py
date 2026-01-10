from app.client.ciam import get_otp, submit_otp
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
from app.service.auth import AuthInstance


def show_login_menu():
    clear_screen()
    width = get_terminal_width()
    print_header("Login Akun XL (MyXL)", width)
    print_menu_box(
        "Menu",
        [
            "1. Request OTP",
            "2. Submit OTP",
            "99. Tutup aplikasi",
        ],
        width=width,
        color=C,
    )


def login_prompt(api_key: str):
    clear_screen()
    width = get_terminal_width()
    print_header("Login Akun XL (MyXL)", width)
    print_card(
        ["Masukkan nomor XL yang akan digunakan untuk transaksi."],
        "Nomor XL (MyXL)",
        width=width,
        color=C,
    )
    phone_number = input_box("Nomor:", width=width)

    if not phone_number.startswith("628") or len(phone_number) < 10 or len(phone_number) > 14:
        print_card(
            ["Nomor tidak valid. Pastikan diawali '628' dan panjang benar."],
            "Error",
            width=width,
            color=R,
        )
        return None

    try:
        subscriber_id = get_otp(phone_number)
        if not subscriber_id:
            return None
        print_card(["OTP XL berhasil dikirim ke nomor Anda."], "OTP XL Terkirim", width=width, color=G)

        try_count = 5
        while try_count > 0:
            print_card([f"Sisa percobaan: {try_count}"], "Verifikasi OTP", width=width, color=Y)
            otp = input_box("Masukkan OTP:", width=width)
            if not otp.isdigit() or len(otp) != 6:
                print_card(
                    ["OTP tidak valid. Pastikan 6 digit angka."],
                    "Periksa OTP",
                    width=width,
                    color=Y,
                )
                continue

            tokens = submit_otp(api_key, "SMS", phone_number, otp)
            if not tokens:
                print_card(["OTP salah. Silakan coba lagi."], "Gagal", width=width, color=R)
                try_count -= 1
                continue

            print_card(["Berhasil login!"], "Sukses", width=width, color=G)
            return phone_number, tokens["refresh_token"]

        print_card(
            ["Gagal login setelah beberapa percobaan.", "Silakan coba lagi nanti."],
            "Gagal",
            width=width,
            color=R,
        )
        return None, None
    except Exception as e:
        print_card([f"Gagal login: {e}"], "Error", width=width, color=R)
        return None, None


def show_account_menu():
    clear_screen()
    AuthInstance.load_tokens()
    users = AuthInstance.refresh_tokens
    active_user = AuthInstance.get_active_user()

    in_account_menu = True
    add_user = False
    while in_account_menu:
        clear_screen()
        width = get_terminal_width()
        print_header("Akun MyXL", width)
        if AuthInstance.get_active_user() is None or add_user:
            number, refresh_token = login_prompt(AuthInstance.api_key)
            if not refresh_token:
                print_card(["Gagal menambah akun. Silakan coba lagi."], "Gagal", width=width, color=R)
                pause()
                continue

            AuthInstance.add_refresh_token(int(number), refresh_token)
            AuthInstance.load_tokens()
            users = AuthInstance.refresh_tokens
            active_user = AuthInstance.get_active_user()

            if add_user:
                add_user = False
            continue

        lines = []
        if not users or len(users) == 0:
            lines.append("Tidak ada akun tersimpan.")
        else:
            for idx, user in enumerate(users):
                is_active = active_user and user["number"] == active_user["number"]
                active_marker = "ACTIVE" if is_active else ""

                number = str(user.get("number", "")).ljust(14)
                sub_type = user.get("subscription_type", "").center(12)
                lines.append(f"{idx + 1}. {number} [{sub_type}] {active_marker}")

        print_card(lines, "Akun Tersimpan", width=width, color=C)

        print_menu_box(
            "Command",
            [
                "0: Tambah Akun",
                "No: Ganti akun",
                "del <no>: Hapus akun",
                "00: Kembali ke menu utama",
            ],
            width=width,
            color=C,
        )

        input_str = input_box("Pilihan:", width=width)
        if input_str == "00":
            in_account_menu = False
            return active_user["number"] if active_user else None
        elif input_str == "0":
            add_user = True
            continue
        elif input_str.isdigit() and 1 <= int(input_str) <= len(users):
            selected_user = users[int(input_str) - 1]
            return selected_user["number"]
        elif input_str.startswith("del "):
            parts = input_str.split()
            if len(parts) == 2 and parts[1].isdigit():
                del_index = int(parts[1])

                if active_user and users[del_index - 1]["number"] == active_user["number"]:
                    print_card(
                        ["Tidak dapat menghapus akun aktif.", "Silakan ganti akun terlebih dahulu."],
                        "Peringatan",
                        width=width,
                        color=Y,
                    )
                    pause()
                    continue

                if 1 <= del_index <= len(users):
                    user_to_delete = users[del_index - 1]
                    confirm = input(
                        f"Yakin ingin menghapus akun {user_to_delete['number']}? (y/n): "
                    ).strip()
                    if confirm.lower() == "y":
                        AuthInstance.remove_refresh_token(user_to_delete["number"])
                        users = AuthInstance.refresh_tokens
                        active_user = AuthInstance.get_active_user()
                        print_card(["Akun berhasil dihapus."], "Sukses", width=width, color=G)
                        pause()
                    else:
                        print_card(["Penghapusan akun dibatalkan."], "Info", width=width, color=Y)
                        pause()
                else:
                    print_card(["Nomor urut tidak valid."], "Error", width=width, color=R)
                    pause()
            else:
                print_card(["Perintah tidak valid. Gunakan format: del <no>"], "Error", width=width, color=R)
                pause()
            continue
        else:
            print_card(["Input tidak valid. Silakan coba lagi."], "Error", width=width, color=R)
            pause()
            continue
