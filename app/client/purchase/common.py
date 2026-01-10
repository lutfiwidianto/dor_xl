import json
from app.client.myxl_api import send_api_request

from app.config import load_config

_CONFIG = load_config()
BASE_API_URL = str(_CONFIG.get("base_api_url", "")).strip()
if not BASE_API_URL:
    raise ValueError("base_api_url missing in firebase.config.json")
AX_FP = str(_CONFIG.get("ax_fp", "")).strip()
UA = str(_CONFIG.get("user_agent", _CONFIG.get("ua", ""))).strip()
if not UA:
    raise ValueError("user_agent missing in firebase.config.json")

def get_payment_methods(
    api_key: str,
    tokens: dict,
    token_confirmation: str,
    payment_target: str,
):
    payment_path = "payments/api/v8/payment-methods-option"
    payment_payload = {
        "payment_type": "PURCHASE",
        "is_enterprise": False,
        "payment_target": payment_target,
        "lang": "en",
        "is_referral": False,
        "token_confirmation": token_confirmation
    }
    
    payment_res = send_api_request(api_key, payment_path, payment_payload, tokens["id_token"], "POST")
    if payment_res["status"] != "SUCCESS":
        print("Failed to fetch payment methods.")
        print(f"Error: {payment_res}")
        return None

    return payment_res["data"]
