"""schema — 環境檢查層：mission 之前要過 schema 檢查（環境 ready 先可以做 mission） package

模組分工：
    sql.py       資料庫存取層（registry 表）
    api.py       對外 API（Schema 類）

2026-10-27（用戶要求 redesign）：
    schema_check / schema_run 表已移除（drop）
    -> 新 registry 表：run_id 由 terminology 產生（全站 flow 引擎）

用法：
    from schema import Schema
    s = Schema()
    s.add_registry(run_id=1, plan_id=2, skill_id=3)
    s.close()
"""

from .api import Schema

__all__ = ["Schema"]
__version__ = "1.0.0"