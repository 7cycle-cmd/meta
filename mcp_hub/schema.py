"""schema.py — mcp_hub 權威 DDL 入口（唯一 schema 來源）

由 sql.py 搬遷：MCP_SERVER_DDL, MCP_TOOL_DDL, MCP_CALL_DDL
（7 檔標準：__init__/function/api/route/schema/sql/skill）
"""

MCP_SERVER_DDL = """
CREATE TABLE IF NOT EXISTS mcp_server (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    meta        TEXT    NOT NULL UNIQUE,   -- server 名（python / sql）
    description TEXT,
    transport   TEXT    NOT NULL DEFAULT 'stdio',  -- stdio / sse / http
    command     TEXT,                       -- 啟動命令（例如 python -m mcp.server）
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

MCP_TOOL_DDL = """
CREATE TABLE IF NOT EXISTS mcp_tool (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    server_id   INTEGER NOT NULL,           -- FK -> mcp_server.id
    meta        TEXT    NOT NULL,           -- tool 名（run_python / query）
    description TEXT,
    input_schema TEXT,                      -- JSON schema（參數）
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (server_id, meta)
);
"""

MCP_CALL_DDL = """
CREATE TABLE IF NOT EXISTS mcp_call (
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
"""
__all__ = ['MCP_SERVER_DDL', 'MCP_TOOL_DDL', 'MCP_CALL_DDL']
