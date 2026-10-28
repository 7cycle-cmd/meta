"""schema.py — migration 權威 DDL 入口（唯一 schema 來源）

migration = 全部 module 嘅遷移審計日誌（中央記錄）

用戶設計（2026-10-28，已修正）：
    id | run_id | type_id | taxonomy_id | structure_db_table | row_id | is_active
（2026-10-28 用戶修正：api_id -> type_id，+ type 字典表）
    type 表：id | value | description（value 幫助識別類型）

概念澄清：
    migration ≠ api（api 係對外 REST 介面）
    sync 係 migration 一種（type 字典 = schema/seed/sync/cutover/other）
    呢張表 = 每個 module 改過邊張表邊行嘅完整記錄

欄位：
    run_id              = run.id（邊次 flow 執行 / session）
    type_id             = type.id（migration type 字典：schema/seed/sync/cutover/other）
    taxonomy_id         = taxonomy.registry.id（邊個 module 做 migration）
    structure_db_table  = 改邊張表（structure.db db_table 名，DB 驅動）
    description         = 描述（例如「rebuild api 表加 proven 欄」）
    row_id              = 改邊行（0 = 全表）
    is_active           = 是否生效（0 = 已回滾/停用）
"""

# type 字典：migration 類型（2026-10-28 用戶設計）
# value 幫助識別（唔使淨靠 id）
TYPE_DDL = """
CREATE TABLE IF NOT EXISTS type (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    value       TEXT    NOT NULL UNIQUE,  -- schema / seed / sync / cutover / other
    description TEXT,                      -- 描述
    is_active   INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

# migration_log：遷移審計日誌（2026-10-28 用戶設計）
# type_id -> type.id（migration 類型：schema/seed/sync/cutover/other）
# flow_id  -> flow.id（行邊條 migration flow，2026-10-28 用戶要求）
# step_id  -> step.id（停喺邊步；全 pass = 最後一步）
MIGRATION_LOG_DDL = """
CREATE TABLE IF NOT EXISTS migration_log (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id             INTEGER,            -- terminology run.id（驗證鏈執行）
    type_id            INTEGER,            -- type.id（migration type 字典）
    taxonomy_id        INTEGER,            -- taxonomy.registry.id（邊個 module）
    structure_db_table TEXT,               -- 改邊張表（db_table 名）
    description        TEXT,               -- 描述
    row_id             INTEGER NOT NULL DEFAULT 0,  -- 改邊行（0 = 全表）
    flow_id            INTEGER,            -- flow.id（migration flow）
    step_id            INTEGER,            -- step.id（停喺邊步）
    is_active          INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at         TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

# flow 表：migration 流程（2026-10-28 用戶要求：migration 都要有 flow）
# 每個 migration type 一條 flow：
#   migrate_schema（建表/改表鏈）
#   migrate_seed（字典 seed 鏈）
#   migrate_sync（數據同步鏈）
#   migrate_cutover（搬遷鏈）
#   migrate_other（其他）
MIGRATION_FLOW_DDL = """
CREATE TABLE IF NOT EXISTS flow (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    flow_name  TEXT    NOT NULL UNIQUE,
    is_active  INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

# step 表：migration 流程步驟（2026-10-28 用戶要求）
# **每個 step = 1 line / 1 action**，有 input -> output
#   action       = 動作名（inspect_table / add_column ...）
#   input_desc   = 呢步食咩（例如「table 名」）
#   output_desc  = 呢步出咩（例如「現有欄位清單」）
# seq           = 第幾步（seq DT? 直接用序號）
MIGRATION_STEP_DDL = """
CREATE TABLE IF NOT EXISTS step (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    flow_id     INTEGER NOT NULL,   -- flow.id（邊條 migration 流程）
    seq         INTEGER NOT NULL,   -- 第幾步（1, 2, 3...）
    action      TEXT    NOT NULL,   -- 動作（1 line = 1 action）
    input_desc  TEXT,               -- 輸入（食咩）
    output_desc TEXT,               -- 輸出（出咩）
    is_active   INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (flow_id, seq)
);
"""

# step_log 表：每次 migration 執行嘅每步實際記錄（2026-10-28 用戶要求）
# run_id      = migration_log.id（邊次 migration）
# step_id     = step.id（行咗邊步）
# input_value_id  = value.db value.id（真實輸入，可證明）
# output_value_id = value.db value.id（真實輸出，可證明）
# input_value  = 實際輸入 snapshot（文字）
# output_value = 實際輸出 snapshot（文字）
# is_pass     = 0/1（呢步成功？）
# 2026-10-28（用戶）：all value must can proof at DB ——
# 每步 input/output 都入 value.db（value_id 指過去），唔淨係文字。
MIGRATION_STEP_LOG_DDL = """
CREATE TABLE IF NOT EXISTS step_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id          INTEGER NOT NULL,   -- migration_log.id
    step_id         INTEGER NOT NULL,   -- step.id
    input_value_id  INTEGER,            -- value.db value.id（真實輸入）
    output_value_id INTEGER,            -- value.db value.id（真實輸出）
    input_value     TEXT,               -- 實際輸入 snapshot（文字）
    output_value    TEXT,               -- 實際輸出 snapshot（文字）
    is_pass         INTEGER NOT NULL DEFAULT 1,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (run_id, step_id)
);
"""

__all__ = ['TYPE_DDL', 'MIGRATION_LOG_DDL',
           'MIGRATION_FLOW_DDL', 'MIGRATION_STEP_DDL', 'MIGRATION_STEP_LOG_DDL']
