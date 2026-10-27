"""structure — DB 結構層 package

模組分工：
    sql.py       資料庫存取層
    api.py       對外 API（Structure 類）
    route.py     命令行入口（CLI）

用法：
    from structure import Structure
    s = Structure()
    s.list_db_field_settings()
    s.list_db_table_settings()
    s.close()
"""

from .api import Structure

__all__ = ["Structure"]
__version__ = "1.0.0"