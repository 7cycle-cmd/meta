"""sql.py — guard.db 存取層（token registry）

用法：
    from guard.sql import SqlStore
    s = SqlStore()
    s.register_token('terminology.api', module_id=4)
    s.valid_token('terminology.api')   # True / False
    s.close()
"""

import sqlite3

from .schema import *  # noqa: F401,E402

DB_PATH = r"C:\projects\meta\guard\guard.db"


class SqlStore:
    def __init__(self, db_path=DB_PATH):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute(REGISTRY_DDL)
        self.conn.commit()

    # ---------- registry（token 登記） ----------
    def register_token(self, token_id, module_id, file_id=None,
                       description=None):
        """登記一個 token（冪等，登記即啟用 is_active=1）

        token_id  = token 文字識別（例如 'terminology.api'）
        module_id = taxonomy.taxonomy.id（tree=module）
        file_id   = structure_module file 行 id（可選）

        2026-10-26：is_active DEFAULT 0（預設停用）——
        登記 = 明確啟用（呢個 write 本身就係 decide），所以 INSERT 直接設 1。
        """
        self.conn.execute(
            "INSERT INTO registry (token_id, module_id, file_id, is_active)"
            " SELECT ?, ?, ?, 1 WHERE NOT EXISTS"
            " (SELECT 1 FROM registry WHERE token_id = ?)",
            (token_id, module_id, file_id, token_id))
        self.conn.commit()
        r = self.conn.execute(
            "SELECT id FROM registry WHERE token_id = ?",
            (token_id,)).fetchone()
        return r["id"] if r else None

    def register_many(self, items):
        """一次過登記多個 token

        items = [(token_id, module_id), ...]
        """
        out = []
        for token_id, module_id in items:
            out.append(self.register_token(token_id, module_id))
        return out

    def valid_token(self, token_id, active_only=True):
        """驗證 token 有冇效（存在 + is_active=1）"""
        sql = "SELECT 1 FROM registry WHERE token_id = ?"
        if active_only:
            sql += " AND is_active = 1"
        return self.conn.execute(sql, (token_id,)).fetchone() is not None

    def token_row(self, token_id, active_only=True):
        """攞 token 行（list[dict]；唔存在 = []）"""
        sql = ("SELECT r.id, r.token_id, r.module_id, r.file_id,"
               " r.is_active, r.created_at, r.updated_at"
               " FROM registry r WHERE r.token_id = ?")
        if active_only:
            sql += " AND r.is_active = 1"
        return [dict(r) for r in self.conn.execute(sql, (token_id,))]

    def tokens(self, active_only=True):
        """列出全部 token"""
        sql = "SELECT * FROM registry"
        if active_only:
            sql += " WHERE is_active = 1"
        sql += " ORDER BY id"
        return [dict(r) for r in self.conn.execute(sql)]

    def count(self):
        return self.conn.execute(
            "SELECT COUNT(*) FROM registry WHERE is_active = 1").fetchone()[0]

    def commit(self):
        self.conn.commit()

    def close(self):
        self.conn.close()
