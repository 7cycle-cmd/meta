"""schema.py — common 權威 DDL 入口（唯一 schema 來源）

2026-10-23：中央字典（action / status）——
所有 module 引用 common.db，唔好喺自己 DB 再複製 action/status 表。

設計：
    action    id | meta | is_active      動作字典（DROP/create/read/...）
    status    id | meta | is_active      狀態字典（active/dead/empty/...）

2026-10-23b：每資源嘅正確 action / status 選項（debug 用）——
    resource_action    id | ontology_id | filling_id | resource_id | action_id
    resource_status    id | ontology_id | filling_id | resource_id | status_id
    記錄「呢個資源喺呢個 ontology / filling 之下嘅正確選項」，
    option 會正確 + 幫手 debug（唔使估）。
"""

# 動作字典：id | meta | is_active
# 由舊 action 表合併（sweep.db / step.db / legacy registry）
# 大階 = 清理動作（DROP/KEEP/RENAME...）；小階 = 資料庫動作（create/read/update...）
ACTION_DDL = """
CREATE TABLE IF NOT EXISTS action (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    meta        TEXT    NOT NULL UNIQUE,   -- 動作名（DROP / create / read ...）
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

# 狀態字典：id | meta | is_active
# 由舊 status 表合併（sweep.db / legacy registry / na.db）
STATUS_DDL = """
CREATE TABLE IF NOT EXISTS status (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    meta        TEXT    NOT NULL UNIQUE,   -- 狀態名（active / dead / pending ...）
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

# 資源 × 動作選項：呢個資源（喺呢個 ontology / filling 下）嘅正確動作
RESOURCE_ACTION_DDL = """
CREATE TABLE IF NOT EXISTS resource_action (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ontology_id INTEGER,                    -- ontology.db ontology.id（可選：邊個 ontology）
    filling_id  INTEGER,                    -- code_gen.db filling.id（可選：邊個 filling）
    resource_id INTEGER NOT NULL,           -- resource.db registry.id（邊個資源）
    action_id   INTEGER NOT NULL,           -- common.db action.id（正確動作）
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (resource_id, action_id, ontology_id, filling_id)
);
"""

# 資源 × 狀態選項：呢個資源（喺呢個 ontology / filling 下）嘅正確狀態
RESOURCE_STATUS_DDL = """
CREATE TABLE IF NOT EXISTS resource_status (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ontology_id INTEGER,                    -- ontology.db ontology.id（可選：邊個 ontology）
    filling_id  INTEGER,                    -- code_gen.db filling.id（可選：邊個 filling）
    resource_id INTEGER NOT NULL,           -- resource.db registry.id（邊個資源）
    status_id   INTEGER NOT NULL,           -- common.db status.id（正確狀態）
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (resource_id, status_id, ontology_id, filling_id)
);
"""

# sweep_activity 表：資源清理活動記錄（中央）—— 所有 module 嘅清理動作都寫喺度
# 2026-10-23：action / status 中央化之後，清理活動都應該喺 common ——
# 每個資源嘅清理決定（DROP/KEEP/RENAME... + 狀態）一個地方記錄。
# 2026-10-23b：*sweep -> sweep_activity*（sweep 係一次清理任務嘅概念，
#             sweep_activity = 每個資源嘅活動記錄，sweep_id 指返父 sweep）
#    sweep_id    = 父 sweep 嘅 id（一次清理任務；可選）
#    resource_id = resource.db registry.id（邊個資源）
#    type_id     = common.db status.id（類型/狀態：empty/dead/legacy/active）
#    action_id   = common.db action.id（動作：DROP/KEEP/RENAME...）
SWEEP_ACTIVITY_DDL = """
CREATE TABLE IF NOT EXISTS sweep_activity (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    sweep_id    INTEGER,                    -- 父 sweep（一次清理任務；可選）
    resource_id INTEGER NOT NULL,           -- resource.db registry.id（邊個資源）
    type_id     INTEGER NOT NULL,           -- common.db status.id（類型/狀態）
    action_id   INTEGER NOT NULL,           -- common.db action.id（動作）
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

# migration_activity 表：資源遷移活動記錄（中央）—— proof migration 係真
# 2026-10-23：同 sweep_activity 模式 —— 每次 migration 動作（detect/apply/
# add_db_field/upgrade/compact）記錄一條，證明 migration 真係做咗（唔係 fake）。
#    migration_id      = 父 migration（一次遷移任務；可選）
#    resource_id       = resource.db registry.id（邊個資源被遷移）
#    resource_type_id  = registry.type_id（資源類型快照）
#    action_id         = common.db action.id（動作：ALTER/CREATE/DROP...）
#    status_id         = common.db status.id（狀態：active/done/...）
MIGRATION_ACTIVITY_DDL = """
CREATE TABLE IF NOT EXISTS migration_activity (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    migration_id     INTEGER,                    -- 父 migration（一次遷移任務；可選）
    resource_id      INTEGER NOT NULL,           -- resource.db registry.id（邊個資源）
    resource_type_id INTEGER,                    -- registry.type_id（資源類型快照）
    action_id        INTEGER NOT NULL,           -- common.db action.id（動作）
    status_id        INTEGER NOT NULL,           -- common.db status.id（狀態）
    is_active        BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at       TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at       TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

# 角色字典：id | meta | is_active —— 邊種職責身份（api / worker / migration...）
# 2026-10-23：guard 寫入證明時用 role_id 做「邊個角色做嘢」，
# 唔好 fallback 做 module 名。role 係業務身份（跨 module），
# module 係技術來源（邊個 code 檔）。
ROLE_DDL = """
CREATE TABLE IF NOT EXISTS role (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    meta        TEXT    NOT NULL UNIQUE,   -- 角色名（api / worker / migration / sweep ...）
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

# 位置字典：id | meta | value | is_active —— 通用位置（package 內第幾張表 / 欄位第幾個位）
# 2026-10-23：由 structure.db 搬過嚟 —— position 係跨 module 共用嘅字典，
# 應該同 action / status / role 一齊放喺 common（中央字典）。
# 2026-10-25（用戶要求）：加 value 欄（10-100 正規數值）—— meta 保留舊名兼容。
# 2026-10-27（用戶要求）：position -> seq（統一命名，配合 template 嘅 seq 字典）
SEQ_DDL = """
CREATE TABLE IF NOT EXISTS seq (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    meta        TEXT    NOT NULL UNIQUE,   -- 位置名（1 / 2 / 3 ...）
    value       INTEGER,                   -- 正規數值（10-100；2026-10-25 用戶要求）
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

# 布林字典：id | value | description | is_active —— 純值字典
# 2026-10-25（用戶要求新增）：只用嚟話你知「value 只有 0 / 1」——
# 唔係欄位名。db_field_check.boolean_id 引用呢度（CHECK 0/1 權威）。
BOOLEAN_DDL = """
CREATE TABLE IF NOT EXISTS boolean (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    value       INTEGER NOT NULL UNIQUE CHECK (value IN (0,1)),  -- 只有 0 / 1
    description TEXT,                       -- 人讀描述（0 = 否 / 1 = 是）
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

# token 表：寫入憑證（2026-10-26 用戶設計，取代 guard._guard 單列表）
# 每個「module × 檔案 × 角色」嘅有效 token 一行（by_id，零 hardcode）：
#    id         = token 行 id
#    token_id   = token 本身（文字識別，例如 'terminology.api'）
#    module_id  = taxonomy.taxonomy.id（邊個 module，tree=module）
#    file_id    = structure_module file 行 id（邊個檔案；可選 = 全 module）
#    role_id    = common.db role.id（邊個角色：api / worker / seed ...）
# 2026-10-26：guard module 已刪除 —— 中央 token 表放 common.db，
# rest_api 用嚟驗證「邊個 module 嘅邊個 HTTP 入口」有權寫入。
TOKEN_DDL = """
CREATE TABLE IF NOT EXISTS token (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    token_id    TEXT    NOT NULL UNIQUE,   -- token 文字識別（module.file）
    module_id   INTEGER NOT NULL,          -- taxonomy.taxonomy.id（tree=module）
    file_id     INTEGER,                   -- structure_module file 行 id（可選）
    role_id     INTEGER NOT NULL,          -- common.db role.id（api / worker ...）
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

# rest_api_type 表：REST API 類型字典（2026-10-27 用戶要求：放 common，all modules 共用）
#   一行 = 一個 REST API 類型
#   meta = 類型名：READ / WRITE
# 2026-10-27（用戶要求）：rest_api_type 已移除
# READ 中心 = monitor（rest_api_READ）
# WRITE 中心 = tool（rest_api_WRITE）
# 唔需要中央字典（READ/WRITE 由兩張表分開表達）

COMMON_DDL = (ACTION_DDL + STATUS_DDL + ROLE_DDL + SEQ_DDL + BOOLEAN_DDL
              + RESOURCE_ACTION_DDL + RESOURCE_STATUS_DDL
              + SWEEP_ACTIVITY_DDL + MIGRATION_ACTIVITY_DDL
              + TOKEN_DDL)

__all__ = ["ACTION_DDL", "STATUS_DDL", "ROLE_DDL", "SEQ_DDL",
           "BOOLEAN_DDL",
           "RESOURCE_ACTION_DDL",
           "RESOURCE_STATUS_DDL", "SWEEP_ACTIVITY_DDL",
           "MIGRATION_ACTIVITY_DDL", "TOKEN_DDL",
           "COMMON_DDL"]
