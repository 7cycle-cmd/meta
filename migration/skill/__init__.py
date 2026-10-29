"""skill package — migration 技能層（2026-10-29 用戶要求）

module : migration > package : skill > schema.py

    schema.py  = migrate_schema 7 個真 action（SchemaSkill）
                 inspect_table / check_column / add_column /
                 backfill_column / verify_column / verify_rowcount / report

用法：
    from migration.skill import SchemaSkill
    s = SchemaSkill()
    s.check_column("source", "api", "proven")
    s.close()
"""

from .schema import SchemaSkill

__all__ = ["SchemaSkill"]