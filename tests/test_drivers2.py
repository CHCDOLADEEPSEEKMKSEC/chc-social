"""Tests for the v0.2.0 drivers: browser modes, soundcloud, instagram, whatsapp."""
import json, os, pathlib, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["CHC_SOCIAL_DB"] = str(ROOT / "tests" / "tmp_queue2.db")
os.environ["CHC_VAULT"] = "/tmp/fakevault_noseal"

from chc_social import drivers, registry

FAILS = []


def check(name, cond, extra=""):
    print(("PASS " if cond else "FAIL ") + name + (("  " + str(extra)[:160]) if extra and not cond else ""))
    if not cond:
        FAILS.append(name)


def test_registration():
    check("10 drivers registered", len(drivers.DRIVERS) == 10, len(drivers.DRIVERS))
    check("fb_browser registered", "fb_browser" in drivers.DRIVERS)
    check("x_browser registered", "x_browser" in drivers.DRIVERS)
    check("facebook browser fallback points at fb_browser",
          registry.get("facebook")["browser_fallback"] == "fb_browser")
    check("x browser fallback points at x_browser", registry.get("x")["browser_fallback"] == "x_browser")


def test_fb_browser_dry():
    d = drivers.load("fb_browser", dry_run=True)
    r = d.post("hello profiles", target_url="https://www.facebook.com/groups/123")
    check("fb dry-run reports target", r["ok"] and r["would_navigate"].endswith("/123"), dict(r))
    check("fb dry-run does not touch the browser", r.get("steps") == [], r.get("steps"))


def test_x_browser():
    d = drivers.load("x_browser", dry_run=True)
    check("x browser dry-run ok", d.post("hi").get("ok") is True)
    check("x browser blocks >280", d.post("a" * 300).get("ok") is False)


def test_instagram():
    d = drivers.load("graph_instagram", dry_run=True)
    check("ig dry-run image", d.post("cap", media="https://x/y.jpg").get("ok") is True)
    check("ig dry-run carousel", d.post("cap", carousel="https://a,https://b").get("ok") is True)
    check("ig dry-run reel", d.post("cap", reel="https://x/v.mp4").get("ok") is True)
    check("ig carousel needs 2+", d.post("cap", carousel="https://a").get("ok") is False)
    check("ig text-only refused", d.post("just text").get("ok") is False)


def test_whatsapp_media():
    os.environ["CHC_WA_TOKEN"] = "t"; os.environ["CHC_WA_PHONE_ID"] = "p"; os.environ["CHC_WA_TO"] = "44123"
    d = drivers.load("whatsapp_cloud", dry_run=True)
    r = d.post("look", media="https://x/pic.jpg")
    check("wa media -> image type", r["ok"] and r["request"]["body"]["type"] == "image", json.dumps(r)[:200])
    for k in ("CHC_WA_TOKEN", "CHC_WA_PHONE_ID", "CHC_WA_TO"):
        os.environ.pop(k, None)


def test_soundcloud():
    d = drivers.load("soundcloud", dry_run=True)
    check("sc without creds fails loudly", d.post("t", media="/tmp/x.mp3").get("ok") is False)
    os.environ["CHC_SC_TOKEN"] = "t"; os.environ["CHC_SC_CLIENT_ID"] = "c"
    d = drivers.load("soundcloud", dry_run=True)
    tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False); tmp.write(b"ID3" + b"0" * 100); tmp.close()
    r = d.post("track title\ndesc", media=tmp.name)
    check("sc dry-run reports bytes", r["ok"] and r["bytes"] > 100, dict(r))
    check("sc missing file fails loudly", d.post("t", media="/nope/x.mp3").get("ok") is False)
    os.unlink(tmp.name)
    for k in ("CHC_SC_TOKEN", "CHC_SC_CLIENT_ID"):
        os.environ.pop(k, None)


def test_scheduler_assets():
    base = ROOT / "deploy"
    check("drain service exists", (base / "chc-social-drain.service").is_file())
    check("drain timer exists", (base / "chc-social-drain.timer").is_file())
    check("timer is every 2 min", "OnUnitActiveSec=2min" in (base / "chc-social-drain.timer").read_text())
    check("installer is executable", os.access(base / "install.sh", os.X_OK))
    check("pyproject declares entry point", "chc-social = " in (ROOT / "pyproject.toml").read_text())
    check("licence is source-available not MIT", "SOURCE-AVAILABLE" in (ROOT / "LICENSE").read_text())


if __name__ == "__main__":
    for fn in (test_registration, test_fb_browser_dry, test_x_browser, test_instagram,
               test_whatsapp_media, test_soundcloud, test_scheduler_assets):
        print("--", fn.__name__)
        fn()
    print()
    if FAILS:
        print("%d FAILURES: %s" % (len(FAILS), FAILS)); sys.exit(1)
    print("ALL DRIVER TESTS PASSED")
