"""Cliente para a API da Groq (console.groq.com) — não confundir com a Grok/xAI
(api.x.ai), serviço diferente com API incompatível.

Usa o endpoint padrão (compatível com OpenAI) `/openai/v1/chat/completions`.
A busca na web é executada server-side pela Groq, de duas formas:
- modelos `openai/gpt-oss-*`: ferramenta `browser_search` pedida em `tools`
  (a linha `groq/compound*` foi descontinuada em 21/09/2026);
- modelos `groq/compound*`: busca embutida no próprio modelo, sem `tools`.
Modelos sem busca (Llama, Qwen etc.) NÃO devem ser usados aqui, pois o modelo
tende a inventar notícias e fontes quando pedido pra citar algo que não está
nos dados de treino.

Atenção: cada chamada consome tokens (e as buscas feitas pelo modelo),
cobrados pela Groq. Controle a frequência via `scan_interval_minutes` no
config.yaml.
"""
import logging
import threading
import time

import requests

log = logging.getLogger("groq_client")

BASE_URL = "https://api.groq.com/openai/v1"

# Uma busca web gasta dezenas de milhares de tokens e o limite por minuto da conta
# (TPM) é bem menor que isso: chamadas simultâneas de mercados diferentes se
# esbarram em 429. Serializa todas as chamadas do processo.
_CALL_LOCK = threading.Lock()
# Uma busca consome ~35k tokens contra um balde de 8k/min: depois de uma chamada
# pesada o balde fica "devendo" e leva ~4-5 min pra recuperar, então o teto de
# espera precisa ser folgado.
_MAX_429_RETRIES = 5
_MAX_429_WAIT_SECONDS = 300


def _retry_after_seconds(resp: requests.Response) -> float:
    try:
        return min(float(resp.headers["retry-after"]), _MAX_429_WAIT_SECONDS)
    except (KeyError, ValueError):
        return 30.0


class GroqClient:
    def __init__(self, api_key: str, model: str):
        self.model = model
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    def ask_with_search(self, prompt: str, timeout: int = 240) -> str:
        """Envia um prompt a um modelo Groq com busca na web habilitada e
        retorna o texto da resposta."""
        body = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
        }
        if self.model.startswith("openai/gpt-oss"):
            body["tools"] = [{"type": "browser_search"}]
            body["tool_choice"] = "required"
            # a Groq recomenda esforço baixo: níveis maiores alongam a navegação
            # e consomem muito mais tokens
            body["reasoning_effort"] = "low"
        with _CALL_LOCK:
            for attempt in range(_MAX_429_RETRIES + 1):
                resp = requests.post(
                    f"{BASE_URL}/chat/completions", headers=self._headers, json=body, timeout=timeout
                )
                if resp.status_code != 429 or attempt == _MAX_429_RETRIES:
                    break
                wait = _retry_after_seconds(resp)
                log.warning("Groq respondeu 429 (limite de tokens/min); aguardando %.0fs...", wait)
                time.sleep(wait)
        resp.raise_for_status()
        return _extract_message_text(resp.json())


def _extract_message_text(data: dict) -> str:
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError(f"Resposta da Groq sem texto reconhecível: {str(data)[:500]}") from exc
