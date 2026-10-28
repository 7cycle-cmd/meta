"""skill.py — task package 嘅技能登記（SSOT 表）

task 技能 = 任務管理（preflight + schema 都通過之後先可以 task）。
"""

import sqlite3

DB_PATH = r"C:\projects\meta\task\task.db"


class SkillStore:
    def __init__(self, db_path=DB_PATH):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS skill (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                resource_id   INTEGER,
                value_id      INTEGER,
                condition_id  INTEGER,
                rest_api_id   INTEGER,
                lineage_id    INTEGER,
                is_active     BOOLEAN NOT NULL DEFAULT 1
                              CHECK (is_active IN (0,1)),
                created_at    TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
                updated_at    TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
            )
        """)
        self.conn.commit()

    def list_skills(self, active_only=True):
        sql = "SELECT * FROM skill WHERE 1=1"
        if active_only:
            sql += " AND is_active = 1"
        sql += " ORDER BY id"
        return [dict(r) for r in self.conn.execute(sql)]

    def add_skill(self, resource_id=None, value_id=None, condition_id=None,
                  rest_api_id=None, lineage_id=None):
        """登記一個 skill（冪等）"""
        if resource_id is None and value_id is None and condition_id is None:
            raise ValueError("resource_id / value_id / condition_id 至少一個")
        self.conn.execute(
            "INSERT INTO skill"
            " (resource_id, value_id, condition_id, rest_api_id, lineage_id)"
            " SELECT ?, ?, ?, ?, ? WHERE NOT EXISTS"
            " (SELECT 1 FROM skill"
            "  WHERE coalesce(resource_id, -1) = coalesce(?, -1)"
            "    AND coalesce(value_id, -1) = coalesce(?, -1)"
            "    AND coalesce(condition_id, -1) = coalesce(?, -1))",
            (resource_id, value_id, condition_id, rest_api_id, lineage_id,
             resource_id, value_id, condition_id))
        self.conn.commit()
        r = self.conn.execute(
            "SELECT id FROM skill"
            " WHERE coalesce(resource_id, -1) = coalesce(?, -1)"
            " AND coalesce(value_id, -1) = coalesce(?, -1)"
            " AND coalesce(condition_id, -1) = coalesce(?, -1)"
            " ORDER BY id DESC LIMIT 1",
            (resource_id, value_id, condition_id)).fetchone()
        return r["id"] if r else None

    
    def count(self):
        return self.conn.execute("SELECT COUNT(*) c FROM skill").fetchone()["c"]

    def close(self):
        self.conn.close()