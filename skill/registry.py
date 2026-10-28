# registry.py — skill package 嘅名稱註冊表（SSOT）
# 2026-10-27（用戶要求 redesign）：registry 表 = id | name | resource_formula_id | resource_structure_id
# 技能註冊 = registry 表本身（唔再另建 meta 字典）

import sqlite3

DB_PATH = "C:/projects/meta/skill/skill.db"


class RegistryStore:
    def __init__(self, db_path=DB_PATH):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row

    def list_registry(self, active_only=True):
        sql = "SELECT * FROM registry WHERE 1=1"
        if active_only:
            sql += " AND is_active = 1"
        sql += " ORDER BY id"
        return [dict(r) for r in self.conn.execute(sql)]

    def register(self, name, resource_formula_id=None,
                 resource_structure_id=None):
        """登記一個技能（冪等：name 唯一）"""
        self.conn.execute(
            "INSERT INTO registry (name, resource_formula_id,"
            " resource_structure_id)"
            " SELECT ?, ?, ? WHERE NOT EXISTS"
            " (SELECT 1 FROM registry WHERE name = ?)",
            (name, resource_formula_id, resource_structure_id, name))
        self.conn.commit()
        r = self.conn.execute(
            "SELECT id FROM registry WHERE name = ?", (name,)).fetchone()
        return r["id"] if r else None

    def close(self):
        self.conn.close()
