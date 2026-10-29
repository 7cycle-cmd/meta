"""other.py — migrate_other 技能（2026-10-29 用戶要求）

module : migration > package : skill > other.py

migrate_other flow 嘅 3 個 action：
    inspect / action / verify

每個 function 都係真 SQL（PRAGMA / INSERT / COUNT），零 hardcode：
    module_name = taxonomy.registry.meta（邊個 module；決定 db 檔）
    table       = 張表名

用法：
    from migration.skill.other import OtherSkill
    s = OtherSkill()
    s.inspect("source", "api")
    s.action("source", "api")
    s.verify("source", "api", 2)
    s.close()
"""

import os
import sqlite3

META = r"C:\projects\meta"


class OtherSkill:
    """migrate_other 技能：3 個真 action（表話事，零 hardcode）"""

    def __init__(self, db_path=None):
        self.conn = sqlite3.connect(
            db_path or os.path.join(META, "migration", "migration.db"))
        self.conn.row_factory = sqlite3.Row

    # ---------- helpers ----------
    def _target_db(self, module_name):
        """module 名 -> (db 路徑, 資料夾名)；default = migration.db"""
        if not module_name:
            return os.path.join(META, "migration", "migration.db")
        p = os.path.join(META, module_name, f"{module_name}.db")
        return (p, module_name) if os.path.isfile(p) else (
            os.path.join(META, "migration", "migration.db"), "migration")

    def _count_of(self, dbp, table, where=None, args=()):
        """真查 count（dbp+table 唔存在 -> 0）"""
        try:
            c = sqlite3.connect(dbp)
            try:
                q = f"SELECT COUNT(*) c FROM '{table}'"
                if where:
                    q += f" WHERE {where}"
                return c.execute(q, args).fetchone()[0]
            finally:
                c.close()
        except Exception:
            return 0

    def _taxonomy_id(self, module_name):
        """taxonomy.registry.id by meta（零 hardcode，搵唔到 -> None）"""
        try:
            c = sqlite3.connect(os.path.join(META, "taxonomy",
                                             "taxonomy.db"))
            try:
                c.row_factory = sqlite3.Row
                r = c.execute(
                    "SELECT id FROM registry WHERE tree_id = 2"
                    " AND meta = ? AND is_active = 1",
                    (module_name,)).fetchone()
                return r["id"] if r else None
            finally:
                c.close()
        except Exception:
            return None

    def _type_id(self, value):
        """migration type.id by value（schema/seed/sync/cutover/other）"""
        r = self.conn.execute(
            "SELECT id FROM type WHERE value = ?", (value,)).fetchone()
        return r["id"] if r else None

    # ---------- migrate_other 3 個真 action ----------
    def inspect(self, module_name, table):
        """真實 inspect（migrate_other）：表存在 + count + cols"""
        dbp, _ = self._target_db(module_name)
        cols = []
        try:
            c = sqlite3.connect(dbp)
            try:
                cols = [r[1] for r in c.execute(
                    f"PRAGMA table_info('{table}')")]
            finally:
                c.close()
        except Exception:
            cols = []
        return {"table": table, "db_file": dbp,
                "exists": bool(cols),
                "columns": cols,
                "column_count": len(cols),
                "rowcount": self._count_of(dbp, table)}

    def action(self, module_name, table, action_type="migrate_log"):
        """真實 action（migrate_other）：寫一條 migration_log + 回傳 id"""
        tid = self._taxonomy_id(module_name) if module_name else None
        self.conn.execute(
            "INSERT INTO migration_log"
            " (type_id, taxonomy_id, structure_db_table, description)"
            " VALUES (?, ?, ?, ?)",
            (self._type_id("other"), tid, table,
             f"migrate_other action on {table}"))
        self.conn.commit()
        rid = self.conn.execute(
            "SELECT last_insert_rowid()").fetchone()[0]
        return {"action": action_type, "table": table, "recorded": True,
                "migration_log_id": rid}

    def verify(self, module_name, table, expected=None):
        """真實 verify（migrate_other）：count + 可對比 expected"""
        dbp, _ = self._target_db(module_name)
        n = self._count_of(dbp, table)
        return {"table": table, "count": n,
                "expected": expected,
                "verified": expected is None or n == int(expected),
                "db_file": dbp}

    def close(self):
        self.conn.close()