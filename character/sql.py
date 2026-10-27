"""sql.py — character.db 存取層"""

import sqlite3

import character.schema as _schema

DB_PATH = r"C:\projects\meta\character\character.db"


class SqlStore:
    def __init__(self, db_path=DB_PATH):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        try:
            for ddl in _schema.__all__:
                self.conn.execute(getattr(_schema, ddl))
            self.conn.commit()
        except Exception:
            self.conn.close()
            raise

    # ---------- 字符集 ----------
    def charset_values(self, table, active_only=True):
        """由字符集表攞全部字符（set[str]）

        table = symbol / letter / INT
        letter 特殊：value 欄（每行一個字母）
        """
        if table == "letter":
            sql = ("SELECT value FROM letter WHERE value IS NOT NULL"
                   " AND is_active = 1")
            return {r["value"] for r in self.conn.execute(sql)}
        sql = f'SELECT value FROM "{table}" WHERE value IS NOT NULL'
        if active_only:
            sql += " AND is_active = 1 AND source_id IS NOT NULL"
        return {r["value"] for r in self.conn.execute(sql)}

    def charset_rows(self, table, active_only=True):
        """字符集表全部行（list[dict]）"""
        sql = f'SELECT * FROM "{table}"'
        if active_only:
            sql += " WHERE is_active = 1"
        sql += " ORDER BY id"
        return [dict(r) for r in self.conn.execute(sql)]

    def commit(self):
        self.conn.commit()

    def close(self):
        self.conn.close()