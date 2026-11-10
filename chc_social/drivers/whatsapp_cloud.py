from .base import Driver, ok, fail


class WhatsApp(Driver):
    """WhatsApp Cloud API — business number, approved templates. Not a personal-account channel."""
    driver = "whatsapp_cloud"
    network = "whatsapp"
    caps = ["post", "read"]

    def post(self, text, to=None, phone_id=None, template=None, media=None, **kw):
        try:
            token = self._env("CHC_WA_TOKEN")
            pid = phone_id or self._env("CHC_WA_PHONE_ID")
            recipient = to or self._env("CHC_WA_TO", required=False)
        except KeyError as e:
            return fail(str(e))
        if not recipient:
            return fail("whatsapp needs a recipient number (to=... or CHC_WA_TO)")
        if media:
            kind = "image" if str(media).lower().endswith((".jpg", ".jpeg", ".png", ".webp")) else "document"
            body = {"messaging_product": "whatsapp", "to": recipient, "type": kind,
                    kind: {"link": media, "caption": text[:1024]}}
        elif template:
            body = {"messaging_product": "whatsapp", "to": recipient, "type": "template",
                    "template": {"name": template, "language": {"code": "en_GB"}}}
        else:
            body = {"messaging_product": "whatsapp", "to": recipient, "type": "text",
                    "text": {"body": text[:4096]}}
        r = self.http("POST", "https://graph.facebook.com/v21.0/%s/messages" % pid,
                      json_body=body, headers={"authorization": "Bearer %s" % token})
        if self.dry_run:
            return ok(network="whatsapp", dry_run=True, request=r)
        if "error" in r or r.get("status", 200) >= 400:
            return fail(r.get("error") or r, network="whatsapp")
        return ok(network="whatsapp", id=((r.get("json") or {}).get("messages") or [{}])[0].get("id"))
