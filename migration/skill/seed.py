"""seed.py — migrate_seed 技能（2026-10-29 用戶要求）

module : migration > package : skill > seed.py

migrate_seed flow 嘅 4 個 action：
    check_dictionary / check_symbol / insert_symbol / verify_symbol

每個 function 都係真 SQL（SELECT / INSERT，冪等），零 hardcode：
    module_name = taxonomy.registry.meta（邊個 module；決定 db 檔）
    table       = 張表名
    symbol      = symbol 值

用法：
    from migration.skill.seed import SeedSkill
    s = SeedSkill()
    s.check_symbol("source", "symbol", "ABILITY")
    s.insert_symbol("source", "symbol", "ACTION", "desc")
    s.close()
"""

import os
import sqlite3

META = r"C:\projects\meta"


class SeedSkill:
    """migrate_seed 技能：4 個真 action（表話事，零 hardcode）"""

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

    def _rows_of(self, dbp, table, where=None, args=()):
        """真查 rows（dbp+table 唔存在 -> []）"""
        try:
            c = sqlite3.connect(dbp)
            try:
                c.row_factory = sqlite3.Row
                q = f"SELECT * FROM '{table}'"
                if where:
                    q += f" WHERE {where}"
                return [dict(r) for r in c.execute(q, args)]
            finally:
                c.close()
        except Exception:
            return []

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

    # ---------- migrate_seed 4 個真 action ----------
    def check_dictionary(self, module_name, table):
        """真實 check dictionary：已有值清單（table 唔存在 -> []）"""
        dbp, _ = self._target_db(module_name)
        rows = self._rows_of(dbp, table)
        return {"table": table, "rows": rows, "count": len(rows),
                "db_file": dbp}

    def check_symbol(self, module_name, table, symbol, column="symbol"):
        """真實 check symbol：SELECT 有冇呢個 symbol（0/1）"""
        dbp, _ = self._target_db(module_name)
        n = self._count_of(dbp, table, f"\"{column}\" = ?", (symbol,))
        return {"table": table, "symbol": symbol, "exists": n > 0,
                "found": n, "db_file": dbp}

    def insert_symbol(self, module_name, table, symbol, description=None,
                      column="symbol"):
        """真實 insert symbol（冪等：先查後插，WHERE NOT EXISTS）"""
        dbp, _ = self._target_db(module_name)
        inserted = False
        exists = self._count_of(dbp, table, f"\"{column}\" = ?",
                                (symbol,)) > 0
        if not exists:
            try:
                c = sqlite3.connect(dbp)
                try:
                    if description is not None:
                        c.execute(
                            f"INSERT INTO '{table}' (\"{column}\","
                            f" description) SELECT ?, ? WHERE NOT EXISTS"
                            f" (SELECT 1 FROM '{table}'"
                            f"  WHERE \"{column}\" = ?)",
                            (symbol, description, symbol))
                    else:
                        c.execute(
                            f"INSERT INTO '{table}' (\"{column}\")"
                            f" SELECT ? WHERE NOT EXISTS"
                            f" (SELECT 1 FROM '{table}'"
                            f"  WHERE \"{column}\" = ?)",
                            (symbol, symbol))
                    c.commit()
                    inserted = True
                finally:
                    c.close()
            except Exception:
                inserted = False
        return {"table": table, "symbol": symbol, "inserted": inserted,
                "already": exists, "exists": exists or inserted,
                "db_file": dbp}

    def verify_symbol(self, module_name, table, symbol, column="symbol"):
        """真實 verify symbol：SELECT 確認存在"""
        r = self.check_symbol(module_name, table, symbol, column)
        return {"verified": r["exists"], "table": table, "symbol": symbol,
                "db_file": r["db_file"]}

    def close(self):
        self.conn.close()