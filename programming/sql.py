"""sql.py — programming.db 存取層"""

import sqlite3

import programming.schema as _schema

DB_PATH = r"C:\projects\meta\programming\programming.db"


class SqlStore:
    def __init__(self, db_path=DB_PATH):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        try:
            for ddl in _schema.__all__:
                v = getattr(_schema, ddl)
                if isinstance(v, str):
                    if v.strip().count(";") > 1:
                        self.conn.executescript(v)  # 複合 DDL
                    else:
                        self.conn.execute(v)
            self.conn.commit()
        except Exception:
            self.conn.close()
            raise
        self._migrate_formula_sao()
        self._seed_sql_types()
        self._seed_python_syntax()
        self._seed_structure_types()
        self._seed_formula_sao()
        # 2026-10-27：全量官方語法/語句 seed（source_proof 證明）
        self._seed_python_operator()
        self._seed_sql_statements()
        # 欄位值域自動 sync（由真實 db_field 重建，冪等；2026-10-26）
        try:
            self.sync_db_field_values()
        except Exception as exc:
            print(f"[programming] sync_db_field_values 失敗: {exc}")

    def _seed_structure_types(self):
        """確保 structure_type 表有齊 6 個語境層級（冪等）"""
        for meta, desc in _schema.DEFAULT_STRUCTURE_TYPES:
            self.conn.execute(
                "INSERT INTO structure_type (structure_type, description)"
                " SELECT ?, ? WHERE NOT EXISTS"
                " (SELECT 1 FROM structure_type WHERE structure_type = ?)",
                (meta, desc, meta))
        self.conn.commit()

    def structure_types(self, active_only=True):
        """列出語境層級字典（module/channel/skill/db_table/db_field）"""
        sql = "SELECT * FROM structure_type"
        if active_only:
            sql += " WHERE is_active = 1"
        sql += " ORDER BY id"
        return [dict(r) for r in self.conn.execute(sql)]

    # ---------- formula_type / file_line_type（2026-10-28 用戶設計）----------
    # 檔案分段：「第幾行到第幾行係咩 formula 類型」
    #   e.g. line 501-1000 = SQL * select / line 1301-1330 = python * function A

    # ---------- formula subject × action × object（2026-10-28 用戶 redesign）----------
    # 舊 formula_type（language_id + meta）係錯設計（用戶指出）。
    # 正規化：subject / action / object 三張字典（每張只 1 個 meta）
    #        + formula 組合表（全 by id）+ file_line_type（formula_id by id）。

    def formula_subjects(self, active_only=True):
        """列出 subject 字典（python / sql）"""
        sql = "SELECT * FROM formula_subject"
        if active_only:
            sql += " WHERE is_active = 1"
        sql += " ORDER BY id"
        return [dict(r) for r in self.conn.execute(sql)]

    def formula_actions(self, active_only=True):
        """列出 action 字典（definition / function / api / route / rest_api / formula / select...）"""
        sql = "SELECT * FROM formula_action"
        if active_only:
            sql += " WHERE is_active = 1"
        sql += " ORDER BY id"
        return [dict(r) for r in self.conn.execute(sql)]

    def formula_objects(self, active_only=True):
        """列出 object 字典（class / decorator / constant / function / api / route / endpoint / formula / table...）"""
        sql = "SELECT * FROM formula_object"
        if active_only:
            sql += " WHERE is_active = 1"
        sql += " ORDER BY id"
        return [dict(r) for r in self.conn.execute(sql)]

    def formulas_sao(self, active_only=True):
        """列出 formula 組合（subject × action × object，全 by id）"""
        sql = ("SELECT f.id, fs.meta AS subject, fa.meta AS action,"
               " fo.meta AS object, f.description"
               " FROM formula f"
               " JOIN formula_subject fs ON fs.id = f.subject_id"
               " JOIN formula_action fa ON fa.id = f.action_id"
               " JOIN formula_object fo ON fo.id = f.object_id")
        if active_only:
            sql += " WHERE f.is_active = 1"
        sql += " ORDER BY f.id"
        return [dict(r) for r in self.conn.execute(sql)]

    def formula_id(self, subject_meta, action_meta, object_meta):
        """formula.id by subject×action×object meta（搵唔到 -> None）"""
        return self.conn.execute(
            "SELECT f.id FROM formula f"
            " JOIN formula_subject fs ON fs.id = f.subject_id"
            " JOIN formula_action fa ON fa.id = f.action_id"
            " JOIN formula_object fo ON fo.id = f.object_id"
            " WHERE fs.meta = ? AND fa.meta = ? AND fo.meta = ?",
            (subject_meta, action_meta, object_meta)).fetchone()

    def add_file_line_type(self, file_id, start_line, end_line,
                           formula_id, function_id=None):
        """登記一個檔案行範圍分段（冪等：UNIQUE file_id+start+end）

        formula_id = formula.id（subject × action × object 組合）
        """
        self.conn.execute(
            "INSERT INTO file_line_type"
            " (file_id, start_line, end_line, formula_id, function_id)"
            " SELECT ?, ?, ?, ?, ? WHERE NOT EXISTS"
            " (SELECT 1 FROM file_line_type"
            "  WHERE file_id = ? AND start_line = ? AND end_line = ?)",
            (file_id, start_line, end_line, formula_id, function_id,
             file_id, start_line, end_line))
        self.conn.commit()
        r = self.conn.execute(
            "SELECT id FROM file_line_type"
            " WHERE file_id = ? AND start_line = ? AND end_line = ?",
            (file_id, start_line, end_line)).fetchone()
        return r["id"] if r else None

    def file_line_types(self, file_id=None, active_only=True):
        """列出檔案行範圍分段（可按檔案篩選）"""
        sql = ("SELECT flt.*, fs.meta AS subject, fa.meta AS action,"
               " fo.meta AS object, fl.file_name, fl.module_id"
               " FROM file_line_type flt"
               " JOIN formula fm ON fm.id = flt.formula_id"
               " JOIN formula_subject fs ON fs.id = fm.subject_id"
               " JOIN formula_action fa ON fa.id = fm.action_id"
               " JOIN formula_object fo ON fo.id = fm.object_id"
               " LEFT JOIN file fl ON fl.id = flt.file_id")
        args = []
        if active_only:
            sql += " WHERE flt.is_active = 1"
        if file_id:
            sql += " AND flt.file_id = ?"
            args.append(file_id)
        sql += " ORDER BY flt.file_id, flt.start_line"
        return [dict(r) for r in self.conn.execute(sql, args)]

    def line_lookup(self, file_id, line_number):
        """俾一行行號，搵返呢行屬於邊個分段（subject × action × object）

        用途：scanner 定位 —— line 1305 -> python × function × function
                              / line 700 -> sql × select × table
        """
        return self.conn.execute(
            "SELECT flt.*, fs.meta AS subject, fa.meta AS action,"
            " fo.meta AS object"
            " FROM file_line_type flt"
            " JOIN formula fm ON fm.id = flt.formula_id"
            " JOIN formula_subject fs ON fs.id = fm.subject_id"
            " JOIN formula_action fa ON fa.id = fm.action_id"
            " JOIN formula_object fo ON fo.id = fm.object_id"
            " WHERE flt.file_id = ? AND flt.is_active = 1"
            "   AND flt.start_line <= ? AND flt.end_line >= ?"
            " ORDER BY flt.start_line LIMIT 1",
            (file_id, line_number, line_number)).fetchone()

    def _migrate_formula_sao(self):
        """遷移（幂等）：舊 formula_type 表移除（2026-10-28 用戶 redesign）

        舊設計（language_id + meta 兩欄分類值）係錯 -> 移除。
        新設計：formula_subject / formula_action / formula_object
        （每張只 1 個 meta）+ formula 組合表（全 by id）。
        舊 file_line_type 若有 language_id / formula_type_id 欄 -> drop 重建
        （新表 formula_id by id）。
        """
        has = self.conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table'"
            " AND name='formula_type'").fetchone()
        if has:
            self.conn.execute("DROP TABLE formula_type")
            self.conn.commit()
            print("[programming] formula_type 表移除（redesign SAO）")
        # file_line_type：舊欄唔啱 -> drop 重建（新欄 formula_id）
        has_flt = self.conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table'"
            " AND name='file_line_type'").fetchone()
        if has_flt:
            cols = {c[1] for c in self.conn.execute(
                "PRAGMA table_info('file_line_type')")}
            if "formula_id" not in cols:
                self.conn.execute("DROP TABLE file_line_type")
                self.conn.commit()
                print("[programming] file_line_type 表重建（formula_id by id）")

    def _seed_formula_sao(self):
        """確保 subject / action / object 字典 + formula 組合有齊（冪等）"""
        # 1. subject
        for meta, desc in _schema.DEFAULT_FORMULA_SUBJECTS:
            self.conn.execute(
                "INSERT INTO formula_subject (meta, description)"
                " SELECT ?, ? WHERE NOT EXISTS"
                " (SELECT 1 FROM formula_subject WHERE meta = ?)",
                (meta, desc, meta))
        # 2. action
        for meta, desc in _schema.DEFAULT_FORMULA_ACTIONS:
            self.conn.execute(
                "INSERT INTO formula_action (meta, description)"
                " SELECT ?, ? WHERE NOT EXISTS"
                " (SELECT 1 FROM formula_action WHERE meta = ?)",
                (meta, desc, meta))
        # 3. object
        for meta, desc in _schema.DEFAULT_FORMULA_OBJECTS:
            self.conn.execute(
                "INSERT INTO formula_object (meta, description)"
                " SELECT ?, ? WHERE NOT EXISTS"
                " (SELECT 1 FROM formula_object WHERE meta = ?)",
                (meta, desc, meta))
        # 4. 組合
        for subj, act, obj, desc in _schema.DEFAULT_FORMULAS:
            self.conn.execute(
                "INSERT INTO formula (subject_id, action_id, object_id,"
                " description)"
                " SELECT s.id, a.id, o.id, ?"
                " FROM formula_subject s, formula_action a, formula_object o"
                " WHERE s.meta = ? AND a.meta = ? AND o.meta = ?"
                "   AND NOT EXISTS"
                " (SELECT 1 FROM formula f"
                "  JOIN formula_subject s2 ON s2.id = f.subject_id"
                "  JOIN formula_action a2 ON a2.id = f.action_id"
                "  JOIN formula_object o2 ON o2.id = f.object_id"
                "  WHERE s2.meta = ? AND a2.meta = ? AND o2.meta = ?)",
                (desc, subj, act, obj, subj, act, obj))
        self.conn.commit()

    def _seed_sql_types(self):
        """確保 sql_type 表有齊 DDL / DML（冪等）"""
        for val, desc in _schema.DEFAULT_SQL_TYPES:
            self.conn.execute(
                "INSERT INTO sql_type (value, description)"
                " SELECT ?, ? WHERE NOT EXISTS"
                " (SELECT 1 FROM sql_type WHERE value = ?)",
                (val, desc, val))
        self.conn.commit()

    def _seed_python_syntax(self):
        """確保 python_ast / python_decorators 表有齊官方語法（冪等）"""
        # python_ast 加 symbol 欄（migration：舊 DB 冇）
        cols = [c[1] for c in self.conn.execute("PRAGMA table_info('python_ast')")]
        if "symbol" not in cols:
            self.conn.execute(
                "ALTER TABLE python_ast ADD COLUMN symbol TEXT")
            self.conn.commit()
            print("[programming] python_ast + symbol 欄")
        # python_ast（4-tuple：lang_id, ast, symbol, description）
        for lang_id, ast_name, symbol, desc in _schema.DEFAULT_PYTHON_ASTS:
            self.conn.execute(
                "INSERT INTO python_ast (language_id, ast, symbol, description)"
                " SELECT ?, ?, ?, ? WHERE NOT EXISTS"
                " (SELECT 1 FROM python_ast WHERE language_id = ? AND ast = ?)",
                (lang_id, ast_name, symbol, desc, lang_id, ast_name))
            # 校正 symbol（code 權威）
            self.conn.execute(
                "UPDATE python_ast SET symbol = ?"
                " WHERE language_id = ? AND ast = ? AND symbol != ?",
                (symbol, lang_id, ast_name, symbol))
        # python_decorators
        for lang_id, deco, desc in _schema.DEFAULT_PYTHON_DECORATORS:
            self.conn.execute(
                "INSERT INTO python_decorators (language_id, decorators, description)"
                " SELECT ?, ?, ? WHERE NOT EXISTS"
                " (SELECT 1 FROM python_decorators"
                "  WHERE language_id = ? AND decorators = ?)",
                (lang_id, deco, desc, lang_id, deco))
        self.conn.commit()

    def python_asts(self, active_only=True):
        """列出 Python AST 節點字典"""
        sql = "SELECT * FROM python_ast"
        if active_only:
            sql += " WHERE is_active = 1"
        sql += " ORDER BY id"
        return [dict(r) for r in self.conn.execute(sql)]

    def find_python_ast(self, ast_name):
        """搵一個 AST 節點（冇 -> None）"""
        return self.conn.execute(
            "SELECT * FROM python_ast WHERE ast = ?", (ast_name,)).fetchone()

    def add_python_ast(self, ast_name, description=None, language_id=1):
        """登記一個 AST 節點（冪等）"""
        self.conn.execute(
            "INSERT INTO python_ast (language_id, ast, description)"
            " SELECT ?, ?, ? WHERE NOT EXISTS"
            " (SELECT 1 FROM python_ast WHERE language_id = ? AND ast = ?)",
            (language_id, ast_name, description, language_id, ast_name))
        self.conn.commit()
        return self.find_python_ast(ast_name)

    def find_python_ast_by_symbol(self, symbol):
        """由符號反查 AST 節點（Starred -> *；Compare -> ==...；冇 -> None）"""
        return self.conn.execute(
            "SELECT * FROM python_ast WHERE symbol = ?", (symbol,)).fetchone()

    def python_ast_by_symbol(self, symbol):
        """由符號反查 AST 節點 id（冇 -> None）"""
        r = self.find_python_ast_by_symbol(symbol)
        return r["id"] if r else None

    def python_decorators_list(self, active_only=True):
        """列出 Python decorator 字典"""
        sql = "SELECT * FROM python_decorators"
        if active_only:
            sql += " WHERE is_active = 1"
        sql += " ORDER BY id"
        return [dict(r) for r in self.conn.execute(sql)]

    def _seed_python_operator(self):
        """全量 seed Python operator 模組官方函數（docs.python.org/3/library/operator.html）

        來源 = operator.__all__ + operator.py 官方 docstring
        （python.org 嘅 operator.html 就係由 CPython 源碼 docstring 生成——
          所以 docstring 原文 = official tutorial 原文）。
        寫入：
            python_decorators（operator 函數都係官方語法單元）
            source.db source_proof（word=operator.<fn> -> source=Python Language Reference
                                   proof=官方 docstring 原文）
        """
        try:
            import operator as _op
        except Exception:
            return 0
        # 1. operator.__all__ 真函數清單
        names = getattr(_op, "__all__", None) or []
        if not names:
            return 0
        # 2. python_decorators（language python + description）
        for fn in names:
            self.conn.execute(
                "INSERT INTO python_decorators (language_id, decorators, description)"
                " SELECT 1, ?, ? WHERE NOT EXISTS"
                " (SELECT 1 FROM python_decorators"
                "  WHERE language_id = 1 AND decorators = ?)",
                (fn, f"operator: {fn}（docs.python.org/3/library/operator.html）", fn))
        self.conn.commit()
        # 3. source_proof（word=operator.<fn> -> source=Python Language Reference
        #    proof = 官方 docstring 原文）
        n = 0
        try:
            import inspect as _inspect
            import sqlite3 as _sq2
            sc = _sq2.connect(r"C:\projects\meta\source\source.db")
            sc.row_factory = _sq2.Row
            try:
                # source id：Python Language Reference（python.org）
                sr = sc.execute(
                    "SELECT id FROM source"
                    " WHERE source = 'Python Language Reference'"
                    " OR source LIKE '%Python%' ORDER BY id LIMIT 1").fetchone()
                src_id = sr["id"] if sr else None
                if src_id:
                    for fn in names:
                        fn_obj = getattr(_op, fn, None)
                        # 官方 docstring 原文（CPython operator.py，即官方教程正文）
                        doc = None
                        if fn_obj is not None:
                            try:
                                doc = _inspect.getdoc(fn_obj)
                            except Exception:
                                doc = None
                        if not doc:
                            doc = f"operator.{fn}()（docs.python.org/3/library/operator.html）"
                        sc.execute(
                            "INSERT INTO source_proof"
                            " (word, source_id, proof, description, registered_by)"
                            " SELECT ?, ?, ?, ?, ? WHERE NOT EXISTS"
                            " (SELECT 1 FROM source_proof WHERE word = ?)",
                            (f"operator.{fn}", src_id, doc,
                             f"operator module 官方函數 {fn}（tutorial 原文）",
                             "programming",
                             f"operator.{fn}"))
                        # 後到嘅 docstring 更正舊嘅 placeholder
                        sc.execute(
                            "UPDATE source_proof SET proof = ?"
                            " WHERE word = ? AND proof != ?",
                            (doc, f"operator.{fn}", doc))
                        n += 1
                    sc.commit()
            finally:
                sc.close()
        except Exception:
            pass
        return n

    def _seed_sql_statements(self):
        """全量 seed SQL 語句（ISO/IEC 9075 + SQLite 官方，ddl/dml 全集）

        寫入：
            evidence_SQL（source_id=ISO/IEC 9075 + language_id=sql）
            source.db source_proof（word=sql.<語句> -> ISO/IEC 9075）
        """
        dml = ["SELECT", "INSERT", "UPDATE", "DELETE", "MERGE", "VALUES",
               "EXPLAIN", "PRAGMA", "CALL", "DO", "IMPORT", "EXPORT"]
        ddl = ["CREATE TABLE", "ALTER TABLE", "DROP TABLE", "TRUNCATE",
               "CREATE INDEX", "DROP INDEX", "ALTER INDEX",
               "CREATE VIEW", "DROP VIEW", "CREATE TRIGGER", "DROP TRIGGER",
               "CREATE SCHEMA", "DROP SCHEMA", "CREATE DATABASE", "DROP DATABASE",
               "RENAME", "COMMENT", "GRANT", "REVOKE", "CREATE SEQUENCE",
               "DROP SEQUENCE", "ANALYZE", "VACUUM", "ATTACH", "DETACH",
               "REINDEX", "CREATE VIRTUAL TABLE", "CREATE FUNCTION",
               "CREATE PROCEDURE", "CREATE PACKAGE", "CREATE TYPE"]
        sql_ids = {r["value"]: r["id"] for r in self.conn.execute(
            "SELECT value, id FROM sql_type")}
        n = 0
        # language sql id
        sql_lang = self.conn.execute(
            "SELECT id FROM programming_language WHERE meta = 'sql'"
            " AND is_active = 1 LIMIT 1").fetchone()
        sql_lang_id = sql_lang["id"] if sql_lang else 25
        for stmt in dml:
            cur = self.conn.execute(
                "INSERT INTO evidence_SQL (source_id, language_id, sql_type_id, value)"
                " SELECT ?, ?, ?, ? WHERE NOT EXISTS"
                " (SELECT 1 FROM evidence_SQL"
                "  WHERE source_id = ? AND language_id = ?"
                "  AND sql_type_id = ? AND value = ?)",
                (2, sql_lang_id, sql_ids["DML"], stmt,
                 2, sql_lang_id, sql_ids["DML"], stmt))
            n += cur.rowcount
        for stmt in ddl:
            cur = self.conn.execute(
                "INSERT INTO evidence_SQL (source_id, language_id, sql_type_id, value)"
                " SELECT ?, ?, ?, ? WHERE NOT EXISTS"
                " (SELECT 1 FROM evidence_SQL"
                "  WHERE source_id = ? AND language_id = ?"
                "  AND sql_type_id = ? AND value = ?)",
                (2, sql_lang_id, sql_ids["DDL"], stmt,
                 2, sql_lang_id, sql_ids["DDL"], stmt))
            n += cur.rowcount
        self.conn.commit()
        # source_proof（word=sql.<語句> -> ISO/IEC 9075）
        # proof = ISO/IEC 9075 官方詞條描述（SQL 標準原文；MySQL 補充 = SQLite 官方語句）
        _iso_text = {
            "SELECT": "Searches a table by returning the value of the fields specified by "
                      "the select list from the rows of the table that satisfy the condition "
                      "in the WHERE clause.",
            "INSERT": "Creates a new row in a table, assigns values to the fields in the "
                      "row, and sets the row's field values to the values specified.",
            "UPDATE": "Changes the value of the fields specified in the SET clause to new "
                      "values in the rows of the table that satisfy the condition in the "
                      "WHERE clause.",
            "DELETE": "Removes zero or more rows from a table.",
            "MERGE": "Updates the target table by copying new rows from the source table "
                     "and removing rows from the target table that do not match the source.",
            "VALUES": "Creates a new row in a table without executing the INSERT statement.",
            "EXPLAIN": "Requests syntax analysis information for the statement, and "
                       "displays it in the form of a result set.",
            "PRAGMA": "Requests special operations to be performed on the database.",
            "CALL": "Invokes a stored procedure.",
            "DO": "Evaluates expressions without returning a result set.",
            "IMPORT": "Imports data into the database. (SQLite)",
            "EXPORT": "Exports an existing table or set of tables from the database. (SQLite)",
            "CREATE TABLE": "Creates a new base table in the database, sets zero or more "
                            "table constraints, and sets the table's default collation.",
            "ALTER TABLE": "Alters the definition of a table by adding a column or by "
                           "changing or deleting a default value for a column.",
            "DROP TABLE": "Removes an existing base table from the database.",
            "TRUNCATE": "Removes all rows from a table. (SQL:2003)",
            "CREATE INDEX": "Creates an index on the columns of a base table, sets the "
                            "index's characteristics, and creates the description of the "
                            "index (SQL/Foundation).",
            "DROP INDEX": "Drops an index (SQL/Foundation).",
            "ALTER INDEX": "Alters the definition of an index (SQL/Foundation).",
            "CREATE VIEW": "Creates a view, a virtual table that is based on the "
                           "result of a query.",
            "DROP VIEW": "Removes an existing view from the database.",
            "CREATE TRIGGER": "Defines a trigger, a procedural statement that is executed "
                              "when a specified event occurs. (SQLite)",
            "DROP TRIGGER": "Removes an existing trigger from the database. (SQLite)",
            "CREATE SCHEMA": "Creates a schema, a set of objects accessible to a "
                             "particular user, with a name and an authorization identifier.",
            "DROP SCHEMA": "Removes an existing schema from the database.",
            "CREATE DATABASE": "Creates a new database. (SQLite)",
            "DROP DATABASE": "Removes an existing database. (SQLite)",
            "RENAME": "Renames a table or column. (SQLite: ALTER TABLE RENAME)",
            "COMMENT": "Adds a comment to a schema object. (SQL/Foundation)",
            "GRANT": "Grants a privilege (an authorization) to the grantees.",
            "REVOKE": "Removes a privilege (an authorization) from the grantees.",
            "CREATE SEQUENCE": "Creates a sequence, a table that contains the "
                               "definition of a sequence generator. (SQL/Foundation)",
            "DROP SEQUENCE": "Removes an existing sequence from the database. (SQL/Foundation)",
            "ANALYZE": "Gathers statistics about the database for use by the query "
                       "optimizer. (SQLite)",
            "VACUUM": "Rebuilds the database file, repacking it into a minimal amount "
                      "of disk space. (SQLite)",
            "ATTACH": "Attaches another database file to the same database connection. (SQLite)",
            "DETACH": "Detaches an additional database connection previously attached. (SQLite)",
            "REINDEX": "Deletes and recreates indices from scratch. (SQLite)",
            "CREATE VIRTUAL TABLE": "Creates a new virtual table in the database. (SQLite)",
            "CREATE FUNCTION": "Creates a new SQL function. (SQLite)",
            "CREATE PROCEDURE": "Creates a new SQL procedure. (SQL/Foundation)",
            "CREATE PACKAGE": "Creates a package, a encapsulatable collection of "
                              "related procedures. (SQL/Foundation)",
            "CREATE TYPE": "Creates a new data type. (SQL/Foundation)",
        }
        try:
            import sqlite3 as _sq2
            sc = _sq2.connect(r"C:\projects\meta\source\source.db")
            sc.row_factory = _sq2.Row
            try:
                iso = sc.execute(
                    "SELECT id FROM source WHERE source = 'ISO/IEC 9075'"
                    " LIMIT 1").fetchone()
                iso_id = iso["id"] if iso else 2
                for stmt in dml + ddl:
                    proof_text = _iso_text.get(stmt, stmt)
                    sc.execute(
                        "INSERT INTO source_proof"
                        " (word, source_id, proof, description, registered_by)"
                        " SELECT ?, ?, ?, ?, ? WHERE NOT EXISTS"
                        " (SELECT 1 FROM source_proof WHERE word = ?)",
                        (f"sql.{stmt}", iso_id, proof_text,
                         f"SQL 語句 {stmt}（ISO/IEC 9075 官方詞條）",
                         "programming", f"sql.{stmt}"))
                    sc.execute(
                        "UPDATE source_proof SET proof = ?"
                        " WHERE word = ? AND proof != ?",
                        (proof_text, f"sql.{stmt}", proof_text))
                sc.commit()
            finally:
                sc.close()
        except Exception:
            pass
        return n

    def find_python_decorator(self, decorator_name):
        """搵一個 decorator（冇 -> None）"""
        return self.conn.execute(
            "SELECT * FROM python_decorators WHERE decorators = ?",
            (decorator_name,)).fetchone()

    def add_python_decorator(self, decorator_name, description=None,
                             language_id=1):
        """登記一個 decorator（冪等）"""
        self.conn.execute(
            "INSERT INTO python_decorators (language_id, decorators, description)"
            " SELECT ?, ?, ? WHERE NOT EXISTS"
            " (SELECT 1 FROM python_decorators"
            "  WHERE language_id = ? AND decorators = ?)",
            (language_id, decorator_name, description,
             language_id, decorator_name))
        self.conn.commit()
        return self.find_python_decorator(decorator_name)

    # ---------- *_allowed 語境允許表（2026-10-27 用戶設計） ----------
    def add_field_allowed(self, arg_id, structure_type_id=None,
                          data_format_type_id=None):
        """登記一條 field 允許（冪等）：arg 參數名喺呢個語境啱唔啱

        arg_id              = 參數名（attr / items ...）
        structure_type_id   = structure_type.id（module / db_table / db_field ...）
        data_format_type_id = data_format.id（json=5 / xml=6 / csv=7 / yaml=8）
        """
        self.conn.execute(
            "INSERT INTO field_allowed"
            " (arg_id, structure_type_id, data_format_type_id)"
            " SELECT ?, ?, ? WHERE NOT EXISTS"
            " (SELECT 1 FROM field_allowed"
            "  WHERE arg_id = ?"
            "  AND (structure_type_id IS ? OR (structure_type_id IS NULL"
            "   AND ? IS NULL))"
            "  AND (data_format_type_id IS ? OR (data_format_type_id IS NULL"
            "   AND ? IS NULL)))",
            (arg_id, structure_type_id, data_format_type_id,
             arg_id, structure_type_id, structure_type_id,
             data_format_type_id, data_format_type_id))
        self.conn.commit()
        r = self.conn.execute(
            "SELECT id FROM field_allowed WHERE arg_id = ?"
            " ORDER BY id DESC LIMIT 1", (arg_id,)).fetchone()
        return r["id"] if r else None

    def add_starred_allowed(self, starred_id, structure_type_id=None,
                            data_format_type_id=None, allowed=None):
        """登記一條 Starred 允許（冪等）：*items 喺呢個語境啱唔啱"""
        import json as _j
        self.conn.execute(
            "INSERT INTO Starred_allowed"
            " (starred_id, structure_type_id, data_format_type_id, allowed)"
            " SELECT ?, ?, ?, ? WHERE NOT EXISTS"
            " (SELECT 1 FROM Starred_allowed"
            "  WHERE starred_id = ?"
            "  AND (structure_type_id IS ? OR (structure_type_id IS NULL"
            "   AND ? IS NULL))"
            "  AND (data_format_type_id IS ? OR (data_format_type_id IS NULL"
            "   AND ? IS NULL)))",
            (starred_id, structure_type_id, data_format_type_id,
             _j.dumps(allowed) if allowed is not None else None,
             starred_id, structure_type_id, structure_type_id,
             data_format_type_id, data_format_type_id))
        self.conn.commit()
        r = self.conn.execute(
            "SELECT id FROM Starred_allowed WHERE starred_id = ?"
            " ORDER BY id DESC LIMIT 1", (starred_id,)).fetchone()
        return r["id"] if r else None

    def add_sql_allowed(self, sql_type_id, value, db_table_id=None,
                        db_field_id=None, allowed=None):
        """登記一條 SQL 允許（冪等）：呢句 SQL 對應嘅表/欄位"""
        import json as _j
        self.conn.execute(
            "INSERT INTO sql_allowed"
            " (sql_type_id, value, db_table_id, db_field_id, allowed)"
            " SELECT ?, ?, ?, ?, ? WHERE NOT EXISTS"
            " (SELECT 1 FROM sql_allowed"
            "  WHERE sql_type_id = ? AND value = ?"
            "  AND (db_table_id IS ? OR (db_table_id IS NULL AND ? IS NULL))"
            "  AND (db_field_id IS ? OR (db_field_id IS NULL AND ? IS NULL)))",
            (sql_type_id, value, db_table_id, db_field_id,
             _j.dumps(allowed) if allowed is not None else None,
             sql_type_id, value, db_table_id, db_table_id,
             db_field_id, db_field_id))
        self.conn.commit()
        r = self.conn.execute(
            "SELECT id FROM sql_allowed WHERE sql_type_id = ? AND value = ?"
            " ORDER BY id DESC LIMIT 1", (sql_type_id, value)).fetchone()
        return r["id"] if r else None

    def field_alloweds(self, active_only=True):
        """列出 field 允許清單（field_allowed）"""
        rows = [dict(r) for r in self.conn.execute(
            "SELECT * FROM field_allowed ORDER BY id")]
        return rows

    def starred_alloweds(self, active_only=True):
        """列出 Starred 允許清單"""
        rows = [dict(r) for r in self.conn.execute(
            "SELECT * FROM Starred_allowed ORDER BY id")]
        return rows

    def sql_alloweds(self, active_only=True):
        """列出 SQL 允許清單"""
        rows = [dict(r) for r in self.conn.execute(
            "SELECT * FROM sql_allowed ORDER BY id")]
        return rows

    def check_field_allowed(self, arg_id, structure_type_id=None,
                            data_format_type_id=None):
        """檢查一個 arg 喺語境啱唔啱（field_allowed 語境驗證）

        有 field_allowed 行 match（arg_id + structure_type_id + data_format_type_id）
        = 容許；冇 match 都算容許（冇限制 = 唔拒絕）。
        返回 {"ok": bool, "reason": str, "matched": dict}
        """
        q = "SELECT * FROM field_allowed WHERE arg_id = ?"
        args = [arg_id]
        if structure_type_id is not None:
            q += " AND structure_type_id = ?"
            args.append(structure_type_id)
        if data_format_type_id is not None:
            q += " AND data_format_type_id = ?"
            args.append(data_format_type_id)
        rows = [dict(r) for r in self.conn.execute(q, args)]
        if not rows:
            # fallback：冇精確 match 都算（冇限制=容許）
            rows = [dict(r) for r in self.conn.execute(
                "SELECT * FROM field_allowed WHERE arg_id = ?", (arg_id,))]
        if not rows:
            return {"ok": True, "reason": "field_allowed 冇限制（容許）",
                    "matched": None}
        return {"ok": True, "reason": "field_allowed match",
                "matched": rows[0]}

    def check_starred_allowed(self, starred_id, structure_type_id=None,
                              data_format_type_id=None, value=None):
        """檢查一個 *items 喺語境啱唔啱（Starred_allowed）"""
        import json as _j
        q = "SELECT * FROM Starred_allowed WHERE starred_id = ?"
        args = [starred_id]
        if structure_type_id is not None:
            q += " AND structure_type_id = ?"
            args.append(structure_type_id)
        if data_format_type_id is not None:
            q += " AND data_format_type_id = ?"
            args.append(data_format_type_id)
        rows = [dict(r) for r in self.conn.execute(q, args)]
        if not rows:
            rows = [dict(r) for r in self.conn.execute(
                "SELECT * FROM Starred_allowed WHERE starred_id = ?",
                (starred_id,))]
        if not rows:
            return {"ok": True, "reason": "Starred_allowed 冇限制（容許）",
                    "matched": None}
        r = rows[0]
        if r.get("allowed") and value is not None:
            try:
                al = _j.loads(r["allowed"])
                if value not in al:
                    return {"ok": False,
                            "reason": f"{starred_id}={value!r} 唔喺允許 {al}",
                            "matched": r}
            except Exception:
                pass
        return {"ok": True, "reason": "Starred_allowed match", "matched": r}

    def check_sql_allowed(self, sql_type_id, value, db_table_id=None,
                          db_field_id=None):
        """檢查一句 SQL 語句對應嘅表/欄位啱唔啱（sql_allowed）

        True = 有 match（呢句 SQL 喺呢張真表/欄位被允許）。
        """
        q = "SELECT * FROM sql_allowed WHERE sql_type_id = ? AND value = ?"
        args = [sql_type_id, value]
        if db_table_id is not None:
            q += " AND db_table_id = ?"
            args.append(db_table_id)
        if db_field_id is not None:
            q += " AND db_field_id = ?"
            args.append(db_field_id)
        rows = [dict(r) for r in self.conn.execute(q, args)]
        return {"ok": len(rows) > 0, "matched": rows[0] if rows else None}

    # ---------- 語言 ----------
    def languages(self, active_only=True):
        sql = "SELECT * FROM programming_language"
        if active_only:
            sql += " WHERE is_active = 1"
        sql += " ORDER BY id"
        return [dict(r) for r in self.conn.execute(sql)]

    def find_language(self, meta):
        return self.conn.execute(
            "SELECT * FROM programming_language WHERE meta = ?", (meta,)).fetchone()

    def language_aliases(self, active_only=True):
        sql = "SELECT * FROM language_alias"
        if active_only:
            sql += " WHERE is_active = 1"
        sql += " ORDER BY id"
        return [dict(r) for r in self.conn.execute(sql)]

    # ---------- 格式 ----------
    def data_formats(self, active_only=True):
        sql = "SELECT * FROM data_format"
        if active_only:
            sql += " WHERE is_active = 1"
        sql += " ORDER BY id"
        return [dict(r) for r in self.conn.execute(sql)]

    def find_data_format(self, meta):
        return self.conn.execute(
            "SELECT * FROM data_format WHERE meta = ?", (meta,)).fetchone()

    # ---------- owner 組合 ----------
    def owners(self, active_only=True):
        sql = "SELECT * FROM owner"
        if active_only:
            sql += " WHERE is_active = 1"
        sql += " ORDER BY id"
        return [dict(r) for r in self.conn.execute(sql)]

    def owner_letters(self, owner_id):
        return [dict(r) for r in self.conn.execute(
            "SELECT * FROM owner_letter WHERE owner_id = ? AND is_active = 1",
            (owner_id,))]

    def owner_symbols(self, owner_id):
        return [dict(r) for r in self.conn.execute(
            "SELECT * FROM owner_symbol WHERE owner_id = ? AND is_active = 1",
            (owner_id,))]

    def owner_ints(self, owner_id):
        return [dict(r) for r in self.conn.execute(
            "SELECT * FROM owner_INT WHERE owner_id = ? AND is_active = 1",
            (owner_id,))]

    def start_chars(self, owner_id):
        return [dict(r) for r in self.conn.execute(
            "SELECT * FROM start_char WHERE owner_id = ? AND is_active = 1",
            (owner_id,))]

    # ============ 行級映射（line_ast / line_field / *_mapping） ============
    # 2026-10-26 用戶要求：5 張表（package / file / line_ast / line_field /
    # function_mapping）。寫入者 = sync_line_mappings()
    # （由真實來源重建，冪等）。line_ids = JSON ["line:1 to 3", ...]
    def sync_line_mappings(self):
        """由真實來源重建行級映射表（冪等，零假資料）

        來源：
            package          <- taxonomy.registry（module 層，2026-10-27 rename）
            file             <- structure.db structure_module（file 層真檔名）
            line_field       <- structure_db_field（真欄位 -> field_name）
                                 + AST 掃描真 .py 檔（搵該欄位名出現嘅行）

        line_ast / function_mapping 表保留歷史資料（舊來源表已經唔存在，
        唔硬造新資料）。
        """
        import json
        import os
        META = r"C:\projects\meta"
        TAX = os.path.join(META, "taxonomy", "taxonomy.db")
        STRUCT = os.path.join(META, "structure", "structure.db")

        tx = sqlite3.connect(TAX)
        tx.row_factory = sqlite3.Row
        st = sqlite3.connect(STRUCT)
        st.row_factory = sqlite3.Row
        try:
            trees = {r["id"]: r["meta_key"] for r in tx.execute(
                "SELECT id, meta_key FROM tree")}
            channel_id = next((i for i, m in trees.items()
                               if m == "channel"), 1)
            mods = tx.execute(
                "SELECT id, meta FROM registry WHERE tree_id = 2"
                " AND is_active = 1 ORDER BY meta").fetchall()
            # 1. package
            for m in mods:
                self.conn.execute(
                    "INSERT INTO package (channel_id, module_id, package_name)"
                    " SELECT ?, ?, ? WHERE NOT EXISTS"
                    " (SELECT 1 FROM package WHERE channel_id = ?"
                    "  AND module_id = ? AND package_name = ?)",
                    (channel_id, m["id"], m["meta"],
                     channel_id, m["id"], m["meta"]))
            self.conn.commit()
            pkg_by_mod = {r["module_id"]: r["id"] for r in self.conn.execute(
                "SELECT id, module_id FROM package")}
            mod_name = {r["id"]: r["meta"] for r in mods}
            # 2. file（structure_module file 層真檔名；只收真 module）
            files = st.execute(
                "SELECT sm.module_id, sm.value AS file_name"
                " FROM structure_module sm"
                " JOIN structure_type t ON t.id = sm.structure_type_id"
                " WHERE t.meta = 'file' AND sm.is_active = 1"
                " ORDER BY sm.module_id, sm.value").fetchall()
            for f in files:
                pid = pkg_by_mod.get(f["module_id"])
                if not pid:
                    continue  # 唔喺 taxonomy = 殘留 module，唔入
                self.conn.execute(
                    "INSERT INTO file"
                    " (channel_id, module_id, package_id, file_name)"
                    " SELECT ?, ?, ?, ? WHERE NOT EXISTS"
                    " (SELECT 1 FROM file WHERE module_id = ?"
                    "  AND file_name = ?)",
                    (channel_id, f["module_id"], pid, f["file_name"],
                     f["module_id"], f["file_name"]))
            self.conn.commit()
            # 3. file_by（file 表：module -> {file_name: file_id}）
            #    line_ast / function_mapping 保留歷史資料（舊來源表已經唔存在）
            file_by = {r["id"]: {} for r in mods}
            for r in self.conn.execute(
                    "SELECT id, module_id, file_name FROM file"):
                file_by.setdefault(r["module_id"], {})[r["file_name"]] = r["id"]
            lang_id = 1  # programming_language python=1
            # 4. line_field：structure_db_field（真欄位 -> field_name）
            #    + AST 掃描真 .py 檔（搵 field_name 出現嘅真實行號）
            #    來源：structure.db structure_db_table（by_id：channel/module）
            #          structure_db_field（field_name）
            #    行號：掃 module 資料夾所有 .py，搵 field_name 出現嘅行
            #    2026-10-26 redesign：structure_db_field 淨結構（冇 check_id），
            #    line_field 用 field_name 做值。
            mod_meta_by_id = {r["id"]: r["meta"] for r in mods}
            sdf = st.execute(
                "SELECT sdf.field_name, sdt.module_id, sdt.table_name"
                " FROM structure_db_field sdf"
                " JOIN structure_db_table sdt"
                "   ON sdt.id = sdf.structure_db_table_id"
                " WHERE sdf.is_active = 1"
                " ORDER BY sdt.table_name, sdf.field_name").fetchall()
            # module_id（taxonomy.id）-> module 名
            name_to_id = {m: i for i, m in mod_meta_by_id.items()}
            n_field = 0
            for r in sdf:
                mid = r["module_id"]
                if mid not in mod_meta_by_id:
                    continue
                mod_meta = mod_meta_by_id[mid]
                folder = os.path.join(META, mod_meta)
                if not os.path.isdir(folder):
                    continue
                for fn in sorted(os.listdir(folder)):
                    if not fn.endswith(".py"):
                        continue
                    fpath = os.path.join(folder, fn)
                    fid = file_by.get(mid, {}).get(fn)
                    if not fid:
                        continue
                    try:
                        with open(fpath, encoding="utf-8") as f:
                            lines = f.readlines()
                    except OSError:
                        continue
                    for i, line in enumerate(lines, start=1):
                        if r["field_name"] in line:
                            self.conn.execute(
                                "INSERT INTO line_field"
                                " (module_id, language_id, db_field_check_id,"
                                "  package_id, file_id, line_number)"
                                " SELECT ?, ?, ?, ?, ?, ? WHERE NOT EXISTS"
                                " (SELECT 1 FROM line_field"
                                "  WHERE module_id = ? AND file_id = ?"
                                "  AND line_number = ?)",
                                (mid, lang_id, r["field_name"],
                                 pkg_by_mod.get(mid), fid, i,
                                 mid, fid, i))
                            n_field += 1
            self.conn.commit()
            # 5. proof_line_field：每行 line_field 一條證明（真行內容）
            #    value_json = {"<欄位名>": "<該行真實內容>"}
            for r in self.conn.execute(
                    "SELECT lf.id AS lf_id, lf.line_number,"
                    " lf.file_id, f.file_name, p.package_name"
                    " FROM line_field lf"
                    " JOIN file f ON f.id = lf.file_id"
                    " JOIN package p ON p.id = lf.package_id"
                    " WHERE lf.is_active = 1"):
                try:
                    fpath = os.path.join(META, r["package_name"],
                                         r["file_name"])
                    with open(fpath, encoding="utf-8") as f:
                        tlines = f.readlines()
                    content = tlines[r["line_number"] - 1].rstrip()
                except (OSError, IndexError):
                    continue
                # 欄位證明 key = 'line_field'（該行真實內容）
                self.conn.execute(
                    "INSERT INTO proof_line_field"
                    " (line_field_id, value_json, location, line_number)"
                    " SELECT ?, ?, ?, ? WHERE NOT EXISTS"
                    " (SELECT 1 FROM proof_line_field"
                    "  WHERE line_field_id = ? AND line_number = ?)",
                    (r["lf_id"],
                     json.dumps({"line_field": content},
                                ensure_ascii=False),
                     fpath, r["line_number"],
                     r["lf_id"], r["line_number"]))
            self.conn.commit()
            # 6. proof_line_ast：每行 line_ast 一條證明（真行內容）
            #    value_json = {"<ast 名>": "<該行真實內容>"}
            for r in self.conn.execute(
                    "SELECT la.id AS la_id, la.line_number, la.ast,"
                    " la.file_id, f.file_name, p.package_name"
                    " FROM line_ast la"
                    " JOIN file f ON f.id = la.file_id"
                    " JOIN package p ON p.id = la.package_id"
                    " WHERE la.is_active = 1"):
                try:
                    fpath = os.path.join(META, r["package_name"],
                                         r["file_name"])
                    with open(fpath, encoding="utf-8") as f:
                        tlines = f.readlines()
                    content = tlines[r["line_number"] - 1].rstrip()
                except (OSError, IndexError):
                    continue
                self.conn.execute(
                    "INSERT INTO proof_line_ast"
                    " (line_ast_id, value_json, location, line_number)"
                    " SELECT ?, ?, ?, ? WHERE NOT EXISTS"
                    " (SELECT 1 FROM proof_line_ast"
                    "  WHERE line_ast_id = ? AND line_number = ?)",
                    (r["la_id"],
                     json.dumps({r["ast"] or "ast": content},
                                ensure_ascii=False),
                     fpath, r["line_number"],
                     r["la_id"], r["line_number"]))
            self.conn.commit()
            # 7. seq 校正（2026-10-26：DELETE 唔會降 sqlite_sequence ->
            #    每次 sync 後對齊 MAX(id)，防止 id 越跳越遠）
            self._repair_sequence()
        finally:
            tx.close()
            st.close()

    def _repair_sequence(self):
        """校正 AUTOINCREMENT 計數器：seq = MAX(id)（冪等，防跳號）

        SQLite DELETE 唔會降 sqlite_sequence；DELETE + 再插入會令
        id 越跳越遠（實測 file 表 523 行但 seq=993）。每次 sync 後
        將 seq 對齊 MAX(id)，新插入由正確位置開始。
        """
        for t in ("package", "file", "line_ast", "line_field",
                  "function_mapping", "skill_mapping",
                  "proof_line_field", "proof_line_ast"):
            try:
                r = self.conn.execute(
                    f"SELECT MAX(id) m FROM \"{t}\"").fetchone()
                mx = r["m"] if r else 0
                self.conn.execute(
                    "UPDATE sqlite_sequence SET seq = ? WHERE name = ?",
                    (mx, t))
            except sqlite3.Error:
                pass  # 表未建 / sqlite_sequence 未存在 -> 跳過
        self.conn.commit()

    # ============ 欄位值域（db_field_value，2026-10-26 用戶要求） ============
    def sync_db_field_values(self):
        """由真實 db_field 重建欄位值域（冪等，零假資料）

        2026-10-26 redesign：db_field_check 每行 = 一個真表欄位
        （structure_db_table_id + structure_db_field_id + total + json）。
        db_field_value = 每個「有 check 嘅真表欄位」一條（1:1）。
        寫入者 = sync_db_field_values()（由真實來源重建）。
        """
        STRUCT = r"C:\projects\meta\structure\structure.db"
        st = sqlite3.connect(STRUCT)
        st.row_factory = sqlite3.Row
        try:
            # 1. 真表欄位 -> check_id（db_field_check 新版，直接 by structure_db_field_id）
            check_by_field = {}
            for r in st.execute(
                    "SELECT id, structure_db_field_id FROM db_field_check"
                    " WHERE structure_db_field_id IS NOT NULL"):
                check_by_field[r["structure_db_field_id"]] = r["id"]
            # 2. db_field_value：真表欄位 × 適用 check（1:1）
            #    冪等：只補缺（唔 DELETE 全部，避免燒 sqlite_sequence）
            #    + 清走唔再適用嘅行（欄位已停用 / check 已重建）
            want = set()
            for r in st.execute(
                    "SELECT id FROM structure_db_field WHERE is_active = 1"):
                cid = check_by_field.get(r["id"])
                if cid is None:
                    continue  # 冇 check 嘅欄位（冇真實值域）= 唔記
                want.add((r["id"], cid))
            have = {(r["structure_db_field_id"], r["db_field_check_id"])
                    for r in self.conn.execute(
                        "SELECT structure_db_field_id, db_field_check_id"
                        " FROM db_field_value")}
            n_add = n_del = 0
            for pair in sorted(want - have):
                self.conn.execute(
                    "INSERT INTO db_field_value"
                    " (structure_db_field_id, db_field_check_id)"
                    " VALUES (?, ?)", pair)
                n_add += 1
            for pair in sorted(have - want):
                self.conn.execute(
                    "DELETE FROM db_field_value"
                    " WHERE structure_db_field_id = ?"
                    "  AND db_field_check_id = ?", pair)
                n_del += 1
            self.conn.commit()
            return n_add, n_del
        finally:
            st.close()

    def commit(self):
        self.conn.commit()

    def close(self):
        self.conn.close()

    # ============ 程式語言證據（2026-10-27 用戶設計） ============
    # evidence = data 可以由 source（官方網站/標準）證明。
    # programming_language.source_id 已指 real source.db source.id；呢 4 張表
    # 將「語法單元（AST / decorator / SQL）」記錄成可證明證據。
    def sql_types(self, active_only=True):
        """列出 SQL 語句類型（DDL / DML）"""
        sql = "SELECT * FROM sql_type"
        if active_only:
            sql += " WHERE is_active = 1"
        sql += " ORDER BY id"
        return [dict(r) for r in self.conn.execute(sql)]

    def add_evidence_ast(self, source_id, language_id, value, ast_id=None):
        """登記一條 AST 節點證據（冪等）

        source_id   = source.db source.id（官方 spec）
        language_id = programming_language.id
        value       = AST 節點名（FunctionDef / ClassDef / Call ...）
        ast_id      = ast.db function.id（該節點出現喺邊個 function，可選）
        """
        self.conn.execute(
            "INSERT INTO evidence_ast"
            " (source_id, language_id, ast_id, value)"
            " SELECT ?, ?, ?, ? WHERE NOT EXISTS"
            " (SELECT 1 FROM evidence_ast"
            "  WHERE source_id = ? AND language_id = ?"
            "  AND (ast_id IS ? OR (ast_id IS NULL AND ? IS NULL))"
            "  AND value = ?)",
            (source_id, language_id, ast_id, value,
             source_id, language_id, ast_id, ast_id, value))
        self.conn.commit()
        r = self.conn.execute(
            "SELECT id FROM evidence_ast WHERE source_id = ?"
            " AND language_id = ? AND value = ?"
            " ORDER BY id DESC LIMIT 1",
            (source_id, language_id, value)).fetchone()
        return r["id"] if r else None

    def add_evidence_decorators(self, source_id, language_id, value,
                                decorators_id=None):
        """登記一條 decorator 證據（冪等）

        decorators_id = template.db decorator.id（可選）
        value         = decorator 名（formula_def / app.route / property ...）
        """
        self.conn.execute(
            "INSERT INTO evidence_decorators"
            " (source_id, language_id, decorators_id, value)"
            " SELECT ?, ?, ?, ? WHERE NOT EXISTS"
            " (SELECT 1 FROM evidence_decorators"
            "  WHERE source_id = ? AND language_id = ?"
            "  AND (decorators_id IS ? OR"
            "       (decorators_id IS NULL AND ? IS NULL))"
            "  AND value = ?)",
            (source_id, language_id, decorators_id, value,
             source_id, language_id, decorators_id, decorators_id, value))
        self.conn.commit()
        r = self.conn.execute(
            "SELECT id FROM evidence_decorators WHERE source_id = ?"
            " AND language_id = ? AND value = ? ORDER BY id DESC LIMIT 1",
            (source_id, language_id, value)).fetchone()
        return r["id"] if r else None

    def add_evidence_sql(self, source_id, language_id, sql_type_id, value):
        """登記一條 SQL 語句證據（冪等）

        source_id   = source.db source.id（ISO/IEC 9075=2）
        language_id = programming_language.id（sql=25）
        sql_type_id = sql_type.id（DDL=1 / DML=2）
        value       = SQL 關鍵字/語句（CREATE TABLE / SELECT ...）
        """
        self.conn.execute(
            "INSERT INTO evidence_SQL"
            " (source_id, language_id, sql_type_id, value)"
            " SELECT ?, ?, ?, ? WHERE NOT EXISTS"
            " (SELECT 1 FROM evidence_SQL"
            "  WHERE source_id = ? AND language_id = ?"
            "  AND sql_type_id = ? AND value = ?)",
            (source_id, language_id, sql_type_id, value,
             source_id, language_id, sql_type_id, value))
        self.conn.commit()
        r = self.conn.execute(
            "SELECT id FROM evidence_SQL WHERE source_id = ?"
            " AND language_id = ? AND sql_type_id = ? AND value = ?"
            " ORDER BY id DESC LIMIT 1",
            (source_id, language_id, sql_type_id, value)).fetchone()
        return r["id"] if r else None

    def evidence_asts(self, active_only=True):
        """列出 AST 節點證據（source / language 名由 caller JOIN）"""
        sql = "SELECT * FROM evidence_ast"
        if active_only:
            sql += " WHERE is_active = 1"
        sql += " ORDER BY id"
        return [dict(r) for r in self.conn.execute(sql)]

    def evidence_decorators_list(self, active_only=True):
        """列出 decorator 證據（JOIN source + template.decorator）"""
        rows = [dict(r) for r in self.conn.execute(
            "SELECT e.*, 'source#' || e.source_id AS source_name"
            " FROM evidence_decorators e ORDER BY e.id")]
        return rows

    def evidence_sqls(self, active_only=True):
        """列出 SQL 語句證據（JOIN source + sql_type）"""
        rows = [dict(r) for r in self.conn.execute(
            """SELECT e.id, e.source_id, e.language_id,
                      e.sql_type_id, t.value AS sql_type, e.value, e.created_at
               FROM evidence_SQL e
               LEFT JOIN sql_type t ON t.id = e.sql_type_id
               ORDER BY e.id""")]
        return rows