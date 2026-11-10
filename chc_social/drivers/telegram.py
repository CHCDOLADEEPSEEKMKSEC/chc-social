"""Telegram — full Bot API surface we care about: post, edit, delete, pin, identify, read."""
import os
from .base import Driver, ok, fail


class Telegram(Driver):
    driver = "telegram"
    network = "telegram"
    caps = ["post", "edit", "delete", "read", "media", "account"]

    def _base(self):
        return "https://api.telegram.org/bot%s" % self._env("CHC_TELEGRAM_BOT_TOKEN")

    def _chat(self, chat_id=None):
        return chat_id or self._env("CHC_TELEGRAM_CHAT_ID")

    def post(self, text, media=None, chat_id=None, parse_mode=None, **kw):
        try:
            base = self._base()
            chat = self._chat(chat_id)
        except KeyError as e:
            return fail("%s — set it or run with --dry-run" % e)
        body = {"chat_id": chat}
        if media:
            r = self.http("POST", base + "/sendPhoto", json_body={"chat_id": chat, "photo": media,
                                                                 "caption": text[:1024]})
        else:
            body["text"] = text
            if parse_mode:
                body["parse_mode"] = parse_mode
            r = self.http("POST", base + "/sendMessage", json_body=body)
        if self.dry_run:
            return ok(network="telegram", dry_run=True, request=r)
        if "error" in r or r.get("status", 200) >= 400:
            return fail(r.get("error") or r, network="telegram")
        j = r.get("json") or {}
        return ok(network="telegram", id=(j.get("result") or {}).get("message_id"), response=j)

    def edit(self, message_id, text, chat_id=None, **kw):
        try:
            base = self._base()
            chat = self._chat(chat_id)
        except KeyError as e:
            return fail(str(e), network="telegram")
        r = self.http("POST", base + "/editMessageText",
                      json_body={"chat_id": chat, "message_id": int(message_id), "text": text})
        if self.dry_run:
            return ok(network="telegram", dry_run=True, request=r)
        if "error" in r or r.get("status", 200) >= 400:
            return fail(r.get("error") or r, network="telegram")
        return ok(network="telegram", edited=int(message_id))

    def delete(self, message_id, chat_id=None, **kw):
        try:
            base = self._base()
            chat = self._chat(chat_id)
        except KeyError as e:
            return fail(str(e), network="telegram")
        r = self.http("POST", base + "/deleteMessage",
                      json_body={"chat_id": chat, "message_id": int(message_id)})
        if self.dry_run:
            return ok(network="telegram", dry_run=True, request=r)
        if "error" in r or r.get("status", 200) >= 400:
            return fail(r.get("error") or r, network="telegram")
        return ok(network="telegram", deleted=int(message_id))

    def pin(self, message_id, chat_id=None, **kw):
        try:
            base = self._base()
            chat = self._chat(chat_id)
        except KeyError as e:
            return fail(str(e), network="telegram")
        r = self.http("POST", base + "/pinChatMessage",
                      json_body={"chat_id": chat, "message_id": int(message_id)})
        if self.dry_run:
            return ok(network="telegram", dry_run=True, request=r)
        if "error" in r or r.get("status", 200) >= 400:
            return fail(r.get("error") or r, network="telegram")
        return ok(network="telegram", pinned=int(message_id))

    def account(self, **kw):
        """getMe — proves which identity the token belongs to before anything is posted."""
        try:
            base = self._base()
        except KeyError as e:
            return fail(str(e), network="telegram")
        r = self.http("GET", base + "/getMe")
        if self.dry_run:
            return ok(network="telegram", dry_run=True, request=r)
        j = r.get("json") or {}
        me = j.get("result") or {}
        if not me:
            return fail(r.get("error") or r, network="telegram")
        return ok(network="telegram", username=me.get("username"), name=me.get("first_name"),
                  bot_id=me.get("id"), is_bot=me.get("is_bot"))

    def read(self, limit=10, chat_id=None, **kw):
        try:
            base = self._base()
        except KeyError as e:
            return fail(str(e), network="telegram")
        r = self.http("GET", base + "/getUpdates")
        updates = (r.get("json") or {}).get("result", [])
        out = []
        for u in updates[-limit:]:
            msg = u.get("message") or u.get("channel_post") or {}
            out.append({"id": msg.get("message_id"), "text": msg.get("text"),
                        "date": msg.get("date")})
        return ok(network="telegram", updates=out)
