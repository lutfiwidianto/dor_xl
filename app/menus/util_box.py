# app/menus/util_box.py
# Terminal UI helpers: border rapi (box drawing), card, menu box, paging, dll.

from __future__ import annotations

import os
import re
import sys
import textwrap
import unicodedata
from typing import Any, Dict, List, Optional, Sequence, Union

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

# coba pakai wcwidth kalau ada (paling akurat di terminal)
try:
    from wcwidth import wcwidth as _wcwidth, wcswidth as _wcswidth  # type: ignore
except Exception:
    _wcwidth = None
    _wcswidth = None


# =========================
# Utils: strip ANSI
# =========================
def strip_ansi(s: str) -> str:
    return ANSI_RE.sub("", str(s))


# =========================
# Width calculation (FIX emoji width)
# =========================
def _char_width_fallback(ch: str) -> int:
    if not ch:
        return 0

    code = ord(ch)

    # Control chars
    if code < 32 or code == 127:
        return 0

    # Variation Selectors (emoji variation) -> 0
    if 0xFE00 <= code <= 0xFE0F:
        return 0

    # Zero Width Joiner -> 0
    if code == 0x200D:
        return 0

    # ✅ Zero Width Space / Word Joiner -> 0  (INI YANG KURANG)
    if code in (0x200B, 0x2060):
        return 0

    # Combining marks -> 0
    if unicodedata.combining(ch):
        return 0

    # Banyak emoji/simbol ada di kategori "So" dan tampil 2 kolom di terminal
    cat = unicodedata.category(ch)
    if cat == "So":
        return 2

    # East Asian wide/fullwidth -> 2
    eaw = unicodedata.east_asian_width(ch)
    if eaw in ("F", "W"):
        return 2

    # Heuristik blok emoji umum
    if (
        0x1F300 <= code <= 0x1FAFF
        or 0x2600 <= code <= 0x27BF
        or 0x2300 <= code <= 0x23FF
    ):
        return 2

    return 1


def char_width(ch: str) -> int:
    if _wcwidth is not None:
        w = _wcwidth(ch)
        return 0 if w < 0 else w
    return _char_width_fallback(ch)


def display_width(text: Any) -> int:
    """
    Hitung lebar tampilan string:
    - mengabaikan ANSI
    - pakai wcwidth bila tersedia (akurasi terbaik utk emoji/box drawing)
    """
    s = strip_ansi(str(text))

    if _wcswidth is not None:
        w = _wcswidth(s)
        return 0 if w < 0 else w

    width = 0
    for ch in s:
        width += char_width(ch)
    return width


def pad_right(text: Any, width: int) -> str:
    s = str(text)
    pad = max(0, width - display_width(s))
    return f"{s}{' ' * pad}"


def center_display(text: Any, width: int) -> str:
    """
    Center string berdasarkan lebar tampilan terminal (bukan len()).
    Ini yang bikin header emoji tetap lurus.
    """
    s = str(text)
    w = display_width(s)
    if w >= width:
        return s
    pad_total = width - w
    left = pad_total // 2
    right = pad_total - left
    return (" " * left) + s + (" " * right)


def get_terminal_width(min_width: int = 40, fallback: int = 50, padding: int = 2) -> int:
    """
    Ambil lebar terminal. Default dikurangi padding supaya tidak wrap di pinggir.
    """
    try:
        columns, _ = os.get_terminal_size()
        return max(columns - padding, min_width)
    except Exception:
        return max(fallback, min_width)


# =========================
# Wrapping helpers (width-aware)
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
    aman untuk ANSI color codes.
    """
    s = str(text)
    if drop_empty and not s.strip():
        return []

    tokens = re.findall(r"\x1b\[[0-9;]*m|.", s)

    def _tok_w(tok: str) -> int:
        if ANSI_RE.fullmatch(tok):
            return 0
        return char_width(tok)

    lines: List[str] = []
    cur: List[str] = []
    cur_w = 0

    def flush() -> None:
        nonlocal cur, cur_w
        lines.append("".join(cur).rstrip())
        cur = []
        cur_w = 0

    def add_str(raw: str) -> None:
        nonlocal cur, cur_w
        for t in re.findall(r"\x1b\[[0-9;]*m|.", raw):
            cur.append(t)
            cur_w += _tok_w(t)

    if indent_first:
        add_str(indent_first)

    i = 0
    while i < len(tokens):
        t = tokens[i]
        w = _tok_w(t)

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

    if cur:
        flush()

    return lines if lines else [""]


def kv_lines(kv: Dict[Any, Any], width: int, *, sep: str = ": ") -> List[str]:
    out: List[str] = []
    for k, v in kv.items():
        out.extend(wrap_lines(f"{k}{sep}{v}", width))
    return out


# =========================
# Core UI: header & card
# =========================
def print_header(title: str, width: Optional[int] = None, color: str = C) -> None:
    if width is None:
        width = get_terminal_width()
    inner = width - 2
    print(f"{color}{TL}{H * inner}{TR}{RESET}")
    print(f"{color}{V}{RESET}{W}{B}{center_display(title, inner)}{RESET}{color}{V}{RESET}")
    print(f"{color}{BL}{H * inner}{BR}{RESET}")


def print_card(
    content: Union[str, Sequence[Any]],
    title: Optional[str] = None,
    *,
    width: Optional[int] = None,
    color: str = G,
) -> None:
    if width is None:
        width = get_terminal_width()

    inner = width - 2
    content_width = width - 4

    if title:
        print(f"\n{color}{TL}{H * inner}{TR}{RESET}")
        print(f"{color}{V}{RESET}{W}{B}{center_display(title, inner)}{RESET}{color}{V}{RESET}")
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