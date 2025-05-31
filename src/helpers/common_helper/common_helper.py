from typing import Dict

def require_keys(payload: Dict, keys: list):
    missing = [k for k in keys if k not in payload]
    if missing:
        raise ValueError(f"Missing required keys: {', '.join(missing)}")
