"""schema — 環境檢查層：mission 之前要過 schema 檢查（環境 ready 先可以做 mission） package

模組分工：
    sql.py       資料庫存取層（schema_check / schema_run 表）
    api.py       對外 API（Schema 類）

用法：
    from schema import Schema
    s = Schema()
    result = s.check_environment(task_id=1, required_apis=10)
    s.close()
"""

from .api import Schema

__all__ = ["Schema"]
__version__ = "1.0.0"