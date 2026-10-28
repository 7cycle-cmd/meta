"""schema.py — plan 權威 DDL 入口（唯一 schema 來源）

plan.db 存放「計劃」：
    plan    計劃表（preflight_id | role_id | rule_id | tool_id | value_id | run_id）

2026-10-27（用戶要求）：
    plan = preflight 通過之後先可以 plan
    時機鏈：preflight → plan → schema → task
    2026-10-27b：skill_id → tool_id（工具層話事）
    2026-10-27d：+ role_id（邊個角色落 order，role.db registry 表）
    2026-10-27e：+ rule_id（跟邊條規則，rule.db rule 表；多維度 SSOT）
"""

# plan 表：計劃（2026-10-27 用戶要求）
#   一行 = 一個計劃（preflight 通過之後先可以 plan）
#   preflight_id = preflight.registry.id（起飛前檢查通過咗）
#   role_id      = role.db registry.id（邊個角色落 order，2026-10-27d）
#   rule_id      = rule.db rule.id（跟邊條規則，2026-10-27e）
#   tool_id      = tool.registry.id（邊個工具幫手）
#   value_id     = value.id（處理邊個值）
#   run_id       = terminology.run.id（全站 flow 引擎產生）
PLAN_DDL = """
CREATE TABLE IF NOT EXISTS plan (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    preflight_id INTEGER NOT NULL,       -- preflight.registry.id
    role_id     INTEGER,                 -- role.db registry.id（邊個角色落 order）
    rule_id     INTEGER,                 -- rule.db rule.id（跟邊條規則）
    tool_id     INTEGER,                 -- tool.registry.id
    value_id    INTEGER,                 -- value.id
    run_id      INTEGER NOT NULL,        -- terminology.run.id（flow 產生）
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""
__all__ = ['PLAN_DDL']