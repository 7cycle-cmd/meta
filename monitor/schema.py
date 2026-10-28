"""schema.py — monitor 權威 DDL 入口（唯一 schema 來源）"""

# current_structure 表：structure.db 各實體類型當前行數
#   id                 = 快照行 id
#   structure_type_id  = structure.db structure_type.id（1=package 2=file 3=db_table 4=db_field 5=db 6=root）
#   total              = 該實體類型喺 structure.db 嘅真實行數
CURRENT_STRUCTURE_DDL = """
CREATE TABLE IF NOT EXISTS current_structure (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    structure_type_id  INTEGER NOT NULL,  -- structure.db structure_type.id
    total              INTEGER NOT NULL DEFAULT 0,  -- 真實行數
    is_active          BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at         TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at         TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (structure_type_id)
);
"""

# current_taxonomy 表：taxonomy.db 各樹層當前行數
#   id         = 快照行 id
#   tree_id    = taxonomy.db tree.id（channel / module / skill）
#   total      = 該層喺 taxonomy.taxonomy 嘅真實行數
CURRENT_TAXONOMY_DDL = """
CREATE TABLE IF NOT EXISTS current_taxonomy (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    tree_id    INTEGER NOT NULL,  -- taxonomy.db tree.id
    total      INTEGER NOT NULL DEFAULT 0,  -- 真實行數
    is_active  BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (tree_id)
);
"""

# db_field_check 表：structure.db db_field_check 快照（2026-10-27 用戶要求）
#   一行 = 一個 structure.db db_field_check 行嘅監控狀態
#   id                 = 快照行 id
#   db_field_check_id  = structure.db db_field_check.id（邊個值域 check）
#   json_not_integer   = json 係咪含「非整數」值（1=有 0=全整數）
#                        （值域入面有非 integer = 要留意）
DB_FIELD_CHECK_DDL = """
CREATE TABLE IF NOT EXISTS db_field_check (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    db_field_check_id  INTEGER NOT NULL,  -- structure.db db_field_check.id
    json_not_integer   BOOLEAN NOT NULL DEFAULT 0 CHECK (json_not_integer IN (0,1)),
    is_active          BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at         TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at         TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (db_field_check_id)
);
"""

# skill 表：monitor 技能登記（2026-10-27 用戶要求）
#   id           = 技能 id
#   resource_id  = 對應資源 id（db_field_check 快照行 / x = 任意資源）
#   value        = 技能名（json_not_integer = 監控「值域有冇非整數」）
SKILL_DDL = """
CREATE TABLE IF NOT EXISTS skill (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    resource_id INTEGER NOT NULL,  -- 對應資源 id（db_field_check.id）
    value       TEXT    NOT NULL,   -- 技能名（json_not_integer）
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

# skill 種子（冪等）：json_not_integer = 監控「db_field_check.json 有冇非整數」
DEFAULT_SKILLS = [
    (1, "json_not_integer", "監控 db_field_check.json 係咪含非整數值"),
]

# source_register 表：terminology.db source_register 快照（2026-10-27 用戶要求）
#   一行 = 一個詞 -> source 登記選擇嘅監控狀態
#   source_register_id = terminology.db source_register.id
#   word              = 詞
#   source_id         = source.db source.id（用邊個 source）
#   registered_by     = 邊個 caller 登記
SOURCE_REGISTER_DDL = """
CREATE TABLE IF NOT EXISTS source_register (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    source_register_id INTEGER NOT NULL,  -- terminology.db source_register.id
    word               TEXT    NOT NULL,   -- 詞
    source_id          INTEGER NOT NULL,   -- source.db source.id
    registered_by      TEXT,               -- 邊個 caller
    is_active          BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at         TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at         TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (source_register_id)
);
"""

# sweep 表：sweep.db 清理狀態快照（2026-10-27 用戶要求）
#   一行 = 一個 sweep target/run 嘅監控狀態
#   sweep_id        = sweep.db target.id（清理目標）
#   resource_id     = target.resource_id（db.table）
#   status_meta     = target 狀態（empty / dead / legacy / active / protected）
#   plan_action     = 計劃動作（DROP / KEEP / RENAME ...）
#   run_count       = 該 target 嘅 sweep_prove run 次數
#   last_run_status = 最近一次 run 狀態（approved / rejected）
SWEEP_DDL = """
CREATE TABLE IF NOT EXISTS sweep (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    sweep_id         INTEGER NOT NULL,  -- sweep.db target.id
    resource_id      TEXT,               -- target.resource_id（db.table）
    status_meta      TEXT,               -- empty / dead / legacy / active / protected
    plan_action      TEXT,               -- DROP / KEEP / RENAME ...
    run_count        INTEGER NOT NULL DEFAULT 0,  -- sweep_prove run 次數
    last_run_status  TEXT,               -- 最近 run 狀態（approved / rejected）
    is_active        BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at       TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at       TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (sweep_id)
);
"""

# fallback 表：後備值快照（2026-10-27 用戶要求）
#   一行 = 一個「後備/預設」監控狀態（例如 source_register 後備 source）
#   fallback_id    = 後備行 id
#   resource       = 後備屬於邊度（source_register / db_field_option ...）
#   value          = 後備值（例如 source_id=1）
#   description    = 描述
FALLBACK_DDL = """
CREATE TABLE IF NOT EXISTS fallback (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    fallback_id INTEGER,               -- 原表 id（可選）
    resource    TEXT    NOT NULL,      -- 後備屬於邊度（source_register / ...）
    value       TEXT    NOT NULL,      -- 後備值（例如 '1' = source_id）
    description TEXT,                  -- 描述
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (resource, value)
);
"""

# rest_api_READ 表：全站 READ API 中心（2026-10-27 用戶要求）
#   一行 = 一個 module 嘅 READ API（monitor 中心，零 hardcode）
#   taxonomy_id = taxonomy.registry.id（邊個 module）
#   rest_api    = API 名（例如 /source-register /word-proof ...）
REST_API_READ_DDL = """
CREATE TABLE IF NOT EXISTS rest_api_READ (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    taxonomy_id INTEGER NOT NULL,      -- taxonomy.registry.id（module）
    rest_api    TEXT    NOT NULL,       -- API 名（/source-register）
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (taxonomy_id, rest_api)
);
"""

# rest_api_watch 表：REST API 就緒度監控（2026-10-27 用戶要求）
#   一行 = 一個 module 嘅一個 API 嘅監控狀態（expected vs actual 比對）
#   taxonomy_id = taxonomy.registry.id（邊個 module）
#   rest_api    = API 名（/values /registry ...）
#   status      = ready（連續出現）/ missing（上個快照有、今次冇）/ new（新出現）
#   first_seen  = 第一次見到
#   last_seen   = 最近一次見到
REST_API_WATCH_DDL = """
CREATE TABLE IF NOT EXISTS rest_api_watch (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    taxonomy_id INTEGER NOT NULL,      -- taxonomy.registry.id（module）
    rest_api    TEXT    NOT NULL,       -- API 名（/values）
    status      TEXT    NOT NULL DEFAULT 'ready',  -- ready / missing / new
    first_seen  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    last_seen   TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (taxonomy_id, rest_api)
);
"""

__all__ = ["CURRENT_STRUCTURE_DDL", "CURRENT_TAXONOMY_DDL",
           "DB_FIELD_CHECK_DDL", "SKILL_DDL", "DEFAULT_SKILLS",
           "SOURCE_REGISTER_DDL", "SWEEP_DDL", "FALLBACK_DDL",
           "REST_API_READ_DDL", "REST_API_WATCH_DDL"]
