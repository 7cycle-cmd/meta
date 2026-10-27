"""character — 字符定義 layer

（2026-10-24s 由 terminology 拆出）
    字符集：symbol / letter / INT / letter_char_format

模組分工：
    schema.py  DDL（唯一 schema 來源）
    sql.py     資料庫存取層
    api.py     對外 API（Character 類）
"""

from .api import Character

__all__ = ["Character"]
__version__ = "1.0.0"