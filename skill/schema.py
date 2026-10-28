"""skill module 權威 DDL。

2026-10-27（用戶要求 redesign）：
    registry 表：id | name | resource_formula_id | resource_structure_id
    module_skill 表已移除（drop）
"""

REGISTRY_DDL = """
CREATE TABLE IF NOT EXISTS registry (
    id                     INTEGER PRIMARY KEY AUTOINCREMENT,
    name                   TEXT    NOT NULL UNIQUE,  -- 技能名（例如 word_proof / build）
    resource_formula_id    INTEGER,                  -- 資源 formula（未註冊）
    resource_structure_id  INTEGER,                  -- 資源 structure（未註冊）
    is_active              BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at             TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at             TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

__all__ = ["REGISTRY_DDL"]
