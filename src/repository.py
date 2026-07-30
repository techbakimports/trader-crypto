"""Persistência local via SQLite para o radar de notícias multi-mercado.

Guarda os cooldowns de alerta por (mercado, ativo) e o histórico completo de
oportunidades encontradas (usado pelo dashboard web). O scanner de tendência
de cripto (`src/scanner.py`) continua usando `src/state.py` (JSON) — não foi
migrado porque não precisa alimentar o dashboard e não há motivo para tocar
num módulo que já funciona.

Cada função abre e fecha sua própria conexão — volume de escrita é baixo
(alguns registros por ciclo de scan) então não vale a complexidade de pool de
conexões ou de lidar com threads compartilhando uma única conexão sqlite3.
"""
import json
import os
import sqlite3
import time
from contextlib import contextmanager

DATA_DIR = "data"
DB_PATH = os.path.join(DATA_DIR, "app.db")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS opportunities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    market TEXT NOT NULL,
    ativo TEXT NOT NULL,
    referencia_operacional TEXT,
    direcao TEXT,
    horizonte TEXT,
    confianca INTEGER,
    catalisador TEXT,
    resumo TEXT,
    riscos TEXT,
    fontes TEXT,
    panorama TEXT,
    created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_opportunities_market_asset ON opportunities(market, ativo);
CREATE INDEX IF NOT EXISTS idx_opportunities_market_created ON opportunities(market, created_at);

CREATE TABLE IF NOT EXISTS news_cooldowns (
    market TEXT NOT NULL,
    ativo TEXT NOT NULL,
    last_alert_at REAL NOT NULL,
    PRIMARY KEY (market, ativo)
);
"""


@contextmanager
def _connect():
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with _connect() as conn:
        conn.executescript(_SCHEMA)


def is_news_on_cooldown(market: str, ativo: str, cooldown_hours: float) -> bool:
    with _connect() as conn:
        row = conn.execute(
            "SELECT last_alert_at FROM news_cooldowns WHERE market = ? AND ativo = ?",
            (market, ativo),
        ).fetchone()
    if not row:
        return False
    return (time.time() - row["last_alert_at"]) < cooldown_hours * 3600


def mark_news_alerted(market: str, ativo: str) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO news_cooldowns (market, ativo, last_alert_at) VALUES (?, ?, ?) "
            "ON CONFLICT(market, ativo) DO UPDATE SET last_alert_at = excluded.last_alert_at",
            (market, ativo, time.time()),
        )


def save_opportunity(opp, panorama: str) -> None:
    """`opp` é uma instância de `news_analyst.Opportunity`. Grava sempre, mesmo
    que a oportunidade não passe no filtro de confiança/cooldown do alerta —
    o dashboard mostra o histórico completo, não só o que virou alerta."""
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO opportunities (
                market, ativo, referencia_operacional, direcao, horizonte,
                confianca, catalisador, resumo, riscos, fontes, panorama, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                opp.market, opp.ativo, opp.referencia_operacional, opp.direcao, opp.horizonte,
                opp.confianca, opp.catalisador, opp.resumo, opp.riscos,
                json.dumps(opp.fontes), panorama, time.time(),
            ),
        )


def get_latest_opportunities(market: str, limit: int = 50) -> list[dict]:
    """Última oportunidade registrada por ativo naquele mercado, mais recentes primeiro."""
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT o.* FROM opportunities o
            INNER JOIN (
                SELECT ativo, MAX(created_at) AS max_created
                FROM opportunities WHERE market = ?
                GROUP BY ativo
            ) latest ON o.ativo = latest.ativo AND o.created_at = latest.max_created
            WHERE o.market = ?
            ORDER BY o.created_at DESC
            LIMIT ?
            """,
            (market, market, limit),
        ).fetchall()
    return [_row_to_dict(row) for row in rows]


def get_asset_history(market: str, ativo: str, limit: int = 50) -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM opportunities WHERE market = ? AND ativo = ? "
            "ORDER BY created_at DESC LIMIT ?",
            (market, ativo, limit),
        ).fetchall()
    return [_row_to_dict(row) for row in rows]


def get_last_updated(market: str) -> float | None:
    """Timestamp da oportunidade mais recente gravada para o mercado, usado
    pelo endpoint de status do dashboard para mostrar quando cada mercado foi
    varrido pela última vez."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT MAX(created_at) AS last FROM opportunities WHERE market = ?",
            (market,),
        ).fetchone()
    return row["last"] if row and row["last"] is not None else None


def _row_to_dict(row: sqlite3.Row) -> dict:
    item = dict(row)
    try:
        item["fontes"] = json.loads(item["fontes"]) if item.get("fontes") else []
    except json.JSONDecodeError:
        item["fontes"] = []
    return item
