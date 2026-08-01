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


def get_quotes(tickers: list[str]) -> list[dict]:
    """Cotação atual (preço, variação %, volume) para vários tickers da B3 num
    único request (usado pra cotação ao vivo, sem custo de IA). Cada item:
    {"symbol", "price", "change_pct", "volume"}. Tickers que falharem na brapi
    e no fallback são omitidos do resultado, não interrompem os demais."""
    try:
        quotes = _get_quotes_brapi(tickers)
        if quotes:
            return quotes
    except Exception:
        pass
    return _get_quotes_yfinance(tickers)


def _get_quotes_brapi(tickers: list[str]) -> list[dict]:
    params = {"fundamental": "false", "dividends": "false"}
    token = _brapi_token()
    if token:
        params["token"] = token
    joined = ",".join(tickers)
    resp = _session.get(f"{BASE_URL}/quote/{joined}", params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    results = data.get("results") or []
    return [
        {
            "symbol": r["symbol"],
            "price": r.get("regularMarketPrice"),
            "change_pct": r.get("regularMarketChangePercent"),
            "volume": r.get("regularMarketVolume"),
        }
        for r in results
        if r.get("regularMarketPrice") is not None
    ]


def _get_quotes_yfinance(tickers: list[str]) -> list[dict]:
    import yfinance as yf  # dependência opcional, só importada no fallback

    quotes = []
    for ticker in tickers:
        symbol = ticker if ticker.upper().endswith(".SA") else f"{ticker.upper()}.SA"
        try:
            hist = yf.Ticker(symbol).history(period="2d", interval="1d")
            if hist.empty:
                continue
            closes = hist["Close"]
            price = float(closes.iloc[-1])
            change_pct = (
                (price - float(closes.iloc[-2])) / float(closes.iloc[-2]) * 100
                if len(closes) > 1 and closes.iloc[-2]
                else None
            )
            quotes.append(
                {
                    "symbol": ticker.upper(),
                    "price": price,
                    "change_pct": change_pct,
                    "volume": float(hist["Volume"].iloc[-1]),
                }
            )
        except Exception:
            continue
    return quotes


def _get_candles_yfinance(ticker: str, range_: str, interval: str) -> list[Candle]:
    import yfinance as yf  # dependência opcional, só importada no fallback

    symbol = ticker if ticker.upper().endswith(".SA") else f"{ticker.upper()}.SA"
    hist = yf.Ticker(symbol).history(period=range_, interval=interval)
    if hist.empty:
        raise ValueError(f"yfinance sem dados para {symbol}")
    return [Candle(close=float(row.Close), volume=float(row.Volume)) for row in hist.itertuples()]
