# -*- coding: utf-8 -*-
"""value/__init__.py — value（數值資產）package

value = 資產層：全站共用嘅「值」字典（id | value | taxonomy_id）

設計（2026-10-27 用戶要求）：
    每個 module 都可以登記一個值（asset）
    taxonomy_id = 邊個 module 登記（trace 用）

用法：
    from value import Value
    v = Value()
    vid = v.add("data", taxonomy_id=4)   # terminology 登記
    v.get(vid)                           # -> {"id":1, "value":"data", ...}
    v.list()                             # 全部
    v.close()
"""

from .api import Value

__all__ = ["Value"]
__version__ = "1.0.0"
