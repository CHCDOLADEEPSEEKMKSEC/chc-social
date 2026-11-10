"""Plain-python tests (no pytest needed): python3 tests/test_core.py"""
import json, os, sys, tempfile, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("CHC_SOCIAL_DB", str(ROOT / "tests" / "tmp_queue.db"))
os.environ.setdefault("CHC_ALLOW_UNSIGNED_LEDGER", "1")
os.environ["CHC_VAULT"] = str(ROOT / "tests" / "fakevault")
os.environ["CHC_SOCIAL_RECIPES"] = str(ROOT / "tests" / "tmp_recipes.json")
pathlib.Path(os.environ["CHC_SOCIAL_RECIPES"]).unlink(missing_ok=True)

from chc_social import registry, mcp, queue, learn, ledger, drivers

FAILS = []


def check(name, cond, extra=""):
    print(("PASS " if cond else "FAIL ") + name + (("  " + str(extra)[:200]) if extra and not cond else ""))
    if not cond:
        FAILS.append(name)


def test_registry():
    t = registry.table()
    check("registry has 8 networks", len(t) == 8, len(t))
    check("facebook notes pages-only", "PAGES ONLY" in registry.get("facebook")["notes"])
    ready = registry.available({})
    check("no creds => not ready", all(not r["ready"] for r in ready if r["network"] != "browser"))
    ready2 = registry.available({"CHC_TELEGRAM_BOT_TOKEN": "x", "CHC_TELEGRAM_CHAT_ID": "1"})
    check("telegram ready with creds", any(r["network"] == "telegram" and r["ready"] for r in ready2))


def test_mcp_handshake():
    out = mcp.handle({"jsonrpc": "2.0", "id": 1, "method": "initialize"})
    check("initialize returns serverInfo", out["result"]["serverInfo"]["name"] == "chc-social")
    tl = mcp.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    names = [t["name"] for t in tl["result"]["tools"]]
    check("tools/list has 10 tools", len(names) == 10, names)
    check("notification returns None", mcp.handle({"method": "notifications/initialized"}) is None)
    unknown = mcp.handle({"jsonrpc": "2.0", "id": 3, "method": "nope"})
    check("unknown method -> -32601", unknown["error"]["code"] == -32601)
    bad = mcp.handle({"jsonrpc": "2.0", "id": 4, "method": "tools/call",
                      "params": {"name": "social_post", "arguments": {"network": "nope", "text": "x"}}})
    body = json.loads(bad["result"]["content"][0]["text"])
    check("unknown network fails loudly", body["ok"] is False, body)


def test_drivers_dry_run():
    tg = drivers.load("telegram", dry_run=True)
    res = tg.post("hello", chat_id="123")
    check("telegram dry-run builds request", res.get("ok") and res["request"]["body"]["text"] == "hello", dict(res))
    ig = drivers.load("graph_instagram", dry_run=True)
    res2 = ig.post("no media")
    check("instagram rejects text-only", res2.get("ok") is False, dict(res2))
    x = drivers.load("x", dry_run=True)
    check("x enforces 280", x.post("a" * 300).get("ok") is False)
    fb = drivers.load("graph_page", dry_run=True)
    res3 = fb.post("page post")
    check("facebook dry-run builds a page request", res3.get("ok") is True, dict(res3))
    live = drivers.load("graph_page", dry_run=False)
    res4 = live.post("page post")
    check("facebook live without creds fails loudly", res4.get("ok") is False, dict(res4))


def test_queue():
    j = queue.add("telegram", "queued hello", in_seconds=-1)
    check("queue add", j["ok"] and j["id"] > 0, j)
    d = queue.due()
    check("queue due finds it", any(x["id"] == j["id"] for x in d), d)
    queue.mark(j["id"], "sent", {"ok": True})
    check("queue mark", all(x["id"] != j["id"] for x in queue.due()))


def test_learning():
    rec = learn.absorb_from_dom("x", "https://x.com", "div[contenteditable='true'] and button[type='submit']")
    check("absorb from DOM gives selectors", bool(rec["composer_selector"]), rec)
    check("learned recipes start unverified", rec["verified"] is False)
    saved = learn.save(rec, note="test")
    check("save bumps version", saved["recipe"]["version"] == 1, saved["recipe"])
    again = learn.save(rec, note="test 2")
    check("save bumps version again", again["recipe"]["version"] == 2)
    got = learn.get("x")
    check("recipe round-trips", got["network"] == "x" and got["version"] == 2)


def test_ledger():
    r = ledger.record("social-selftest", "unit test", {"ok": True})
    check("ledger writes somewhere", r["ok"] is True, r)


def test_stdio():
    import io
    inp = io.StringIO('\n'.join([
        json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize"}),
        json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}),
        "not json",
    ]) + "\n")
    out = io.StringIO()
    mcp.serve(inp, out)
    lines = [json.loads(l) for l in out.getvalue().strip().split("\n")]
    check("stdio: 3 replies", len(lines) == 3, len(lines))
    check("stdio: parse error reported", lines[-1]["error"]["code"] == -32700)
    check("stdio: tools listed", len(lines[1]["result"]["tools"]) == 10)


if __name__ == "__main__":
    for fn in (test_registry, test_mcp_handshake, test_drivers_dry_run, test_queue,
               test_learning, test_ledger, test_stdio):
        print("--", fn.__name__)
        fn()
    print()
    if FAILS:
        print("%d FAILURES: %s" % (len(FAILS), FAILS)); sys.exit(1)
    print("ALL TESTS PASSED")
