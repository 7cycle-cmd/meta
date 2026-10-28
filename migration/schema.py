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
# flow_id  -> terminology.flow.id（行邊條 migration flow，2026-10-28 用戶要求；
#             flow/step 已全部喺 terminology.db，呢度由 run_id 反查）
# step_id  -> terminology.step.id（停喺邊步；全 pass = 最後一步）
MIGRATION_LOG_DDL = """
CREATE TABLE IF NOT EXISTS migration_log (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id             INTEGER,            -- terminology run.id（驗證鏈執行）
    type_id            INTEGER,            -- type.id（migration type 字典）
    taxonomy_id        INTEGER,            -- taxonomy.registry.id（邊個 module）
    structure_db_table TEXT,               -- 改邊張表（db_table 名）
    description        TEXT,               -- 描述
    row_id             INTEGER NOT NULL DEFAULT 0,  -- 改邊行（0 = 全表）
    flow_id            INTEGER,            -- terminology.flow.id（migration flow）
    step_id            INTEGER,            -- terminology.step.id（停喺邊步）
    is_active          INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at         TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

__all__ = ['TYPE_DDL', 'MIGRATION_LOG_DDL']
