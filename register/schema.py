"""schema.py — register 權威 DDL 入口（唯一 schema 來源）

register.db 存放「註冊結果」：
    rest_api    REST API 註冊（module | type | api）—— 執行規則嘅結果
"""

# rest_api 表：REST API 註冊結果（2026-10-27 用戶要求）
#   一行 = 一個 module 嘅一個 REST API（由 rule 執行產生）
#   module    = module 名
#   type      = READ / WRITE（common.rest_api_type）
#   api       = API 名（/word-proof）
#   rule_id   = 邊條規則產生（rule.db rule.id）
REST_API_DDL = """
CREATE TABLE IF NOT EXISTS rest_api (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    module      TEXT    NOT NULL,           -- module 名
    type        TEXT    NOT NULL,           -- READ / WRITE
    api         TEXT    NOT NULL,           -- API 名（/word-proof）
    rule_id     INTEGER,                    -- rule.db rule.id（邊條規則）
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (module, type, api)
);
"""

__all__ = ["REST_API_DDL"]