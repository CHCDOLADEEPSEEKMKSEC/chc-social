"""Browser driver — for networks whose APIs will not do it (profiles, groups, no paid tier).

Drives the logged-in Chrome over CDP, using LEARNED recipes (see chc_social/learn.py)
rather than hardcoded selectors. If a recipe is missing, it fails loudly with the reason.
"""
import json, os, subprocess, pathlib
from .base import Driver, ok, fail

VAULT = pathlib.Path(os.environ.get("CHC_VAULT", "/mnt/ledger/vault"))
CDPJS = VAULT / "tools" / "cdpjs.py"


def _cdp(expr, port=None):
    port = str(port or os.environ.get("CHC_CDP_PORT", "9241"))
    r = subprocess.run(["python3", str(CDPJS), expr, "--port", port],
                       capture_output=True, text=True, timeout=45)
    if r.returncode != 0:
        return {"error": (r.stderr or r.stdout).strip()[:400]}
    try:
        return {"ok": True, "value": json.loads(r.stdout.strip())}
    except Exception:
        return {"ok": True, "value": r.stdout.strip()[:2000]}


class Browser(Driver):
    driver = "browser"
    network = "browser"
    caps = ["post", "read"]

    def post(self, text, recipe=None, network=None, **kw):
        from .. import learn
        net = network or (recipe or {}).get("network")
        rec = learn.get(net) if net else None
        if not rec:
            return fail("no learned recipe for network %r — run: chc_social learn propose %s <url>" % (net, net))
        if self.dry_run:
            return ok(network=net, dry_run=True, recipe=rec.get("name"))
        steps = []
        # 1. navigate
        url = (recipe or {}).get("url") or rec.get("url")
        steps.append(_cdp('(function(){location.href=%s;return "nav"})()' % json.dumps(url)))
        import time
        time.sleep(4)
        # 2. focus composer
        sel = rec.get("composer_selector")
        focus = _cdp("(function(){const e=document.querySelector(%s); if(!e) return 'none';"
                     "if(e.focus) e.focus(); if('value' in e){e.value=%s; e.dispatchEvent(new Event('input',{bubbles:true}));}"
                     "else {e.textContent=%s; e.dispatchEvent(new InputEvent('input',{bubbles:true}));}"
                     "return 'filled'})()" % (json.dumps(sel), json.dumps(text), json.dumps(text)))
        steps.append(focus)
        # 3. press send
        send_sel = rec.get("send_selector")
        if send_sel:
            steps.append(_cdp("(function(){const b=document.querySelector(%s); if(!b) return 'no-button';"
                              "b.click(); return 'clicked'})()" % json.dumps(send_sel)))
        else:
            steps.append({"note": "recipe has no send_selector — text only filled, human must submit"})
        return ok(network=net, recipe=rec.get("name"), steps=steps)

    def read(self, recipe=None, network=None, **kw):
        from .. import learn
        rec = learn.get(network)
        if not rec or not rec.get("read_selector"):
            return fail("no learned read recipe for %r" % network)
        return ok(network=network, value=_cdp("(function(){return [...document.querySelectorAll(%s)].slice(0,20)"
                                             ".map(e=>e.innerText.trim())})()" % json.dumps(rec["read_selector"])))
