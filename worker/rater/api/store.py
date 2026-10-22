"""SQLite-backed job store (survives restarts; safe across threads)."""
from __future__ import annotations

import json
import sqlite3
import threading
import time
import uuid


class JobStore:
    def __init__(self, path: str):
        self._lock = threading.Lock()
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.execute("""CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, status TEXT, stage TEXT, progress REAL,
                           message TEXT, client TEXT, created REAL, updated REAL, report TEXT)""")
        self.db.execute("UPDATE jobs SET status='failed', message='Worker restarted during processing' WHERE status IN ('queued','running')")
        self.db.commit()

    def create(self, client: str) -> str:
        jid = uuid.uuid4().hex[:16]
        now = time.time()
        with self._lock:
            self.db.execute("INSERT INTO jobs VALUES (?,?,?,?,?,?,?,?,?)", (jid, "queued", "queued", 0.0, "", client, now, now, None))
            self.db.commit()
        return jid

    def update(self, jid: str, **kw) -> None:
        if "report" in kw and kw["report"] is not None:
            kw["report"] = json.dumps(kw["report"])
        kw["updated"] = time.time()
        cols = ", ".join(f"{k}=?" for k in kw)
        with self._lock:
            self.db.execute(f"UPDATE jobs SET {cols} WHERE id=?", (*kw.values(), jid))
            self.db.commit()

    def get(self, jid: str) -> dict | None:
        with self._lock:
            row = self.db.execute("SELECT id,status,stage,progress,message,created,updated,report FROM jobs WHERE id=?", (jid,)).fetchone()
        if not row:
            return None
        keys = ["id", "status", "stage", "progress", "message", "created", "updated", "report"]
        d = dict(zip(keys, row, strict=True))
        d["report"] = json.loads(d["report"]) if d["report"] else None
        return d

    def active_for(self, client: str) -> int:
        with self._lock:
            return self.db.execute("SELECT COUNT(*) FROM jobs WHERE client=? AND status IN ('queued','running')", (client,)).fetchone()[0]

    def queue_position(self, jid: str) -> int:
        with self._lock:
            row = self.db.execute("SELECT created FROM jobs WHERE id=?", (jid,)).fetchone()
            if not row:
                return 0
            return self.db.execute("SELECT COUNT(*) FROM jobs WHERE status='queued' AND created < ?", (row[0],)).fetchone()[0]
