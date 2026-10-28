"""schema.py — preflight 權威 DDL 入口（唯一 schema 來源）

preflight.db 存放「起飛前檢查」：
    registry    全局 readiness 檢查（run_id 由 terminology 產生）

2026-10-27（用戶要求）：
    preflight 表同 schema 好相似（都係 run_id 主導 + 資源引用）
    分別係時機：
        preflight = before plan（全局：成個系統 ready 未？）
        schema    = before execution（局部：呢個 job 要嘅嘢 ready 未？）
"""

# registry 表：preflight 檢查登記（2026-10-27 用戶要求）
#   一行 = 一次全局 readiness 檢查（run_id 由 terminology flow 產生）
#   run_id                 = terminology.run.id（全站 flow 引擎產生）
#   plan_id                = sweep.target.id（可選；preflight 喺 plan 之前）
#   skill_id               = skill.id
#   resource_formula_id    = 資源 formula（未註冊）
#   resource_structure_id  = 資源 structure（未註冊）
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
__all__ = ['REGISTRY_DDL']