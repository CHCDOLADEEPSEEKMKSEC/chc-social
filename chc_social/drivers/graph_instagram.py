"""Instagram Graph API — single image, carousel, and Reels. Media is always required."""
import time
from .base import Driver, ok, fail

GRAPH = "https://graph.facebook.com/v21.0"


class Instagram(Driver):
    driver = "graph_instagram"
    network = "instagram"
    caps = ["post", "media"]

    def _creds(self, ig_user_id=None):
        token = self._env("CHC_FB_PAGE_TOKEN")
        uid = ig_user_id or self._env("CHC_IG_USER_ID")
        return token, uid

    def post(self, text, media=None, carousel=None, reel=None, ig_user_id=None, **kw):
        try:
            token, uid = self._creds(ig_user_id)
        except KeyError as e:
            return fail(str(e), network="instagram")

        if carousel:
            items = [m for m in (carousel if isinstance(carousel, list) else carousel.split(",")) if m]
            if len(items) < 2:
                return fail("carousel needs 2+ media urls", network="instagram")
            if self.dry_run:
                return ok(network="instagram", dry_run=True, kind="carousel", items=len(items), caption=text[:120])
            children = []
            for m in items:
                r = self.http("POST", GRAPH + "/%s/media" % uid,
                              json_body={"image_url": m, "is_carousel_item": True, "access_token": token})
                cid = (r.get("json") or {}).get("id")
                if not cid:
                    return fail(r.get("error") or r, network="instagram", step="carousel child")
                children.append(cid)
            create = self.http("POST", GRAPH + "/%s/media" % uid,
                               json_body={"media_type": "CAROUSEL", "children": ",".join(children),
                                          "caption": text[:2200], "access_token": token})
            return self._publish(create, uid, token, kind="carousel", extra={"children": len(children)})

        if reel:
            if self.dry_run:
                return ok(network="instagram", dry_run=True, kind="reel", video=reel)
            create = self.http("POST", GRAPH + "/%s/media" % uid,
                               json_body={"media_type": "REELS", "video_url": reel,
                                          "caption": text[:2200], "access_token": token})
            cid = (create.get("json") or {}).get("id")
            if not cid:
                return fail(create.get("error") or create, network="instagram", step="reel create")
            # reels need processing time before publish; poll status a few times
            for _ in range(10):
                time.sleep(3)
                st = self.http("GET", GRAPH + "/%s?fields=status_code&access_token=%s" % (cid, token))
                code = (st.get("json") or {}).get("status_code")
                if code == "FINISHED":
                    break
            return self._publish({"json": {"id": cid}}, uid, token, kind="reel")

        if not media:
            return fail("instagram cannot post text-only — pass media=<public image url>, "
                        "carousel=<urls>, or reel=<public video url>", network="instagram")
        if self.dry_run:
            return ok(network="instagram", dry_run=True, kind="image", media=media)
        create = self.http("POST", GRAPH + "/%s/media" % uid,
                           json_body={"image_url": media, "caption": text[:2200], "access_token": token})
        cid = (create.get("json") or {}).get("id")
        if not cid:
            return fail(create.get("error") or create, network="instagram", step="create")
        return self._publish({"json": {"id": cid}}, uid, token, kind="image")

    def _publish(self, create, uid, token, kind, extra=None):
        cid = (create.get("json") or {}).get("id")
        if not cid:
            return fail(create.get("error") or create, network="instagram", step="create")
        pub = self.http("POST", GRAPH + "/%s/media_publish" % uid,
                        json_body={"creation_id": cid, "access_token": token})
        if "error" in pub or pub.get("status", 200) >= 400:
            return fail(pub.get("error") or pub, network="instagram", step="publish", creation=cid, kind=kind)
        out = {"network": "instagram", "kind": kind, "id": (pub.get("json") or {}).get("id")}
        if extra:
            out.update(extra)
        return ok(**out)
