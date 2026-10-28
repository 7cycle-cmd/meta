"""sql.py — ast.db 存取層（AST 分析：function 字典 + analyze 表）"""

import importlib.util
import os
import sqlite3

# 標準庫 ast（module 名撞名：cwd 有 ast package，直接 load 標準庫 ast.py）
_ast = importlib.util.spec_from_file_location(
    "_stdlib_ast", os.path.join(os.path.dirname(os.__file__), "ast.py"))
_ast = importlib.util.module_from_spec(_ast)
_ast.__loader__.exec_module(_ast)

from .schema import *  # noqa: F401,E402

DB_PATH = r"C:\projects\meta\ast\ast.db"
META_DIR = r"C:\projects\meta"
STRUCT_DB = r"C:\projects\meta\structure\structure.db"
PROGRAMMING_DB = r"C:\projects\meta\programming\programming.db"
# 權威武 = taxonomy\taxonomy.db（guard resolve 後；根目錄 taxonomy.db 係舊）
TAXONOMY_DB = r"C:\projects\meta\taxonomy\taxonomy.db"

# python 語言 id（programming.db programming_language.id）
PYTHON_LANG_ID = 1


class SqlStore:
    def __init__(self, db_path=DB_PATH):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        # 建表（全部 IF NOT EXISTS，冪等）
        self.conn.executescript(";\n".join([
            FUNCTION_DDL, FUNCTION_CLASS_DDL,
            ANALYZE_ROOT_DDL, ANALYZE_MODULE_DDL,
            ANALYZE_SKILL_DDL,
            DECORATOR_DDL,
        ]))
        self.conn.commit()
        self._seed_decorators()

    def close(self):
        try:
            self.conn.close()
        except Exception:
            pass

    # ---------- function 字典 ----------
    def add_function(self, function, class_id=None,
                     programming_language_id=PYTHON_LANG_ID, commit=True):
        """登記一個函數（冪等）"""
        self.conn.execute(
            "INSERT INTO function (function, class_id, programming_language_id)"
            " SELECT ?, ?, ? WHERE NOT EXISTS"
            " (SELECT 1 FROM function WHERE function = ?)",
            (function, class_id, programming_language_id, function))
        self.conn.execute(
            "UPDATE function SET class_id = COALESCE(?, class_id),"
            " programming_language_id = ? WHERE function = ?",
            (class_id, programming_language_id, function))
        if commit:
            self.conn.commit()
        r = self.conn.execute(
            "SELECT id FROM function WHERE function = ?", (function,)).fetchone()
        return r["id"] if r else None

    def function_id(self, function):
        r = self.conn.execute(
            "SELECT id FROM function WHERE function = ?", (function,)).fetchone()
        return r["id"] if r else None

    def functions(self, active_only=True):
        sql = ("SELECT f.*, fc.meta AS class_name"
               " FROM function f"
               " LEFT JOIN function_class fc ON fc.id = f.class_id"
               " WHERE 1=1")
        if active_only:
            sql += " AND f.is_active = 1"
        sql += " ORDER BY f.function"
        return [dict(r) for r in self.conn.execute(sql)]

    # ---------- function_class 字典 ----------
    def add_function_class(self, meta, description=None, commit=True):
        """登記一個函數類別（冪等）"""
        self.conn.execute(
            "INSERT INTO function_class (meta, description)"
            " SELECT ?, ? WHERE NOT EXISTS"
            " (SELECT 1 FROM function_class WHERE meta = ?)",
            (meta, description, meta))
        self.conn.execute(
            "UPDATE function_class SET description = COALESCE(?, description)"
            " WHERE meta = ?", (description, meta))
        if commit:
            self.conn.commit()
        r = self.conn.execute(
            "SELECT id FROM function_class WHERE meta = ?", (meta,)).fetchone()
        return r["id"] if r else None

    def function_class_id(self, meta):
        r = self.conn.execute(
            "SELECT id FROM function_class WHERE meta = ?", (meta,)).fetchone()
        return r["id"] if r else None

    def function_classes(self, active_only=True):
        sql = "SELECT * FROM function_class WHERE 1=1"
        if active_only:
            sql += " AND is_active = 1"
        sql += " ORDER BY meta"
        return [dict(r) for r in self.conn.execute(sql)]

    # ---------- decorator 字典（2026-10-28 用戶：由 programming 搬嚟 ast） ----------
    def _seed_decorators(self):
        """確保 decorator 表有齊官方/實務 decorator（冪等）"""
        for meta, desc in DEFAULT_DECORATORS:
            self.conn.execute(
                "INSERT INTO decorator (meta, description)"
                " SELECT ?, ? WHERE NOT EXISTS"
                " (SELECT 1 FROM decorator WHERE meta = ?)",
                (meta, desc, meta))
        self.conn.commit()

    def add_decorator(self, meta, description=None, commit=True):
        """登記一個 decorator（冪等）"""
        self.conn.execute(
            "INSERT INTO decorator (meta, description)"
            " SELECT ?, ? WHERE NOT EXISTS"
            " (SELECT 1 FROM decorator WHERE meta = ?)",
            (meta, description, meta))
        self.conn.execute(
            "UPDATE decorator SET description = COALESCE(?, description)"
            " WHERE meta = ?", (description, meta))
        if commit:
            self.conn.commit()
        r = self.conn.execute(
            "SELECT id FROM decorator WHERE meta = ?", (meta,)).fetchone()
        return r["id"] if r else None

    def decorator_id(self, meta):
        r = self.conn.execute(
            "SELECT id FROM decorator WHERE meta = ?", (meta,)).fetchone()
        return r["id"] if r else None

    def decorators(self, active_only=True):
        sql = "SELECT * FROM decorator WHERE 1=1"
        if active_only:
            sql += " AND is_active = 1"
        sql += " ORDER BY meta"
        return [dict(r) for r in self.conn.execute(sql)]

    # ---------- analyze 表 ----------
    def add_analyze(self, table, parent_id, function_id, db_field_check_id=None,
                    commit=True):
        """寫入一條 analyze 行（冪等）

        table = analyze_root / analyze_module / analyze_skill
        parent_id = 對應層表 id（structure_root.id / structure_module.id / ...）
        """
        parent_col = {
            "analyze_root": "structure_root_id",
            "analyze_module": "structure_module_id",
            "analyze_skill": "structure_skill_id",
        }.get(table)
        if not parent_col:
            raise ValueError("未知 analyze 表: %s" % table)
        self.conn.execute(
            "INSERT INTO %s (%s, function_id, db_field_check_id)"
            " SELECT ?, ?, ? WHERE NOT EXISTS"
            " (SELECT 1 FROM %s WHERE %s = ? AND function_id = ?)"
            % (table, parent_col, table, parent_col),
            (parent_id, function_id, db_field_check_id,
             parent_id, function_id))
        if commit:
            self.conn.commit()

    def analyze(self, table, active_only=True):
        """列出一個 analyze 表（JOIN function 名）"""
        parent_col = {
            "analyze_root": "structure_root_id",
            "analyze_module": "structure_module_id",
            "analyze_skill": "structure_skill_id",
        }.get(table)
        if not parent_col:
            raise ValueError("未知 analyze 表: %s" % table)
        sql = ("SELECT a.*, f.function AS function_name"
               " FROM %s a JOIN function f ON f.id = a.function_id"
               " WHERE 1=1" % table)
        if active_only:
            sql += " AND a.is_active = 1"
        sql += " ORDER BY a.id"
        return [dict(r) for r in self.conn.execute(sql)]

    # ---------- AST 掃描 ----------
    def scan_module(self, module_name):
        """AST 掃描一個 module 資料夾，抽出 function 寫入 analyze 表

        1. 掃 <META>/<module_name>/*.py 檔
        2. AST 解析每個檔：module 級 function + class 級 method
        3. function 入 function 字典（class 入 function_class 字典）
        4. 對應層 analyze 表寫入：
           - analyze_module：structure_module.id（file 層，type=2）
           - analyze_skill：structure_skill.id（skill 層）
           - analyze_root：structure_root.id（root 層）

        返回 {"module": name, "functions": n, "files": n_files}
        """
        folder = os.path.join(META_DIR, module_name)
        if not os.path.isdir(folder):
            return {"module": module_name, "functions": 0, "files": 0,
                    "error": "資料夾唔存在"}
        # 1. 掃 .py 檔
        py_files = sorted(f for f in os.listdir(folder)
                          if f.endswith(".py") and not f.startswith("_"))
        # 2. 攞 structure 層 id（by module 名 -> taxonomy.package.id）
        struct_ids = self._structure_ids(module_name)
        if not struct_ids:
            return {"module": module_name, "functions": 0, "files": len(py_files),
                    "error": "structure 層搵唔到 module"}
        n_func = 0
        for fn in py_files:
            path = os.path.join(folder, fn)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    tree = _ast.parse(f.read(), filename=path)
            except (SyntaxError, UnicodeDecodeError, OSError):
                continue
            # 3. 抽出 function（module 級 + class 級）
            for node in _ast.walk(tree):
                if isinstance(node, (_ast.FunctionDef, _ast.AsyncFunctionDef)):
                    fname = node.name
                    if fname.startswith("_"):
                        continue
                    # class 級 method -> class_id
                    class_id = None
                    for parent in _ast.walk(tree):
                        if isinstance(parent, _ast.ClassDef):
                            for child in parent.body:
                                if child is node:
                                    class_id = self.add_function_class(
                                        parent.name, commit=False)
                                    break
                    fid = self.add_function(fname, class_id, commit=False)
                    # 4. 寫入 analyze 表
                    self._write_analyze(struct_ids, fid, fn, fname)
                    n_func += 1
        self.conn.commit()
        return {"module": module_name, "functions": n_func,
                "files": len(py_files)}

    def scan_all(self):
        """AST 掃描全部 module（有 __init__.py 嘅資料夾）"""
        results = []
        for entry in sorted(os.listdir(META_DIR)):
            folder = os.path.join(META_DIR, entry)
            if not os.path.isdir(folder):
                continue
            if entry.startswith("_"):
                continue
            if not os.path.isfile(os.path.join(folder, "__init__.py")):
                continue
            results.append(self.scan_module(entry))
        return results

    # ---------- formula decorator 掃描（2026-10-27：table-driven） ----------
    def scan_formula_decorators(self, module_name, commit=True):
        """掃一個 module 嘅 .py，抽出 @formula_def 並回填 formula 出處

        流程（內容全部由 template.decorator 表話事）：
            1. 掃 <META>/<module_name>/*.py 嘅 AST
            2. 搵到 @formula_def("<name>") -> 攞 package_id + file_id + line
            3. 呼叫 template.SqlStore.register_formula_from_decorator()
               （表定義 formula / proof / preflight / cuter；回填出處）

        返回 {"module": name, "formulas": n, "files": n_files,
              "skipped": [...], "errors": [...]}
        """
        folder = os.path.join(META_DIR, module_name)
        if not os.path.isdir(folder):
            return {"module": module_name, "formulas": 0, "files": 0,
                    "error": "資料夾唔存在"}
        from .function import scan_formula_decorators as _scan_decos
        py_files = sorted(f for f in os.listdir(folder)
                          if f.endswith(".py") and not f.startswith("_"))
        # module 身份（taxonomy.taxonomy.id）+ file 層 id（structure.db）
        package_id = self._package_id(module_name)
        file_ids = self._file_ids(module_name)  # {file_name: structure_module.id}
        # template store（decorator 表權威）
        try:
            from template.sql import SqlStore as TemplateStore
            ts = TemplateStore()
            try:
                n_formula = 0
                skipped = []
                errors = []
                for fn in py_files:
                    path = os.path.join(folder, fn)
                    try:
                        decos = _scan_decos(path)
                    except (SyntaxError, UnicodeDecodeError, OSError) as e:
                        skipped.append(f"{fn}: {e}")
                        continue
                    for d in decos:
                        file_id = file_ids.get(fn)
                        if file_id is None:
                            skipped.append(
                                f"{fn}:{d['line']} {d['decorator']}"
                                "（file 層冇登記）")
                            continue
                        res = ts.register_formula_from_decorator(
                            d["decorator"], package_id, file_id, d["line"])
                        if res.get("error"):
                            errors.append(
                                f"{fn}:{d['line']} {d['decorator']}"
                                f" -> {res['error']}")
                        else:
                            n_formula += 1
                if commit:
                    self.conn.commit()
                return {"module": module_name, "formulas": n_formula,
                        "files": len(py_files), "skipped": skipped,
                        "errors": errors}
            finally:
                ts.close()
        except Exception as e:
            return {"module": module_name, "formulas": 0,
                    "files": len(py_files), "errors": [str(e)]}

    def _package_id(self, module_name):
        """module 名 -> taxonomy.registry.id（tree = module；2026-10-27 rename）"""
        try:
            tc = sqlite3.connect(TAXONOMY_DB)
            tc.row_factory = sqlite3.Row
            try:
                r = tc.execute(
                    "SELECT t.id FROM registry t"
                    " JOIN tree tr ON tr.id = t.tree_id"
                    " WHERE tr.meta_key = 'module' AND t.meta = ?"
                    " AND t.is_active = 1", (module_name,)).fetchone()
                return r["id"] if r else None
            finally:
                tc.close()
        except Exception:
            return None

    def _file_ids(self, module_name):
        """module 名 -> {file_name: structure_module.id}（file 層 type=2）"""
        out = {}
        try:
            sc = sqlite3.connect(STRUCT_DB)
            sc.row_factory = sqlite3.Row
            try:
                mid = self._package_id(module_name)
                if not mid:
                    return out
                for r in sc.execute(
                        "SELECT id, value FROM structure_module"
                        " WHERE module_id = ? AND structure_type_id = 2"
                        " AND is_active = 1", (mid,)):
                    out[r["value"]] = r["id"]
            finally:
                sc.close()
        except Exception:
            pass
        return out

    def scan_formula_decorators_all(self):
        """掃全部 module 嘅 @formula_def（scan_all 嘅 formula 版本）"""
        results = []
        for entry in sorted(os.listdir(META_DIR)):
            folder = os.path.join(META_DIR, entry)
            if not os.path.isdir(folder):
                continue
            if entry.startswith("_"):
                continue
            if not os.path.isfile(os.path.join(folder, "__init__.py")):
                continue
            results.append(self.scan_formula_decorators(entry))
        return results

    # ---------- 內部 helper ----------
    def _structure_ids(self, module_name):
        """由 module 名攞 structure 層 id（module / skill / root）

        返回 {"module": [structure_module.id...], "skill": [...],
              "root": [structure_root.id...]}
        """
        out = {"module": {}, "skill": {}, "root": []}
        try:
            sc = sqlite3.connect(STRUCT_DB)
            sc.row_factory = sqlite3.Row
            try:
                # module 名 -> taxonomy.registry.id（tree = module）
                # 2026-10-26（用戶要求）：taxonomy.package 表已移除 ——
                # module 清單 = registry 表（tree = module；2026-10-27 rename）。
                tc = sqlite3.connect(TAXONOMY_DB)
                tc.row_factory = sqlite3.Row
                try:
                    pkg = tc.execute(
                        "SELECT t.id FROM registry t"
                        " JOIN tree tr ON tr.id = t.tree_id"
                        " WHERE tr.meta_key = 'module' AND t.meta = ?"
                        " AND t.is_active = 1", (module_name,)).fetchone()
                finally:
                    tc.close()
                if not pkg:
                    return out
                mid = pkg["id"]
                # structure_module（file 層 type=2）-> {file_name: id}
                out["module"] = {r["value"]: r["id"] for r in sc.execute(
                    "SELECT id, value FROM structure_module"
                    " WHERE module_id = ? AND structure_type_id = 2"
                    " AND is_active = 1", (mid,))}
                # structure_skill（父 = structure_module package 行）
                # value = function 名 -> {function 名: structure_skill.id}
                out["skill"] = {r["value"]: r["id"] for r in sc.execute(
                    "SELECT sk.id, sk.value FROM structure_skill sk"
                    " JOIN structure_module sm ON sm.id = sk.structure_module_id"
                    " WHERE sm.module_id = ? AND sk.is_active = 1", (mid,))}
                # structure_root
                out["root"] = [r["id"] for r in sc.execute(
                    "SELECT id FROM structure_root WHERE is_active = 1")]
            finally:
                sc.close()
        except Exception:
            pass
        return out

    def _write_analyze(self, struct_ids, function_id, file_name, function_name):
        """將 function 寫入各層 analyze 表

        file_name     = 邊個 .py 檔（用嚟 match structure_module file 層）
        function_name = function 名（用嚟 match structure_skill）
        """
        # module 層：match file 層（value = file_name）
        sm_id = struct_ids.get("module", {}).get(file_name)
        if sm_id:
            self.add_analyze("analyze_module", sm_id, function_id, commit=False)
        # skill 層：match function 名（value = function 名）
        sk_id = struct_ids.get("skill", {}).get(function_name)
        if sk_id:
            self.add_analyze("analyze_skill", sk_id, function_id, commit=False)
        # root 層
        for rt_id in struct_ids.get("root", []):
            self.add_analyze("analyze_root", rt_id, function_id, commit=False)
