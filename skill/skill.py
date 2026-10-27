# skill.py — skill package 嘅技能登記（SSOT 表）
# 本地表記錄 skill 自己嘅技能。
# 表結構 = table_definition 權威（structure generate_table_ddl）

import sqlite3

DB_PATH = "C:/projects/meta/skill/skill.db"


class SkillStore:
    def __init__(self, db_path=DB_PATH):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        ddl = """CREATE TABLE IF NOT EXISTS skill (
    id INTEGER PRIMARY KEY AUTOINCREMENT, description TEXT NOT NULL, is_active BOOLEAN NOT NULL DEFAULT 0, created_at TEXT NOT NULL DEFAULT (datetime('now')), updated_at TEXT NOT NULL DEFAULT (datetime('now'))
)"""
        self.conn.executescript(ddl)
        self.conn.commit()

    def list_skills(self, active_only=True):
        sql = "SELECT * FROM skill WHERE 1=1"
        if active_only:
            sql += " AND is_active = 1"
        sql += " ORDER BY id"
        return [dict(r) for r in self.conn.execute(sql)]

    def add_skill(self, meta_key, description=None):
        """登記一個 skill（冪等）"""
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
