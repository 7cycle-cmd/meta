"""sql.py — template.db 存取層

2026-10-26（用戶要求）：template 完全獨立 module，唔再 clone question。
自己 schema（template/schema.py 12 張表）+ seed 字典表。

用法：
    from template.sql import SqlStore
    s = SqlStore()
    s.tables()
    s.query("SELECT * FROM seq LIMIT 5")
    s.close()
"""

import sqlite3

from .schema import *  # noqa: F401,E402

DB_PATH = r"C:\projects\meta\template\template.db"

# 字典表 seed（冪等）—— 新 blue module 開檔即有基礎字典
DEFAULT_5W2H = ["what", "where", "when", "who", "why", "how", "how much"]
DEFAULT_CONDITIONS = ["symbol", "english", "INT", "speech", "single word",
                      "spelling", "approved", "proof", "source", "industry",
                      "table", "module_id", "package_id", "file_id",
                      "db_field_check_id", "preflight", "SQL",
                      "table_value_match", "module_table_match",
                      "is empty", "is NULL"]
DEFAULT_OPERATORS = [
    ("==", "float(answer) == float(pass_value)", "等於"),
    (">=", "float(answer) >= float(pass_value)", "大過等於"),
    ("<=", "float(answer) <= float(pass_value)", "細過等於"),
    ("!=", "float(answer) != float(pass_value)", "唔等於"),
    (">", "float(answer) > float(pass_value)", "大過"),
    ("<", "float(answer) < float(pass_value)", "細過"),
]
DEFAULT_SEQ = list(range(1, 301))  # 2026-10-27：1-300（用戶要求加 101-300）


class SqlStore:
    def __init__(self, db_path=DB_PATH):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.ensure_tables()
        self._seed()

    def ensure_tables(self):
        """確保表存在（自己 schema：12 張 + 5 張 Proof 系統表 + decorator + evidence）"""
        self.conn.executescript(TEMPLATE_DDL + PROOF_DDL_ALL
                                + DECORATOR_DDL + EVIDENCE_DDL_ALL)
        self.conn.commit()
        self._migrate_formula_cuter_seq()
        self._migrate_names()
        self._seed_decorators()

    def _migrate_names(self):
        """遷移（幂等）：test -> condition；calculation -> operator（2026-10-27 用戶要求）

        - 舊表 test 有資料 -> 搬去 condition（保 id）-> drop test
        - 舊表 calculation 有資料 -> 搬去 operator（保 id）-> drop calculation
        - question.test_id 欄 -> condition_id（RENAME COLUMN）
        - formula 加 db_file 欄（evidence 用）
        """
        # 1. test -> condition（保 id）
        has_test = self.conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table'"
            " AND name='test'").fetchone()
        has_cond = self.conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table'"
            " AND name='condition'").fetchone()
        if has_test and has_cond:
            n_cond = self.conn.execute(
                "SELECT COUNT(*) c FROM condition").fetchone()["c"]
            if n_cond == 0:
                n_src = self.conn.execute(
                    "SELECT COUNT(*) c FROM test").fetchone()["c"]
                self.conn.execute(
                    "INSERT INTO condition (id, meta, is_active, created_at)"
                    " SELECT id, meta, is_active, created_at FROM test")
                self.conn.commit()
                print(f"[template] test -> condition：搬 {n_src} 行")
            self.conn.execute("DROP TABLE test")
            self.conn.commit()
        # 2. calculation -> operator（保 id）
        has_cal = self.conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table'"
            " AND name='calculation'").fetchone()
        has_op = self.conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table'"
            " AND name='operator'").fetchone()
        if has_cal and has_op:
            n_op = self.conn.execute(
                "SELECT COUNT(*) c FROM operator").fetchone()["c"]
            if n_op == 0:
                n_src = self.conn.execute(
                    "SELECT COUNT(*) c FROM calculation").fetchone()["c"]
                self.conn.execute(
                    "INSERT INTO operator (id, meta, expression, description,"
                    " is_active, created_at)"
                    " SELECT id, meta, expression, description,"
                    "        is_active, created_at FROM calculation")
                self.conn.commit()
                print(f"[template] calculation -> operator：搬 {n_src} 行")
            self.conn.execute("DROP TABLE calculation")
            self.conn.commit()
        # 3. question.test_id -> condition_id（RENAME COLUMN）
        has_q = self.conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table'"
            " AND name='question'").fetchone()
        if has_q:
            qcols = [c[1] for c in self.conn.execute(
                "PRAGMA table_info('question')")]
            if "test_id" in qcols and "condition_id" not in qcols:
                self.conn.execute(
                    "ALTER TABLE question RENAME COLUMN test_id TO condition_id")
                self.conn.commit()
                print("[template] question.test_id -> condition_id")
            elif "test_id" in qcols and "condition_id" in qcols:
                self.conn.execute(
                    "ALTER TABLE question DROP COLUMN test_id")
                self.conn.commit()
                print("[template] question drop 舊 test_id 欄")
        # 4. formula 加 db_file 欄（evidence 執行 DB 用；2026-10-27）
        fcols = [c[1] for c in self.conn.execute(
            "PRAGMA table_info('formula')")]
        if "db_file" not in fcols:
            self.conn.execute(
                "ALTER TABLE formula ADD COLUMN db_file TEXT")
            self.conn.commit()
            print("[template] formula + db_file 欄")

    def _migrate_formula_cuter_seq(self):
        """遷移（幂等）：formula_cuter.position_id -> seq_id（2026-10-27）

        舊表（position_id 欄）-> RENAME COLUMN 做 seq_id（值唔郁）。
        2026-10-27：+ python_ast_id / source_id 欄（symbol 證明；冇 -> NULL）。
        """
        has = self.conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table'"
            " AND name='formula_cuter'").fetchone()
        if not has:
            return
        cols = [c[1] for c in self.conn.execute(
            "PRAGMA table_info('formula_cuter')")]
        if "position_id" not in cols:
            # 冇 position_id -> 檢查要唔要加 python_ast_id / source_id
            if "python_ast_id" not in cols:
                self.conn.execute(
                    "ALTER TABLE formula_cuter ADD COLUMN python_ast_id INTEGER")
                self.conn.commit()
                print("[template] formula_cuter + python_ast_id 欄")
            if "source_id" not in cols:
                self.conn.execute(
                    "ALTER TABLE formula_cuter ADD COLUMN source_id INTEGER")
                self.conn.commit()
                print("[template] formula_cuter + source_id 欄")
            return
        if "seq_id" in cols:
            self.conn.execute(
                "ALTER TABLE formula_cuter DROP COLUMN position_id")
            self.conn.commit()
            return
        self.conn.execute(
            "ALTER TABLE formula_cuter RENAME COLUMN"
            " position_id TO seq_id")
        self.conn.commit()
        print("[template] formula_cuter.position_id -> seq_id")

    def _seed_decorators(self):
        """確保 decorator 表有齊公式裝飾器定義（冪等，唔燒 sqlite_sequence）

        2026-10-27（用戶要求 table-driven）：裝飾器內容全部由表話事，
        ast 掃碼時只回填出處（package_id / file_id / line）。
        """
        n = 0
        for name, full, lang, tmeta, fmeta, op, pv, dbf, cuter in \
                DEFAULT_DECORATORS:
            cur = self.conn.execute(
                "INSERT INTO decorator"
                " (name, formula_full, language_id, table_meta, field_meta,"
                "  operator_meta, preflight_value, db_file, cuter_split)"
                " SELECT ?, ?, ?, ?, ?, ?, ?, ?, ? WHERE NOT EXISTS"
                " (SELECT 1 FROM decorator WHERE name = ?)",
                (name, full, lang, tmeta, fmeta, op, pv, dbf, cuter, name))
            n += cur.rowcount
        self.conn.commit()
        return n

    def decorators(self, active_only=True):
        """列出全部裝飾器定義（decorator 表，table-driven）"""
        sql = "SELECT * FROM decorator"
        if active_only:
            sql += " WHERE is_active = 1"
        sql += " ORDER BY id"
        return [dict(r) for r in self.conn.execute(sql)]

    def _seed(self):
        """字典表 seed（冪等：唔撞先插，唔燒 sqlite_sequence）"""
        # boolean（0/1）
        for val, desc in ((0, "假"), (1, "真")):
            self.conn.execute(
                "INSERT INTO boolean (id, value, description)"
                " SELECT ?, ?, ? WHERE NOT EXISTS"
                " (SELECT 1 FROM boolean WHERE id = ?)",
                (val, val, desc, val))
        # answer / expected（boolean_id 指 boolean、有 description）
        for meta in ("answer",):
            self.conn.execute(
                f"INSERT INTO {meta} (boolean_id, description)"
                " SELECT 1, '真/有' WHERE NOT EXISTS"
                f" (SELECT 1 FROM {meta} WHERE boolean_id = 1)")
            self.conn.execute(
                f"INSERT INTO {meta} (boolean_id, description)"
                " SELECT 0, '假/冇' WHERE NOT EXISTS"
                f" (SELECT 1 FROM {meta} WHERE boolean_id = 0)")
        # status（冇 description 欄，只插 boolean_id）
        for bid in (1, 0):
            self.conn.execute(
                "INSERT INTO status (boolean_id) SELECT ? WHERE NOT EXISTS"
                " (SELECT 1 FROM status WHERE boolean_id = ?)",
                (bid, bid))
        self.conn.execute(
            "INSERT INTO expected (boolean_id, description)"
            " SELECT 1, '期望值 1（真）' WHERE NOT EXISTS"
            " (SELECT 1 FROM expected WHERE boolean_id = 1)")
        self.conn.execute(
            "INSERT INTO expected (boolean_id, description)"
            " SELECT 0, '期望值 0（假）' WHERE NOT EXISTS"
            " (SELECT 1 FROM expected WHERE boolean_id = 0)")
        # 5W2H
        for m in DEFAULT_5W2H:
            self.conn.execute(
                "INSERT INTO \"5W2H\" (meta) SELECT ? WHERE NOT EXISTS"
                ' (SELECT 1 FROM "5W2H" WHERE meta = ?)', (m, m))
        # condition（2026-10-27 rename from test）
        for m in DEFAULT_CONDITIONS:
            self.conn.execute(
                "INSERT INTO condition (meta) SELECT ? WHERE NOT EXISTS"
                " (SELECT 1 FROM condition WHERE meta = ?)", (m, m))
        # operator（2026-10-27 rename from calculation）
        for meta, expr, desc in DEFAULT_OPERATORS:
            self.conn.execute(
                "INSERT INTO operator (meta, expression, description)"
                " SELECT ?, ?, ? WHERE NOT EXISTS"
                " (SELECT 1 FROM operator WHERE meta = ?)",
                (meta, expr, desc, meta))
        # seq 1-300（2026-10-27：用戶要求加 101-300）
        for n in DEFAULT_SEQ:
            self.conn.execute(
                "INSERT INTO seq (seq) SELECT ? WHERE NOT EXISTS"
                " (SELECT 1 FROM seq WHERE seq = ?)", (n, n))
        self.conn.commit()
        # Proof 系統 seed（2026-10-27 用戶設計）
        self._seed_proof_system()

    # ================= Proof 系統（2026-10-27 用戶設計） =================
    def _seed_proof_system(self):
        """seed Proof 表 + 預設 flows（冪等）

        flows（用戶定義）：
            verfity_table   STEP1 what is table    STEP2 where is source
            verfity_module  STEP1 what is module_id  STEP2 where is source
                            STEP3 how to proof（select * from table
                            where module_id ="module_id"）
            SQL             = verfity_table + verfity_module（合併）
            schema          STEP1 what is db_field_check_id
                            STEP2 where is source
                            STEP3 how to proof（select * from table
                            where db_field_check ="db_field_check_id"）
            preflight       test = preflight
                            STEP3 ... and value ="preflight"
            verfity_package STEP1 what is package_id  STEP2 where is source
            verfity_file    STEP1 what is file_id     STEP2 where is source
            Physical        = verfity_package + verfity_file（合併）
            Proof           STEP3 select * from structure_db_field
                            where package_id ="module_id" and
                            file_id ="file_id"
        step = (test_meta, 5w2h_meta, op_meta, exp_bool, seq)
        全部冪等；flow 已存在 -> 唔重建。
        """
        import json as _json

        def _add_flow_quiet(name, steps):
            try:
                return self._add_flow(name, steps)
            except ValueError:
                return None  # 字典 seed 次序問題 -> 唔嘈

        # 2026-10-27：plan flow upgrade（加 is empty + is NULL 2 步）
        # 舊版 plan（2 步）存在 -> 刪 flow + 其 steps/questions，等重建
        _pf = self.conn.execute(
            "SELECT id FROM flow WHERE flow_name = 'plan'").fetchone()
        if _pf:
            _old_steps = self.conn.execute(
                "SELECT COUNT(*) c FROM step WHERE flow_id = ?",
                (_pf["id"],)).fetchone()["c"]
            if _old_steps < 4:
                self.conn.execute(
                    "DELETE FROM step WHERE flow_id = ?", (_pf["id"],))
                self.conn.execute(
                    "DELETE FROM flow WHERE id = ?", (_pf["id"],))
                self.conn.commit()
                print("[template] plan flow 升級重置（準備加 4 步）")

        # 先建 proof 用嘅 flow（全部 steps 字典都喺 seed 內）
        cl = _add_flow_quiet
        cl("position", [
            ("INT", "what", "==", 1, 1),            # 值一定要係數字
            ("single word", "how", "==", 1, 2),     # 單一詞（冇空格）
        ])
        cl("verfity_table", [
            ("table", "what", "==", 1, 1),
            ("source", "where", "==", 1, 2),
        ])
        cl("verfity_module", [
            ("module_id", "what", "==", 1, 1),
            ("source", "where", "==", 1, 2),
            ("SQL", "how", "==", 1, 3),
        ])
        cl("SQL", [
            ("table", "what", "==", 1, 1),     # verfity_table
            ("module_id", "what", "==", 1, 2), # verfity_module
            ("source", "where", "==", 1, 3),
            ("SQL", "how", "==", 1, 4),
        ])
        cl("schema", [
            ("db_field_check_id", "what", "==", 1, 1),
            ("source", "where", "==", 1, 2),
            ("SQL", "how", "==", 1, 3),
        ])
        cl("preflight", [
            ("db_field_check_id", "what", "==", 1, 1),
            ("source", "where", "==", 1, 2),
            ("preflight", "how", "==", 1, 3),
        ])
        cl("db_field_check", [
            ("db_field_check_id", "what", "==", 1, 1),  # 真 db_field_check id
            ("source", "where", "==", 1, 2),
            ("SQL", "how", "==", 1, 3),                  # 執行 formula 證明
        ])
        # plan flow（2026-10-27 用戶設計：condition + value + FLOW + STEP）
        # 每個 step 一個「match 驗證」：
        #   STEP1  table_value_match   table + db_field 嘅 value 要 match
        #   STEP2  module_table_match  module + table 要 match
        #   STEP3  is empty            value 唔可以係空（''）
        #   STEP4  is NULL             value 唔可以係 NULL（資料庫冇值）
        # STEP3/4 期望=0（空/NULL 唔存在先 pass）—— 完整性檢查
        cl("plan", [
            ("table_value_match", "what", "==", 1, 1),
            ("module_table_match", "what", "==", 1, 2),
            ("is empty", "what", "==", 0, 3),
            ("is NULL", "what", "==", 0, 4),
        ])
        # check_value flow（2026-10-27：is empty + is NULL 完整性檢查）
        # 唔要求 match 任何表——淨係檢查 submission 唔空、唔 NULL
        cl("check_value", [
            ("is empty", "what", "==", 0, 1),
            ("is NULL", "what", "==", 0, 2),
        ])
        cl("verfity_package", [
            ("package_id", "what", "==", 1, 1),
            ("source", "where", "==", 1, 2),
        ])
        cl("verfity_file", [
            ("file_id", "what", "==", 1, 1),
            ("source", "where", "==", 1, 2),
        ])
        cl("Physical", [
            ("package_id", "what", "==", 1, 1),  # verfity_package
            ("file_id", "what", "==", 1, 2),      # verfity_file
            ("source", "where", "==", 1, 3),
            ("SQL", "how", "==", 1, 4),
        ])
        cl("Proof", [
            ("package_id", "what", "==", 1, 1),
            ("file_id", "what", "==", 1, 2),
            ("SQL", "how", "==", 1, 3),
        ])
        # formula seed：每條 proof 一條 formula（用戶指定 SQL）
        # full 入面 <...> = 證明 SQL；package_id/file_id 等 = placeholder
        formulas = {
            "verfity_module": [
                "xxx=<select * from table where module_id =\"module_id\">",
                "table", "module_id", "=\"module_id\""],
            "schema": [
                "xxx=<select * from table where db_field_check"
                " =\"db_field_check_id\">",
                "db_field_check", "db_field_check_id",
                "=\"db_field_check_id\""],
            "preflight": [
                "xxx=<select * from table where db_field_check"
                " =\"db_field_check_id\" and value =\"preflight\">",
                "db_field_check", "db_field_check_id",
                "=\"db_field_check_id\" and value =\"preflight\""],
        }
        # formula 要 attach 去邊個 flow（Proof flow 用「Physical」formula）
        # 唔可以 hardcode formula_id：逐條 INSERT 再攞 lastrowid
        flow_fid = {r["flow_name"]: r["id"] for r in self.flows()}

        def _find_field(table_meta, field):
            """由 structure.db 攞真表欄位 id（冇 -> None）"""
            import sqlite3 as _sq
            try:
                _c = _sq.connect(
                    r"C:\projects\meta\structure\structure.db")
                _c.row_factory = _sq.Row
                try:
                    r = _c.execute(
                        "SELECT f.id FROM structure_db_field f"
                        " JOIN structure_db_table t ON t.id ="
                        "  f.structure_db_table_id"
                        " WHERE t.table_name = ? AND f.field_name = ?"
                        " AND f.is_active = 1 LIMIT 1",
                        (table_meta, field)).fetchone()
                    return r["id"] if r else None
                finally:
                    _c.close()
            except Exception:
                return None

        def _table_row_id(table_meta):
            """structure.db structure_db_table.id（冇 -> None）"""
            import sqlite3 as _sq
            try:
                _c = _sq.connect(
                    r"C:\projects\meta\structure\structure.db")
                _c.row_factory = _sq.Row
                try:
                    r = _c.execute(
                        "SELECT id FROM structure_db_table"
                        " WHERE table_name = ? LIMIT 1",
                        (table_meta,)).fetchone()
                    return r["id"] if r else None
                finally:
                    _c.close()
            except Exception:
                return None

        lang_sql_id = 1  # language 表由 language module 管；SQL 固定 id=1
        for flow_name, (full, table_meta, fld, cond_expr) in formulas.items():
            # 已 seed 過 -> 跳過
            exists = self.conn.execute(
                "SELECT 1 FROM formula WHERE full = ?", (full,)).fetchone()
            if exists:
                continue
            cur = self.conn.execute(
                "INSERT INTO formula (full) VALUES (?)", (full,))
            formula_id = cur.lastrowid
            self.conn.commit()
            # proof（SQL 語言）
            self.conn.execute(
                "INSERT INTO proof (language_id, formula_id)"
                " SELECT ?, ? WHERE NOT EXISTS"
                " (SELECT 1 FROM proof WHERE language_id = ?"
                "  AND formula_id = ?)",
                (lang_sql_id, formula_id, lang_sql_id, formula_id))
            # preflight_table：formula 驗證邊張真表
            tid = _table_row_id(table_meta)
            if tid:
                self.conn.execute(
                    "INSERT INTO preflight_table"
                    " (formula_id, structure_db_table_id)"
                    " SELECT ?, ? WHERE NOT EXISTS"
                    " (SELECT 1 FROM preflight_table"
                    "  WHERE formula_id = ?"
                    "  AND structure_db_table_id = ?)",
                    (formula_id, tid, formula_id, tid))
            # preflight_condition：條件（structure_db_field_id + op + preflight_id）
            fid_real = _find_field(table_meta, fld)
            if fid_real:
                op_id = self.conn.execute(
                    "SELECT id FROM operator WHERE meta = '=='"
                ).fetchone()["id"]
                preflight_id = None
                self.conn.execute(
                    "INSERT INTO preflight_condition"
                    " (formula_id, structure_db_field_id, operator_id,"
                    "  preflight_id)"
                    " SELECT ?, ?, ?, ? WHERE NOT EXISTS"
                    " (SELECT 1 FROM preflight_condition"
                    "  WHERE formula_id = ?"
                    "  AND structure_db_field_id = ?)",
                    (formula_id, fid_real, op_id, preflight_id,
                     formula_id, fid_real))
            self.conn.commit()
        # Proof / Physical：structure_db_field 證明（package_id + file_id）
        if flow_fid.get("Proof"):
            fid_real = _find_field("structure_db_field", "package_id")
            fid_file = _find_field("structure_db_field", "file_id")
            if not (fid_real and fid_file):
                # 用真表欄位（structure_module 有 module_id/value）
                fid_real = _find_field("structure_module", "module_id") or \
                    _find_field("structure_db_field", "id")
                fid_file = _find_field("structure_module", "value") or \
                    _find_field("structure_db_field", "field_name")
            full_pf = ("xxx=<select * from structure_db_field where"
                       " package_id =\"module_id\" and"
                       " file_id =\"file_id\">")
            exists = self.conn.execute(
                "SELECT 1 FROM formula WHERE full = ?",
                (full_pf,)).fetchone()
            if not exists and fid_real and fid_file:
                cur = self.conn.execute(
                    "INSERT INTO formula (full) VALUES (?)", (full_pf,))
                formula_id = cur.lastrowid
                self.conn.commit()
                self.conn.execute(
                    "INSERT INTO proof (language_id, formula_id)"
                    " SELECT ?, ? WHERE NOT EXISTS"
                    " (SELECT 1 FROM proof WHERE language_id = ?"
                    "  AND formula_id = ?)",
                    (lang_sql_id, formula_id, lang_sql_id, formula_id))
                for fld_real, preflight_v in ((fid_real, "module_id"),
                                               (fid_file, "file_id")):
                    op_id = self.conn.execute(
                        "SELECT id FROM operator WHERE meta = '=='"
                    ).fetchone()["id"]
                    self.conn.execute(
                        "INSERT INTO preflight_condition"
                        " (formula_id, structure_db_field_id,"
                        "  operator_id, preflight_id)"
                        " SELECT ?, ?, ?, ? WHERE NOT EXISTS"
                        " (SELECT 1 FROM preflight_condition"
                        "  WHERE formula_id = ?"
                        "  AND structure_db_field_id = ?)",
                        (formula_id, fld_real, op_id, preflight_v,
                         formula_id, fld_real))
                self.conn.commit()

    def formula(self, formula_id):
        """攞一條 formula 連 cuter 粒"""
        r = self.conn.execute(
            "SELECT * FROM formula WHERE id = ?", (formula_id,)).fetchone()
        if not r:
            return None
        d = dict(r)
        d["cuter"] = [dict(x) for x in self.conn.execute(
            "SELECT * FROM formula_cuter WHERE formula_id = ?"
            " ORDER BY seq_id", (formula_id,))]
        d["proofs"] = [dict(x) for x in self.conn.execute(
            "SELECT * FROM proof WHERE formula_id = ?", (formula_id,))]
        d["tables"] = [dict(x) for x in self.conn.execute(
            "SELECT * FROM preflight_table WHERE formula_id = ?",
            (formula_id,))]
        d["conditions"] = [dict(x) for x in self.conn.execute(
            "SELECT * FROM preflight_condition WHERE formula_id = ?",
            (formula_id,))]
        return d

    def formulas(self, active_only=True):
        """列出全部 formula"""
        sql = "SELECT * FROM formula"
        if active_only:
            sql += " WHERE is_active = 1"
        sql += " ORDER BY id"
        return [dict(r) for r in self.conn.execute(sql)]

    def _cut_formula(self, formula_id):
        """將 formula.full 切粒入 formula_cuter（冪等）

        切法（用戶指定）：
            SPACE = 空格；" = 獨立一粒；= / < / > 獨立一粒；
            字 = 一粒（select / * / from / structure_db_field ...）
        例：
            xxx=<select * from ...>
            -> [xxx, =, <, select, SPACE, *, SPACE, from, ...]

        2026-10-27：每粒 symbol 對應 programming.python_ast 節點
        （Starred -> "*" / Compare -> "=="...）+ source_id（python.org），
        令 formula_cuter 每粒都有官方證明。
        """
        r = self.conn.execute(
            "SELECT full FROM formula WHERE id = ?", (formula_id,)).fetchone()
        if not r:
            return []
        full = r["full"]
        tokens = []
        buf = ""
        for ch in full:
            if ch in ' "=<>':
                if buf:
                    tokens.append(buf)
                    buf = ""
                if ch == ' ':
                    tokens.append("SPACE")
                else:
                    tokens.append(ch)
            else:
                buf += ch
        if buf:
            tokens.append(buf)
        # 2026-10-27：symbol -> python_ast node（programming.db 反查）
        ast_by_symbol = {}
        src_python = None
        try:
            import sqlite3 as _sq
            pc = _sq.connect(r"C:\projects\meta\programming\programming.db")
            pc.row_factory = _sq.Row
            try:
                for x in pc.execute(
                        "SELECT id, symbol FROM python_ast"
                        " WHERE symbol IS NOT NULL AND is_active = 1"):
                    ast_by_symbol[x["symbol"]] = x["id"]
                # python 語言 source_id（programming_language.source_id）
                pl = pc.execute(
                    "SELECT source_id FROM programming_language"
                    " WHERE meta = 'python' AND is_active = 1 LIMIT 1"
                ).fetchone()
                src_python = pl["source_id"] if pl else None
            finally:
                pc.close()
        except Exception:
            pass
        # 收斂：重切（新 cuter 取代舊）
        self.conn.execute(
            "DELETE FROM formula_cuter WHERE formula_id = ?", (formula_id,))
        for pos, tok in enumerate(tokens, 1):
            p_ast = ast_by_symbol.get(tok)
            self.conn.execute(
                "INSERT INTO formula_cuter"
                " (formula_id, seq_id, value, python_ast_id, source_id)"
                " VALUES (?, ?, ?, ?, ?)",
                (formula_id, pos, tok,
                 p_ast if p_ast else None,
                 src_python if p_ast else None))
        self.conn.commit()
        return tokens

    def register_formula_from_decorator(self, decorator_name,
                                        package_id, file_id, line):
        """ast 掃到 @formula_def 時呼叫：由 decorator 表建立/回填 formula

        2026-10-27（用戶要求 table-driven）：裝飾器嘅公式內容全部由
        decorator 表話事（formula_full / language / table / field /
        operator / preflight_value / db_file / cuter_split）。
        呢度只做：
            1. formula 存在（全字串 match）-> 回填出處（package/file/line）
            2. 唔存在 -> 按表定義建 formula + proof + preflight_* + cuter
        返回 {"formula_id", "created", "updated"}
        """
        d = self.conn.execute(
            "SELECT * FROM decorator WHERE name = ? AND is_active = 1",
            (decorator_name,)).fetchone()
        if not d:
            return {"error": f"decorator '{decorator_name}' 未定義（decorator 表）"}
        d = dict(d)
        full = d["formula_full"]
        # 1. 已存在？全字串 match -> 回填出處
        r = self.conn.execute(
            "SELECT id FROM formula WHERE full = ? AND is_active = 1",
            (full,)).fetchone()
        created = False
        if not r:
            cur = self.conn.execute(
                "INSERT INTO formula (full, package_id, file_id, line,"
                " db_file) VALUES (?, ?, ?, ?, ?)",
                (full, package_id, file_id, line, d.get("db_file")))
            formula_id = cur.lastrowid
            created = True
            # proof（語言）
            self.conn.execute(
                "INSERT INTO proof (language_id, formula_id)"
                " SELECT ?, ? WHERE NOT EXISTS"
                " (SELECT 1 FROM proof WHERE language_id = ?"
                "  AND formula_id = ?)",
                (d.get("language_id") or 1, formula_id,
                 d.get("language_id") or 1, formula_id))
            # preflight_table（真表）
            tid = self._decorator_table_id(d.get("table_meta"))
            if tid:
                self.conn.execute(
                    "INSERT INTO preflight_table"
                    " (formula_id, structure_db_table_id)"
                    " SELECT ?, ? WHERE NOT EXISTS"
                    " (SELECT 1 FROM preflight_table"
                    "  WHERE formula_id = ?"
                    "  AND structure_db_table_id = ?)",
                    (formula_id, tid, formula_id, tid))
            # preflight_condition（欄位 + operator + 值）
            fid_real = self._decorator_field_id(d.get("table_meta"),
                                                d.get("field_meta"))
            if fid_real and d.get("operator_meta"):
                op_id = self.conn.execute(
                    "SELECT id FROM operator WHERE meta = ?",
                    (d["operator_meta"],)).fetchone()
                if op_id:
                    self.conn.execute(
                        "INSERT INTO preflight_condition"
                        " (formula_id, structure_db_field_id, operator_id,"
                        "  preflight_id)"
                        " SELECT ?, ?, ?, ? WHERE NOT EXISTS"
                        " (SELECT 1 FROM preflight_condition"
                        "  WHERE formula_id = ?"
                        "  AND structure_db_field_id = ?)",
                        (formula_id, fid_real, op_id["id"],
                         d.get("preflight_value"), formula_id, fid_real))
            # cuter（表話事：1 切 / 0 唔切）
            if d.get("cuter_split", 1):
                self._cut_formula(formula_id)
            self.conn.commit()
            return {"formula_id": formula_id, "created": True,
                    "updated": False}
        # 2. 已存在 -> 回填出處（ast 真實資料）+ 補齊 proof/preflight/cuter
        formula_id = r["id"]
        self.conn.execute(
            "UPDATE formula SET package_id = ?, file_id = ?, line = ?"
            " WHERE id = ? AND (package_id IS NULL OR file_id IS NULL"
            "  OR line IS NULL)",
            (package_id, file_id, line, formula_id))
        # 補齊 proof（冪等）
        self.conn.execute(
            "INSERT INTO proof (language_id, formula_id)"
            " SELECT ?, ? WHERE NOT EXISTS"
            " (SELECT 1 FROM proof WHERE language_id = ?"
            "  AND formula_id = ?)",
            (d.get("language_id") or 1, formula_id,
             d.get("language_id") or 1, formula_id))
        # 補齊 preflight_table（冪等）
        tid = self._decorator_table_id(d.get("table_meta"))
        if tid:
            self.conn.execute(
                "INSERT INTO preflight_table"
                " (formula_id, structure_db_table_id)"
                " SELECT ?, ? WHERE NOT EXISTS"
                " (SELECT 1 FROM preflight_table"
                "  WHERE formula_id = ? AND structure_db_table_id = ?)",
                (formula_id, tid, formula_id, tid))
        # 補齊 preflight_condition（冪等）
        fid_real = self._decorator_field_id(d.get("table_meta"),
                                            d.get("field_meta"))
        if fid_real and d.get("operator_meta"):
            op_id = self.conn.execute(
                "SELECT id FROM operator WHERE meta = ?",
                (d["operator_meta"],)).fetchone()
            if op_id:
                self.conn.execute(
                    "INSERT INTO preflight_condition"
                    " (formula_id, structure_db_field_id, operator_id,"
                    "  preflight_id)"
                    " SELECT ?, ?, ?, ? WHERE NOT EXISTS"
                    " (SELECT 1 FROM preflight_condition"
                    "  WHERE formula_id = ? AND structure_db_field_id = ?)",
                    (formula_id, fid_real, op_id["id"],
                     d.get("preflight_value"), formula_id, fid_real))
        # cuter：表話事 + 冇切過先切（唔 overwrite 手切嘅）
        if d.get("cuter_split", 1):
            has_cuter = self.conn.execute(
                "SELECT 1 FROM formula_cuter WHERE formula_id = ? LIMIT 1",
                (formula_id,)).fetchone()
            if not has_cuter:
                self._cut_formula(formula_id)
        self.conn.commit()
        return {"formula_id": formula_id, "created": False, "updated": True}

    def _decorator_table_id(self, table_meta):
        """（helper）表名 -> structure_db_table.id（structure.db 權威）

        template.db 自己嘅字典表（seq / condition / operator / flow）
        唔喺 structure.db -> 用真表反查；搵唔到 -> None。
        """
        if not table_meta:
            return None
        import sqlite3 as _sq
        try:
            sc = _sq.connect(r"C:\projects\meta\structure\structure.db")
            sc.row_factory = _sq.Row
            try:
                r = sc.execute(
                    "SELECT id FROM structure_db_table"
                    " WHERE table_name = ? LIMIT 1", (table_meta,)).fetchone()
                return r["id"] if r else None
            finally:
                sc.close()
        except Exception:
            return None

    def _decorator_field_id(self, table_meta, field_meta):
        """（helper）欄位名 -> structure_db_field.id（structure.db 權威）"""
        if not table_meta or not field_meta:
            return None
        tid = self._decorator_table_id(table_meta)
        if not tid:
            return None
        import sqlite3 as _sq
        try:
            sc = _sq.connect(r"C:\projects\meta\structure\structure.db")
            sc.row_factory = _sq.Row
            try:
                r = sc.execute(
                    "SELECT id FROM structure_db_field"
                    " WHERE structure_db_table_id = ? AND field_name = ?"
                    " LIMIT 1", (tid, field_meta)).fetchone()
                return r["id"] if r else None
            finally:
                sc.close()
        except Exception:
            return None

    def proof_formula_for_flow(self, flow_name):
        """搵一條 flow 嘅 proof formula（冇 -> None）

        flow（verfity_module / schema / preflight / Proof ...）
        每個 proof step 用嘅 formula = flow 入面 "SQL"/"preflight" condition
        步驟。搵法 = step 連去 question -> question 連去 step -> flow
        所有有 SQL condition 嘅 step。
        """
        rows = self.conn.execute(
            """SELECT s.id AS step_id, q.id AS question_id
               FROM step s
               JOIN flow f ON f.id = s.flow_id
               JOIN question q ON q.id = s.question_id
               JOIN condition c ON c.id = q.condition_id
               WHERE f.flow_name = ? AND c.meta IN ('SQL', 'preflight')""",
            (flow_name,)).fetchall()
        if rows:
            return dict(rows[0])
        return None

    def execute_formula(self, formula_id, params=None):
        """執行一條 formula 嘅 SQL（冇結果 / 出錯 -> False）

        formula.full 入面 <...> 之間係 SQL。
        有 preflight_condition -> 用條件生成 WHERE（真實欄位）；
        冇條件 -> 攞 <...> 內 SQL，placeholder（"module_id" 等）由
        params 代換，`table` 由 preflight_table 真表名代換。
        返回 {"ok": bool, "rows": int, "error": str}
        """
        import re
        r = self.conn.execute(
            "SELECT * FROM formula WHERE id = ? AND is_active = 1",
            (formula_id,)).fetchone()
        if not r:
            return {"ok": False, "error": f"formula {formula_id} 唔存在"}
        params = params or {}
        full = r["full"]
        m = re.search(r"<(.+)>", full)
        if not m:
            return {"ok": False, "error": "冇 <...> SQL"}
        sql = m.group(1)
        # 真表名（preflight_table）
        tbl_row = self.conn.execute(
            "SELECT * FROM preflight_table WHERE formula_id = ? LIMIT 1",
            (formula_id,)).fetchone()
        conditions = [dict(x) for x in self.conn.execute(
            "SELECT * FROM preflight_condition WHERE formula_id = ?"
            " ORDER BY id", (formula_id,))]
        # 真資料讀取 helper（structure.db / 真表所在 db）
        def _real_table(tid):
            import sqlite3 as _sq
            try:
                _c = _sq.connect(
                    r"C:\projects\meta\structure\structure.db")
                _c.row_factory = _sq.Row
                try:
                    rr = _c.execute(
                        "SELECT table_name, module_id, channel_id"
                        " FROM structure_db_table WHERE id = ?",
                        (tid,)).fetchone()
                    if not rr:
                        return None
                    # module_id -> module 資料夾（taxonomy.registry，2026-10-27 rename）
                    mm = _c.execute(
                        "SELECT meta FROM taxdb.registry WHERE id = ?",
                        (rr["module_id"],)).fetchone()
                    return dict(rr)
                finally:
                    _c.close()
            except Exception:
                return None

        def _field_name(fid):
            import sqlite3 as _sq
            try:
                _c = _sq.connect(
                    r"C:\projects\meta\structure\structure.db")
                _c.row_factory = _sq.Row
                try:
                    rr = _c.execute(
                        "SELECT f.field_name FROM structure_db_field f"
                        " WHERE f.id = ?", (fid,)).fetchone()
                    return rr["field_name"] if rr else None
                finally:
                    _c.close()
            except Exception:
                return None

        if tbl_row and tbl_row["structure_db_table_id"]:
            tinfo = _real_table(tbl_row["structure_db_table_id"])
        else:
            tinfo = None
        # 用 preflight_condition（真實欄位）生成 WHERE
        where_parts = []
        args = []
        cond_fname = {}
        for cond in conditions:
            fname = _field_name(cond["structure_db_field_id"])
            if not fname:
                continue
            cond_fname[fname] = cond
            op = "="
            if cond["operator_id"]:
                orow = self.conn.execute(
                    "SELECT meta FROM operator WHERE id = ?",
                    (cond["operator_id"],)).fetchone()
                if orow and orow["meta"] == "==":
                    op = "="
            val = params.get(cond["preflight_id"])
            if cond["preflight_id"] and val is None:
                # preflight 值（例如 "preflight"）= 固定
                val = cond["preflight_id"]
            if val is None:
                continue
            if isinstance(val, (int, float)) and not isinstance(val, bool):
                where_parts.append(f'"{fname}" {op} ?')
                args.append(val)
            else:
                where_parts.append(f'"{fname}" = ?')
                args.append(str(val))
        # 有條件 -> 用真表執行（FROM 表由 conditions 嘅真欄位反查，唔用 formula 文字）
        if where_parts and conditions:
            # 由 condition 嘅 structure_db_field_id 反查真表（第一個）
            from_tbl = None
            try:
                import sqlite3 as _sq
                _c = _sq.connect(
                    f"file:{r'C:\projects\meta\structure\structure.db'}?mode=ro",
                    uri=True)
                _c.row_factory = _sq.Row
                try:
                    c0 = conditions[0]
                    rr = _c.execute(
                        "SELECT t.table_name, t.module_id, t.channel_id"
                        " FROM structure_db_field f"
                        " JOIN structure_db_table t"
                        "   ON t.id = f.structure_db_table_id"
                        " WHERE f.id = ?", (c0["structure_db_field_id"],)
                    ).fetchone()
                    if rr:
                        from_tbl = dict(rr)
                finally:
                    _c.close()
            except Exception:
                pass
            if from_tbl:
                tinfo = from_tbl
        if where_parts and tinfo:
            if tinfo:
                table = tinfo["table_name"]
                import os
                folder = "structure"  # 由 module_id 反查
                # 實際 db：module 資料夾
                try:
                    import sqlite3 as _sq
                    _c = _sq.connect(r"C:\projects\meta\taxonomy\taxonomy.db")
                    _c.row_factory = _sq.Row
                    try:
                        mr = _c.execute(
                            "SELECT meta FROM registry WHERE id = ?",
                            (tinfo["module_id"],)).fetchone()
                        if mr:
                            folder = mr["meta"]
                    finally:
                        _c.close()
                except Exception:
                    pass
                db_path = os.path.join(r"C:\projects\meta", folder,
                                       f"{folder}.db")
                if not os.path.exists(db_path):
                    db_path = r"C:\projects\meta\structure\structure.db"
                try:
                    import sqlite3 as _sq
                    _c = _sq.connect(f"file:{db_path}?mode=ro", uri=True)
                    try:
                        q = (f"SELECT * FROM \"{table}\" WHERE "
                             + " AND ".join(where_parts))
                        rows = _c.execute(q, args)
                        n = sum(1 for _ in rows)
                        return {"ok": True, "rows": n, "table": table,
                                "sql": q, "args": args}
                    finally:
                        _c.close()
                except Exception as exc:
                    return {"ok": False, "error": str(exc), "sql": sql}
        # 冇條件 / 動態 table -> 攞 <...> 內 SQL，代換 placeholder
        # 原本 pattern：`where module_id ="module_id"`（欄名冇引號、
        # 值 slot 有引號）-> replace `"k"` 只會命中值 slot
        for k, v in params.items():
            if isinstance(v, str):
                v = v.replace("'", "''")
                sql = sql.replace(f'"{k}"', f"'{v}'")
            else:
                sql = sql.replace(f'"{k}"', str(v))
        # `table` -> 真表名
        if " from table" in sql and tbl_row:
            tname = None
            if tbl_row["structure_db_table_id"]:
                ti = _real_table(tbl_row["structure_db_table_id"])
                tname = ti["table_name"] if ti else None
            if tname:
                sql = sql.replace(" from table", f' from "{tname}"')
        # 執行（db_file 決定邊個 DB；冇 = structure.db）
        try:
            import sqlite3 as _sq
            import os as _os
            db_path = r'C:\projects\meta\structure\structure.db'
            db_file = r["db_file"] if "db_file" in r.keys() else None
            if db_file:
                db_path = _os.path.join(r"C:\projects\meta", "template",
                                        db_file)
                if not _os.path.exists(db_path):
                    db_path = _os.path.join(r"C:\projects\meta", db_file)
            _c = _sq.connect(f"file:{db_path}?mode=ro", uri=True)
            try:
                rows = _c.execute(sql, args)
                n = sum(1 for _ in rows)
                return {"ok": True, "rows": n, "sql": sql}
            finally:
                _c.close()
        except Exception as exc:
            return {"ok": False, "error": str(exc), "sql": sql}

    # ============ Evidence 引擎（2026-10-27 用戶要求：formula 生成證據） ============
    def gen_evidence_formulas(self, targets=None):
        """由 SSOT 表自動生成 evidence formulas 並執行（零 replace）

        唔郁任何 SSOT 表（position / db_field_check / seq ...）——
        淨係讀佢哋，生成 formula，執行，寫入 evidence 表。

        targets = 可選表名清單（冇 = 全部自動偵測）：
            要 scan 嘅表 = structure.db structure_db_table 有 row 嘅真表
            + template 字典表（condition / operator / seq / flow）

        每條 formula：
            <select * from <table> where <field> = "<value>">
        執行後，expected = 1（SSOT 有 row），actual = rows count（真 coding
        有冇呢 row）。is_match = expected == actual。

        返回 evidence rows count。
        """
        import json as _json
        created = 0
        # 1. 偵測 targets（冇傳 -> 由 structure.db + template 字典自動）
        if not targets:
            targets = []
            try:
                import sqlite3 as _sq
                _c = _sq.connect(
                    f"file:{r'C:\projects\meta\structure\structure.db'}?mode=ro",
                    uri=True)
                try:
                    for r in _c.execute(
                            "SELECT table_name FROM structure_db_table"
                            " WHERE is_active = 1 ORDER BY table_name"):
                        if r[0] not in targets:
                            targets.append(r[0])
                finally:
                    _c.close()
            except Exception:
                pass
            # template 字典表
            for t in ("condition", "operator", "seq", "flow", "value"):
                if t not in targets:
                    targets.append(t)
        # 2. 每張表：最多 MAX_RECORDS 條 formula（避免爆）
        MAX_RECORDS = 10
        # db_file 對應：template 字典表 -> template.db；其他 -> structure.db
        TPL_TABLES = {"condition", "operator", "seq", "flow", "value",
                      "5W2H", "answer", "expected", "status", "boolean",
                      "question", "step", "run", "formula", "proof",
                      "preflight_table", "preflight_condition",
                      "formula_cuter", "evidence"}
        for tname in targets:
            try:
                rows = self.conn.execute(
                    f'SELECT * FROM "{tname}" LIMIT ?', (MAX_RECORDS,))
                rows = [dict(r) for r in rows]
            except Exception:
                continue
            if not rows:
                continue
            for row in rows:
                # 揀一個有值欄位做 compare value（id 優先，其次第一個非空）
                field = "id"
                if field not in row:
                    for k, v in row.items():
                        if v is not None:
                            field, _ = k, v
                            break
                if field not in row or row[field] is None:
                    continue
                val = row[field]
                # 生成 formula（full）+ db_file（執行 DB）
                # 格式：欄名冇引號、值 slot 有引號（同 verify formula 一致）
                db_file = "template.db" if tname in TPL_TABLES else None
                qname = f'"{tname}"' if not tname.replace("_", "").isalnum() \
                    else tname
                full = (f"xxx=<select * from {qname}"
                        f" where {field} =\"{field}\">")
                # 揾 existing formula（冪等）
                fr = self.conn.execute(
                    "SELECT id FROM formula WHERE full = ?", (full,)
                ).fetchone()
                if fr:
                    fid = fr["id"]
                else:
                    cur = self.conn.execute(
                        "INSERT INTO formula (full, db_file) VALUES (?, ?)",
                        (full, db_file))
                    fid = cur.lastrowid
                    self.conn.commit()
                    # proof：記住呢條 formula 驗邊張表
                    pr = self.conn.execute(
                        "SELECT p.id FROM proof p WHERE p.formula_id = ?",
                        (fid,)).fetchone()
                    if not pr:
                        self.conn.execute(
                            "INSERT INTO proof (language_id, formula_id)"
                            " SELECT 1, ? WHERE NOT EXISTS"
                            " (SELECT 1 FROM proof WHERE language_id = 1"
                            "  AND formula_id = ?)", (fid, fid))
                        self.conn.commit()
                # 執行 formula（攞 actual rows）
                res = self.execute_formula(fid, {field: val})
                actual = res.get("rows", 0)
                ok = bool(res.get("ok") and actual > 0)
                expected = 1 if ok else 0
                # 寫 evidence
                self.conn.execute(
                    "INSERT INTO evidence"
                    " (formula_id, table_name, field_name, value,"
                    "  expected, actual, is_match, evidence)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (fid, tname, field, str(val), expected, actual,
                     1 if ok else 0,
                     _json.dumps({"sql": res.get("sql"),
                                  "error": res.get("error")},
                                 ensure_ascii=False)))
                created += 1
        self.conn.commit()
        return created

    def evidences(self, active_only=True, limit=50):
        """列出 evidence 記錄"""
        sql = "SELECT * FROM evidence WHERE 1=1"
        if active_only:
            sql += " AND is_active = 1"
        sql += " ORDER BY id DESC LIMIT %d" % limit
        return [dict(r) for r in self.conn.execute(sql)]

    def evidence_summary(self):
        """evidence 摘要：total / match / mismatch"""
        return {
            "total": self.conn.execute(
                "SELECT COUNT(*) c FROM evidence WHERE is_active = 1"
            ).fetchone()["c"],
            "match": self.conn.execute(
                "SELECT COUNT(*) c FROM evidence"
                " WHERE is_active = 1 AND is_match = 1"
            ).fetchone()["c"],
            "mismatch": self.conn.execute(
                "SELECT COUNT(*) c FROM evidence"
                " WHERE is_active = 1 AND is_match = 0"
            ).fetchone()["c"],
        }

    def _table_real_check(self, value):
        """value 係咪真表（structure.db structure_db_table 有 row）"""
        try:
            import sqlite3 as _sq
            _c = _sq.connect(
                f"file:{r'C:\projects\meta\structure\structure.db'}?mode=ro",
                uri=True)
            try:
                r = _c.execute(
                    "SELECT 1 FROM structure_db_table WHERE table_name = ?"
                    " AND is_active = 1", (value,)).fetchone()
                return 1 if r else 0
            finally:
                _c.close()
        except Exception:
            return 0

    def _module_id_real_check(self, value):
        """value 係咪真 module id（taxonomy registry tree=module）"""
        try:
            import sqlite3 as _sq
            _c = _sq.connect(r"C:\projects\meta\taxonomy\taxonomy.db")
            _c.row_factory = _sq.Row
            try:
                r = _c.execute(
                    "SELECT 1 FROM registry t JOIN tree tr ON tr.id ="
                    " t.tree_id WHERE tr.meta_key = 'module'"
                    " AND t.id = ? AND t.is_active = 1", (value,)).fetchone()
                return 1 if r else 0
            finally:
                _c.close()
        except Exception:
            return 0

    def _file_id_real_check(self, value):
        """value 係咪真 file id（structure_module file 層）"""
        try:
            import sqlite3 as _sq
            _c = _sq.connect(
                f"file:{r'C:\projects\meta\structure\structure.db'}?mode=ro",
                uri=True)
            try:
                r = _c.execute(
                    "SELECT 1 FROM structure_module sm"
                    " JOIN structure_type st ON st.id = sm.structure_type_id"
                    " WHERE st.meta = 'file' AND sm.id = ?"
                    " AND sm.is_active = 1", (value,)).fetchone()
                return 1 if r else 0
            finally:
                _c.close()
        except Exception:
            return 0

    def _db_field_check_real_check(self, value):
        """value 係咪真 db_field_check id（structure.db）"""
        try:
            import sqlite3 as _sq
            _c = _sq.connect(
                f"file:{r'C:\projects\meta\structure\structure.db'}?mode=ro",
                uri=True)
            try:
                r = _c.execute(
                    "SELECT 1 FROM db_field_check WHERE id = ?",
                    (value,)).fetchone()
                return 1 if r else 0
            finally:
                _c.close()
        except Exception:
            return 0

    def _preflight_in_checks(self, value):
        """value 有冇出現喺任何 db_field_check.json（check value in (x,y)）"""
        try:
            import sqlite3 as _sq
            import json as _json
            _c = _sq.connect(
                f"file:{r'C:\projects\meta\structure\structure.db'}?mode=ro",
                uri=True)
            try:
                for r in _c.execute(
                        "SELECT json FROM db_field_check"
                        " WHERE json IS NOT NULL"):
                    try:
                        vals = _json.loads(r[0])
                    except Exception:
                        continue
                    if str(value) in {str(v) for v in vals}:
                        return 1
                return 0
            finally:
                _c.close()
        except Exception:
            return 0

    # ============ flow 執行引擎（2026-10-27：template 自己 build，唔 import） ============
    def flows(self, active_only=True):
        """列出驗證鏈（flow 表）"""
        sql = "SELECT * FROM flow"
        if active_only:
            sql += " WHERE is_active = 1"
        sql += " ORDER BY id"
        return [dict(r) for r in self.conn.execute(sql)]

    def flow_steps(self, flow_name, active_only=True):
        """列出一個 flow 嘅 steps（JOIN 全部字典）

        每 step = 一個 condition 判斷：
            condition   判斷維度（symbol / english / INT / speech ...）
            operator    點比（== / >= ...）
            expected    期望值（boolean 0/1）
            question    問咩（condition × 5W2H）
        """
        sql = """SELECT s.id, s.flow_id, s.seq_id, sq.seq AS seq,
                        s.question_id,
                        q.condition_id, c.meta AS condition,
                        q."5w2h_id", w.meta AS w5w2h,
                        q.operator_id, o.meta AS operator_meta,
                        o.expression AS operator_expression,
                        q.expected_id, e.boolean_id AS expected_boolean_id
                 FROM step s
                 JOIN flow f ON f.id = s.flow_id
                 LEFT JOIN seq sq ON sq.id = s.seq_id
                 LEFT JOIN question q ON q.id = s.question_id
                 LEFT JOIN condition c ON c.id = q.condition_id
                 LEFT JOIN "5W2H" w ON w.id = q."5w2h_id"
                 LEFT JOIN operator o ON o.id = q.operator_id
                 LEFT JOIN expected e ON e.id = q.expected_id
                 WHERE f.flow_name = ?"""
        args = [flow_name]
        if active_only:
            sql += " AND s.is_active = 1"
        sql += " ORDER BY s.seq_id"
        return [dict(r) for r in self.conn.execute(sql, args)]

    def _add_flow(self, flow_name, steps):
        """定義一條 flow（冪等）：flow + question + step 全部入表

        steps = [(condition_meta, w5w2h_meta, operator_meta, expected_bool,
                  seq), ...]
        step 順序由 seq 決定。
        用同一流 transaction 寫（缺任何字典 -> raise，唔半寫）。
        """
        fr = self.conn.execute(
            "SELECT id FROM flow WHERE flow_name = ?", (flow_name,)).fetchone()
        if fr:
            return fr["id"]
        cur = self.conn.execute(
            "INSERT INTO flow (flow_name) VALUES (?)", (flow_name,))
        fid = cur.lastrowid
        for (cond_meta, w5w2h_meta, op_meta, exp_bool, seq_no) in steps:
            cr = self.conn.execute(
                "SELECT id FROM condition WHERE meta = ?",
                (cond_meta,)).fetchone()
            wr = self.conn.execute(
                'SELECT id FROM "5W2H" WHERE meta = ?', (w5w2h_meta,)).fetchone()
            or_ = self.conn.execute(
                "SELECT id FROM operator WHERE meta = ?",
                (op_meta,)).fetchone()
            er = self.conn.execute(
                "SELECT id FROM expected WHERE boolean_id = ?",
                (exp_bool,)).fetchone()
            s_r = self.conn.execute(
                "SELECT id FROM seq WHERE seq = ?", (seq_no,)).fetchone()
            if not all((cr, wr, or_, er, s_r)):
                raise ValueError(
                    f"字典缺：condition={cond_meta} 5W2H={w5w2h_meta} "
                    f"operator={op_meta} expected={exp_bool} seq={seq_no}")
            qr = self.conn.execute(
                "SELECT id FROM question WHERE condition_id = ?"
                ' AND "5w2h_id" = ? AND expected_id = ?',
                (cr["id"], wr["id"], er["id"])).fetchone()
            if qr:
                qid = qr["id"]
            else:
                qc = self.conn.execute(
                    "INSERT INTO question (condition_id, \"5w2h_id\","
                    " operator_id, expected_id) VALUES (?, ?, ?, ?)",
                    (cr["id"], wr["id"], or_["id"], er["id"]))
                qid = qc.lastrowid
            self.conn.execute(
                "INSERT INTO step (flow_id, question_id, seq_id)"
                " SELECT ?, ?, ? WHERE NOT EXISTS"
                " (SELECT 1 FROM step WHERE flow_id = ? AND seq_id = ?)",
                (fid, qid, s_r["id"], fid, s_r["id"]))
        self.conn.commit()
        return fid

    def _judge(self, expression, pass_value, answer):
        """用 operator expression 判斷（expression = code 片段，DB 定義）

        expression 入面用 'answer' 同 'pass_value' 兩個變數。
        pass_value 可能係 '0'/'1'（str 由 expected.boolean_id 嚟），
        answer 係 int —— 統一 normalize 做數值先比較。
        """

        def _num(x):
            if isinstance(x, str):
                try:
                    return float(x)
                except ValueError:
                    return x
            return float(x) if isinstance(x, (int, bool)) and not isinstance(x, bool) else x

        try:
            av, pv = _num(answer), _num(pass_value)
            safe = {"float": float, "int": int, "str": str,
                    "len": len, "abs": abs, "bool": bool}
            return bool(eval(expression, {"__builtins__": safe},
                             {"answer": av, "pass_value": pv}))
        except Exception:
            return False

    def _auto_answer(self, test, value):
        """由 test 維度自動計答案（1 = pass / 0 = fail）

        判斷全部查表（唔 hardcode）：
            symbol       -> value 有冇 character.symbol 字符（冇就 fail）
            english      -> value 全英文字母
            INT          -> value 全數字
            speech       -> value 係英文單詞（全字母）
            single word  -> 冇 _ 冇空格
            spelling     -> 有拼寫（value 唔空）
            proof        -> 有 source 證明（source.db source_proof）
            source       -> 同上
            approved     -> 有 approved run
            industry     -> 有 industry 證據
            其他         -> value 有嘢 = 1
        """
        v = value or ""
        if test == "symbol":
            try:
                from character import Character
                ch = Character()
                try:
                    chars = ch.symbols()
                    return 1 if any(c in v for c in chars) else 0
                finally:
                    ch.close()
            except Exception:
                return 0
        elif test == "english":
            return 1 if v.isalpha() and v.isascii() else 0
        elif test == "INT":
            return 1 if v.isdigit() else 0
        elif test == "speech":
            return 1 if v.isalpha() else 0
        elif test == "single word":
            return 1 if ("_" not in v and " " not in v and v) else 0
        elif test == "spelling":
            return 1 if v else 0
        elif test in ("proof", "source"):
            try:
                from source import Source
                s2 = Source()
                try:
                    return 1 if s2.source_proof(v)["has"] else 0
                finally:
                    s2.close()
            except Exception:
                return 0
        elif test == "approved":
            r = self.conn.execute(
                "SELECT 1 FROM run r"
                " JOIN value v2 ON v2.id = r.value_id"
                " WHERE v2.value = ? AND r.status_id = 1"
                " AND r.is_active = 1", (v,)).fetchone()
            return 1 if r else 0
        elif test == "industry":
            return 0  # industry 證據要 terminology；template 唔依賴
        # ---- Proof 系統（2026-10-27 用戶設計）----
        elif test == "table":
            # 真表（structure_db_table 有 row）
            return self._table_real_check(v)
        elif test == "module_id":
            return self._module_id_real_check(v)
        elif test == "package_id":
            return self._module_id_real_check(v)  # module = package
        elif test == "file_id":
            return self._file_id_real_check(v)
        elif test == "db_field_check_id":
            return self._db_field_check_real_check(v)
        elif test == "preflight":
            # 有冇出現喺任何 db_field_check.json（check value in (x,y)）
            return self._preflight_in_checks(v)
        elif test == "SQL":
            return 1 if v else 0  # 有 SQL formula 就 pass（執行由 run_flow 做）
        elif test == "is empty":
            # value 係咪空（'' 或 None/冇值）
            return 1 if (value is None or str(value).strip() == "") else 0
        elif test == "is NULL":
            # value 係咪 NULL/None（SQL 層面：資料庫真 NULL）
            return 1 if value is None else 0
        elif test == "table_value_match":
            # table + db_field 嘅 value 要 match：
            # value = "<table>.<db_field>=<value>" 依 preflight_condition 反查
            # 真表真欄，喺真 DB 執行睇有冇 row。
            # 格式唔啱（冇 =）-> pass（由 module_table_match step 處理）
            if "=" not in (value or ""):
                return 1
            return self._match_by_preflight(v, mode="value")
        elif test == "module_table_match":
            # module + table 要 match：
            # value = "<module_id>.<table>" —— module 嘅 db 有呢張真表？
            # 格式唔啱（有 = 係 table_value_match 嘅嘢）-> pass
            if "=" in (value or ""):
                return 1
            return self._match_by_preflight(v, mode="table")
        return 1 if v else 0

    def _match_by_preflight(self, value, mode="value"):
        """用 preflight_condition 反查真表真欄真 DB 執行 match（零 hardcode）

        mode="value"：
            value = "<table>.<db_field>=<value>"
            -> 喺真 DB SELECT * FROM <table> WHERE <db_field> = <value>
            有 row = match（例如 db_field_check 有呢個值）
        mode="table"：
            value = "<module_id>.<table>"
            -> module 嘅 db（structure_module db 層）有冇呢張真表
        """
        import sqlite3 as _sq
        v = (value or "").strip()
        if not v:
            return 0
        try:
            # 1. 拆 value 格式（"." 分隔：前段=目標，後段=值）
            if mode == "value":
                if "=" not in v:
                    return 0
                target_part, _, want = v.partition("=")
                target = target_part.strip().strip('"')
                want = want.strip().strip('"')
                # 2. 查 structure.db：呢個 target（table.db_field 或 table）
                #    喺 structure_db_table / structure_db_field 存在？
                c = _sq.connect(
                    f"file:{r'C:\projects\meta\structure\structure.db'}?mode=ro",
                    uri=True)
                c.row_factory = _sq.Row
                try:
                    if "." in target:
                        tname, fname = target.split(".", 1)
                        r = c.execute(
                            "SELECT f.id, t.table_name, t.module_id"
                            " FROM structure_db_field f"
                            " JOIN structure_db_table t"
                            "   ON t.id = f.structure_db_table_id"
                            " WHERE t.table_name = ? AND f.field_name = ?"
                            " AND f.is_active = 1 AND t.is_active = 1"
                            " LIMIT 1", (tname, fname)).fetchone()
                    else:
                        r = c.execute(
                            "SELECT id, table_name, module_id"
                            " FROM structure_db_table"
                            " WHERE table_name = ? AND is_active = 1"
                            " LIMIT 1", (target,)).fetchone()
                    if not r:
                        return 0
                    tinfo = dict(r)
                finally:
                    c.close()
                # 3. 真 DB：優先 structure.db（字典表喺呢度），
                #    搵唔到先試 module 自己 DB（module_id -> taxonomy.registry folder）
                db_paths = [r"C:\projects\meta\structure\structure.db"]
                folder = "structure"
                try:
                    tc = _sq.connect(
                        r"C:\projects\meta\taxonomy\taxonomy.db")
                    tc.row_factory = _sq.Row
                    try:
                        mr = tc.execute(
                            "SELECT meta FROM registry WHERE id = ?",
                            (tinfo["module_id"],)).fetchone()
                        if mr:
                            folder = mr["meta"]
                            import os as _os
                            mdb = _os.path.join(
                                r"C:\projects\meta", folder, f"{folder}.db")
                            if _os.path.exists(mdb):
                                db_paths.append(mdb)
                    finally:
                        tc.close()
                except Exception:
                    pass
                # 4. 逐個 DB 執行 match（有 row = 1）
                fld = fname if "." in target else "id"
                for db_path in db_paths:
                    try:
                        q = (f'SELECT * FROM "{tinfo["table_name"]}"'
                             f' WHERE "{fld}" = ? LIMIT 1')
                        rc = _sq.connect(f"file:{db_path}?mode=ro", uri=True)
                        try:
                            row = rc.execute(q, (want,)).fetchone()
                            if row:
                                return 1
                        finally:
                            rc.close()
                    except Exception:
                        continue
                return 0
            elif mode == "table":
                # value = "<module_id>.<table>"
                if "." not in v:
                    return 0
                mid_s, _, tname = v.partition(".")
                mid_s = mid_s.strip().strip('"')
                tname = tname.strip().strip('"')
                c = _sq.connect(
                    f"file:{r'C:\projects\meta\structure\structure.db'}?mode=ro",
                    uri=True)
                c.row_factory = _sq.Row
                try:
                    r = c.execute(
                        "SELECT sm.value AS db_file"
                        " FROM structure_module sm"
                        " JOIN structure_type st ON st.id = sm.structure_type_id"
                        " WHERE st.meta = 'db' AND sm.module_id = ?"
                        " AND sm.is_active = 1 LIMIT 1", (mid_s,)).fetchone()
                    if not r:
                        return 0
                    db_file = r["db_file"]
                finally:
                    c.close()
                # folder = taxonomy.registry.meta（2026-10-27 rename）
                folder = "structure"
                try:
                    tc = _sq.connect(
                        r"C:\projects\meta\taxonomy\taxonomy.db")
                    tc.row_factory = _sq.Row
                    try:
                        mr = tc.execute(
                            "SELECT meta FROM registry WHERE id = ?",
                            (mid_s,)).fetchone()
                        if mr:
                            folder = mr["meta"]
                    finally:
                        tc.close()
                except Exception:
                    pass
                db_path = __import__("os").path.join(
                    r"C:\projects\meta", folder, db_file)
                if not __import__("os").path.exists(db_path):
                    return 0
                try:
                    dc = _sq.connect(f"file:{db_path}?mode=ro", uri=True)
                    try:
                        r = dc.execute(
                            "SELECT 1 FROM sqlite_master"
                            " WHERE type='table' AND name = ?",
                            (tname,)).fetchone()
                        return 1 if r else 0
                    finally:
                        dc.close()
                except Exception:
                    return 0
        except Exception:
            return 0
        return 0

    def run_flow(self, flow_name, value, save=True):
        """行一條 flow：逐步判斷（第一個 FAIL 停），寫 run

        value = 提交去檢查嘅值
        全部 PASS -> status_id=1（approved）；有 FAIL -> status_id=2（rejected）
        返回 {"status_id", "step_id", "steps": [{...}], "run_id"}
        """
        steps = self.flow_steps(flow_name)
        if not steps:
            raise ValueError(f"flow '{flow_name}' 冇任何 step")
        # value 入表（value.id）
        vid = None
        if value is not None:
            r = self.conn.execute(
                "SELECT id FROM value WHERE value IS ?", (value,)).fetchone()
            if r:
                vid = r["id"]
            else:
                cur = self.conn.execute(
                    "INSERT INTO value (value) VALUES (?)", (value,))
                vid = cur.lastrowid
        # 逐步判斷
        judged = []
        stopped = None
        all_pass = True
        status_id = 2
        for s in steps:
            raw = self._auto_answer(s["condition"], value)
            # SQL / preflight step：執行真正 formula（row > 0 = pass）
            proof_note = None
            if s["condition"] in ("SQL", "preflight"):
                fid = self.conn.execute(
                    "SELECT id FROM formula WHERE is_active = 1"
                    " ORDER BY id LIMIT 1").fetchone()
                if fid:
                    res = self.execute_formula(
                        fid["id"], {"module_id": value, "value": value})
                    ok = bool(res.get("ok") and res.get("rows", 0) > 0)
                    raw = 1 if ok else 0
                    proof_note = res
                else:
                    ok = False
            else:
                # expected_boolean_id 可能係 0（假）—— 唔可以用 `or 1`（0 or 1 = 1 bug）
                exp = s.get("expected_boolean_id")
                pv = str(exp) if exp is not None else "1"
                ok = self._judge(s.get("operator_expression")
                                 or "answer == pass_value", pv, raw)
            judged.append({
                "step_id": s["id"], "seq": s["seq"],
                "condition": s["condition"], "w5w2h": s["w5w2h"],
                "operator": s["operator_meta"],
                "expected": s["expected_boolean_id"],
                "answer": raw, "is_pass": ok,
                "proof": proof_note,
            })
            if not ok:
                all_pass = False
                stopped = s["id"]
                break
        status_id = 1 if all_pass else 2
        # 寫 run（flow_id / value_id / step_id / status_id）
        run_id = None
        if save:
            fr = self.conn.execute(
                "SELECT id FROM flow WHERE flow_name = ?", (flow_name,)).fetchone()
            fid = fr["id"] if fr else None
            last_step = stopped or steps[-1]["id"]
            cur = self.conn.execute(
                "INSERT INTO run (flow_id, value_id, step_id, status_id)"
                " VALUES (?, ?, ?, ?)",
                (fid, vid, last_step, status_id))
            run_id = cur.lastrowid
            # 自動寫 evidence（2026-10-27：flow 執行 = 證據閉環）
            # 每 step 一條 evidence：expected vs actual
            import json as _json
            for j in judged:
                self.conn.execute(
                    "INSERT INTO evidence"
                    " (formula_id, table_name, field_name, value,"
                    "  expected, actual, is_match, evidence)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (0, "flow", flow_name,
                     str(j.get("condition")),
                     str(j.get("expected", 1)),
                     1 if j.get("is_pass") else 0,
                     1 if j.get("is_pass") else 0,
                     _json.dumps({"run_id": run_id,
                                  "seq": j.get("seq"),
                                  "operator": j.get("operator"),
                                  "answer": j.get("answer"),
                                  "step_id": j.get("step_id"),
                                  "proof": j.get("proof")},
                                 ensure_ascii=False,
                                 default=str)))
            self.conn.commit()
        return {"status_id": status_id, "step_id": stopped,
                "steps": judged, "run_id": run_id,
                "value": value, "value_id": vid}

    def flows_runs(self, limit=20):
        """列出執行記錄（JOIN flow + value + status）"""
        rows = [dict(r) for r in self.conn.execute(
            """SELECT r.id, r.flow_id, f.flow_name,
                      r.value_id, v.value,
                      r.step_id, sq.seq AS step_seq,
                      r.status_id, r.created_at
               FROM run r
               LEFT JOIN flow f ON f.id = r.flow_id
               LEFT JOIN value v ON v.id = r.value_id
               LEFT JOIN step st ON st.id = r.step_id
               LEFT JOIN seq sq ON sq.id = st.seq_id
               ORDER BY r.id DESC LIMIT ?""", (limit,))]
        for d in rows:
            d["status"] = ("approved" if d["status_id"] == 1
                           else "rejected")
        return rows

    def tables(self):
        return [r["name"] for r in self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
            " AND name NOT LIKE 'sqlite_%' ORDER BY name")]

    def table_count(self, t):
        return self.conn.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]

    def query(self, sql, args=()):
        return [dict(r) for r in self.conn.execute(sql, args)]

    def commit(self):
        self.conn.commit()

    def close(self):
        self.conn.close()