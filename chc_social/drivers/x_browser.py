"""X / Twitter via the logged-in browser — free route, no paid API tier."""
import json, time
from .base import Driver, ok, fail
from .browser import _cdp

NAV = '(function(){location.href=%s;return location.href})()'
COMPOSE = """(() => {
  const sels=["[data-testid='tweetTextarea_0']","div[contenteditable='true'][role='textbox']","div[contenteditable='true']"];
  for(const s of sels){ const e=document.querySelector(s); if(e){ e.focus(); return {found:true, sel:s}; } }
  return {found:false};
})()"""
POSTBTN = """(() => {
  const b=[...document.querySelectorAll("[data-testid='tweetButtonInline'],[data-testid='tweetButton'],div[role=button],button")]
    .filter(x=>/^(post|post all|tweet)$/i.test((x.innerText||'').trim()) && x.getBoundingClientRect().width>10);
  if(!b.length) return {found:false};
  const r=b[b.length-1].getBoundingClientRect();
  return {found:true, x:Math.round(r.x+r.width/2), y:Math.round(r.y+r.height/2)};
})()"""


class XBrowser(Driver):
    driver = "x_browser"
    network = "x"
    caps = ["post", "read"]

    def post(self, text, url="https://x.com/compose/post", **kw):
        steps = []
        if len(text) > 280:
            return fail("x limit is 280 chars, got %d" % len(text), network="x", steps=steps)
        if self.dry_run:
            return ok(network="x", dry_run=True, mode="logged-in browser", would_post=text)
        steps.append({"step": "navigate", "result": _cdp(NAV % json.dumps(url)).get("value")})
        time.sleep(7)
        foc = _cdp(COMPOSE)
        steps.append({"step": "focus editor", "result": foc.get("value")})
        if not (foc.get("value") or {}).get("found"):
            return fail("no editable tweet box (not logged in, or compose URL changed)", network="x", steps=steps)
        typed = _cdp("""(function(){
          const e=document.activeElement;
          if(!e || !e.getAttribute) return {ok:false};
          e.innerText=%s;
          e.dispatchEvent(new InputEvent('input',{bubbles:true,data:null,inputType:'insertText'}));
          return {ok:true, chars:(e.innerText||'').length};
        })()""" % json.dumps(text))
        steps.append({"step": "type", "result": typed.get("value")})
        time.sleep(2)
        btn = _cdp(POSTBTN)
        steps.append({"step": "find post", "result": btn.get("value")})
        b = btn.get("value") or {}
        if not isinstance(b, dict) or not b.get("found"):
            return fail("Post button not found — text typed but NOT sent", network="x", steps=steps)
        steps.append({"step": "click post", "result": _cdp(
            "(function(){const el=document.elementFromPoint(%d,%d); if(!el) return 'none'; el.click(); return el.tagName})()"
            % (b["x"], b["y"])).get("value")})
        time.sleep(7)
        return ok(network="x", mode="logged-in browser", steps=steps)
