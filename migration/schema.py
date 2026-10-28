"""schema.py — migration 權威 DDL 入口（唯一 schema 來源）

migration = 全部 module 嘅遷移審計日誌（中央記錄）

用戶設計（2026-10-28）：
    id | run_id | api_id | taxonomy_id | structure_db_table | row_id | is_active

概念澄清：
    migration ≠ api（api 係對外 REST 介面）
    sync 係 migration 一種（migration_type = schema/seed/sync/cutover）
    呢張表 = 每個 module 改過邊張表邊行嘅完整記錄

欄位：
    run_id              = run.id（邊次 flow 執行 / session）
    api_id              = api.id（經邊條 api 觸發；冇 = 內部啟動）
    taxonomy_id         = taxonomy.registry.id（邊個 module 做 migration）
    structure_db_table  = 改邊張表（structure.db db_table 名，DB 驅動）
    migration_type      = schema（建表/改表）/ seed（字典）/ sync（數據同步）
                          / cutover（搬遷）/ other
    description         = 描述（例如「rebuild api 表加 proven 欄」）
    row_id              = 改邊行（0 = 全表）
    is_active           = 是否生效（0 = 已回滾/停用）
"""

# migration_log：遷移審計日誌（2026-10-28 用戶設計 + migration_type）
MIGRATION_LOG_DDL = """
CREATE TABLE IF NOT EXISTS migration_log (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id             INTEGER,            -- run.id（邊次執行；冇 = NULL）
    api_id             INTEGER,            -- api.id（經 api 觸發；內部啟動 = NULL）
    taxonomy_id        INTEGER,            -- taxonomy.registry.id（邊個 module）
    structure_db_table TEXT,               -- 改邊張表（db_table 名）
    migration_type     TEXT    NOT NULL DEFAULT 'schema',
                                           -- schema / seed / sync / cutover / other
    description        TEXT,               -- 描述
    row_id             INTEGER NOT NULL DEFAULT 0,  -- 改邊行（0 = 全表）
    is_active          INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at         TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

__all__ = ['MIGRATION_LOG_DDL']
