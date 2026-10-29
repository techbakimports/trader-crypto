"""Agendador do radar de notícias para o serviço web (`server.py`).

Registra jobs por mercado configurado (`APScheduler`), chamando
`news_scanner.scan_once` diretamente. Cada mercado roda em horários fixos
(`run_at` + `days`, no fuso `news.timezone`) ou, se não declarar `run_at`, num
intervalo fixo (`scan_interval_minutes`). Também é usado pelo loop bloqueante
de `news_main.py`.
"""
import logging
from datetime import datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from . import news_scanner, repository, schedule
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
    interval_markets = []
    for market_cfg in cfg.markets:
        args = [client, market_cfg, notifier]
        if market_cfg.run_at:
            tz = schedule.validate_timezone(market_cfg.timezone)
            for t in schedule.parse_run_at(market_cfg.run_at):
                scheduler.add_job(
                    news_scanner.scan_once,
                    trigger=CronTrigger(
                        day_of_week=market_cfg.days.replace(" ", ""),
                        hour=t.hour, minute=t.minute, timezone=tz,
                    ),
                    args=args,
                    id=f"scan_{market_cfg.key}_{t:%H%M}",
                    coalesce=True,
                    max_instances=1,
                    misfire_grace_time=int(schedule.SCHEDULED_TOLERANCE.total_seconds()),
                )
            continue
        interval_markets.append(market_cfg)
        scheduler.add_job(
            news_scanner.scan_once,
            trigger="interval",
            minutes=market_cfg.scan_interval_minutes,
            args=args,
            id=f"scan_{market_cfg.key}",
            next_run_time=None,  # dispara já no start (ver abaixo)
            coalesce=True,
            max_instances=1,
        )
    scheduler.start()

    # Mercados por intervalo disparam um ciclo logo no start, sem esperar o
    # primeiro intervalo completo (senão o dashboard fica vazio até lá) — mas
    # escalonado por mercado, não tudo de uma vez: cada chamada ao modelo
    # com busca web consome bastante tokens/minuto, e disparar vários mercados
    # simultâneos facilmente estoura o rate limit (TPM) da conta. Mercados com
    # horário fixo NÃO rodam no start: cada reinício gastaria cota da Groq à toa
    # (o histórico já está no banco).
    for i, market_cfg in enumerate(interval_markets):
        scheduler.modify_job(
            f"scan_{market_cfg.key}", next_run_time=datetime.now() + timedelta(seconds=i * 20)
        )

    for job in sorted(scheduler.get_jobs(), key=lambda j: j.id):
        log.info("Agendado %s — próxima execução: %s", job.id, job.next_run_time)
    log.info(
        "Scheduler iniciado para mercados: %s",
        ", ".join(m.key for m in cfg.markets),
    )
    _scheduler = scheduler
    return scheduler


def stop() -> None:
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
