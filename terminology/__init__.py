"""terminology — 術語 package

模組分工：
    sql.py       資料庫存取層
    api.py       對外 API（Terminology 類）
    route.py     命令行入口（CLI）

用法：
    from terminology import Terminology
    t = Terminology()
    t.list_terms()
    t.close()
"""

from .api import Terminology

__all__ = ["Terminology"]
__version__ = "1.0.0"