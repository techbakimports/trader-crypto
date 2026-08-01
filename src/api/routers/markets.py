"""Endpoints REST consumidos pelo dashboard web."""
from fastapi import APIRouter, HTTPException

from .. import status as api_status
from ...config import load_news_config
from ...markets import MARKETS
from ...watchlists import WATCHLISTS
from ... import binance_client, news_scanner, repository
from ...groq_client import GroqClient
from ...market_data import b3_client
from ...telegram_notifier import TelegramNotifier

router = APIRouter(prefix="/api")


@router.get("/markets")
def list_markets():
    return [{"key": m.key, "label": m.label} for m in MARKETS.values()]


@router.get("/markets/{market}/quotes")
def market_quotes(market: str):
    """Cotação ao vivo (preço, variação, volume) — dado de mercado puro, sem IA."""
    if market not in MARKETS:
        raise HTTPException(status_code=404, detail=f"Mercado desconhecido: {market}")
    tickers = WATCHLISTS.get(market, [])
    if not tickers:
        return []
    try:
        if market == "crypto":
            raw = binance_client.get_ticker_24h(tickers)
            return [
                {
                    "symbol": t["symbol"],
                    "price": float(t["lastPrice"]),
                    "change_pct": float(t["priceChangePercent"]),
                    "volume": float(t["volume"]),
                }
                for t in raw
            ]
        if market == "b3":
            return b3_client.get_quotes(tickers)
        return []
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Falha ao buscar cotações: {exc}")


@router.post("/markets/{market}/scan")
def trigger_scan(market: str):
    """Dispara um ciclo de análise agora, fora do agendamento — consome a API
    da Groq como qualquer ciclo normal (não é gratuito nem instantâneo)."""
    if market not in MARKETS:
        raise HTTPException(status_code=404, detail=f"Mercado desconhecido: {market}")
    cfg = load_news_config()
    market_cfg = next((m for m in cfg.markets if m.key == market), None)
    if market_cfg is None:
        raise HTTPException(
            status_code=404, detail=f"Mercado {market} não está configurado em news.markets"
        )
    client = GroqClient(cfg.groq_api_key, cfg.model)
    notifier = TelegramNotifier(cfg.telegram_bot_token, cfg.telegram_chat_id)
    result = news_scanner.scan_once(client, market_cfg, notifier)
    return {
        "ok": result.ok,
        "total_oportunidades": result.total,
        "alertadas": result.alerted,
        "error": result.error,
    }


@router.get("/markets/{market}/opportunities")
def latest_opportunities(market: str, limit: int = 50):
    if market not in MARKETS:
        raise HTTPException(status_code=404, detail=f"Mercado desconhecido: {market}")
    return repository.get_latest_opportunities(market, limit=limit)


@router.get("/markets/{market}/opportunities/{asset}/history")
def asset_history(market: str, asset: str, limit: int = 50):
    if market not in MARKETS:
        raise HTTPException(status_code=404, detail=f"Mercado desconhecido: {market}")
    return repository.get_asset_history(market, asset.upper(), limit=limit)


@router.get("/status")
def status():
    return api_status.get_status()
