"""Capability registry — the honest map of what each network can actually do.

caps: post, read, dm, media, delete, insights
auth: none | token | oauth | session  (session = logged-in browser, no API)
"""
REGISTRY = {
    "telegram": {
        "name": "Telegram", "caps": ["post", "edit", "delete", "read", "media", "account"],
        "auth": "token", "env": ["CHC_TELEGRAM_BOT_TOKEN"],
        "chat_id_env": "CHC_TELEGRAM_CHAT_ID",
        "driver": "telegram",
        "api": "https://api.telegram.org/bot{token}/sendMessage",
        "notes": "Full Bot API: post, edit, delete, pin, getMe identity check. Free, no review.",
    },
    "discord": {
        "name": "Discord", "caps": ["post", "media"],
        "auth": "token", "env": ["CHC_DISCORD_WEBHOOK"],
        "driver": "discord",
        "api": "webhook POST",
        "notes": "Webhook posting, no bot registration needed. Free.",
    },
    "facebook": {
        "name": "Facebook", "caps": ["post", "read", "insights"],
        "auth": "token", "env": ["CHC_FB_PAGE_TOKEN", "CHC_FB_PAGE_ID"],
        "driver": "graph_page",
        "api": "https://graph.facebook.com/v21.0/{page}/feed",
        "notes": "Graph API = PAGES ONLY. Profiles and Groups are not available; use the browser driver for those.",
        "browser_fallback": "fb_browser",
    },
    "instagram": {
        "name": "Instagram", "caps": ["post", "media"],
        "auth": "token", "env": ["CHC_IG_USER_ID", "CHC_FB_PAGE_TOKEN"],
        "driver": "graph_instagram",
        "api": "https://graph.facebook.com/v21.0/{ig}/media",
        "notes": "Business/Creator account required. Image/video posts only, no text-only.",
    },
    "x": {
        "name": "X / Twitter", "caps": ["post", "delete"],
        "auth": "oauth", "env": ["CHC_X_BEARER"],
        "driver": "x",
        "api": "https://api.x.com/2/tweets",
        "notes": "API v2 write needs a paid tier. Browser driver works without it.",
        "browser_fallback": "x_browser",
    },
    "whatsapp": {
        "name": "WhatsApp", "caps": ["post", "read"],
        "auth": "token", "env": ["CHC_WA_TOKEN", "CHC_WA_PHONE_ID"],
        "driver": "whatsapp_cloud",
        "api": "https://graph.facebook.com/v21.0/{phone}/messages",
        "notes": "Cloud API: business number + approved templates. Not a personal-account channel.",
    },
    "soundcloud": {
        "name": "SoundCloud", "caps": ["post", "media"],
        "auth": "oauth", "env": ["CHC_SC_CLIENT_ID", "CHC_SC_TOKEN"],
        "driver": "soundcloud",
        "api": "https://api.soundcloud.com/tracks",
        "notes": "Uploads need the upload endpoint + OAuth token. Comments/reads are easier than uploads.",
        "browser_fallback": "browser",
    },
    "browser": {
        "name": "Any site via logged-in browser", "caps": ["post", "read"],
        "auth": "session", "env": ["CHC_CDP_PORT"],
        "driver": "browser",
        "api": "CDP on loopback",
        "notes": "Last resort for networks with no usable API. Fragile by nature; recipes are learned, not hardcoded.",
    },
}


def get(net):
    return REGISTRY.get(net)


def table():
    return [{"network": k, "caps": v["caps"], "auth": v["auth"], "driver": v["driver"],
             "env": v["env"], "notes": v["notes"]} for k, v in REGISTRY.items()]


def available(env=None):
    import os
    env = env if env is not None else os.environ
    out = []
    for k, v in REGISTRY.items():
        if v["auth"] == "session":
            out.append({"network": k, "ready": True, "missing": []})
            continue
        missing = [e for e in v["env"] if not env.get(e)]
        out.append({"network": k, "ready": not missing, "missing": missing})
    return out
