"""Laço principal do módulo de notícias: consulta o modelo (Groq) periodicamente (um
mercado por vez), filtra oportunidades por confiança e cooldown, enriquece com
dados de gráfico da fonte de mercado correspondente, grava o histórico
completo no banco local (para o dashboard) e envia um resumo consolidado no
Telegram para as que passaram no filtro.

Este módulo só envia alertas informativos. Nenhuma ordem é executada.
"""
import logging
import time
from dataclasses import dataclass

from . import binance_client, repository
from .config import MarketConfig, NewsConfig
from .groq_client import GroqClient
from .market_data import b3_client
from .markets import MARKETS
from .news_analyst import Opportunity, fetch_report
from .telegram_notifier import TelegramNotifier

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("news_scanner")


def _enrich_crypto(ref: str) -> str:
    klines = binance_client.get_recent_klines(ref, "1h", 25)
    if len(klines) < 3:
        return ""
    closes = [float(k[4]) for k in klines]
    volumes = [float(k[5]) for k in klines]
    change = (closes[-1] - closes[0]) / closes[0] * 100 if closes[0] > 0 else 0
    avg_vol = sum(volumes[:-1]) / len(volumes[:-1])
    vol_ratio = volumes[-1] / avg_vol if avg_vol > 0 else 0
    return (
        f"\nGráfico ({ref}): preço {closes[-1]:g}, {change:+.2f}% em 24h, "
        f"volume da última hora {vol_ratio:.1f}x a média."
    )


def _enrich_b3(ref: str) -> str:
    candles = b3_client.get_recent_candles(ref, range_="1mo", interval="1d")
    if len(candles) < 3:
        return ""
    closes = [c.close for c in candles]
    volumes = [c.volume for c in candles]
    change = (closes[-1] - closes[0]) / closes[0] * 100 if closes[0] > 0 else 0
    avg_vol = sum(volumes[:-1]) / len(volumes[:-1])
    vol_ratio = volumes[-1] / avg_vol if avg_vol > 0 else 0
    return (
        f"\nGráfico ({ref}): preço R$ {closes[-1]:.2f}, {change:+.2f}% no período, "
        f"volume do último pregão {vol_ratio:.1f}x a média."
    )


_ENRICHERS = {"crypto": _enrich_crypto, "b3": _enrich_b3}


def enrich_with_chart(opp: Opportunity) -> str:
    """Busca dados de gráfico na fonte de mercado correspondente para dar
    contexto ao alerta. Retorna string vazia se não houver referência
    operacional ou a consulta falhar."""
    if not opp.referencia_operacional:
        return ""
    enricher = _ENRICHERS.get(opp.market)
    if not enricher:
        return ""
    try:
        return enricher(opp.referencia_operacional)
    except Exception as exc:
        log.info("Sem dados de gráfico para %s (%s): %s", opp.referencia_operacional, opp.market, exc)
        return ""


def format_alert(opp: Opportunity) -> str:
    seta = "▲" if opp.direcao == "alta" else "▼"
    lines = [
        f"{seta} {opp.ativo} — {opp.direcao.upper()} (confiança {opp.confianca}/10)",
        f"Horizonte: {opp.horizonte}",
        f"Catalisador: {opp.catalisador}",
        f"Tese: {opp.resumo}",
        f"Risco: {opp.riscos}",
    ]
    chart = enrich_with_chart(opp)
    if chart:
        lines.append(chart.strip())
    if opp.fontes:
        lines.append("Fontes: " + " | ".join(opp.fontes))
    return "\n".join(lines)


@dataclass
class ScanResult:
    ok: bool
    total: int = 0
    alerted: int = 0
    error: str | None = None


def scan_once(
    client: GroqClient, market_cfg: MarketConfig, notifier: TelegramNotifier
) -> ScanResult:
    """Roda um ciclo do radar pra um mercado. O retorno é usado pelo disparo
    manual (endpoint da API) pra devolver status real ao usuário — o loop
    agendado (scheduler/`run`) ignora o retorno, como sempre fez."""
    market = MARKETS[market_cfg.key]
    log.info(
        "[%s] Consultando Groq por notícias das últimas %dh...",
        market.key, market_cfg.lookback_hours,
    )
    try:
        report = fetch_report(
            client, market, market_cfg.lookback_hours, market_cfg.max_opportunities
        )
    except Exception as exc:
        log.error("[%s] Falha na análise de notícias via Groq: %s", market.key, exc)
        return ScanResult(ok=False, error=str(exc))

    # Grava o histórico completo (mesmo o que não vira alerta) para o dashboard.
    for o in report.oportunidades:
        try:
            repository.save_opportunity(o, report.panorama)
        except Exception as exc:
            log.error("[%s] Falha ao gravar oportunidade no banco: %s", market.key, exc)

    selected = [
        o for o in report.oportunidades
        if o.confianca >= market_cfg.min_confidence
        and not repository.is_news_on_cooldown(market.key, o.ativo, market_cfg.cooldown_hours)
    ]
    log.info(
        "[%s] Groq retornou %d oportunidade(s); %d passaram no filtro de confiança/cooldown",
        market.key, len(report.oportunidades), len(selected),
    )
    if not selected:
        return ScanResult(ok=True, total=len(report.oportunidades), alerted=0)

    blocks = [f"📰 Radar de notícias — {market.label}\n"]
    if report.panorama:
        blocks.append(f"Panorama: {report.panorama}\n")
    blocks.extend(format_alert(o) + "\n" for o in selected)
    blocks.append("_Síntese de fontes públicas gerada por IA — não é recomendação de investimento. DYOR._")

    try:
        # parse_mode desativado: o texto vem do modelo e pode conter caracteres
        # que quebram o Markdown do Telegram.
        notifier.send("\n".join(blocks), parse_mode=None)
        for o in selected:
            repository.mark_news_alerted(market.key, o.ativo)
    except Exception as exc:
        log.error("[%s] Falha ao enviar alerta de notícias no Telegram: %s", market.key, exc)
        return ScanResult(ok=True, total=len(report.oportunidades), alerted=0, error=f"alerta Telegram falhou: {exc}")

    return ScanResult(ok=True, total=len(report.oportunidades), alerted=len(selected))


def run(cfg: NewsConfig) -> None:
    repository.init_db()
    client = GroqClient(cfg.groq_api_key, cfg.model)
    notifier = TelegramNotifier(cfg.telegram_bot_token, cfg.telegram_chat_id)
    log.info(
        "Radar de notícias iniciado. Modelo: %s | mercados: %s",
        cfg.model, ", ".join(m.key for m in cfg.markets),
    )

    next_run = {m.key: 0.0 for m in cfg.markets}
    poll_seconds = min(m.scan_interval_minutes for m in cfg.markets) * 60
    while True:
        now = time.time()
        for market_cfg in cfg.markets:
            if now >= next_run[market_cfg.key]:
                scan_once(client, market_cfg, notifier)
                next_run[market_cfg.key] = now + market_cfg.scan_interval_minutes * 60
        time.sleep(poll_seconds)
