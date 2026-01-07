import os
import textwrap

from app.client.ciam import get_otp, submit_otp
from app.menus.util import clear_screen, pause
from app.service.auth import AuthInstance

def _term_width():
    try:
        columns, _ = os.get_terminal_size()
        return max(columns - 2, 48)
    except:
        return 55

def _print_header(title, width):
    print(f"┏{'━' * (width - 2)}┓")
    print(f"┃{title.center(width - 2)}┃")
    print(f"┗{'━' * (width - 2)}┛")

def _print_box(lines, title=None, width=None):
    if width is None:
        width = _term_width()

    print(f"┌{'─' * (width - 2)}┐")
    if title:
        print(f"│{title.center(width - 2)}│")
        print(f"├{'─' * (width - 2)}┤")

    for line in lines:
        wrapped = textwrap.wrap(str(line), width=width - 4) or [""]
        for piece in wrapped:
            print(f"│ {piece.ljust(width - 4)} │")

    print(f"└{'─' * (width - 2)}┘")

def _prompt_start(width):
    print(f"╭{'─' * (width // 3)}╮")

def _prompt_end(width):
    print(f"╰{'─' * (width // 3)}╯")

def show_login_menu():
    clear_screen()
    width = _term_width()
    _print_header("🔐 Login ke MyXL", width)
    _print_box(
        [
            "1. Request OTP",
            "2. Submit OTP",
            "99. Tutup aplikasi"
        ],
        "✨ Menu",
        width
    )
    
def login_prompt(api_key: str):
    clear_screen()
    width = _term_width()
    _print_header("🔐 Login ke MyXL", width)
    _print_box(
        ["Masukkan nomor XL (Contoh 6281234567890)"],
        "📱 Nomor XL",
        width
    )
    _prompt_start(width)
    phone_number = input(" › Nomor: ").strip()
    _prompt_end(width)

    if not phone_number.startswith("628") or len(phone_number) < 10 or len(phone_number) > 14:
        _print_box(
            ["Nomor tidak valid. Pastikan diawali '628' dan panjang benar."],
            "❌ Error",
            width
        )
        return None

    try:
        subscriber_id = get_otp(phone_number)
        if not subscriber_id:
            return None
        _print_box(["OTP berhasil dikirim ke nomor Anda."], "📨 OTP Terkirim", width)
        
        try_count = 5
        while try_count > 0:
            _print_box([f"Sisa percobaan: {try_count}"], "⏳ Verifikasi OTP", width)
            _prompt_start(width)
            otp = input(" › Masukkan OTP: ").strip()
            _prompt_end(width)
            if not otp.isdigit() or len(otp) != 6:
                _print_box(["OTP tidak valid. Pastikan 6 digit angka."], "⚠️ Periksa OTP", width)
                continue
            
            tokens = submit_otp(api_key, "SMS", phone_number, otp)
            if not tokens:
                _print_box(["OTP salah. Silakan coba lagi."], "❌ Gagal", width)
                try_count -= 1
                continue
            
            _print_box(["Berhasil login!"], "✅ Sukses", width)
            return phone_number, tokens["refresh_token"]

        _print_box(
            ["Gagal login setelah beberapa percobaan.", "Silakan coba lagi nanti."],
            "❌ Gagal",
            width
        )
        return None, None
    except Exception as e:
        _print_box([f"Gagal login: {e}"], "❌ Error", width)
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
        width = _term_width()
        _print_header("👤 Akun MyXL", width)
        if AuthInstance.get_active_user() is None or add_user:
            number, refresh_token = login_prompt(AuthInstance.api_key)
            if not refresh_token:
                _print_box(["Gagal menambah akun. Silakan coba lagi."], "❌ Gagal", width)
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
                active_marker = "✅" if is_active else ""
                
                number = str(user.get("number", "")).ljust(14)
                sub_type = user.get("subscription_type", "").center(12)
                lines.append(f"{idx + 1}. {number} [{sub_type}] {active_marker}")
        
        _print_box(lines, "📌 Akun Tersimpan", width)

        _print_box(
            [
                "0: Tambah Akun",
                "No: Ganti akun",
                "del <no>: Hapus akun",
                "00: Kembali ke menu utama"
            ],
            "🧭 Command",
            width
        )

        _prompt_start(width)
        input_str = input(" › Pilihan: ").strip()
        _prompt_end(width)
        if input_str == "00":
            in_account_menu = False
            return active_user["number"] if active_user else None
        elif input_str == "0":
            add_user = True
            continue
        elif input_str.isdigit() and 1 <= int(input_str) <= len(users):
            selected_user = users[int(input_str) - 1]
            return selected_user['number']
        elif input_str.startswith("del "):
            parts = input_str.split()
            if len(parts) == 2 and parts[1].isdigit():
                del_index = int(parts[1])
                
                # Prevent deleting the active user here
                if active_user and users[del_index - 1]["number"] == active_user["number"]:
                    _print_box(
                        ["Tidak dapat menghapus akun aktif.", "Silakan ganti akun terlebih dahulu."],
                        "⚠️ Peringatan",
                        width
                    )
                    pause()
                    continue
                
                if 1 <= del_index <= len(users):
                    user_to_delete = users[del_index - 1]
                    confirm = input(f"Yakin ingin menghapus akun {user_to_delete['number']}? (y/n): ").strip()
                    if confirm.lower() == 'y':
                        AuthInstance.remove_refresh_token(user_to_delete["number"])
                        # AuthInstance.load_tokens()
                        users = AuthInstance.refresh_tokens
                        active_user = AuthInstance.get_active_user()
                        _print_box(["Akun berhasil dihapus."], "✅ Sukses", width)
                        pause()
                    else:
                        _print_box(["Penghapusan akun dibatalkan."], "ℹ️ Info", width)
                        pause()
                else:
                    _print_box(["Nomor urut tidak valid."], "❌ Error", width)
                    pause()
            else:
                _print_box(["Perintah tidak valid. Gunakan format: del <no>"], "❌ Error", width)
                pause()
            continue
        else:
            _print_box(["Input tidak valid. Silakan coba lagi."], "❌ Error", width)
            pause()
            continue
