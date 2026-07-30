"""Perfis de mercado suportados pelo radar de notícias.

Cada `MarketProfile` parametriza o prompt genérico em `news_analyst.py` — o que
muda de um mercado para outro é só o que pedimos ao modelo para procurar e como
formatar a referência operacional do ativo (par da Binance vs. ticker da B3).
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class MarketProfile:
    key: str
    label: str
    catalyst_bullets: str
    ref_format_hint: str
    source_hint: str


CRYPTO = MarketProfile(
    key="crypto",
    label="Criptomoedas",
    catalyst_bullets="""\
- listagens novas ou anunciadas em exchanges grandes (Binance, Coinbase, OKX, Bybit)
- lançamentos de token / TGE / vendas públicas (o "IPO" do mundo cripto) próximos ou recentes
- destravamentos de tokens (unlocks), airdrops relevantes e upgrades de rede
- notícias de ETFs, adoção institucional, parcerias e regulamentação
- hacks, exploits ou colapsos (oportunidades de baixa também contam)
- narrativas com tração súbita no X (memecoins, setores em rotação)""",
    ref_format_hint='par de negociação na Binance no formato "TICKERUSDT", ou null se não for negociado lá',
    source_hint="exchanges, dados on-chain, anúncios oficiais de projetos e threads relevantes no X",
)

B3 = MarketProfile(
    key="b3",
    label="Ações da B3 (Brasil)",
    catalyst_bullets="""\
- relatórios e mudanças de recomendação/rating de bancos e corretoras (ex: Citi, Safra, \
BTG Pactual, Itaú BBA, Bradesco BBI, XP, Goldman Sachs)
- resultados trimestrais (balanços) acima ou abaixo do esperado pelo consenso
- fatos relevantes divulgados à CVM (fusões, aquisições, recompras, mudanças de gestão)
- revisão de guidance/projeções de lucro para cima ou para baixo
- entrada ou saída relevante de grandes investidores/gestoras na base acionária
- notícias macro ou regulatórias com impacto direto e específico no setor da empresa""",
    ref_format_hint='ticker da B3 no formato usual (ex: "PETR4", "ITUB4", "INBR32")',
    source_hint=(
        "relatórios públicos e notícias de bancos/corretoras (Citi, Safra, BTG Pactual, "
        "Itaú BBA, Bradesco BBI, XP), fatos relevantes na CVM e portais financeiros "
        "(InfoMoney, Money Times, Valor Econômico, Suno)"
    ),
)

MARKETS: dict[str, MarketProfile] = {
    CRYPTO.key: CRYPTO,
    B3.key: B3,
}
