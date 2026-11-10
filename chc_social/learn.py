"""Learning layer — absorb a new network by observation, not by hardcoding.

A recipe is a small JSON document describing how to post/read on one site:
  {name, network, url, composer_selector, send_selector, read_selector,
   learned_from, confidence, probes: [...], version, ts}

`propose()` looks at a live page over CDP and GUESSES selectors, scoring candidates.
`save()` stores it with a version bump. Every save is signed into the ledger.
Nothing is ever claimed as "working" until a real post returns steps with no error.
"""
import json, os, pathlib, time

STORE = pathlib.Path(os.environ.get("CHC_SOCIAL_RECIPES",
                                    os.path.expanduser("~/.chc-social/recipes.json")))
HEURISTICS = {
    "composer_selector": [
        "div[contenteditable='true'][role='textbox']",
        "div[contenteditable='true']",
        "textarea[aria-label]",
        "textarea",
        "[data-testid*='tweetTextarea']",
        "[aria-label*='post' i]",
    ],
    "send_selector": [
        "div[role='button'][aria-label*='Post' i]",
        "button[type='submit']",
        "[data-testid*='tweetButton']",
        "button[aria-label*='send' i]",
        "input[type='submit']",
    ],
    "read_selector": ["article", "[role='article']", "div[data-testid*='cellInnerDiv']"],
}


def _load():
    if STORE.is_file():
        try:
            return json.loads(STORE.read_text())
        except Exception:
            return {}
    return {}


def _save(db):
    STORE.parent.mkdir(parents=True, exist_ok=True)
    tmp = STORE.with_suffix(".tmp")
    tmp.write_text(json.dumps(db, indent=1, sort_keys=True))
    tmp.replace(STORE)


def get(network):
    return _load().get(network)


def all_recipes():
    return _load()


def save(recipe, note=""):
    from . import ledger
    db = _load()
    prev = db.get(recipe["network"]) or {}
    recipe["version"] = int(prev.get("version", 0)) + 1
    recipe["ts"] = time.time()
    db[recipe["network"]] = recipe
    _save(db)
    rec = ledger.record("social-recipe", "learned recipe %s v%d" % (recipe["network"], recipe["version"]),
                        {"recipe": recipe, "note": note})
    return {"ok": True, "recipe": recipe, "ledger": rec}


def propose(network, url, probe=None):
    """Score candidate selectors against the live page and return a draft recipe."""
    from .drivers import browser as bmod
    probe = probe or HEURISTICS
    result = {}
    for key, candidates in probe.items():
        found = None
        for sel in candidates:
            r = bmod._cdp("(function(){const n=document.querySelectorAll(%s);"
                          "return {count:n.length, visible:[...n].filter(e=>e.getBoundingClientRect().width>50).length}})()"
                          % json.dumps(sel))
            v = r.get("value") or {}
            if isinstance(v, dict) and v.get("count"):
                found = {"selector": sel, "matches": v["count"], "visible": v.get("visible", 0)}
                break
        result[key] = found
    confidence = sum(1 for v in result.values() if v) / max(1, len(result))
    return {"network": network, "url": url, "learned_from": "live DOM probe",
            "confidence": round(confidence, 2), "selectors": result,
            "composer_selector": (result.get("composer_selector") or {}).get("selector"),
            "send_selector": (result.get("send_selector") or {}).get("selector"),
            "read_selector": (result.get("read_selector") or {}).get("selector"),
            "verified": False}


def absorb_from_dom(network, url, dom_snapshot_text):
    """Offline learning: infer selectors from a saved DOM/screenshot text.

    Used when no live browser is available. Always low confidence, always marked unverified.
    """
    t = (dom_snapshot_text or "").lower()
    hints = []
    for key, cands in HEURISTICS.items():
        for sel in cands:
            token = sel.split("[")[0].replace("'", "")
            if token in t:
                hints.append({"key": key, "selector": sel})
                break
    rec = {"network": network, "url": url, "learned_from": "offline DOM text",
           "confidence": 0.3 if hints else 0.0, "selectors": hints, "verified": False,
           "composer_selector": next((h["selector"] for h in hints if h["key"] == "composer_selector"), None),
           "send_selector": next((h["selector"] for h in hints if h["key"] == "send_selector"), None),
           "read_selector": next((h["selector"] for h in hints if h["key"] == "read_selector"), None)}
    return rec
