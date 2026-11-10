"""Scheduled posts — sqlite queue, drained by `chc_social run-queue` on a timer."""
import json, os, pathlib, sqlite3, time

DB = pathlib.Path(os.environ.get("CHC_SOCIAL_DB", os.path.expanduser("~/.chc-social/queue.db")))


def _c():
    DB.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    c.execute("""create table if not exists jobs(
        id integer primary key autoincrement,
        network text not null, body text not null, media text,
        due integer not null, state text not null default 'pending',
        attempts integer not null default 0, result text, created integer not null)""")
    c.commit()
    return c


def add(network, body, due=None, media=None, in_seconds=None):
    if due is None:
        due = int(time.time()) + int(in_seconds or 0)
    c = _c()
    cur = c.execute("insert into jobs(network,body,media,due,created) values(?,?,?,?,?)",
                    (network, body, media, int(due), int(time.time())))
    c.commit()
    jid = cur.lastrowid
    c.close()
    return {"ok": True, "id": jid, "due": int(due), "network": network}


def due(now=None):
    now = int(now or time.time())
    c = _c()
    rows = c.execute("select * from jobs where state='pending' and due<=? order by due limit 50",
                     (now,)).fetchall()
    c.close()
    return [dict(r) for r in rows]


def mark(job_id, state, result=None):
    c = _c()
    c.execute("update jobs set state=?, attempts=attempts+1, result=? where id=?",
              (state, json.dumps(result)[:4000] if result is not None else None, job_id))
    c.commit()
    c.close()
    return {"ok": True, "id": job_id, "state": state}


def listing(state=None, limit=50):
    c = _c()
    q = "select * from jobs" + (" where state=?" if state else "") + " order by id desc limit ?"
    args = (state, limit) if state else (limit,)
    rows = c.execute(q, args).fetchall()
    c.close()
    return [dict(r) for r in rows]
