"""sql.py — rule.db 存取層

rule = 自動化規則層：每個 module 可以註冊自己嘅自動化規則

2026-10-27（用戶要求）：
    registry 表：id | taxonomy_id | flow_id | step_id | parameter
    flow_id / step_id 指 terminology.db（flow 引擎）
    setting 表唔需要（parameter 欄存 JSON）

用法：
    from rule.sql import SqlStore
    s = SqlStore()
    s.add_rule(taxonomy_id=1, flow_id=2, step_id=3, parameter='{"pattern": "^/"}')
    s.close()
"""

import sqlite3

from .schema import *  # noqa: F401,E402

DB_PATH = r"C:\projects\meta\rule\rule.db"


class SqlStore:
    def __init__(self, db_path=DB_PATH):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute(REGISTRY_DDL)
        self.conn.commit()

    # ---------- registry ----------
    def add_rule(self, taxonomy_id, flow_id, step_id, parameter=None):
        """登記一條自動化規則（冪等：taxonomy_id + flow_id + step_id 組合）

        taxonomy_id = taxonomy.registry.id（邊個 module 要自動做嘢）
        flow_id     = terminology.db flow.id（行邊條 flow）
        step_id     = terminology.db step.id（行到邊個 step）
        parameter   = 額外參數（JSON 字串，可選）
        """
        cur = self.conn.execute(
            "INSERT INTO registry (taxonomy_id, flow_id, step_id, parameter)"
            " SELECT ?, ?, ?, ? WHERE NOT EXISTS"
            " (SELECT 1 FROM registry"
            "  WHERE taxonomy_id = ? AND flow_id = ? AND step_id = ?)",
            (taxonomy_id, flow_id, step_id, parameter,
             taxonomy_id, flow_id, step_id))
        self.conn.commit()
        if cur.rowcount:
            return cur.lastrowid
        r = self.conn.execute(
            "SELECT id FROM registry"
            " WHERE taxonomy_id = ? AND flow_id = ? AND step_id = ?",
            (taxonomy_id, flow_id, step_id)).fetchone()
        return r["id"] if r else None

    def rules(self, taxonomy_id=None, flow_id=None, active_only=True,
              limit=100):
        """列出規則（可按 module / flow 篩選）"""
        sql = "SELECT * FROM registry WHERE 1=1"
        args = []
        if taxonomy_id is not None:
            sql += " AND taxonomy_id = ?"
            args.append(taxonomy_id)
        if flow_id is not None:
            sql += " AND flow_id = ?"
            args.append(flow_id)
        if active_only:
            sql += " AND is_active = 1"
        sql += " ORDER BY taxonomy_id, flow_id, step_id LIMIT ?"
        args.append(limit)
        return [dict(r) for r in self.conn.execute(sql, args)]

    def count(self):
        return self.conn.execute(
            "SELECT COUNT(*) FROM registry WHERE is_active = 1").fetchone()[0]

    def commit(self):
        self.conn.commit()

    def close(self):
        self.conn.close()