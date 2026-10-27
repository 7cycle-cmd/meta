"""common — 常用字典 package（中央字典）

所有 module 共用嘅字典集中喺呢度，唔使每個 module 再建：
    action   動作字典（DROP / KEEP / create / read / update / delete / run ...）
    status   狀態字典（active / legacy / dead / empty / pending / done ...）

用法：
    from common import Common
    c = Common()
    c.action_id("DROP")     # 攞 action id
    c.status_id("active")   # 攞 status id
    c.close()
"""

from .api import Common
from .function import stdlib_ast

__all__ = ["Common", "stdlib_ast"]
__version__ = "1.0.0"
