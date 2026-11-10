from .base import Driver, Result, ok, fail
from . import (telegram, discord, graph_page, graph_instagram, x, x_browser,
               whatsapp_cloud, soundcloud, browser, fb_browser)

DRIVERS = {
    "telegram": telegram.Telegram,
    "discord": discord.Discord,
    "graph_page": graph_page.FacebookPage,
    "graph_instagram": graph_instagram.Instagram,
    "x": x.X,
    "x_browser": x_browser.XBrowser,
    "whatsapp_cloud": whatsapp_cloud.WhatsApp,
    "soundcloud": soundcloud.SoundCloud,
    "browser": browser.Browser,
    "fb_browser": fb_browser.FacebookBrowser,
}


def load(name, **kw):
    cls = DRIVERS.get(name)
    if not cls:
        raise KeyError("unknown driver %r (have: %s)" % (name, ", ".join(sorted(DRIVERS))))
    return cls(**kw)
