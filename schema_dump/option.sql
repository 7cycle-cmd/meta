-- schema dump: option.db
-- generated : 2026-10-27T15:47:40
-- objects   : 4（table=4）

-- [table] registry
CREATE TABLE registry (
    id INTEGER PRIMARY KEY AUTOINCREMENT, meta TEXT NOT NULL UNIQUE, description TEXT, is_active BOOLEAN NOT NULL CHECK (is_active IN (0,1)) DEFAULT 1, created_at TEXT DEFAULT (datetime('now', 'localtime')), updated_at TEXT DEFAULT (datetime('now', 'localtime'))
);

-- [table] skill
CREATE TABLE skill (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                meta_key    TEXT NOT NULL UNIQUE,
                description TEXT,
                is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
                created_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
            );

-- [table] sqlite_sequence
CREATE TABLE sqlite_sequence(name,seq);

-- [table] table_field_option
CREATE TABLE table_field_option (
    id                     INTEGER PRIMARY KEY AUTOINCREMENT,
    resource_id            INTEGER,   -- resource.db registry.id（舊；可選）
    structure_db_field_id  INTEGER,   -- structure.db structure_db_field.id（欄位）
    structure_db_table_id  INTEGER,   -- structure.db structure_db_table.id（表）
    value                  TEXT    NOT NULL,   -- 允許值（'0' / '1' / 'json' ...）
    description            TEXT,               -- 描述
    is_active              INTEGER NOT NULL DEFAULT 1,
    created_at             TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at             TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (resource_id, value),
    UNIQUE (structure_db_field_id, value)
);
