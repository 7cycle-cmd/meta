"""schema.py — guard 權威 DDL 入口（唯一 schema 來源）

guard.db 存放「寫入憑證 registry」（2026-10-26 重建，用戶設計）：

    registry    每一行 = 一個有效 token（by_id，零 hardcode）：
        id         = token 行 id
        token_id   = token 文字識別（例如 'terminology.api'）
        module_id  = taxonomy.taxonomy.id（邊個 module，tree=module）
        file_id    = structure_module file 行 id（邊個檔案；可選 = 全 module）

設計原則（2026-10-26 用戶要求）：
    - 守衛只存在於 rest_api（HTTP 入口），內部直接 sqlite3.connect
    - token 喺 rest_api 驗證（?token= 或 X-API-Token header）有冇效
    - registry 係唯一 token 證明（存在 + 由配方 seed，唔係自行註冊）

（7 檔標準：__init__/function/api/route/schema/sql/skill）
"""

REGISTRY_DDL = """
CREATE TABLE IF NOT EXISTS registry (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    token_id    TEXT    NOT NULL UNIQUE,   -- token 文字識別（module.file）
    module_id   INTEGER NOT NULL,          -- taxonomy.taxonomy.id（tree=module）
    file_id     INTEGER,                   -- structure_module file 行 id（可選）
    is_active   BOOLEAN NOT NULL DEFAULT 0 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

__all__ = ["REGISTRY_DDL"]
