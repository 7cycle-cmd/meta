"""skill package — migration 技能層（2026-10-29 用戶要求）

module : migration > package : skill

    schema.py   = migrate_schema 7 個真 action（SchemaSkill）
    audit.py    = migrate_audit 3 個真檢查（AuditSkill）
    seed.py     = migrate_seed 4 個真 action（SeedSkill）
    sync.py     = migrate_sync 5 個真 action（SyncSkill）
    cutover.py  = migrate_cutover 5 個真 action（CutoverSkill）
    other.py    = migrate_other 3 個真 action（OtherSkill）

用法：
    from migration.skill import SchemaSkill, SeedSkill, SyncSkill, \
        CutoverSkill, OtherSkill, AuditSkill
    s = SchemaSkill()
    s.check_column("source", "api", "proven")
    s.close()
"""

from .schema import SchemaSkill
from .audit import AuditSkill
from .seed import SeedSkill
from .sync import SyncSkill
from .cutover import CutoverSkill
from .other import OtherSkill

__all__ = ["SchemaSkill", "AuditSkill", "SeedSkill", "SyncSkill",
           "CutoverSkill", "OtherSkill"]