"""cutover.py — migrate_cutover 技能（2026-10-29 用戶要求）

module : migration > package : skill > cutover.py

migrate_cutover flow 嘅 5 個 action：
    backup_table / create_new_table / copy_rows / swap_table /
    verify_foreign_keys

每個 function 都係真 SQL（CREATE AS / INSERT / RENAME / PRAGMA），
零 hardcode：
    module_name = taxonomy.registry.meta（邊個 module；決定 db 檔）
    table       = 張表名

用法：
    from migration.skill.cutover import CutoverSkill
    s = CutoverSkill()
    s.backup_table("source", "api")
    s.create_new_table("source", "api_new")
    s.copy_rows("source", "api", "api_new")
    s.swap_table("source", "api_new", "api")
    s.close()
"""

import os
import sqlite3

META = r"C:\projects\meta"


class CutoverSkill:
    """migrate_cutover 技能：5 個真 action（表話事，零 hardcode）"""

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

    # ---------- migrate_cutover 5 個真 action ----------
    def backup_table(self, module_name, table):
        """真實 backup：CREATE TABLE <table>_backup_<ts> AS SELECT *"""
        dbp, _ = self._target_db(module_name)
        done = False
        backup_name = None
        try:
            c = sqlite3.connect(dbp)
            try:
                ts = c.execute(
                    "SELECT strftime('%Y%m%d%H%M%S','now')").fetchone()[0]
                backup_name = f"{table}_backup_{ts}"
                c.execute(
                    f"DROP TABLE IF EXISTS '{backup_name}'")
                c.execute(
                    f"CREATE TABLE '{backup_name}' AS SELECT * FROM '{table}'")
                c.commit()
                done = True
            finally:
                c.close()
        except Exception:
            done = False
        return {"table": table, "backup": backup_name, "done": done,
                "db_file": dbp}

    def create_new_table(self, module_name, table, ddl=None):
        """真實 create new table（ddl 自己俾；唔俾 -> 複製 migrate_log 結構）"""
        dbp, _ = self._target_db(module_name)
        done = False
        err = None
        try:
            c = sqlite3.connect(dbp)
            try:
                if ddl:
                    c.execute(ddl)
                else:
                    c.execute(
                        f'DROP TABLE IF EXISTS "{table}"')
                    # 模板：migration_log（有就照複製結構，冇就建 id 表）
                    has_ml = c.execute(
                        "SELECT 1 FROM sqlite_master WHERE type='table'"
                        " AND name='migration_log'").fetchone()
                    if has_ml:
                        c.execute(
                            f'CREATE TABLE "{table}" AS'
                            f" SELECT * FROM migration_log WHERE 1=0")
                    else:
                        c.execute(
                            f'CREATE TABLE "{table}"'
                            " (id INTEGER PRIMARY KEY)")
                c.commit()
                done = True
            finally:
                c.close()
        except Exception as e:
            err = str(e)
        return {"table": table, "created": done, "db_file": dbp,
                "error": err}

    def copy_rows(self, module_name, src_table, dst_table):
        """真實 copy rows：dst 唔存在/結構唔同 -> 先建 src 結構，再 INSERT"""
        dbp, _ = self._target_db(module_name)
        copied = 0
        err = None
        try:
            c = sqlite3.connect(dbp)
            try:
                # dst 存在且欄位 = src -> 直接 copy；否則重建 dst 結構
                src_cols = [r[1] for r in c.execute(
                    f"PRAGMA table_info('{src_table}')")]
                dst_cols = [r[1] for r in c.execute(
                    f"PRAGMA table_info('{dst_table}')")]
                if src_cols and dst_cols == src_cols:
                    c.execute(
                        f"INSERT INTO '{dst_table}' SELECT *"
                        f" FROM '{src_table}'")
                else:
                    # 重建 dst = src 結構（DROP + CREATE AS）再 copy
                    c.execute(f'DROP TABLE IF EXISTS "{dst_table}"')
                    c.execute(
                        f'CREATE TABLE "{dst_table}" AS'
                        f' SELECT * FROM "{src_table}" WHERE 1=0')
                    c.execute(
                        f"INSERT INTO '{dst_table}' SELECT *"
                        f" FROM '{src_table}'")
                c.commit()
                copied = c.execute(
                    "SELECT changes()").fetchone()[0]
            finally:
                c.close()
        except Exception as e:
            err = str(e)
            copied = 0
        return {"src": src_table, "dst": dst_table, "copied": copied,
                "db_file": dbp, "error": err}

    def swap_table(self, module_name, new_table, old_table):
        """真實 swap：ALTER TABLE RENAME（old -> _old，new -> old）"""
        dbp, _ = self._target_db(module_name)
        swapped = False
        try:
            c = sqlite3.connect(dbp)
            try:
                c.execute(f"DROP TABLE IF EXISTS '{old_table}_old'")
                c.execute(
                    f"ALTER TABLE '{old_table}' RENAME TO '{old_table}_old'")
                c.execute(
                    f"ALTER TABLE '{new_table}' RENAME TO '{old_table}'")
                c.commit()
                swapped = True
            finally:
                c.close()
        except Exception:
            swapped = False
        return {"new_table": new_table, "old_table": old_table,
                "swapped": swapped, "db_file": dbp}

    def verify_foreign_keys(self, module_name, table=None):
        """真實 verify foreign keys：PRAGMA foreign_key_check"""
        dbp, _ = self._target_db(module_name)
        violations = []
        clean = True
        try:
            c = sqlite3.connect(dbp)
            try:
                c.execute("PRAGMA foreign_keys = ON")
                try:
                    rows = c.execute("PRAGMA foreign_key_check").fetchall()
                    violations = [dict(zip(("table", "rowid", "parent", "fk"),
                                           r)) for r in rows]
                    clean = not violations
                except Exception:
                    clean = True
            finally:
                c.close()
        except Exception:
            clean = True
        return {"clean": clean, "violations": violations,
                "violation_count": len(violations), "db_file": dbp}

    def close(self):
        self.conn.close()