import time

from app.service.auth import AuthInstance
from app.service.firebase_sync import FirebaseSync
from app.service.local_db import LocalDB


def _mask_number(number: str) -> str:
    num = str(number or "")
    if len(num) < 4:
        return num
    return f"{num[:2]}****{num[-2:]}"


def _parse_response(response):
    status = "UNKNOWN"
    error_code = ""
    error_message = ""
    if isinstance(response, dict):
        status = response.get("status") or response.get("payment_status") or "UNKNOWN"
        error_code = str(response.get("code") or response.get("code_detail") or "")
        error_message = (
            response.get("message")
            or response.get("description")
            or response.get("title")
            or ""
        )
    elif response is None:
        status = "FAILED"
        error_message = "no_response"
    else:
        status = "FAILED"
        error_message = str(response)
    return status, error_code, error_message


def log_transaction(
    method: str,
    items: list[dict],
    amount: int,
    response,
    *,
    status_override: str | None = None,
    error_code_override: str | None = None,
    error_message_override: str | None = None,
):
    package_code = ""
    package_name = ""
    if items:
        package_code = items[0].get("item_code", "")
        package_name = items[0].get("item_name", "")

    user_number = ""
    if AuthInstance.active_user:
        user_number = str(AuthInstance.active_user.get("number", ""))

    status, error_code, error_message = _parse_response(response)
    if status_override is not None:
        status = status_override
    if error_code_override is not None:
        error_code = error_code_override
    if error_message_override is not None:
        error_message = error_message_override

    store = LocalDB()
    local_id = store.log_transaction(
        user_number=user_number,
        package_code=package_code,
        package_name=package_name,
        method=method,
        amount=amount,
        status=status,
        error_code=error_code,
        error_message=error_message,
        response_json=response,
    )

    payload = {
        "timestamp": int(time.time()),
        "package_code": package_code,
        "package_name": package_name,
        "method": method,
        "amount": amount,
        "status": status,
        "error_code": error_code,
        "error_message": error_message,
        "user_number_masked": _mask_number(user_number),
    }
    ok, err = FirebaseSync.push_transaction(payload)
    store.mark_synced(local_id, None if ok else err)


def log_simple_transaction(
    method: str,
    package_code: str,
    package_name: str,
    amount: int,
    response,
):
    items = [{"item_code": package_code, "item_name": package_name}]
    log_transaction(method, items, amount, response)
