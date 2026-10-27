"""sql.py — language.db 存取層（語言 + 顯示文字字典）

2026-10-25（用戶要求）：language 表由 definition.db 搬嚟 + display_text 表。
"""

import sqlite3

from .schema import *  # noqa: F401,E402

DB_PATH = r"language\language.db"


class SqlStore:
    def __init__(self, db_path=DB_PATH):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(LANGUAGE_DDL + DISPLAY_TEXT_DDL)
        self.conn.commit()

    # ---------- language（語言字典） ----------
    def languages(self, active_only=True):
        """列出全部語言"""
        sql = "SELECT * FROM language WHERE 1=1"
        if active_only:
            sql += " AND is_active = 1"
        sql += " ORDER BY id"
        return [dict(r) for r in self.conn.execute(sql)]

    def add_language(self, meta, description=None):
        """新增語言（冪等）"""
        self.conn.execute(
            "INSERT INTO language (meta, description)"
            " SELECT ?, ? WHERE NOT EXISTS"
            " (SELECT 1 FROM language WHERE meta = ?)",
            (meta, description, meta))
        self.conn.commit()
        r = self.conn.execute(
            "SELECT id FROM language WHERE meta = ?", (meta,)).fetchone()
        return r["id"] if r else None

    # ---------- display_text（顯示文字字典） ----------
    def display_texts(self, active_only=True):
        """列出全部顯示文字"""
        sql = "SELECT * FROM display_text WHERE 1=1"
        if active_only:
            sql += " AND is_active = 1"
        sql += " ORDER BY id"
        return [dict(r) for r in self.conn.execute(sql)]

    def add_display_text(self, meta, description=None):
        """新增顯示文字（冪等）"""
        self.conn.execute(
            "INSERT INTO display_text (meta, description)"
            " SELECT ?, ? WHERE NOT EXISTS"
            " (SELECT 1 FROM display_text WHERE meta = ?)",
            (meta, description, meta))
        self.conn.commit()
        r = self.conn.execute(
            "SELECT id FROM display_text WHERE meta = ?", (meta,)).fetchone()
        return r["id"] if r else None

    def close(self):
        self.conn.close()
