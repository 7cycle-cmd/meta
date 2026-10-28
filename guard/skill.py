"""skill.py — guard package 嘅技能登記（SSOT 表，2026-10-27 全站統一）

skill 表（全站統一設計）：
    id            = 技能行 id
    resource_id   = resource 識別（例如 db_table / api 名）
    value_id      = value.id（技能處理嘅值）
    condition_id  = condition.id（技能用邊個判斷）
    rest_api_id   = rest_api 識別（例如 '/' 或 route 名）
    lineage_id    = lineage.id（值嘅運行時條件記錄，2026-10-27）

guard 技能 = token 守衛（rest_api_guard / token_seed），由 DB 表存（唔再 hardcode）。
"""

import sqlite3

DB_PATH = r"C:\projects\meta\guard\guard.db"

DEFAULT_GUARD_SKILLS = [
    (1, 0, "rest_api_guard", "HTTP 入口 token 驗證"),
    (2, 0, "token_seed", "由配方 seed token"),
]


class SkillStore:
    def __init__(self, db_path=DB_PATH):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS skill (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                resource_id   INTEGER,           -- resource 識別（db_table / api）
                value_id      INTEGER,           -- value.id
                condition_id  INTEGER,           -- condition.id
                rest_api_id   INTEGER,           -- rest_api route 識別
                lineage_id    INTEGER,           -- lineage.id（運行時條件）
                description   TEXT,              -- 技能描述（guard seed 用）
                is_active     BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
                created_at    TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
                updated_at    TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
            )
        """)
        self.conn.commit()
        self._migrate_description()

    def _migrate_description(self):
        """遷移（幂等）：skill 表加 description 欄"""
        cols = {c[1] for c in self.conn.execute(
            "PRAGMA table_info('skill')")}
        if "description" not in cols:
            self.conn.execute(
                "ALTER TABLE skill ADD COLUMN description TEXT")
            self.conn.commit()
            print("[guard.skill] skill 表加 description 欄")
        self._seed()

    def _seed(self):
        """seed guard 技能（冪等：固定 id）"""
        for sid, resource_id, meta_key, desc in DEFAULT_GUARD_SKILLS:
            self.conn.execute(
                "INSERT INTO skill (id, resource_id, value_id, description)"
                " SELECT ?, ?, ?, ? WHERE NOT EXISTS"
                " (SELECT 1 FROM skill WHERE id = ?)",
                (sid, resource_id, meta_key, desc, sid))
        self.conn.commit()

    def list_skills(self, active_only=True):
        sql = "SELECT * FROM skill WHERE 1=1"
        if active_only:
            sql += " AND is_active = 1"
        sql += " ORDER BY id"
        return [dict(r) for r in self.conn.execute(sql)]

    def add_skill(self, resource_id=None, value_id=None, condition_id=None,
                  rest_api_id=None, lineage_id=None):
        """登記一個 skill（冪等：resource_id + value_id + condition_id 組合）"""
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
