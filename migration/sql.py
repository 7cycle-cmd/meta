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

from .skill.schema import (MIGRATION_LOG_DDL, TYPE_DDL,
                           FLOW_REGISTRY_DDL, STEP_REGISTRY_DDL)  # noqa: F401

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
        self.conn.execute(FLOW_REGISTRY_DDL)
        self.conn.execute(STEP_REGISTRY_DDL)
        self._seed_types()
        self._migrate_type_id()
        self._migrate_log_flow_columns()
        self._migrate_drop_flow_tables()
        self._migrate_step_registry_flow_id()
        self._seed_flow_registry()
        self.conn.commit()

    def _seed_flow_registry(self):
        """遷移（幂等）：flow_registry + step_registry seed（2026-10-29 用戶要求）

        flow_registry：6 個 skill 檔案（audit/schema/seed/sync/cutover/other）
            total_line = 檔案真實行數（AST 掃，零 hardcode）
        step_registry：每個檔案嘅全部 function（包括 __init__ / close / helper）
            flow_registry_id -> flow_registry.id（subject = 邊個 skill 檔案）
            function_name    = function 真實名（AST 掃 = action）
            flow_id          -> template.flow.id（object，由 flow_name 真查）
            line_number      = function 真實行號（AST 掃）
        """
        import os as _os
        import importlib.util as _ilu
        # 標準庫 ast（cwd 有 ast package shadow）
        _ast_sp = _ilu.spec_from_file_location(
            "_stdlib_ast",
            _os.path.join(_os.path.dirname(_os.__file__), "ast.py"))
        _ast_m = _ilu.module_from_spec(_ast_sp)
        _ast_sp.loader.exec_module(_ast_m)
        skill_dir = _os.path.join(r"C:\projects\meta", "migration", "skill")
        # 6 個 skill 檔案（用戶指定順序）
        files = ["audit", "schema", "seed", "sync", "cutover", "other"]
        # template.flow.id by flow_name（真查，零 hardcode）
        flow_ids = {}
        try:
            tc = sqlite3.connect(
                r"C:\projects\meta\template\template.db")
            try:
                tc.row_factory = sqlite3.Row
                for r in tc.execute(
                        "SELECT id, flow_name FROM flow"
                        " WHERE is_active = 1"):
                    flow_ids[r["flow_name"]] = r["id"]
            finally:
                tc.close()
        except Exception:
            pass
        for fname in files:
            path = _os.path.join(skill_dir, f"{fname}.py")
            total = 0
            funcs = []
            try:
                with open(path, "r", encoding="utf-8") as f:
                    src = f.read()
                total = src.count("\n") + 1
                tree = _ast_m.parse(src)
                for node in _ast_m.walk(tree):
                    if isinstance(node, (_ast_m.FunctionDef,
                                         _ast_m.AsyncFunctionDef)):
                        # 全部 function 都係 step（包括 __init__ / close / helper）
                        funcs.append((node.name, node.lineno))
            except (OSError, SyntaxError):
                pass
            # flow_registry（filename UNIQUE -> 冪等）
            self.conn.execute(
                "INSERT INTO flow_registry (filename, total_line)"
                " SELECT ?, ? WHERE NOT EXISTS"
                " (SELECT 1 FROM flow_registry WHERE filename = ?)",
                (fname, total, fname))
            fr = self.conn.execute(
                "SELECT id FROM flow_registry WHERE filename = ?",
                (fname,)).fetchone()
            if not fr:
                continue
            # 更新 total_line（每次跑同步真實行數）
            self.conn.execute(
                "UPDATE flow_registry SET total_line = ? WHERE id = ?",
                (total, fr["id"]))
            # step_registry（每個 function 一行；冪等：UNIQUE 組合）
            fid = flow_ids.get(fname)
            for fname2, line in funcs:
                self.conn.execute(
                    "INSERT INTO step_registry"
                    " (flow_registry_id, function_name, flow_id, line_number)"
                    " SELECT ?, ?, ?, ? WHERE NOT EXISTS"
                    " (SELECT 1 FROM step_registry"
                    "  WHERE flow_registry_id = ? AND function_name = ?)",
                    (fr["id"], fname2, fid, line, fr["id"], fname2))
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

    def _migrate_step_registry_flow_id(self):
        """遷移（幂等）：step_registry 加 function_name（2026-10-29 用戶指出）

        用戶：「why didn't registry? they are step, why you remove field:
        function_id」——全部 function 都係 step（包括 __init__ / close /
        helper），唔可以淨係登記 public function；而且冇 function 名欄位
        淨得 line_number 根本唔知邊個 function。
        舊表（冇 function_name 欄）drop 重建；新表由 _seed_flow_registry
        重新 seed（全部 function + function_name）。
        """
        cols = {c[1] for c in self.conn.execute(
            "PRAGMA table_info('step_registry')")}
        if "function_name" not in cols:
            self.conn.execute("DROP TABLE step_registry")
            self.conn.execute(STEP_REGISTRY_DDL)
            self.conn.commit()
            print("[migration] step_registry + function_name（drop 重建）")

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
