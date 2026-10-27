"""schema.py — identity 權威 DDL 入口

identity.db 唯一 schema（8 檔標準：schema.py required）。
表：
    registry  名字 -> id 對應（kind + name 唯一）
              額外：taxonomy_id（taxonomy 分類）、resource_id（resource 資源）
"""
import sqlite3

REGISTRY_DDL = """
CREATE TABLE IF NOT EXISTS registry (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    kind       TEXT NOT NULL,             -- package / skill / flow / step ...
    name       TEXT NOT NULL,             -- 個名（例如 codegen / create_table）
    ref_id     INTEGER,                   -- 對應返來源系統嘅 id（例如 system.skill.id）
    taxonomy_id INTEGER,                  -- taxonomy.db taxonomy.id（分類）
    resource_id INTEGER,                  -- resource.db resource.id（資源）
    description TEXT,
    is_active  BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (kind, name)
)
"""

# 舊名 alias（遷移期兼容：2026-10-23 identity 表改名做 registry）
IDENTITY_DDL = REGISTRY_DDL

# 支援嘅身份類型（kind）
KINDS = ["package", "flow", "step", "skill",
         "module", "resource", "db"]

__all__ = ["IDENTITY_DDL", "KINDS"]
