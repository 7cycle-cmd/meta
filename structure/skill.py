"""skill.py — structure package 嘅技能登記（SSOT 表）

每個 skill = 一個能力單元（例如 fill_value、build_tree）。
即使未有 skill，呢張表都存在（空表）。

用法：
    from structure.skill import SkillStore
    s = SkillStore()
    s.list_skills()      # 列出全部 skill
    s.add_skill("xxx")   # 登記一個 skill
    s.close()
"""

import sqlite3

DB_PATH = r"C:\projects\meta\structure\structure.db"


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
        # 冪等：唔撞先插（唔燒 sqlite_sequence）
        cur = self.conn.execute(
            "INSERT INTO skill (meta_key, description)"
            " SELECT ?, ? WHERE NOT EXISTS"
            " (SELECT 1 FROM skill WHERE meta_key = ?)",
            (meta_key, description, meta_key))
        self.conn.commit()
        if cur.lastrowid:
            return cur.lastrowid
        r = self.conn.execute(
            "SELECT id FROM skill WHERE meta_key = ?",
            (meta_key,)).fetchone()
        return r["id"] if r else None

    def count(self):
        return self.conn.execute("SELECT COUNT(*) c FROM skill").fetchone()["c"]

    def close(self):
        self.conn.close()
