"""schema.py — source 權威 DDL 入口（唯一 schema 來源）

由 sql.py 搬遷：SOURCE_TABLE_DDL, PROVIDER_TABLE_DDL
（2026-10-24p 用戶要求：字典表 language/speech/industry/spec 全數歸 terminology，
 source 只保留證明引擎 —— source/provider/api_type/api/flow/seq/step/status/run/result/source_proof/value）
（7 檔標準：__init__/function/api/route/schema/sql/skill）
"""

SOURCE_TABLE_DDL = """
CREATE TABLE IF NOT EXISTS source (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    source      TEXT    NOT NULL UNIQUE,   -- 來源（例如 Anthropic spec）
    provider_id INTEGER,                    -- 提供者（FK -> provider.id）
    description TEXT,                       -- 來源說明
    is_active   INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

PROVIDER_TABLE_DDL = """
CREATE TABLE IF NOT EXISTS provider (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    meta               TEXT    NOT NULL UNIQUE,   -- 提供者名（例如 Anthropic、ISO/IEC、IETF）
    authority_level_id INTEGER,                    -- 權威等級（字典：terminology.authority_level.id，冇 FK 因為跨 DB）
    industry_id        INTEGER,                    -- 行業（字典：terminology.industry.id，冇 FK 因為跨 DB）
    official_url       TEXT,                       -- 官方網址（例如 https://www.anthropic.com）
    description        TEXT,                       -- 提供者說明
    is_active          INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at         TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

# api_type 表：HTTP 方法字典（GET / POST / PUT / DELETE）
API_TYPE_DDL = """
CREATE TABLE IF NOT EXISTS api_type (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    value       TEXT    NOT NULL UNIQUE,   -- GET / POST / PUT / DELETE
    description TEXT,                       -- 描述
    is_active   INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

# api 表：module 對外 REST API 註冊（module 之間點樣 work together）
# 2026-10-24（用戶要求）：question & source 點樣經 API 合作要有表管理。
# 每個 module 自己 DB 有呢張表 —— 記錄自己對外開放嘅 API。
# api_type_id -> api_type.id（GET / POST）
# flow_id     -> 呢條 API 屬於邊條 flow（跨 module：query/question 嘅 flow）
# value_id    -> 呢條 API 消耗邊種 value（跨 module：value 表）
# status_id   -> status.id（active / deprecated...）
API_DDL = """
CREATE TABLE IF NOT EXISTS api (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    api         TEXT    NOT NULL,           -- API 路徑（例如 /sources）
    api_type_id INTEGER NOT NULL,           -- api_type.id（GET / POST）
    flow_id     INTEGER,                    -- flow.id（呢條 API 屬於邊條 flow）
    value_id    INTEGER,                    -- value.id（呢條 API 消耗邊種 value）
    description TEXT,                       -- 描述
    status_id   INTEGER,                    -- status.id（1=active 2=deprecated）
    is_active   INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (api, api_type_id)
);
"""

# flow 表：驗證鏈（同 question module 一樣設計）
# 2026-10-24（用戶要求）：source 都要有 flow + step，
# 令 api.flow_id 有實際目標（/languages /charsets 屬於邊條 source flow）。
FLOW_DDL = """
CREATE TABLE IF NOT EXISTS flow (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    flow_name  TEXT    NOT NULL UNIQUE,   -- 驗證鏈名（source / charsets / languages ...）
    is_active  INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

# seq 表：序號字典（第幾步，由表控制）—— 同 question 一樣
SEQ_DDL = """
CREATE TABLE IF NOT EXISTS seq (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    seq         INTEGER NOT NULL UNIQUE,  -- 序號（1, 2, 3... 10）
    is_active   INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

# step 表：驗證鏈步驟（同 question 一樣設計，但 source 版指 source 表）
# flow_id   -> flow.id（邊條驗證鏈）
# source_id -> source.id（確認邊個來源 —— 等於 question 版嘅 question_id）
# seq_id    -> seq.id（第幾步）
STEP_DDL = """
CREATE TABLE IF NOT EXISTS step (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    flow_id        INTEGER NOT NULL,   -- flow.id（邊條驗證鏈）
    source_id      INTEGER NOT NULL,   -- source.id（檢查邊個來源）
    seq_id         INTEGER NOT NULL,   -- seq.id（第幾步：1, 2, 3...）
    is_active      INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at     TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at     TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (flow_id, seq_id)
);
"""

# status 表：狀態字典（同 question 一樣）
STATUS_DDL = """
CREATE TABLE IF NOT EXISTS status (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    status     TEXT    NOT NULL UNIQUE,   -- approved / rejected / NA
    is_active  INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

# value 表：提交值字典（同 question 一樣設計）
# 2026-10-24n（用戶要求）：api.value_id 唔可以 NULL ——
# source 都要有 value 表，每條 API 消耗嘅值註冊喺度。
VALUE_DDL = """
CREATE TABLE IF NOT EXISTS value (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    value       TEXT,                      -- 值（source / provider / industry...）
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

# run 表：flow 執行記錄（同 question 一樣設計）
# 2026-10-24i（用戶要求）：source 都要有 run + result ——
# 令 register 可以「先 flow/step 定義 → 後 proof（provider_id）驗證」。
# flow_id   -> flow.id（行邊條驗證鏈）
# step_id   -> step.id（停喺邊步，第一個 fail 就停）
# status_id -> status.id（1=approved 2=rejected 3=NA）
RUN_DDL = """
CREATE TABLE IF NOT EXISTS run (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    flow_id    INTEGER NOT NULL,   -- flow.id（邊條驗證鏈）
    step_id    INTEGER,            -- step.id（停喺邊步）
    status_id  INTEGER,            -- status.id（1=approved 2=rejected 3=NA）
    is_active  INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

# result 表：每個 step 嘅驗證結果（證明）
# source 版冇 answer（唔係 1/0 問題）—— 證明 = provider 存在 + URL 非空
# run_id    -> run.id（邊次執行）
# step_id   -> step.id（驗證邊步）
# source_id -> source.id（驗證邊個來源）
# has_provider   -> 有冇 provider（0/1）
# has_url        -> provider 有冇 official_url（0/1）
# status_id      -> status.id（1=approved 2=rejected 3=NA）
RESULT_DDL = """
CREATE TABLE IF NOT EXISTS result (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id       INTEGER NOT NULL,    -- run.id（邊次執行）
    step_id      INTEGER NOT NULL,    -- step.id（驗證邊步）
    source_id    INTEGER NOT NULL,    -- source.id（驗證邊個來源）
    has_provider INTEGER NOT NULL DEFAULT 0,  -- provider 存在（0/1）
    has_url      INTEGER NOT NULL DEFAULT 0,  -- official_url 非空（0/1）
    status_id    INTEGER,             -- status.id（1=approved 2=rejected 3=NA）
    created_at   TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (run_id, step_id)
);
"""

# source_proof 表：詞 → source 證明（source module 資產）
# 2026-10-24j（用戶要求）：proof source 應該由 module : source 擁有，
# 唔係 codegen 擁有 + terminology.db 存放。呢張表取代
# is_english.source_id / is_industry_spec.source_id。
# 2026-10-24m（用戶要求）：word_source 改名 source_proof。
# word      -> 詞（例如 'definition' / 'mcp'）
# source_id -> source.id（證明來源）
# proof     -> proof 文字（例如 'Wikipedia: Identifier'）
# 2026-10-24l（用戶要求）：caller 記錄 —— 邊個模組批准註冊 + 邊次 flow run
# registered_by -> caller 模組名（verify / question / system...）
# run_id        -> source flow run.id（批准嗰次驗證）
# source 證明：詞有冇來源證明，由 source module 管
SOURCE_PROOF_DDL = """
CREATE TABLE IF NOT EXISTS source_proof (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    word          TEXT    NOT NULL UNIQUE,   -- 詞（mcp / definition...）
    source_id     INTEGER,                   -- source.id（證明來源）
    proof         TEXT,                      -- proof 文字（'Provider: Topic'）
    description   TEXT,                       -- 描述
    registered_by TEXT,                       -- 邊個 caller 批准（verify...）
    run_id        INTEGER,                    -- source run.id（批准嗰次驗證）
    is_active     INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at    TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at    TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""
__all__ = ['SOURCE_TABLE_DDL', 'PROVIDER_TABLE_DDL',
           'API_TYPE_DDL', 'API_DDL', 'FLOW_DDL', 'SEQ_DDL', 'STEP_DDL',
           'STATUS_DDL', 'RUN_DDL', 'RESULT_DDL', 'SOURCE_PROOF_DDL',
           'VALUE_DDL']
