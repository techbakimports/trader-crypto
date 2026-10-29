"""Análise de notícias de mercado via Groq (modelo com busca web embutida),
parametrizada por `MarketProfile`.

Monta o prompt de pesquisa, pede saída em JSON estrito e converte a resposta
em objetos `Opportunity`. Toda a inteligência de "o que é relevante" vive no
prompt — ajuste os `MarketProfile` em `markets.py` se quiser mudar o perfil das
oportunidades buscadas em cada mercado.
"""
import json
import logging
import re
from dataclasses import dataclass, field

from .groq_client import GroqClient
from .markets import MarketProfile

log = logging.getLogger("news_analyst")

PROMPT_TEMPLATE = """\
Você é um analista de mercado focado em {market_label} e em oportunidades de trade de \
curto a médio prazo.

Pesquise na web (incluindo notícias, sites de bancos/corretoras e, se encontrar, \
menções relevantes no X/Twitter) as informações das últimas {lookback_hours} horas sobre:
{catalyst_bullets}

Com base nisso, selecione até {max_opportunities} ativos com potencial de movimento
de preço em horizonte de horas a poucos meses, para cima ou para baixo.

Regras de conduta (importantes):
- Você NÃO deve emitir opinião ou recomendação própria de investimento. Sintetize apenas o
  que fontes reais e identificáveis já disseram (bancos, corretoras, agências de rating,
  portais de notícia, fatos relevantes, dados de mercado).
- Toda oportunidade deve citar explicitamente de onde veio a informação (ex: "segundo
  relatório do Citi", "segundo fato relevante publicado na CVM", "segundo InfoMoney").
- Inclua apenas oportunidades com catalisador concreto e verificável nas fontes.
- Se não houver nada relevante o suficiente, retorne "oportunidades": [].
- Priorize informação das últimas {lookback_hours} horas; ignore notícias velhas.
- Cite sempre a notícia/artigo específico por trás do catalisador. Uma página agregadora
  genérica (ex: uma capa tipo "top stories" ou "daily market wrap" sem um evento isolado)
  NÃO conta como fonte suficiente sozinha — se for tudo que encontrar, trate a oportunidade
  como baixa confiança (ver régua abaixo) ou descarte.

Régua obrigatória para o campo "confianca" (não é uma nota livre — ancore nestes critérios,
do mais forte pro mais fraco, e não pule graus sem justificativa no campo "catalisador"):
- 9-10: catalisador confirmado por fonte primária/oficial (anúncio da própria exchange,
  comunicado oficial do projeto/empresa, fato relevante publicado na CVM) E o evento já
  está confirmado ou em andamento, não é rumor nem projeção.
- 7-8: catalisador confirmado por múltiplas fontes jornalísticas independentes e
  reconhecidas, mesmo que nenhuma seja a fonte primária/oficial.
- 5-6: catalisador vem de uma única fonte secundária específica (um artigo identificável,
  não uma capa agregadora), ou é uma leitura de mercado/narrativa (ex: "rotação de setor",
  "sentimento positivo retornando") sem um evento isolado e datável por trás.
- 1-4: rumor não confirmado, fonte única de baixa confiabilidade, catalisador fraco/indireto,
  ou a única fonte disponível é uma página agregadora genérica.

Responda SOMENTE com um JSON válido, sem texto fora dele, neste formato exato:
{{
  "panorama": "resumo de 2-3 frases do clima geral do mercado agora",
  "oportunidades": [
    {{
      "ativo": "TICKER",
      "referencia_operacional": "{ref_format_hint}",
      "direcao": "alta" ou "baixa",
      "horizonte": "ex: 6-24h, 1-3 dias, 1-3 meses",
      "confianca": inteiro de 1 a 10,
      "catalisador": "a notícia/evento específico que motiva a oportunidade, com atribuição de fonte",
      "resumo": "1-2 frases explicando a tese, atribuída às fontes (não é opinião própria)",
      "riscos": "principal risco da tese em 1 frase",
      "fontes": ["url ou @conta do X de onde veio a informação"]
    }}
  ]
}}

Fontes preferenciais para este mercado: {source_hint}.
"""


@dataclass
class Opportunity:
    market: str
    ativo: str
    referencia_operacional: str | None
    direcao: str
    horizonte: str
    confianca: int
    catalisador: str
    resumo: str
    riscos: str
    fontes: list[str] = field(default_factory=list)


@dataclass
class NewsReport:
    panorama: str
    oportunidades: list[Opportunity]


def fetch_report(
    client: GroqClient, market: MarketProfile, lookback_hours: int, max_opportunities: int
) -> NewsReport:
    prompt = PROMPT_TEMPLATE.format(
        market_label=market.label,
        catalyst_bullets=market.catalyst_bullets,
        lookback_hours=lookback_hours,
        max_opportunities=max_opportunities,
        ref_format_hint=market.ref_format_hint,
        source_hint=market.source_hint,
    )
    raw = client.ask_with_search(prompt)
    return _parse_report(raw, market.key)


def _parse_report(raw: str, market_key: str) -> NewsReport:
    data = _extract_json(raw)
    opportunities = []
    for item in data.get("oportunidades", []):
        try:
            ref = item.get("referencia_operacional")
            if isinstance(ref, str) and ref.strip().lower() in ("", "null", "none", "n/a"):
                ref = None
            opportunities.append(
                Opportunity(
                    market=market_key,
                    ativo=str(item["ativo"]).upper().strip(),
                    referencia_operacional=ref.upper().strip() if isinstance(ref, str) else None,
                    direcao=str(item.get("direcao", "alta")).lower(),
                    horizonte=str(item.get("horizonte", "?")),
                    confianca=int(item.get("confianca", 0)),
                    catalisador=str(item.get("catalisador", "")),
                    resumo=str(item.get("resumo", "")),
                    riscos=str(item.get("riscos", "")),
                    fontes=[str(f) for f in item.get("fontes", [])][:3],
                )
            )
        except (KeyError, ValueError, TypeError) as exc:
            log.warning("Oportunidade malformada ignorada (%s): %s", exc, item)
    return NewsReport(panorama=str(data.get("panorama", "")), oportunidades=opportunities)


def _extract_json(raw: str) -> dict:
    """O modelo às vezes envolve o JSON em cercas de código ou texto solto;
    tenta o parse direto e depois recorta do primeiro `{` ao último `}`."""
    # a busca dos modelos gpt-oss deixa marcadores de citação tipo 【2†L6-L10】 no texto
    raw = re.sub(r"【[^】]*】", "", raw)
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip())
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    start, end = raw.find("{"), raw.rfind("}")
    if start == -1 or end <= start:
        raise ValueError(f"Resposta da Groq não contém JSON: {raw[:300]}")
    return json.loads(raw[start : end + 1])
