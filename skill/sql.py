"""skill module SQLite 存取層。"""

import sqlite3

from .schema import MODULE_SKILL_DDL, REGISTRY_DDL

DB_PATH = r"C:\projects\meta\skill\skill.db"


class SqlStore:
    def __init__(self, db_path=DB_PATH):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(REGISTRY_DDL + MODULE_SKILL_DDL)
        self.conn.commit()

    def registry(self, module_id=None):
        sql = "SELECT id, module_id, value FROM registry"
        args = ()
        if module_id is not None:
            sql += " WHERE module_id = ?"
            args = (module_id,)
        sql += " ORDER BY id"
        return [dict(row) for row in self.conn.execute(sql, args)]

    def register(self, module_id, value):
        self.conn.execute(
            "INSERT OR IGNORE INTO registry (module_id, value) VALUES (?, ?)",
            (module_id, value))
        self.conn.commit()
        row = self.conn.execute(
            "SELECT id FROM registry WHERE module_id = ? AND value = ?",
            (module_id, value)).fetchone()
        return row["id"] if row else None

    def module_skills(self, skill_id=None):
        sql = "SELECT id, skill_id, flow_id, value_id FROM module_skill"
        args = ()
        if skill_id is not None:
            sql += " WHERE skill_id = ?"
            args = (skill_id,)
        sql += " ORDER BY id"
        return [dict(row) for row in self.conn.execute(sql, args)]

    def link(self, skill_id, flow_id, value_id):
        self.conn.execute(
            "INSERT OR IGNORE INTO module_skill"
            " (skill_id, flow_id, value_id) VALUES (?, ?, ?)",
            (skill_id, flow_id, value_id))
        self.conn.commit()
        row = self.conn.execute(
            "SELECT id FROM module_skill"
            " WHERE skill_id = ? AND flow_id = ? AND value_id = ?",
            (skill_id, flow_id, value_id)).fetchone()
        return row["id"] if row else None

    def close(self):
        self.conn.close()
