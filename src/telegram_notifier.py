import logging

import requests

log = logging.getLogger("telegram_notifier")


class TelegramNotifier:
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self._url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    @property
    def enabled(self) -> bool:
        """False quando TELEGRAM_BOT_TOKEN/CHAT_ID não estão configurados no
        .env — nesse caso `send` só loga e não faz a chamada HTTP. Permite
        rodar o dashboard (que tem interface própria) sem depender do
        Telegram; usado como canal opcional de alerta."""
        return bool(self.bot_token and self.chat_id)

    def send(self, text: str, parse_mode: str | None = "Markdown") -> None:
        if not self.enabled:
            log.info(
                "Telegram não configurado (.env sem TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID) — "
                "alerta não enviado, oportunidade continua salva no histórico do dashboard."
            )
            return
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "disable_web_page_preview": True,
        }
        if parse_mode:
            payload["parse_mode"] = parse_mode
        resp = requests.post(self._url, json=payload, timeout=15)
        resp.raise_for_status()
