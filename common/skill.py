"""skill.py — common package 嘅技能登記（SSOT 表）

common 係中央字典，冇自己嘅 skill 表（技能由 mapping.db 管）。
呢個檔只係 8 檔標準嘅空殼。

用法：
    from common.skill import SkillStore
    s = SkillStore()
    s.count()
    s.close()
"""

import sqlite3

DB_PATH = r"C:\projects\meta\common\common.db"


class SkillStore:
    def __init__(self, db_path=DB_PATH):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS skill (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                meta_key    TEXT NOT NULL UNIQUE,
                description TEXT,
                is_active   BOOLEAN NOT NULL DEFAULT 1
                            CHECK (is_active IN (0,1)),
                created_at  TEXT NOT NULL
                            DEFAULT (datetime('now', 'localtime'))
            )
        """)
        self.conn.commit()

    def list_skills(self, active_only=True):
        return []

    def add_skill(self, meta_key, description=None):
        return None

    def count(self):
        return 0

    def close(self):
        self.conn.close()
