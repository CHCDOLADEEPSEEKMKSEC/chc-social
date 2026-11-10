import os
from .base import Driver, ok, fail


class Telegram(Driver):
    driver = "telegram"
    network = "telegram"
    caps = ["post", "read", "media", "delete"]

    def post(self, text, media=None, chat_id=None, **kw):
        try:
            token = self._env("CHC_TELEGRAM_BOT_TOKEN")
            chat = chat_id or self._env("CHC_TELEGRAM_CHAT_ID", required=False) or self._env("CHC_TELEGRAM_CHAT_ID")
        except KeyError as e:
            return fail("%s — set it or run with --dry-run" % e)
        base = "https://api.telegram.org/bot%s" % token
        if media:
            r = self.http("POST", base + "/sendPhoto",
                          json_body={"chat_id": chat, "photo": media, "caption": text[:1024]})
        else:
            r = self.http("POST", base + "/sendMessage",
                          json_body={"chat_id": chat, "text": text, "disable_web_page_preview": False})
        if self.dry_run:
            return ok(network="telegram", dry_run=True, request=r)
        if "error" in r or r.get("status", 200) >= 400:
            return fail(r.get("error") or r, network="telegram")
        j = r.get("json") or {}
        return ok(network="telegram", id=(j.get("result") or {}).get("message_id"), response=j)

    def read(self, limit=10, **kw):
        try:
            token = self._env("CHC_TELEGRAM_BOT_TOKEN")
            chat = self._env("CHC_TELEGRAM_CHAT_ID")
        except KeyError as e:
            return fail(str(e))
        r = self.http("GET", "https://api.telegram.org/bot%s/getUpdates" % token)
        return ok(network="telegram", updates=(r.get("json") or {}).get("result", [])[:limit], raw=r)
