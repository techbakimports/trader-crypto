import json
import os
import time

DATA_DIR = "data"
LISTINGS_FILE = os.path.join(DATA_DIR, "listing_ages.json")
COOLDOWN_FILE = os.path.join(DATA_DIR, "cooldowns.json")
NEWS_COOLDOWN_FILE = os.path.join(DATA_DIR, "news_cooldowns.json")


def _load(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save(path: str, data: dict) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)


def load_listing_times() -> dict[str, int]:
    return _load(LISTINGS_FILE)


def save_listing_times(times: dict[str, int]) -> None:
    _save(LISTINGS_FILE, times)


def load_cooldowns() -> dict[str, float]:
    return _load(COOLDOWN_FILE)


def is_on_cooldown(symbol: str, cooldown_hours: float) -> bool:
    cooldowns = load_cooldowns()
    last = cooldowns.get(symbol)
    if last is None:
        return False
    return (time.time() - last) < cooldown_hours * 3600


def mark_alerted(symbol: str) -> None:
    cooldowns = load_cooldowns()
    cooldowns[symbol] = time.time()
    _save(COOLDOWN_FILE, cooldowns)


def is_news_on_cooldown(asset: str, cooldown_hours: float) -> bool:
    cooldowns = _load(NEWS_COOLDOWN_FILE)
    last = cooldowns.get(asset)
    if last is None:
        return False
    return (time.time() - last) < cooldown_hours * 3600


def mark_news_alerted(asset: str) -> None:
    cooldowns = _load(NEWS_COOLDOWN_FILE)
    cooldowns[asset] = time.time()
    _save(NEWS_COOLDOWN_FILE, cooldowns)
