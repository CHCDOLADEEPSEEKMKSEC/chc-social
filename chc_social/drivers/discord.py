from .base import Driver, ok, fail


class Discord(Driver):
    driver = "discord"
    network = "discord"
    caps = ["post", "media"]

    def post(self, text, media=None, webhook=None, **kw):
        try:
            hook = webhook or self._env("CHC_DISCORD_WEBHOOK")
        except KeyError as e:
            return fail("%s — set it or run with --dry-run" % e)
        payload = {"content": text[:2000]}
        if media:
            payload["embeds"] = [{"image": {"url": media}}]
        r = self.http("POST", hook, json_body=payload)
        if self.dry_run:
            return ok(network="discord", dry_run=True, request=r)
        if "error" in r or r.get("status", 204) >= 400:
            return fail(r.get("error") or r, network="discord")
        return ok(network="discord", status=r.get("status"))
