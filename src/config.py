import os
from dataclasses import dataclass, field

import yaml
from dotenv import load_dotenv

from . import schedule

load_dotenv()


@dataclass
class Config:
    quote_asset: str
    timeframe: str
    max_listing_age_days: int
    lookback_candles: int
    min_price_change_pct: float
    min_volume_spike_ratio: float
    cooldown_hours: float
    scan_interval_seconds: int
    refresh_listings_every_cycles: int
    telegram_bot_token: str
    telegram_chat_id: str


@dataclass
class MarketConfig:
    key: str
    scan_interval_minutes: int
    lookback_hours: int
    max_opportunities: int
    min_confidence: int
    cooldown_hours: float
    # Horário fixo (opcional): se `run_at` estiver preenchido, ele substitui
    # `scan_interval_minutes` — ver src/schedule.py.
    run_at: list[str] = field(default_factory=list)
    days: str = "mon-sun"
    max_lookback_hours: int = 96
    timezone: str = "America/Sao_Paulo"


@dataclass
class NewsConfig:
    model: str
    groq_api_key: str
    telegram_bot_token: str
    telegram_chat_id: str
    markets: list[MarketConfig]


def _load_yaml(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _require_telegram_env() -> tuple[str, str]:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    if not token or not chat_id:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID precisam estar definidos no .env "
            "(copie .env.example para .env e preencha)."
        )
    return token, chat_id


def _optional_telegram_env() -> tuple[str, str]:
    """Como `_require_telegram_env`, mas não falha se estiver vazio — usado pelo
    radar de notícias/dashboard, que tem a própria interface web (`server.py`) e
    não precisa do Telegram pra ser útil. Sem essas variáveis, os alertas
    simplesmente não são enviados (ver `TelegramNotifier.enabled`), mas o
    scanner, o histórico no banco e o dashboard continuam funcionando normalmente."""
    return os.environ.get("TELEGRAM_BOT_TOKEN", ""), os.environ.get("TELEGRAM_CHAT_ID", "")


def load_config(path: str = "config.yaml") -> Config:
    raw = _load_yaml(path)
    token, chat_id = _require_telegram_env()

    return Config(
        quote_asset=raw["quote_asset"],
        timeframe=raw["timeframe"],
        max_listing_age_days=int(raw["max_listing_age_days"]),
        lookback_candles=int(raw["lookback_candles"]),
        min_price_change_pct=float(raw["min_price_change_pct"]),
        min_volume_spike_ratio=float(raw["min_volume_spike_ratio"]),
        cooldown_hours=float(raw["cooldown_hours"]),
        scan_interval_seconds=int(raw["scan_interval_seconds"]),
        refresh_listings_every_cycles=int(raw["refresh_listings_every_cycles"]),
        telegram_bot_token=token,
        telegram_chat_id=chat_id,
    )


def load_news_config(path: str = "config.yaml") -> NewsConfig:
    raw = _load_yaml(path)
    news = raw.get("news") or {}
    token, chat_id = _optional_telegram_env()

    groq_key = os.environ.get("GROQ_API_KEY", "")
    if not groq_key:
        raise RuntimeError(
            "GROQ_API_KEY precisa estar definida no .env para usar o radar de notícias "
            "(crie uma chave em https://console.groq.com — atenção: Groq, não confundir "
            "com a Grok/xAI, são serviços diferentes)."
        )

    markets_raw = news.get("markets")
    if not markets_raw:
        # Compatibilidade com o formato antigo (sem seção `markets:`): assume só cripto.
        markets_raw = {
            "crypto": {
                "scan_interval_minutes": news.get("scan_interval_minutes", 30),
                "lookback_hours": news.get("lookback_hours", 12),
                "max_opportunities": news.get("max_opportunities", 5),
                "min_confidence": news.get("min_confidence", 6),
                "cooldown_hours": news.get("cooldown_hours", 12),
            }
        }

    timezone = str(news.get("timezone", "America/Sao_Paulo"))
    schedule.validate_timezone(timezone)

    markets = []
    for key, m in markets_raw.items():
        run_at = [str(t) for t in (m.get("run_at") or [])]
        days = str(m.get("days", "mon-sun"))
        try:
            schedule.parse_run_at(run_at)
            schedule.parse_days(days)
        except ValueError as exc:
            raise RuntimeError(f"news.markets.{key}: {exc}") from exc
        markets.append(
            MarketConfig(
                key=key,
                scan_interval_minutes=int(m.get("scan_interval_minutes", 30)),
                lookback_hours=int(m.get("lookback_hours", 12)),
                max_opportunities=int(m.get("max_opportunities", 5)),
                min_confidence=int(m.get("min_confidence", 6)),
                cooldown_hours=float(m.get("cooldown_hours", 12)),
                run_at=run_at,
                days=days,
                max_lookback_hours=int(m.get("max_lookback_hours", 96)),
                timezone=timezone,
            )
        )

    return NewsConfig(
        model=news.get("model", "openai/gpt-oss-120b"),
        groq_api_key=groq_key,
        telegram_bot_token=token,
        telegram_chat_id=chat_id,
        markets=markets,
    )
