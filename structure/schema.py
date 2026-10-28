"""schema.py — structure 權威 DDL 入口（schema 集中地）

所有 schema 定義集中喺呢度：
    db_field_type      資料型別字典（INTEGER / TEXT / BOOLEAN / DATETIME）
    db_field_format    原子格式 token 字典（primary_key / unique / ...）
    db_field_property  型別 × 性質組合字典（db_field_type_id + db_field_format_id）
    db_field_check     規格檢查字典（db_field_property_id）
    structure_db_field 真表欄位（型別＋性質＋檢查）
    structure_db_table 真表定義（表名 → db_file）
    db_table_setting   通用欄位模板（一行 = 一個欄位）
fallback 值字典 = common.boolean（0/1；db_field_default 已移除 2026-10-25）。
db_field_position 已移除（2026-10-25：欄位次序由 structure_db_field.position_id 表達）。position 位置字典已搬去 common.db（2026-10-23 中央化）。
package_setting / package_type / column_definition 已移除（2026-10-23）。
db_field_format 由舊 db_field_setting（約束 token）rebuild 做原子 token
（2026-10-25）；db_field_xxxx 改名做 db_field_setting 後已移除（2026-10-25：
型別直接存欄位，性質直接掛欄位——冇中層）。
2026-10-25（用戶要求 rebuild）：db_field_unique -> id+value；
db_field_property -> 型別×性質字典；db_field_check -> 淨 property_id；
db_field_stucture / db_table_stucture renname 做 structure_db_field / structure_db_table。

sql.py 由呢度 import 全部 DDL 常量去執行（唯一擁有者：呢度 + sql.py 只執行）。
"""

# 由 sql.py re-export（避免重複定義，schema 權威 = 呢度）
from .sql import (  # noqa: F401
    DB_FIELD_TYPE_DDL,
    DEFAULT_FIELD_TYPES,
    DB_FIELD_UNIQUE_DDL,
    DEFAULT_FIELD_UNIQUES,
    DB_FIELD_SETTING_DDL,
    DEFAULT_FIELD_SETTINGS,
    DB_FIELD_PROPERTY_DDL,
    DB_FIELD_CHECK_DDL,
    VALUE_DDL,
    DEFAULT_VALUES,
    DB_TABLE_STRUCTURE_DDL,
    TABLE_COLUMN_DDL,
    DB_FIELD_DDL,
    DB_FIELD_FORMAT_DDL,
    DEFAULT_FIELD_FORMATS,
    DB_TABLE_SETTING_DDL,
    DB_TABLE_TYPE_DDL,
    POSITION_DDL,
    PACKAGE_TYPE_DDL,
    PACKAGE_SETTING_DDL,
    STRUCTURE_TAXONOMY_DDL,
    STRUCTURE_TYPE_DDL,
    STRUCTURE_ADDRESS_DDL,
    DEFAULT_STRUCTURE_TYPES,
    DEFAULT_STRUCTURE_ADDRESSES,
    STRUCTURE_FUNCTION_DDL,
)

__all__ = [
    "DB_FIELD_TYPE_DDL", "DEFAULT_FIELD_TYPES",
    "DB_FIELD_UNIQUE_DDL", "DEFAULT_FIELD_UNIQUES",
    "DB_FIELD_SETTING_DDL", "DEFAULT_FIELD_SETTINGS",
    "DB_FIELD_PROPERTY_DDL", "DB_FIELD_CHECK_DDL",
    "VALUE_DDL", "DEFAULT_VALUES",
    "DB_TABLE_STRUCTURE_DDL", "TABLE_COLUMN_DDL", "DB_FIELD_DDL",
    "DB_FIELD_FORMAT_DDL", "DEFAULT_FIELD_FORMATS",
    "DB_TABLE_SETTING_DDL", "DB_TABLE_TYPE_DDL", "POSITION_DDL",
    "PACKAGE_TYPE_DDL", "PACKAGE_SETTING_DDL",
    "STRUCTURE_TAXONOMY_DDL", "STRUCTURE_TYPE_DDL",
    "STRUCTURE_ADDRESS_DDL", "DEFAULT_STRUCTURE_TYPES",
    "DEFAULT_STRUCTURE_ADDRESSES",
    "STRUCTURE_FUNCTION_DDL",
]