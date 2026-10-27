"""guard — 寫入憑證守衛（2026-10-26 重建）

之前：全站 DB trigger + _guard 表 + task 訂單（過度設計，已刪）
而家：**守衛只存在於 rest_api（HTTP 入口）**

    guard.db.registry    每個有效 token 一行（by_id）：
        token_id  = 'module.file'（例如 terminology.api）
        module_id = taxonomy.taxonomy.id（tree=module）
        file_id   = structure_module file 行 id（可選）

    rest_api 驗證：?token= 或 X-API-Token header -> valid_token()。

模組分工：
    schema.py  DDL（唯一 schema 來源）
    sql.py     資料庫存取層
    api.py     對外 API（Guard 類）
"""

from .api import Guard

__all__ = ["Guard"]
__version__ = "2.0.0"
