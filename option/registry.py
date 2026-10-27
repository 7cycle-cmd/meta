# registry.py — option package 嘅名稱註冊表（SSOT）
# 每個 module 自己嘅資源註冊（meta UNIQUE）

import sqlite3

DB_PATH = "C:/projects/meta/option/option.db"


class RegistryStore:
    def __init__(self, db_path=DB_PATH):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS registry (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                meta        TEXT    NOT NULL UNIQUE,
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

    def register(self, meta, description=None):
        """登記一個名稱（冪等）"""
        self.conn.execute(
            "INSERT INTO registry (meta, description)"
            " SELECT ?, ? WHERE NOT EXISTS"
            " (SELECT 1 FROM registry WHERE meta = ?)",
            (meta, description, meta))
        self.conn.commit()
        r = self.conn.execute(
            "SELECT id FROM registry WHERE meta = ?", (meta,)).fetchone()
        return r["id"] if r else None

    def close(self):
        self.conn.close()
