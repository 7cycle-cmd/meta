"""taxonomy — 分類學 package

模組分工：
    sql.py       tree / registry / physical_path 資料庫存取層
    api.py       對外 API（Taxonomy 類）
    route.py     命令行入口（CLI）
    rest_api.py REST API

用法：
    from taxonomy import Taxonomy
    t = Taxonomy()
    t.list_modules()
    t.register_module("codegen")
    t.register_skill("fill_value", "填入值")
    t.register_channel("cli", "命令列")
    t.close()
"""

from .api import Taxonomy

__all__ = ["Taxonomy"]
__version__ = "1.0.0"