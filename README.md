# CHC SOCIAL v0.2.0

**One MCP server. Every network. A signed receipt for every action.**

Built because every existing social MCP is one of two things: a hosted service that wants
your accounts behind their OAuth, or a Facebook-Pages-only wrapper. We wanted one server we
own, that tells the truth about what each network can actually do, learns the ones with no
usable API, and records every action in an append-only signed chain.

## Networks

| network | post | read | media | auth | the honest bit |
|---|---|---|---|---|---|
| telegram | ✅ | ✅ | ✅ | bot token | Real public API, free, no review. Best first channel. |
| discord | ✅ | – | ✅ | webhook URL | Webhook posting, no bot registration. |
| facebook | ✅ | ✅ | – | page token | **Pages only** — profiles and groups are not available via Graph. Use `browser` for those. |
| instagram | ✅ | – | ✅ | IG business + page token | Media required; no text-only posts. |
| x | ✅ | – | – | OAuth bearer | API v2 write is a paid tier. `browser` works without it. |
| whatsapp | ✅ | ✅ | – | Cloud API token | Business number + approved templates. Not a personal-account channel. |
| soundcloud | ✅ | – | ⚠️ | OAuth | Comments/reads are easy; audio upload is multipart and **not implemented yet** (it says so). |
| browser | ✅ | ✅ | – | logged-in session | Last resort, driven by **learned recipes**, fragile by nature. |

## What is real, and what is not

- **Telegram, Discord, X (API), Facebook Pages, Instagram, WhatsApp** — real HTTP APIs, implemented against
  the documented endpoints, dry-run mode shows you the exact request before it sends anything.
- **Facebook profiles/groups and X without a paid tier** — real browser drivers, proven on this machine:
  they click what a human clicks and report each step. They break if a site changes its layout; that is
  stated, not hidden.
- **SoundCloud** — real multipart upload (needs an OAuth token with upload scope).
- **The learning layer** — a recipe is only ever called *working* after a real post returns steps with
  no error. Recipes start at `verified: false` and stay there until proven.

Nothing in this repo posts on your behalf without credentials or a logged-in browser you control.

## Scheduler

```bash
sudo deploy/install.sh     # systemd timer, drains the queue every 2 minutes
```

## Install

```bash
git clone <this> && cd chc_social
python3 -m pip install -e .     # no dependencies beyond the standard library
python3 -m chc_social.cli networks
```

## Use as an MCP server

```json
{"mcpServers": {"chc-social": {"command": "python3", "args": ["-m", "chc_social.mcp"]}}}
```

Tools: `social_networks`, `social_post`, `social_read`, `social_schedule`, `social_queue`,
`social_learn`, `social_recipes`, `social_ledger_selftest`.

## Use from the shell

```bash
chc_social networks
chc_social post telegram "hello from the house" --dry-run
chc_social post facebook "page post" --dry-run
chc_social schedule telegram "later" --in 3600
chc_social queue --drain
chc_social learn x https://x.com --save        # probe the live DOM, propose selectors
chc_social recipes
```

## The learning layer

There is no way to give a clean API to a site that has none, so we do the honest thing:
**observe, propose, store, verify.**

1. `social_learn` probes the live page over CDP and scores candidate selectors
   (contenteditable boxes, submit buttons, article containers) by match count and visibility.
2. It returns a **draft recipe** with a confidence score, always `verified: false`.
3. Saving bumps the version and signs a receipt.
4. A recipe is only ever described as working once a real post returns steps with no error.

`absorb_from_dom` does the same offline from a saved DOM/text snapshot, at low confidence.
Recipes are JSON, versioned, and never overwrite history silently.

## The ledger

Every post, queued send, recipe save and selftest appends a receipt. If the house chain is
available (`tools/seal.py`) it is signed and chained. If the chain is unavailable the record
is **still kept**, self-hashed, and marked `unsigned: true` with a warning — a broken chain
must never lose the record.

## Tests

```bash
python3 tests/test_core.py     # 27 checks, no pytest, no network
```

## Licence

Same as the rest of the house: source-available, all rights reserved. Read it, run it
unmodified; do not repackage it.
