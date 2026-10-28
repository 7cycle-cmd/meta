"""sql.py — identity.db 存取層（身份層：value × condition × flow × step）"""

import sqlite3

from .schema import REGISTRY_DDL  # noqa: F401

DB_PATH = r"C:\projects\meta\identity\identity.db"


class SqlStore:
    def __init__(self, db_path=DB_PATH):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._migrate_old_registry()
        self.conn.execute(REGISTRY_DDL)
        self.conn.commit()

    def _migrate_old_registry(self):
        """遷移（幂等）：舊 registry（kind + name）-> 新版（value × condition × flow × step）

        2026-10-28（用戶要求）：kind 舊設計已撤換。
        舊表有 kind 欄 -> DROP（舊資料係 kind+name，冇 value 鏈，搬唔到）。
        新表用 REGISTRY_DDL 重建（空）。
        """
        has = self.conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table'"
            " AND name='registry'").fetchone()
        if not has:
            return
        cols = {c[1] for c in self.conn.execute(
            "PRAGMA table_info('registry')")}
        if "kind" not in cols:
            return  # 已新版
        n = self.conn.execute(
            "SELECT COUNT(*) FROM registry").fetchone()[0]
        self.conn.execute("DROP TABLE registry")
        self.conn.commit()
        print(f"[identity] 舊 registry（kind+name，{n} 行）drop —— "
              f"新設計：value × condition × flow × step")

    # ---------- 登記 ----------
    def register(self, value_id, condition_id, flow_id, step_id,
                 taxonomy_id=None, permit_id=None, description=None):
        """登記一個身份（冪等：value × condition × flow × step 組合）

        value_id     = value.db value.id（身份主檔）
        condition_id = terminology.condition.id（判斷）
        flow_id      = terminology.flow.id（證明 flow）
        step_id      = terminology.step.id（證明步驟）
        5W2H 7 步：what/where/when/who/why/how/how much
        """
        self.conn.execute(
            """INSERT INTO registry (value_id, condition_id, flow_id,
                                     step_id, taxonomy_id, permit_id,
                                     description)
               VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(value_id, condition_id, flow_id, step_id)
               DO UPDATE SET
                   taxonomy_id = COALESCE(excluded.taxonomy_id, registry.taxonomy_id),
                   permit_id = COALESCE(excluded.permit_id, registry.permit_id),
                   description = COALESCE(excluded.description, registry.description),
                   is_active = 1""",
            (value_id, condition_id, flow_id, step_id,
             taxonomy_id, permit_id, description))
        self.conn.commit()
        r = self.conn.execute(
            "SELECT id FROM registry"
            " WHERE value_id = ? AND condition_id = ?"
            " AND flow_id = ? AND step_id = ?",
            (value_id, condition_id, flow_id, step_id)).fetchone()
        return r["id"] if r else None

    # ---------- 查詢 ----------
    def lookup(self, value_id, condition_id=None, flow_id=None,
               step_id=None):
        """按 value（+ condition/flow/step 可選）查身份"""
        sql = "SELECT * FROM registry WHERE value_id = ? AND is_active = 1"
        args = [value_id]
        if condition_id:
            sql += " AND condition_id = ?"
            args.append(condition_id)
        if flow_id:
            sql += " AND flow_id = ?"
            args.append(flow_id)
        if step_id:
            sql += " AND step_id = ?"
            args.append(step_id)
        return self.conn.execute(sql, tuple(args)).fetchall()

    def lookup_all(self, value_id=None, flow_id=None, active_only=True):
        """列出全部身份（可按 value / flow 篩選）"""
        sql = "SELECT * FROM registry WHERE 1=1"
        args = []
        if value_id:
            sql += " AND value_id = ?"
            args.append(value_id)
        if flow_id:
            sql += " AND flow_id = ?"
            args.append(flow_id)
        if active_only:
            sql += " AND is_active = 1"
        sql += " ORDER BY value_id, id"
        return [dict(r) for r in self.conn.execute(sql, args)]

    def resolve(self, value_id, condition_id, flow_id, step_id):
        """由 value + condition + flow + step 攞身份（冇 = None）"""
        return self.conn.execute(
            "SELECT * FROM registry"
            " WHERE value_id = ? AND condition_id = ? AND flow_id = ?"
            " AND step_id = ? AND is_active = 1",
            (value_id, condition_id, flow_id, step_id)).fetchone()

    def commit(self):
        self.conn.commit()

    def close(self):
        self.conn.close()
