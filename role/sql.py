"""sql.py — role.db 存取層

role = 角色層：CQRS 身份（邊個 module 以咩角色做嘢）

2026-10-27（用戶要求）：
    module : rule -> rename -> role
    remove -> table : role and rule
    table : registry + taxonomy_id

用法：
    from role.sql import SqlStore
    s = SqlStore()
    s.add_role(taxonomy_id=1, meta="owner")
    s.close()
"""

import sqlite3

from .schema import *  # noqa: F401,E402

DB_PATH = r"C:\projects\meta\role\role.db"


class SqlStore:
    def __init__(self, db_path=DB_PATH):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute(REGISTRY_DDL)
        self.conn.commit()

    # ---------- registry ----------
    def add_role(self, taxonomy_id, meta):
        """登記一個角色（冪等：taxonomy_id + meta 組合）

        taxonomy_id = taxonomy.registry.id（邊個 module 擁有）
        meta        = 角色名（owner / reader / orderer / recorder ...）
        """
        cur = self.conn.execute(
            "INSERT INTO registry (taxonomy_id, meta)"
            " SELECT ?, ? WHERE NOT EXISTS"
            " (SELECT 1 FROM registry WHERE taxonomy_id = ? AND meta = ?)",
            (taxonomy_id, meta, taxonomy_id, meta))
        self.conn.commit()
        if cur.rowcount:
            return cur.lastrowid
        r = self.conn.execute(
            "SELECT id FROM registry WHERE taxonomy_id = ? AND meta = ?",
            (taxonomy_id, meta)).fetchone()
        return r["id"] if r else None

    def role_id(self, taxonomy_id, meta):
        """由 module + 角色名攞 id（唔存在 None）"""
        r = self.conn.execute(
            "SELECT id FROM registry WHERE taxonomy_id = ? AND meta = ?",
            (taxonomy_id, meta)).fetchone()
        return r["id"] if r else None

    def roles(self, taxonomy_id=None, active_only=True):
        """列出角色（可按 module 篩選）"""
        sql = "SELECT * FROM registry WHERE 1=1"
        args = []
        if taxonomy_id is not None:
            sql += " AND taxonomy_id = ?"
            args.append(taxonomy_id)
        if active_only:
            sql += " AND is_active = 1"
        sql += " ORDER BY taxonomy_id, meta"
        return [dict(r) for r in self.conn.execute(sql, args)]

    def count(self):
        return self.conn.execute(
            "SELECT COUNT(*) FROM registry WHERE is_active = 1").fetchone()[0]

    def commit(self):
        self.conn.commit()

    def close(self):
        self.conn.close()