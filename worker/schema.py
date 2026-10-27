"""schema.py — worker 權威 DDL 入口（唯一 schema 來源）

由 sql.py 搬遷：WORKER_DDL, WORKER_ABILITY_DDL, WORKER_IDENTITY_DDL, PROVIDER_DDL, WORKER_TOKEN_DDL, TOKEN_USAGE_DDL
（7 檔標準：__init__/function/api/route/schema/sql/skill）
"""

WORKER_DDL = """
CREATE TABLE IF NOT EXISTS worker (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    name           TEXT    NOT NULL UNIQUE,  -- LLM 代理名（例如 Laya / DeepSeek V4 Flash 0731）
    session_id     TEXT,                      -- 對話 session id（VS Code chat session）
    provider_id    INTEGER,                   -- provider.id（1=Local / 2=cloud / 3=openrouter / 4=vscode）
    is_active      BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at     TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at     TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

WORKER_ABILITY_DDL = """
CREATE TABLE IF NOT EXISTS worker_ability (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ability     TEXT    NOT NULL UNIQUE,   -- generatic / desicion / can_text / can_visual
    description TEXT,
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

WORKER_IDENTITY_DDL = """
CREATE TABLE IF NOT EXISTS worker_identity (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    worker_id   INTEGER NOT NULL,           -- worker.id
    ability_id  INTEGER NOT NULL,           -- worker_ability.id
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (worker_id, ability_id)
);
"""

PROVIDER_DDL = """
CREATE TABLE IF NOT EXISTS provider (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    meta        TEXT    NOT NULL UNIQUE,   -- Local / cloud / openrouter / vscode
    description TEXT,
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

WORKER_TOKEN_DDL = """
CREATE TABLE IF NOT EXISTS worker_token (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    worker_id   INTEGER NOT NULL,           -- worker.id（邊個代理）
    provider_id INTEGER NOT NULL DEFAULT 1, -- provider.id（1=Local 2=cloud 3=openrouter 4=vscode）
    condition_id INTEGER,                   -- 條件 id（邊個條件下用呢個 token 配額）
    token       INTEGER NOT NULL DEFAULT 0, -- token 配額
    input       INTEGER NOT NULL DEFAULT 0, -- 已用 input token
    output      INTEGER NOT NULL DEFAULT 0, -- 已用 output token
    fee         REAL    NOT NULL DEFAULT 0, -- 費用（元 / 美元）
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

TOKEN_USAGE_DDL = """
CREATE TABLE IF NOT EXISTS token_usage (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id      INTEGER NOT NULL,           -- task.db task.id（邊個 task）
    llm_id       INTEGER NOT NULL,           -- worker.id（邊個 LLM 代理）
    provider_id  INTEGER NOT NULL DEFAULT 1, -- provider.id（1=Local 2=cloud 3=openrouter 4=vscode）
    input        INTEGER NOT NULL DEFAULT 0, -- input token 用量
    output       INTEGER NOT NULL DEFAULT 0, -- output token 用量
    cache_read   INTEGER NOT NULL DEFAULT 0, -- prompt cache read token（命中快取）
    cache_write  INTEGER NOT NULL DEFAULT 0, -- prompt cache write token（寫入快取）
    reasoning    INTEGER NOT NULL DEFAULT 0, -- reasoning / thinking token
    model        TEXT,                        -- 實際 model 名（例如 deepseek-chat）
    latency_ms   INTEGER,                     -- 延遲（毫秒）
    request_id   TEXT,                        -- provider 嘅 request id（追帳單）
    fee          REAL    NOT NULL DEFAULT 0, -- 費用（元 / 美元；Local=0）
    created_at   TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""
__all__ = ['WORKER_DDL', 'WORKER_ABILITY_DDL', 'WORKER_IDENTITY_DDL', 'PROVIDER_DDL', 'WORKER_TOKEN_DDL', 'TOKEN_USAGE_DDL']
