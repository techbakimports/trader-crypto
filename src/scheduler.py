"""Agendador do radar de notícias para o serviço web (`server.py`).

Registra um job por mercado configurado, cada um no seu próprio intervalo
(`APScheduler`), chamando `news_scanner.scan_once` diretamente — a mesma
função usada pelo loop bloqueante de `news_main.py`, só que aqui despachada
por um scheduler dentro do processo FastAPI ao invés de um `while True`.
"""
import logging
from datetime import datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler

from . import news_scanner, repository
from .config import NewsConfig
from .groq_client import GroqClient
from .telegram_notifier import TelegramNotifier

log = logging.getLogger("scheduler")

_scheduler: BackgroundScheduler | None = None


def start(cfg: NewsConfig) -> BackgroundScheduler:
    global _scheduler
    repository.init_db()

    client = GroqClient(cfg.groq_api_key, cfg.model)
    notifier = TelegramNotifier(cfg.telegram_bot_token, cfg.telegram_chat_id)

    scheduler = BackgroundScheduler()
    for market_cfg in cfg.markets:
        scheduler.add_job(
            news_scanner.scan_once,
            trigger="interval",
            minutes=market_cfg.scan_interval_minutes,
            args=[client, market_cfg, notifier],
            id=f"scan_{market_cfg.key}",
            next_run_time=None,  # dispara já no start (ver abaixo)
            coalesce=True,
            max_instances=1,
        )
    scheduler.start()

    # Dispara um ciclo inicial de cada mercado logo no start, sem esperar o
    # primeiro intervalo completo (senão o dashboard fica vazio até lá) — mas
    # escalonado por mercado, não tudo de uma vez: cada chamada ao modelo
    # "compound" consome bastante tokens/minuto, e disparar vários mercados
    # simultâneos facilmente estoura o rate limit (TPM) da conta.
    for i, market_cfg in enumerate(cfg.markets):
        scheduler.modify_job(
            f"scan_{market_cfg.key}", next_run_time=datetime.now() + timedelta(seconds=i * 20)
        )

    log.info(
        "Scheduler iniciado para mercados: %s",
        ", ".join(m.key for m in cfg.markets),
    )
    _scheduler = scheduler
    return scheduler


def stop() -> None:
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
