-- schema dump: identity.db
-- generated : 2026-10-27T15:47:40
-- objects   : 3（table=3）

-- [table] registry
CREATE TABLE "registry" (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                kind       TEXT NOT NULL,             -- package / skill / flow / step ...
                name       TEXT NOT NULL,             -- 個名（例如 codegen / create_table）
                ref_id     INTEGER,                   -- 對應返來源系統嘅 id（例如 system.registry.id）
                description TEXT,
                is_active  BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
                created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')), taxonomy_id INTEGER, resource_id INTEGER,
                UNIQUE (kind, name)
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
