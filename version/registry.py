# registry.py — version package 嘅名稱註冊表（SSOT）
#
# 2026-10-27（用戶要求）：version 表 -> rename -> registry
#   （id | pass_id | value_id | github_id）
#
# ⚠️ 呢個檔案同 sql.py **同一個 package、同一個 DB 檔**（version/version.db）。
#    SQLite 表名係 per-DB 唯一，唔係 per-file —— 所以呢度唔可以再建一個
#    叫 registry 嘅表（會撞 sql.py 嘅版本註冊表）。
#    正確做法：registry.py 就係嗰張 registry 表嘅入口（同 terminology 一樣）。

import sqlite3

from .schema import REGISTRY_DDL, VALUE_DDL

DB_PATH = "C:/projects/meta/version/version.db"


class RegistryStore:
    """version 版本註冊表（id | pass_id | value_id | github_id）

    同 sql.py 共用同一張 registry 表（同一個 DB 檔）——
    呢度只係 registry.py 標準入口，唔另建表。
    """

    def __init__(self, db_path=DB_PATH):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute(VALUE_DDL)      # 版本值表（版本字串）
        self.conn.execute(REGISTRY_DDL)   # 版本註冊表（同一張）
        self.conn.commit()

    def list_registry(self, active_only=True):
        """列出註冊版本（registry JOIN value）"""
        sql = ("SELECT r.id, v.value AS version, r.pass_id, r.value_id,"
               " r.github_id, r.is_active, r.created_at, r.updated_at"
               " FROM registry r LEFT JOIN value v ON v.id = r.value_id"
               " WHERE 1=1")
        if active_only:
            sql += " AND r.is_active = 1"
        sql += " ORDER BY r.id"
        return [dict(r) for r in self.conn.execute(sql)]

    def register(self, version, pass_id=None, github_id=None):
        """登記一個版本（冪等）—— value 存字串，registry 存註冊行

        返回 registry.id
        """
        self.conn.execute(
            "INSERT INTO value (value) SELECT ? WHERE NOT EXISTS"
            " (SELECT 1 FROM value WHERE value = ?)", (version, version))
        row = self.conn.execute(
            "SELECT id FROM value WHERE value = ?", (version,)).fetchone()
        if not row:
            return None
        vid = row["id"]
        self.conn.execute(
            "INSERT INTO registry (value_id, pass_id, github_id)"
            " SELECT ?, ?, ? WHERE NOT EXISTS"
            " (SELECT 1 FROM registry WHERE value_id = ?)",
            (vid, pass_id, github_id, vid))
        self.conn.commit()
        r = self.conn.execute(
            "SELECT id FROM registry WHERE value_id = ?", (vid,)).fetchone()
        return r["id"] if r else None

    def close(self):
        self.conn.close()
