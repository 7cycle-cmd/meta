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
# ─── Postman 真實數據同步（2026-10-28，用戶要求）─────────────────────
# 證據原則：唔可以係 agent 自己生成 —— 一定要係 Postman 平台真實記錄，
# 經官方 API（api.postman.com + X-API-Key）拉返嚟，保留原始返回。

# postman_sync：每次 API 拉取嘅原始記錄（證據本身）
# api_type   -> workspace / environment / request / mock_list /
#               mock_responses / run_list / run
# url        -> 完整請求 URL（證明拉咗邊度）
# http_status-> HTTP 狀態（200 = 成功；401 = key 錯；404 = uid 唔存在）
# uid        -> Postman 物件 UID（如有）
# raw_json   -> Postman 官方 API 原封不動嘅 response body（鐵證）
# source_id  -> source.id=15（Postman API）；拉取來源證明
POSTMAN_SYNC_DDL = """
CREATE TABLE IF NOT EXISTS postman_sync (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    api_type    TEXT    NOT NULL,           -- workspace / environment / ...
    url         TEXT    NOT NULL,           -- 完整請求 URL
    http_status INTEGER NOT NULL,           -- 200 / 401 / 404 ...
    uid         TEXT,                       -- Postman 物件 UID（如有）
    raw_json    TEXT,                       -- 官方 API 原始返回（鐵證）
    source_id   INTEGER,                    -- source.id（15 = Postman API）
    note        TEXT,                       -- 記錄（錯誤原因 / 摘要）
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

# postman_mock：Mock Server 真實執行 log（用戶要嘅「執行記錄」）
# server_response_id -> Postman 平台 log 條目 ID
# collection_uid      -> 邊個 collection 被 mock
# mock_uid            -> 邊個 mock server 接咗
# method / request_path / request_headers / request_body
# response_status / response_headers / response_body（真實回應）
# created_at          -> Postman 平台記錄嘅時間（唔係本地時間）
POSTMAN_MOCK_DDL = """
CREATE TABLE IF NOT EXISTS postman_mock (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    sync_id             INTEGER NOT NULL,   -- postman_sync.id（原始證據）
    server_response_id  TEXT,               -- 平台 log ID
    collection_uid      TEXT,               -- collection UID
    mock_uid            TEXT,               -- mock server UID
    method              TEXT,               -- GET / POST ...
    request_path        TEXT,               -- 完整 path（含 query）
    request_headers     TEXT,               -- JSON（如有）
    request_body        TEXT,               -- JSON（如有）
    response_status     INTEGER,            -- 200 / 404 ...
    response_headers    TEXT,               -- JSON（如有）
    response_body       TEXT,               -- JSON（真實回應 body）
    postman_created_at  TEXT,               -- 平台記錄時間
    created_at          TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

# postman_mock_server：mock server 實體（1 行 per mock，2026-10-28）
# owner       -> 外部 owner：Postman account user id（由 /me API 攞）
# owner_name  -> Postman username（cyclegithub）
# 用途 = proof（證明 mock server 真係存在喺 Postman 平台）
POSTMAN_MOCK_SERVER_DDL = """
CREATE TABLE IF NOT EXISTS postman_mock_server (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    mock_uid        TEXT    NOT NULL UNIQUE,   -- Postman UID（59268432-...）
    mock_bare_id    TEXT,                       -- API 用 bare id（387d2903-...）
    name            TEXT    NOT NULL,           -- mock 名（meta-evidence-mock）
    mock_url        TEXT    NOT NULL,           -- https://xxx.mock.pstmn.io
    collection_uid  TEXT,                       -- 綁定嘅 collection
    environment_uid TEXT,                       -- 綁定嘅 environment
    is_public       INTEGER NOT NULL DEFAULT 1,
    owner           TEXT,                       -- Postman user id（59268432）
    owner_name      TEXT,                       -- Postman username（cyclegithub）
    source_id       INTEGER,                    -- source.id（15 = Postman API）
    synced_at       TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

# postman_mock_exec：每次真實執行（即時捕捉，2026-10-28）
# x_srv_trace / x_srv_span / cf_ray = Postman mock 平台 + Cloudflare
# 直接發出嘅執行追蹤 ID —— 唔可以偽造，證明「真係經 Postman 平台執行」
# 用途 = verify（驗證 rest_api 行為真係發生過）
POSTMAN_MOCK_EXEC_DDL = """
CREATE TABLE IF NOT EXISTS postman_mock_exec (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    server_id      INTEGER NOT NULL,   -- postman_mock_server.id
    method         TEXT    NOT NULL,   -- GET / POST ...
    path           TEXT    NOT NULL,   -- /get?run=meta-proof-1
    http_status    INTEGER NOT NULL,   -- 200 / 404 ...
    response_body  TEXT,               -- 實際回應 body（真實）
    x_srv_trace    TEXT,               -- 平台執行 ID（不可偽造）
    x_srv_span     TEXT,
    cf_ray         TEXT,               -- Cloudflare ray ID
    server_date    TEXT,               -- 平台 Date header
    captured_at    TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (server_id) REFERENCES postman_mock_server(id)
);
"""

# postman_run：Runner / Cloud Run 真實執行結果
# run_uid        -> Postman run ID
# collection_uid -> 邊個 collection 被執行
# environment_uid-> 用邊個 environment 執行
# status         -> running / failed / succeeded ...
# total / passed / failed / skipped（真實計數）
# test_results   -> 每個 assertion 嘅原始結果 JSON
# started_at / completed_at -> 平台記錄時間
POSTMAN_RUN_DDL = """
CREATE TABLE IF NOT EXISTS postman_run (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    sync_id         INTEGER NOT NULL,       -- postman_sync.id（原始證據）
    run_uid         TEXT,                   -- Postman run ID
    collection_uid  TEXT,                   -- collection UID
    environment_uid TEXT,                   -- environment UID
    status          TEXT,                   -- succeeded / failed ...
    total           INTEGER,                -- 總請求數
    passed          INTEGER,                -- 通過數
    failed          INTEGER,                -- 失敗數
    skipped         INTEGER,                -- 跳過數
    test_results    TEXT,                   -- assertion 原始結果 JSON
    started_at      TEXT,                   -- 平台 start
    completed_at    TEXT,                   -- 平台 complete
    created_at      TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

__all__ = ['SOURCE_TABLE_DDL', 'PROVIDER_TABLE_DDL',
           'API_TYPE_DDL', 'API_DDL', 'FLOW_DDL', 'SEQ_DDL', 'STEP_DDL',
           'STATUS_DDL', 'RUN_DDL', 'RESULT_DDL', 'SOURCE_PROOF_DDL',
           'VALUE_DDL', 'POSTMAN_SYNC_DDL', 'POSTMAN_MOCK_DDL',
           'POSTMAN_MOCK_SERVER_DDL', 'POSTMAN_MOCK_EXEC_DDL',
           'POSTMAN_RUN_DDL']
