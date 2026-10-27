"""schema.py — monitor 權威 DDL 入口（唯一 schema 來源）"""

# current_structure 表：structure.db 各實體類型當前行數
#   id                 = 快照行 id
#   structure_type_id  = structure.db structure_type.id（1=package 2=file 3=db_table 4=db_field 5=db 6=root）
#   total              = 該實體類型喺 structure.db 嘅真實行數
CURRENT_STRUCTURE_DDL = """
CREATE TABLE IF NOT EXISTS current_structure (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    structure_type_id  INTEGER NOT NULL,  -- structure.db structure_type.id
    total              INTEGER NOT NULL DEFAULT 0,  -- 真實行數
    is_active          BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at         TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at         TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (structure_type_id)
);
"""

# current_taxonomy 表：taxonomy.db 各樹層當前行數
#   id         = 快照行 id
#   tree_id    = taxonomy.db tree.id（channel / module / skill）
#   total      = 該層喺 taxonomy.taxonomy 嘅真實行數
CURRENT_TAXONOMY_DDL = """
CREATE TABLE IF NOT EXISTS current_taxonomy (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    tree_id    INTEGER NOT NULL,  -- taxonomy.db tree.id
    total      INTEGER NOT NULL DEFAULT 0,  -- 真實行數
    is_active  BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (tree_id)
);
"""

__all__ = ["CURRENT_STRUCTURE_DDL", "CURRENT_TAXONOMY_DDL"]
