"""Signed action ledger. Uses the house seal tool if present; never swallows errors."""
import json, os, pathlib, subprocess, time, hashlib

VAULT = pathlib.Path(os.environ.get("CHC_VAULT", "/mnt/ledger/vault"))
SEAL = VAULT / "tools" / "seal.py"
FALLBACK = pathlib.Path(os.environ.get("CHC_SOCIAL_LEDGER", "/tmp/chc_social_ledger.jsonl"))


def record(kind, subject, data):
    """Append one signed receipt. Returns dict with ok + where."""
    payload = json.dumps(data, sort_keys=True)
    if SEAL.is_file():
        budget = float(os.environ.get("CHC_SOCIAL_LEDGER_TIMEOUT", "90"))
        try:
            r = subprocess.run(["python3", str(SEAL), "append", "--kind", kind,
                                "--subject", subject, "--data", payload],
                               capture_output=True, text=True, timeout=budget)
            if r.returncode == 0:
                return {"ok": True, "sink": str(SEAL), "seq": _seq(r.stdout)}
            # a broken chain must not lose the record: keep it, and say plainly it is unsigned
            return _unsigned(kind, subject, data, warning="seal failed: " + r.stderr.strip()[:200])
        except Exception as e:
            # a hung or broken chain must not swallow the record either
            return _unsigned(kind, subject, data, warning="seal unavailable: %s" % str(e)[:200])
    return _unsigned(kind, subject, data)


def _unsigned(kind, subject, data, warning=None):
    """Self-hashed fallback record. Never silent: the caller gets sink + warning."""
    rec = {"ts": time.time(), "kind": kind, "subject": subject, "data": data}
    if warning:
        rec["warning"] = warning
    rec["sha256"] = hashlib.sha256(json.dumps(rec, sort_keys=True).encode()).hexdigest()
    FALLBACK.parent.mkdir(parents=True, exist_ok=True)
    with FALLBACK.open("a") as f:
        f.write(json.dumps(rec) + "\n")
    out = {"ok": True, "sink": str(FALLBACK), "unsigned": True}
    if warning:
        out["warning"] = warning
    return out


def _seq(out):
    try:
        return json.loads(out).get("seq")
    except Exception:
        return None
