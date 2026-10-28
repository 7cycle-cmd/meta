"""sql.py — plan.db 存取層

plan = 計劃層：preflight 通過之後先可以 plan

2026-10-27（用戶要求）：
    plan 表：id | preflight_id | role_id | rule_id | tool_id | value_id | run_id
    時機鏈：preflight → plan → schema → task
    2026-10-27b：skill_id → tool_id（工具層話事）
    2026-10-27d：+ role_id（邊個角色落 order，role.db registry 表）
    2026-10-27e：+ rule_id（跟邊條規則，rule.db rule 表；多維度 SSOT）

用法：
    from plan.sql import SqlStore
    s = SqlStore()
    s.add_plan(preflight_id=1, run_id=4, role_id=3, rule_id=5,
               tool_id=2, value_id=3)
    s.close()
"""

import sqlite3

from .schema import *  # noqa: F401,E402

DB_PATH = r"C:\projects\meta\plan\plan.db"


class SqlStore:
    def __init__(self, db_path=DB_PATH):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute(PLAN_DDL)
        self.conn.commit()
        self._migrate_skill_to_tool()
        self._migrate_role_id()
        self._migrate_rule_id()

    def _migrate_skill_to_tool(self):
        """遷移（幂等）：skill_id -> tool_id（2026-10-27 用戶要求）

        舊表有 skill_id 欄 -> RENAME 做 tool_id（保留資料）。
        """
        cols = {c[1] for c in self.conn.execute(
            "PRAGMA table_info('plan')")}
        if "skill_id" in cols and "tool_id" not in cols:
            self.conn.execute(
                "ALTER TABLE plan RENAME COLUMN skill_id TO tool_id")
            self.conn.commit()
            print("[plan] skill_id -> tool_id（rename，保資料）")

    def _migrate_role_id(self):
        """遷移（幂等）：plan 加 role_id 欄（2026-10-27d 用戶要求）"""
        cols = {c[1] for c in self.conn.execute(
            "PRAGMA table_info('plan')")}
        if "role_id" not in cols:
            self.conn.execute("ALTER TABLE plan ADD COLUMN role_id INTEGER")
            self.conn.commit()
            print("[plan] plan 表加 role_id 欄")

    def _migrate_rule_id(self):
        """遷移（幂等）：plan 加 rule_id 欄（2026-10-27e 用戶要求）"""
        cols = {c[1] for c in self.conn.execute(
            "PRAGMA table_info('plan')")}
        if "rule_id" not in cols:
            self.conn.execute("ALTER TABLE plan ADD COLUMN rule_id INTEGER")
            self.conn.commit()
            print("[plan] plan 表加 rule_id 欄")

    # ---------- plan ----------
    def add_plan(self, preflight_id, run_id, role_id=None, rule_id=None,
                 tool_id=None, value_id=None):
        """登記一個計劃（冪等：preflight_id + run_id 組合）

        preflight_id = preflight.registry.id（起飛前檢查通過咗）
        run_id       = terminology.run.id（全站 flow 引擎產生）
        role_id      = role.db registry.id（邊個角色落 order）
        rule_id      = rule.db rule.id（跟邊條規則）
        tool_id      = tool.registry.id（邊個工具幫手）
        """
        cur = self.conn.execute(
            "INSERT INTO plan (preflight_id, role_id, rule_id, tool_id,"
            " value_id, run_id)"
            " SELECT ?, ?, ?, ?, ?, ? WHERE NOT EXISTS"
            " (SELECT 1 FROM plan WHERE preflight_id = ? AND run_id = ?)",
            (preflight_id, role_id, rule_id, tool_id, value_id, run_id,
             preflight_id, run_id))
        self.conn.commit()
        if cur.rowcount:
            return cur.lastrowid
        r = self.conn.execute(
            "SELECT id FROM plan WHERE preflight_id = ? AND run_id = ?",
            (preflight_id, run_id)).fetchone()
        return r["id"] if r else None

    def plans(self, preflight_id=None, role_id=None, rule_id=None,
              tool_id=None, value_id=None, active_only=True, limit=100):
        """列出計劃（可按 preflight / role / rule / tool / value 篩選）"""
        sql = "SELECT * FROM plan WHERE 1=1"
        args = []
        if preflight_id is not None:
            sql += " AND preflight_id = ?"
            args.append(preflight_id)
        if role_id is not None:
            sql += " AND role_id = ?"
            args.append(role_id)
        if rule_id is not None:
            sql += " AND rule_id = ?"
            args.append(rule_id)
        if tool_id is not None:
            sql += " AND tool_id = ?"
            args.append(tool_id)
        if value_id is not None:
            sql += " AND value_id = ?"
            args.append(value_id)
        if active_only:
            sql += " AND is_active = 1"
        sql += " ORDER BY id DESC LIMIT ?"
        args.append(limit)
        return [dict(r) for r in self.conn.execute(sql, args)]

    def count(self):
        return self.conn.execute(
            "SELECT COUNT(*) FROM plan WHERE is_active = 1").fetchone()[0]

    def commit(self):
        self.conn.commit()

    def close(self):
        self.conn.close()