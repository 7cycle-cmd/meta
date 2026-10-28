"""sql.py — value.db 存取層（值資產）"""

import sqlite3

from .schema import *  # noqa: F401,E402

DB_PATH = r"C:\projects\meta\value\value.db"


class SqlStore:
    def __init__(self, db_path=DB_PATH):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute(VALUE_DDL)
        self.conn.commit()

    def add(self, value, taxonomy_id=None):
        """新增 / 攞一個值嘅 id（冪等；taxonomy_id = 邊個 module 登記）"""
        r = self.conn.execute(
            "SELECT id FROM value WHERE value IS ?", (value,)).fetchone()
        if r:
            if taxonomy_id is not None:
                self.conn.execute(
                    "UPDATE value SET taxonomy_id = ?"
                    " WHERE id = ? AND taxonomy_id IS NULL",
                    (taxonomy_id, r["id"]))
                self.conn.commit()
            return r["id"]
        cur = self.conn.execute(
            "INSERT INTO value (value, taxonomy_id) VALUES (?, ?)",
            (value, taxonomy_id))
        self.conn.commit()
        return cur.lastrowid

    def get(self, value_id):
        """按 id 攞一個值"""
        r = self.conn.execute(
            "SELECT * FROM value WHERE id = ?", (value_id,)).fetchone()
        return dict(r) if r else None

    def by_value(self, value):
        """按值攞行（唔存在 None）"""
        r = self.conn.execute(
            "SELECT * FROM value WHERE value IS ?", (value,)).fetchone()
        return dict(r) if r else None

    def list(self, taxonomy_id=None, active_only=True):
        """列出值（可按 module 篩選）"""
        sql = "SELECT * FROM value WHERE 1=1"
        args = []
        if taxonomy_id is not None:
            sql += " AND taxonomy_id = ?"
            args.append(taxonomy_id)
        if active_only:
            sql += " AND is_active = 1"
        sql += " ORDER BY id"
        return [dict(r) for r in self.conn.execute(sql, args)]

    def count(self):
        return self.conn.execute("SELECT COUNT(*) c FROM value").fetchone()["c"]

    def close(self):
        self.conn.close()