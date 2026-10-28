"""registry.py — task package 嘅名稱註冊表

task 嘅註冊 = 任務本身（task 表）。8 檔標準佔位。
"""

import sqlite3

DB_PATH = r"C:\projects\meta\task\task.db"


class RegistryStore:
    def __init__(self, db_path=DB_PATH):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row

    def list_registry(self, active_only=True):
        """任務就係 registry"""
        sql = "SELECT * FROM task WHERE 1=1"
        if active_only:
            sql += " AND is_active = 1"
        sql += " ORDER BY id"
        return [dict(r) for r in self.conn.execute(sql)]

    def close(self):
        self.conn.close()