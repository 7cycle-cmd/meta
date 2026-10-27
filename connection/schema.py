"""schema.py — connection 權威 DDL 入口（唯一 schema 來源）

由 sql.py 搬遷：IDENTITY_DDL, CONNECTION_REGISTRY_DDL, CONNECTION_DDL, CONNECTION_STATUS_DDL, CONNECTION_QUALITY_DDL
（7 檔標準：__init__/function/api/route/schema/sql/skill）
"""

IDENTITY_DDL = """
CREATE TABLE IF NOT EXISTS identity (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    meta        TEXT    NOT NULL UNIQUE,      -- sender / receiver
    description TEXT,
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

CONNECTION_REGISTRY_DDL = """
CREATE TABLE IF NOT EXISTS connection_registry (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    identity_id INTEGER NOT NULL,           -- identity.id（1=sender / 2=receiver）
    resource_id INTEGER NOT NULL,           -- resource.db registry.id（由 API 攞）
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (identity_id, resource_id)
);
"""

CONNECTION_DDL = """
CREATE TABLE IF NOT EXISTS connection (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    sender_id   INTEGER NOT NULL,          -- FK -> connection_registry.id(identity=1)（A）
    receiver_id INTEGER NOT NULL,          -- FK -> connection_registry.id(identity=2)（B）
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)), -- proof：連接存唔存在
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),  -- 最後連接時間
    UNIQUE (sender_id, receiver_id)
);
"""

CONNECTION_STATUS_DDL = """
CREATE TABLE IF NOT EXISTS connection_status (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    meta        TEXT    NOT NULL UNIQUE,   -- pass / fail
    description TEXT,
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

CONNECTION_QUALITY_DDL = """
CREATE TABLE IF NOT EXISTS connection_quality (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    connection_id  INTEGER NOT NULL,       -- FK -> connection.id
    status_id      INTEGER NOT NULL,       -- FK -> connection_status.id（pass / fail）
    is_active      BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),  -- proof：品質記錄存唔存在
    performance_ms REAL,                    -- 效能（毫秒）
    created_at     TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at     TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""
__all__ = ['IDENTITY_DDL', 'CONNECTION_REGISTRY_DDL', 'CONNECTION_DDL', 'CONNECTION_STATUS_DDL', 'CONNECTION_QUALITY_DDL']
