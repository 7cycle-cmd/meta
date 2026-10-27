-- schema dump: connection.db
-- generated : 2026-10-27T15:47:40
-- objects   : 8（table=8）

-- [table] connection
CREATE TABLE connection (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    sender_id   INTEGER NOT NULL,          -- FK -> sender.id（A）
    receiver_id INTEGER NOT NULL,          -- FK -> receiver.id（B）
    is_active   BOOLEAN NOT NULL DEFAULT 1, -- proof：連接存唔存在
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),  -- 最後連接時間
    UNIQUE (sender_id, receiver_id)
);

-- [table] connection_quality
CREATE TABLE connection_quality (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    connection_id  INTEGER NOT NULL,       -- FK -> connection.id
    status_id      INTEGER NOT NULL,       -- FK -> connection_status.id（pass / fail）
    is_active      BOOLEAN NOT NULL DEFAULT 1,  -- proof：品質記錄存唔存在
    performance_ms REAL,                    -- 效能（毫秒）
    created_at     TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at     TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- [table] connection_registry
CREATE TABLE connection_registry (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    identity_id INTEGER NOT NULL,           -- identity.id（1=sender / 2=receiver）
    resource_id INTEGER NOT NULL,           -- resource.db registry.id
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (identity_id, resource_id)
);

-- [table] connection_status
CREATE TABLE connection_status (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    meta        TEXT    NOT NULL UNIQUE,   -- pass / fail
    description TEXT,
    is_active   BOOLEAN NOT NULL DEFAULT 1,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- [table] identity
CREATE TABLE identity (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    meta        TEXT    NOT NULL UNIQUE,      -- sender / receiver
    description TEXT,
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
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
