"""option — 值域定義 layer

（2026-10-24u 用戶要求：option 唔止 0/1，擴展做 formula/filling 值域）
    每個資源（resource.db registry.id）有允許值清單。
    定義層 —— 唔執行，只定義「邊啲值合法」。
    證明 = 真實 run/result 記錄（唔係評估引擎）。

模組分工：
    schema.py  DDL（唯一 schema 來源）
    sql.py     資料庫存取層
    api.py     對外 API（Option 類）
"""

from .api import Option

__all__ = ["Option"]
__version__ = "1.0.0"