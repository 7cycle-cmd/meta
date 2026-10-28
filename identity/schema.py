"""schema.py — identity 權威 DDL 入口

identity.db 唯一 schema（8 檔標準：schema.py required）。
表：
    registry  身份註冊（2026-10-28 改建：value × condition × flow × step）

2026-10-28（用戶要求）：
    舊設計 kind + name（package/flow/step/skill/module）已撤換
    -> 新設計：身份 = value + 證明鏈（condition × flow × step，5W2H 7 步）
       value = 身份主檔（value.db value.id）
       condition = 判斷條件（terminology.condition.id）
       flow = 證明 flow（terminology.flow.id）
       step = 證明步驟（terminology.step.id）
    5W2H 7 步：what / where / when / who / why / how / how much
"""
import sqlite3

REGISTRY_DDL = """
CREATE TABLE IF NOT EXISTS registry (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    value_id    INTEGER NOT NULL,             -- value.db value.id（身份主檔）
    condition_id INTEGER NOT NULL,            -- terminology.condition.id（判斷）
    flow_id     INTEGER NOT NULL,             -- terminology.flow.id（證明 flow）
    step_id     INTEGER NOT NULL,             -- terminology.step.id（證明步驟）
    taxonomy_id INTEGER,                      -- taxonomy.db taxonomy.id（分類）
    permit_id   INTEGER,                      -- permit.db permit.id（授權）
    description TEXT,
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (value_id, condition_id, flow_id, step_id)
)
"""

# 舊名 alias（遷移期兼容：2026-10-23 identity 表改名做 registry）
IDENTITY_DDL = REGISTRY_DDL

__all__ = ["IDENTITY_DDL"]
