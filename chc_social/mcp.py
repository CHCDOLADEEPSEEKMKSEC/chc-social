"""The MCP server. JSON-RPC 2.0 over stdio — works with any MCP client.

Tools:
  social_networks      — what we can do, per network, honestly
  social_post          — post to one network (or several with 'all')
  social_read          — read recent items
  social_schedule      — queue a post for later
  social_queue         — list or drain the queue
  social_learn         — propose/absorb/verify a browser recipe for any site
  social_recipes       — list learned recipes
  social_ledger_selftest — prove the signed ledger works
"""
import json, sys, traceback

from . import registry, queue, learn, ledger, drivers

TOOLS = [
    {"name": "social_networks", "description": "List networks, capabilities and whether credentials are present.",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "social_post", "description": "Post text (and optional media) to one network, or 'all'.",
     "inputSchema": {"type": "object", "properties": {
         "network": {"type": "string"}, "text": {"type": "string"},
         "media": {"type": "string"}, "dry_run": {"type": "boolean"}}, "required": ["network", "text"]}},
    {"name": "social_read", "description": "Read recent posts/messages from a network.",
     "inputSchema": {"type": "object", "properties": {
         "network": {"type": "string"}, "limit": {"type": "integer"}}, "required": ["network"]}},
    {"name": "social_schedule", "description": "Queue a post for a future time.",
     "inputSchema": {"type": "object", "properties": {
         "network": {"type": "string"}, "text": {"type": "string"},
         "in_seconds": {"type": "integer"}, "due": {"type": "integer"},
         "media": {"type": "string"}}, "required": ["network", "text"]}},
    {"name": "social_queue", "description": "List queued jobs, or drain the ones that are due.",
     "inputSchema": {"type": "object", "properties": {
         "drain": {"type": "boolean"}, "state": {"type": "string"}}}},
    {"name": "social_learn", "description": "Learn (or verify) how to post on any site via the browser.",
     "inputSchema": {"type": "object", "properties": {
         "network": {"type": "string"}, "url": {"type": "string"},
         "dom_text": {"type": "string"}, "save": {"type": "boolean"}},
         "required": ["network", "url"]}},
    {"name": "social_recipes", "description": "List learned recipes and their version/confidence.",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "social_delete", "description": "Delete a post/message by id (network-dependent).",
     "inputSchema": {"type": "object", "properties": {
         "network": {"type": "string"}, "id": {"type": "string"},
         "dry_run": {"type": "boolean"}}, "required": ["network", "id"]}},
    {"name": "social_account", "description": "Prove which account/identity the credentials belong to.",
     "inputSchema": {"type": "object", "properties": {"network": {"type": "string"}},
                     "required": ["network"]}},
    {"name": "social_ledger_selftest", "description": "Append a test receipt and report where it went.",
     "inputSchema": {"type": "object", "properties": {}}},
]


def _post(args):
    net = args["network"]
    text = args["text"]
    dry = bool(args.get("dry_run"))
    media = args.get("media")
    if net == "all":
        out = {}
        for n, spec in registry.REGISTRY.items():
            if "post" not in spec["caps"]:
                continue
            out[n] = _post({"network": n, "text": text, "media": media, "dry_run": dry})
        return {"ok": True, "results": out}
    spec = registry.get(net)
    if not spec:
        return {"ok": False, "error": "unknown network %r" % net}
    if "post" not in spec["caps"]:
        return {"ok": False, "error": "%s cannot post (caps: %s)" % (net, spec["caps"])}
    drv = drivers.load(spec["driver"], dry_run=dry)
    res = drv.post(text, media=media)
    led = ledger.record("social-post", "%s post (%s)" % (net, "dry-run" if dry else "live"),
                        {"network": net, "text": text[:500], "media": media,
                         "result": dict(res)})
    return {"ok": bool(res.get("ok")), "network": net, "result": dict(res), "ledger": led}


def _read(args):
    spec = registry.get(args["network"])
    if not spec:
        return {"ok": False, "error": "unknown network"}
    drv = drivers.load(spec["driver"])
    return dict(drv.read(limit=int(args.get("limit") or 10)))


def _learn(args):
    net = args["network"]
    url = args["url"]
    if args.get("dom_text"):
        rec = learn.absorb_from_dom(net, url, args["dom_text"])
    else:
        rec = learn.propose(net, url)
    if args.get("save") and rec.get("confidence", 0) > 0:
        saved = learn.save(rec, note="proposed by agent")
        return {"ok": True, "draft": rec, "saved": saved}
    return {"ok": True, "draft": rec, "saved": None,
            "next": "review the selectors, then call social_learn again with save=true"}


def call(name, args):
    args = args or {}
    if name == "social_networks":
        return {"ok": True, "networks": registry.table(), "ready": registry.available()}
    if name == "social_post":
        return _post(args)
    if name == "social_read":
        return _read(args)
    if name == "social_schedule":
        return queue.add(args["network"], args["text"], due=args.get("due"),
                         media=args.get("media"), in_seconds=args.get("in_seconds"))
    if name == "social_queue":
        if args.get("drain"):
            done = []
            for job in queue.due():
                spec = registry.get(job["network"])
                if not spec:
                    queue.mark(job["id"], "failed", {"error": "unknown network"})
                    continue
                drv = drivers.load(spec["driver"])
                res = drv.post(job["body"], media=job.get("media"))
                queue.mark(job["id"], "sent" if res.get("ok") else "failed", dict(res))
                ledger.record("social-queue", "%s queued post" % job["network"],
                              {"job": job["id"], "result": dict(res)})
                done.append({"job": job["id"], "ok": bool(res.get("ok"))})
            return {"ok": True, "drained": done}
        return {"ok": True, "jobs": queue.listing(args.get("state"))}
    if name == "social_learn":
        return _learn(args)
    if name == "social_recipes":
        return {"ok": True, "recipes": learn.all_recipes()}
    if name == "social_delete":
        spec = registry.get(args["network"])
        if not spec:
            return {"ok": False, "error": "unknown network %r" % args["network"]}
        if "delete" not in spec["caps"]:
            return {"ok": False, "error": "%s cannot delete (caps: %s) — say so, do not pretend"
                    % (args["network"], spec["caps"])}
        drv = drivers.load(spec["driver"], dry_run=bool(args.get("dry_run")))
        res = drv.delete(args["id"])
        led = ledger.record("social-delete", "%s delete" % args["network"],
                            {"network": args["network"], "id": args["id"], "result": dict(res)})
        return {"ok": bool(res.get("ok")), "network": args["network"],
                "result": dict(res), "ledger": led}
    if name == "social_account":
        spec = registry.get(args["network"])
        if not spec:
            return {"ok": False, "error": "unknown network %r" % args["network"]}
        if not hasattr(drivers.load(spec["driver"]), "account"):
            return {"ok": False, "error": "%s driver has no identity check" % args["network"]}
        res = drivers.load(spec["driver"]).account()
        ledger.record("social-account", "%s identity check" % args["network"],
                      {"network": args["network"], "result": dict(res)})
        return {"ok": bool(res.get("ok")), "network": args["network"], "result": dict(res)}
    if name == "social_ledger_selftest":
        return {"ok": True, "ledger": ledger.record("social-selftest", "ledger selftest", {"ok": True})}
    raise KeyError("unknown tool %r" % name)


def handle(msg):
    """One JSON-RPC message in, one dict out (or None for notifications)."""
    mid = msg.get("id")
    method = msg.get("method")
    params = msg.get("params") or {}
    try:
        if method == "initialize":
            res = {"protocolVersion": "2024-11-05",
                   "capabilities": {"tools": {"listChanged": False}},
                   "serverInfo": {"name": "chc-social", "version": "0.1.0",
                                  "vendor": "CHC / Mirage Intelligence"}}
        elif method == "tools/list":
            res = {"tools": TOOLS}
        elif method == "tools/call":
            res = {"content": [{"type": "text", "text": json.dumps(
                call(params.get("name"), params.get("arguments")), indent=1)}]}
        elif method in ("notifications/initialized", "initialized"):
            return None
        elif method == "ping":
            res = {}
        else:
            return {"jsonrpc": "2.0", "id": mid,
                    "error": {"code": -32601, "message": "method not found: %s" % method}}
        return {"jsonrpc": "2.0", "id": mid, "result": res}
    except Exception as e:
        return {"jsonrpc": "2.0", "id": mid,
                "error": {"code": -32000, "message": str(e)[:400],
                          "data": traceback.format_exc()[-800:] if os_debug() else None}}


def os_debug():
    import os
    return os.environ.get("CHC_SOCIAL_DEBUG") == "1"


def serve(stdin=None, stdout=None):
    stdin = stdin or sys.stdin
    stdout = stdout or sys.stdout
    for line in stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except Exception:
            stdout.write(json.dumps({"jsonrpc": "2.0", "id": None,
                                     "error": {"code": -32700, "message": "parse error"}}) + "\n")
            stdout.flush()
            continue
        out = handle(msg)
        if out is not None:
            stdout.write(json.dumps(out) + "\n")
            stdout.flush()


if __name__ == "__main__":
    serve()
