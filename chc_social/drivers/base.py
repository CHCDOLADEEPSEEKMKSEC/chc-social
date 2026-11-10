"""Driver contract. Every driver returns a Result; nothing raises silently."""
import json, os, urllib.request, urllib.error


class Result(dict):
    @property
    def ok(self):
        return bool(self.get("ok"))


def ok(**kw):
    d = {"ok": True}
    d.update(kw)
    return Result(d)


def fail(error, **kw):
    d = {"ok": False, "error": str(error)[:600]}
    d.update(kw)
    return Result(d)


class Driver:
    driver = "base"
    network = "base"
    caps = []

    def __init__(self, dry_run=False, timeout=25):
        self.dry_run = dry_run or os.environ.get("CHC_SOCIAL_DRY_RUN") == "1"
        self.timeout = timeout

    # helpers -----------------------------------------------------------------
    def _env(self, name, required=True):
        v = os.environ.get(name)
        if not v and required:
            if self.dry_run:
                return "DRY-RUN"
            raise KeyError("missing env %s" % name)
        return v

    def http(self, method, url, data=None, headers=None, json_body=None):
        """One HTTP call. In dry-run we return the request instead of sending it."""
        body = None
        hdrs = dict(headers or {})
        if json_body is not None:
            body = json.dumps(json_body).encode()
            hdrs["content-type"] = "application/json"
        elif data is not None:
            body = json.dumps(data).encode()
            hdrs["content-type"] = "application/json"
        if self.dry_run:
            return {"dry_run": True, "method": method, "url": url,
                    "body": json.loads(body) if body else None, "headers": sorted(hdrs)}
        req = urllib.request.Request(url, data=body, headers=hdrs, method=method)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                txt = r.read().decode("utf-8", "replace")
                try:
                    return {"status": r.status, "json": json.loads(txt)}
                except Exception:
                    return {"status": r.status, "text": txt[:2000]}
        except urllib.error.HTTPError as e:
            return {"status": e.code, "error": e.read().decode("utf-8", "replace")[:600]}
        except Exception as e:
            return {"error": str(e)[:600]}

    # interface ---------------------------------------------------------------
    def post(self, text, media=None, **kw):
        raise NotImplementedError

    def read(self, **kw):
        raise NotImplementedError

    def delete(self, target_id, **kw):
        """Not every network can delete. Say so as data, never as a traceback."""
        return fail("%s does not implement delete" % self.network, network=self.network)

    def account(self, **kw):
        return fail("%s driver has no identity check" % self.network, network=self.network)
