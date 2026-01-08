from app.client.store.search import get_family_list, get_store_packages
from app.client.engsel import get_family, get_package, send_api_request
from app.menus.util import clear_screen, pause
from app.menus.util_box import display_width, get_terminal_width, pad_right
from app.service.auth import AuthInstance


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


def _collect_from_store(api_key: str, tokens: dict, subs_type: str, is_enterprise: bool) -> list[dict]:
    store_res = get_store_packages(api_key, tokens, subs_type, is_enterprise)
    if not store_res:
        return []

    results = store_res.get("data", {}).get("results_price_only", [])
    entries = []
    for item in results:
        if item.get("action_type") != "PDP":
            continue
        option_code = item.get("action_param", "")
        if not option_code:
            continue
        detail = get_package(api_key, tokens, option_code)
        if not detail:
            continue

        family_code = detail.get("package_family", {}).get("package_family_code", "")
        family_name = detail.get("package_family", {}).get("name", "")
        variant_name = detail.get("package_detail_variant", {}).get("name", "")
        option_name = detail.get("package_option", {}).get("name", "")
        price = detail.get("package_option", {}).get("price", 0)

        name_parts = [family_name, variant_name, option_name]
        name = " - ".join([p for p in name_parts if p]).strip()

        entries.append(
            {
                "family_code": family_code,
                "code": option_code,
                "name": name,
                "price": price,
            }
        )

    return entries


def _collect_from_family_list(api_key: str, tokens: dict, subs_type: str, is_enterprise: bool) -> list[dict]:
    family_res = get_family_list(api_key, tokens, subs_type, is_enterprise)
    if not family_res:
        return []

    families = family_res.get("data", {}).get("results", [])
    entries = []
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
                option_name = option.get("name", "")
                price = option.get("price", 0)

                name_parts = [family_name, variant_name, option_name]
                name = " - ".join([p for p in name_parts if p]).strip()

                entries.append(
                    {
                        "family_code": family_code,
                        "code": option_code,
                        "name": name,
                        "price": price,
                    }
                )

    return entries


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

    active_names = _get_active_package_names(api_key, tokens)

    entries = []
    entries.extend(_collect_from_store(api_key, tokens, subs_type, is_enterprise))
    entries.extend(_collect_from_family_list(api_key, tokens, subs_type, is_enterprise))

    # Deduplicate by option code
    dedup = {}
    for e in entries:
        code = e.get("code", "")
        if not code:
            continue
        dedup[code] = e

    rows = list(dedup.values())

    # Best-effort filter: remove packages whose name matches active package names
    if active_names:
        rows = [r for r in rows if _normalize_name(r.get("name", "")) not in active_names]

    rows.sort(key=lambda r: (r.get("family_code", ""), r.get("name", "")))

    clear_screen()
    print("=" * width)
    print("HASIL SCAN FAMILY CODE".center(width))
    print("=" * width)

    if not rows:
        print("Tidak ada data ditemukan.")
        pause()
        return

    _print_table(rows)
    pause()
