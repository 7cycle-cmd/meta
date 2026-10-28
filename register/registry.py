"""registry.py — register package 嘅名稱註冊表（SSOT）

register 嘅註冊 = 註冊結果本身（rest_api 表）。呢個檔案係 8 檔標準佔位。
"""

import sqlite3

DB_PATH = r"C:\projects\meta\register\register.db"


class RegistryStore:
    def __init__(self, db_path=DB_PATH):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row

    def list_registry(self, active_only=True):
        """註冊結果就係 registry（rest_api 表）"""
        sql = "SELECT * FROM rest_api WHERE 1=1"
        if active_only:
            sql += " AND is_active = 1"
        sql += " ORDER BY id"
        return [dict(r) for r in self.conn.execute(sql)]

    def close(self):
        self.conn.close()