"""template — 模板層（2026-10-26 重做：完全獨立）

自己 12 張表（字典 seed + runtime 空），開新 module 嘅藍本。
唔再 clone question（用戶要求：independence）。

模組分工：
    schema.py  DDL（唯一 schema 來源，自己 12 張）
    sql.py     資料庫存取層（ensure_tables + 字典 seed）
    api.py     對外 API（Template 類）
"""

from .api import Template

__all__ = ["Template"]
__version__ = "1.0.0"