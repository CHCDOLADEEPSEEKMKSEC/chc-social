"""Command line: same powers as the MCP, for humans and cron."""
import argparse, json, sys
from . import registry, queue as q, learn, ledger, drivers, mcp


def main(argv=None):
    ap = argparse.ArgumentParser(prog="chc_social", description="CHC SOCIAL — multi-network posting with a ledger")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("networks", help="list networks + readiness")
    sub.add_parser("recipes", help="list learned recipes")

    p = sub.add_parser("post", help="post now")
    p.add_argument("network"); p.add_argument("text"); p.add_argument("--media"); p.add_argument("--dry-run", action="store_true")

    r = sub.add_parser("read", help="read recent items")
    r.add_argument("network"); r.add_argument("--limit", type=int, default=10)

    s = sub.add_parser("schedule", help="queue a post")
    s.add_argument("network"); s.add_argument("text"); s.add_argument("--in", dest="in_seconds", type=int, default=0)
    s.add_argument("--media")

    d = sub.add_parser("queue", help="list or drain queue")
    d.add_argument("--drain", action="store_true"); d.add_argument("--state")

    lr = sub.add_parser("learn", help="propose a recipe for any site")
    lr.add_argument("network"); lr.add_argument("url"); lr.add_argument("--save", action="store_true")
    lr.add_argument("--dom-text", help="learn offline from a saved DOM/text snapshot")

    dl = sub.add_parser("delete", help="delete a post by id")
    dl.add_argument("network"); dl.add_argument("id"); dl.add_argument("--dry-run", action="store_true")
    sub.add_parser("whoami", help="show which account each network's credentials belong to").add_argument(
        "network", nargs="?", default="all")

    sub.add_parser("mcp", help="run the MCP server on stdio")
    sub.add_parser("selftest", help="prove the ledger works")

    a = ap.parse_args(argv)
    if a.cmd == "networks":
        for row in registry.table():
            st = next(x for x in registry.available() if x["network"] == row["network"])
            print("%-14s %-5s %-44s %s" % (row["network"], "READY" if st["ready"] else "need",
                                           ",".join(row["caps"]),
                                           "" if st["ready"] else "missing " + ",".join(st["missing"])))
        return 0
    if a.cmd == "post":
        out = mcp.call("social_post", {"network": a.network, "text": a.text,
                                       "media": a.media, "dry_run": a.dry_run})
    elif a.cmd == "read":
        out = mcp.call("social_read", {"network": a.network, "limit": a.limit})
    elif a.cmd == "schedule":
        out = mcp.call("social_schedule", {"network": a.network, "text": a.text,
                                           "in_seconds": a.in_seconds, "media": a.media})
    elif a.cmd == "queue":
        out = mcp.call("social_queue", {"drain": a.drain, "state": a.state})
    elif a.cmd == "learn":
        out = mcp.call("social_learn", {"network": a.network, "url": a.url,
                                        "save": a.save, "dom_text": a.dom_text})
    elif a.cmd == "delete":
        out = mcp.call("social_delete", {"network": a.network, "id": a.id, "dry_run": a.dry_run})
    elif a.cmd == "whoami":
        nets = [a.network] if a.network and a.network != "all" else list(registry.REGISTRY)
        out = {"ok": True, "accounts": {n: mcp.call("social_account", {"network": n}) for n in nets
                                        if hasattr(drivers.load(registry.REGISTRY[n]["driver"]), "account")}}
    elif a.cmd == "recipes":
        out = mcp.call("social_recipes", {})
    elif a.cmd == "selftest":
        out = mcp.call("social_ledger_selftest", {})
    elif a.cmd == "mcp":
        mcp.serve(); return 0
    else:
        return 2
    print(json.dumps(out, indent=1))
    return 0 if out.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
