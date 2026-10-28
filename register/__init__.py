# -*- coding: utf-8 -*-
"""register/__init__.py — register（註冊）package

register = 註冊層：執行規則（rule）→ 寫入註冊結果（rest_api 等）

設計（2026-10-27 用戶要求）：
    rule     決定（邊啲要註冊）—— rule module
    register 執行（寫入註冊表）—— 呢度
    應用     自動註冊 REST API（taxonomy.rest_api）

用法：
    from register import Register
    reg = Register()
    reg.sync_rest_apis()   # 讀 rule -> 掃 module -> 註冊
    reg.list_rest_apis()
    reg.close()
"""

from .api import Register

__all__ = ["Register"]
__version__ = "1.0.0"