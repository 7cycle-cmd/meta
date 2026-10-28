"""registry.py — preflight package 嘅名稱註冊表

preflight 嘅註冊 = 檢查記錄本身（registry 表）。8 檔標準佔位。
"""

import sqlite3

DB_PATH = r"C:\projects\meta\preflight\preflight.db"


class RegistryStore:
    def __init__(self, db_path=DB_PATH):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row

    def list_registry(self, active_only=True):
        """preflight 檢查記錄就係 registry"""
        sql = "SELECT * FROM registry WHERE 1=1"
        if active_only:
            sql += " AND is_active = 1"
        sql += " ORDER BY id"
        return [dict(r) for r in self.conn.execute(sql)]

    def close(self):
        self.conn.close()