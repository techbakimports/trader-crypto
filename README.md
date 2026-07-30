# Trader Crypto — Scanner de Tendência + Radar de Notícias + Dashboard

Três formas de consumir o mesmo radar de notícias, mais um scanner independente:

1. **Scanner de tendência** (`main.py`) — monitora criptomoedas **recém-listadas
   na Binance** e alerta quando detecta movimento de alta forte (variação de
   preço + pico de volume). Independente de tudo abaixo.
2. **Radar de notícias via Telegram** (`news_main.py`) — usa a **API da Groq**
   (modelo com busca web embutida) para achar notícias/relatórios relevantes e
   sugerir oportunidades, mandando um resumo por ciclo no Telegram. Cobre só o
   mercado cripto por padrão (comportamento idêntico ao original).
3. **Dashboard web** (`server.py` + `frontend/`) — o mesmo radar de notícias,
   agora **multi-mercado (cripto + ações da B3)**, rodando em background dentro
   de uma API FastAPI, com histórico persistido em SQLite e uma interface web
   com abas por mercado (ver [Dashboard web](#dashboard-web) abaixo).

**Este projeto só gera alertas e análises informativas. Nenhuma ordem de
compra/venda é executada, e nenhuma recomendação de investimento é emitida —
tudo é síntese de fontes públicas (notícias, relatórios de bancos/corretoras,
fatos relevantes), sempre com atribuição.**

## Como funciona — Scanner de tendência

1. Busca todos os pares SPOT da Binance contra a moeda de cotação configurada (padrão: USDT).
2. Descobre quais são "recém-lançados" olhando o primeiro candle diário disponível de cada par
   (a API pública da Binance não expõe data de listagem diretamente).
3. Para cada moeda recém-lançada, avalia os últimos candles do timeframe configurado:
   - variação de preço no período (`min_price_change_pct`)
   - pico de volume no candle mais recente vs. média anterior (`min_volume_spike_ratio`)
4. Se os dois critérios baterem, envia um alerta no Telegram (com cooldown por moeda
   para não repetir o aviso toda hora).

## Como funciona — Radar de notícias

1. A cada `scan_interval_minutes`, pergunta a um modelo da Groq (linha "compound",
   com busca web embutida) o que aconteceu de relevante nas últimas `lookback_hours`
   horas: listagens em exchanges, TGEs/vendas públicas, unlocks, ETFs, hacks e
   narrativas ganhando tração (cripto), ou relatórios/ratings de bancos, resultados
   trimestrais e fatos relevantes (B3).
2. O modelo devolve um JSON com até `max_opportunities` oportunidades (ativo, direção,
   horizonte, confiança 1-10, catalisador, tese, riscos e fontes).
3. Oportunidades com confiança abaixo de `min_confidence` ou em cooldown são descartadas.
4. Para ativos negociados na Binance ou na B3, o alerta é enriquecido com dados do
   gráfico (variação e volume recente vs. média).
5. Tudo é enviado num único resumo no Telegram por ciclo.

> **Custo:** cada ciclo consome tokens (e as buscas feitas pelo modelo) cobrados
> pela Groq. Com o padrão de 30 min são ~48 consultas/dia só de cripto — ajuste o
> intervalo conforme seu orçamento. O mercado B3 usa um intervalo maior por padrão
> (120 min) justamente para não dobrar o custo à toa.
>
> **Atenção:** use um modelo da linha "compound" da Groq (com busca web real).
> Modelos padrão (Llama, Mixtral etc.) não têm acesso à internet e podem *inventar*
> notícias/fontes quando pedidos para citar algo — o que quebraria a premissa de
> "só sintetizar fontes reais" deste projeto.

## Configuração

1. Crie um bot no Telegram com o [@BotFather](https://t.me/BotFather) e pegue o `TELEGRAM_BOT_TOKEN`.
2. Descubra o `TELEGRAM_CHAT_ID` (converse com o bot e use `https://api.telegram.org/bot<TOKEN>/getUpdates`,
   ou use um bot como @userinfobot para pegar seu chat id).
3. Para o radar de notícias, crie uma chave de API em [console.groq.com](https://console.groq.com)
   (`GROQ_API_KEY`) — **atenção:** é a Groq, não a Grok/xAI, são serviços diferentes
   apesar do nome parecido. A chave da Groq começa com `gsk_`.
4. (Opcional, recomendado para o mercado B3) crie um token gratuito em
   [brapi.dev](https://brapi.dev) (`BRAPI_TOKEN`) — sem ele o client de dados da B3
   ainda funciona (cai para `yfinance`), só com rate limit mais restrito.
5. Copie `.env.example` para `.env` e preencha os valores.
6. Ajuste os parâmetros em [config.yaml](config.yaml) (estratégia do scanner, seção
   `news.markets` para cripto/B3).

```bash
pip install -r requirements.txt
python main.py        # scanner de tendência (Binance)
python news_main.py   # radar de notícias (Groq) por Telegram — pode rodar em paralelo
```

## Dashboard web

`server.py` sobe uma API FastAPI que roda o mesmo radar de notícias em
background (cripto + B3, cada mercado no seu próprio intervalo) e persiste o
histórico completo de oportunidades em SQLite (`data/app.db`) — não só o que
vira alerta, para o dashboard poder mostrar a análise completa de cada ativo.

### Rodando localmente

```bash
python server.py          # backend + scheduler na porta 8000 (configurável via $PORT)
cd frontend
npm install
npm run dev                # dashboard em http://localhost:5173
```

O frontend lê `VITE_API_BASE_URL` (padrão `http://localhost:8000`, ver
`frontend/.env.example`).

### Expondo o backend à internet (para hospedar só o frontend)

Como o scheduler precisa rodar continuamente, o jeito mais simples e gratuito de
ter o dashboard acessível de qualquer lugar sem pagar hospedagem é manter o
`server.py` rodando no seu PC e expor a porta via túnel:

1. Crie uma conta grátis em [ngrok.com](https://ngrok.com) e reserve um domínio
   estático gratuito (evita que a URL mude toda vez que reiniciar o túnel).
2. Com o `server.py` rodando, execute `ngrok http 8000 --domain=SEU-DOMINIO.ngrok-free.app`.
3. Configure `DASHBOARD_ALLOWED_ORIGINS` no `.env` com a URL do frontend hospedado
   (para o CORS liberar) e `VITE_API_BASE_URL` do frontend com a URL do ngrok.
4. Faça o deploy do `frontend/` na [Vercel](https://vercel.com) (build estático,
   free tier) apontando a env var `VITE_API_BASE_URL` para a URL do ngrok.

**Limitação:** o dashboard só mostra dados atualizados enquanto seu PC estiver
ligado com `server.py` e o ngrok ativos — é a contrapartida de não pagar
hospedagem. Migrar o backend para um serviço always-on (Fly.io, Railway, ~US$5-7/mês)
no futuro resolve isso sem tocar no resto da arquitetura.

## Estrutura

- `src/binance_client.py` — chamadas aos endpoints públicos de mercado da Binance.
- `src/strategy.py` — regra de detecção de tendência (variação de preço + spike de volume).
- `src/scanner.py` — laço principal do scanner de tendência.
- `src/telegram_notifier.py` — envio de alertas via Bot API do Telegram.
- `src/state.py` — cache local em JSON (idade de listagem e cooldown) usado só pelo
  scanner de tendência.
- `src/groq_client.py` — cliente da API da Groq (`/openai/v1/chat/completions`,
  modelo "compound" com busca web embutida), agnóstico de mercado.
- `src/markets.py` — perfis de mercado (`MarketProfile`) para cripto e B3: o que pedir
  ao modelo e como formatar a referência operacional de cada um.
- `src/news_analyst.py` — prompt (parametrizado por mercado) e parsing do JSON de oportunidades.
- `src/news_scanner.py` — laço do radar de notícias: filtra, enriquece com gráfico
  (Binance ou B3, conforme o mercado), persiste no banco e alerta no Telegram.
- `src/market_data/b3_client.py` — dados de mercado da B3 (brapi.dev, fallback yfinance).
- `src/repository.py` — persistência SQLite (`data/app.db`) do radar de notícias:
  cooldowns por (mercado, ativo) e histórico completo de oportunidades.
- `src/scheduler.py` — agenda o `scan_once` de cada mercado dentro do processo do
  dashboard (usado só por `server.py`, não pelos loops de `news_main.py`/`main.py`).
- `src/api/` — app FastAPI (`app.py`) e endpoints REST (`routers/markets.py`)
  consumidos pelo dashboard.
- `server.py` — entrypoint do backend do dashboard (API + scheduler).
- `frontend/` — dashboard web (Vite + React + TypeScript + Tailwind).

## Aviso

Moedas recém-listadas com movimentos rápidos são **extremamente voláteis e arriscadas**.
Ações também estão sujeitas a riscos de mercado. Este projeto é uma ferramenta
informativa — toda análise é síntese de fontes públicas, atribuída, e **não é
recomendação de investimento**.
