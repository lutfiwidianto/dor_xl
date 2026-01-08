import json
import os
import sys
import threading
import time

from app.client.store.search import get_family_list, get_store_packages
from app.client.engsel import get_family, get_package, send_api_request
from app.menus.util import clear_screen, pause
from app.menus.util_box import display_width, get_terminal_width, pad_right
from app.menus.package import show_package_details
from app.service.auth import AuthInstance

CACHE_PATH = "scanner_cache.json"
CACHE_VERSION = 1
OUTPUT_PATH = "scan_results.txt"


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


def _price_value(price: int) -> int:
    try:
        return int(price)
    except Exception:
        return 0


def _build_table_lines(rows: list[dict], *, with_index: bool = False) -> list[str]:
    width = get_terminal_width()
    avail = max(40, width)
    sep = " | "
    min_price = 10
    min_name = 18

    fc_vals = [str(r.get("family_code", "")) for r in rows]
    code_vals = [str(r.get("code", "")) for r in rows]

    col_idx = max(display_width("no"), 2) if with_index else 0
    col_fc = max([display_width("family_code")] + [display_width(v) for v in fc_vals])
    col_code = max([display_width("code")] + [display_width(v) for v in code_vals])
    content_w = avail - (len(sep) * (4 if with_index else 3))
    if with_index:
        content_w -= col_idx
    col_price = min_price
    col_name = content_w - (col_fc + col_code + col_price)

    if col_name < min_name:
        col_name = min_name

    header_parts = []
    if with_index:
        header_parts.append(pad_right("no", col_idx))
    header_parts.extend(
        [
            pad_right("family_code", col_fc),
            pad_right("code", col_code),
            pad_right("nama paket", col_name),
            pad_right("harga", col_price),
        ]
    )
    header = sep.join(header_parts)

    lines = [header, "-" * min(avail, display_width(header))]

    for idx, row in enumerate(rows, start=1):
        price = _format_price(row.get("price", ""))
        row_parts = []
        if with_index:
            row_parts.append(pad_right(str(idx), col_idx))
        row_parts.extend(
            [
                pad_right(_truncate_to_width(row.get("family_code", ""), col_fc), col_fc),
                pad_right(_truncate_to_width(row.get("code", ""), col_code), col_code),
                pad_right(_truncate_to_width(row.get("name", ""), col_name), col_name),
                pad_right(_truncate_to_width(price, col_price), col_price),
            ]
        )
        lines.append(sep.join(row_parts))

    return lines


def _write_output(rows: list[dict]) -> None:
    try:
        lines = _build_table_lines(rows)
        with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
            for line in lines:
                f.write(line + "\n")
    except Exception:
        pass


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
    for line in _build_table_lines(rows):
        print(line)


def _merge_provider_updates(
    cache_entries: dict,
    api_key: str,
    tokens: dict,
    subs_type: str,
    is_enterprise: bool,
) -> int:
    added = 0
    family_res = get_family_list(api_key, tokens, subs_type, is_enterprise)
    families = []
    if family_res:
        families = family_res.get("data", {}).get("results", [])

    for fam in families:
        family_code = fam.get("id", "")
        if not family_code:
            continue

        family_data = get_family(api_key, tokens, family_code, is_enterprise)
        if not family_data:
            continue

        family_name = family_data.get("package_family", {}).get("name", "")
        variants = family_data.get("package_variants", [])

        for variant in variants:
            variant_name = variant.get("name", "")
            for option in variant.get("package_options", []):
                option_code = option.get("package_option_code", "")
                if not option_code:
                    continue

                entry = _entry_from_option(family_code, family_name, variant_name, option)
                entry["source"] = "provider"

                cached = cache_entries.get(option_code)
                if not cached:
                    cache_entries[option_code] = entry
                    added += 1
                    continue

                if (
                    cached.get("price") != entry.get("price")
                    or cached.get("name") != entry.get("name")
                    or cached.get("family_code") != entry.get("family_code")
                ):
                    cache_entries[option_code] = entry
                    added += 1

    return added


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

    error_msg = None
    active_names = _get_active_package_names(api_key, tokens)

    cache = _load_cache()
    cache_entries = cache.get("entries", {})

    entries = {}
    done = 0
    total = 0

    try:
        store_res = get_store_packages(api_key, tokens, subs_type, is_enterprise)
    except Exception as e:
        store_res = None
        error_msg = str(e)
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
            try:
                detail = get_package(api_key, tokens, option_code)
            except Exception as e:
                error_msg = str(e)
                break
            if not detail:
                continue
            entry = _entry_from_detail(detail, option_code)
            cache_entries[option_code] = entry

        entry["source"] = "store"
        entries[option_code] = entry

    if not stop_flag.get("stop"):
        try:
            family_res = get_family_list(api_key, tokens, subs_type, is_enterprise)
        except Exception as e:
            family_res = None
            error_msg = str(e)
        families = []
        if family_res:
            families = family_res.get("data", {}).get("results", [])

        for fam in families:
            if stop_flag.get("stop"):
                break

            family_code = fam.get("id", "")
            if not family_code:
                continue

            try:
                family_data = get_family(api_key, tokens, family_code, is_enterprise)
            except Exception as e:
                error_msg = str(e)
                break
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
    elif error_msg:
        print(f"Scan terhenti karena error: {error_msg}")
        print("")

    if not rows:
        print("Tidak ada data ditemukan.")
        pause()
        return

    _print_table(rows)
    _write_output(rows)
    print(f"Hasil disimpan ke {OUTPUT_PATH}")
    pause()


def show_store_purchase_from_scan(subs_type: str = "PREPAID", is_enterprise: bool = False) -> None:
    api_key = AuthInstance.api_key
    tokens = AuthInstance.get_active_tokens()
    if not tokens:
        print("Token tidak ditemukan.")
        pause()
        return

    cache = _load_cache()
    cache_entries = cache.get("entries", {})

    try:
        added = _merge_provider_updates(cache_entries, api_key, tokens, subs_type, is_enterprise)
    except Exception as e:
        added = 0
        print(f"Gagal update dari provider: {e}")

    _save_cache(cache)

    rows = list(cache_entries.values())
    if not rows:
        print("Cache kosong. Jalankan scan terlebih dahulu.")
        pause()
        return

    rows.sort(key=lambda r: (_price_value(r.get("price", 0)), r.get("name", "")))

    clear_screen()
    width = get_terminal_width()
    print("=" * width)
    print("BELI PAKET STORE DARI HASIL SCAN".center(width))
    print("=" * width)
    if added > 0:
        print(f"Update provider: {added} item ditambahkan/diperbarui.")
    print("Pilih nomor paket untuk melihat detail & beli.")
    print("00 untuk kembali.")

    for line in _build_table_lines(rows, with_index=True):
        print(line)

    choice = input("Pilih nomor: ").strip()
    if choice == "00":
        return

    if not choice.isdigit():
        print("Input tidak valid.")
        pause()
        return

    idx = int(choice)
    if idx < 1 or idx > len(rows):
        print("Nomor paket tidak ditemukan.")
        pause()
        return

    selected = rows[idx - 1]
    option_code = selected.get("code", "")
    if not option_code:
        print("Option code tidak ditemukan.")
        pause()
        return

    show_package_details(api_key, tokens, option_code, is_enterprise)
