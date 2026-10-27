"""ast — AST 分析 package

模組分工：
    sql.py       資料庫存取層（AST 掃描 + function 字典 + analyze 表）
    api.py       對外 API（Ast 類）
    route.py     命令行入口（CLI）

用法：
    from ast import Ast
    a = Ast()
    a.scan_module("codegen")
    a.scan_all()
    a.close()
"""

from .api import Ast

__all__ = ["Ast"]
__version__ = "1.0.0"
