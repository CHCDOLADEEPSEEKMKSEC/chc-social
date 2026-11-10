from .base import Driver, ok, fail


class X(Driver):
    driver = "x"
    network = "x"
    caps = ["post", "delete"]

    def post(self, text, media=None, **kw):
        if len(text) > 280:
            return fail("x limit is 280 chars, got %d" % len(text))
        try:
            token = self._env("CHC_X_BEARER")
        except KeyError as e:
            return fail("%s — X API v2 write needs a paid tier; use --network browser for the free route" % e)
        r = self.http("POST", "https://api.x.com/2/tweets",
                      json_body={"text": text},
                      headers={"authorization": "Bearer %s" % token})
        if self.dry_run:
            return ok(network="x", dry_run=True, request=r)
        if "error" in r or r.get("status", 201) >= 400:
            return fail(r.get("error") or r, network="x")
        return ok(network="x", id=((r.get("json") or {}).get("data") or {}).get("id"))

    def delete(self, tweet_id, **kw):
        try:
            token = self._env("CHC_X_BEARER")
        except KeyError as e:
            return fail(str(e), network="x")
        r = self.http("DELETE", "https://api.x.com/2/tweets/%s" % tweet_id,
                      headers={"authorization": "Bearer %s" % token})
        if self.dry_run:
            return ok(network="x", dry_run=True, request=r)
        if "error" in r or r.get("status", 200) >= 400:
            return fail(r.get("error") or r, network="x")
        return ok(network="x", deleted=str(tweet_id))
