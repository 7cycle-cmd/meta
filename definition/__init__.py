"""definition — DB 欄位定義 package

模組分工：
    sql.py       資料庫存取層
    api.py       對外 API（Definition 類）
    route.py     命令行入口（CLI）

用法：
    from definition import Definition
    d = Definition()
    d.list_table_settings()
    d.close()
"""

from .api import Definition

__all__ = ["Definition"]
__version__ = "1.0.0"