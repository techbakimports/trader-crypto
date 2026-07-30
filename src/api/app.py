"""App FastAPI que serve o dashboard: inicia o scheduler do radar de notícias
no startup e expõe os endpoints REST consumidos pelo frontend.
"""
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .. import scheduler
from ..config import load_news_config
from .routers.markets import router as markets_router

app = FastAPI(title="Trader Crypto — Dashboard API")

_allowed_origins = [
    origin.strip()
    for origin in os.environ.get("DASHBOARD_ALLOWED_ORIGINS", "http://localhost:5173").split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(markets_router)


@app.on_event("startup")
def on_startup() -> None:
    cfg = load_news_config()
    scheduler.start(cfg)


@app.on_event("shutdown")
def on_shutdown() -> None:
    scheduler.stop()
