"""decorators.py — @formula_def 裝飾器（2026-10-27 用戶要求 table-driven）

裝飾器本身只係「掛鉤」：
    @formula_def("prove_seq_by_id")
    def my_fn(): ...

公式嘅內容（formula_full / language / table / field / operator /
preflight_value / db_file / cuter_split）全部由 decorator 表話事。
ast 掃碼見到 @formula_def(<name>) -> 查 decorator 表 ->
register_formula_from_decorator() 建 formula 全套 + 回填出處。

呢度唔 import template（避免 circular）；只係定義裝飾器語法。
"""


def formula_def(name, **kwargs):
    """裝飾器：將一個 function 標記為「公式定義」

    name = decorator 表嘅 name（必填；內容由表話事）
    kwargs 可選覆寫（唔常用；表有就好）
    用法：
        @formula_def("prove_seq_by_id")
        def prove_seq(): ...
    """
    def _deco(fn):
        fn._formula_def = name
        fn._formula_def_kwargs = kwargs
        return fn
    return _deco


def formula_defs_from_module(mod):
    """（helper）由一個 module 攞全部 @formula_def 標記嘅 function

    返回 [{"name": decorator_name, "function": fn}, ...]
    """
    out = []
    for attr in dir(mod):
        obj = getattr(mod, attr, None)
        if callable(obj) and getattr(obj, "_formula_def", None):
            out.append({"name": obj._formula_def, "function": obj})
    return out