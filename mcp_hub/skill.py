"""skill.py — mcp_hub package 嘅技能登記（SSOT 表）

每個 skill = 一個技能（例如 sql / api / route）。

用法：
    from mcp_hub.skill import SkillStore
    s = SkillStore()
    s.list_skills()      # 列出全部 skill
    s.add_skill("xxx")   # 登記一個 skill
    s.close()
"""

import sqlite3

DB_PATH = r"C:\projects\meta\mcp_hub\mcp.db"


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
        cur = self.conn.execute(
            "INSERT OR IGNORE INTO skill (meta_key, description) VALUES (?, ?)",
            (meta_key, description))
        self.conn.commit()
        return cur.lastrowid

    def count(self):
        return self.conn.execute("SELECT COUNT(*) c FROM skill").fetchone()["c"]

    def close(self):
        self.conn.close()
