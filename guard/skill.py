"""skill.py — guard package 嘅技能登記（SSOT 表）

2026-10-26 重建：guard = token registry 守衛。
技能 = 驗證流程（rest_api 檢查 token）。
"""

import sqlite3

DB_PATH = r"C:\projects\meta\guard\guard.db"


class SkillStore:
    """guard 技能清單（2026-10-26：token 守衛技能）"""

    SKILLS = [
        ("rest_api_guard", "HTTP 入口 token 驗證"),
        ("token_seed", "由配方 seed token"),
    ]

    def __init__(self, db_path=DB_PATH):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.commit()

    def list_skills(self):
        return [{"id": i + 1, "meta_key": m, "description": d}
                for i, (m, d) in enumerate(self.SKILLS)]

    def close(self):
        self.conn.close()
