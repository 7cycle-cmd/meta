"""schema.py — tool 權威 DDL 入口（唯一 schema 來源）

tool.db 存放「工具」：
    rest_api_WRITE    全站 WRITE API 中心（WRITE 中心 = tool）
    registry          工具註冊（module_id | skill_id | REST_API_WRITE_id | REST_API_READ_id）

2026-10-27（用戶要求）：
    tool = 一個 mission 可以攞到邊個工具幫手（by REST_API_id）
    READ 中心 = monitor（rest_api_READ）
    WRITE 中心 = tool（rest_api_WRITE）
    common.rest_api_type 已移除（READ/WRITE 由兩張表分開表達）
"""

# rest_api_WRITE 表：全站 WRITE API 中心（2026-10-27 用戶要求）
#   一行 = 一個 module 嘅 WRITE API（tool 中心，零 hardcode）
#   module_id = taxonomy.registry.id（邊個 module）
#   rest_api  = API 名（例如 /values /source-register ...）
REST_API_WRITE_DDL = """
CREATE TABLE IF NOT EXISTS rest_api_WRITE (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    module_id   INTEGER NOT NULL,      -- taxonomy.registry.id（module）
    rest_api    TEXT    NOT NULL,       -- API 名（/source-register）
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (module_id, rest_api)
);
"""

# registry 表：工具註冊（2026-10-27 用戶要求）
#   一行 = 一個工具（module + skill + 佢嘅 READ/WRITE API）
#   module_id          = taxonomy.registry.id（邊個 module 擁有）
#   skill_id           = skill.registry.id（邊個技能）
#   REST_API_WRITE_id  = tool.rest_api_WRITE.id（WRITE API）
#   REST_API_READ_id   = monitor.rest_api_READ.id（READ API）
REGISTRY_DDL = """
CREATE TABLE IF NOT EXISTS registry (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    module_id           INTEGER NOT NULL,  -- taxonomy.registry.id
    skill_id            INTEGER,           -- skill.registry.id
    REST_API_WRITE_id   INTEGER,           -- tool.rest_api_WRITE.id
    REST_API_READ_id    INTEGER,           -- monitor.rest_api_READ.id
    is_active           BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at          TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at          TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""
__all__ = ['REST_API_WRITE_DDL', 'REGISTRY_DDL']