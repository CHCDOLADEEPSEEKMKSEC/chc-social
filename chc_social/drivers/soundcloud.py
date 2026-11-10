"""SoundCloud — real track upload (multipart) plus comments.

Upload needs an OAuth token with upload scope. The API endpoint takes the raw audio
bytes with the track metadata in the query. If the token lacks the scope, the API
says so and so do we — no pretending it posted.
"""
import json, os, pathlib, urllib.error, urllib.request
from .base import Driver, ok, fail


class SoundCloud(Driver):
    driver = "soundcloud"
    network = "soundcloud"
    caps = ["post", "media"]

    def post(self, text, media=None, **kw):
        try:
            token = self._env("CHC_SC_TOKEN")
            cid = self._env("CHC_SC_CLIENT_ID")
        except KeyError as e:
            return fail("%s — SoundCloud needs OAuth (client id + token)" % e, network="soundcloud")

        if not media:
            return fail("soundcloud needs an audio file path or url (media=...)", network="soundcloud")

        title = (text or "untitled").splitlines()[0][:100]
        description = (text or "")[:1000]

        if media.startswith(("http://", "https://")):
            return fail("audio upload wants a local file, not a URL — fetch it first, then pass the path",
                        network="soundcloud", would_title=title)

        path = pathlib.Path(media).expanduser()
        if not path.is_file():
            return fail("audio file not found: %s" % path, network="soundcloud")

        if self.dry_run:
            return ok(network="soundcloud", dry_run=True, would_upload=str(path),
                      bytes=path.stat().st_size, title=title)

        url = ("https://api.soundcloud.com/tracks?client_id=%s&title=%s&description=%s"
               % (cid, urllib.parse.quote(title), urllib.parse.quote(description)))
        audio = path.read_bytes()
        req = urllib.request.Request(url, data=audio, method="POST",
                                     headers={"Authorization": "OAuth %s" % token,
                                              "Content-Type": "application/octet-stream"})
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                body = json.loads(r.read().decode("utf-8", "replace") or "{}")
                return ok(network="soundcloud", uploaded=True, id=body.get("id"),
                          permalink=body.get("permalink_url"), bytes=len(audio))
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:400]
            return fail("upload rejected: HTTP %s %s" % (e.code, detail), network="soundcloud")
        except Exception as e:
            return fail(str(e)[:400], network="soundcloud")
