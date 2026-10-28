"""schema.py — role 權威 DDL 入口（唯一 schema 來源）

role.db 存放「角色」：
    registry    角色註冊（taxonomy_id | meta）

2026-10-27（用戶要求）：
    module : rule -> rename -> role
    remove -> table : role and rule
    table : registry + taxonomy_id
    role 同 rule 係 2 個獨立 module（之前擺埋一齊係錯）
"""

# registry 表：角色註冊（2026-10-27 用戶要求）
#   一行 = 一個角色（CQRS 身份）
#   taxonomy_id = taxonomy.registry.id（邊個 module 擁有）
#   meta        = 角色名（owner / reader / orderer / recorder ...）
REGISTRY_DDL = """
CREATE TABLE IF NOT EXISTS registry (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    taxonomy_id INTEGER NOT NULL,      -- taxonomy.registry.id（module 擁有者）
    meta        TEXT    NOT NULL,      -- 角色名（owner / reader / orderer ...）
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (taxonomy_id, meta)
);
"""
__all__ = ['REGISTRY_DDL']