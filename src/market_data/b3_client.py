"""Cliente de dados de mercado para ações da B3.

Fonte primária: brapi.dev (API pública dedicada a ativos da B3, cotações e
histórico de candles). Fallback: yfinance (tickers com sufixo `.SA`), usado
automaticamente se a brapi falhar ou não retornar dados para o ticker.

Nenhuma ordem é executada aqui — só leitura de dados públicos de mercado.
"""
import os

import requests

BASE_URL = "https://brapi.dev/api"
_session = requests.Session()


class Candle:
    __slots__ = ("close", "volume")

    def __init__(self, close: float, volume: float):
        self.close = close
        self.volume = volume


def _brapi_token() -> str | None:
    return os.environ.get("BRAPI_TOKEN") or None


def get_recent_candles(ticker: str, range_: str = "1mo", interval: str = "1d") -> list[Candle]:
    """Retorna candles recentes (fechamento e volume) para um ticker da B3
    (ex: "PETR4", "ITUB4"). Tenta a brapi.dev primeiro; se falhar ou não
    retornar histórico, cai para yfinance."""
    try:
        candles = _get_candles_brapi(ticker, range_, interval)
        if candles:
            return candles
    except Exception:
        pass
    return _get_candles_yfinance(ticker, range_, interval)


def _get_candles_brapi(ticker: str, range_: str, interval: str) -> list[Candle]:
    params = {"range": range_, "interval": interval, "fundamental": "false", "dividends": "false"}
    token = _brapi_token()
    if token:
        params["token"] = token
    resp = _session.get(f"{BASE_URL}/quote/{ticker}", params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    results = data.get("results") or []
    if not results:
        return []
    history = results[0].get("historicalDataPrice") or []
    return [
        Candle(close=float(h["close"]), volume=float(h.get("volume") or 0))
        for h in history
        if h.get("close") is not None
    ]


def _get_candles_yfinance(ticker: str, range_: str, interval: str) -> list[Candle]:
    import yfinance as yf  # dependência opcional, só importada no fallback

    symbol = ticker if ticker.upper().endswith(".SA") else f"{ticker.upper()}.SA"
    hist = yf.Ticker(symbol).history(period=range_, interval=interval)
    if hist.empty:
        raise ValueError(f"yfinance sem dados para {symbol}")
    return [Candle(close=float(row.Close), volume=float(row.Volume)) for row in hist.itertuples()]
