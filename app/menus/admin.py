from app.menus.util import clear_screen, pause
from app.menus.util_box import get_terminal_width
from app.service.app_user_auth import AppUserAuthInstance


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


def _list_users(width: int) -> list[dict]:
    try:
        users = AppUserAuthInstance.list_users()
    except Exception as exc:
        _print_ascii_card("Error", [f"Gagal mengambil user: {exc}"], width=width)
        pause()
        return []
    if not users:
        _print_ascii_card("Info", ["Tidak ada user."], width=width)
        pause()
        return []
    lines = []
    for idx, user in enumerate(users, start=1):
        username = str(user.get("username", ""))
        status = str(user.get("status", "active"))
        role = str(user.get("role", "user"))
        lines.append(f"{idx}. {username} [{status}] ({role})")
    _print_ascii_card("Daftar User", lines, width=width)
    return users


def show_admin_menu():
    width = get_terminal_width()
    while True:
        clear_screen()
        _print_ascii_header("ADMIN USER", width=width)
        _print_ascii_menu(
            "Menu",
            [
                "1. List User",
                "2. Blokir User",
                "3. Buka Blokir User",
                "4. Hapus User",
                "00. Kembali",
            ],
            width=width,
        )
        choice = _input_full_box("Pilihan:", width=width).strip().lower()
        if choice == "00":
            return
        if choice == "1":
            _list_users(width)
            pause()
            continue
        if choice in {"2", "3", "4"}:
            users = _list_users(width)
            if not users:
                continue
            sel = _input_full_box("Pilih nomor user:", width=width).strip()
            if not sel.isdigit() or not (1 <= int(sel) <= len(users)):
                _print_ascii_card("Error", ["Nomor tidak valid."], width=width)
                pause()
                continue
            user = users[int(sel) - 1]
            uid = user["uid"]
            username = user.get("username", "")
            if choice == "2":
                AppUserAuthInstance.set_user_status(uid, "blocked")
                _print_ascii_card("Sukses", [f"User {username} diblokir."], width=width)
                pause()
                continue
            if choice == "3":
                AppUserAuthInstance.set_user_status(uid, "active")
                _print_ascii_card("Sukses", [f"User {username} diaktifkan."], width=width)
                pause()
                continue
            if choice == "4":
                confirm = _input_full_box("Ketik HAPUS untuk lanjut:", width=width).strip()
                if confirm != "HAPUS":
                    _print_ascii_card("Info", ["Penghapusan dibatalkan."], width=width)
                    pause()
                    continue
                AppUserAuthInstance.set_user_status(uid, "deleted")
                _print_ascii_card("Sukses", [f"User {username} dihapus."], width=width)
                pause()
                continue

        _print_ascii_card("Error", ["Pilihan tidak valid."], width=width)
        pause()
