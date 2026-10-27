"""registry.py — monitor 資源登記（SSOT 表）"""

import sqlite3

DB_PATH = r"C:\projects\meta\monitor\monitor.db"


class RegistryStore:
    def __init__(self, db_path=DB_PATH):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS registry (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                meta_key    TEXT NOT NULL UNIQUE,
                description TEXT,
                is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
                created_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
            )
        """)
        self.conn.commit()

    def list_registry(self, active_only=True):
        sql = "SELECT * FROM registry WHERE 1=1"
        if active_only:
            sql += " AND is_active = 1"
        sql += " ORDER BY id"
        return [dict(r) for r in self.conn.execute(sql)]

    def add(self, meta_key, description=None):
        cur = self.conn.execute(
            "INSERT INTO registry (meta_key, description)"
            " SELECT ?, ? WHERE NOT EXISTS"
            " (SELECT 1 FROM registry WHERE meta_key = ?)",
            (meta_key, description, meta_key))
        self.conn.commit()
        if cur.lastrowid:
            return cur.lastrowid
        r = self.conn.execute(
            "SELECT id FROM registry WHERE meta_key = ?",
            (meta_key,)).fetchone()
        return r["id"] if r else None

    def count(self):
        return self.conn.execute("SELECT COUNT(*) c FROM registry").fetchone()["c"]

    def close(self):
        self.conn.close()
