"""Entrypoint do backend do dashboard: sobe a API FastAPI + o scheduler do
radar de notícias (B3 + cripto) num único processo.

Uso: python server.py
Depois exponha a porta (padrão 8000) à internet com um túnel (ex: ngrok) para
o frontend hospedado conseguir consultar a API.
"""
import os

import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("src.api.app:app", host="0.0.0.0", port=port, reload=False)
