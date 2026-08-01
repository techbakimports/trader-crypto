"""Lista padrão de ativos exibidos na cotação ao vivo (independente da análise
de IA) — ajuste livremente conforme o que você quer acompanhar.
"""

WATCHLISTS: dict[str, list[str]] = {
    "crypto": ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT"],
    "b3": ["PETR4", "VALE3", "ITUB4", "BBDC4", "ABEV3", "WEGE3", "B3SA3"],
}
