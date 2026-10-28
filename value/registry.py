"""registry.py — value package 嘅名稱註冊表（SSOT）

value 嘅註冊 = 值本身（value 表）。呢個檔案係 8 檔標準佔位。
"""

import sqlite3

DB_PATH = r"C:\projects\meta\value\value.db"


class RegistryStore:
    def __init__(self, db_path=DB_PATH):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row

    def list_registry(self, active_only=True):
        """值就係 registry（value 表）"""
        sql = "SELECT * FROM value WHERE 1=1"
        if active_only:
            sql += " AND is_active = 1"
        sql += " ORDER BY id"
        return [dict(r) for r in self.conn.execute(sql)]

    def close(self):
        self.conn.close()