-- schema dump: character.db
-- generated : 2026-10-27T16:21:48
-- objects   : 7（table=7）

-- [table] INT
CREATE TABLE "INT" (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    value       TEXT    NOT NULL UNIQUE,
    description TEXT,
    source_id   INTEGER,
    is_active   INTEGER NOT NULL DEFAULT 1,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- [table] letter
CREATE TABLE letter (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    letter_char_format_id  INTEGER NOT NULL,  -- letter_char_format.id（uppercase / lowercase）
    value                   TEXT    NOT NULL,  -- 字母本身（a-z / A-Z）
    description             TEXT,
    source_id               INTEGER,
    is_active               INTEGER NOT NULL DEFAULT 1,
    created_at              TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (letter_char_format_id, value)
);

-- [table] letter_char_format
CREATE TABLE letter_char_format (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    value       TEXT    NOT NULL UNIQUE,
    description TEXT,
    source_id   INTEGER,
    is_active   INTEGER NOT NULL DEFAULT 1,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

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

-- [table] symbol
CREATE TABLE symbol (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    value       TEXT    NOT NULL UNIQUE,
    description TEXT,
    source_id   INTEGER,
    is_active   INTEGER NOT NULL DEFAULT 1,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
