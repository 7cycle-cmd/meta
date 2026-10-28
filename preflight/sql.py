"""sql.py — preflight.db 存取層

preflight = 起飛前檢查：plan 之前要過 preflight 檢查（系統 ready 先可以 plan）

2026-10-27（用戶要求）：
    preflight 表同 schema 好相似（都係 run_id 主導 + 資源引用）
    分別係時機：
        preflight = before plan（全局：成個系統 ready 未？）
        schema    = before execution（局部：呢個 job 要嘅嘢 ready 未？）

registry 表：
    run_id                 = terminology.run.id（flow 產生）
    plan_id                = sweep.target.id（可選）
    skill_id               = skill.id
    resource_formula_id    = 資源 formula（未註冊）
    resource_structure_id  = 資源 structure（未註冊）

用法：
    from preflight.sql import SqlStore
    s = SqlStore()
    s.add_registry(run_id=1, plan_id=2, skill_id=3)
    s.close()
"""

import sqlite3

from .schema import *  # noqa: F401,E402

DB_PATH = r"C:\projects\meta\preflight\preflight.db"


class SqlStore:
    def __init__(self, db_path=DB_PATH):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute(REGISTRY_DDL)
        self.conn.commit()

    # ---------- registry ----------
    def add_registry(self, run_id, plan_id=None, skill_id=None,
                     resource_formula_id=None, resource_structure_id=None):
        """登記一次 preflight 檢查（冪等：run_id 唯一）

        run_id = terminology.run.id（全站 flow 引擎產生）
        """
        cur = self.conn.execute(
            "INSERT INTO registry"
            " (run_id, plan_id, skill_id, resource_formula_id,"
            "  resource_structure_id)"
            " SELECT ?, ?, ?, ?, ? WHERE NOT EXISTS"
            " (SELECT 1 FROM registry WHERE run_id = ?)",
            (run_id, plan_id, skill_id, resource_formula_id,
             resource_structure_id, run_id))
        self.conn.commit()
        if cur.rowcount:
            return cur.lastrowid
        r = self.conn.execute(
            "SELECT id FROM registry WHERE run_id = ?", (run_id,)).fetchone()
        return r["id"] if r else None

    def registries(self, run_id=None, plan_id=None, skill_id=None,
                   active_only=True, limit=100):
        """列出 preflight 檢查（可按 run / plan / skill 篩選）"""
        sql = "SELECT * FROM registry WHERE 1=1"
        args = []
        if run_id is not None:
            sql += " AND run_id = ?"
            args.append(run_id)
        if plan_id is not None:
            sql += " AND plan_id = ?"
            args.append(plan_id)
        if skill_id is not None:
            sql += " AND skill_id = ?"
            args.append(skill_id)
        if active_only:
            sql += " AND is_active = 1"
        sql += " ORDER BY id DESC LIMIT ?"
        args.append(limit)
        return [dict(r) for r in self.conn.execute(sql, args)]

    def count(self):
        return self.conn.execute(
            "SELECT COUNT(*) FROM registry WHERE is_active = 1").fetchone()[0]

    def commit(self):
        self.conn.commit()

    def close(self):
        self.conn.close()