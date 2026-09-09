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

ALTCOINS = MarketProfile(
    key="altcoins",
    label="Altcoins (cripto pequenas)",
    catalyst_bullets="""\
- moedas de baixa capitalização (fora do top ~100 por market cap) com movimento ou \
narrativa nascente, antes de virarem notícia mainstream
- listagens em exchanges menores ou DEXs (não só Binance/Coinbase/OKX/Bybit) e novos pares
- TGEs, pré-vendas ou IDOs de projetos pouco conhecidos ainda em fase inicial
- narrativas de nicho ganhando tração em comunidades pequenas (Reddit, Telegram, X) antes \
de se espalhar
- menções a "gems" ou "próximas 100x" em fontes específicas e rastreáveis (não em \
posts de hype vago sem evento concreto por trás)""",
    ref_format_hint=(
        'par de negociação na Binance no formato "TICKERUSDT" se existir lá, ou null se '
        'só negociar em exchanges menores/DEXs (nesse caso o dashboard não consegue '
        'enriquecer com gráfico, mas a oportunidade ainda é registrada)'
    ),
    source_hint=(
        "listagens novas no CoinGecko/CoinMarketCap, anúncios oficiais de projetos, "
        "plataformas de IDO/TGE (CoinList, DAO Maker, Polkastarter), e menções "
        "específicas e rastreáveis no X — evite fontes de hype genérico sem evento "
        "identificável por trás"
    ),
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

B3_SMALLCAPS = MarketProfile(
    key="b3_smallcaps",
    label="B3 Small Caps",
    catalyst_bullets="""\
- fatos relevantes na CVM de empresas de menor capitalização, fora do Ibovespa e \
pouco cobertas por grandes bancos
- início de cobertura ("initiation of coverage") por casas de research de small caps \
(ex: Empiricus, Nord Research, Suno) sobre empresas pouco conhecidas
- resultados trimestrais de empresas de segunda linha, especialmente surpresas \
positivas/negativas em relação ao histórico da própria empresa (consenso de mercado \
costuma ser escasso pra essas)
- IPOs recentes, follow-ons ou fusões/aquisições envolvendo empresas menores
- entrada de fundos/gestoras especializadas em small caps na base acionária
- notícias setoriais específicas com pouca cobertura mainstream (ex: agro, saúde, \
tecnologia de nicho) que afetem uma empresa pequena de forma direta""",
    ref_format_hint='ticker da B3 no formato usual (ex: "PETR4", "ITUB4", "INBR32")',
    source_hint=(
        "fatos relevantes na CVM, casas de research especializadas em small caps "
        "(Empiricus, Nord Research, Suno), seções de small caps de portais "
        "financeiros (InfoMoney, Money Times) — evite replicar a mesma cobertura "
        "de blue chips que já sai no mercado 'b3' padrão"
    ),
)

MARKETS: dict[str, MarketProfile] = {
    CRYPTO.key: CRYPTO,
    ALTCOINS.key: ALTCOINS,
    B3.key: B3,
    B3_SMALLCAPS.key: B3_SMALLCAPS,
}
