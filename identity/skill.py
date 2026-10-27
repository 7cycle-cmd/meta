"""skill.py — identity package 嘅技能登記（SSOT 表）

每個 skill = 一個技能（sql / api / route ...）。
"""

import sqlite3

DB_PATH = r"C:\projects\meta\identity\identity.db"


class SkillStore:
    def __init__(self, db_path=DB_PATH):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS skill (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                meta_key    TEXT NOT NULL UNIQUE,
                description TEXT,
                is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
                created_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
            )
        """)
        self.conn.commit()

    def list_skills(self, active_only=True):
        sql = "SELECT * FROM skill WHERE 1=1"
        if active_only:
            sql += " AND is_active = 1"
        sql += " ORDER BY id"
        return [dict(r) for r in self.conn.execute(sql)]

    def add_skill(self, meta_key, description=None):
        """登記一個技能（冪等）"""
        self.conn.execute(
            "INSERT INTO skill (meta_key, description)"
            " SELECT ?, ? WHERE NOT EXISTS"
            " (SELECT 1 FROM skill WHERE meta_key = ?)",
            (meta_key, description, meta_key))
        self.conn.commit()
        r = self.conn.execute(
            "SELECT id FROM skill WHERE meta_key = ?",
            (meta_key,)).fetchone()
        return r["id"] if r else None

    def close(self):
        self.conn.close()
