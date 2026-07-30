"""Endpoints REST consumidos pelo dashboard web."""
from fastapi import APIRouter, HTTPException

from .. import status as api_status
from ...markets import MARKETS
from ... import repository

router = APIRouter(prefix="/api")


@router.get("/markets")
def list_markets():
    return [{"key": m.key, "label": m.label} for m in MARKETS.values()]


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
