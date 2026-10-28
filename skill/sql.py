"""skill module SQLite 存取層。

2026-10-27（用戶要求 redesign）：
    registry 表：id | name | resource_formula_id | resource_structure_id
    module_skill 表已移除（drop）
"""

import sqlite3

from .schema import REGISTRY_DDL

DB_PATH = r"C:\projects\meta\skill\skill.db"


class SqlStore:
    def __init__(self, db_path=DB_PATH):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._migrate_drop_module_skill()
        self.conn.execute(REGISTRY_DDL)
        self.conn.commit()

    def _migrate_drop_module_skill(self):
        """遷移（幂等）：drop 舊 module_skill 表（2026-10-27 用戶要求）"""
        has = self.conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table'"
            " AND name='module_skill'").fetchone()
        if has:
            self.conn.execute("DROP TABLE module_skill")
            self.conn.commit()
            print("[skill] drop 舊表 module_skill")
        # 舊 registry（module_id + value）-> drop（新 registry 表 name 設計）
        has = self.conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table'"
            " AND name='registry'").fetchone()
        if has:
            cols = {c[1] for c in self.conn.execute(
                "PRAGMA table_info('registry')")}
            if "name" not in cols:
                self.conn.execute("DROP TABLE registry")
                self.conn.commit()
                print("[skill] drop 舊 registry 表（module_id + value）")

    def registry(self, active_only=True):
        """列出技能（registry 表）"""
        sql = "SELECT * FROM registry WHERE 1=1"
        if active_only:
            sql += " AND is_active = 1"
        sql += " ORDER BY id"
        return [dict(row) for row in self.conn.execute(sql)]

    def register(self, name, resource_formula_id=None,
                 resource_structure_id=None):
        """登記一個技能（冪等：name 唯一）"""
        cur = self.conn.execute(
            "INSERT INTO registry (name, resource_formula_id,"
            " resource_structure_id)"
            " SELECT ?, ?, ? WHERE NOT EXISTS"
            " (SELECT 1 FROM registry WHERE name = ?)",
            (name, resource_formula_id, resource_structure_id, name))
        self.conn.commit()
        if cur.rowcount:
            return cur.lastrowid
        row = self.conn.execute(
            "SELECT id FROM registry WHERE name = ?", (name,)).fetchone()
        return row["id"] if row else None

    def skill_id(self, name):
        """由技能名攞 id（唔存在 None）"""
        row = self.conn.execute(
            "SELECT id FROM registry WHERE name = ?", (name,)).fetchone()
        return row["id"] if row else None

    def close(self):
        self.conn.close()
