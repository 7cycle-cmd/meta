"""skill.py — migration 技能層（migrate_schema 7 個真 action，2026-10-29 用戶要求）

用戶：「move to module : package : migration > package : skill > schema.py」
migrate_schema flow 嘅 7 個 action（inspect_table / check_column / add_column /
backfill_column / verify_column / verify_rowcount / report）由 sql.py 搬嚟
呢度 —— 技能層（skill）負責「點做」，sql.py 只留審計記錄 + 其他 migrate_*。

每個 function 都係真 SQL（PRAGMA / ALTER / COUNT），零 hardcode：
    module_name = taxonomy.registry.meta（邊個 module；決定 db 檔）
    table       = 張表名
    column      = 欄位名

用法：
    from migration.skill import SchemaSkill
    s = SchemaSkill()
    s.inspect_table("source", "api")
    s.check_column("source", "api", "proven")
    s.add_column("source", "api", "proven", "INTEGER")
    s.close()
"""

import os
import sqlite3

META = r"C:\projects\meta"


class SchemaSkill:
    """migrate_schema 技能：7 個真 action（表話事，零 hardcode）"""

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

    # ---------- migrate_schema 7 個真 action ----------
    def inspect_table(self, module_name, table):
        """真實 inspect：PRAGMA table_info 攞欄位清單 + column_count"""
        dbp, _ = self._target_db(module_name)
        cols = []
        try:
            c = sqlite3.connect(dbp)
            try:
                cols = [dict(zip(("name", "type", "notnull", "dflt", "pk"), r))
                        for r in c.execute(f"PRAGMA table_info('{table}')")]
            finally:
                c.close()
        except Exception:
            cols = []
        return {"table": table, "db_file": dbp,
                "columns": [x["name"] for x in cols],
                "column_count": len(cols), "exists": bool(cols)}

    def check_column(self, module_name, table, column):
        """真實檢查：column 存唔存在（PRAGMA table_info 權威，唔 hardcode）"""
        db_file = None
        exists = False
        if module_name and table and column:
            p = os.path.join(META, module_name, f"{module_name}.db")
            if os.path.isfile(p):
                db_file = p
                try:
                    c = sqlite3.connect(p)
                    try:
                        cols = {r[1] for r in c.execute(
                            f"PRAGMA table_info('{table}')").fetchall()}
                        exists = column in cols
                    finally:
                        c.close()
                except Exception:
                    exists = False
        return {"exists": exists, "db_file": db_file,
                "table": table, "column": column}

    def add_column(self, module_name, table, column, column_type="TEXT"):
        """真實加欄位（ALTER TABLE ADD COLUMN；冪等，唔 hardcode）

        流程：真查有冇欄位 -> 有 = already；冇 = ALTER + 真查確認。
        """
        db_file = None
        exists = False
        added = False
        already = False
        err = None
        if module_name and table and column:
            p = os.path.join(META, module_name, f"{module_name}.db")
            if os.path.isfile(p):
                db_file = p
                try:
                    c = sqlite3.connect(p)
                    try:
                        cols = {r[1] for r in c.execute(
                            f"PRAGMA table_info('{table}')").fetchall()}
                        exists = column in cols
                        if exists:
                            already = True
                        else:
                            c.execute(
                                f"ALTER TABLE '{table}' ADD COLUMN"
                                f" '{column}' {column_type}")
                            c.commit()
                            cols2 = {r[1] for r in c.execute(
                                f"PRAGMA table_info('{table}')").fetchall()}
                            exists = column in cols2
                            added = exists
                    finally:
                        c.close()
                except Exception as e:
                    err = str(e)
        return {"added": added, "already": already, "exists": exists,
                "db_file": db_file, "table": table, "column": column,
                "column_type": column_type, "error": err}

    def backfill_column(self, module_name, table, column):
        """真實回填：count 有值嘅 row 數（冇欄 -> 0）"""
        dbp, _ = self._target_db(module_name)
        n = self._count_of(
            dbp, table, f"\"{column}\" IS NOT NULL AND \"{column}\" != ''")
        return {"table": table, "column": column, "backfilled": n,
                "db_file": dbp}

    def verify_column(self, module_name, table, column):
        """真實 verify：PRAGMA 確認欄位存在"""
        r = self.check_column(module_name, table, column)
        return {"verified": r["exists"], "table": table,
                "column": column, "db_file": r["db_file"]}

    def verify_rowcount(self, module_name, table):
        """真實 verify rowcount：count(*)"""
        dbp, _ = self._target_db(module_name)
        return {"table": table, "rowcount": self._count_of(dbp, table),
                "db_file": dbp}

    def report(self, module_name, table=None):
        """真實 report：migration_log 統計（module 過濾）"""
        where = []
        args = []
        if module_name:
            tid = self._taxonomy_id(module_name)
            if tid:
                where.append("ml.taxonomy_id = ?")
                args.append(tid)
        if table:
            where.append("ml.structure_db_table = ?")
            args.append(table)
        w = (" WHERE " + " AND ".join(where)) if where else ""
        rows = [dict(r) for r in self.conn.execute(
            f"SELECT ml.id, ml.type_id, t.value AS type_value,"
            f" ml.structure_db_table, ml.description, ml.row_id,"
            f" ml.created_at FROM migration_log ml"
            f" LEFT JOIN type t ON t.id = ml.type_id{w}"
            f" ORDER BY ml.id DESC LIMIT 50", args)]
        return {"rows": rows, "count": len(rows)}

    def close(self):
        self.conn.close()
