"""sql.py — register.db 存取層（註冊結果）"""

import sqlite3

from .schema import *  # noqa: F401,E402

DB_PATH = r"C:\projects\meta\register\register.db"


class SqlStore:
    def __init__(self, db_path=DB_PATH):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute(REST_API_DDL)
        self.conn.commit()

    def rest_apis(self, module=None, type=None, active_only=True):
        """列出 REST API 註冊（可按 module / type 篩選）"""
        sql = "SELECT * FROM rest_api WHERE 1=1"
        args = []
        if module:
            sql += " AND module = ?"
            args.append(module)
        if type:
            sql += " AND type = ?"
            args.append(type)
        if active_only:
            sql += " AND is_active = 1"
        sql += " ORDER BY module, type, id"
        return [dict(r) for r in self.conn.execute(sql, args)]

    def add_rest_api(self, module, type, api, rule_id=None):
        """登記一個 REST API（冪等）"""
        cur = self.conn.execute(
            "INSERT INTO rest_api (module, type, api, rule_id)"
            " SELECT ?, ?, ?, ? WHERE NOT EXISTS"
            " (SELECT 1 FROM rest_api WHERE module = ? AND type = ? AND api = ?)",
            (module, type, api, rule_id, module, type, api))
        self.conn.commit()
        if cur.rowcount:
            return cur.lastrowid
        r = self.conn.execute(
            "SELECT id FROM rest_api WHERE module = ? AND type = ? AND api = ?",
            (module, type, api)).fetchone()
        return r["id"] if r else None

    def reset(self, module=None):
        """清空註冊（可指定 module；重新 sync 用）"""
        if module:
            cur = self.conn.execute(
                "DELETE FROM rest_api WHERE module = ?", (module,))
        else:
            cur = self.conn.execute("DELETE FROM rest_api")
        self.conn.commit()
        return cur.rowcount

    def count(self):
        return self.conn.execute("SELECT COUNT(*) c FROM rest_api").fetchone()["c"]

    def close(self):
        self.conn.close()
