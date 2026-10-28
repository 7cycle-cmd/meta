"""sql.py — tool.db 存取層

tool = 工具層：一個 mission 可以攞到邊個工具幫手（by REST_API_id）

2026-10-27（用戶要求）：
    registry 表：id | module_id | skill_id | REST_API_WRITE_id | REST_API_READ_id
    READ 中心 = monitor（rest_api_READ）
    WRITE 中心 = tool（rest_api_WRITE）

用法：
    from tool.sql import SqlStore
    s = SqlStore()
    s.add_tool(module_id=1, skill_id=2, rest_api_write_id=3, rest_api_read_id=4)
    s.close()
"""

import sqlite3

from .schema import *  # noqa: F401,E402

DB_PATH = r"C:\projects\meta\tool\tool.db"


class SqlStore:
    def __init__(self, db_path=DB_PATH):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(";\n".join([
            REST_API_WRITE_DDL, REGISTRY_DDL,
        ]))
        self.conn.commit()

    # ---------- rest_api_WRITE（WRITE 中心） ----------
    def add_write_api(self, module_id, rest_api):
        """登記一個 WRITE API（冪等：module_id + rest_api 組合）"""
        cur = self.conn.execute(
            "INSERT INTO rest_api_WRITE (module_id, rest_api)"
            " SELECT ?, ? WHERE NOT EXISTS"
            " (SELECT 1 FROM rest_api_WRITE"
            "  WHERE module_id = ? AND rest_api = ?)",
            (module_id, rest_api, module_id, rest_api))
        self.conn.commit()
        if cur.rowcount:
            return cur.lastrowid
        r = self.conn.execute(
            "SELECT id FROM rest_api_WRITE"
            " WHERE module_id = ? AND rest_api = ?",
            (module_id, rest_api)).fetchone()
        return r["id"] if r else None

    def write_apis(self, module_id=None, active_only=True):
        """列出 WRITE API 中心（可按 module 篩選）"""
        sql = "SELECT * FROM rest_api_WRITE WHERE 1=1"
        args = []
        if module_id is not None:
            sql += " AND module_id = ?"
            args.append(module_id)
        if active_only:
            sql += " AND is_active = 1"
        sql += " ORDER BY module_id, rest_api"
        return [dict(r) for r in self.conn.execute(sql, args)]

    # ---------- registry ----------
    def add_tool(self, module_id, skill_id=None, rest_api_write_id=None,
                 rest_api_read_id=None):
        """登記一個工具（冪等：module_id + skill_id + WRITE + READ 組合）"""
        cur = self.conn.execute(
            "INSERT INTO registry (module_id, skill_id, REST_API_WRITE_id,"
            " REST_API_READ_id)"
            " SELECT ?, ?, ?, ? WHERE NOT EXISTS"
            " (SELECT 1 FROM registry"
            "  WHERE module_id = ?"
            "    AND coalesce(skill_id, -1) = coalesce(?, -1)"
            "    AND coalesce(REST_API_WRITE_id, -1) = coalesce(?, -1)"
            "    AND coalesce(REST_API_READ_id, -1) = coalesce(?, -1))",
            (module_id, skill_id, rest_api_write_id, rest_api_read_id,
             module_id, skill_id, rest_api_write_id, rest_api_read_id))
        self.conn.commit()
        if cur.rowcount:
            return cur.lastrowid
        r = self.conn.execute(
            "SELECT id FROM registry"
            " WHERE module_id = ?"
            "   AND coalesce(skill_id, -1) = coalesce(?, -1)"
            "   AND coalesce(REST_API_WRITE_id, -1) = coalesce(?, -1)"
            "   AND coalesce(REST_API_READ_id, -1) = coalesce(?, -1)"
            " ORDER BY id DESC LIMIT 1",
            (module_id, skill_id, rest_api_write_id, rest_api_read_id)).fetchone()
        return r["id"] if r else None

    def tools(self, module_id=None, skill_id=None, active_only=True,
              limit=100):
        """列出工具（可按 module / skill 篩選）"""
        sql = "SELECT * FROM registry WHERE 1=1"
        args = []
        if module_id is not None:
            sql += " AND module_id = ?"
            args.append(module_id)
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