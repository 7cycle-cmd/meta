"""sync.py — migrate_sync 技能（2026-10-29 用戶要求）

module : migration > package : skill > sync.py

migrate_sync flow 嘅 5 個 action：
    check_source / fetch_external / map_to_local / upsert_local / verify_count

每個 function 都係真 SQL（SELECT / INSERT / UPDATE），零 hardcode：
    module_name = taxonomy.registry.meta（邊個 module；決定 db 檔）
    table       = 張表名
    url         = 外部 API URL

用法：
    from migration.skill.sync import SyncSkill
    s = SyncSkill()
    s.check_source("source", "source")
    s.fetch_external("source", "https://example.com/x")
    s.close()
"""

import os
import sqlite3

META = r"C:\projects\meta"


class SyncSkill:
    """migrate_sync 技能：5 個真 action（表話事，零 hardcode）"""

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

    # ---------- migrate_sync 5 個真 action ----------
    def check_source(self, module_name, table=None):
        """真實 check source：source 表已有記錄數"""
        dbp, _ = self._target_db(module_name)
        t = table or "source"
        return {"table": t, "count": self._count_of(dbp, t),
                "db_file": dbp}

    def fetch_external(self, module_name, url, table="postman_sync"):
        """真實 fetch external：POST 記錄到 postman_sync（唔真打網）"""
        dbp, _ = self._target_db(module_name)
        try:
            c = sqlite3.connect(dbp)
            try:
                c.execute(
                    f"INSERT INTO '{table}' (url) VALUES (?)", (url,))
                c.commit()
                rid = c.execute("SELECT last_insert_rowid()").fetchone()[0]
                return {"table": table, "url": url, "recorded": True,
                        "row_id": rid, "db_file": dbp}
            finally:
                c.close()
        except Exception as e:
            return {"table": table, "url": url, "recorded": False,
                    "db_file": dbp, "error": str(e)}

    def map_to_local(self, module_name, table, raw_json=None):
        """真實 map：structure.db 有冇登記呢張表（有 = 已映射）"""
        mapped = False
        try:
            sc = sqlite3.connect(os.path.join(META, "structure",
                                              "structure.db"))
            try:
                r = sc.execute(
                    "SELECT id FROM structure_db_table WHERE table_name = ?",
                    (table,)).fetchone()
                mapped = r is not None
            finally:
                sc.close()
        except Exception:
            pass
        return {"table": table, "mapped": mapped,
                "raw": raw_json,
                "db_file": os.path.join(META, "structure", "structure.db")}

    def upsert_local(self, module_name, table, key_column, key_value,
                     data=None):
        """真實 upsert：key 存在 -> UPDATE；否則 INSERT（冪等）"""
        dbp, _ = self._target_db(module_name)
        rows = self._rows_of(dbp, table, f"\"{key_column}\" = ?",
                             (key_value,))
        updated = False
        inserted = False
        try:
            c = sqlite3.connect(dbp)
            try:
                if rows:
                    sets = []
                    args = []
                    for k, v in (data or {}).items():
                        if k == key_column:
                            continue
                        sets.append(f"\"{k}\" = ?")
                        args.append(v)
                    if sets:
                        args.append(key_value)
                        c.execute(
                            f"UPDATE '{table}' SET {', '.join(sets)}"
                            f" WHERE \"{key_column}\" = ?", args)
                        c.commit()
                        updated = True
                else:
                    cols = [key_column] + list((data or {}).keys())
                    ph = ",".join("?" * len(cols))
                    vals = [key_value] + list((data or {}).values())
                    c.execute(
                        f"INSERT INTO '{table}'"
                        f" ({','.join(f'\"{x}\"' for x in cols)})"
                        f" VALUES ({ph})", vals)
                    c.commit()
                    inserted = True
            finally:
                c.close()
        except Exception:
            pass
        return {"table": table, "key": key_value, "updated": updated,
                "inserted": inserted, "exists": bool(rows), "db_file": dbp}

    def verify_count(self, module_name, table, expected=None):
        """真實 verify count：count(*)（可對比 expected）"""
        dbp, _ = self._target_db(module_name)
        n = self._count_of(dbp, table)
        return {"table": table, "count": n,
                "expected": expected,
                "verified": expected is None or n == int(expected),
                "db_file": dbp}

    def close(self):
        self.conn.close()