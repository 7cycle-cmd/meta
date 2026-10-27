"""api.py — ast.db 對外 API（AST 分析）"""

from .sql import SqlStore


class Ast:
    """AST 分析（ast.db）嘅對外介面

    用法：
        a = Ast()
        a.scan_module("codegen")   # 掃描一個 module
        a.scan_all()               # 掃描全部 module
        a.list_functions()         # 列出函數字典
        a.list_analyze("analyze_module")  # 列出 module 層分析
        a.close()
    """

    def __init__(self, db_path=None):
        self.store = SqlStore(db_path) if db_path else SqlStore()

    def close(self):
        self.store.close()

    # ---------- function 字典 ----------
    def list_functions(self, active_only=True):
        """列出函數字典（function JOIN function_class）"""
        return self.store.functions(active_only)

    def register_function(self, function, class_id=None,
                          programming_language_id=1):
        """登記一個函數（冪等）"""
        return self.store.add_function(function, class_id,
                                       programming_language_id)

    # ---------- function_class 字典 ----------
    def list_function_classes(self, active_only=True):
        """列出函數類別字典"""
        return self.store.function_classes(active_only)

    def register_function_class(self, meta, description=None):
        """登記一個函數類別（冪等）"""
        return self.store.add_function_class(meta, description)

    # ---------- analyze 表 ----------
    def list_analyze(self, table, active_only=True):
        """列出一個 analyze 表（analyze_root / analyze_module / analyze_skill）"""
        return self.store.analyze(table, active_only)

    # ---------- AST 掃描 ----------
    def scan_module(self, module_name):
        """AST 掃描一個 module，抽出 function 寫入 analyze 表"""
        return self.store.scan_module(module_name)

    def scan_all(self):
        """AST 掃描全部 module"""
        return self.store.scan_all()

    # ---------- formula decorator 掃描（2026-10-27 table-driven） ----------
    def scan_formula_decorators(self, module_name):
        """掃一個 module 嘅 .py，抽出 @formula_def 並回填 formula 出處

        內容由 template.decorator 表話事（table-driven）。
        """
        return self.store.scan_formula_decorators(module_name)

    def scan_formula_decorators_all(self):
        """掃全部 module 嘅 @formula_def"""
        return self.store.scan_formula_decorators_all()
