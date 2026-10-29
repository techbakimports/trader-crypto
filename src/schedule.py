"""Agendamento por horário fixo do radar de notícias.

Em vez de rodar a cada N minutos, um mercado pode declarar `run_at` (lista de
"HH:MM") e `days` (ex: "mon-fri") no `config.yaml`, no fuso `news.timezone`.
Este módulo só valida essa configuração e calcula a janela de notícias: quando o
radar roda poucas vezes por dia (a cota diária da Groq é pequena), a janela de
cada ciclo precisa cobrir o intervalo desde o ciclo anterior — por exemplo, a
varredura de segunda de manhã tem que olhar o fim de semana inteiro.
"""
import math
import re
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

_DAY_NAMES = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]

# O APScheduler pode disparar um job atrasado (servidor fora do ar, CPU ocupada)
# até `misfire_grace_time`; dentro dessa tolerância o ciclo ainda conta como "o
# horário agendado", não como um disparo manual.
SCHEDULED_TOLERANCE = timedelta(minutes=35)


def parse_run_at(run_at: list[str]) -> list[time]:
    parsed = []
    for item in run_at:
        m = re.fullmatch(r"([01]?\d|2[0-3]):([0-5]\d)", str(item).strip())
        if not m:
            raise ValueError(f'Horário inválido em run_at: {item!r} (use "HH:MM", ex: "08:30")')
        parsed.append(time(int(m.group(1)), int(m.group(2))))
    return sorted(set(parsed))


def parse_days(spec: str) -> set[int]:
    """Aceita "mon-fri", "mon,wed,fri" ou combinações ("mon-wed,sat"); devolve
    os índices de dia da semana (0 = segunda)."""
    days: set[int] = set()
    for part in str(spec).lower().replace(" ", "").split(","):
        if "-" in part:
            start, _, end = part.partition("-")
            if start not in _DAY_NAMES or end not in _DAY_NAMES:
                raise ValueError(f"Dia inválido em days: {part!r} (use mon,tue,wed,thu,fri,sat,sun)")
            a, b = _DAY_NAMES.index(start), _DAY_NAMES.index(end)
            days.update(range(a, b + 1) if a <= b else [*range(a, 7), *range(0, b + 1)])
        elif part in _DAY_NAMES:
            days.add(_DAY_NAMES.index(part))
        else:
            raise ValueError(f"Dia inválido em days: {part!r} (use mon,tue,wed,thu,fri,sat,sun)")
    if not days:
        raise ValueError("days está vazio")
    return days


def validate_timezone(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except Exception as exc:
        raise ValueError(f"Fuso horário inválido em news.timezone: {name!r}") from exc


def _past_slots(run_at: list[time], days: set[int], tz: ZoneInfo, now: datetime):
    """Horários agendados <= now, do mais recente para o mais antigo (até 8 dias
    para trás, o bastante para cobrir qualquer combinação de `days`)."""
    for back in range(0, 9):
        date = (now - timedelta(days=back)).date()
        if date.weekday() not in days:
            continue
        for t in sorted(run_at, reverse=True):
            slot = datetime.combine(date, t, tzinfo=tz)
            if slot <= now:
                yield slot


def effective_lookback_hours(market_cfg, now: datetime | None = None) -> int:
    """Janela de notícias (em horas) a pedir ao modelo neste ciclo.

    Sem `run_at` (modo por intervalo) é o `lookback_hours` fixo. Com `run_at`, é
    o tempo desde o ciclo agendado anterior (+1h de folga), nunca menor que
    `lookback_hours` e nunca maior que `max_lookback_hours`."""
    if not market_cfg.run_at:
        return market_cfg.lookback_hours

    tz = ZoneInfo(market_cfg.timezone)
    now = (now or datetime.now(tz)).astimezone(tz)
    slots = _past_slots(parse_run_at(market_cfg.run_at), parse_days(market_cfg.days), tz, now)

    current = next(slots, None)
    if current is None:
        return market_cfg.lookback_hours
    previous = next(slots, None) if now - current <= SCHEDULED_TOLERANCE else current
    if previous is None:
        return market_cfg.lookback_hours

    gap_hours = math.ceil((now - previous).total_seconds() / 3600) + 1
    return min(max(market_cfg.lookback_hours, gap_hours), market_cfg.max_lookback_hours)
