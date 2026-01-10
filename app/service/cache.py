import json
import os
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
CACHE_PATH = Path(os.getenv('DORXL_CACHE_PATH', str(BASE_DIR / 'data' / 'cache.json')))
DEFAULT_TTL = 120


def _load_cache() -> dict:
    if not CACHE_PATH.exists():
        return {}
    try:
        return json.loads(CACHE_PATH.read_text(encoding='utf-8'))
    except Exception:
        return {}


def _save_cache(data: dict) -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(data, ensure_ascii=True, indent=2), encoding='utf-8')


def make_cache_key(*parts) -> str:
    return ':'.join(str(p) for p in parts)


def cache_get(key: str):
    data = _load_cache()
    entry = data.get(key)
    if not entry:
        return None
    ts = int(entry.get('ts', 0))
    ttl = int(entry.get('ttl', 0))
    if ttl <= 0 or (int(time.time()) - ts) > ttl:
        data.pop(key, None)
        _save_cache(data)
        return None
    return entry.get('value')


def cache_set(key: str, value, ttl: int = DEFAULT_TTL) -> None:
    data = _load_cache()
    data[key] = {
        'ts': int(time.time()),
        'ttl': int(ttl),
        'value': value,
    }
    _save_cache(data)
