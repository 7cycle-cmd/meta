-- schema dump: monitor.db
-- generated : 2026-10-27T15:47:40
-- objects   : 3（table=3）

-- [table] current_structure
CREATE TABLE current_structure (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    structure_type_id  INTEGER NOT NULL,  -- structure.db structure_type.id
    total              INTEGER NOT NULL DEFAULT 0,  -- 真實行數
    is_active          BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at         TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at         TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (structure_type_id)
);

-- [table] current_taxonomy
CREATE TABLE current_taxonomy (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    tree_id    INTEGER NOT NULL,  -- taxonomy.db tree.id
    total      INTEGER NOT NULL DEFAULT 0,  -- 真實行數
    is_active  BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (tree_id)
);

-- [table] sqlite_sequence
CREATE TABLE sqlite_sequence(name,seq);
