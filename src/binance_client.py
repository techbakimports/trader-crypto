"""Cliente simples para os endpoints públicos de mercado da Binance.

Nenhum endpoint aqui exige API key: são todos dados públicos de mercado.
"""
import time

import requests

BASE_URL = "https://api.binance.com"
_session = requests.Session()


def get_trading_symbols(quote_asset: str) -> list[str]:
    """Retorna todos os pares SPOT em negociação contra `quote_asset` (ex: USDT)."""
    resp = _session.get(f"{BASE_URL}/api/v3/exchangeInfo", timeout=15)
    resp.raise_for_status()
    data = resp.json()

    symbols = []
    for s in data["symbols"]:
        if (
            s["quoteAsset"] == quote_asset
            and s["status"] == "TRADING"
            and s.get("isSpotTradingAllowed", True)
        ):
            symbols.append(s["symbol"])
    return symbols


def get_first_candle_open_time(symbol: str) -> int:
    """Timestamp (ms) do primeiro candle diário disponível, usado como proxy
    da data de listagem do par (a API pública da Binance não expõe isso direto)."""
    params = {"symbol": symbol, "interval": "1d", "startTime": 0, "limit": 1}
    resp = _session.get(f"{BASE_URL}/api/v3/klines", params=params, timeout=15)
    resp.raise_for_status()
    klines = resp.json()
    if not klines:
        return int(time.time() * 1000)
    return int(klines[0][0])


def get_recent_klines(symbol: str, interval: str, limit: int) -> list[list]:
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    resp = _session.get(f"{BASE_URL}/api/v3/klines", params=params, timeout=15)
    resp.raise_for_status()
    return resp.json()
