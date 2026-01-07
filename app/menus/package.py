# app/menus/package.py

import textwrap
import requests

from app.service.auth import AuthInstance
from app.client.engsel import (
    get_family,
    get_package,
    get_addons,
    get_package_details,
    send_api_request,
    unsubscribe,
)
from app.client.ciam import get_auth_code
from app.service.bookmark import BookmarkInstance
from app.client.purchase.redeem import settlement_bounty, settlement_loyalty, bounty_allotment
from app.menus.util import clear_screen, pause, display_html, format_quota_byte
from app.client.purchase.qris import show_qris_payment
from app.client.purchase.ewallet import show_multipayment
from app.client.purchase.balance import settlement_balance
from app.type_dict import PaymentItem
from app.menus.purchase import purchase_n_times, purchase_n_times_by_option_code
from app.service.decoy import DecoyInstance

# ✅ Pakai util_box (semua UI dipusatkan)
from app.menus.util_box import (
    print_header,
    print_card,
    print_menu_box,
    print_paged,
    wrap_bullets,
    input_box,
    get_terminal_width,
    pad_right, print_paged, wrap_bullets, display_width,
    # warna & karakter border jika masih mau dipakai manual
    C, G, Y, R, M, W, B, D, RESET,
    TL, TR, BL, BR, H, V, LM, RM,
)

__all__ = ["show_package_details", "get_packages_by_family", "fetch_my_packages"]


def format_price(price):
    return f"Rp {price:,}"


def format_duration(validity):
    if not validity:
        return "-"
    v = str(validity)
    if "day" in v.lower() or "hour" in v.lower():
        return v
    return f"{v} hari"


def show_package_details(api_key, tokens, package_option_code, is_enterprise, option_order=-1):
    """Show package details in card layout"""
    active_user = AuthInstance.active_user
    width = get_terminal_width()

    clear_screen()
    print_header("📋 DETAIL PAKET", width)

    package = get_package(api_key, tokens, package_option_code)
    if not package:
        print_card(f"{R}Gagal memuat detail paket.{RESET}", "❌ Error", width=width, color=R)
        pause()
        return False

    price = package["package_option"]["price"]
    tnc_html = package["package_option"]["tnc"]
    detail = display_html(tnc_html)
    validity = package["package_option"]["validity"]
    point = package["package_option"]["point"]

    option_name = package.get("package_option", {}).get("name", "")
    family_name = package.get("package_family", {}).get("name", "")
    variant_name = package.get("package_detail_variant", {}).get("name", "")

    title_parts = [family_name, variant_name, option_name]
    title_parts = [p for p in title_parts if p]
    title = " - ".join(title_parts).strip()

    family_code = package.get("package_family", {}).get("package_family_code", "")
    parent_code = package.get("package_addon", {}).get("parent_code", "N/A")
    plan_type = package["package_family"]["plan_type"]
    payment_for = package["package_family"]["payment_for"] or "BUY_PACKAGE"

    token_confirmation = package["token_confirmation"]
    ts_to_sign = package["timestamp"]

    payment_items = [
        PaymentItem(
            item_code=package_option_code,
            product_type="",
            item_price=price,
            item_name=f"{variant_name} {option_name}".strip(),
            tax=0,
            token_confirmation=token_confirmation,
        )
    ]

    overview_content = [
        {f"{W}Nama Paket{RESET}": f"{B}{Y}{title}{RESET}"},
        {f"{W}Harga{RESET}": f"{B}{G}{format_price(price)}{RESET}"},
        {f"{W}Tipe Pembayaran{RESET}": f"{C}{payment_for}{RESET}"},
        {f"{W}Masa Aktif{RESET}": f"{M}{format_duration(validity)}{RESET}"},
        {f"{W}Poin{RESET}": f"{Y}{point} poin{RESET}"},
        {f"{W}Tipe Plan{RESET}": f"{G}{plan_type}{RESET}"},
        {f"{W}Family Code{RESET}": f"{D}{family_code}{RESET}"},
        {f"{W}Parent Code{RESET}": f"{D}{parent_code}{RESET}"},
    ]
    print_card(overview_content, "📊 OVERVIEW PAKET", width=width, color=C)

    # Benefits
    benefits = package["package_option"].get("benefits", [])
    if benefits and isinstance(benefits, list):
        benefits_content = []
        for benefit in benefits:
            benefit_name = benefit.get("name", "")
            data_type = benefit.get("data_type", "")
            total = benefit.get("total", 0)
            remaining = benefit.get("remaining", total)

            if data_type == "VOICE" and total > 0:
                display = f"{remaining/60:.0f}/{total/60:.0f} menit"
                icon = "📞"
            elif data_type == "TEXT" and total > 0:
                display = f"{remaining}/{total} SMS"
                icon = "💬"
            elif data_type == "DATA" and total > 0:
                if total >= 1_000_000_000:
                    display = f"{remaining/1_000_000_000:.2f}/{total/1_000_000_000:.2f} GB"
                elif total >= 1_000_000:
                    display = f"{remaining/1_000_000:.2f}/{total/1_000_000:.2f} MB"
                elif total >= 1_000:
                    display = f"{remaining/1_000:.2f}/{total/1_000:.2f} KB"
                else:
                    display = f"{remaining}/{total} B"
                icon = "📊"
            else:
                display = f"{remaining}/{total} ({data_type})"
                icon = "📦"

            unlimited_mark = f" {Y}♾️{RESET}" if benefit.get("is_unlimited") else ""
            benefits_content.append({f"{icon} {W}{benefit_name}{RESET}": f"{G}{display}{unlimited_mark}{RESET}"})

        print_card(benefits_content, "🎁 BENEFITS & KUOTA", width=width, color=G)

    # Addons
    addons = get_addons(api_key, tokens, package_option_code)
    if addons and addons.get("bonuses"):
        bonuses = addons["bonuses"]
        addons_content = []
        for i, bonus in enumerate(bonuses[:3], 1):
            addons_content.append({
                f"{W}{i}. {bonus.get('name', 'Bonus')}{RESET}": f"{Y}{bonus.get('package_option_code', '')}{RESET}"
            })
        if len(bonuses) > 3:
            addons_content.append({f"{D}... dan {len(bonuses) - 3} bonus lainnya{RESET}": ""})

        print_card(addons_content, "🎉 BONUS TERSEDIA", width=width, color=Y)

    # ✅ Syarat & Ketentuan FULL (pakai util_box)
    if detail and str(detail).strip():
        tnc_lines = wrap_bullets(detail, width)
        print_paged(tnc_lines, "📜 SYARAT & KETENTUAN", width=width, color=M, page_size=12)

    # Menu
    while True:
        options_grid = [
            f"{C}[{W}1{C}] {W}Pulsa{RESET}",
            f"{C}[{W}2{C}] {W}E-Wallet{RESET}",
            f"{C}[{W}3{C}] {W}QRIS{RESET}",
            f"{C}[{W}4{C}] {W}Pulsa + Decoy{RESET}",
            f"{C}[{W}5{C}] {W}Decoy V2{RESET}",
            f"{C}[{W}6{C}] {W}QRIS + Decoy{RESET}",
            f"{C}[{W}7{C}] {W}QRIS Decoy V2{RESET}",
            f"{C}[{W}8{C}] {W}Beli N kali{RESET}",
        ]

        if payment_for == "REDEEM_VOUCHER":
            options_grid.append(
                f"{C}[{W}B{C}] {W}Ambil Bonus{RESET} | {C}[{W}BA{C}] {W}Kirim Bonus{RESET} | {C}[{W}L{C}] {W}Tukar Poin{RESET}"
            )

        if option_order != -1:
            options_grid.append(f"{C}[{W}0{C}] {W}Tambah ke Bookmark{RESET}")

        options_grid.append(f"{C}[{R}00{C}] {W}Kembali{RESET}")

        print_menu_box("🚀 PILIHAN PEMBELIAN", options_grid, width=width, color=C)

        choice = input_box("Pilihan:", width=width).lower()

        if choice == "00":
            return False

        elif choice == "0" and option_order != -1:
            success = BookmarkInstance.add_bookmark(
                family_code=family_code,
                family_name=family_name,
                is_enterprise=is_enterprise,
                variant_name=variant_name,
                option_name=option_name,
                order=option_order,
            )
            if success:
                print_card(f"{G}✓ Paket berhasil ditambahkan ke bookmark{RESET}", "✅ BERHASIL", width=width // 2, color=G)
            else:
                print_card(f"{Y}⚠ Paket sudah ada di bookmark{RESET}", "ℹ INFO", width=width // 2, color=Y)
            pause()
            continue

        elif choice == "1":
            result = settlement_balance(api_key, tokens, payment_items, payment_for, True)
            if result and result.get("status") == "SUCCESS":
                print_card(f"{G}✓ Pembelian berhasil!{RESET}", "✅ BERHASIL", width=width, color=G)
            else:
                error_msg = result.get("message", "Unknown error") if result else "Gagal memproses"
                print_card(f"{R}✗ {error_msg}{RESET}", "❌ GAGAL", width=width, color=R)
            input(f"\n{W}Tekan Enter untuk kembali...{RESET}")
            return True

        elif choice == "2":
            show_multipayment(api_key, tokens, payment_items, payment_for, True)
            input(f"\n{W}Silakan cek hasil pembelian di aplikasi MyXL. Tekan Enter...{RESET}")
            return True

        elif choice == "3":
            show_qris_payment(api_key, tokens, payment_items, payment_for, True)
            input(f"\n{W}Silakan lakukan pembayaran & cek hasil pembelian. Tekan Enter...{RESET}")
            return True

        elif choice == "4":
            decoy = DecoyInstance.get_decoy("balance")
            decoy_package_detail = get_package(api_key, tokens, decoy["option_code"])
            if not decoy_package_detail:
                print_card(f"{R}Gagal memuat detail decoy package!{RESET}", "❌ ERROR", width=width, color=R)
                pause()
                return False

            payment_items.append(
                PaymentItem(
                    item_code=decoy_package_detail["package_option"]["package_option_code"],
                    product_type="",
                    item_price=decoy_package_detail["package_option"]["price"],
                    item_name=decoy_package_detail["package_option"]["name"],
                    tax=0,
                    token_confirmation=decoy_package_detail["token_confirmation"],
                )
            )

            overwrite_amount = price + decoy_package_detail["package_option"]["price"]
            print_card(
                [
                    f"{W}Harga Paket Utama:{RESET} {G}{format_price(price)}{RESET}",
                    f"{W}Harga Decoy:{RESET} {G}{format_price(decoy_package_detail['package_option']['price'])}{RESET}",
                    f"{W}Total:{RESET} {Y}{format_price(overwrite_amount)}{RESET}",
                ],
                "💰 TOTAL PEMBAYARAN",
                width=width,
                color=Y,
            )

            res = settlement_balance(
                api_key,
                tokens,
                payment_items,
                payment_for,
                False,
                overwrite_amount=overwrite_amount,
            )

            if res and res.get("status", "") != "SUCCESS":
                error_msg = res.get("message", "Unknown error")
                if "Bizz-err.Amount.Total" in error_msg:
                    valid_amount = int(error_msg.split("=")[1].strip())
                    print_card(
                        f"{Y}Mengadjust total amount ke: {format_price(valid_amount)}{RESET}",
                        "⚠ ADJUSTMENT",
                        width=width,
                        color=Y,
                    )
                    res = settlement_balance(
                        api_key,
                        tokens,
                        payment_items,
                        payment_for,
                        False,
                        overwrite_amount=valid_amount,
                    )
                    if res and res.get("status", "") == "SUCCESS":
                        print_card(f"{G}✓ Pembelian berhasil!{RESET}", "✅ BERHASIL", width=width, color=G)
            else:
                print_card(f"{G}✓ Pembelian berhasil!{RESET}", "✅ BERHASIL", width=width, color=G)

            pause()
            return True

        elif choice == "5":
            decoy = DecoyInstance.get_decoy("balance")
            decoy_package_detail = get_package(api_key, tokens, decoy["option_code"])
            if not decoy_package_detail:
                print_card(f"{R}Gagal memuat detail decoy package!{RESET}", "❌ ERROR", width=width, color=R)
                pause()
                return False

            payment_items.append(
                PaymentItem(
                    item_code=decoy_package_detail["package_option"]["package_option_code"],
                    product_type="",
                    item_price=decoy_package_detail["package_option"]["price"],
                    item_name=decoy_package_detail["package_option"]["name"],
                    tax=0,
                    token_confirmation=decoy_package_detail["token_confirmation"],
                )
            )

            overwrite_amount = price + decoy_package_detail["package_option"]["price"]
            print_card(
                [
                    f"{W}Harga Paket Utama:{RESET} {G}{format_price(price)}{RESET}",
                    f"{W}Harga Decoy:{RESET} {G}{format_price(decoy_package_detail['package_option']['price'])}{RESET}",
                    f"{W}Total:{RESET} {Y}{format_price(overwrite_amount)}{RESET}",
                    f"{D}Menggunakan token confirmation dari decoy{RESET}",
                ],
                "💰 TOTAL PEMBAYARAN (V2)",
                width=width,
                color=Y,
            )

            res = settlement_balance(
                api_key,
                tokens,
                payment_items,
                "SHARE_PACKAGE",
                False,
                overwrite_amount=overwrite_amount,
                token_confirmation_idx=1,
            )

            if res and res.get("status", "") != "SUCCESS":
                error_msg = res.get("message", "Unknown error")
                if "Bizz-err.Amount.Total" in error_msg:
                    valid_amount = int(error_msg.split("=")[1].strip())
                    print_card(
                        f"{Y}Mengadjust total amount ke: {format_price(valid_amount)}{RESET}",
                        "⚠ ADJUSTMENT",
                        width=width,
                        color=Y,
                    )
                    res = settlement_balance(
                        api_key,
                        tokens,
                        payment_items,
                        "SHARE_PACKAGE",
                        False,
                        overwrite_amount=valid_amount,
                        token_confirmation_idx=-1,
                    )
                    if res and res.get("status", "") == "SUCCESS":
                        print_card(f"{G}✓ Pembelian berhasil!{RESET}", "✅ BERHASIL", width=width, color=G)
            else:
                print_card(f"{G}✓ Pembelian berhasil!{RESET}", "✅ BERHASIL", width=width, color=G)

            pause()
            return True

        elif choice == "6":
            decoy = DecoyInstance.get_decoy("qris")
            decoy_package_detail = get_package(api_key, tokens, decoy["option_code"])
            if not decoy_package_detail:
                print_card(f"{R}Gagal memuat detail decoy package!{RESET}", "❌ ERROR", width=width, color=R)
                pause()
                return False

            payment_items.append(
                PaymentItem(
                    item_code=decoy_package_detail["package_option"]["package_option_code"],
                    product_type="",
                    item_price=decoy_package_detail["package_option"]["price"],
                    item_name=decoy_package_detail["package_option"]["name"],
                    tax=0,
                    token_confirmation=decoy_package_detail["token_confirmation"],
                )
            )

            print_card(
                [
                    f"{W}Harga Paket Utama:{RESET} {G}{format_price(price)}{RESET}",
                    f"{W}Harga Paket Decoy:{RESET} {G}{format_price(decoy_package_detail['package_option']['price'])}{RESET}",
                    f"{Y}Silakan sesuaikan amount (trial & error, 0 = malformed){RESET}",
                    f"{D}Menggunakan token confirmation idx: 1{RESET}",
                ],
                "💳 QRIS + DECOY",
                width=width,
                color=Y,
            )

            show_qris_payment(
                api_key,
                tokens,
                payment_items,
                "SHARE_PACKAGE",
                True,
                token_confirmation_idx=1,
            )

            input(f"\n{W}Silakan lakukan pembayaran & cek hasil pembelian. Tekan Enter...{RESET}")
            return True

        elif choice == "7":
            decoy = DecoyInstance.get_decoy("qris0")
            decoy_package_detail = get_package(api_key, tokens, decoy["option_code"])
            if not decoy_package_detail:
                print_card(f"{R}Gagal memuat detail decoy package!{RESET}", "❌ ERROR", width=width, color=R)
                pause()
                return False

            payment_items.append(
                PaymentItem(
                    item_code=decoy_package_detail["package_option"]["package_option_code"],
                    product_type="",
                    item_price=decoy_package_detail["package_option"]["price"],
                    item_name=decoy_package_detail["package_option"]["name"],
                    tax=0,
                    token_confirmation=decoy_package_detail["token_confirmation"],
                )
            )

            print_card(
                [
                    f"{W}Harga Paket Utama:{RESET} {G}{format_price(price)}{RESET}",
                    f"{W}Harga Paket Decoy:{RESET} {G}{format_price(decoy_package_detail['package_option']['price'])}{RESET}",
                    f"{Y}Silakan sesuaikan amount (trial & error, 0 = malformed){RESET}",
                    f"{D}Menggunakan token confirmation idx: 1{RESET}",
                ],
                "💳 QRIS DECOY V2",
                width=width,
                color=Y,
            )

            show_qris_payment(
                api_key,
                tokens,
                payment_items,
                "SHARE_PACKAGE",
                True,
                token_confirmation_idx=1,
            )

            input(f"\n{W}Silakan lakukan pembayaran & cek hasil pembelian. Tekan Enter...{RESET}")
            return True

        elif choice == "8":
            use_decoy = input(f"{W}Gunakan decoy package? (y/n): {RESET}").strip().lower() == "y"
            n_times_str = input(f"{W}Jumlah pembelian (contoh: 3): {RESET}").strip()
            delay_str = input(f"{W}Delay antar pembelian (detik): {RESET}").strip() or "0"

            if not n_times_str.isdigit() or not delay_str.isdigit():
                print_card(f"{R}Input tidak valid!{RESET}", "❌ ERROR", width=width // 2, color=R)
                pause()
                continue

            n_times = int(n_times_str)
            if n_times < 1:
                print_card(f"{R}Jumlah minimal 1!{RESET}", "❌ ERROR", width=width // 2, color=R)
                pause()
                continue

            purchase_n_times_by_option_code(
                n_times,
                option_code=package_option_code,
                use_decoy=use_decoy,
                delay_seconds=int(delay_str),
                pause_on_success=False,
                token_confirmation_idx=1,
            )

        elif choice.lower() == "b":
            settlement_bounty(
                api_key=api_key,
                tokens=tokens,
                token_confirmation=token_confirmation,
                ts_to_sign=ts_to_sign,
                payment_target=package_option_code,
                price=price,
                item_name=variant_name,
            )
            input(f"\n{W}Silakan cek hasil pembelian di aplikasi MyXL. Tekan Enter...{RESET}")
            return True

        elif choice.lower() == "ba":
            destination_msisdn = input(f"{W}Nomor tujuan bonus (62xxxxxxxx): {RESET}").strip()
            bounty_allotment(
                api_key=api_key,
                tokens=tokens,
                ts_to_sign=ts_to_sign,
                destination_msisdn=destination_msisdn,
                item_name=option_name,
                item_code=package_option_code,
                token_confirmation=token_confirmation,
            )
            pause()
            return True

        elif choice.lower() == "l":
            settlement_loyalty(
                api_key=api_key,
                tokens=tokens,
                token_confirmation=token_confirmation,
                ts_to_sign=ts_to_sign,
                payment_target=package_option_code,
                price=price,
            )
            input(f"\n{W}Silakan cek hasil pembelian di aplikasi MyXL. Tekan Enter...{RESET}")
            return True

        else:
            print_card(f"{R}Pilihan tidak valid!{RESET}", "⚠ PERINGATAN", width=width // 2, color=R)
            pause()


def get_packages_by_family(family_code: str, is_enterprise: bool | None = None, migration_type: str | None = None):
    api_key = AuthInstance.api_key
    tokens = AuthInstance.get_active_tokens()
    if not tokens:
        print_card(f"{R}Token tidak ditemukan!{RESET}", "❌ ERROR", width=get_terminal_width(), color=R)
        pause()
        return None

    width = get_terminal_width()
    data = get_family(api_key, tokens, family_code, is_enterprise, migration_type)

    if not data:
        print_card(f"{R}Gagal memuat data keluarga paket!{RESET}", "❌ ERROR", width=width, color=R)
        pause()
        return None

    family_name = data["package_family"]["name"]
    family_type = data["package_family"]["package_family_type"]
    rc_bonus_type = data["package_family"].get("rc_bonus_type", "")
    price_currency = "Poin" if rc_bonus_type == "MYREWARDS" else "Rp"

    variants = data["package_variants"]
    packages = []

    while True:
        clear_screen()
        print_header(f"📦 PAKET {family_name.upper()}", width)

        family_info = [
            {f"{W}Kode Keluarga{RESET}": f"{C}{family_code}{RESET}"},
            {f"{W}Tipe Keluarga{RESET}": f"{G}{family_type}{RESET}"},
            {f"{W}Jumlah Variant{RESET}": f"{Y}{len(variants)} variant{RESET}"},
            {f"{W}Mata Uang{RESET}": f"{M}{price_currency}{RESET}"},
        ]
        print_card(family_info, "📊 INFORMASI KELUARGA PAKET", width=width, color=C)

        option_number = 1
        packages.clear()

        for variant_idx, variant in enumerate(variants, 1):
            variant_name = variant["name"]
            variant_code = variant["package_variant_code"]

            variant_content = [
                f"{B}{Y}Variant {variant_idx}: {variant_name}{RESET}",
                f"{D}Kode: {variant_code}{RESET}",
                f"{W}{H * (width - 6)}{RESET}",
            ]

            options_content = []
            for option in variant["package_options"]:
                option_name = option["name"]
                option_price = option["price"]
                option_code = option["package_option_code"]

                packages.append(
                    {
                        "number": option_number,
                        "variant_name": variant_name,
                        "option_name": option_name,
                        "price": option_price,
                        "code": option_code,
                        "option_order": option["order"],
                    }
                )

                price_display = f"{price_currency} {option_price:,}"
                option_display = f"{C}[{W}{option_number:2}{C}]{RESET} {W}{option_name:<30}{RESET} {G}{price_display:>15}{RESET}"
                options_content.append(option_display)
                option_number += 1

            print_card(variant_content + options_content, f"🎯 VARIANT {variant_idx}", width=width, color=M)

        nav_options = [
            f"{C}[{W}No{C}]{RESET} {W}Pilih paket dengan nomor{RESET}",
            f"{C}[{R}00{C}]{RESET} {W}Kembali ke menu utama{RESET}",
        ]
        print_menu_box("📋 MENU NAVIGASI", nav_options, width=width, color=C)

        pkg_choice = input_box(f"Pilih paket (1-{option_number-1}) atau 00:", width=width)

        if pkg_choice == "00":
            return None

        if not pkg_choice.isdigit():
            print_card(f"{R}Masukkan nomor yang valid!{RESET}", "⚠ PERINGATAN", width=width // 2, color=R)
            pause()
            continue

        selected_num = int(pkg_choice)
        selected_pkg = next((p for p in packages if p["number"] == selected_num), None)

        if not selected_pkg:
            print_card(f"{R}Paket #{selected_num} tidak ditemukan!{RESET}", "❌ ERROR", width=width // 2, color=R)
            pause()
            continue

        show_package_details(
            api_key,
            tokens,
            selected_pkg["code"],
            is_enterprise,
            option_order=selected_pkg["option_order"],
        )

def fetch_my_packages():
    width = get_terminal_width()

    # helper: potong teks berdasarkan display width (bukan len)
    def truncate_to_width(s: str, maxw: int) -> str:
        s = str(s)
        if display_width(s) <= maxw:
            return s
        out = ""
        for ch in s:
            if display_width(out + ch + "...") > maxw:
                break
            out += ch
        return out + "..."

    while True:
        api_key = AuthInstance.api_key
        tokens = AuthInstance.get_active_tokens()
        if not tokens:
            print_card(f"{R}Error: Token tidak ditemukan!{RESET}", "❌ ERROR", width=width, color=R)
            pause()
            return None

        clear_screen()
        print(f"\n{W}🔄{RESET} {C}Sedang sinkronisasi data paket...{RESET}")
        print(f"{W}{H * (width // 2)}{RESET}")

        # ✅ lang Indonesia
        res = send_api_request(
            api_key,
            "api/v8/packages/quota-details",
            {"is_enterprise": False, "lang": "id", "family_member_id": ""},
            tokens.get("id_token"),
            "POST",
        )

        if res.get("status") != "SUCCESS":
            print_card(f"{R}Gagal memuat data paket!{RESET}", "❌ ERROR", width=width, color=R)
            pause()
            return None

        quotas = res["data"]["quotas"]
        package_buffer = []

        for i, quota in enumerate(quotas, 1):
            benefits_list = []
            for b in quota.get("benefits", []):
                name = b.get("name", "")

                rem = b.get("remaining", 0)
                tot = b.get("total", 0)
                dtype = b.get("data_type", "DATA")

                if dtype == "DATA":
                    usage = f"{format_quota_byte(rem).split(' ')[0]}/{format_quota_byte(tot)}"
                elif dtype == "VOICE":
                    usage = f"{rem/60:.0f}/{tot/60:.0f}m"
                else:
                    usage = f"{rem}/{tot}"

                benefits_list.append({"name": name, "usage": usage})

            package_buffer.append(
                {
                    "num": i,
                    "name": quota.get("name", ""),
                    "q_code": quota.get("quota_code", ""),
                    "benefits": benefits_list,
                    "raw": quota,
                }
            )

        clear_screen()
        print_header("📦 DAFTAR PAKET SAYA", width)

        if not package_buffer:
            print_card(f"{Y}Tidak ada paket aktif.{RESET}", "ℹ INFO", width=width, color=Y)
        else:
            for pkg in package_buffer:
                # lebar area isi card (tanpa border + spasi kiri kanan)
                content_width = width - 4

                # rapihin nama paket juga biar gak over
                pkg_name = truncate_to_width(pkg["name"], max(10, content_width - 6))

                card_content = [
                    f"{B}{Y}{pkg['num']}. {pkg_name}{RESET}",
                    f"{D}{'-' * content_width}{RESET}",
                ]
                # Format: "├ <name> ..... : <usage>"
                for b in pkg["benefits"]:
                    name = str(b.get("name", ""))
                    usage = str(b.get("usage", ""))

                    prefix = f"{W}├ {RESET}"
                    sep = f"{W}: {RESET}"
                    right = f"{G}{usage}{RESET}"

                    fixed = display_width(prefix) + display_width(sep) + display_width(right)
                    max_name_w = max(6, content_width - fixed - 1)  # -1 biar aman
                    name = truncate_to_width(name, max_name_w)

                    left = f"{D}{name}{RESET}"

                    filler = content_width - (
                        display_width(prefix) + display_width(left) + display_width(sep) + display_width(right)
                    )
                    filler = max(1, filler)

                    card_content.append(f"{prefix}{left}{' ' * filler}{sep}{right}")

                card_content.append(f"{W}╰ {M}ID: {pkg['q_code'][:12]}...{RESET}")
                print_card(card_content, f"📱 PAKET {pkg['num']}", width=width, color=C)

        nav_options = [
            f"{C}[{W}No{C}]{RESET} {W}Lihat detail paket{RESET}",
            f"{C}[{R}del No{C}]{RESET} {W}Unsubscribe paket{RESET}",
            f"{C}[{R}00{C}]{RESET} {W}Kembali{RESET}",
        ]
        print_menu_box("📋 MENU NAVIGASI", nav_options, width=width, color=C)

        choice = input_box("Pilihan:", width=width).strip().lower()

        if choice == "00":
            return None

        elif choice.isdigit():
            idx = int(choice)
            if 0 < idx <= len(package_buffer):
                show_package_details(api_key, tokens, package_buffer[idx - 1]["q_code"], False)

        elif choice.startswith("del "):
            try:
                idx = int(choice[4:])
                if 0 < idx <= len(package_buffer):
                    quota_code = package_buffer[idx - 1]["q_code"]
                    unsubscribe_res = unsubscribe(api_key, tokens, quota_code)
                    if unsubscribe_res and unsubscribe_res.get("status") == "SUCCESS":
                        print_card(f"{G}✓ Paket berhasil di-unsubscribe!{RESET}", "✅ BERHASIL", width=width, color=G)
                    else:
                        error_msg = unsubscribe_res.get("message", "Unknown error") if unsubscribe_res else "Gagal"
                        print_card(f"{R}✗ {error_msg}{RESET}", "❌ GAGAL", width=width, color=R)
                    pause()
            except ValueError:
                print_card(f"{R}Format tidak valid!{RESET}", "❌ ERROR", width=width // 2, color=R)
                pause()
        else:
            print_card(f"{R}Pilihan tidak valid!{RESET}", "⚠ PERINGATAN", width=width // 2, color=R)
            pause()

