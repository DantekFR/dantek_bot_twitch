from __future__ import annotations

try:
    import sqlite3
    import threading
    import time
    from pathlib import Path

except ModuleNotFoundError as e:
    print(f"[ERREUR] Le module est introuvable : {e}")
    raise RuntimeError(
        "Impossible de démarrer l'application."
    )

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DB = ROOT / "data" / "dantek_bot.db"

class Database:
    def __init__(self, db_path: str | Path | None = None) -> None:
        self.path = Path(db_path) if db_path is not None else DEFAULT_DB
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self.conn = sqlite3.connect(str(self.path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        self.conn.execute("PRAGMA busy_timeout=5000")
        self._migrate()

    def _migrate(self) -> None:
        with self._lock:
            self.conn.executescript("""
                CREATE TABLE IF NOT EXISTS channel_facts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT UNIQUE NOT NULL,
                    value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS ai_conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    viewer_id TEXT NOT NULL,
                    viewer TEXT NOT NULL,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    created_at INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS viewer_memory (
                    viewer_id TEXT PRIMARY KEY,
                    viewer TEXT NOT NULL,
                    facts TEXT NOT NULL DEFAULT '',
                    updated_at INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    channel_id TEXT NOT NULL,
                    viewer_id TEXT NOT NULL,
                    viewer TEXT NOT NULL,
                    text TEXT NOT NULL,
                    created_at INTEGER NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_conv_viewer
                    ON ai_conversations (viewer_id, created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_chat_channel
                    ON chat_messages (channel_id, id DESC);
                CREATE INDEX IF NOT EXISTS idx_chat_viewer
                    ON chat_messages (viewer_id, id DESC);
            """)
            self.conn.commit()
        
    def upsert_fact(self, key: str, value: str) -> None:
        with self._lock:
            self.conn.execute(
                "INSERT INTO channel_facts (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, value),
            )
            self.conn.commit()

    def facts_text(self) -> str:
        with self._lock:
            rows = self.conn.execute(
                "SELECT key, value FROM channel_facts"
            ).fetchall()
        return "\n".join(f" - {r['key']} : {r['value']}" for r in rows)

    def set_viewer_facts(self, viewer_id: str, viewer: str, facts: str) -> None:
        facts = (facts or "").strip()[:1000]
        now = int(time.time())
        with self._lock:
            self.conn.execute(
                "INSERT INTO viewer_memory (viewer_id, viewer, facts, updated_at) "
                "VALUES (?, ?, ?, ?) "
                "ON CONFLICT(viewer_id) DO UPDATE SET "
                "viewer=excluded.viewer, facts=excluded.facts, updated_at=excluded.updated_at",
                (str(viewer_id), str(viewer), facts, now),
            )
            self.conn.commit()

    def get_viewer_facts(self, viewer_id: str) -> str:
        with self._lock:
            row = self.conn.execute(
                "SELECT facts FROM viewer_memory WHERE viewer_id=?", (str(viewer_id),)
            ).fetchone()
        return (row["facts"] if row else "") or ""

    def log_chat_message(self, channel_id: str, viewer_id: str, viewer: str, text: str) -> None:
        text = (text or "").strip()[:500]
        if not text:
            return
        now = int(time.time())
        with self._lock:
            self.conn.execute(
                "INSERT INTO chat_messages (channel_id, viewer_id, viewer, text, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (str(channel_id or ""), str(viewer_id or ""), str(viewer or "viewer"), text, now),
            )
            self.conn.commit()
    
    def recent_chat_text(self, channel_id: str, limit: int = 20) -> str:
        limit = max(1, min(int(limit or 20), 20))
        with self._lock:
            rows = self.conn.execute(
                "SELECT viewer, text FROM chat_messages "
                "WHERE channel_id=? AND viewer != 'dantekos_bot' "
                "ORDER BY id DESC LIMIT ?",
                (str(channel_id or ""), limit),
            ).fetchall()
        lines = []
        for r in reversed(rows):
            v = (r["viewer"] or "viewer").strip()[:40]
            t = (r["text"] or "").strip()[:120]
            if t:
                lines.append(f"{v}: {t}")
        return "\n".join(lines)[:800]

    def search_chat(self, query: str, limit: int = 10) -> list[str]:
        query = (query or "").strip()[:100]
        if not query:
            return []
        limit = max(1, min(int(limit or 10), 20))
        with self._lock:
            rows = self.conn.execute(
                "SELECT viewer, text FROM chat_messages "
                "WHERE text LIKE ? ODER BY id DESC LIMIT ?",
                (f"%{query}%", limit),
            ).fetchall()
        return [f"{(r['viewer'] or 'viewer')}: {(r['text'] or '')[:160]}" for r in rows]

    def log_exchange(self, viewer_id: str, viewer: str, question: str, answer: str) -> None:
        question = (question or '').strip()[:500]
        answer = (answer or '').strip()[:500]
        now = int(time.time())
        with self._lock:
            self.conn.execute(
                "INSERT INTO ai_conversations (viewer_id, viewer, question, answer, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (str(viewer_id), str(viewer), question, answer, now),
            )
            self.conn.commit()

    def recent_exchanges(self, viewer_id: str, limit: int = 20) -> list[str]:
        limit = max(1, min(int(limit or 20), 50))
        with self._lock:
            rows = self.conn.execute(
                "SELECT viewer, question, answer FROM ai_conversations "
                "WHERE viewer_id=? ORDER BY created_at DESC LIMIT ?",
                (str(viewer_id), limit),
            ).fetchall()
        return [ f"{r['viewer']} a demandé : {r['question']} -> {r['answer']}" for r in reversed(rows)]

    def close(self) -> None:
        try:
            with self._lock:
                self.conn.close()
        except Exception:
            pass