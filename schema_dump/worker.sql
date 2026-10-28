-- schema dump: worker.db
-- generated : 2026-10-27T16:21:48
-- objects   : 9（table=9）

-- [table] provider
CREATE TABLE "provider" (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    meta        TEXT    NOT NULL UNIQUE,   -- Local / cloud（執行環境）
    description TEXT,
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
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

-- [table] token_usage
CREATE TABLE token_usage (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id     INTEGER NOT NULL,           -- task.db task.id（邊個 task）
    llm_id      INTEGER NOT NULL,           -- worker.id（邊個 LLM 代理）
    provider_id INTEGER NOT NULL DEFAULT 1, -- provider.id（1=Local 2=cloud 3=openrouter 4=vscode）
    input       INTEGER NOT NULL DEFAULT 0, -- input token 用量
    output      INTEGER NOT NULL DEFAULT 0, -- output token 用量
    fee         REAL    NOT NULL DEFAULT 0, -- 費用（元 / 美元；Local=0）
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
, "cache_read" INTEGER NOT NULL DEFAULT 0, "cache_write" INTEGER NOT NULL DEFAULT 0, "reasoning" INTEGER NOT NULL DEFAULT 0, "model" TEXT, "latency_ms" INTEGER, "request_id" TEXT);

-- [table] worker
CREATE TABLE worker (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL UNIQUE,   -- LLM 代理名（例如 Laya / DeepSeek V4 Flash 0731）
    session_id  TEXT,                       -- 對話 session id（VS Code chat session）
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
, provider_id INTEGER);

-- [table] worker_ability
CREATE TABLE worker_ability (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ability     TEXT    NOT NULL UNIQUE,   -- generatic / desicion / can_text / can_visual
    description TEXT,
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- [table] worker_identity
CREATE TABLE worker_identity (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    worker_id   INTEGER NOT NULL,           -- worker.id
    ability_id  INTEGER NOT NULL,           -- worker_ability.id
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (worker_id, ability_id)
);

-- [table] worker_token
CREATE TABLE worker_token (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    worker_id   INTEGER NOT NULL,           -- worker.id（邊個代理）
    condition_id INTEGER,                   -- 條件 id（邊個條件下用呢個 token 配額）
    token       INTEGER NOT NULL DEFAULT 0, -- token 配額
    input       INTEGER NOT NULL DEFAULT 0, -- 已用 input token
    output      INTEGER NOT NULL DEFAULT 0, -- 已用 output token
    fee         REAL    NOT NULL DEFAULT 0, -- 費用（元 / 美元）
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
, provider_id INTEGER NOT NULL DEFAULT 1);
