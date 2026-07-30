from dataclasses import dataclass


@dataclass
class Signal:
    symbol: str
    price_change_pct: float
    volume_spike_ratio: float
    last_price: float


def evaluate_momentum(
    symbol: str,
    klines: list[list],
    min_price_change_pct: float,
    min_volume_spike_ratio: float,
) -> Signal | None:
    """Detecta tendência de alta recente: variação de preço forte acompanhada
    de um pico de volume no candle mais atual, típico de moedas novas
    ganhando tração rapidamente."""
    if len(klines) < 3:
        return None

    closes = [float(k[4]) for k in klines]
    volumes = [float(k[5]) for k in klines]

    first_close = closes[0]
    last_close = closes[-1]
    if first_close <= 0:
        return None
    price_change_pct = (last_close - first_close) / first_close * 100

    prior_volumes = volumes[:-1]
    avg_prior_volume = sum(prior_volumes) / len(prior_volumes) if prior_volumes else 0
    last_volume = volumes[-1]
    volume_spike_ratio = (last_volume / avg_prior_volume) if avg_prior_volume > 0 else 0

    if price_change_pct >= min_price_change_pct and volume_spike_ratio >= min_volume_spike_ratio:
        return Signal(
            symbol=symbol,
            price_change_pct=price_change_pct,
            volume_spike_ratio=volume_spike_ratio,
            last_price=last_close,
        )
    return None
