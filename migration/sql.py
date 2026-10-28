"""sql.py — migration.db 存取層（遷移審計日誌）

概念（2026-10-28 用戶設計）：
    migration ≠ api（api 係對外介面）
    sync 係 migration 一種（migration_type 區分）
    呢張表 = 每個 module 改過邊張表邊行嘅完整記錄
"""

import sqlite3

from .schema import MIGRATION_LOG_DDL  # noqa: F401（逐個 symbol，permit 化）

DB_PATH = r"C:\projects\meta\migration\migration.db"


class SqlStore:
    def __init__(self, db_path=DB_PATH):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute(MIGRATION_LOG_DDL)
        self.conn.commit()

    # ---------- 記錄 ----------
    def record(self, module_name, table=None, migration_type="schema",
               description=None, run_id=None, api_id=None, row_id=0):
        """記錄一次 migration（冪等：同 run + module + table + desc 唔重複）

        module_name = taxonomy.registry.meta（邊個 module）
        table       = 改邊張表（db_table 名）
        migration_type = schema / seed / sync / cutover / other
        run_id      = run.id（有先）
        api_id      = api.id（經 api 觸發先有）
        row_id      = 改邊行（0 = 全表）
        """
        # taxonomy_id 反查（零 hardcode）
        taxonomy_id = self._taxonomy_id(module_name)
        if table:
            self.conn.execute(
                "INSERT INTO migration_log"
                " (run_id, api_id, taxonomy_id, structure_db_table,"
                "  migration_type, description, row_id)"
                " SELECT ?, ?, ?, ?, ?, ?, ? WHERE NOT EXISTS"
                " (SELECT 1 FROM migration_log WHERE run_id IS ?"
                "  AND taxonomy_id IS ? AND structure_db_table IS ?"
                "  AND migration_type = ? AND description IS ?)",
                (run_id, api_id, taxonomy_id, table, migration_type,
                 description, row_id,
                 run_id, taxonomy_id, table, migration_type, description))
        else:
            self.conn.execute(
                "INSERT INTO migration_log"
                " (run_id, api_id, taxonomy_id, structure_db_table,"
                "  migration_type, description, row_id)"
                " SELECT ?, ?, ?, NULL, ?, ?, ? WHERE NOT EXISTS"
                " (SELECT 1 FROM migration_log WHERE run_id IS ?"
                "  AND taxonomy_id IS ? AND structure_db_table IS NULL"
                "  AND migration_type = ? AND description IS ?)",
                (run_id, api_id, taxonomy_id, migration_type,
                 description, row_id,
                 run_id, taxonomy_id, migration_type, description))
        self.conn.commit()
        r = self.conn.execute(
            "SELECT id FROM migration_log WHERE run_id IS ?"
            " AND taxonomy_id IS ? AND structure_db_table IS ?"
            " AND migration_type = ? AND description IS ?",
            (run_id, taxonomy_id, table, migration_type, description)).fetchone()
        return r["id"] if r else None

    def _taxonomy_id(self, module_name):
        """taxonomy.registry.id by meta（零 hardcode，搵唔到 -> None）"""
        try:
            import sqlite3 as _sq
            c = _sq.connect(r"C:\projects\meta\taxonomy\taxonomy.db")
            try:
                c.row_factory = _sq.Row
                r = c.execute(
                    "SELECT id FROM registry WHERE meta = ?"
                    " AND tree_id = 2 AND is_active = 1",
                    (module_name,)).fetchone()
                return r["id"] if r else None
            finally:
                c.close()
        except Exception:
            return None

    # ---------- 查詢 ----------
    def logs(self, module_name=None, migration_type=None, limit=100):
        """列出 migration 記錄（可按 module / type 篩選）"""
        args = []
        where = []
        if module_name:
            tid = self._taxonomy_id(module_name)
            where.append("ml.taxonomy_id = ?")
            args.append(tid)
        if migration_type:
            where.append("ml.migration_type = ?")
            args.append(migration_type)
        sql = ("SELECT * FROM migration_log ml")
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY ml.id DESC LIMIT ?"
        args.append(limit)
        rows = [dict(r) for r in self.conn.execute(sql, args)]
        # 補 module 名（跨 DB，SQL JOIN 唔到）
        mods = self._module_names()
        for r in rows:
            r["module_name"] = mods.get(r.get("taxonomy_id"))
        return rows

    def _module_names(self):
        """taxonomy_id -> meta map"""
        try:
            import sqlite3 as _sq
            c = _sq.connect(r"C:\projects\meta\taxonomy\taxonomy.db")
            try:
                c.row_factory = _sq.Row
                return {r["id"]: r["meta"] for r in c.execute(
                    "SELECT id, meta FROM registry WHERE tree_id = 2"
                    " AND is_active = 1")}
            finally:
                c.close()
        except Exception:
            return {}

    def count(self):
        return self.conn.execute(
            "SELECT COUNT(*) FROM migration_log").fetchone()[0]

    def by_module(self):
        """按 module 統計"""
        return [dict(r) for r in self.conn.execute(
            "SELECT taxonomy_id, migration_type, COUNT(*) AS n"
            " FROM migration_log GROUP BY taxonomy_id, migration_type"
            " ORDER BY n DESC")]

    def commit(self):
        self.conn.commit()

    def close(self):
        self.conn.close()
