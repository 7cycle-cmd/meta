-- schema dump: mcp.db
-- generated : 2026-10-27T16:21:48
-- objects   : 5（table=5）

-- [table] mcp_call
CREATE TABLE mcp_call (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    server_id   INTEGER NOT NULL,           -- FK -> mcp_server.id
    tool_id     INTEGER NOT NULL,           -- FK -> mcp_tool.id
    source_id   INTEGER NOT NULL,           -- source.db source.id（證明來源）
    task_id     INTEGER,                    -- task.db task.id（邊個 task 觸發）
    ok          BOOLEAN NOT NULL DEFAULT 1 CHECK (ok IN (0,1)),
    input_json  TEXT,                       -- 呼叫參數（JSON）
    output_json TEXT,                       -- 回傳結果（JSON）
    error       TEXT,                       -- 錯誤訊息（ok=0 時）
    duration_ms REAL,                       -- 執行時間（毫秒）
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- [table] mcp_server
CREATE TABLE mcp_server (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    meta        TEXT    NOT NULL UNIQUE,   -- server 名（python / sql）
    description TEXT,
    transport   TEXT    NOT NULL DEFAULT 'stdio',  -- stdio / sse / http
    command     TEXT,                       -- 啟動命令（例如 python -m mcp.server）
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- [table] mcp_tool
CREATE TABLE mcp_tool (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    server_id   INTEGER NOT NULL,           -- FK -> mcp_server.id
    meta        TEXT    NOT NULL,           -- tool 名（run_python / query）
    description TEXT,
    input_schema TEXT,                      -- JSON schema（參數）
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (server_id, meta)
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
