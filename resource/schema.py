"""schema.py — resource.db 權威 DDL 入口"""

TYPE_DDL = """
CREATE TABLE IF NOT EXISTS "type" (
    id          INTEGER PRIMARY KEY,
    type        TEXT    NOT NULL UNIQUE,
    is_active   INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

REGISTRY_DDL = """
CREATE TABLE IF NOT EXISTS registry (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    value       TEXT    NOT NULL,
    type_id     INTEGER NOT NULL,
    taxonomy_id INTEGER,
    is_active   INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (type_id) REFERENCES "type" (id)
);
"""

RESOURCE_TAXONOMY_DDL = """
CREATE TABLE IF NOT EXISTS resource_taxonomy (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    value_id    INTEGER NOT NULL,
    taxonomy_id INTEGER NOT NULL,
    is_active   INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (value_id) REFERENCES registry (id)
);
"""

# structure_taxonomy_id = structure.db structure_taxonomy.id（「有設定嘅組合」：
# 嗰行本身帶 tree_id × structure_type_id × is_active —— 例如 (3, 2, 5, 1)
# = tree_id 2(module) × structure_type_id 5(db) × is_active 1）
RESOURCE_STRUCTURE_DDL = """
CREATE TABLE IF NOT EXISTS resource_structure (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    value_id             INTEGER NOT NULL,
    structure_taxonomy_id INTEGER NOT NULL,  -- structure.db structure_taxonomy.id
    is_active            INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at           TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at           TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (value_id) REFERENCES registry (id)
);
"""

RESOURCE_FORMULA_DDL = """
CREATE TABLE IF NOT EXISTS resource_formula (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    value_id           INTEGER NOT NULL,
    formula_mapping_id INTEGER NOT NULL,
    is_active          INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at         TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at         TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (value_id) REFERENCES registry (id)
);
"""

# resource_schema 表（2026-10-28 用戶設計）：
#   一行 = 「邊個 module（taxonomy.tree_id）用邊個 schema（schema.db registry.id）」
#   schema.registry_id = schema.db registry.id（schema 執行登記，run_id 產生）
#   零 hardcode：tree_id / registry_id 都係其他 db 嘅真實 id
RESOURCE_SCHEMA_DDL = """
CREATE TABLE IF NOT EXISTS resource_schema (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    taxonomy_tree_id  INTEGER NOT NULL,   -- taxonomy.tree.id（channel / module / skill）
    schema_registry_id INTEGER NOT NULL,   -- schema.db registry.id
    is_active         INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at        TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at        TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (taxonomy_tree_id, schema_registry_id)
);
"""

# resource_tool 表（2026-10-28 用戶設計）：
#   一行 = 「邊個 module（taxonomy.tree_id）用邊個 tool（tool.db registry.id）」
#   tool.registry_id = tool.db registry.id（module_id + skill_id + WRITE + READ）
#   tool_registry_id 允許 NULL = 「未用任何 tool」嘅誠實狀態（唔可以 fake）
RESOURCE_TOOL_DDL = """
CREATE TABLE IF NOT EXISTS resource_tool (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    taxonomy_tree_id  INTEGER NOT NULL,   -- taxonomy.tree.id（channel / module / skill）
    tool_registry_id  INTEGER,            -- tool.db registry.id（NULL = 未用）
    is_active         INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at        TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at        TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (taxonomy_tree_id, tool_registry_id)
);
"""

DEFAULT_TYPES = [
    (1, "taxonomy"),
    (2, "structure"),
    (3, "formula"),
]

__all__ = [
    "TYPE_DDL",
    "REGISTRY_DDL",
    "RESOURCE_TAXONOMY_DDL",
    "RESOURCE_STRUCTURE_DDL",
    "RESOURCE_FORMULA_DDL",
    "RESOURCE_SCHEMA_DDL",
    "RESOURCE_TOOL_DDL",
    "DEFAULT_TYPES",
]
