"""connection — 連接證明 package

檢查表之間嘅 FK 連接（雙向證明）：
    唔單止「有人引用」，仲要證明引用嗰邊都活躍（有資料）。
    如果引用者都係空/孤島，連接唔成立 -> 兩邊都可以一齊清理。

模組分工：
    sql.py        檢查記錄（connection.db connection_run 表）
    api.py        Connection 類（check / scan / disconnected）
    route.py      CLI

用法：
    from connection import Connection
    c = Connection()
    result = c.check("taxonomy.db", "module")   # 檢查一張表
    report = c.scan()                            # 掃描所有 DB
    c.close()
"""

from .api import Connection

__all__ = ["Connection"]
__version__ = "1.0.0"