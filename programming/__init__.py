"""programming — 程式語言/格式/組合規則 layer

（2026-10-24s 由 terminology 拆出）
    語言：  programming_language / language_alias
    格式：  data_format
    組合：  owner / owner_letter / owner_symbol / owner_INT / start_char

模組分工：
    schema.py  DDL（唯一 schema 來源）
    sql.py     資料庫存取層
    api.py     對外 API（Programming 類）
"""

from .api import Programming

__all__ = ["Programming"]
__version__ = "1.0.0"