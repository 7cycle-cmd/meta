"""schema.py — permit 權威 DDL 入口（唯一 schema 來源）

permit.db 存放「授權」：
    permit       授權記錄（subject_id | permit_type_id | object_id）
    permit_type  許可類型字典（call / read / write / run ...）
    subject      主體（subject | subject_type_id）
    subject_type 主體類型字典（module / split_value / worker ...）
    object       目標（object | object_type_id）
    object_type  目標類型字典（terminology / rest_api / flow ...）

2026-10-28（用戶要求）：
    permit = subject × permit × object（統一授權模型）
    取代分散式：value.terminology / role / rule / tool 嘅授權維度
"""

# subject_type 表：主體類型字典
SUBJECT_TYPE_DDL = """
CREATE TABLE IF NOT EXISTS subject_type (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    subject_type TEXT NOT NULL UNIQUE,   -- module / split_value / worker / tool ...
    description TEXT,
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

# 預設主體類型種子（冪等）
DEFAULT_SUBJECT_TYPES = [
    ("module",      "taxonomy.registry.id（module）"),
    ("split_value", "value.split_value.id（拆分值）"),
    ("worker",      "worker.id（LLM 代理）"),
    ("tool",        "tool.registry.id（工具）"),
]

# subject 表：主體
SUBJECT_DDL = """
CREATE TABLE IF NOT EXISTS subject (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    subject         TEXT    NOT NULL,      -- 主體識別（例如 value.split_value.1）
    subject_type_id INTEGER NOT NULL,      -- subject_type.id
    is_active       BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at      TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at      TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (subject, subject_type_id)
);
"""

# object_type 表：目標類型字典
OBJECT_TYPE_DDL = """
CREATE TABLE IF NOT EXISTS object_type (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    object_type TEXT NOT NULL UNIQUE,    -- terminology / rest_api / flow / step ...
    description TEXT,
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

# 預設目標類型種子（冪等）
DEFAULT_OBJECT_TYPES = [
    ("terminology",  "terminology.api（word-proof 等）"),
    ("rest_api",     "REST API"),
    ("flow",         "terminology flow"),
    ("step",         "terminology step"),
    ("value",        "value.id（值資產）"),
    ("tool",         "tool.registry.id"),
]

# object 表：目標
OBJECT_DDL = """
CREATE TABLE IF NOT EXISTS object (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    object        TEXT    NOT NULL,      -- 目標識別（例如 terminology.word_proof）
    object_type_id INTEGER NOT NULL,     -- object_type.id
    is_active     BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at    TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at    TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (object, object_type_id)
);
"""

# permit_type 表：許可類型字典
PERMIT_TYPE_DDL = """
CREATE TABLE IF NOT EXISTS permit_type (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    permit_type TEXT NOT NULL UNIQUE,    -- call / read / write / run / execute ...
    description TEXT,
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

# 預設許可類型種子（冪等）
DEFAULT_PERMIT_TYPES = [
    ("call",    "呼叫（例如 call terminology / REST API）"),
    ("read",    "讀"),
    ("write",   "寫"),
    ("run",     "執行（flow / run）"),
    ("order",   "落 order"),
    ("record",  "記錄（lineage）"),
]

# permit 表：授權記錄（2026-10-28 用戶要求）
#   permit = subject × permit × object
#   subject_id    = subject.id（邊個有權）
#   permit_type_id = permit_type.id（有咩許可）
#   object_id     = object.id（對邊個目標）
PERMIT_DDL = """
CREATE TABLE IF NOT EXISTS permit (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    subject_id     INTEGER NOT NULL,      -- subject.id
    permit_type_id INTEGER NOT NULL,      -- permit_type.id
    object_id      INTEGER NOT NULL,      -- object.id
    is_active      BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at     TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at     TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (subject_id, permit_type_id, object_id)
);
"""

# ============ import_registry（2026-10-28 用戶：worker 唔可以靠 import 逃工）============
# 目的：import 都係一個動作（action），要入表 + permit 管。
# 之前 `from .schema import *` 係 wildcard —— worker 可以唔經 permit
# 就拎晒所有 symbol。而家：全部 import 入呢張表，啟動時 check permit。
#
# import_registry：一行 = 一個 module 一次 import
#   module_id      = taxonomy.registry.id（邊個 module 做 import）
#   imported       = 被 import 嘅嘢（'.schema' / 'sqlite3' / '.api' ...）
#   symbols        = import 嘅 symbols（'*' = wildcard；'SqlStore' / 'Ast' ...')
#   is_wildcard    = 1 = from x import *（wildcard，要 permit 先准）
#   permit_object_type = object_type.id（import 屬邊類目標：module / rest_api / flow）
IMPORT_REGISTRY_DDL = """
CREATE TABLE IF NOT EXISTS import_registry (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    module_id          INTEGER NOT NULL,      -- taxonomy.registry.id（邊個 module）
    imported           TEXT    NOT NULL,      -- 被 import 嘅嘢（'.schema' / 'sqlite3'）
    symbols            TEXT    NOT NULL DEFAULT '*',  -- import 嘅 symbols
    is_wildcard        BOOLEAN NOT NULL DEFAULT 0 CHECK (is_wildcard IN (0,1)),
    is_active          BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at         TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (module_id, imported, symbols)
);
"""

# import_permit 表：邊個 module 有權 import 咩（2026-10-28 用戶：permit for all module）
#   module_id = taxonomy.registry.id（邊個 module；NULL = 任何 module 都准）
#   imported  = 被 import 嘅嘢（'.schema' = 自己 module 嘅 schema）
#   symbols   = 准 import 嘅 symbols（'*' = wildcard 都要記錄）
#   description = 描述
#   granted_by = 邊個批（'tool' / 'monitor' / 'admin_module' —— module 有自己
#              function/skill，需要 import 就申請，tool/monitor 管局）
# 冇呢張表嘅 record = 唔准 import（擋住 worker 逃工）
# 2026-10-28（用戶要求）：唔可以有「default」—— 全部按 need 申請。
# 每個 module 有自己 function/skill，需要 import 就登記申請（import_request），
# 由 tool（module 嘅工具中心）/ monitor（READ API 中心）批准先寫入呢張 permit。
IMPORT_PERMIT_DDL = """
CREATE TABLE IF NOT EXISTS import_permit (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    module_id          INTEGER,             -- taxonomy.registry.id（NULL = 任何 module）
    imported           TEXT    NOT NULL,    -- 被 import 嘅嘢
    symbols            TEXT    NOT NULL DEFAULT '*',  -- 准 import 嘅 symbols
    description        TEXT,
    granted_by         TEXT,                -- 邊個批（'tool' / 'monitor' / admin module）
    is_active          BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at         TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (module_id, imported, symbols)
);
"""

# import_request 表：module 嘅 import 申請（2026-10-28 用戶：按 need 申請，冇 default）
#   module_id      = taxonomy.registry.id（邊個 module 申請）
#   imported       = 想 import 嘅嘢（'.schema' / 'sqlite3' / 'source.api' ...）
#   symbols        = 想 import 嘅 symbols（'ALL' = 全部；'SqlStore' 單個）
#   reason         = 點解需要（module 自己講，link 返 skill/function）
#   status_id      = 1=pending（等批）2=approved（已批）3=rejected（已拒）
#   tool_id        = tool.registry.id（邊個工具需要呢個 import，可空）
# 一次申請 -> 批准 -> 寫 import_permit（正式授權記錄）
IMPORT_REQUEST_DDL = """
CREATE TABLE IF NOT EXISTS import_request (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    module_id          INTEGER NOT NULL,      -- taxonomy.registry.id（申請者）
    imported           TEXT    NOT NULL,      -- 想 import 嘅嘢
    symbols            TEXT    NOT NULL DEFAULT 'ALL',  -- 想 import 嘅 symbols
    reason             TEXT,                  -- 點解需要
    status_id          INTEGER NOT NULL DEFAULT 1,      -- 1=pending 2=approved 3=rejected
    tool_id            INTEGER,               -- tool.registry.id（需要嘅工具）
    decided_by         TEXT,                   -- 邊個決定（tool / monitor / admin）
    created_at         TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at         TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (module_id, imported, symbols)
);
"""

__all__ = ["SUBJECT_TYPE_DDL", "DEFAULT_SUBJECT_TYPES", "SUBJECT_DDL",
           "OBJECT_TYPE_DDL", "DEFAULT_OBJECT_TYPES", "OBJECT_DDL",
           "PERMIT_TYPE_DDL", "DEFAULT_PERMIT_TYPES", "PERMIT_DDL",
           "IMPORT_REGISTRY_DDL", "IMPORT_PERMIT_DDL", "IMPORT_REQUEST_DDL"]