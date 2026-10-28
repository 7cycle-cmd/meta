-- schema dump: guard.db
-- generated : 2026-10-27T16:21:48
-- objects   : 2（table=2）

-- [table] registry
CREATE TABLE registry (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    token_id    TEXT    NOT NULL UNIQUE,
    module_id   INTEGER NOT NULL,
    file_id     INTEGER,
    is_active   BOOLEAN NOT NULL DEFAULT 0 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- [table] sqlite_sequence
CREATE TABLE sqlite_sequence(name,seq);
