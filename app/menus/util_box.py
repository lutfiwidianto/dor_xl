# app/menus/util_box.py
# Terminal UI helpers: border rapi (box drawing), card, menu box, paging, dll.

from __future__ import annotations

import os
import re
import sys
import textwrap
import unicodedata
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple, Union

# =========================
# ANSI Colors (opsional)
# =========================
C = "\033[36m"  # Cyan
G = "\033[32m"  # Green
Y = "\033[33m"  # Yellow
R = "\033[31m"  # Red
M = "\033[35m"  # Magenta
W = "\033[97m"  # White
B = "\033[1m"   # Bold
D = "\033[90m"  # Dark Gray
RESET = "\033[0m"

# Pastikan output UTF-8 (Windows friendly)
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# =========================
# Box Drawing Characters
# =========================
TL, TR = "┌", "┐"
BL, BR = "└", "┘"
H, V = "─", "│"
LM, RM = "├", "┤"

ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


# =========================
# Utils: width-aware padding
# =========================
def strip_ansi(s: str) -> str:
    return ANSI_RE.sub("", str(s))


def display_width(text: Any) -> int:
    """
    Hitung lebar tampilan string (mengabaikan ANSI dan memperhitungkan wide char).
    """
    stripped = strip_ansi(str(text))
    width = 0
    for ch in stripped:
        width += 2 if unicodedata.east_asian_width(ch) in ("F", "W") else 1
    return width


def pad_right(text: Any, width: int) -> str:
    s = str(text)
    return f"{s}{' ' * max(0, width - display_width(s))}"


def get_terminal_width(min_width: int = 40, fallback: int = 50, padding: int = 2) -> int:
    """
    Ambil lebar terminal. Default dikurangi padding supaya tidak wrap di pinggir.
    """
    try:
        columns, _ = os.get_terminal_size()
        w = max(columns - padding, min_width)
        return w
    except Exception:
        return max(fallback, min_width)


# =========================
# Text wrapping helpers
# =========================

def wrap_lines(
    text: Any,
    width: int,
    *,
    indent_first: str = "",
    indent_next: str = "",
    drop_empty: bool = False,
) -> List[str]:
    """
    Wrap teks berdasarkan DISPLAY WIDTH (bukan len()),
    aman untuk ANSI color codes, dan lebih rapih di Termux.
    """
    s = str(text)
    if drop_empty and not s.strip():
        return []

    # Tokenize: ANSI escapes atau karakter biasa
    tokens = re.findall(r"\x1b\[[0-9;]*m|.", s)

    def _ch_w(ch: str) -> int:
        # ANSI tidak punya lebar tampilan
        if ANSI_RE.fullmatch(ch):
            return 0
        # Lebar 2 untuk wide char (termasuk banyak emoji)
        return 2 if unicodedata.east_asian_width(ch) in ("F", "W") else 1

    lines: List[str] = []
    cur: List[str] = []
    cur_w = 0

    def flush():
        nonlocal cur, cur_w
        out = "".join(cur).rstrip()
        lines.append(out)
        cur = []
        cur_w = 0

    # helper: add string (indent) tanpa menghitung ANSI
    def add_str(raw: str):
        nonlocal cur, cur_w
        for t in re.findall(r"\x1b\[[0-9;]*m|.", raw):
            cur.append(t)
            cur_w += _ch_w(t)

    # indent awal
    if indent_first:
        add_str(indent_first)

    i = 0
    while i < len(tokens):
        t = tokens[i]
        w = _ch_w(t)

        # kalau char normal dan akan overflow, pindah baris
        if w > 0 and cur_w + w > width:
            flush()
            if indent_next:
                add_str(indent_next)

            # skip spasi awal baris
            if not ANSI_RE.fullmatch(t) and t == " ":
                i += 1
                continue

        cur.append(t)
        cur_w += w
        i += 1

    # flush terakhir
    if cur:
        flush()

    # Kalau hasil wrap kosong
    if not lines:
        return [""]

    return lines


def kv_lines(
    kv: Dict[Any, Any],
    width: int,
    *,
    sep: str = ": ",
) -> List[str]:
    """
    Ubah dict key->value menjadi baris-baris yang wrap.
    """
    lines: List[str] = []
    for k, v in kv.items():
        base = f"{k}{sep}{v}"
        lines.extend(wrap_lines(base, width))
    return lines


# =========================
# Core UI: header & card
# =========================
def print_header(title: str, width: Optional[int] = None, color: str = C) -> None:
    """
    Header 3 baris, border rapi.
    """
    if width is None:
        width = get_terminal_width()
    inner = width - 2
    print(f"{color}{TL}{H * inner}{TR}{RESET}")
    print(f"{color}{V}{RESET}{W}{B}{pad_right(title.center(inner), inner)}{RESET}{color}{V}{RESET}")
    print(f"{color}{BL}{H * inner}{BR}{RESET}")


def print_card(
    content: Union[str, Sequence[Any]],
    title: Optional[str] = None,
    *,
    width: Optional[int] = None,
    color: str = G,
) -> None:
    """
    Card box rapi:
    - content bisa string
    - atau list berisi string / dict
    """
    if width is None:
        width = get_terminal_width()

    inner = width - 2
    content_width = width - 4

    if title:
        print(f"\n{color}{TL}{H * inner}{TR}{RESET}")
        print(f"{color}{V}{RESET}{W}{B}{pad_right(title.center(inner), inner)}{RESET}{color}{V}{RESET}")
        print(f"{color}{LM}{H * inner}{RM}{RESET}")
    else:
        print(f"\n{color}{TL}{H * inner}{TR}{RESET}")

    def _print_body_line(line: Any) -> None:
        for piece in wrap_lines(line, content_width):
            print(f"{color}{V}{RESET} {pad_right(piece, content_width)} {color}{V}{RESET}")

    if isinstance(content, (list, tuple)):
        for item in content:
            if isinstance(item, dict):
                for line in kv_lines(item, content_width):
                    _print_body_line(line)
            else:
                _print_body_line(item)
    else:
        _print_body_line(content)

    print(f"{color}{BL}{H * inner}{BR}{RESET}")


# =========================
# Menu Box helpers
# =========================
def print_menu_box(
    title: str,
    options: Sequence[str],
    *,
    width: Optional[int] = None,
    color: str = C,
) -> None:
    """
    Cetak kotak menu sederhana dengan daftar opsi.
    options: list string (sudah berformat/berwarna juga boleh).
    """
    if width is None:
        width = get_terminal_width()

    inner = width - 2
    content_width = width - 4

    print(f"\n{color}{TL}{H * inner}{TR}{RESET}")
    print(f"{color}{V}{RESET} {pad_right(f'{W}{B}{title}{RESET}', content_width)} {color}{V}{RESET}")
    print(f"{color}{LM}{H * inner}{RM}{RESET}")

    for opt in options:
        for piece in wrap_lines(opt, content_width):
            print(f"{color}{V}{RESET} {pad_right(piece, content_width)} {color}{V}{RESET}")

    print(f"{color}{BL}{H * inner}{BR}{RESET}")


def input_box(prompt: str, *, width: Optional[int] = None) -> str:
    """
    Input dengan kotak kecil (opsional).
    """
    if width is None:
        width = get_terminal_width()
    w = max(16, min(width // 3, 30))
    print(f"\n{W}{TL}{H * (w - 2)}{TR}{RESET}")
    value = input(f" {B}{C}›{W} {prompt}{RESET}").strip()
    print(f"{W}{BL}{H * (w - 2)}{BR}{RESET}")
    return value


# =========================
# Paging for long output
# =========================
def print_paged(
    lines: Sequence[Any],
    title: str,
    *,
    width: Optional[int] = None,
    color: str = M,
    page_size: int = 12,
    pause_text: str = "Tekan Enter untuk lanjut...",
) -> None:
    """
    Cetak list baris panjang per halaman (paging).
    lines: list string (atau objek yang bisa str()).
    """
    if width is None:
        width = get_terminal_width()

    total = len(lines)
    if total == 0:
        return

    start = 0
    page = 1
    while start < total:
        end = min(start + page_size, total)
        chunk = [str(x) for x in lines[start:end]]
        print_card(chunk, f"{title} (Hal {page})", width=width, color=color)

        start = end
        page += 1

        if start < total:
            input(f"{W}{pause_text}{RESET}")


# =========================
# Convenience T&C wrapper
# =========================
def wrap_bullets(
    text: str,
    width: int,
    *,
    bullet: str = "• ",
    bullet_color: str = D,
) -> List[str]:
    """
    Wrap teks menjadi bullet list (tiap paragraf jadi bullet).
    Cocok untuk Syarat & Ketentuan hasil HTML->text.
    """
    content_width = max(20, width - 6)
    out: List[str] = []
    for raw in str(text).splitlines():
        t = raw.strip()
        if not t:
            continue
        wrapped = textwrap.wrap(t, width=content_width - 2) or [""]
        for i, piece in enumerate(wrapped):
            prefix = bullet if i == 0 else "  "
            out.append(f"{bullet_color}{prefix}{piece}{RESET}")
    return out
