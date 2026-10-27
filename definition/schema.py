"""schema.py — definition 權威 DDL 入口（唯一 schema 來源）

由 sql.py 搬遷：DESIGN_TABLES, COLUMN_DEFINITION_DDL, DB_TABLE_REQUIRED_DDL...

2026-10-25：structure / structure_parent / table_definition / taxonomy_dict
已移除（冇 owner，死表）。
2026-10-26：file_required 表移除 —— 檔案必需規則由 definition/sql.py
嘅 DEFAULT_FILE_TYPES（code 常數）提供；file_type / structure_file 亦已刪。
"""

DESIGN_TABLES = []

COLUMN_DEFINITION_DDL = ""

# db_table_required 表：必需表（2026-10-25 用戶要求 v2，同 file_required 設計）
# 字典（table_definition）喺 structure —— by API 攞。
# table_definition_id = structure.db table_definition.id（db_file + table_name）
# 存在呢張表 = 每個 module db 都要有呢張表（is_required 唔再要）。
DB_TABLE_REQUIRED_DDL = """
CREATE TABLE IF NOT EXISTS db_table_required (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    table_definition_id INTEGER NOT NULL,   -- structure.db table_definition.id
    seq_id              INTEGER NOT NULL,   -- common.seq.id（次序，by REST api；2026-10-27）
    is_active           BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at          TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at          TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (table_definition_id)
);
"""

# db_field_required 表：必需欄位（2026-10-25 用戶要求 v2，同 file_required 設計）
# 字典（db_field）喺 structure —— by API 攞。
# table_definition_id = structure.db table_definition.id（邊張表）
# db_field_id          = structure.db db_field.id（邊個欄位）
# 存在呢張表 = 每個 module 都要有呢個欄位。
DB_FIELD_REQUIRED_DDL = """
CREATE TABLE IF NOT EXISTS db_field_required (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    table_definition_id INTEGER NOT NULL,   -- structure.db table_definition.id
    db_field_id         INTEGER NOT NULL,   -- structure.db db_field.id
    seq_id              INTEGER NOT NULL,   -- common.seq.id（次序，by REST api；2026-10-27）
    is_active           BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at          TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at          TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (table_definition_id, db_field_id)
);
"""

# ==================================================================
# structure_required 表：每個大類（taxonomy.tree）必須有咩實體（2026-10-25 用戶要求）
# structure_type 字典喺 structure module（2026-10-25 搬遷）—— by API 攞。
# 關係同 taxonomy > tree 一樣：tree_id 指返 taxonomy.tree.id。
# 每個大類都要有齊（package / file / db_table / db_field / db）：
#   channel    -> package
#   module     -> package + db_table + db_field + db（module 要有表 + 欄位 + 自己嘅 .db）
#   skill      -> package + file
STRUCTURE_REQUIRED_DDL = """
CREATE TABLE IF NOT EXISTS structure_required (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    tree_id          INTEGER NOT NULL,     -- taxonomy.tree.id（channel / module / skill）
    structure_type_id INTEGER NOT NULL,    -- structure.db structure_type.id
    is_active        BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at       TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (tree_id, structure_type_id)
);
"""

# ==================================================================
# code_condition 定義表（純定義，零執行）+ 三張支援字典表
# 2026-10-24：定義層邊個 subject 對邊個 operator 期望咩 expected
#   subject  （例如 api.py 嘅 do_GET）
#   operator （必須 / 唔可以 / 至少一次）
#   expected （例如 /health 一定要有 route）
# 三張字典表支援 code_condition（subject_id / operator_id / expected_id），
# 每個字典項目都帶 resource_id（對應 resource.db registry，真正嘅 source of truth）
# ==================================================================

SUBJECT_DDL = """
CREATE TABLE IF NOT EXISTS subject (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    value       TEXT    NOT NULL UNIQUE,   -- 主體名（例如 api.py 嘅 do_GET）
    resource_id INTEGER,                   -- resource.db registry.id（source of truth）
    description TEXT,
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

OPERATOR_DDL = """
CREATE TABLE IF NOT EXISTS operator (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    value       TEXT    NOT NULL UNIQUE,   -- 必須 / 唔可以 / 至少一次
    resource_id INTEGER,                   -- resource.db registry.id（source of truth）
    description TEXT,
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

EXPECTED_DEF_DDL = """
CREATE TABLE IF NOT EXISTS expected_def (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    value       TEXT    NOT NULL UNIQUE,   -- 期望值（例如 /health 一定要有 route）
    resource_id INTEGER,                   -- resource.db registry.id（source of truth）
    description TEXT,
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

CODE_CONDITION_DDL = """
CREATE TABLE IF NOT EXISTS code_condition (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    subject_id  INTEGER NOT NULL,          -- subject.id（邊個 subject）
    operator_id INTEGER NOT NULL,          -- operator.id（必須 / 唔可以 / 至少一次）
    expected_id INTEGER NOT NULL,          -- expected_def.id（期望咩）
    description TEXT,
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (subject_id, operator_id, expected_id)
);
"""

__all__ = ['DESIGN_TABLES', 'COLUMN_DEFINITION_DDL', 'DB_TABLE_REQUIRED_DDL', 'DB_FIELD_REQUIRED_DDL', 'STRUCTURE_REQUIRED_DDL', 'SUBJECT_DDL', 'OPERATOR_DDL', 'EXPECTED_DEF_DDL', 'CODE_CONDITION_DDL']
