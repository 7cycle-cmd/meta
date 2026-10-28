"""schema.py — schema 權威 DDL 入口（唯一 schema 來源）

由 sql.py 搬遷：REGISTRY_DDL
（8 檔標準：__init__/function/api/route/schema/sql/registry/rest_api）

2026-10-27（用戶要求 redesign）：
    schema_check / schema_run 表已移除（drop）
    -> 新 registry 表：run_id 由 terminology 產生（全站 flow 引擎）
"""

# registry 表：schema 執行登記（2026-10-27 用戶要求 redesign）
#   一行 = 一個 schema 檢查（run_id 由 terminology flow 產生）
#   run_id                 = terminology.run.id（全站 flow 引擎產生）
#   plan_id                = sweep.target.id（value_id + condition_id 喺 run_id）
#   skill_id               = skill.id（邊個技能）
#   resource_formula_id    = 資源 formula（未註冊，等 terminology 註冊 taxonomy + structure）
#   resource_structure_id  = 資源 structure（未註冊，等 terminology 註冊 taxonomy + structure）
REGISTRY_DDL = """
CREATE TABLE IF NOT EXISTS registry (
    id                     INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id                 INTEGER NOT NULL,  -- terminology.run.id（flow 產生）
    plan_id                INTEGER,           -- sweep.target.id
    skill_id               INTEGER,           -- skill.id
    resource_formula_id    INTEGER,           -- 資源 formula（未註冊）
    resource_structure_id  INTEGER,           -- 資源 structure（未註冊）
    is_active              BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at             TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at             TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

# schema_registry 表（2026-10-28 用戶設計）：
#   schema 定義登記 —— 一行 = 一個 schema（DDL symbol）by id。
#   資源層（resource_schema.schema_registry_id）指向呢度（by_id，零 hardcode）。
#   meta   = schema 名（e.g. REGISTRY_DDL / CONDITION_DDL —— DDL symbol 名）
#   source = 定義來源（e.g. terminology/schema.py —— 邊個檔定義）
SCHEMA_REGISTRY_DDL = """
CREATE TABLE IF NOT EXISTS schema_registry (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    meta        TEXT    NOT NULL UNIQUE,  -- schema 名（DDL symbol：REGISTRY_DDL ...）
    source      TEXT,                     -- 定義來源（module/schema.py）
    description TEXT,
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""
__all__ = ['REGISTRY_DDL', 'SCHEMA_REGISTRY_DDL']
