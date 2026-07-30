"""Cliente para a API da Groq (console.groq.com) — não confundir com a Grok/xAI
(api.x.ai), serviço diferente com API incompatível.

Usa o endpoint padrão (compatível com OpenAI) `/openai/v1/chat/completions` com
um modelo da linha "compound" (ex: `groq/compound`), que tem busca na web
embutida server-side. Modelos padrão da Groq (Llama, Mixtral etc.) NÃO têm
acesso à internet — não usar aqui, pois o modelo tende a inventar notícias e
fontes quando pedido pra citar algo que não está nos dados de treino.

Atenção: cada chamada consome tokens (e as invocações de busca do modelo
compound), cobrados pela Groq. Controle a frequência via
`scan_interval_minutes` no config.yaml.
"""
import requests

BASE_URL = "https://api.groq.com/openai/v1"


class GroqClient:
    def __init__(self, api_key: str, model: str):
        self.model = model
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    def ask_with_search(self, prompt: str, timeout: int = 240) -> str:
        """Envia um prompt a um modelo Groq com busca na web habilitada
        (assumindo um modelo da linha "compound") e retorna o texto da resposta."""
        body = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
        }
        resp = requests.post(
            f"{BASE_URL}/chat/completions", headers=self._headers, json=body, timeout=timeout
        )
        resp.raise_for_status()
        return _extract_message_text(resp.json())


def _extract_message_text(data: dict) -> str:
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError(f"Resposta da Groq sem texto reconhecível: {str(data)[:500]}") from exc
