-- schema dump: mcp_hub.db
-- generated : 2026-10-27T16:21:48
-- objects   : 2（table=2）

-- [table] registry
CREATE TABLE registry (
    id INTEGER PRIMARY KEY AUTOINCREMENT, meta TEXT NOT NULL UNIQUE, description TEXT, is_active BOOLEAN NOT NULL CHECK (is_active IN (0,1)) DEFAULT 1, created_at TEXT DEFAULT (datetime('now', 'localtime')), updated_at TEXT DEFAULT (datetime('now', 'localtime'))
);

-- [table] sqlite_sequence
CREATE TABLE sqlite_sequence(name,seq);
