from datetime import datetime

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


def _format_status(status_raw: str) -> str:
    if status_raw in {"blocked", "inactive"}:
        return "nonaktif"
    if status_raw == "deleted":
        return "deleted"
    return "active"


def _filter_users(users: list[dict], term: str) -> list[dict]:
    if not term:
        return users
    t = term.lower()
    filtered = []
    for user in users:
        hay = " ".join(
            [
                str(user.get("username", "")),
                str(user.get("name", "")),
                str(user.get("whatsapp_number", "")),
                str(user.get("status", "")),
                str(user.get("role", "")),
            ]
        ).lower()
        if t in hay:
            filtered.append(user)
    return filtered


def _list_users(width: int, *, filter_text: str | None = None) -> list[dict]:
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
    users = _filter_users(users, filter_text or "")
    if not users:
        _print_ascii_card("Info", ["User tidak ditemukan."], width=width)
        pause()
        return []
    lines = []
    for idx, user in enumerate(users, start=1):
        username = str(user.get("username", ""))
        status = _format_status(str(user.get("status", "active")))
        role = str(user.get("role", "user"))
        lines.append(f"{idx}. {username} [{status}] ({role})")
    _print_ascii_card("Daftar User", lines, width=width)
    return users


def _pick_user(width: int, *, filter_text: str | None = None) -> dict | None:
    users = _list_users(width, filter_text=filter_text)
    if not users:
        return None
    sel = _input_full_box("Pilih nomor user:", width=width).strip()
    if not sel.isdigit() or not (1 <= int(sel) <= len(users)):
        _print_ascii_card("Error", ["Nomor tidak valid."], width=width)
        pause()
        return None
    return users[int(sel) - 1]


def _show_user_detail(width: int, uid: str) -> None:
    try:
        detail = AppUserAuthInstance.get_user_detail(uid)
    except Exception as exc:
        _print_ascii_card("Error", [f"Gagal ambil detail: {exc}"], width=width)
        pause()
        return
    if not detail:
        _print_ascii_card("Info", ["Detail user tidak ditemukan."], width=width)
        pause()
        return

    def _fmt_ts(ts: int | str | None) -> str:
        try:
            ts_i = int(ts or 0)
        except Exception:
            return "-"
        if ts_i <= 0:
            return "-"
        return datetime.fromtimestamp(ts_i).strftime("%Y-%m-%d %H:%M")

    lines = [
        f"Username: {detail.get('username', '')}",
        f"Nama: {detail.get('name', '')}",
        f"WhatsApp: {detail.get('whatsapp_number', '')}",
        f"Status: {_format_status(str(detail.get('status', 'active')))}",
        f"Role: {detail.get('role', 'user')}",
        f"Created: {_fmt_ts(detail.get('created_at'))}",
        f"Last login: {_fmt_ts(detail.get('last_login_at'))}",
    ]
    _print_ascii_card("Detail User", lines, width=width)


def _show_admin_logs(width: int) -> None:
    try:
        logs = AppUserAuthInstance.list_admin_logs(30)
    except Exception as exc:
        _print_ascii_card("Error", [f"Gagal ambil log: {exc}"], width=width)
        pause()
        return
    if not logs:
        _print_ascii_card("Info", ["Belum ada log."], width=width)
        pause()
        return

    lines = []
    for entry in logs:
        ts = entry.get("ts", 0)
        try:
            t = datetime.fromtimestamp(int(ts)).strftime("%Y-%m-%d %H:%M")
        except Exception:
            t = "-"
        action = entry.get("action", "")
        target = entry.get("target_username", "")
        lines.append(f"{t} - {action} - {target}")
    _print_ascii_card("Log Admin", lines, width=width)


def show_admin_menu():
    if not AppUserAuthInstance.is_admin():
        _print_ascii_card("Error", ["Akses ditolak. Admin saja."], width=get_terminal_width())
        pause()
        return
    width = get_terminal_width()
    while True:
        clear_screen()
        _print_ascii_header("ADMIN USER", width=width)
        _print_ascii_menu(
            "Menu",
            [
                "1. List User",
                "2. Cari User",
                "3. Detail User",
                "4. Nonaktifkan User",
                "5. Aktifkan User",
                "6. Ganti Role User",
                "7. Hapus User",
                "8. Lihat Log Admin",
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
        if choice == "2":
            term = _input_full_box("Cari (username/WA/status/role):", width=width).strip()
            _list_users(width, filter_text=term)
            pause()
            continue
        if choice == "3":
            user = _pick_user(width)
            if user:
                _show_user_detail(width, user.get("uid", ""))
                pause()
            continue
        if choice in {"4", "5", "6", "7"}:
            user = _pick_user(width)
            if not user:
                continue
            uid = user.get("uid", "")
            username = user.get("username", "")
            if choice == "4":
                AppUserAuthInstance.set_user_status(uid, "inactive")
                AppUserAuthInstance.log_admin_action("set_inactive", uid, username)
                _print_ascii_card("Sukses", [f"User {username} dinonaktifkan."], width=width)
                pause()
                continue
            if choice == "5":
                AppUserAuthInstance.set_user_status(uid, "active")
                AppUserAuthInstance.log_admin_action("set_active", uid, username)
                _print_ascii_card("Sukses", [f"User {username} diaktifkan."], width=width)
                pause()
                continue
            if choice == "6":
                role = _input_full_box("Role baru (admin/user):", width=width).strip().lower()
                if role not in {"admin", "user"}:
                    _print_ascii_card("Error", ["Role tidak valid."], width=width)
                    pause()
                    continue
                AppUserAuthInstance.set_user_role(uid, role)
                AppUserAuthInstance.log_admin_action("set_role", uid, username, {"role": role})
                _print_ascii_card("Sukses", [f"Role {username} -> {role}."], width=width)
                pause()
                continue
            if choice == "7":
                confirm = _input_full_box("Ketik HAPUS untuk lanjut:", width=width).strip()
                if confirm != "HAPUS":
                    _print_ascii_card("Info", ["Penghapusan dibatalkan."], width=width)
                    pause()
                    continue
                AppUserAuthInstance.set_user_status(uid, "deleted")
                AppUserAuthInstance.log_admin_action("set_deleted", uid, username)
                _print_ascii_card("Sukses", [f"User {username} dihapus."], width=width)
                pause()
                continue
        if choice == "8":
            _show_admin_logs(width)
            pause()
            continue

        _print_ascii_card("Error", ["Pilihan tidak valid."], width=width)
        pause()
