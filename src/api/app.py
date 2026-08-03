"""App FastAPI que serve o dashboard: inicia o scheduler do radar de notícias
no startup, expõe os endpoints REST e, se existir um build do frontend
(`frontend/dist/`), serve ele também — assim um único processo (`server.py`)
cobre backend + frontend, sem precisar de Node/Nginx separado (útil pra rodar
em ambientes com poucos recursos, ex: Termux num celular).
"""
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

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
    allow_methods=["GET", "POST"],
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


_frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if _frontend_dist.is_dir():
    app.mount("/", StaticFiles(directory=str(_frontend_dist), html=True), name="frontend")
