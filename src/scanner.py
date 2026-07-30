import logging
import time

from . import binance_client, state
from .config import Config
from .strategy import evaluate_momentum
from .telegram_notifier import TelegramNotifier

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("scanner")

MS_PER_DAY = 24 * 60 * 60 * 1000


def refresh_new_listings(cfg: Config) -> list[str]:
    """Atualiza o cache de idade de listagem e retorna os símbolos
    lançados há menos de `max_listing_age_days` dias."""
    log.info("Atualizando lista de pares e idade de listagem...")
    symbols = binance_client.get_trading_symbols(cfg.quote_asset)
    cached = state.load_listing_times()

    now_ms = int(time.time() * 1000)
    for symbol in symbols:
        if symbol not in cached:
            try:
                cached[symbol] = binance_client.get_first_candle_open_time(symbol)
            except Exception as exc:  # nao deixa um simbolo problematico derrubar o scan
                log.warning("Falha ao obter idade de listagem de %s: %s", symbol, exc)

    state.save_listing_times(cached)

    new_listings = [
        s for s in symbols
        if s in cached and (now_ms - cached[s]) <= cfg.max_listing_age_days * MS_PER_DAY
    ]
    log.info("Moedas recém-lançadas monitoradas: %d de %d pares totais", len(new_listings), len(symbols))
    return new_listings


def format_alert(signal, cfg: Config) -> str:
    return (
        f"*Tendência detectada: {signal.symbol}*\n"
        f"Preço atual: `{signal.last_price}`\n"
        f"Variação ({cfg.lookback_candles}x{cfg.timeframe}): `+{signal.price_change_pct:.2f}%`\n"
        f"Volume vs média: `{signal.volume_spike_ratio:.1f}x`\n"
        f"Par recém-listado na Binance (janela de {cfg.max_listing_age_days} dias).\n"
        f"_Isto é um alerta informativo, não é recomendação de investimento._"
    )


def scan_once(symbols: list[str], cfg: Config, notifier: TelegramNotifier) -> None:
    for symbol in symbols:
        if state.is_on_cooldown(symbol, cfg.cooldown_hours):
            continue
        try:
            klines = binance_client.get_recent_klines(
                symbol, cfg.timeframe, cfg.lookback_candles + 1
            )
        except Exception as exc:
            log.warning("Falha ao buscar klines de %s: %s", symbol, exc)
            continue

        signal = evaluate_momentum(
            symbol, klines, cfg.min_price_change_pct, cfg.min_volume_spike_ratio
        )
        if signal:
            log.info(
                "Sinal em %s: %.2f%% / volume %.1fx",
                signal.symbol, signal.price_change_pct, signal.volume_spike_ratio,
            )
            try:
                notifier.send(format_alert(signal, cfg))
                state.mark_alerted(symbol)
            except Exception as exc:
                log.error("Falha ao enviar alerta do Telegram para %s: %s", symbol, exc)


def run(cfg: Config) -> None:
    notifier = TelegramNotifier(cfg.telegram_bot_token, cfg.telegram_chat_id)
    watchlist = refresh_new_listings(cfg)
    cycle = 0

    log.info("Scanner iniciado. Intervalo de varredura: %ds", cfg.scan_interval_seconds)
    while True:
        if cycle > 0 and cycle % cfg.refresh_listings_every_cycles == 0:
            watchlist = refresh_new_listings(cfg)

        scan_once(watchlist, cfg, notifier)
        cycle += 1
        time.sleep(cfg.scan_interval_seconds)
