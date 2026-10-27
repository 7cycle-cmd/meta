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
    "DEFAULT_TYPES",
]
