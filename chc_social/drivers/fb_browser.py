"""Facebook via the logged-in browser — profiles AND groups, which the Graph API cannot touch.

This is the route we have actually proven live on this machine: click "What's on your mind",
type into the contenteditable, click Post. Group flow: navigate to the group, then the same.
Every step returns what it saw, so a failure says WHERE it failed, not just that it did.
"""
import json, time
from .base import Driver, ok, fail
from .browser import _cdp

COMPOSER_JS = """(() => {
  const e=[...document.querySelectorAll('div[role=button]')].find(x=>/on your mind|write something/i.test(x.innerText||''));
  if(!e) return {found:false};
  const r=e.getBoundingClientRect(); return {found:true, x:Math.round(r.x+r.width/2), y:Math.round(r.y+r.height/2)};
})()"""

FOCUS_JS = """(() => {
  const els=[...document.querySelectorAll('div[contenteditable=true]')].filter(e=>e.getBoundingClientRect().width>200);
  const e=els[els.length-1]; if(!e) return {found:false};
  e.focus();
  return {found:true, nodes:els.length};
})()"""

POST_JS = """(() => {
  const b=[...document.querySelectorAll('div[role=button]')]
    .filter(x=>/^(post|publish)$/i.test((x.innerText||'').trim()) && x.getBoundingClientRect().width>20);
  if(!b.length) return {found:false};
  const r=b[b.length-1].getBoundingClientRect();
  return {found:true, x:Math.round(r.x+r.width/2), y:Math.round(r.y+r.height/2)};
})()"""

STATE_JS = """(() => ({
  url: location.href,
  composer_open: !!document.querySelector('div[role=dialog]') || !!document.querySelector('div[contenteditable=true]'),
  typed_chars: (() => { const e=[...document.querySelectorAll('div[contenteditable=true]')].pop(); return e ? (e.innerText||'').length : 0; })()
}))()"""


class FacebookBrowser(Driver):
    driver = "fb_browser"
    network = "facebook"
    caps = ["post", "read"]

    def post(self, text, media=None, target_url="https://www.facebook.com/", **kw):
        steps = []
        if self.dry_run:
            return ok(network="facebook", dry_run=True, mode="logged-in browser",
                      would_navigate=target_url, would_type=text[:200], steps=[])

        nav = _cdp('(function(){location.href=%s;return location.href})()' % json.dumps(target_url))
        steps.append({"step": "navigate", "to": target_url, "result": nav.get("value")})
        time.sleep(6)

        cur = _cdp("location.href")
        if "facebook.com" not in str(cur.get("value") or ""):
            return fail("browser did not reach facebook.com (got %r) — is the tab logged in?" % cur.get("value"),
                        network="facebook", steps=steps)

        box = _cdp(COMPOSER_JS)
        steps.append({"step": "find composer", "result": box.get("value")})
        pos = box.get("value") or {}
        if not isinstance(pos, dict) or not pos.get("found"):
            return fail("composer trigger not found on this page (logged out, captcha, or layout change)",
                        network="facebook", steps=steps)

        click = _cdp("(function(){const el=document.elementFromPoint(%d,%d); if(!el) return 'none'; el.click(); return el.tagName})()"
                     % (pos["x"], pos["y"]))
        steps.append({"step": "click composer", "result": click.get("value")})
        time.sleep(4)

        foc = _cdp(FOCUS_JS)
        steps.append({"step": "focus editor", "result": foc.get("value")})
        if not (foc.get("value") or {}).get("found"):
            return fail("composer opened but no editable box found", network="facebook", steps=steps)

        # typing through the page's own input path, otherwise React ignores it
        typed = _cdp("""(function(){
          const e=[...document.querySelectorAll('div[contenteditable=true]')].pop();
          if(!e) return {ok:false};
          e.focus();
          e.innerText=%s;
          e.dispatchEvent(new InputEvent('input', {bubbles:true, data:null, inputType:'insertText'}));
          return {ok:true, chars:(e.innerText||'').length};
        })()""" % json.dumps(text))
        steps.append({"step": "type text", "result": typed.get("value")})
        if not (typed.get("value") or {}).get("ok"):
            return fail("could not type into the editor", network="facebook", steps=steps)
        time.sleep(2)

        btn = _cdp(POST_JS)
        steps.append({"step": "find post button", "result": btn.get("value")})
        bpos = btn.get("value") or {}
        if not isinstance(bpos, dict) or not bpos.get("found"):
            return fail("Post button not found — text is typed but NOT published", network="facebook", steps=steps)

        pub = _cdp("(function(){const el=document.elementFromPoint(%d,%d); if(!el) return 'none'; el.click(); return el.tagName})()"
                   % (bpos["x"], bpos["y"]))
        steps.append({"step": "click post", "result": pub.get("value")})
        time.sleep(9)

        after = _cdp(STATE_JS)
        steps.append({"step": "verify", "result": after.get("value")})
        st = after.get("value") or {}
        closed = not (isinstance(st, dict) and st.get("composer_open"))
        return ok(network="facebook", mode="logged-in browser", target=target_url,
                  composer_closed=closed, steps=steps,
                  note="composer closed after clicking Post" if closed else
                       "composer still open — post may have failed, check the page")

    def read(self, url="https://www.facebook.com/", limit=10, **kw):
        _cdp('(function(){location.href=%s;return 1})()' % json.dumps(url)); time.sleep(5)
        r = _cdp("""(() => [...document.querySelectorAll('div[role=article]')].slice(0,20)
          .map(e => (e.innerText||'').trim().slice(0,300)).filter(Boolean))()""")
        return ok(network="facebook", posts=(r.get("value") or [])[:limit])
