"""sql.py — lineage.db 存取層（值嘅運行時條件）"""

import sqlite3

from .schema import *  # noqa: F401,E402

DB_PATH = r"C:\projects\meta\lineage\lineage.db"


class SqlStore:
    def __init__(self, db_path=DB_PATH):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute(LINEAGE_DDL)
        self.conn.commit()

    def add(self, value_id, run_id=None, flow_id=None, step_id=None,
            resource_id=None, taxonomy_id=None, value=None):
        """記錄一個值嘅運行時條件（冪等：同 run + value + step 組合）

        value 字串快照自動由 value.db 攞（如果冇傳）。
        """
        if value is None and value_id is not None:
            try:
                r = self.conn.execute(
                    "SELECT value FROM vdb.value WHERE id = ?",
                    (value_id,)).fetchone()
                value = r["value"] if r else None
            except sqlite3.OperationalError:
                pass  # vdb 未 ATTACH -> 由 caller 提供
        cur = self.conn.execute(
            "INSERT INTO lineage"
            " (resource_id, value_id, taxonomy_id, run_id, flow_id,"
            "  step_id, value)"
            " SELECT ?, ?, ?, ?, ?, ?, ? WHERE NOT EXISTS"
            " (SELECT 1 FROM lineage"
            "  WHERE coalesce(run_id, -1) = coalesce(?, -1)"
            "    AND coalesce(value_id, -1) = coalesce(?, -1)"
            "    AND coalesce(step_id, -1) = coalesce(?, -1))",
            (resource_id, value_id, taxonomy_id, run_id, flow_id, step_id,
             value, run_id, value_id, step_id))
        self.conn.commit()
        r = self.conn.execute(
            "SELECT id FROM lineage"
            " WHERE coalesce(run_id, -1) = coalesce(?, -1)"
            "   AND coalesce(value_id, -1) = coalesce(?, -1)"
            "   AND coalesce(step_id, -1) = coalesce(?, -1)"
            " ORDER BY id DESC LIMIT 1",
            (run_id, value_id, step_id)).fetchone()
        return r["id"] if r else None

    def list(self, value_id=None, run_id=None, flow_id=None,
             taxonomy_id=None, active_only=True, limit=100):
        """列出運行時條件（可按 value / run / flow / module 篩選）"""
        sql = "SELECT * FROM lineage WHERE 1=1"
        args = []
        if value_id is not None:
            sql += " AND value_id = ?"
            args.append(value_id)
        if run_id is not None:
            sql += " AND run_id = ?"
            args.append(run_id)
        if flow_id is not None:
            sql += " AND flow_id = ?"
            args.append(flow_id)
        if taxonomy_id is not None:
            sql += " AND taxonomy_id = ?"
            args.append(taxonomy_id)
        if active_only:
            sql += " AND is_active = 1"
        sql += " ORDER BY id DESC LIMIT ?"
        args.append(limit)
        return [dict(r) for r in self.conn.execute(sql, args)]

    def count(self):
        return self.conn.execute("SELECT COUNT(*) c FROM lineage").fetchone()["c"]

    def close(self):
        self.conn.close()