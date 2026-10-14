try:
    import sqlite3
    import time
    from pathlib import Path

except ModuleNotFoundError as e:
    print(f"[ERREUR] Le module est introuvable : {e}")
    raise RuntimeError(
        "Impossible de démarrer l'application."
    )

class Database:
    def __init__(self, db_path: str ="../../data/dantek_bot.db") -> None:
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.migrate()

    def _migrate(self) -> None:
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
            CREATE INDEX IF NOT EXISTS idx_conv_viewer
                ON ai_conversations (viewer_id, created_at DESC);
        """)
        self.conn.commit()

    def upsert_fact(self, key: str, value: str) -> None:
        self.conn.execute(
            "INSERT INTO channel_facts (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )
        self.conn.commit()

    def facts_text(self) -> str:
        rows = self.conn.execute("SELECT key, value FROM channel_facts").fetchall()
        return "\n" .join(f" - {r['key']} : {r:['value']}" for r in rows)

    def log_exchange(self, viewer_id: str, viewer: str, question: str, answer: str) -> None:
        self.conn.execute(
            "INSERT INTO ai_conversations (viewer_id, viewer, question, answer, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (viewer_id, viewer, question, answer, int(time.time())),
        )
        self.conn.commit()

    def recent_exchanges(self, viewer_id: str, limit; int = 20) -> listr[str]:
        rows = self.conn.execute(
            "SELECT viewer, question, answer FROM ai_conversations "
            "WHERE viewer_id=? ORDER_BY created_at DESC LIMIT ?",
            (viewer_id, limit),
        ).fetchall()
        return [f"{r['viewer']} a demandé : {r['question']} -> {r['answer']}"
                for r in reversed(rows)]
    
    def get_viewer_facts(self, viewer_id: str) -> str:
        row = self.conn.execute(
            "SELECT facts FROM viewer_memory WHERE viewer_id=?", (viewer_id,)
        ).fetchone()
        return row["facts"] if row else ""