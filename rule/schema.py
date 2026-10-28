"""schema.py — rule 權威 DDL 入口（唯一 schema 來源）

rule.db 存放「自動化規則」：
    registry    規則註冊（taxonomy_id | flow_id | step_id | parameter）

2026-10-27（用戶要求）：
    auto = rule 話事 —— 每個 module 可以註冊自己嘅自動化規則
    flow_id / step_id 指 terminology.db（flow 引擎）嘅 flow + step
    setting 表唔需要（額外參數用 parameter 欄存 JSON）
"""

# registry 表：自動化規則註冊（2026-10-27 用戶要求）
#   一行 = 一條自動化規則
#   taxonomy_id = taxonomy.registry.id（邊個 module 要自動做嘢）
#   flow_id     = terminology.db flow.id（行邊條 flow）
#   step_id     = terminology.db step.id（行到邊個 step）
#   parameter   = 額外參數（JSON 字串；可選，取代 setting 表）
REGISTRY_DDL = """
CREATE TABLE IF NOT EXISTS registry (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    taxonomy_id INTEGER NOT NULL,      -- taxonomy.registry.id（module）
    flow_id     INTEGER NOT NULL,      -- terminology.db flow.id
    step_id     INTEGER NOT NULL,      -- terminology.db step.id
    parameter   TEXT,                  -- 額外參數（JSON，可選）
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (taxonomy_id, flow_id, step_id)
);
"""
__all__ = ['REGISTRY_DDL']