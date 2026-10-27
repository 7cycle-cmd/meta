"""monitor — 全站當前計數快照（2026-10-27）

兩張表：
    current_structure  id | structure_type_id | total   （structure.db 實體類型計數）
    current_taxonomy   id | taxonomy.tree_id  | total   （taxonomy.db 樹層計數）

total 由真實 DB 掃描填入，每次 refresh 更新（冪等）。
"""

from .api import Monitor

__all__ = ["Monitor"]
__version__ = "1.0.0"
