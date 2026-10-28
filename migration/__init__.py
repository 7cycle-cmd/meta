"""migration module — 遷移審計日誌（中央記錄）

用戶設計（2026-10-28）：
    id | run_id | api_id | taxonomy_id | structure_db_table | row_id | is_active

概念：
    migration ≠ api（api 係對外介面）
    sync 係 migration 一種（migration_type = schema/seed/sync/cutover/other）
    呢個 module 記錄「邊個 module 改過邊張表邊行」嘅完整審計

用法：
    from migration import Migration
    m = Migration()
    m.record("source", table="api", migration_type="schema",
             description="api 加 proven 欄")
"""

from .api import Migration

__all__ = ["Migration"]

__version__ = "1.0.0"
