import json
import os
import sys
import threading
import time

from app.client.store.search import get_family_list, get_store_packages
from app.client.engsel import get_family, get_package, send_api_request
from app.menus.util import clear_screen, pause
from app.menus.util_box import display_width, get_terminal_width, pad_right
from app.service.auth import AuthInstance

CACHE_PATH = "scanner_cache.json"
CACHE_VERSION = 1


def _normalize_name(name: str) -> str:
    return " ".join(str(name).split()).strip().lower()


def _truncate_to_width(text: str, maxw: int) -> str:
    s = str(text)
    if display_width(s) <= maxw:
        return s
    out = ""
    for ch in s:
        if display_width(out + ch + "...") > maxw:
            break
        out += ch
    return out + "..."


def _format_price(price: int) -> str:
    try:
        return f"Rp {int(price):,}".replace(",", ".")
    except Exception:
        return str(price)


def _get_active_package_names(api_key: str, tokens: dict) -> set[str]:
    path = "api/v8/packages/quota-details"
    payload = {"is_enterprise": False, "lang": "id", "family_member_id": ""}
    res = send_api_request(api_key, path, payload, tokens.get("id_token"), "POST")
    if not isinstance(res, dict) or res.get("status") != "SUCCESS":
        return set()
    quotas = res.get("data", {}).get("quotas", [])
    return {_normalize_name(q.get("name", "")) for q in quotas if q.get("name")}


def _load_cache() -> dict:
    if not os.path.exists(CACHE_PATH):
        return {"version": CACHE_VERSION, "entries": {}}

    try:
        with open(CACHE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict) or "entries" not in data:
            return {"version": CACHE_VERSION, "entries": {}}
        if not isinstance(data.get("entries"), dict):
            return {"version": CACHE_VERSION, "entries": {}}
        return data
    except Exception:
        return {"version": CACHE_VERSION, "entries": {}}


def _save_cache(cache: dict) -> None:
    try:
        cache["version"] = CACHE_VERSION
        cache["updated_at"] = int(time.time())
        with open(CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2, ensure_ascii=True)
    except Exception:
        pass


def _start_stop_listener(stop_flag: dict) -> None:
    def _listen() -> None:
        while not stop_flag.get("stop"):
            line = sys.stdin.readline()
            if not line:
                continue
            if line.strip().lower() in ("q", "quit", "00"):
                stop_flag["stop"] = True
                break

    t = threading.Thread(target=_listen, daemon=True)
    t.start()


def _progress(done: int, total: int) -> None:
    if total < 1:
        total = 1
    print(f"Progress: {done}/{total}", end="\r", flush=True)


def _entry_from_detail(detail: dict, option_code: str) -> dict:
    family_code = detail.get("package_family", {}).get("package_family_code", "")
    family_name = detail.get("package_family", {}).get("name", "")
    variant_name = detail.get("package_detail_variant", {}).get("name", "")
    option_name = detail.get("package_option", {}).get("name", "")
    price = detail.get("package_option", {}).get("price", 0)

    name_parts = [family_name, variant_name, option_name]
    name = " - ".join([p for p in name_parts if p]).strip()

    return {
        "family_code": family_code,
        "code": option_code,
        "name": name,
        "price": price,
    }


def _entry_from_option(family_code: str, family_name: str, variant_name: str, option: dict) -> dict:
    option_code = option.get("package_option_code", "")
    option_name = option.get("name", "")
    price = option.get("price", 0)

    name_parts = [family_name, variant_name, option_name]
    name = " - ".join([p for p in name_parts if p]).strip()

    return {
        "family_code": family_code,
        "code": option_code,
        "name": name,
        "price": price,
    }


def _print_table(rows: list[dict]) -> None:
    width = get_terminal_width()
    avail = max(40, width)
    sep = " | "
    min_fc = 10
    min_code = 12
    min_price = 10
    min_name = 18

    content_w = avail - (len(sep) * 3)
    col_fc = min_fc
    col_code = min_code
    col_price = min_price
    col_name = content_w - (col_fc + col_code + col_price)

    if col_name < min_name:
        shortage = min_name - col_name
        shrink_fc = min(col_fc - 6, shortage // 2) if col_fc > 6 else 0
        shrink_code = min(col_code - 8, shortage - shrink_fc) if col_code > 8 else 0
        col_fc -= shrink_fc
        col_code -= shrink_code
        col_name = content_w - (col_fc + col_code + col_price)
        if col_name < 8:
            col_name = 8

    header = (
        f"{pad_right('family_code', col_fc)}{sep}"
        f"{pad_right('code', col_code)}{sep}"
        f"{pad_right('nama paket', col_name)}{sep}"
        f"{pad_right('harga', col_price)}"
    )

    print(header)
    print("-" * min(avail, display_width(header)))

    for row in rows:
        price = _format_price(row.get("price", ""))
        line = (
            f"{pad_right(_truncate_to_width(row['family_code'], col_fc), col_fc)}{sep}"
            f"{pad_right(_truncate_to_width(row['code'], col_code), col_code)}{sep}"
            f"{pad_right(_truncate_to_width(row['name'], col_name), col_name)}{sep}"
            f"{pad_right(_truncate_to_width(price, col_price), col_price)}"
        )
        print(line)


def show_active_family_code_scanner(subs_type: str = "PREPAID", is_enterprise: bool = False) -> None:
    api_key = AuthInstance.api_key
    tokens = AuthInstance.get_active_tokens()
    if not tokens:
        print("Token tidak ditemukan.")
        pause()
        return

    clear_screen()
    width = get_terminal_width()
    print("=" * width)
    print("SCAN FAMILY CODE AKTIF (STORE + PROVIDER)".center(width))
    print("=" * width)
    print("Sedang memindai data, mohon tunggu...")
    print("Tekan 'q' + Enter untuk menghentikan scan dan tampilkan hasil sementara.")

    stop_flag = {"stop": False}
    _start_stop_listener(stop_flag)

    active_names = _get_active_package_names(api_key, tokens)

    cache = _load_cache()
    cache_entries = cache.get("entries", {})

    entries = {}
    done = 0
    total = 0

    store_res = get_store_packages(api_key, tokens, subs_type, is_enterprise)
    store_items = []
    if store_res:
        store_items = store_res.get("data", {}).get("results_price_only", [])

    total += len(store_items)

    for item in store_items:
        if stop_flag.get("stop"):
            break
        done += 1
        _progress(done, total)

        if item.get("action_type") != "PDP":
            continue
        option_code = item.get("action_param", "")
        if not option_code:
            continue
        if option_code in entries:
            continue

        cached = cache_entries.get(option_code)
        if cached:
            entry = cached.copy()
        else:
            detail = get_package(api_key, tokens, option_code)
            if not detail:
                continue
            entry = _entry_from_detail(detail, option_code)
            cache_entries[option_code] = entry

        entry["source"] = "store"
        entries[option_code] = entry

    if not stop_flag.get("stop"):
        family_res = get_family_list(api_key, tokens, subs_type, is_enterprise)
        families = []
        if family_res:
            families = family_res.get("data", {}).get("results", [])

        for fam in families:
            if stop_flag.get("stop"):
                break

            family_code = fam.get("id", "")
            if not family_code:
                continue

            family_data = get_family(api_key, tokens, family_code, is_enterprise)
            if not family_data:
                continue

            family_name = family_data.get("package_family", {}).get("name", "")
            variants = family_data.get("package_variants", [])

            options_count = sum(len(v.get("package_options", [])) for v in variants)
            total += options_count

            for variant in variants:
                if stop_flag.get("stop"):
                    break

                variant_name = variant.get("name", "")
                for option in variant.get("package_options", []):
                    if stop_flag.get("stop"):
                        break

                    done += 1
                    _progress(done, total)

                    option_code = option.get("package_option_code", "")
                    if not option_code:
                        continue

                    entry = _entry_from_option(family_code, family_name, variant_name, option)
                    entry["source"] = "provider"

                    entries[option_code] = entry
                    cache_entries[option_code] = entry

    print("")
    _save_cache(cache)

    rows = list(entries.values())

    if active_names:
        rows = [r for r in rows if _normalize_name(r.get("name", "")) not in active_names]

    rows.sort(
        key=lambda r: (
            0 if r.get("source") == "provider" else 1,
            r.get("family_code", ""),
            r.get("name", ""),
        )
    )

    clear_screen()
    print("=" * width)
    print("HASIL SCAN FAMILY CODE".center(width))
    print("=" * width)

    if stop_flag.get("stop"):
        print("Scan dihentikan. Menampilkan hasil sementara.")
        print("")

    if not rows:
        print("Tidak ada data ditemukan.")
        pause()
        return

    _print_table(rows)
    pause()
