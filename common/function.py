"""function.py — common 核心業務邏輯層

呢個 module 嘅核心邏輯全部喺 api.py class 方法內（真實業務邏輯）：

    Common: list_actions, get_action, action_id, register_action,
            list_statuses, get_status, status_id, register_status

（7 檔標準：__init__/function/api/route/schema/sql/skill 全部 required）
"""

import os


def stdlib_ast():
    """攞標準庫 ast module（繞過本地 `ast/` package shadow）

    2026-10-26：workspace 保留 `ast/` module（用戶清單），會 shadow
    Python 標準庫 ast —— 任何 `import ast` 喺 workspace root 跑都會
    攞到 `C:\\projects\\meta\\ast\\__init__.py`（AST parse 全部壞）。

    用法：
        from common import stdlib_ast
        ast = stdlib_ast()
        tree = ast.parse(src)

    **注意：SQL 程式根本唔應該在 process 內 import ast，呢個函數只係
    俾「真係要做 AST parse」嘅 code 用（例如 question 掃描自己檔案）。
    返回標準庫 ast module（Python313\\Lib\\ast.py）。**
    """
    import importlib.util
    import sys
    for _p in sys.path:
        if not _p or _p == r"C:\projects\meta" or _p.startswith(r"C:\projects\meta"):
            continue  # 跳過 workspace 路徑（含 ast/ package）
        _cand = os.path.join(_p, "ast.py")
        if os.path.isfile(_cand):
            _spec = importlib.util.spec_from_file_location("_stdlib_ast", _cand)
            if _spec and _spec.loader:
                _m = importlib.util.module_from_spec(_spec)
                try:
                    _spec.loader.exec_module(_m)
                except Exception:
                    continue
                return _m
    raise ImportError("搵唔到標準庫 ast（被本地 ast/ shadow）")
