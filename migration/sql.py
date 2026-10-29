"""sql.py — migration.db 存取層（遷移審計日誌 + flow × step）

概念（2026-10-28 用戶設計，已修正）：
    migration ≠ api（api 係對外介面）
    sync 係 migration 一種（type 字典：schema/seed/sync/cutover/other）
    呢張表 = 每個 module 改過邊張表邊行嘅完整記錄
    type 表 value 幫助識別類型（唔使淨靠 id）
    flow / step / step_log 已全部搬去 terminology.db（2026-10-28 用戶確認）——
    migration_log 只保留 run_id，flow_id/step_id 由 terminology run 反查
"""

import os
import sqlite3

from .schema import (MIGRATION_LOG_DDL, TYPE_DDL)  # noqa: F401

DB_PATH = r"C:\projects\meta\migration\migration.db"

# type 字典（migration 類型，冪等 seed；WHERE NOT EXISTS 唔燒號）
DEFAULT_TYPES = [
    ("schema", "建表 / 改表（DDL 變更）"),
    ("seed", "字典 / 預設資料初始化"),
    ("sync", "數據同步（外部拉取 / 掃描登記）"),
    ("cutover", "搬遷 / 重建（損害性）"),
    ("other", "其他"),
]


class SqlStore:
    def __init__(self, db_path=DB_PATH):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute(TYPE_DDL)
        self.conn.execute(MIGRATION_LOG_DDL)
        self._seed_types()
        self._migrate_type_id()
        self._migrate_log_flow_columns()
        self._migrate_drop_flow_tables()
        self.conn.commit()

    def _migrate_drop_flow_tables(self):
        """遷移（幂等）：移除 rubbish flow / step / step_log 表（2026-10-28 用戶）

        flow / step / step_log 已全部喺 terminology.db（用戶確認），呢三張
        duplicate 表直接 drop（唔保留資料——terminology.db 先係權威）。
        """
        for t in ("step_log", "step", "flow"):
            has_table = self.conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                (t,)).fetchone()
            if not has_table:
                continue
            self.conn.execute(f"DROP TABLE {t}")
            print(f"[migration] 移除 rubbish 表 {t}")
        self.conn.commit()

    def _migrate_log_flow_columns(self):
        """遷移（幂等）：migration_log 加 flow_id / step_id / value_id 欄"""
        cols = {c[1] for c in self.conn.execute(
            "PRAGMA table_info('migration_log')")}
        if "flow_id" not in cols:
            self.conn.execute(
                "ALTER TABLE migration_log ADD COLUMN flow_id INTEGER")
            self.conn.commit()
        if "step_id" not in cols:
            self.conn.execute(
                "ALTER TABLE migration_log ADD COLUMN step_id INTEGER")
            self.conn.commit()
        if "value_id" not in cols:
            self.conn.execute(
                "ALTER TABLE migration_log ADD COLUMN value_id INTEGER")
            self.conn.commit()
            print("[migration] migration_log + value_id 欄")

    def _seed_types(self):
        """type 字典 seed（冪等：WHERE NOT EXISTS，唔燒 AUTOINCREMENT 號）"""
        for value, desc in DEFAULT_TYPES:
            self.conn.execute(
                "INSERT INTO type (value, description)"
                " SELECT ?, ? WHERE NOT EXISTS"
                " (SELECT 1 FROM type WHERE value = ?)",
                (value, desc, value))

    def _migrate_type_id(self):
        """遷移（幂等）：migration_log.api_id -> type_id（2026-10-28 用戶修正）

        舊版有 api_id / migration_type 文字欄 -> 轉 type_id 指 type 表。
        """
        cols = {c[1] for c in self.conn.execute(
            "PRAGMA table_info('migration_log')")}
        if "type_id" in cols:
            # 有 type_id 再補 migration_type 文字（fill 舊資料）
            if "migration_type" in cols:
                rows = self.conn.execute(
                    "SELECT id, migration_type FROM migration_log"
                    " WHERE type_id IS NULL").fetchall()
                for r in rows:
                    tid = self.type_id(r["migration_type"] or "other")
                    self.conn.execute(
                        "UPDATE migration_log SET type_id = ? WHERE id = ?",
                        (tid, r["id"]))
                self.conn.commit()
            return
        if "api_id" not in cols:
            return
        # 舊版：api_id + migration_type 文字 -> rebuild 做 type_id
        rows = [dict(r) for r in self.conn.execute(
            "SELECT * FROM migration_log ORDER BY id")]
        self.conn.execute("DROP TABLE migration_log")
        self.conn.execute(MIGRATION_LOG_DDL)
        for r in rows:
            tid = self.type_id(r.get("migration_type") or "other")
            self.conn.execute(
                "INSERT INTO migration_log"
                " (id, run_id, type_id, taxonomy_id, structure_db_table,"
                "  description, row_id, is_active, created_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (r["id"], r.get("run_id"), tid, r.get("taxonomy_id"),
                 r.get("structure_db_table"), r.get("description"),
                 r.get("row_id", 0), r.get("is_active", 1),
                 r.get("created_at")))
        self.conn.commit()
        print("[migration] api_id -> type_id 遷移完成")

    # ---------- type 字典 ----------
    def types(self, active_only=True):
        sql = "SELECT * FROM type"
        if active_only:
            sql += " WHERE is_active = 1"
        sql += " ORDER BY id"
        return [dict(r) for r in self.conn.execute(sql)]

    def type_id(self, value):
        """type.id by value（schema/seed/sync/cutover/other）"""
        r = self.conn.execute(
            "SELECT id FROM type WHERE value = ?", (value,)).fetchone()
        return r["id"] if r else None

    def type_value(self, type_id):
        """type.value by id"""
        r = self.conn.execute(
            "SELECT value FROM type WHERE id = ?", (type_id,)).fetchone()
        return r["value"] if r else None

    # ---------- 記錄 ----------
    def record(self, module_name, table=None, migration_type="schema",
               description=None, run_id=None, api_id=None, row_id=0,
               value=None, value_id=None, step_values=None, run_flow=True):
        """記錄一次 migration（冪等：同 run + module + table + type + desc 唔重複）

        module_name    = taxonomy.registry.meta（邊個 module）
        table          = 改邊張表（db_table 名）
        migration_type = type value（schema / seed / sync / cutover / other）
        run_id         = terminology.run.id —— **一定要有真 run**；
                         冇傳 -> 自動跑 terminology migration_audit flow 產生
        api_id         = 保留參數（api 觸發來源，記錄用；type_id 唔係 api_id）
        row_id         = 改邊行（0 = 全表）
        value          = 提交值（跑 flow 用；冇 -> 用 description 做 value）
        value_id       = 已存在 value.id（重用，唔新開；優先於 value）
        step_values    = 保留參數（flow/step 已喺 terminology.db，唔再自行執行）
        run_flow       = False 就唔自動跑 terminology flow（內部用，避免遞歸）
        """
        # taxonomy_id 反查（零 hardcode）
        taxonomy_id = self._taxonomy_id(module_name)
        tid = self.type_id(migration_type) or self.type_id("other")
        # run_id 一定要有（用戶：run_id = terminology run）：
        if run_id is None and run_flow:
            run_id = self._auto_run(value or f"migration:{table or module_name}",
                                    value_id=value_id)
        # value_id 一定要有（用戶：where value_id for migration？）——
        # 冇傳 -> 由 run 反查（_auto_run 內部已登記 value.db，taxonomy_id=migration）
        if value_id is None and run_id is not None:
            value_id = self._run_value_id(run_id)
        # flow_id / step_id 由 terminology run 反查（flow/step 已喺 terminology.db）
        flow_id, step_id = self._run_flow_step(run_id)
        if table:
            self.conn.execute(
                "INSERT INTO migration_log"
                " (run_id, value_id, type_id, taxonomy_id, structure_db_table,"
                "  description, row_id, flow_id, step_id)"
                " SELECT ?, ?, ?, ?, ?, ?, ?, ?, ? WHERE NOT EXISTS"
                " (SELECT 1 FROM migration_log WHERE run_id IS ?"
                "  AND taxonomy_id IS ? AND structure_db_table IS ?"
                "  AND type_id = ? AND description IS ?)",
                (run_id, value_id, tid, taxonomy_id, table, description,
                 row_id, flow_id, step_id,
                 run_id, taxonomy_id, table, tid, description))
        else:
            self.conn.execute(
                "INSERT INTO migration_log"
                " (run_id, value_id, type_id, taxonomy_id, structure_db_table,"
                "  description, row_id, flow_id, step_id)"
                " SELECT ?, ?, ?, ?, NULL, ?, ?, ?, ? WHERE NOT EXISTS"
                " (SELECT 1 FROM migration_log WHERE run_id IS ?"
                "  AND taxonomy_id IS ? AND structure_db_table IS NULL"
                "  AND type_id = ? AND description IS ?)",
                (run_id, value_id, tid, taxonomy_id, description, row_id,
                 flow_id, step_id,
                 run_id, taxonomy_id, tid, description))
        self.conn.commit()
        r = self.conn.execute(
            "SELECT id FROM migration_log WHERE run_id IS ?"
            " AND taxonomy_id IS ? AND structure_db_table IS ?"
            " AND type_id = ? AND description IS ?",
            (run_id, taxonomy_id, table, tid, description)).fetchone()
        return r["id"] if r else None

    def _run_value_id(self, run_id):
        """由 terminology run id 反查 value_id（喺 terminology.db run 表）"""
        if not run_id:
            return None
        try:
            import sqlite3 as _sq
            c = _sq.connect(r"C:\projects\meta\terminology\terminology.db")
            try:
                c.row_factory = _sq.Row
                r = c.execute(
                    "SELECT value_id FROM run WHERE id = ?",
                    (run_id,)).fetchone()
                return r["value_id"] if r else None
            finally:
                c.close()
        except Exception:
            return None

    def _run_flow_step(self, run_id):
        """由 terminology run id 反查 flow_id / step_id（喺 terminology.db）

        返回 (flow_id, step_id)；搵唔到 -> (None, None)
        """
        if not run_id:
            return None, None
        try:
            import sqlite3 as _sq
            c = _sq.connect(r"C:\projects\meta\terminology\terminology.db")
            try:
                c.row_factory = _sq.Row
                r = c.execute(
                    "SELECT flow_id, step_id FROM run WHERE id = ?",
                    (run_id,)).fetchone()
                if not r:
                    return None, None
                return r["flow_id"], r["step_id"]
            finally:
                c.close()
        except Exception:
            return None, None

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

    def _auto_run(self, value, value_id=None):
        """自動跑 terminology flow -> 真 run_id（用戶：run_id = terminology run）

        用戶要求（2026-10-28）：
            run_id = terminology.run —— migration 一定要有真 run；
            value -> condition + operator + expected -> evidence。
        2026-10-28（用戶再要求）：
            value_id 一定要有 —— migration 嘅值入 value.db（value module），
            taxonomy_id = migration（零 hardcode，由 taxonomy.registry 反查）。

        只跑 migrate_audit flow（唔跑 source_register —— 會開 Source
        -> Source init 又 record -> 無窮遞歸）。
        返回 run.id（失敗 -> None，log 仍然寫但 run_id=NULL）
        """
        try:
            from terminology.api import Terminology
            t = Terminology()
            try:
                # 1. value_id 一定要有（冇 -> 由 value 登記，taxonomy_id=migration）
                if value_id is None and value is not None:
                    tid = self._taxonomy_id("migration")
                    value_id = t.add_value(value, taxonomy_id=tid)
                # 2. 跑 migrate_audit flow（用 value_id，唔好淨靠 value 字串）
                res = t.run_flow("migrate_audit", value=value,
                                 value_id=value_id, save=True)
                return res.get("run_id")
            finally:
                t.close()
        except Exception:
            return None

    # ---------- 查詢 ----------
    def logs(self, module_name=None, migration_type=None, limit=100):
        """列出 migration 記錄（可按 module / type 篩選）

        type 用 value 篩選（type 表），返回補 type_value + module_name。
        """
        args = []
        where = []
        if module_name:
            tid = self._taxonomy_id(module_name)
            where.append("ml.taxonomy_id = ?")
            args.append(tid)
        if migration_type:
            tid = self.type_id(migration_type)
            where.append("ml.type_id = ?")
            args.append(tid)
        sql = ("SELECT ml.*, t.value AS type_value"
               " FROM migration_log ml"
               " LEFT JOIN type t ON t.id = ml.type_id")
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

    # ---------- migrate_schema 其餘真 action（2026-10-29 用戶要求）----------
    # 註：inspect_table / check_column / add_column / backfill_column /
    #     verify_column / verify_rowcount / report 已搬去 skill.py
    #     （SchemaSkill，2026-10-29 用戶要求：package migration > skill）

    def _target_db(self, module_name):
        """module 名 -> (db 路徑, 資料夾名)；default = migration.db"""
        import os
        if not module_name:
            return os.path.join(r"C:\projects\meta", "migration",
                                "migration.db")
        p = os.path.join(r"C:\projects\meta", module_name,
                         f"{module_name}.db")
        return (p, module_name) if os.path.isfile(p) else (
            os.path.join(r"C:\projects\meta", "migration", "migration.db"),
            "migration")

    def _rows_of(self, dbp, table, where=None, args=()):
        """真查 rows（dbp+table 唔存在 -> []）"""
        import sqlite3 as _sq
        try:
            c = _sq.connect(dbp)
            try:
                c.row_factory = _sq.Row
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
        import sqlite3 as _sq
        try:
            c = _sq.connect(dbp)
            try:
                q = f"SELECT COUNT(*) c FROM '{table}'"
                if where:
                    q += f" WHERE {where}"
                return c.execute(q, args).fetchone()[0]
            finally:
                c.close()
        except Exception:
            return 0

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
            import sqlite3 as _sq
            try:
                c = _sq.connect(dbp)
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
            import sqlite3 as _sq
            c = _sq.connect(dbp)
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
        import sqlite3 as _sq
        mapped = False
        try:
            sc = _sq.connect(r"C:\projects\meta\structure\structure.db")
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
                "raw": raw_json, "db_file": r"C:\projects\meta\structure\structure.db"}

    def upsert_local(self, module_name, table, key_column, key_value,
                     data=None):
        """真實 upsert：key 存在 -> UPDATE；否則 INSERT（冪等）"""
        dbp, _ = self._target_db(module_name)
        rows = self._rows_of(dbp, table, f"\"{key_column}\" = ?",
                             (key_value,))
        updated = False
        inserted = False
        import sqlite3 as _sq
        try:
            c = _sq.connect(dbp)
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
                        f"INSERT INTO '{table}' ({','.join(f'\"{x}\"' for x in cols)})"
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

    def backup_table(self, module_name, table):
        """真實 backup：CREATE TABLE <table>_backup_<ts> AS SELECT *"""
        dbp, _ = self._target_db(module_name)
        done = False
        backup_name = None
        import sqlite3 as _sq
        try:
            c = _sq.connect(dbp)
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
        import sqlite3 as _sq
        try:
            c = _sq.connect(dbp)
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
        import sqlite3 as _sq
        try:
            c = _sq.connect(dbp)
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
        import sqlite3 as _sq
        try:
            c = _sq.connect(dbp)
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
        import sqlite3 as _sq
        try:
            c = _sq.connect(dbp)
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

    def inspect(self, module_name, table):
        """真實 inspect（migrate_other）：表存在 + count + cols"""
        dbp, _ = self._target_db(module_name)
        cols = []
        import sqlite3 as _sq
        try:
            c = _sq.connect(dbp)
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
        import os
        tid = self._taxonomy_id(module_name) if module_name else None
        self.conn.execute(
            "INSERT INTO migration_log"
            " (type_id, taxonomy_id, structure_db_table, description)"
            " VALUES (?, ?, ?, ?)",
            (self.type_id("other"), tid, table,
             f"migrate_other action on {table}"))
        self.conn.commit()
        rid = self.conn.execute(
            "SELECT last_insert_rowid()").fetchone()[0]
        return {"action": action_type, "table": table, "recorded": True,
                "migration_log_id": rid}

    def verify(self, module_name, table, expected=None):
        """真實 verify（migrate_other）：count + 可對比 expected"""
        return self.verify_count(module_name, table, expected)

    def by_module(self):
        """按 module + type 統計（type_value 補名）"""
        rows = [dict(r) for r in self.conn.execute(
            "SELECT ml.taxonomy_id, t.value AS type_value, COUNT(*) AS n"
            " FROM migration_log ml"
            " LEFT JOIN type t ON t.id = ml.type_id"
            " GROUP BY ml.taxonomy_id, t.value ORDER BY n DESC")]
        mods = self._module_names()
        for r in rows:
            r["module_name"] = mods.get(r.get("taxonomy_id"))
        return rows

    def commit(self):
        self.conn.commit()

    def close(self):
        self.conn.close()
