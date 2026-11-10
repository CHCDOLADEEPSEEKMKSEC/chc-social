from .base import Driver, ok, fail


class FacebookPage(Driver):
    """Meta Graph API — Facebook PAGES only (profiles and groups are not available)."""
    driver = "graph_page"
    network = "facebook"
    caps = ["post", "read", "insights"]

    def post(self, text, media=None, link=None, page_id=None, **kw):
        try:
            token = self._env("CHC_FB_PAGE_TOKEN")
            pid = page_id or self._env("CHC_FB_PAGE_ID")
        except KeyError as e:
            return fail("%s — the Graph API needs a Page + token; for profiles/groups use --network browser" % e)
        url = "https://graph.facebook.com/v21.0/%s/feed" % pid
        body = {"message": text, "access_token": token}
        if link:
            body["link"] = link
        r = self.http("POST", url, json_body=body)
        if self.dry_run:
            return ok(network="facebook", dry_run=True, request=r)
        if "error" in r or r.get("status", 200) >= 400:
            return fail(r.get("error") or r, network="facebook")
        return ok(network="facebook", id=(r.get("json") or {}).get("id"))

    def read(self, limit=10, page_id=None, **kw):
        try:
            token = self._env("CHC_FB_PAGE_TOKEN")
            pid = page_id or self._env("CHC_FB_PAGE_ID")
        except KeyError as e:
            return fail(str(e))
        r = self.http("GET", "https://graph.facebook.com/v21.0/%s/posts?limit=%d&access_token=%s" % (pid, limit, token))
        return ok(network="facebook", posts=(r.get("json") or {}).get("data", []), raw=r)
