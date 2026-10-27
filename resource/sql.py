"""sql.py — resource.db 存取層"""

import sqlite3

from . import schema as _schema

DB_PATH = r"C:\projects\meta\resource\resource.db"


class SqlStore:
    def __init__(self, db_path=DB_PATH):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        try:
            for name in _schema.__all__:
                ddl = getattr(_schema, name)
                if isinstance(ddl, str):
                    self.conn.execute(ddl)
            for type_id, type_name in _schema.DEFAULT_TYPES:
                self.conn.execute(
                    'INSERT OR IGNORE INTO "type" (id, type) VALUES (?, ?)',
                    (type_id, type_name),
                )
            self.conn.commit()
        except Exception:
            self.conn.close()
            raise

    def close(self):
        self.conn.close()


__all__ = ["DB_PATH", "SqlStore"]
