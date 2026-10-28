-- schema dump: resource.db
-- generated : 2026-10-27T16:21:48
-- objects   : 6（table=6）

-- [table] registry
CREATE TABLE registry (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    value       TEXT    NOT NULL,
    type_id     INTEGER NOT NULL,
    taxonomy_id INTEGER,
    is_active   INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (type_id) REFERENCES "type" (id)
);

-- [table] resource_formula
CREATE TABLE resource_formula (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    value_id           INTEGER NOT NULL,
    formula_mapping_id INTEGER NOT NULL,
    is_active          INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at         TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at         TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (value_id) REFERENCES registry (id)
);

-- [table] resource_structure
CREATE TABLE resource_structure (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    value_id          INTEGER NOT NULL,
    structure_type_id INTEGER NOT NULL,
    is_active         INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at        TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at        TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (value_id) REFERENCES registry (id)
);

-- [table] resource_taxonomy
CREATE TABLE resource_taxonomy (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    value_id    INTEGER NOT NULL,
    taxonomy_id INTEGER NOT NULL,
    is_active   INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (value_id) REFERENCES registry (id)
);

-- [table] sqlite_sequence
CREATE TABLE sqlite_sequence(name,seq);

-- [table] type
CREATE TABLE "type" (
    id          INTEGER PRIMARY KEY,
    type        TEXT    NOT NULL UNIQUE,
    is_active   INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
