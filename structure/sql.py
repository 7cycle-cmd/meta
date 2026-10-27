"""sql.py — structure.db 存取層（結構層：db_field_type + db_field_format + db_table_setting）"""

import os

import sqlite3

# 業務邏輯（function.py = 核心邏輯層；sql.py = 存取層）
from .function import (
    _migrate_type_to_db_field_type,
    _migrate_table_type_to_db_table_type,
)

DB_PATH = r"C:\projects\meta\structure\structure.db"
DEF_DB = r"C:\projects\meta\definition\definition.db"

# ================= 2026-10-25：由 definition 搬入（用戶要求） =================
# structure_type 嘅新家 = structure。definition 保留 required 關係表
# （file_required / db_*_required）by API 攞字典。
# 2026-10-26：file_type / structure_file 已移除 —— file 行直接用真檔名
# （structure_module.file_name），唔需要檔案類型字典。

# structure_type 表：實體類型字典（固定 id 1=package 2=file 3=db_table 4=db_field 5=db 6=root）
STRUCTURE_TYPE_DDL = """
CREATE TABLE IF NOT EXISTS structure_type (
    id          INTEGER PRIMARY KEY,       -- 固定 id（1=package 2=file 3=db_table 4=db_field 5=db 6=root）
    meta        TEXT    NOT NULL UNIQUE,   -- package / file / db_table / db_field / db / root
    description TEXT,
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

# 3 張分層地址表（root -> module -> skill）
# structure_root:        id | structure_type_id(root) | value
# structure_module:      id | structure_type_id | root_id | module_id | value
# structure_skill:       id | structure_type_id | structure_module_id | skill_id | value
# 身份欄：root_id = structure_root.id；module_id = taxonomy.taxonomy.id
# （tree = module；2026-10-26 用戶要求：taxonomy.package 表已移除）；
# skill_id = taxonomy.taxonomy.id。
# 每行 = 一層一個實體實例；父鍵鏈 = 路徑鏈；path_json 每段
# 直接存該層表 id（by_id，零 hardcode）。
STRUCTURE_ROOT_DDL = """
CREATE TABLE IF NOT EXISTS structure_root (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    structure_type_id INTEGER NOT NULL,   -- structure_type.id（root=6）
    value             TEXT    NOT NULL,   -- 根目錄（C:\\projects\\meta）
    location          TEXT,               -- 物理位置（root 自己 = value）
    is_active         BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at        TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at        TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (structure_type_id, value)
);
"""

STRUCTURE_MODULE_DDL = """
CREATE TABLE IF NOT EXISTS structure_module (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    structure_type_id INTEGER NOT NULL,   -- structure_type.id（package=1 / file=2 / db=5）
    root_id           INTEGER NOT NULL,   -- structure_root.id（父 + 身份）
    module_id         INTEGER NOT NULL,   -- taxonomy.taxonomy.id（module 身份，tree = module）
    value             TEXT    NOT NULL,   -- folder / db_file / folder
    location          TEXT,               -- 物理位置（root + folder + file/db）
    is_active         BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at        TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at        TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (structure_type_id, root_id, module_id, value)
);
"""

STRUCTURE_SKILL_DDL = """
CREATE TABLE IF NOT EXISTS structure_skill (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    structure_type_id   INTEGER NOT NULL,   -- structure_type.id（package=1）
    structure_module_id INTEGER NOT NULL,   -- structure_module.id（父，module 主行）
    skill_id            INTEGER NOT NULL,   -- taxonomy.taxonomy.id（skill 身份）
    value               TEXT    NOT NULL,   -- skill 名
    location            TEXT,               -- 物理位置（root + folder + skill + file）
    is_active           BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at          TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at          TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (structure_type_id, structure_module_id, skill_id, value)
);
"""

STRUCTURE_ADDRESS_DDL = (STRUCTURE_ROOT_DDL + STRUCTURE_MODULE_DDL
                         + STRUCTURE_SKILL_DDL)

# structure_file 表已移除（2026-10-26）—— file 層直接用真檔名：
#   structure_module (structure_type_id=file) 一行一個實體 .py 檔，
#   value = file_name（唔需要 file_type 字典；file_name 就係檔名）。
# 3 張分層地址表（root -> module -> skill）

# structure_type 種子（冪等）：實體類型字典
DEFAULT_STRUCTURE_TYPES = [
    (1, "package", "實體套件（module 資料夾 + db_file）"),
    (2, "file", "實體檔案（.py 檔）"),
    (3, "db_table", "實體表（db 入面嘅表）"),
    (4, "db_field", "實體欄位（db 入面嘅欄位）"),
    (5, "db", "實體資料庫（*.db 檔）"),
    (6, "root", "根目錄地址（path_json root 段嘅 value）"),
]

# structure_address 種子（冪等）：root -> 根目錄地址
# （2026-10-26 用戶要求：root value 入表，零 hardcode）
DEFAULT_STRUCTURE_ADDRESSES = [
    ("root", r"C:\projects\meta"),
]

# structure_taxonomy 表：樹層 ↔ 實體類型映射（2026-10-26 用戶要求）
# 每行 = taxonomy.tree.id（層）+ structure_type.id（該層對應嘅實體類型）
# 例：tree=module(2) -> structure_type=package(1)（module 係套件）
#     tree=module(2) -> structure_type=db(5)（module 要有 db 實體）
#     tree=skill(3)  -> structure_type=file(2)（skill 係檔案）
# 用途：path_definition / physical_path 嘅 path_json "type" 段由呢度
#       決定（零 hardcode —— 層要咩實體 = 表裏有冇 row）。
STRUCTURE_TAXONOMY_DDL = """
CREATE TABLE IF NOT EXISTS structure_taxonomy (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    tree_id           INTEGER NOT NULL,   -- taxonomy.tree.id（channel / module / skill）
    structure_type_id INTEGER NOT NULL,   -- structure_type.id（package / file / db_table / db_field / db）
    is_active         BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at        TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at        TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (tree_id, structure_type_id)
);
"""

# db_field_type 表：資料型別字典（2026-10-25 rebuild）
# id | meta | description NOT NULL | is_active | created_at
#   meta        = 型別名（INTEGER / TEXT / BOOLEAN / DATETIME / REAL /
#                 BLOB / JSON / SLUG / DATE / TIME / UUID）
#   description = 型別描述（人讀，NOT NULL）
#   default_value = 呢個型別有冇「預設值」概念（1=有 0=冇）——
#        有預設值 = 要喺 default_value 表查實際值（2026-10-26 用戶要求）
#   （db_field_unique_id 已移除 2026-10-25 —— unique 由 db_field_setting 引用表達；
#     db_field_setting_id 已移除 2026-10-25 —— 約束組合搬去 db_field_setting）
DB_FIELD_TYPE_DDL = """
CREATE TABLE IF NOT EXISTS db_field_type (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    meta            TEXT    NOT NULL UNIQUE,   -- 型別名：INTEGER / TEXT / ...
    description     TEXT    NOT NULL,          -- 型別描述（人讀）
    default_value   BOOLEAN NOT NULL DEFAULT 0 CHECK (default_value IN (0,1)),
                                                -- 有冇預設值概念（3/10/4/9/7 = 1）
    is_active       BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at      TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

# default_value 表：每個型別嘅實際預設值（2026-10-26 用戶要求）
# id | db_field_type_id | value
#    db_field_type_id = db_field_type.id（邊個型別）
#    value            = 該型別嘅預設值（例如 BOOLEAN->0 / DATETIME->NOW / JSON->[]）
# 一個型別一行；冇行 = 冇預設值（同 db_field_type.default_value=0 一致）。
DEFAULT_VALUE_DDL = """
CREATE TABLE IF NOT EXISTS default_value (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    db_field_type_id  INTEGER NOT NULL,          -- db_field_type.id（型別）
    value             TEXT    NOT NULL,          -- 預設值（0 / NOW / [] ...）
    is_active         BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at        TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at        TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (db_field_type_id)
);
"""

# db_field_unique 表：unique 欄位名字典（2026-10-25 用戶要求 rebuild）
# id | value
#   id    = AUTOINCREMENT PRIMARY KEY UNIQUE
#   value = 欄位名（id / meta_key / is_active / created_at / updated_at ...）TEXT NOT NULL
#   （2026-10-25 rebuild：meta_key/description 合併做 value）
DB_FIELD_UNIQUE_DDL = """
CREATE TABLE IF NOT EXISTS db_field_unique (
    id          INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE,
    value       TEXT    NOT NULL UNIQUE   -- 欄位名（id / meta_key / is_active ...）
);
"""

# ============ db_field_setting：欄位名 × 型別×性質（2026-10-26 用戶要求，由 programming 搬入）============
# 每個「欄位名 × 型別×性質」一行（正規化：一個欄位多個性質 = 多行）。
#    db_field_unique_id   = db_field_unique.id（欄位名：id / meta_key / ...）
#    db_field_property_id = db_field_property.id（型別 × 性質組合）
# 例（seed）：
#    id        -> INTEGER × primary_key + INTEGER × auto_increment
#    meta_key  -> TEXT × NOT NULL
#    is_active -> INTEGER × NOT NULL
#    created_at / updated_at -> DATETIME × NOW + DATETIME × localtime + DATETIME × NOT NULL
DB_FIELD_SETTING_DDL = """
CREATE TABLE IF NOT EXISTS db_field_setting (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    db_field_unique_id   INTEGER NOT NULL,  -- db_field_unique.id（欄位名）
    db_field_property_id INTEGER NOT NULL,  -- db_field_property.id（型別×性質）
    is_active            BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at           TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at           TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (db_field_unique_id, db_field_property_id)
);
"""

# db_field_setting 預設種子（2026-10-26 用戶指定）
# (db_field_unique_id, [db_field_property_id, ...])
# unique：1=id 3=meta_key 4=is_active 5=created_at 6=updated_at
# property（型別×性質）：見 db_field_property
DEFAULT_FIELD_SETTINGS = [
    (1, [7, 9]),     # id -> INTEGER×primary_key + INTEGER×auto_increment
    (3, [6]),        # meta_key -> TEXT×NOT NULL
    (4, [12]),       # is_active -> INTEGER×NOT NULL
    (5, [22, 23, 24]),  # created_at -> DATETIME×NOW + localtime + NOT NULL
    (6, [22, 23, 24]),  # updated_at -> DATETIME×NOW + localtime + NOT NULL
]

# db_field_property 表：欄位性質字典（2026-10-25 用戶要求重建）
# id | db_field_type_id | db_field_format_id
#   一行 = 一個「型別 × 性質 token」組合（例如 INTEGER×primary_key）
# structure_db_field.db_field_property_id 指住呢度
DB_FIELD_PROPERTY_DDL = """
CREATE TABLE IF NOT EXISTS db_field_property (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    db_field_type_id   INTEGER NOT NULL,  -- db_field_type.id（型別）
    db_field_format_id INTEGER NOT NULL,  -- db_field_format.id（性質 token）
    UNIQUE (db_field_type_id, db_field_format_id)
);
"""

# db_field_check 表：欄位規格檢查字典（2026-10-26 用戶 redesign）
# id | structure_db_table_id | structure_db_field_id | total | json
#   一行 = 一個「真表欄位」嘅完整值域
#   structure_db_table_id  = structure.db structure_db_table.id（邊張真表）
#   structure_db_field_id  = structure.db structure_db_field.id（邊個真欄位）
#   total                  = 值數量（len(json)）
#   json                   = 該欄位喺全站真 DB 出現過嘅全部真實值
#                             （例如 [1,2,3] / ["A","B","C","D"]）
#   大小寫規則：真實值有單一 case（全大寫或全小寫）= 有 limit -> 保持；
#              混雜大小寫 = 冇 limit -> 全部轉大寫。
DB_FIELD_CHECK_DDL = """
CREATE TABLE IF NOT EXISTS db_field_check (
    id                     INTEGER PRIMARY KEY AUTOINCREMENT,
    structure_db_table_id  INTEGER NOT NULL,  -- structure_db_table.id
    structure_db_field_id  INTEGER NOT NULL,  -- structure_db_field.id
    total                  INTEGER NOT NULL DEFAULT 0,  -- 值數量
    json                   TEXT,              -- 真實值清單（JSON 陣列）
    UNIQUE (structure_db_field_id)
);
"""

# value 表：DDL 生成規則（2026-10-25 用戶要求：formula 入表，唔係 code 寫死）
#   id      = 規則 id
#   type    = 規則類型（check = CHECK 約束模板）
#   formula = 模板字串，placeholder：
#       <db_field_unique_id>     欄位名（由 db_field_unique.id 反查 value）
#       <db_field_check.json_id> 允許值（由 db_field_check.id 反查 json）
#   例：CHECK (<db_field_unique_id> IN (<db_field_check.json_id>))
VALUE_DDL = """
CREATE TABLE IF NOT EXISTS value (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    type        TEXT    NOT NULL,           -- check（CHECK 約束）
    formula     TEXT    NOT NULL,           -- 模板（placeholder 執行時填）
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

DEFAULT_VALUES = [
    (1, "check",
     "CHECK (<db_field_unique_id> IN (<db_field_check.json_id>))"),
]

# 註：db_field_default 表已移除（2026-10-25）；db_field_default_id 欄亦已移除
#   （2026-10-25）——default/fallback 唔喺結構層。

# db_field_format 表：欄位格式字典（2026-10-25 rebuild：原子 token，唔再重複）
# format = 單一原子 token（唔可以組合）：
#   primary_key / unique / auto_increment / NOW / localtime / NOT NULL
#   （2026-10-25 rebuild：NULL token 已移除——唔需要嘅欄位就唔掛 property）
DB_FIELD_FORMAT_DDL = """
CREATE TABLE IF NOT EXISTS db_field_format (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    format      TEXT    NOT NULL UNIQUE,   -- 原子格式 token（primary_key / unique / ...）
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

# db_field_type 預設種子（冪等）：基礎型別（2026-10-25 用戶要求）
# 基本 4 類型 + REAL/BLOB/JSON/SLUG + 標準型別（DATE/TIME/UUID）。
# CHINESE/PYTHON/SQL 唔係型別（2026-10-25 用戶確認：內容檢查係其他
# function 嘅任務，用 db_field_check 表達，唔係資料型別）
# 2026-10-26：第三項 = default_value（呢個型別有冇預設值概念）
#   3(BOOLEAN)/10(TIME)/4(DATETIME)/9(DATE)/7(JSON) = 1，其餘 = 0
DEFAULT_FIELD_TYPES = [
    ("INTEGER",  "整數（Boolean 0/1 都係呢度）", 0),
    ("TEXT",     "文字/字串（JSON、日期都係存呢度）", 0),
    ("BOOLEAN",  "真假（實際存做 0/1 INTEGER）", 1),
    ("DATETIME", "日期+時間（YYYY-MM-DD HH:MM:SS，實際存做 TEXT）", 1),
    ("REAL",     "浮點數（小數，例如 3.14）", 0),
    ("BLOB",     "原始二進制 bytes（圖片/檔案）", 0),
    ("JSON",     "JSON 字串（實際存做 TEXT）", 1),
    ("SLUG",     "英數代碼（只限 a-z A-Z 0-9，冇符號冇空格）", 0),
    ("DATE",     "日期（YYYY-MM-DD，實際存做 TEXT）", 1),
    ("TIME",     "時間（HH:MM:SS，實際存做 TEXT）", 1),
    ("UUID",     "UUID（36 字符，實際存做 TEXT）", 0),
]

# default_value 預設種子（2026-10-26 用戶指定）：
#   db_field_type_id -> 實際預設值
#   3(BOOLEAN)  -> 0
#   10(TIME)    -> NOW
#   4(DATETIME) -> NOW
#   9(DATE)     -> NOW
#   7(JSON)     -> []
DEFAULT_TYPE_VALUES = [
    (3, "0"),
    (10, "NOW"),
    (4, "NOW"),
    (9, "NOW"),
    (7, "[]"),
]

# db_field_unique 預設種子：通用欄位名（id / meta_key / is_active / created_at / updated_at）
# （2026-10-25 rebuild：value 取代 meta_key+description）
DEFAULT_FIELD_UNIQUES = [
    "id",
    "meta_key",
    "is_active",
    "created_at",
    "updated_at",
]

# db_field_format 預設種子：性質 token 字典（2026-10-25 rebuild：原子 token）
#   primary_key / unique / auto_increment / NOW / localtime / NOT NULL
#   （2026-10-25 rebuild：NULL token 已移除）
DEFAULT_FIELD_FORMATS = [
    (1, "primary_key",   "主鍵（複合或非自增）"),
    (2, "unique",        "唯一欄位（meta/code）"),
    (3, "auto_increment", "自增欄"),
    (4, "NOW",           "建立時間（存 datetime('now')）"),
    (5, "localtime",     "本地時間（存 datetime('now','localtime')）"),
    (7, "NOT NULL",      "非空欄位"),
]

# structure_db_table 表：真表結構定義（一行 = 一張真表，全站掃描）
# （2026-10-25 rename：db_table_stucture -> structure_db_table，正確拼寫）
# （2026-10-26 redesign：by_id —— channel_id + module_id 取代 db_file 字串）
#   channel_id = taxonomy.tree.id（1 = channel）
#   module_id  = taxonomy.taxonomy.id（tree = module，權威 module 清單）
#   table_name = 真表名（question / run / registry ...）
#   description = 表用途（唔可以 NULL）
# 全站掃描（sync_db_tables）：每個 module 資料夾嘅 *module*.db 真表，
# 逐張入表（包含 _guard / sqlite_* 以外全部表）。
DB_TABLE_STRUCTURE_DDL = """
CREATE TABLE IF NOT EXISTS structure_db_table (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id  INTEGER NOT NULL,          -- taxonomy.tree.id（1 = channel）
    module_id   INTEGER NOT NULL,          -- taxonomy.taxonomy.id（tree = module）
    table_name  TEXT    NOT NULL,          -- 真表名（question / run / registry ...）
    description TEXT    NOT NULL DEFAULT '', -- 表用途（唔可以 NULL，2026-10-26）
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (channel_id, module_id, table_name)
);
"""

# structure_db_field 表：一張真表嘅欄位結構（一行 = 一個欄位）
# （2026-10-25 rename：db_field_stucture -> structure_db_field，正確拼寫）
# （2026-10-26 redesign：by_id —— 淨結構描述，型別字典唔再引用）
#   structure_db_table_id = structure_db_table.id（邊張真表）
#   field_name            = 真欄位名（id / question_id / updated_at ...）
#   db_field_unique_id    = db_field_unique.id（欄位名字典，2026-10-26 用戶要求）
#   db_field_check_id     = db_field_check.id（值域 check，2026-10-27 用戶要求）
#   description           = 欄位用途（唔可以 NULL）
# 型別/性質由 resource.db db_field 實例管（呢度淨係結構字典）。
TABLE_COLUMN_DDL = """
CREATE TABLE IF NOT EXISTS structure_db_field (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    structure_db_table_id INTEGER NOT NULL, -- structure_db_table.id（邊張表）
    field_name           TEXT    NOT NULL,  -- 真欄位名（id / question_id ...）
    db_field_unique_id   INTEGER,            -- db_field_unique.id（欄位名字典）
    db_field_check_id    INTEGER,            -- db_field_check.id（值域 check，2026-10-27）
    description          TEXT    NOT NULL DEFAULT '', -- 欄位用途（唔可以 NULL）
    is_active            BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at           TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at           TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (structure_db_table_id, field_name)
);
"""

# 2026-10-25：新名
DB_FIELD_DDL = TABLE_COLUMN_DDL

# db_field_position 已移除（2026-10-25：欄位次序由 db_field_stucture.position_id
# 表達；db_field_setting 唔需要額外 registry）

# db_table_setting 表：通用欄位模板（一行 = 一個欄位）
# meta_key            = 欄位名（例如 id / meta / created_at / updated_at / is_active）
# db_field_type_id    = db_field_type.id（型別）
# seq_id              = common.seq.id（欄位次序，DDL 內嘅先後；2026-10-27 position -> seq）
# 性質 = db_field_property（直掛 db_table_setting.id）
#
# 2026-10-23：db_table_type 概念移除——「表類型」唔存在，表名就係表。
# 2026-10-23c：table_name 都移除——db_table_setting 係「通用模板」。
DB_TABLE_SETTING_DDL = """
CREATE TABLE IF NOT EXISTS db_table_setting (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    meta_key            TEXT    NOT NULL UNIQUE,  -- 欄位名（id / meta / created_at...）
    db_field_type_id    INTEGER NOT NULL,          -- db_field_type.id（型別）
    seq_id              INTEGER,                   -- common.seq.id（欄位次序）
    is_active           BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at          TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at          TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

# position 表：位置字典（package 內第幾張表 / 欄位第幾個位）
# 2026-10-23：由 table_position 改名（通用化，table / db_field 都用得）
POSITION_DDL = """
CREATE TABLE IF NOT EXISTS position (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    meta        TEXT    NOT NULL UNIQUE,
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

# package_setting 表：package × 表（一個 package 包含邊啲真表）
# 2026-10-23：package_setting / package_type 已移除（由 taxonomy.package 管）
PACKAGE_SETTING_DDL = ""
PACKAGE_TYPE_DDL = ""


# 公式裝飾器（2026-10-27：table-driven —— 內容由 template.decorator 表話事，
# ast 掃到 @formula_def 就查表建 formula + 回填出處；呢度只係掛鉤）
from template.decorators import formula_def  # noqa: E402


@formula_def("prove_structure_field_exists")
def _prove_structure_field_source():
    """證明 structure_db_field 有 package_id/file_id 出處（Proof flow 用）"""
    return None


class SqlStore:
    def __init__(self, db_path=DB_PATH):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        # 2026-10-27（用戶要求）：allowed_symbol / registry
        # 兩張本地表移除 —— 存在就 drop（資料由其他 module 管）。
        for _tbl in ("allowed_symbol", "registry"):
            _has = self.conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table'"
                " AND name=?", (_tbl,)).fetchone()
            if _has:
                self.conn.execute(f"DROP TABLE {_tbl}")
                self.conn.commit()
                print(f"[structure] {_tbl} 表移除（2026-10-27 用戶要求）")
        # ATTACH definition.db（table_definition 擁有者）
        self.conn.execute(f"ATTACH DATABASE ? AS defdb", (DEF_DB,))
        # ATTACH common.db（position 字典中央化咗，2026-10-23）
        self.conn.execute(
            f"ATTACH DATABASE ? AS cmmdb", (r"C:\projects\meta\common\common.db",))
        # 自動遷移：type -> column_type -> db_field_type（舊名升級）
        _migrate_type_to_db_field_type(self.conn)
        # 自動遷移：table_type -> db_table_type（舊名升級）
        _migrate_table_type_to_db_table_type(self.conn)
        # 2026-10-25：structure_type 由 definition 搬入（file_type /
        #   structure_file 2026-10-26 已移除 —— file 層直接存真檔名）
        self.conn.execute(STRUCTURE_TYPE_DDL)
        # 3 張分層地址表（root -> module -> skill）
        self.conn.executescript(STRUCTURE_ADDRESS_DDL)
        has_old = self.conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table'"
            " AND name='structure_address'").fetchone()
        if has_old:
            self.conn.execute("DROP TABLE structure_address")
            self.conn.commit()
        # 2026-10-26：舊 structure_file 表（已移除）存在就 drop，資料由
        # structure_module（file 層）重建；file_type 表同樣 drop。
        for _tbl in ("file_type", "structure_file"):
            _has = self.conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table'"
                " AND name=?", (_tbl,)).fetchone()
            if _has:
                self.conn.execute(f"DROP TABLE {_tbl}")
                self.conn.commit()
                print(f"[structure] {_tbl} 表移除（file 層用真檔名替代）")
        self._migrate_from_definition()
        # 3 張分層表加 location 欄 + 推導物理位置（2026-10-26 用戶要求）
        self._migrate_location()
        # structure_taxonomy（2026-10-26：樹層 ↔ 實體類型映射，path 定義用）
        self.conn.execute(STRUCTURE_TAXONOMY_DDL)
        self._seed_structure_taxonomy()
        # db_field_type（新版：id|meta|unique_id|is_active|created_at）
        self.conn.execute(DB_FIELD_TYPE_DDL)
        self._migrate_db_field_type_old()
        # default_value 表（2026-10-26：型別 -> 實際預設值）
        self.conn.execute(DEFAULT_VALUE_DDL)
        # db_field_unique（2026-10-25 rebuild：id+value）
        self.conn.execute(DB_FIELD_UNIQUE_DDL)
        self._migrate_db_field_unique_drop_flag()
        self._sync_db_field_uniques()
        # db_field_setting（2026-10-26 用戶要求：由 programming 搬入）
        self.conn.execute(DB_FIELD_SETTING_DDL)
        self._sync_db_field_settings()
        # db_field_format（rename 自 db_field_setting，2026-10-25 rebuild 原子 token）
        self.conn.execute(DB_FIELD_FORMAT_DDL)
        self._migrate_db_field_format()
        self._sync_db_field_formats()  # 補 missing format value
        # db_field_default（已移除 2026-10-25——fallback 字典 = common.boolean；
        #   舊表存在就 drop）
        self._migrate_db_field_default_drop()
        # db_field_property（2026-10-25 rebuild：id | db_field_type_id | db_field_format_id）
        self.conn.execute(DB_FIELD_PROPERTY_DDL)
        self._migrate_db_field_property_refs()
        # 型別直接存欄位表（db_field_type_id）——migration 由 setting 引用轉換
        self._migrate_db_field_type_direct()
        # db_field_setting 已移除（2026-10-25）——drop 舊表
        self._migrate_db_field_setting_drop()
        # db_field_check（2026-10-26 redesign：structure_db_table_id +
        # structure_db_field_id + total + json）
        self.conn.execute(DB_FIELD_CHECK_DDL)
        self._migrate_db_field_check_refs()
        # 由真資料 sync（差集補缺 + 校正，唔 DELETE 全部 = 唔燒 sqlite_sequence；
        # 全站掃描好慢 -> 每 process 只跑一次）
        if not getattr(SqlStore, "_checks_synced", False):
            self._sync_db_field_checks()
            SqlStore._checks_synced = True
        # value 表（DDL 生成規則；2026-10-25 用戶要求 formula 入表）
        self.conn.execute(VALUE_DDL)
        self._sync_values()
        # 確保 position 字典喺 common.db（中央字典）
        self._sync_positions()
        # db_table_setting 表（表 × 欄位定義；型別直接存）
        self.conn.execute(DB_TABLE_SETTING_DDL)
        self._migrate_position_to_seq()
        self._migrate_db_table_setting()
        self._sync_db_table_settings()
        # db_table_stucture -> structure_db_table（rename）
        self.conn.execute(DB_TABLE_STRUCTURE_DDL)
        self._migrate_db_table_stucture()
        self.conn.execute(TABLE_COLUMN_DDL)
        self._migrate_db_field_stucture()
        # 新表名遷移（db_field_stucture -> structure_db_field 等）
        self._migrate_new_names()
        # 2026-10-26 redesign：by_id（channel_id + module_id + table_name）
        self._migrate_db_table_structure_v2()
        self._migrate_db_field_structure_v2()
        # 2026-10-27：structure_db_field + db_field_check_id（值域 check link）
        self._migrate_db_field_check_link()
        # 性質行同步（按欄位名 seed；冪等）
        self._sync_db_field_properties()
        # db_field_position 已移除（2026-10-25）——舊表 drop
        self._migrate_db_field_position_drop()
        self.conn.commit()
        self._sync_db_field_types()
        # 全站真表掃描（2026-10-26 用戶要求：全部真實資料入表）
        # 每次開 SqlStore 都掃好慢 —— 每 process 只掃一次（module-level flag）
        try:
            if not getattr(SqlStore, "_scanned_all", False):
                self.sync_db_tables()
                SqlStore._scanned_all = True
        except Exception as exc:
            print(f"[structure] sync_db_tables 失敗: {exc}")

    def _migrate_db_field_format_refs(self):
        """遷移（幂等）：db_field_setting_id 欄 -> db_field_format_id（2026-10-25 rebuild）

        兩張引用表（db_field_stucture / db_table_setting）
        欄名 rename，等佢哋明確指 db_field_format。
        """
        for tbl in ("db_field_stucture", "db_table_setting"):
            cols = [c[1] for c in self.conn.execute(
                "PRAGMA table_info(%s)" % tbl)]
            if "db_field_setting_id" not in cols:
                continue
            if "db_field_format_id" in cols:
                continue
            self.conn.execute(
                "ALTER TABLE %s RENAME COLUMN"
                " db_field_setting_id TO db_field_format_id" % tbl)
            self.conn.commit()
            print(f"[structure] {tbl}.db_field_setting_id"
                  f" -> db_field_format_id")

    def _migrate_db_field_position_drop(self):
        """遷移（幂等）：db_field_position 表移除（2026-10-25）

        欄位次序已由 db_field_stucture.position_id 表達；
        db_field_position 係重複 registry —— drop。
        """
        has = self.conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table'"
            " AND name='db_field_position'").fetchone()
        if has:
            self.conn.execute("DROP TABLE db_field_position")
            self.conn.commit()
            print("[structure] db_field_position drop（次序已由"
                  " db_field_stucture.position_id 表達）")

    def _migrate_db_field_setting_drop(self):
        """遷移（幂等）：舊 db_field_setting 表移除（2026-10-25 / 2026-10-26）

        2026-10-25：型別直接存 db_field_stucture.db_field_type_id /
        db_table_setting.db_field_type_id；性質直接掛欄位（db_field_property）。
        舊 db_field_setting 存在 -> drop（冇中層）。
        2026-10-26（用戶要求）：新 db_field_setting 表（欄位名 × 型別×性質
        字典，db_field_unique_id + db_field_property_id）—— 有
        db_field_unique_id 欄 = 新版，**唔可以 drop**。
        """
        for tbl in ("db_field_setting",):
            has = self.conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name = ?",
                (tbl,)).fetchone()
            if not has:
                continue
            cols = [c[1] for c in self.conn.execute(
                "PRAGMA table_info('db_field_setting')")]
            if "db_field_unique_id" in cols:
                continue  # 新版（2026-10-26）——唔郁
            self.conn.execute(f"DROP TABLE {tbl}")
            self.conn.commit()
            print(f"[structure] {tbl} drop（舊版冇中層；新版由 DB_FIELD_SETTING_DDL 重建）")

    def _migrate_db_field_type_direct(self):
        """遷移（幂等）：db_field_stucture / db_table_setting 型別直接化（2026-10-25）

        db_field_format_id（指 db_field_setting）-> db_field_type_id（直接型別）：
            舊值 = db_field_setting.id（1-6）-> 由 db_field_setting 反查 type_id。
        db_field_property / db_field_check 嘅 db_field_setting_id -> 改指欄位 id：
            mapping：setting id 1-6 -> 對應 db_field_stucture.id
            （同 column_name：id/description/is_active/... 對應設定）。
        """
        # 1. db_field_stucture：db_field_format_id -> db_field_type_id
        cols = [c[1] for c in self.conn.execute(
            "PRAGMA table_info('db_field_stucture')")]
        if "db_field_format_id" in cols:
            # 睇 db_field_setting 表存唔存在（轉換用）
            has_setting = self.conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table'"
                " AND name='db_field_setting'").fetchone()
            # 建 type_id 欄
            if "db_field_type_id" not in cols:
                self.conn.execute(
                    "ALTER TABLE db_field_stucture"
                    " ADD COLUMN db_field_type_id INTEGER")
                self.conn.commit()
            # 由 setting id -> type_id 轉換
            rows = self.conn.execute(
                "SELECT id, db_field_format_id FROM db_field_stucture"
                " WHERE db_field_type_id IS NULL").fetchall()
            for r in rows:
                tid = None
                if has_setting:
                    sr = self.conn.execute(
                        "SELECT db_field_type_id FROM db_field_setting"
                        " WHERE id = ?", (r["db_field_format_id"],)).fetchone()
                    tid = sr["db_field_type_id"] if sr else None
                if tid is None:
                    # fallback：由 column_name 對應型別（code 權威）
                    tid = self._column_name_type_id(r["db_field_format_id"])
                if tid:
                    self.conn.execute(
                        "UPDATE db_field_stucture SET db_field_type_id = ?"
                        " WHERE id = ?", (tid, r["id"]))
            # drop 舊欄
            self.conn.execute(
                "ALTER TABLE db_field_stucture DROP COLUMN db_field_format_id")
            self.conn.commit()
            print("[structure] db_field_stucture.db_field_format_id"
                  " -> db_field_type_id")
        # 2. db_table_setting：db_field_format_id -> db_field_type_id
        cols = [c[1] for c in self.conn.execute(
            "PRAGMA table_info('db_table_setting')")]
        if "db_field_format_id" in cols:
            has_setting = self.conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table'"
                " AND name='db_field_setting'").fetchone()
            if "db_field_type_id" not in cols:
                self.conn.execute(
                    "ALTER TABLE db_table_setting"
                    " ADD COLUMN db_field_type_id INTEGER")
                self.conn.commit()
            rows = self.conn.execute(
                "SELECT id, db_field_format_id FROM db_table_setting"
                " WHERE db_field_type_id IS NULL").fetchall()
            for r in rows:
                tid = None
                if has_setting:
                    sr = self.conn.execute(
                        "SELECT db_field_type_id FROM db_field_setting"
                        " WHERE id = ?", (r["db_field_format_id"],)).fetchone()
                    tid = sr["db_field_type_id"] if sr else None
                if tid is None:
                    tid = self._column_name_type_id(r["db_field_format_id"])
                if tid:
                    self.conn.execute(
                        "UPDATE db_table_setting SET db_field_type_id = ?"
                        " WHERE id = ?", (tid, r["id"]))
            self.conn.execute(
                "ALTER TABLE db_table_setting DROP COLUMN db_field_format_id")
            self.conn.commit()
            print("[structure] db_table_setting.db_field_format_id"
                  " -> db_field_type_id")

    def _column_name_type_id(self, setting_id):
        """（helper）由 db_field_setting id / column_name 反查型別 id

        db_field_setting 已 drop 時嘅 fallback：固定對應
            id=1 -> INTEGER / id=2,3 -> TEXT / id=4 -> BOOLEAN /
            id=5,6 -> DATETIME
        """
        type_by_setting = {1: "INTEGER", 2: "TEXT", 3: "TEXT",
                           4: "BOOLEAN", 5: "DATETIME", 6: "DATETIME"}
        meta = type_by_setting.get(setting_id)
        if not meta:
            return None
        r = self.conn.execute(
            "SELECT id FROM db_field_type WHERE meta = ?", (meta,)).fetchone()
        return r["id"] if r else None

    def _migrate_new_names(self):
        """遷移（幂等）：db_field_stucture -> structure_db_field；db_table_stucture -> structure_db_table

        2026-10-25（用戶要求）：正確拼寫 rename。同時處理
        db_field_property.db_field_stucture_id -> db_field_type_id 掛法。
        """
        # 1. db_field_stucture -> structure_db_field
        has_old_f = self.conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table'"
            " AND name='db_field_stucture'").fetchone()
        if has_old_f:
            has_new_f = self.conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table'"
                " AND name='structure_db_field'").fetchone()
            if has_new_f:
                n = self.conn.execute(
                    "SELECT COUNT(*) c FROM structure_db_field").fetchone()["c"]
                if n == 0:
                    # 新表係 DDL 建嘅空表 -> drop 再 rename（保留舊資料）
                    self.conn.execute("DROP TABLE structure_db_field")
                else:
                    # 新表有資料（先前已 rename）-> 唔郁
                    pass
            self.conn.execute(
                "ALTER TABLE db_field_stucture RENAME TO structure_db_field")
            self.conn.commit()
            print("[structure] db_field_stucture -> structure_db_field（rename）")
        else:
            # 冇舊表 -> 確保新表存在（可能已 rename 過 / 直接建）
            self.conn.execute(TABLE_COLUMN_DDL)
        # 2. db_table_stucture -> structure_db_table
        has_old_t = self.conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table'"
            " AND name='db_table_stucture'").fetchone()
        if has_old_t:
            has_new_t = self.conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table'"
                " AND name='structure_db_table'").fetchone()
            if has_new_t:
                n = self.conn.execute(
                    "SELECT COUNT(*) c FROM structure_db_table").fetchone()["c"]
                if n == 0:
                    self.conn.execute("DROP TABLE structure_db_table")
                else:
                    pass
            self.conn.execute(
                "ALTER TABLE db_table_stucture RENAME TO structure_db_table")
            self.conn.commit()
            print("[structure] db_table_stucture -> structure_db_table（rename）")
        else:
            self.conn.execute(DB_TABLE_STRUCTURE_DDL)
        # 3. structure_db_field 加 db_field_property_id / db_field_check_id（若缺）
        cols = [c[1] for c in self.conn.execute(
            "PRAGMA table_info('structure_db_field')")]
        # 2026-10-26 redesign：新版冇 column_name -> 唔再加舊欄（淨結構）
        if "column_name" in cols:
            for col, ddl in (("db_field_property_id", "INTEGER"),
                             ("db_field_check_id", "INTEGER")):
                if col not in cols:
                    self.conn.execute(
                        f"ALTER TABLE structure_db_field ADD COLUMN {col} {ddl}")
                    self.conn.commit()
                    print(f"[structure] structure_db_field + {col} 欄")
            # 4. 回填 db_field_property_id（按 column_name 權威性質）
            self._backfill_property_ids()
        # 5. structure_db_field 加 db_field_unique_id（2026-10-26 用戶要求）
        if "db_field_unique_id" not in cols:
            self.conn.execute(
                "ALTER TABLE structure_db_field ADD COLUMN db_field_unique_id INTEGER")
            self.conn.commit()
            print("[structure] structure_db_field + db_field_unique_id 欄")
        # 6. 回填 db_field_unique_id（由 field_name 反查 db_field_unique.id，
        #    value 欄 = 欄位名；搵唔到 -> NULL 留空，唔假造）
        self._backfill_db_field_unique_ids()

    def _backfill_db_field_unique_ids(self):
        """按 field_name 回填 structure_db_field.db_field_unique_id（幂等）

        欄位名 -> db_field_unique.value -> db_field_unique.id。
        只更新 match 到嘅；搵唔到留 NULL（唔可以假造）。
        """
        uniq = {r["value"]: r["id"] for r in self.conn.execute(
            "SELECT id, value FROM db_field_unique")}
        rows = self.conn.execute(
            "SELECT id, field_name FROM structure_db_field"
            " WHERE db_field_unique_id IS NULL").fetchall()
        n = 0
        for r in rows:
            uid = uniq.get(r["field_name"])
            if not uid:
                continue
            self.conn.execute(
                "UPDATE structure_db_field SET db_field_unique_id = ?"
                " WHERE id = ?", (uid, r["id"]))
            n += 1
        if n:
            self.conn.commit()
            print(f"[structure] db_field_unique_id 回填：{n} 行")

    def _backfill_property_ids(self):
        """按 column_name 回填 structure_db_field.db_field_property_id（幂等）

        權威 mapping（2026-10-25）：
            1 = INTEGER × pk （id）
            2 = INTEGER × unique
            3 = INTEGER × auto_increment
            4 = INTEGER × NOT NULL
            5 = TEXT × NOT NULL（description）
            6 = BOOLEAN × NOT NULL（is_active）
            7 = DATETIME × NOT NULL（created_at/updated_at）
        """
        # property 字典（type × format）
        def _pid(tmeta, fmt):
            r = self.conn.execute(
                "SELECT pr.id FROM db_field_property pr"
                " JOIN db_field_type ft ON ft.id = pr.db_field_type_id"
                " JOIN db_field_format ff ON ff.id = pr.db_field_format_id"
                " WHERE ft.meta = ? AND ff.format = ?",
                (tmeta, fmt)).fetchone()
            return r["id"] if r else None

        _PK = _pid("INTEGER", "primary_key")
        _UK = _pid("INTEGER", "unique")
        _AI = _pid("INTEGER", "auto_increment")
        _IN = _pid("INTEGER", "NOT NULL")
        _TN = _pid("TEXT", "NOT NULL")
        _BN = _pid("BOOLEAN", "NOT NULL")
        _DN = _pid("DATETIME", "NOT NULL")
        _DNow = _pid("DATETIME", "NOW")
        _DLocal = _pid("DATETIME", "localtime")
        # 欄位名 -> 預設 property_id（冇 -> None）
        id_map = {
            "id": _PK,
            "meta_key": _UK,
            "seq": _IN,
            "description": _TN,
            "is_active": _BN,
            "created_at": _DNow,
            "updated_at": _DLocal,
        }
        rows = self.conn.execute(
            "SELECT id, column_name, db_field_type_id"
            " FROM structure_db_field").fetchall()
        for r in rows:
            pid = id_map.get(r["column_name"])
            if pid is None:
                continue
            self.conn.execute(
                "UPDATE structure_db_field SET db_field_property_id = ?"
                " WHERE id = ?"
                " AND (db_field_property_id IS NULL OR db_field_property_id != ?)",
                (pid, r["id"], pid))
            # check_id：property 有對應 check 就回填
            ck = self.conn.execute(
                "SELECT id FROM db_field_check WHERE db_field_property_id = ?",
                (pid,)).fetchone()
            if ck:
                self.conn.execute(
                    "UPDATE structure_db_field SET db_field_check_id = ?"
                    " WHERE id = ?"
                    " AND (db_field_check_id IS NULL OR db_field_check_id != ?)",
                    (ck["id"], r["id"], ck["id"]))
        self.conn.commit()

    def _migrate_db_field_property_refs(self):
        """遷移（幂等）：db_field_property 重建（2026-10-25 rebuild 2）

        新格式：id | db_field_type_id | db_field_format_id（字典，型別 × 性質）。
        舊格式（db_field_stucture_id / db_field_setting_id 掛欄位）-> drop 重建。
        性質組合係 seed 可重建（_sync_db_field_properties）。
        """
        cols = [c[1] for c in self.conn.execute(
            "PRAGMA table_info('db_field_property')")]
        want = {"id", "db_field_type_id", "db_field_format_id"}
        if not (want <= set(cols)):
            self.conn.execute("DROP TABLE db_field_property")
            self.conn.execute(DB_FIELD_PROPERTY_DDL)
            self.conn.commit()
            print("[structure] db_field_property 重建"
                  "（db_field_type_id + db_field_format_id）")
        self._sync_db_field_properties()

    def _sync_db_field_properties(self):
        """確保 db_field_property 有齊權威型別×性質組合（冪等）

        2026-10-25 rebuild 2：db_field_property = 字典
        （id | db_field_type_id | db_field_format_id），唔再掛欄位。
        全部型別 × 全部 format token 組合 seed；刪唔喺權威嘅行。
        """
        n = 0
        # 收斂：刪唔喺權威組合嘅行（全部型別 × token）
        types = [r["id"] for r in self.conn.execute(
            "SELECT id FROM db_field_type WHERE is_active = 1")]
        fmts = [r["id"] for r in self.conn.execute(
            "SELECT id FROM db_field_format WHERE is_active = 1")]
        for tid in types:
            for fid in fmts:
                cur = self.conn.execute(
                    "INSERT INTO db_field_property"
                    " (db_field_type_id, db_field_format_id)"
                    " SELECT ?, ? WHERE NOT EXISTS"
                    " (SELECT 1 FROM db_field_property"
                    "  WHERE db_field_type_id = ? AND db_field_format_id = ?)",
                    (tid, fid, tid, fid))
                n += cur.rowcount
        # 刪唔喺權威（type × format 組合以外）
        self.conn.execute(
            "DELETE FROM db_field_property WHERE db_field_type_id IS NULL"
            " OR db_field_format_id IS NULL")
        self.conn.commit()
        return n

    def _migrate_db_field_check_refs(self):
        """遷移（幂等）：db_field_check 重建（2026-10-26 用戶 redesign）

        新格式：id | structure_db_table_id | structure_db_field_id | total | json。
        舊格式（db_field_unique_id / db_field_property_id）-> drop 重建（資料由
        _sync_db_field_checks 由真資料重建，冇損失）。
        """
        try:
            cols = [c[1] for c in self.conn.execute(
                "PRAGMA table_info('db_field_check')")]
        except Exception:
            cols = []
        want = {"id", "structure_db_table_id", "structure_db_field_id",
                "total", "json"}
        if not (want <= set(cols)):
            self.conn.execute("DROP TABLE IF EXISTS db_field_check")
            self.conn.execute(DB_FIELD_CHECK_DDL)
            self.conn.commit()
            print("[structure] db_field_check 重建"
                  "（structure_db_table_id + structure_db_field_id + total + json）")

    def _sync_db_field_checks(self):
        """確保 db_field_check 有齊檢查（冪等，零 hardcode）

        2026-10-26 redesign：db_field_check = id | structure_db_table_id |
        structure_db_field_id | total | json。
        json = 該欄位喺全站真 DB 實際出現過嘅全部值：
            SELECT DISTINCT <欄位> FROM <真表> WHERE <欄位> IS NOT NULL
        total = len(json)。
        大小寫規則（用戶指定）：真實值有單一 case（全大寫或全小寫）= 有
        limit -> 保持；混雜大小寫 = 冇 limit -> 全部轉大寫。
        每行 = 一個真表欄位（UNIQUE structure_db_field_id）。
        """
        import json as _json
        n = 0
        # 一次過掃全站真 DB，攞每個「表.欄位」嘅實際值
        real_map = self._real_field_values_map()
        # 逐個真表欄位（structure_db_field）
        rows = self.conn.execute(
            "SELECT id, structure_db_table_id, field_name"
            " FROM structure_db_field WHERE is_active = 1"
            " ORDER BY id").fetchall()
        for r in rows:
            fname = r["field_name"]
            real_values = real_map.get(fname) or []
            if not real_values:
                continue  # 全站冇資料 -> 唔造 check
            vals = self._normalize_case(real_values)
            j = _json.dumps(vals)
            total = len(vals)
            cur = self.conn.execute(
                "INSERT INTO db_field_check"
                " (structure_db_table_id, structure_db_field_id, total, json)"
                " SELECT ?, ?, ?, ? WHERE NOT EXISTS"
                " (SELECT 1 FROM db_field_check"
                "  WHERE structure_db_field_id = ?)",
                (r["structure_db_table_id"], r["id"], total, j, r["id"]))
            if cur.rowcount:
                n += 1
            else:
                # 已存在 -> 校正（真實值域可能變咗；用 changes diff 計）
                before = self.conn.total_changes
                self.conn.execute(
                    "UPDATE db_field_check SET total = ?, json = ?"
                    " WHERE structure_db_field_id = ?"
                    "  AND (total != ? OR json != ?)",
                    (total, j, r["id"], total, j))
                if self.conn.total_changes > before:
                    n += 1
        # 清走已停用欄位嘅 check（舊殘留）
        cur = self.conn.execute(
            "DELETE FROM db_field_check WHERE structure_db_field_id NOT IN"
            " (SELECT id FROM structure_db_field WHERE is_active = 1)")
        n += cur.rowcount
        self.conn.commit()
        return n

    def _normalize_case(self, values):
        """大小寫規則（用戶 2026-10-26）

        有單一 case（全大寫或全小寫）= 有 limit -> 保持原樣；
        混雜大小寫 = 冇 limit -> 全部轉大寫。
        """
        strs = [v for v in values if isinstance(v, str)]
        others = [v for v in values if not isinstance(v, str)]
        if not strs:
            return values  # 全數字 -> 唔使郁
        has_lower = any(c.islower() for s in strs for c in s)
        has_upper = any(c.isupper() for s in strs for c in s)
        if has_lower and has_upper:
            # 混雜 -> 全部大寫
            strs = [s.upper() for s in strs]
        # 保持排序（數字先、文字後）
        return others + sorted(set(strs))

    def _real_field_values_map(self):
        """一次過掃全站真 DB，攞所有欄位實際出現過嘅 DISTINCT 值

        返回 {field_name: [values...]}（數字先、文字後，全部真實）。
        來源：每個 module 資料夾嘅 *.db 真表（skip sqlite_% / _ 開頭）。
        無限值域（>MAX_CHECK_VALUES）欄位唔收集（id / created_at 等唔係值域）。
        """
        import os
        import sqlite3 as _sq
        MAX_CHECK_VALUES = 200  # 值域上限：超過 = 無限值域（唔係 check）
        collect = {}
        meta_root = r"C:\projects\meta"
        for folder in sorted(os.listdir(meta_root)):
            fdir = os.path.join(meta_root, folder)
            if not os.path.isdir(fdir):
                continue
            if folder.startswith("_") or folder.startswith("."):
                continue
            for fn in sorted(os.listdir(fdir)):
                if not fn.endswith(".db") or ".bak" in fn:
                    continue
                path = os.path.join(fdir, fn)
                try:
                    c = _sq.connect(f"file:{path}?mode=ro", uri=True)
                    try:
                        tabs = [r[0] for r in c.execute(
                            "SELECT name FROM sqlite_master"
                            " WHERE type='table'"
                            " AND name NOT LIKE 'sqlite_%'"
                            " AND name NOT LIKE '\\_%' ESCAPE '\\'")]
                        for tb in tabs:
                            try:
                                cols = [r[1] for r in c.execute(
                                    f"PRAGMA table_info([{tb}])")]
                            except Exception:
                                continue
                            for col in cols:
                                bucket = collect.setdefault(col, {})
                                if bucket is True:
                                    continue  # 已標記無限（跳過）
                                if len(bucket) > MAX_CHECK_VALUES:
                                    collect[col] = True  # 無限 -> 唔收集
                                    continue
                                try:
                                    q = (f"SELECT DISTINCT [{col}]"
                                         f" FROM [{tb}]"
                                         f" WHERE [{col}] IS NOT NULL")
                                    for r in c.execute(q):
                                        v = r[0]
                                        if isinstance(v, str):
                                            v = v.strip()
                                        if v == "" or v is None:
                                            continue
                                        # 長字串（例如 SQL 片段 / 長 description）
                                        # 唔係值域 -> 跳過（2026-10-27）
                                        if isinstance(v, str) and len(v) > 500:
                                            continue
                                        bucket[v] = True
                                        if len(bucket) > MAX_CHECK_VALUES:
                                            collect[col] = True  # 爆 -> 標記
                                            break
                                except Exception:
                                    continue
                    finally:
                        c.close()
                except Exception:
                    continue
        # 排序（數字先，文字後）；無限值域 -> 唔入結果
        out = {}
        for fname, vals in collect.items():
            if vals is True:
                continue
            nums = sorted(v for v in vals if isinstance(v, (int, float))
                          and not isinstance(v, bool))
            strs = sorted(v for v in vals
                          if isinstance(v, str) or isinstance(v, bool))
            out[fname] = nums + strs
        return out

    def _property_for_values(self, field_name, values):
        """由欄位實際值推導「型別×性質」property id（零 hardcode）

        - 全 0/1（或值全部係 0/1）-> BOOLEAN × NOT NULL
        - 全數字 -> INTEGER × NOT NULL
        - 有字串 -> TEXT × NOT NULL
        """
        all_num = all(isinstance(v, (int, float)) and not isinstance(v, bool)
                      for v in values)
        bool_like = all_num and all(v in (0, 1) for v in values)
        if bool_like:
            meta, fmt = "BOOLEAN", "NOT NULL"
        elif all_num:
            meta, fmt = "INTEGER", "NOT NULL"
        else:
            meta, fmt = "TEXT", "NOT NULL"
        r = self.conn.execute(
            "SELECT pr.id FROM db_field_property pr"
            " JOIN db_field_type ft ON ft.id = pr.db_field_type_id"
            " JOIN db_field_format ff ON ff.id = pr.db_field_format_id"
            " WHERE ft.meta = ? AND ff.format = ?",
            (meta, fmt)).fetchone()
        return r["id"] if r else None

    def _sync_values(self):
        """確保 value 表有齊 DDL 生成規則（冪等，唔燒 sqlite_sequence）

        2026-10-25（用戶要求）：formula 入表，唔係 code 寫死。
        placeholder：
            <db_field_unique_id>     欄位名（db_field_unique.id）
            <db_field_check.json_id> 允許值（db_field_check.id）
        """
        n = 0
        # 收斂：刪唔喺權威清單嘅行（is_active=0）
        ph = ",".join("?" * len(DEFAULT_VALUES))
        cur = self.conn.execute(
            f"DELETE FROM value WHERE id NOT IN ({ph})",
            tuple(v[0] for v in DEFAULT_VALUES))
        n += cur.rowcount
        for vid, vtype, formula in DEFAULT_VALUES:
            cur = self.conn.execute(
                "INSERT INTO value (id, type, formula)"
                " SELECT ?, ?, ? WHERE NOT EXISTS"
                " (SELECT 1 FROM value WHERE id = ?)",
                (vid, vtype, formula, vid))
            n += cur.rowcount
            # 校正（code 權威）
            self.conn.execute(
                "UPDATE value SET type = ?, formula = ?"
                " WHERE id = ? AND (type != ? OR formula != ?)",
                (vtype, formula, vid, vtype, formula))
        self.conn.commit()
        return n

    def values(self, active_only=True):
        """列出 DDL 生成規則（value 表）"""
        sql = "SELECT * FROM value"
        if active_only:
            sql += " WHERE is_active = 1"
        sql += " ORDER BY id"
        return [dict(r) for r in self.conn.execute(sql)]

    def _migrate_db_field_format(self):
        """遷移（幂等）：舊約束 token 表 db_field_setting -> db_field_format（2026-10-25 rebuild）

        只處理「舊約束 token 表」db_field_setting（有 format 欄、冇 db_field_type_id 欄）。
        新組合表 db_field_setting（db_field_xxxx rename 過嚟，有 db_field_type_id）
        唔可以郁（個名而家歸組合表用）。

        rename：db_field_setting -> db_field_format（保資料）。
        但舊資料係「組合」（primary_key|unique|auto_increment）——rebuild：
        remove all exist value，改 seed 原子 token（見 _sync_db_field_formats）。
        """
        has_old = self.conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table'"
            " AND name='db_field_setting'").fetchone()
        if has_old:
            # 檢查係咪舊約束 token 表（有 format 欄、冇 db_field_type_id）
            cols = [c[1] for c in self.conn.execute(
                "PRAGMA table_info('db_field_setting')")]
            if "format" not in cols or "db_field_type_id" in cols:
                return  # 唔係舊 token 表（新組合表用緊個名）——唔郁
            has_new = self.conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table'"
                " AND name='db_field_format'").fetchone()
            if not has_new:
                self.conn.execute(
                    "ALTER TABLE db_field_setting RENAME TO db_field_format")
                self.conn.commit()
                print("[structure] db_field_setting -> db_field_format（rename）")
            else:
                # 兩者都有 -> drop 舊（資料係組合，唔再適用）
                self.conn.execute("DROP TABLE db_field_setting")
                self.conn.commit()
                print("[structure] db_field_setting drop（組合理念移除）")
        # 2. 補 missing format value（原子 token seed）
        self._sync_db_field_formats()

    def _sync_db_field_formats(self):
        """確保 db_field_format 有齊標準原子 token（冪等）

        2026-10-25 rebuild：remove all exist value——
        db_field_format 唔再存「組合」（primary_key|unique|auto_increment 等），
        只存單一原子 token：
            primary_key / unique / auto_increment / NOW / NULL / localtime
        舊格式（primary_key|unique|auto_increment 組合）全部刪除，
        改用新原子 token seed。
        """
        # 1. 清空舊值（組合格式唔再適用）
        self.conn.execute("DELETE FROM db_field_format")
        # 2. seed 新原子 token（固定 id 1-6）
        n = 0
        for fid, fmt, desc in DEFAULT_FIELD_FORMATS:
            cur = self.conn.execute(
                "INSERT INTO db_field_format (id, format, is_active)"
                " SELECT ?, ?, 1 WHERE NOT EXISTS"
                " (SELECT 1 FROM db_field_format WHERE id = ?)",
                (fid, fmt, fid))
            n += cur.rowcount
        self.conn.commit()
        return n

    def _migrate_db_field_default_drop(self):
        """遷移（幂等）：db_field_default 表移除（2026-10-25）

        fallback 值字典 = common.boolean（0/1 權威）；
        db_field_setting.db_field_default_id 直指 cmmdb.boolean.id。
        舊表（含更舊嘅 db_field_default_value 值表）存在 -> drop。
        2026-10-26：default_value_text（殘留 1 行）都 drop —— 預設值由
        build_column_definitions 嘅 default_value 表達式提供，唔需要值表。
        """
        for tbl in ("db_field_default_value", "db_field_default",
                    "default_value_text"):
            has = self.conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                (tbl,)).fetchone()
            if has:
                self.conn.execute(f"DROP TABLE {tbl}")
                print(f"[structure] {tbl} drop（fallback 字典 = common.boolean）")
        self.conn.commit()


    def _migrate_db_field_xxxx(self):
        """遷移（幂等）：db_field_xxxx -> db_field_setting（2026-10-25 rebuild）

        表名 rename：db_field_xxxx 組合表改名做 db_field_setting
        （舊「約束 token 表」db_field_setting 已喺上一輪改名做 db_field_format）。
        同時重建：db_field_unique 移除 unique 欄後，組合表照舊結構。

        做法：
          1. db_field_xxxx 存在 -> ALTER TABLE RENAME TO db_field_setting
             （DB_FIELD_SETTING_DDL 已建新表，rename 前 drop 空表）
          2. 由 _sync_db_field_xxxx 重新 seed（冪等）
        """
        # 1. 舊 db_field_xxxx -> db_field_setting（rename）
        has_old = self.conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table'"
            " AND name='db_field_xxxx'").fetchone()
        if has_old:
            # db_field_setting 可能已由新 DDL 建咗（空表/seed 表）
            has_new = self.conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table'"
                " AND name='db_field_setting'").fetchone()
            old_n = self.conn.execute(
                "SELECT COUNT(*) c FROM db_field_xxxx").fetchone()["c"]
            if has_new:
                new_n = self.conn.execute(
                    "SELECT COUNT(*) c FROM db_field_setting").fetchone()["c"]
                cols_new = [c[1] for c in self.conn.execute(
                    "PRAGMA table_info('db_field_setting')")]
                if "db_field_type_id" in cols_new and new_n <= old_n:
                    # db_field_setting 係新 DDL seed 嘅空表/孖生表 -> drop 再 rename
                    self.conn.execute("DROP TABLE db_field_setting")
                else:
                    # db_field_setting 有真正資料 -> 唔可以亂郁，保留 xxxx？
                    # 唔對：xxxx 應該係唯一組合表；drop xxxx（有 seed 可重建）
                    self.conn.execute("DROP TABLE db_field_xxxx")
                    self.conn.commit()
                    print("[structure] db_field_xxxx drop（db_field_setting 已有）")
                    return
            # rename db_field_xxxx -> db_field_setting
            self.conn.execute(
                "ALTER TABLE db_field_xxxx RENAME TO db_field_setting")
            self.conn.commit()
            print("[structure] db_field_xxxx -> db_field_setting（rename）")
            return
        # 2. 檢查 db_field_setting 係咪新本體表（db_field_xxxx 已 rename 過）
        cols = [c[1] for c in self.conn.execute(
            "PRAGMA table_info('db_field_setting')")]
        if "db_field_type_id" in cols:
            # 2026-10-25 末版：db_field_setting 曾有 db_field_format_id +
            # 4 個 boolean 性質欄 + db_field_unique_id——而家性質搬去
            # db_field_property 表，setting 只保留「型別」本體
            legacy_cols = {"db_field_format_id", "is_primary_key_id",
                           "is_unique_id", "auto_increment_id",
                           "not_null_id", "db_field_default_id"}
            if legacy_cols & set(cols):
                self.conn.execute("DROP TABLE db_field_setting")
                self.conn.execute(DB_FIELD_SETTING_DDL)
                self.conn.commit()
                print("[structure] db_field_setting 重建"
                      "（型別本體；性質搬 db_field_property）")
                return
            # 淨返 db_field_unique_id 要移除（欄位名唔需要喺呢度）
            if "db_field_unique_id" in cols:
                # 有引用 -> 先斷（db_field_setting 冇被 stucture 用就安全）
                self.conn.execute(
                    "ALTER TABLE db_field_setting"
                    " DROP COLUMN db_field_unique_id")
                self.conn.commit()
                print("[structure] db_field_setting 移除"
                      " db_field_unique_id 欄")
            return  # 已新版本體表
        # 3. 舊 db_field_setting（只 format 欄）-> db_field_format 已處理；
        #    呢度確保新組合表存在（由 DDL 建咗）
        self.conn.commit()
        print("[structure] db_field_setting 新組合表就緒")

    def _migrate_db_field_setting_refs_to_xxxx(self):
        """遷移（幂等）：db_field_stucture / db_table_setting 引用校準
        -> 固定 db_field_setting id（2026-10-25 權威本體）

        db_field_setting 而家係「欄位名 + 型別」本體（固定 id 1-6），
        性質喺 db_field_property。舊值（1-423 組合）冇法逐一對應
        -> 用 column_name 對應固定 id：
            id          -> 1（INTEGER）     description 等 -> 2（required TEXT）
            meta_key    -> 1?（冇唯一）-> 唔得；用 2 or 3
        實際固定 mapping：
            id           -> 1
            description/其他 required -> 2
            meta_key     -> 2（冇 unique 性質都啱？meta_key 通常 unique）
            is_active    -> 4
            created_at   -> 5
            updated_at   -> 6
        """
        def _xxxx_for(column_name):
            """column_name -> 固定 db_field_setting id"""
            return {
                "id": 1,
                "meta_key": 2,
                "is_active": 4,
                "created_at": 5,
                "updated_at": 6,
            }.get(column_name, 2)  # 其他 -> required TEXT

        changed = 0
        # db_field_stucture（column_name 對應）
        rows = self.conn.execute(
            "SELECT id, column_name, db_field_format_id"
            " FROM db_field_stucture").fetchall()
        for r in rows:
            xid = _xxxx_for(r["column_name"])
            if not xid:
                continue
            cur = self.conn.execute(
                "UPDATE db_field_stucture SET db_field_format_id = ?"
                " WHERE id = ? AND db_field_format_id != ?",
                (xid, r["id"], xid))
            changed += cur.rowcount
        # db_table_setting（meta_key 對應）
        rows = self.conn.execute(
            "SELECT id, meta_key, db_field_format_id"
            " FROM db_table_setting").fetchall()
        for r in rows:
            xid = _xxxx_for(r["meta_key"])
            if not xid:
                continue
            cur = self.conn.execute(
                "UPDATE db_table_setting SET db_field_format_id = ?"
                " WHERE id = ? AND db_field_format_id != ?",
                (xid, r["id"], xid))
            changed += cur.rowcount
        # db_field_position 已移除（2026-10-25）——冇得對應組合
        self.conn.commit()
        if changed:
            print(f"[structure] db_field_stucture/table_setting"
                  f" 引用校準去 db_field_setting：{changed} 行")
        # 收斂（鐵律 5）：刪冇被引用嘅 setting 組合，但保留 seed 組合
        #   （seed 定義喺 _sync_db_field_xxxx combos 固定 id 1-6；
        #    刪咗會令 reseed 每次開燒號）
        seed_sql = "fx.id BETWEEN 1 AND 6"
        orphan = self.conn.execute(
            f"""SELECT fx.id FROM db_field_setting fx
               WHERE NOT EXISTS (SELECT 1 FROM db_field_stucture tc
                                 WHERE tc.db_field_format_id = fx.id)
                 AND NOT EXISTS (SELECT 1 FROM db_table_setting ts
                                 WHERE ts.db_field_format_id = fx.id)
                 AND NOT ({seed_sql})""").fetchall()
        if orphan:
            for r in orphan:
                self.conn.execute(
                    "DELETE FROM db_field_setting WHERE id = ?", (r["id"],))
            self.conn.commit()
            print(f"[structure] 清理冇引用 db_field_setting：{len(orphan)} 個")

    def _migrate_db_field_type_old(self):
        """遷移（幂等）：db_field_type 舊版 -> 新版（description NOT NULL + 標準型別）

        新版 = id|meta|description|is_active|created_at。
        舊版（有 db_field_unique_id 或「冇 description」）-> drop 重建（保留 meta 資料）。
        重建時 description 由 DEFAULT_FIELD_TYPES 補齊（NOT NULL）。
        """
        cols = [c[1] for c in self.conn.execute(
            "PRAGMA table_info('db_field_type')")]
        if "db_field_unique_id" not in cols and "description" in cols:
            # 已新版；2026-10-26：舊 live DB 冇 default_value 欄 -> ALTER 補
            if "default_value" not in cols:
                self.conn.execute(
                    "ALTER TABLE db_field_type"
                    " ADD COLUMN default_value BOOLEAN NOT NULL DEFAULT 0"
                    " CHECK (default_value IN (0,1))")
                self.conn.commit()
            return  # 已新版
        rows = []
        if "meta" in cols:
            rows = [dict(r) for r in self.conn.execute(
                "SELECT meta FROM db_field_type WHERE is_active = 1")]
        self.conn.execute("DROP TABLE db_field_type")
        self.conn.execute(DB_FIELD_TYPE_DDL)
        # 只保留標準型別（DEFAULT_FIELD_TYPES；CHINESE/PYTHON/SQL 唔係型別）
        desc_map = {m: d for m, d in DEFAULT_FIELD_TYPES}
        for r in rows:
            if r["meta"] not in desc_map:
                continue
            self.conn.execute(
                "INSERT INTO db_field_type (meta, description)"
                " SELECT ?, ? WHERE NOT EXISTS"
                " (SELECT 1 FROM db_field_type WHERE meta = ?)",
                (r["meta"], desc_map[r["meta"]], r["meta"]))
        self.conn.commit()
        metas = [r["meta"] for r in rows]
        kept = [m for m in metas if m in desc_map]
        print(f"[structure] db_field_type 重建（{len(desc_map)} 標準型別）："
              f"{len(metas)} 個原型別 -> {len(kept)} 個保留")

    def _migrate_db_field_unique_drop_flag(self):
        """遷移（幂等）：db_field_unique 重建（2026-10-25 rebuild 2）

        新格式：id（AUTOINCREMENT PK UNIQUE）+ value（TEXT NOT NULL）。
        舊格式（meta_key + description）-> 重建：meta_key 搬去 value。
        """
        cols = [c[1] for c in self.conn.execute(
            "PRAGMA table_info('db_field_unique')")]
        cols = [c[1] for c in self.conn.execute(
            "PRAGMA table_info('db_field_unique')")]
        if cols == ["id", "value"]:
            return  # 已新版
        # copy 舊值（meta_key -> value）
        try:
            rows = [dict(r) for r in self.conn.execute(
                "SELECT id, meta_key, description FROM db_field_unique")]
        except Exception:
            rows = []
        self.conn.execute("DROP TABLE db_field_unique")
        self.conn.execute(DB_FIELD_UNIQUE_DDL)
        for r in rows:
            val = r.get("meta_key") or r.get("value")
            if not val:
                continue
            self.conn.execute(
                "INSERT INTO db_field_unique (id, value)"
                " SELECT ?, ? WHERE NOT EXISTS"
                " (SELECT 1 FROM db_field_unique WHERE id = ?)",
                (r["id"], val, r["id"]))
        self.conn.commit()
        print("[structure] db_field_unique rebuild（id + value）")

    def _sync_db_field_uniques(self):
        """確保 db_field_unique 有齊欄位名（冪等，唔燒 sqlite_sequence）

        2026-10-25 rebuild：value 取代 meta_key+description。
        2026-10-26：欄位名唔再淨係權威 5 個 —— 由「真實 db_field」
        （resource.db db_field 實例）推導補齊，零 hardcode。
        """
        n = 0
        # 權威 seed 先行
        for val in DEFAULT_FIELD_UNIQUES:
            cur = self.conn.execute(
                "INSERT INTO db_field_unique (value)"
                " SELECT ? WHERE NOT EXISTS"
                " (SELECT 1 FROM db_field_unique WHERE value = ?)",
                (val, val))
            n += cur.rowcount
        # 由真實 db_field 補齊欄位名（is_active / passed / boolean_id ...）
        for val in self._real_field_names():
            cur = self.conn.execute(
                "INSERT INTO db_field_unique (value)"
                " SELECT ? WHERE NOT EXISTS"
                " (SELECT 1 FROM db_field_unique WHERE value = ?)",
                (val, val))
            n += cur.rowcount
        self.conn.commit()
        return n

    def _real_field_names(self):
        """由真實 db_field 攞全部欄位名（resource.db 唯讀，零猜測）"""
        try:
            import sqlite3 as _sq
            res = _sq.connect(
                f"file:{r'C:\projects\meta\_resource_removed_20261026\resource.db'}?mode=ro",
                uri=True)
            try:
                return [r[0] for r in res.execute(
                    "SELECT DISTINCT meta_key FROM db_field"
                    " WHERE is_active = 1 ORDER BY meta_key")]
            finally:
                res.close()
        except Exception:
            return []

    def _sync_db_field_settings(self):
        """seed db_field_setting（冪等，2026-10-26 用戶指定 5 個欄位設定）

        一行 = 一個欄位名（db_field_unique_id）× 一個性質（db_field_property_id）。
        正規化：一個欄位多個性質 = 多行（created_at 有 NOW + localtime + NOT NULL
        = 3 行）。只補缺（唔 DELETE，避免燒 sqlite_sequence）。
        """
        n = 0
        for uid, props in DEFAULT_FIELD_SETTINGS:
            for pid in props:
                cur = self.conn.execute(
                    "INSERT INTO db_field_setting"
                    " (db_field_unique_id, db_field_property_id)"
                    " SELECT ?, ? WHERE NOT EXISTS"
                    " (SELECT 1 FROM db_field_setting"
                    "  WHERE db_field_unique_id = ? AND db_field_property_id = ?)",
                    (uid, pid, uid, pid))
                n += cur.rowcount
        self.conn.commit()
        return n

    def db_field_settings(self, active_only=True):
        """列出欄位設定（JOIN db_field_unique + db_field_property）"""
        uniq = {r["id"]: r["value"] for r in self.conn.execute(
            "SELECT id, value FROM db_field_unique")}
        props = {}
        for r in self.conn.execute(
                "SELECT pr.id, ft.meta AS type_name, ff.format"
                " FROM db_field_property pr"
                " JOIN db_field_type ft ON ft.id = pr.db_field_type_id"
                " JOIN db_field_format ff ON ff.id = pr.db_field_format_id"):
            props[r["id"]] = (r["type_name"], r["format"])
        sql = "SELECT * FROM db_field_setting WHERE 1=1"
        if active_only:
            sql += " AND is_active = 1"
        sql += " ORDER BY db_field_unique_id, db_field_property_id"
        rows = [dict(r) for r in self.conn.execute(sql)]
        for d in rows:
            d["unique_name"] = uniq.get(d["db_field_unique_id"])
            t, f = props.get(d["db_field_property_id"], (None, None))
            d["type_name"] = t
            d["format"] = f
        return rows

    def _migrate_db_table_stucture(self):
        """遷移（幂等）：table_definition -> db_table_stucture（2026-10-25 rename）

        舊名 db_table_stucture 之後由 _migrate_new_names rename 做 structure_db_table。
        """
        has_old = self.conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table'"
            " AND name='table_definition'").fetchone()
        if has_old:
            # 目標表（可能已 rename）
            target = "db_table_stucture"
            has_t = self.conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table'"
                " AND name='db_table_stucture'").fetchone()
            if not has_t:
                has_t = self.conn.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table'"
                    " AND name='structure_db_table'").fetchone()
                if has_t:
                    target = "structure_db_table"
                else:
                    self.conn.execute(DB_TABLE_STRUCTURE_DDL)
            n = self.conn.execute(
                f"SELECT COUNT(*) c FROM {target}").fetchone()["c"]
            if n == 0:
                try:
                    self.conn.execute(
                        f"INSERT INTO {target}"
                        " (id, table_name, db_file, description, module_scope,"
                        "  is_active, created_at, updated_at)"
                        " SELECT id, table_name, db_file, description,"
                        "        module_scope, is_active, created_at, updated_at"
                        " FROM table_definition"
                        f" WHERE NOT EXISTS (SELECT 1 FROM {target})")
                    self.conn.commit()
                except Exception:
                    pass
            self.conn.execute("DROP TABLE table_definition")
            self.conn.commit()
            print("[structure] table_definition -> db_table_stucture（rename）")

    # ---------------- 2026-10-26 redesign：structure_db_table / field by_id ----------------
    def _module_ids_by_db(self):
        """db 檔名 -> (channel_id, module_id)（taxonomy 權威）

        由 taxonomy.db tree + taxonomy（tree=module）+ physical_path 組 map：
            db 檔名（question.db / terminology.db / qc.db ...）->
            (tree.channel.id, taxonomy.id)
        db_file 對應由 physical_path（tree_id=2 module 層，full_path 尾段）
        推導（零 hardcode）。搵唔到 -> 無。
        """
        import sqlite3 as _sq
        mods = {}
        try:
            tc = _sq.connect(r"C:\projects\meta\taxonomy\taxonomy.db")
            tc.row_factory = _sq.Row
            try:
                ch = tc.execute(
                    "SELECT id FROM tree WHERE meta_key = 'channel'"
                    " AND is_active = 1").fetchone()
                channel = ch["id"] if ch else 1
                rows = tc.execute(
                    "SELECT t.id AS mid, pp.full_path"
                    " FROM taxonomy t"
                    " LEFT JOIN physical_path pp"
                    "   ON pp.module = t.meta AND pp.tree_id = 2"
                    " WHERE t.tree_id = 2 AND t.is_active = 1").fetchall()
                for r in rows:
                    fp = r["full_path"] or ""
                    if not fp.endswith(".db"):
                        continue
                    mods.setdefault(os.path.basename(fp),
                                    (channel, r["mid"]))
            finally:
                tc.close()
        except Exception:
            pass
        return mods

    def _migrate_db_table_structure_v2(self):
        """遷移（幂等）：structure_db_table 舊版（db_file 字串）-> 新版（by_id）

        2026-10-26 redesign：db_file -> (channel_id, module_id)。
        舊資料（db_file + table_name 唯一）逐行搬：
            db_file -> taxonomy 權威 map（_module_ids_by_db）
            搵到 -> 新版行（channel_id/module_id/table_name）
            搵唔到 -> 丟棄（舊 2 行係 definition.db 測試行，唔係真表）
        新表結構由 DB_TABLE_STRUCTURE_DDL 定義；重建保留 is_active/created_at。
        """
        cols = [c[1] for c in self.conn.execute(
            "PRAGMA table_info('structure_db_table')")]
        if "db_file" not in cols:
            return  # 已係新版
        rows = [dict(r) for r in self.conn.execute(
            "SELECT * FROM structure_db_table")]
        mod_by_db = self._module_ids_by_db()
        self.conn.execute("DROP TABLE structure_db_table")
        self.conn.execute(DB_TABLE_STRUCTURE_DDL)
        n = 0
        for r in rows:
            pair = mod_by_db.get(r["db_file"])
            if not pair:
                continue
            channel_id, module_id = pair
            # 保留原 id（field 遷移靠 id 對應；AUTOINCREMENT 會自動跳過已用 id）
            self.conn.execute(
                "INSERT INTO structure_db_table"
                " (id, channel_id, module_id, table_name, description,"
                "  is_active, created_at, updated_at)"
                " SELECT ?, ?, ?, ?, ?, ?, ?, ? WHERE NOT EXISTS"
                " (SELECT 1 FROM structure_db_table"
                "  WHERE channel_id = ? AND module_id = ? AND table_name = ?)",
                (r["id"], channel_id, module_id, r["table_name"],
                 r.get("description") or "",
                 r.get("is_active", 1),
                 r.get("created_at"), r.get("updated_at"),
                 channel_id, module_id, r["table_name"]))
            n += 1
        self.conn.commit()
        print(f"[structure] structure_db_table v2（by_id）：搬 {n}/{len(rows)} 行")

    def _migrate_db_field_check_link(self):
        """遷移（幂等）：structure_db_field 加 db_field_check_id 欄（2026-10-27 用戶要求）

        db_field_check_id = db_field_check.id（該欄位嘅真實值域 check）。
        db_field_check 表本身有 structure_db_field_id（UNIQUE）——
        link 由 db_field_check.structure_db_field_id 反查（每個 field 最多一個 check）。
        缺欄就 ALTER ADD；回填只填 NULL（唔覆蓋手動值）。
        """
        cols = {c[1] for c in self.conn.execute(
            "PRAGMA table_info(structure_db_field)")}
        if "db_field_check_id" not in cols:
            self.conn.execute(
                "ALTER TABLE structure_db_field ADD COLUMN db_field_check_id INTEGER")
            self.conn.commit()
            print("[structure] structure_db_field + db_field_check_id 欄")
        # 回填：由 db_field_check.structure_db_field_id 反查（只填 NULL）
        cur = self.conn.execute(
            """UPDATE structure_db_field SET db_field_check_id =
               (SELECT c.id FROM db_field_check c
                WHERE c.structure_db_field_id = structure_db_field.id)
               WHERE db_field_check_id IS NULL
                 AND EXISTS (SELECT 1 FROM db_field_check c
                             WHERE c.structure_db_field_id =
                                   structure_db_field.id)""")
        self.conn.commit()
        if cur.rowcount:
            print(f"[structure] db_field_check_id 回填：{cur.rowcount} 行")

    def _migrate_db_field_structure_v2(self):
        """遷移（幂等）：structure_db_field 舊版（column_name 字串）-> 新版（by_id）

        2026-10-26 redesign：column_name -> field_name；淨結構描述。
        舊資料（db_table_stucture_id + column_name 唯一）逐行搬：
            舊 db_table_stucture_id -> 新 table row id（_migrate_db_table_structure_v2
            之後 id 唔變，因為搬遷保留 id 順序插入——但保險起見按
            (channel_id, module_id, table_name) 反查新 id）
        新表結構由 TABLE_COLUMN_DDL 定義。
        """
        cols = [c[1] for c in self.conn.execute(
            "PRAGMA table_info('structure_db_field')")]
        if "column_name" not in cols:
            # 已係新版：若仲有舊殘留欄（db_field_property_id，之前版本
            # ALTER 加過）-> 清走（淨結構）。
            # 2026-10-27：db_field_check_id 保留 —— 用戶要求（值域 check link），
            # 由 _migrate_db_field_check_link 補欄 + 回填。
            for old_col in ("db_field_property_id",):
                if old_col in cols:
                    try:
                        self.conn.execute(
                            "ALTER TABLE structure_db_field"
                            f" DROP COLUMN {old_col}")
                        self.conn.commit()
                        print(f"[structure] structure_db_field 移除舊欄 {old_col}")
                    except Exception as exc:
                        print(f"[structure] drop {old_col} 失敗: {exc}")
            return  # 已係新版
        rows = [dict(r) for r in self.conn.execute(
            "SELECT * FROM structure_db_field")]
        self.conn.execute("DROP TABLE structure_db_field")
        self.conn.execute(TABLE_COLUMN_DDL)
        n = 0
        for r in rows:
            # 保留原 id（table 遷移保留 id，field 直接沿用）
            self.conn.execute(
                "INSERT INTO structure_db_field"
                " (id, structure_db_table_id, field_name, description,"
                "  is_active, created_at, updated_at)"
                " SELECT ?, ?, ?, ?, ?, ?, ? WHERE NOT EXISTS"
                " (SELECT 1 FROM structure_db_field"
                "  WHERE structure_db_table_id = ? AND field_name = ?)",
                (r["id"], r["db_table_stucture_id"], r["column_name"],
                 r.get("description") or "",
                 r.get("is_active", 1),
                 r.get("created_at"), r.get("updated_at"),
                 r["db_table_stucture_id"], r["column_name"]))
            n += 1
        self.conn.commit()
        print(f"[structure] structure_db_field v2（by_id）：搬 {n}/{len(rows)} 行")

    def sync_db_tables(self):
        """全站真實表掃描（2026-10-26 用戶要求：所有真實資料入表）

        掃每個 module 資料夾（taxonomy.taxonomy tree=module 權威）內嘅
        *module*.db（實際檔案，零 physical_path 依賴 —— physical_path
        舊版有錯配記錄）：
            - 每張真表（sqlite_master type='table'，唔包 sqlite_%）入
              structure_db_table（channel_id + module_id + table_name）
            - 每個真欄位（PRAGMA table_info）入 structure_db_field
              （structure_db_table_id + field_name）
        冪等：INSERT WHERE NOT EXISTS；已存在嘅行不變（description 保留）。
        特殊：qc.db（多 module 共用）以檔案存在為主 → 用「邊個 module
        資料夾有呢個檔」決定歸屬。
        """
        meta_root = r"C:\projects\meta"
        # module 權威：taxonomy.registry（tree=module）-> folder
        # （2026-10-27 taxonomy rename 做 registry）
        try:
            import sqlite3 as _sq
            tc = _sq.connect(r"C:\projects\meta\taxonomy\taxonomy.db")
            tc.row_factory = _sq.Row
            mods = []
            try:
                ch = tc.execute(
                    "SELECT id FROM tree WHERE meta_key='channel'"
                    " AND is_active=1").fetchone()
                channel = ch["id"] if ch else 1
                for r in tc.execute(
                        "SELECT id, meta FROM registry"
                        " WHERE tree_id=2 AND is_active=1 ORDER BY meta"):
                    mods.append((r["id"], r["meta"]))
            finally:
                tc.close()
        except Exception:
            return 0, 0
        n_tab = n_fld = 0
        # 已登記嘅 (channel, module, table) 快照（冪等跳過）
        known = set()
        for r in self.conn.execute(
                "SELECT channel_id, module_id, table_name"
                " FROM structure_db_table"):
            known.add((r["channel_id"], r["module_id"], r["table_name"]))
        # 每 module：folder 內嘅 *.db（自己名優先，次選其他）
        for module_id, folder in mods:
            folder_path = os.path.join(meta_root, folder)
            if not os.path.isdir(folder_path):
                continue
            db_files = sorted(f for f in os.listdir(folder_path)
                              if f.endswith(".db")
                              and ".bak" not in f)
            if not db_files:
                continue
            for db_file in db_files:
                path = os.path.join(folder_path, db_file)
                if not os.path.isfile(path):
                    continue
                try:
                    src = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
                except Exception:
                    continue
                try:
                    tabs = [r[0] for r in src.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'"
                        " AND name NOT LIKE 'sqlite_%' ORDER BY name")]
                    for tb in tabs:
                        if (channel, module_id, tb) in known:
                            continue
                        self.conn.execute(
                            "INSERT INTO structure_db_table"
                            " (channel_id, module_id, table_name)"
                            " VALUES (?, ?, ?)",
                            (channel, module_id, tb))
                        tid = self.conn.execute(
                            "SELECT id FROM structure_db_table"
                            " WHERE channel_id = ? AND module_id = ?"
                            "  AND table_name = ?",
                            (channel, module_id, tb)).fetchone()
                        if not tid:
                            continue
                        tid = tid["id"]
                        known.add((channel, module_id, tb))
                        n_tab += 1
                        for col in src.execute(f"PRAGMA table_info([{tb}])"):
                            self.conn.execute(
                                "INSERT INTO structure_db_field"
                                " (structure_db_table_id, field_name)"
                                " SELECT ?, ? WHERE NOT EXISTS"
                                " (SELECT 1 FROM structure_db_field"
                                "  WHERE structure_db_table_id = ?"
                                "  AND field_name = ?)",
                                (tid, col[1], tid, col[1]))
                            n_fld += 1
                finally:
                    src.close()
        # 孤兒清掃：刪「唔對應任何 module folder 內真實 db 檔」嘅表行
        # （舊版靠錯 physical_path 掃入嘅假行）
        real = set()  # (module_id, table_name)
        for module_id, folder in mods:
            folder_path = os.path.join(meta_root, folder)
            if not os.path.isdir(folder_path):
                continue
            for db_file in (f for f in os.listdir(folder_path)
                            if f.endswith(".db") and ".bak" not in f):
                path = os.path.join(folder_path, db_file)
                if not os.path.isfile(path):
                    continue
                try:
                    src = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
                    try:
                        for r in src.execute(
                                "SELECT name FROM sqlite_master"
                                " WHERE type='table'"
                                " AND name NOT LIKE 'sqlite_%'"):
                            real.add((module_id, r[0]))
                    finally:
                        src.close()
                except Exception:
                    continue
        rows = self.conn.execute(
            "SELECT id, module_id, table_name FROM structure_db_table"
        ).fetchall()
        n_orphan = 0
        for r in rows:
            if (r["module_id"], r["table_name"]) not in real:
                # 保底：唔刪含 description 嘅手動行（register_table_definition）
                desc = self.conn.execute(
                    "SELECT description FROM structure_db_table WHERE id=?",
                    (r["id"],)).fetchone()["description"]
                if desc:
                    continue
                self.conn.execute(
                    "DELETE FROM structure_db_table WHERE id=?", (r["id"],))
                self.conn.execute(
                    "DELETE FROM structure_db_field"
                    " WHERE structure_db_table_id=?", (r["id"],))
                n_orphan += 1
        self.conn.commit()
        if n_orphan:
            print(f"[structure] sync_db_tables：清孤兒 {n_orphan} 行")
        return n_tab, n_fld

    def _migrate_db_field_stucture(self):
        """遷移（幂等）：db_field -> db_field_stucture（2026-10-25 rename，舊名）"""
        # 移除 references 欄（FK 唔喺結構層，2026-10-25）
        for rcol in ("references_table", "references_column"):
            cols = [c[1] for c in self.conn.execute(
                "PRAGMA table_info('db_field_stucture')")]
            if rcol in cols:
                self.conn.execute(
                    "ALTER TABLE db_field_stucture DROP COLUMN " + rcol)
                self.conn.commit()
                print(f"[structure] db_field_stucture 移除 {rcol} 欄")
        # table_column -> db_field（舊）
        has_tc = self.conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table'"
            " AND name='table_column'").fetchone()
        if has_tc:
            has_df = self.conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table'"
                " AND name='db_field'").fetchone()
            if has_df:
                n = self.conn.execute(
                    "SELECT COUNT(*) c FROM db_field").fetchone()["c"]
                if n == 0:
                    self.conn.execute("DROP TABLE db_field")
                else:
                    raise ValueError("db_field 已有資料唔可以合併")
            self.conn.execute("ALTER TABLE table_column RENAME TO db_field")
            self.conn.commit()
        # db_field -> db_field_stucture
        has_old = self.conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table'"
            " AND name='db_field'").fetchone()
        if has_old:
            # 目標表（可能已經係 structure_db_field，由 _migrate_new_names rename）
            target = "db_field_stucture"
            has_target = self.conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table'"
                " AND name='db_field_stucture'").fetchone()
            if not has_target:
                # 可能已經 rename 做 structure_db_field
                has_target = self.conn.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table'"
                    " AND name='structure_db_field'").fetchone()
                if has_target:
                    target = "structure_db_field"
                else:
                    self.conn.execute(TABLE_COLUMN_DDL)
            n = self.conn.execute(
                f"SELECT COUNT(*) c FROM {target}").fetchone()["c"]
            if n == 0:
                # 舊欄：table_definition_id -> db_table_stucture_id；
                # db_field db_field_format_id -> 經 db_field_setting 反查型別
                #   （2026-10-25：db_field_format_id 唔見 -> fallback TEXT）
                has_setting = self.conn.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table'"
                    " AND name='db_field_setting'").fetchone()
                try:
                    if has_setting:
                        self.conn.execute(
                            f"""INSERT INTO {target}
                               (id, db_table_stucture_id, column_name,
                                db_field_type_id, position_id,
                                is_active, created_at, updated_at)
                               SELECT f.id, f.table_definition_id, f.column_name,
                                      COALESCE(s.db_field_type_id,
                                               (SELECT id FROM db_field_type
                                                WHERE meta = 'TEXT')),
                                      f.position_id,
                                      f.is_active, f.created_at, f.updated_at
                               FROM db_field f
                               LEFT JOIN db_field_setting s
                                 ON s.id = f.db_field_format_id
                               WHERE NOT EXISTS
                               (SELECT 1 FROM {target})""")
                    else:
                        self.conn.execute(
                            f"""INSERT INTO {target}
                               (id, db_table_stucture_id, column_name,
                                db_field_type_id, position_id,
                                is_active, created_at, updated_at)
                               SELECT id, table_definition_id, column_name,
                                      (SELECT id FROM db_field_type
                                       WHERE meta = 'TEXT'),
                                      position_id,
                                      is_active, created_at, updated_at
                               FROM db_field
                               WHERE NOT EXISTS
                               (SELECT 1 FROM {target})""")
                    self.conn.commit()
                except Exception as e:
                    print(f"[structure] db_field -> stucture 搬入失敗：{e}")
            self.conn.execute("DROP TABLE db_field")
            self.conn.commit()
            print("[structure] db_field -> db_field_stucture（rename）")

    def _migrate_from_definition(self):
        """遷移（幂等）：structure_type 由 definition 搬入（2026-10-25）

        2026-10-25（用戶要求）：字典/檔案表歸 structure。
        definition.db 舊表存在 -> 搬資料 -> drop 舊表（definition 之後建新都係空）。
        2026-10-26：file_type / structure_file 已移除 —— 只搬 structure_type；
        舊 file_type / structure_file 表由 __init__ 統一 drop。
        """
        # 1. structure_type（seed 兜底）
        for pid, meta, desc in DEFAULT_STRUCTURE_TYPES:
            self.conn.execute(
                "INSERT INTO structure_type (id, meta, description)"
                " SELECT ?, ?, ? WHERE NOT EXISTS"
                " (SELECT 1 FROM structure_type WHERE id = ?)",
                (pid, meta, desc, pid))
            self.conn.execute(
                "UPDATE structure_type SET meta = ?, description = ?"
                " WHERE id = ?", (meta, desc, pid))
        # 1b. 3 張分層地址表（seed 兜底：root 地址入表）
        stypes = {r["meta"]: r["id"] for r in self.conn.execute(
            "SELECT id, meta FROM structure_type")}
        boss_rid = stypes.get("root")
        if boss_rid:
            for _smeta, _sval in DEFAULT_STRUCTURE_ADDRESSES:
                self.conn.execute(
                    "INSERT INTO structure_root (structure_type_id, value)"
                    " SELECT ?, ? WHERE NOT EXISTS"
                    " (SELECT 1 FROM structure_root WHERE structure_type_id = ?"
                    "  AND value = ?)",
                    (boss_rid, _sval, boss_rid, _sval))
        self.conn.commit()
        # 1c. 4 表全量 backfill（真實地址入表，唔淨係 root）
        self._backfill_structure_tables()
        self.conn.commit()

    def _backfill_structure_tables(self):
        r"""冪等補充 3 張分層地址表（2026-10-26 用戶設計）

        真實表（structure_root/module/skill）已有資料
        （skill 係真實技能名，絕對唔可以 DELETE）——
        呢度只係 WHERE NOT EXISTS 冪等補充 root + module 層：
            structure_root    -> C:\projects\meta（root type id）
            structure_module  -> 每 module：package=folder / file=folder /
                                db=db_file（root_id + module_id = taxonomy.taxonomy.id）
        skill 表唔郁。
        path_json 每段存各層表 id（by_id，零 hardcode）。
        """
        # ATTACH taxonomy.db（package 地址來源）
        # 2026-10-26：權威武 = taxonomy\taxonomy.db（guard resolve 後），
        # 唔係根目錄 taxonomy.db（舊 bug：新 module 登記咗但呢度讀唔到）
        try:
            self.conn.execute(
                "ATTACH DATABASE ? AS taxdb",
                (r"C:\projects\meta\taxonomy\taxonomy.db",))
        except Exception:
            pass  # 已 ATTACH
        stypes = {r["meta"]: r["id"] for r in self.conn.execute(
            "SELECT id, meta FROM structure_type")}
        # 0. root（冪等：有就唔加）
        rid = stypes.get("root")
        root_id = None
        if rid:
            for _smeta, _sval in DEFAULT_STRUCTURE_ADDRESSES:
                self.conn.execute(
                    "INSERT INTO structure_root (structure_type_id, value)"
                    " SELECT ?, ? WHERE NOT EXISTS"
                    " (SELECT 1 FROM structure_root"
                    "  WHERE structure_type_id = ? AND value = ?)",
                    (rid, _sval, rid, _sval))
            r = self.conn.execute(
                "SELECT id FROM structure_root WHERE structure_type_id = ?"
                " LIMIT 1", (rid,)).fetchone()
            root_id = r[0] if r else None
        pid, did, fid = (stypes.get(k) for k in
                         ("package", "db", "file"))
        # 1. module 層（冪等：每 module 每 type 補一行）
        # 2026-10-26（用戶要求）：taxonomy.package 表已移除 ——
        # module 清單 = taxdb.registry（tree = module；2026-10-27 rename），
        # folder = module 名，db_file = {module}.db。
        if pid and root_id is not None:
            for r in self.conn.execute(
                    "SELECT t.id, t.meta"
                    " FROM taxdb.registry t"
                    " JOIN taxdb.tree tr ON tr.id = t.tree_id"
                    " WHERE tr.meta_key = 'module' AND t.is_active = 1"):
                mod = r["meta"]
                if not mod:
                    continue
                # package + db 層（folder / db_file）
                for t, val in ((pid, mod), (did, f"{mod}.db")):
                    if not t or not val:
                        continue
                    self.conn.execute(
                        "INSERT INTO structure_module"
                        " (structure_type_id, root_id, module_id, value)"
                        " SELECT ?, ?, ?, ? WHERE NOT EXISTS"
                        " (SELECT 1 FROM structure_module"
                        "  WHERE structure_type_id = ? AND root_id = ?"
                        "  AND module_id = ? AND value = ?)",
                        (t, root_id, r["id"], val, t, root_id,
                         r["id"], val))
                # file 層：掃 module 資料夾嘅真實 .py 檔（每個檔一行）
                # 2026-10-26（用戶要求）：file 層 = 真實 .py 檔。
                # 舊 folder 名行（fake）刪除，再 INSERT 真實檔名行（冪等）。
                if fid:
                    self.conn.execute(
                        "DELETE FROM structure_module"
                        " WHERE structure_type_id = ? AND root_id = ?"
                        " AND module_id = ? AND value = ?",
                        (fid, root_id, r["id"], mod))
                    for fname in self._module_py_files(mod):
                        if not fname:
                            continue
                        self.conn.execute(
                            "INSERT INTO structure_module"
                            " (structure_type_id, root_id, module_id, value)"
                            " SELECT ?, ?, ?, ? WHERE NOT EXISTS"
                            " (SELECT 1 FROM structure_module"
                            "  WHERE structure_type_id = ? AND root_id = ?"
                            "  AND module_id = ? AND value = ?)",
                            (fid, root_id, r["id"], fname, fid, root_id,
                             r["id"], fname))
        self.conn.commit()

    def _module_py_files(self, folder):
        """掃一個 module 資料夾嘅真實 .py 檔名（冇資料夾 -> 空 list）"""
        import os
        if not folder:
            return []
        path = os.path.join(r"C:\projects\meta", folder)
        if not os.path.isdir(path):
            return []
        return sorted(fn for fn in os.listdir(path) if fn.endswith(".py"))

    def _migrate_location(self):
        r"""3 張分層表加 location 欄 + 推導物理位置（2026-10-26 用戶要求）

        location = 每個實體嘅實際物理位置（零 hardcode，由父鏈推導）：
            structure_root       -> root value（C:\projects\meta）
            structure_module     -> root + folder + file/db
                package 層（type=1）：root + folder\
                file 層（type=2）  ：root + folder\api.py
                db 層（type=5）    ：root + folder\code_gen.db
            structure_skill      -> root + folder\skill\xxx.py
                （skill 名 = function 名，由 ast.db 攞 function 實際所在 file）

        冪等：缺 location 欄先 ALTER TABLE ADD COLUMN；已有 location 唔重推。
        """
        # 1. 確保 3 張表有 location 欄（ALTER TABLE ADD COLUMN，保留資料）
        for tbl in ("structure_root", "structure_module",
                    "structure_skill"):
            cols = {c[1] for c in self.conn.execute(
                "PRAGMA table_info(%s)" % tbl)}
            if "location" not in cols:
                self.conn.execute(
                    "ALTER TABLE %s ADD COLUMN location TEXT" % tbl)
        self.conn.commit()
        # 2. root 層：location = value
        self.conn.execute(
            "UPDATE structure_root SET location = value"
            " WHERE location IS NULL OR location = ''")
        # 3. module 層：root + folder + file/db
        #    root value（structure_root.value）
        #    folder（taxonomy.registry.meta，tree = module；2026-10-27 rename）
        #    value（file 名 / db 檔名）
        # 2026-10-26（用戶要求）：taxonomy.package 表已移除 ——
        # module 身份 = taxdb.registry（tree = module），folder = meta。
        try:
            self.conn.execute(
                "ATTACH DATABASE ? AS taxdb",
                (r"C:\projects\meta\taxonomy\taxonomy.db",))
        except Exception:
            pass
        # 3a. package 層（type=1）：root + folder\
        self.conn.execute(
            "UPDATE structure_module SET location ="
            " (SELECT sr.value || '\\' || p.meta"
            "  FROM structure_root sr, taxdb.registry p"
            "  WHERE sr.id = structure_module.root_id"
            "   AND p.id = structure_module.module_id)"
            " WHERE structure_type_id = 1"
            " AND (location IS NULL OR location = '')")
        # 3b. file 層（type=2）：root + folder\value
        self.conn.execute(
            "UPDATE structure_module SET location ="
            " (SELECT sr.value || '\\' || p.meta"
            "         || '\\' || structure_module.value"
            "  FROM structure_root sr, taxdb.registry p"
            "  WHERE sr.id = structure_module.root_id"
            "   AND p.id = structure_module.module_id)"
            " WHERE structure_type_id = 2"
            " AND (location IS NULL OR location = '')")
        # 3c. db 層（type=5）：root + folder\value
        self.conn.execute(
            "UPDATE structure_module SET location ="
            " (SELECT sr.value || '\\' || p.meta"
            "         || '\\' || structure_module.value"
            "  FROM structure_root sr, taxdb.registry p"
            "  WHERE sr.id = structure_module.root_id"
            "   AND p.id = structure_module.module_id)"
            " WHERE structure_type_id = 5"
            " AND (location IS NULL OR location = '')")
        # 4. skill 層：真實路徑（function 實際所在 file）
        #    skill 名 = function 名，由 ast.db analyze_skill JOIN analyze_module
        #    攞 function 實際所在 file（同 module 嘅 file 層）
        #    location = root + folder + <實際 file>
        try:
            self.conn.execute(
                "ATTACH DATABASE ? AS astdb", (r"C:\projects\meta\ast\ast.db",))
        except Exception:
            pass
        self.conn.execute(
            "UPDATE structure_skill SET location ="
            " (SELECT sr.value || '\\' || p.meta"
            "         || '\\' || smf.value"
            "  FROM analyze_skill ask"
            "  JOIN astdb.function f ON f.id = ask.function_id"
            "  JOIN analyze_module am ON am.function_id = ask.function_id"
            "  JOIN structure_module smf ON smf.id = am.structure_module_id"
            "  JOIN structure_module smp ON smp.id ="
            "       structure_skill.structure_module_id"
            "  JOIN structure_root sr ON sr.id = smp.root_id"
            "  JOIN taxdb.registry p ON p.id = smp.module_id"
            "  WHERE ask.structure_skill_id = structure_skill.id"
            "   AND smf.module_id = smp.module_id"
            "   AND smf.structure_type_id = 2"
            "  LIMIT 1)"
            " WHERE location IS NULL OR location = ''"
            " OR location LIKE '%\\skill\\%'")
        self.conn.commit()

    def _seed_structure_taxonomy(self):
        """預填 structure_taxonomy（冪等）：樹層 ↔ 實體類型映射

        taxonomy.tree（層）x structure_type（實體類型）：
            channel    -> package（channel = 根目錄套件）
            module     -> package + file + db（module = 套件 + 檔案 + db 實體）
            skill      -> package（skill 層 = 套件 folder）
        階層 = root > package(module) > package(skill)，
        實體（file/db）只發生喺 module 層。
        資料來源：taxonomy.tree（ATTACH）+ structure_type 字典。
        冪等：已有 row 唔重插（WHERE NOT EXISTS）。
        """
        import sqlite3 as _sq
        # ATTACH taxonomy.db（tree 字典）
        try:
            self.conn.execute(
                "ATTACH DATABASE ? AS taxdb",
                (r"C:\projects\meta\taxonomy\taxonomy.db",))
        except Exception:
            pass  # 已 ATTACH
        # tree id 字典
        try:
            trees = {r["meta_key"]: r["id"] for r in self.conn.execute(
                "SELECT id, meta_key FROM taxdb.tree")}
        except Exception:
            trees = {}
        # structure_type id 字典
        stypes = {r["meta"]: r["id"] for r in self.conn.execute(
            "SELECT id, meta FROM structure_type")}
        rows = [
            ("channel", "package"),
            ("module", "package"),
            ("module", "file"),
            ("module", "db"),
            ("skill", "package"),
        ]
        for tree_meta, stype_meta in rows:
            tid = trees.get(tree_meta)
            sid = stypes.get(stype_meta)
            if not tid or not sid:
                continue
            self.conn.execute(
                "INSERT INTO structure_taxonomy (tree_id, structure_type_id)"
                " SELECT ?, ? WHERE NOT EXISTS"
                " (SELECT 1 FROM structure_taxonomy"
                "  WHERE tree_id = ? AND structure_type_id = ?)",
                (tid, sid, tid, sid))
        self.conn.commit()

    def _sync_positions(self):
        """確保 position 字典喺 common.db（本來喺 structure.db，已搬遷）

        2026-10-23：position 係跨 module 共用嘅字典（package 表次序 /
        欄位次序都用），中央化去 common.db。舊 structure.db position
        資料遷移過去，然後刪舊表。
        """
        import sqlite3 as _sq
        # common.db position 表存在？
        has_common = self.conn.execute(
            "SELECT 1 FROM cmmdb.sqlite_master WHERE type='table'"
            " AND name='position'").fetchone()
        if not has_common:
            # 確保 common.db 有 position 表（經 Common API 初始化）
            try:
                from common import Common
                c = Common()
                c.close()
            except Exception:
                pass
        # structure.db 舊 position 有資料 -> 搬（OR IGNORE）
        old = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
            " AND name='position'").fetchone()
        if old:
            try:
                # 舊 position 表（一次性搬遷）—— common 有資料就唔搬
                self.conn.execute(
                    "INSERT INTO cmmdb.position"
                    " (id, meta, is_active, created_at, updated_at)"
                    " SELECT id, meta, is_active, created_at, updated_at"
                    " FROM position"
                    " WHERE NOT EXISTS (SELECT 1 FROM cmmdb.position)")
                self.conn.commit()
            except _sq.Error:
                pass
        # 刪 structure.db 本地 position 表（避免混淆）
        if old and self.conn.execute(
                "SELECT COUNT(*) c FROM cmmdb.position"
        ).fetchone()["c"] > 0:
            self.conn.execute("DROP TABLE IF EXISTS position")
            self.conn.commit()

    def _parse_format(self, fmt):
        """拆 db_field_format.format（2026-10-25 rebuild：單一原子 token）-> dict

        format 係原子 token：primary_key / unique / auto_increment /
        NOW / NULL / localtime（一個 format 一個性質，唔係組合）。
        返回 {"type_name", "not_null", "is_primary_key", "is_unique",
              "auto_increment", "default_now", "default_localtime"}
        支援舊 pattern 名 alias（migration 時須轉換）。
        """
        # 舊 aliases（一次性轉換去新 token，migration 用）
        aliases = {
            "text_optional": "NULL",
            "int_optional": "NULL",
            "real_optional": "NULL",
            "bool_optional": "NULL",
            "datetime_optional": "NULL",
            "text_required": "",
            "text_unique": "unique",
            "datetime_required": "",
            "int_required_pk_unique_auto":
                "primary_key|unique|auto_increment",   # 舊組合（一次過拆散）
            "bool_required": "",
            "int_required": "",
            "real_required": "",
        }
        fmt = aliases.get(fmt, fmt)
        parts = (fmt or "").split("|")
        d = {"type_name": "TEXT",  # 型別唔喺 format；由 db_field_type 提供
             "not_null": 1, "is_primary_key": 0,
             "is_unique": 0, "auto_increment": 0,
             "default_now": 0, "default_localtime": 0}
        for p in parts:
            if not p:
                continue
            if p == "NULL":
                d["not_null"] = 0
            elif p == "primary_key":
                d["is_primary_key"] = 1
            elif p == "unique":
                d["is_unique"] = 1
            elif p == "auto_increment":
                d["auto_increment"] = 1
            elif p == "NOW":
                d["default_now"] = 1
            elif p == "localtime":
                d["default_localtime"] = 1
        return d

    def _format_id(self, format_str):
        """由 db_field_format.format（原子 token 或舊 pattern 名）查 id

        舊 pattern 名 -> alias 轉 token；冇 -> 自動建（冪等）。
        """
        aliases = {
            "text_optional": "NULL",
            "int_optional": "NULL",
            "real_optional": "NULL",
            "bool_optional": "NULL",
            "datetime_optional": "NULL",
            "text_required": "",
            "text_unique": "unique",
            "datetime_required": "",
            "int_required_pk_unique_auto":
                "primary_key|unique|auto_increment",
            "bool_required": "",
            "int_required": "",
            "real_required": "",
        }
        fmt = aliases.get(format_str, format_str)
        if fmt == "":
            fmt = "NOT NULL"  # required 舊名 -> NOT NULL token（自動建）
        r = self.conn.execute(
            "SELECT id FROM db_field_format WHERE format = ?",
            (fmt,)).fetchone()
        if r:
            return r["id"]
        # 冇 -> 自動建（冪等，唔燒 sqlite_sequence）
        self.conn.execute(
            "INSERT INTO db_field_format (format)"
            " SELECT ? WHERE NOT EXISTS"
            " (SELECT 1 FROM db_field_format WHERE format = ?)",
            (fmt, fmt))
        self.conn.commit()
        r = self.conn.execute(
            "SELECT id FROM db_field_format WHERE format = ?",
            (fmt,)).fetchone()
        return r["id"] if r else None

    def _migrate_position_to_seq(self):
        """遷移（幂等）：position_id 欄 -> seq_id（2026-10-27 用戶要求）

        2026-10-27：統一命名 position -> seq（配合 common.seq 字典 + template
        引擎嘅 seq 概念）。db_table_setting.position_id 欄名 RENAME 做 seq_id。
        值唔郁（同樣係 common.seq.id / common.position.id，id 兼容）。
        """
        cols = [c[1] for c in self.conn.execute(
            "PRAGMA table_info(db_table_setting)")]
        if "position_id" not in cols:
            return  # 已新版 / 冇舊欄
        if "seq_id" in cols:
            # 兩個欄都有（唔應該）-> drop 舊
            self.conn.execute(
                "ALTER TABLE db_table_setting DROP COLUMN position_id")
            self.conn.commit()
            return
        self.conn.execute(
            "ALTER TABLE db_table_setting RENAME COLUMN position_id TO seq_id")
        self.conn.commit()
        print("[structure] db_table_setting.position_id -> seq_id")

    def _migrate_db_table_setting(self):
        """遷移 db_table_setting 去最新版（通用模板：型別直接存）

        2026-10-23a：刪 connection / references_table / references_column /
        unique_group / position，加 position_id。
        2026-10-23b：刪 db_table_type_id，加 table_name（db_table_type 概念移除）。
        2026-10-23c：table_name 都刪——所有表共用同一組欄位
        （id / meta / created_at / updated_at / is_active）。
        2026-10-25：db_field_format_id -> db_field_type_id（型別直接存）。
        2026-10-27：position_id -> seq_id（用戶要求，_migrate_position_to_seq）。
        """
        cols = {c[1] for c in self.conn.execute(
            "PRAGMA table_info(db_table_setting)")}
        if "db_field_format_id" in cols:
            if "db_field_type_id" not in cols:
                self.conn.execute(
                    "ALTER TABLE db_table_setting"
                    " ADD COLUMN db_field_type_id INTEGER")
                self.conn.commit()
            rows = self.conn.execute(
                "SELECT id, db_field_format_id FROM db_table_setting").fetchall()
            for r in rows:
                if r["db_field_format_id"] is None:
                    continue
                tid = self._column_name_type_id(r["db_field_format_id"])
                if tid is None:
                    # 由 db_field_setting 反查（可能仲存在）
                    sr = self.conn.execute(
                        "SELECT db_field_type_id FROM db_field_setting"
                        " WHERE id = ?", (r["db_field_format_id"],)).fetchone()
                    if sr:
                        tid = sr["db_field_type_id"]
                if tid:
                    self.conn.execute(
                        "UPDATE db_table_setting SET db_field_type_id = ?"
                        " WHERE id = ?", (tid, r["id"]))
            self.conn.execute(
                "ALTER TABLE db_table_setting DROP COLUMN db_field_format_id")
            self.conn.commit()
            print("[structure] db_table_setting.db_field_format_id"
                  " -> db_field_type_id")

    def _sync_db_table_settings(self):
        """確保 db_table_setting 有齊標準通用模板（冪等，唔燒 sqlite_sequence）

        id / description / is_active / created_at / updated_at 五欄，
        型別直接存；性質 seed 到 db_field_property（直掛 db_table_setting.id）。
        """
        specs = [
            ("id", "INTEGER", 1),
            ("description", "TEXT", 2),
            ("is_active", "BOOLEAN", 3),
            ("created_at", "DATETIME", 4),
            ("updated_at", "DATETIME", 5),
        ]
        n = 0
        for meta_key, tmeta, pos in specs:
            tid = self.conn.execute(
                "SELECT id FROM db_field_type WHERE meta = ?",
                (tmeta,)).fetchone()
            if not tid:
                continue
            cur = self.conn.execute(
                "INSERT INTO db_table_setting"
                " (meta_key, db_field_type_id, seq_id)"
                " SELECT ?, ?, ? WHERE NOT EXISTS"
                " (SELECT 1 FROM db_table_setting WHERE meta_key = ?)",
                (meta_key, tid["id"], pos, meta_key))
            n += cur.rowcount
        self.conn.commit()
        return n

    def _migrate_table_definition(self):
        """遷移（幂等）：structure_db_table 舊版（table_name UNIQUE）-> 新版（db_file+table_name UNIQUE）

        2026-10-24：同名表可以喺唔同 DB；改成 (db_file, table_name)。
        （_migrate_new_names 已將 db_table_stucture rename 做 structure_db_table）
        """
        idxs = {r[1]: r for r in self.conn.execute(
            "PRAGMA index_list('structure_db_table')")}
        for name, row in idxs.items():
            if not name.startswith("sqlite_autoindex"):
                continue
            cols = [r[2] for r in self.conn.execute(
                f"PRAGMA index_info('{name}')")]
            if cols == ["db_file", "table_name"]:
                return  # 已新版
        rows = [dict(r) for r in self.conn.execute(
            "SELECT * FROM structure_db_table ORDER BY id")]
        self.conn.execute("DROP TABLE structure_db_table")
        self.conn.execute(DB_TABLE_STRUCTURE_DDL)
        for r in rows:
            self.conn.execute(
                "INSERT INTO structure_db_table"
                " (id, table_name, db_file, description, is_active,"
                "  created_at, updated_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?) ON CONFLICT(db_file, table_name)"
                " DO NOTHING",
                (r["id"], r["table_name"], r.get("db_file") or "unknown.db",
                 r.get("description"), r.get("is_active", 1),
                 r.get("created_at"), r.get("updated_at")))
        self.conn.commit()

    def db_field_formats(self, active_only=True):
        """列出欄位格式字典（db_field_format，原子 token）"""
        sql = "SELECT * FROM db_field_format"
        if active_only:
            sql += " WHERE is_active = 1"
        sql += " ORDER BY id"
        return [dict(r) for r in self.conn.execute(sql)]

    def _sync_db_field_types(self):
        """確保 db_field_type 有齊標準型別（冪等）

        新版 db_field_type：id | meta | description | default_value | is_active | created_at。
        標準型別（2026-10-25）：
            INTEGER/TEXT/BOOLEAN/DATETIME/REAL/BLOB/JSON/SLUG/DATE/TIME/UUID
        CHINESE/PYTHON/SQL 唔係型別（內容檢查係 db_field_check 嘅任務）。
        2026-10-26：default_value（有冇預設值概念）+ default_value 表 seed。
        """
        n = 0
        for meta, desc, has_default in DEFAULT_FIELD_TYPES:
            # 冪等：唔撞先插（唔燒 sqlite_sequence）
            cur = self.conn.execute(
                "INSERT INTO db_field_type (meta, description, default_value)"
                " SELECT ?, ?, ? WHERE NOT EXISTS"
                " (SELECT 1 FROM db_field_type WHERE meta = ?)",
                (meta, desc, has_default, meta))
            # 描述 + default_value 校正（code 權威）
            self.conn.execute(
                "UPDATE db_field_type SET description = ?"
                " WHERE meta = ? AND description != ?",
                (desc, meta, desc))
            self.conn.execute(
                "UPDATE db_field_type SET default_value = ?"
                " WHERE meta = ? AND default_value != ?",
                (has_default, meta, has_default))
            n += cur.rowcount
        self.conn.commit()
        # 2026-10-26：default_value 表 seed（型別 -> 實際預設值）
        self._seed_default_values()

    def _seed_default_values(self):
        """seed default_value 表（型別 id -> 預設值，冪等）

        用戶指定（2026-10-26）：
            id | db_field_type_id | value
            1 | 3  | 0     (BOOLEAN  -> 0)
            2 | 10 | NOW   (TIME     -> NOW)
            3 | 4  | NOW   (DATETIME -> NOW)
            4 | 9  | NOW   (DATE     -> NOW)
            5 | 7  | []    (JSON     -> [])
        用 meta 名反查 id（唔硬寫數字，避免錯位）。
        """
        meta_id = {}
        for r in self.conn.execute("SELECT id, meta FROM db_field_type"):
            meta_id[r["meta"]] = r["id"]
        for type_meta, value in [("BOOLEAN", "0"), ("TIME", "NOW"),
                                 ("DATETIME", "NOW"), ("DATE", "NOW"),
                                 ("JSON", "[]")]:
            tid = meta_id.get(type_meta)
            if not tid:
                continue
            self.conn.execute(
                "INSERT INTO default_value (db_field_type_id, value)"
                " SELECT ?, ? WHERE NOT EXISTS"
                " (SELECT 1 FROM default_value WHERE db_field_type_id = ?)",
                (tid, value, tid))
            # 值校正（code 權威）
            self.conn.execute(
                "UPDATE default_value SET value = ?"
                " WHERE db_field_type_id = ? AND value != ?",
                (value, tid, value))
        self.conn.commit()

    def _sync_db_field_xxxx(self):
        """（已廢棄 2026-10-25：db_field_setting 表已移除）
        db_field_property 字典 seed 見 _sync_db_field_properties。
        """
        has = self.conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table'"
            " AND name='db_field_setting'").fetchone()
        if not has:
            return 0
        """確保 db_field_setting 有正確本體（權威 rebuild，固定 id 1-6）

        2026-10-25：db_field_setting = 型別本體；
        性質（primary_key/unique/auto/NOT NULL）喺 db_field_property
        （多行性質，見 _sync_db_field_properties）。

        固定 id（權威）：
            1 = id         （INTEGER）    性質：pk/unique/auto/NOT NULL
            2 = required   （TEXT）       性質：NOT NULL
            3 = optional   （TEXT）       （冇性質）
            4 = is_active  （BOOLEAN）    性質：NOT NULL
            5 = created_at （DATETIME）   性質：localtime/NOT NULL
            6 = updated_at （DATETIME）   性質：localtime/NOT NULL
        """
        def _lookup(table, col, val):
            r = self.conn.execute(
                f"SELECT id FROM {table} WHERE {col} = ?", (val,)).fetchone()
            return r["id"] if r else None

        # 固定本體： (setting_id, type_meta)
        combos = [
            (1, "INTEGER"),
            (2, "TEXT"),
            (3, "TEXT"),
            (4, "BOOLEAN"),
            (5, "DATETIME"),
            (6, "DATETIME"),
        ]
        n = 0
        for sid, tmeta in combos:
            tid = _lookup("db_field_type", "meta", tmeta)
            if tid is None:
                continue
            r = self.conn.execute(
                "SELECT id FROM db_field_setting WHERE id = ?", (sid,)
            ).fetchone()
            if r:
                # 校正本體（code 權威）
                self.conn.execute(
                    "UPDATE db_field_setting SET db_field_type_id = ?"
                    " WHERE id = ?",
                    (tid, sid))
                n += 1
            else:
                cur = self.conn.execute(
                    "INSERT INTO db_field_setting"
                    " (id, db_field_type_id)"
                    " SELECT ?, ? WHERE NOT EXISTS"
                    " (SELECT 1 FROM db_field_setting WHERE id = ?)",
                    (sid, tid, sid))
                n += cur.rowcount
        # 刪唔喺權威列表嘅行（1-6 之外）
        cur = self.conn.execute(
            "DELETE FROM db_field_setting WHERE id NOT BETWEEN 1 AND 6")
        n += cur.rowcount
        self.conn.commit()
        return n

    # ---------- table_definition / table_column（2026-10-24 真表結構定義） ----------
    # 2026-10-26 redesign：by_id（channel_id + module_id + table_name）。
    #   舊 API（db_file 字串）保留兼容 —— 內部轉 by_id。
    def _module_pair_for_db(self, db_file):
        """db 檔名 -> (channel_id, module_id)（by taxonomy 權威）"""
        m = self._module_ids_by_db()
        return m.get(db_file)

    def _db_file_for_table(self, tid):
        """（兼容舊 API）新表 id -> db 檔名"""
        r = self.conn.execute(
            "SELECT table_name FROM structure_db_table WHERE id = ?",
            (tid,)).fetchone()
        if not r:
            return None
        try:
            import sqlite3 as _sq
            tc = _sq.connect(r"C:\projects\meta\taxonomy\taxonomy.db")
            tc.row_factory = _sq.Row
            try:
                rr = tc.execute(
                    "SELECT pp.full_path FROM physical_path pp"
                    " JOIN registry t ON t.id = pp.module_id"
                    " WHERE pp.tree_id = 2 AND pp.module = ?"
                    "  AND pp.full_path LIKE '%.db'",
                    (r["table_name"],)).fetchone()
                # 用 module_id 反查（physical_path.module 欄 = module 名）
                rr = tc.execute(
                    "SELECT pp.full_path FROM physical_path pp"
                    " WHERE pp.tree_id = 2 AND pp.full_path LIKE '%.db'"
                    " AND pp.module_id IN (SELECT id FROM registry"
                    "  WHERE tree_id = 2 AND is_active = 1)"
                    " LIMIT 1").fetchone() if not rr else rr
                return os.path.basename(rr["full_path"]) if rr else None
            finally:
                tc.close()
        except Exception:
            return None

    def table_definitions(self, active_only=True, channel_id=None,
                          module_id=None):
        """列出全部表定義（structure_db_table，含欄位清單）

        channel_id / module_id 可選篩選（by_id，2026-10-26）。
        """
        sql = "SELECT * FROM structure_db_table WHERE 1=1"
        args = []
        if channel_id is not None:
            sql += " AND channel_id = ?"
            args.append(channel_id)
        if module_id is not None:
            sql += " AND module_id = ?"
            args.append(module_id)
        if active_only:
            sql += " AND is_active = 1"
        rows = [dict(r) for r in self.conn.execute(
            sql + " ORDER BY id", args)]
        for r in rows:
            r["columns"] = self.table_columns(r["id"], active_only)
            # 兼容舊 caller：補 db_file（by module_id 反查）
            r["db_file"] = self._db_file_for_module(r["module_id"]) or ""
        return rows

    def add_db_table(self, channel_id, module_id, table_name,
                     description=None):
        """（新 API，by_id）登記一張真表（冪等）

        channel_id = taxonomy.tree.id（channel）
        module_id  = taxonomy.taxonomy.id（tree = module）
        """
        self.conn.execute(
            "INSERT INTO structure_db_table"
            " (channel_id, module_id, table_name, description)"
            " SELECT ?, ?, ?, ? WHERE NOT EXISTS"
            " (SELECT 1 FROM structure_db_table"
            "  WHERE channel_id = ? AND module_id = ? AND table_name = ?)",
            (channel_id, module_id, table_name, description or "",
             channel_id, module_id, table_name))
        self.conn.commit()
        r = self.conn.execute(
            "SELECT id FROM structure_db_table"
            " WHERE channel_id = ? AND module_id = ? AND table_name = ?",
            (channel_id, module_id, table_name)).fetchone()
        return r["id"] if r else None

    def add_db_field_by_table(self, table_id, field_name, description=None):
        """（新 API，by_id）登記一個真欄位（冪等）"""
        self.conn.execute(
            "INSERT INTO structure_db_field"
            " (structure_db_table_id, field_name, description)"
            " SELECT ?, ?, ? WHERE NOT EXISTS"
            " (SELECT 1 FROM structure_db_field"
            "  WHERE structure_db_table_id = ? AND field_name = ?)",
            (table_id, field_name, description or "",
             table_id, field_name))
        self.conn.commit()
        r = self.conn.execute(
            "SELECT id FROM structure_db_field"
            " WHERE structure_db_table_id = ? AND field_name = ?",
            (table_id, field_name)).fetchone()
        return r["id"] if r else None

    def _table_definitions_impl(self, active_only=True):
        """實作（改名避開重複）—— 揾唔到就唔好撞名"""
        return self.table_definitions(active_only)

    def table_definition(self, db_file, table_name, active_only=True):
        """攞一個表定義（by db_file + table_name，兼容舊 API）

        db_file = db 檔名（question.db / terminology.db），內部轉 by_id。
        """
        pair = self._module_pair_for_db(db_file)
        if not pair:
            return None
        channel_id, module_id = pair
        r = self.conn.execute(
            "SELECT * FROM structure_db_table"
            " WHERE channel_id = ? AND module_id = ? AND table_name = ?",
            (channel_id, module_id, table_name)).fetchone()
        if not r or (active_only and not r["is_active"]):
            return None
        d = dict(r)
        d["db_file"] = db_file
        d["columns"] = self.table_columns(d["id"], active_only)
        return d

    def _db_file_for_module(self, module_id):
        """module_id（taxonomy.id）-> db 檔名（physical_path 權威）"""
        try:
            import sqlite3 as _sq
            tc = _sq.connect(r"C:\projects\meta\taxonomy\taxonomy.db")
            tc.row_factory = _sq.Row
            try:
                # physical_path.module = module 名（registry.meta）
                r = tc.execute(
                    "SELECT pp.full_path FROM physical_path pp"
                    " JOIN registry t ON t.meta = pp.module"
                    "  AND t.tree_id = 2 AND t.is_active = 1"
                    " WHERE t.id = ? AND pp.tree_id = 2"
                    " AND pp.full_path LIKE '%.db'"
                    " ORDER BY pp.id LIMIT 1",
                    (module_id,)).fetchone()
                if r:
                    return os.path.basename(r["full_path"])
            finally:
                tc.close()
        except Exception:
            pass
        return None

    def add_table_definition(self, table_name, db_file, description=None,
                             module_scope=0, channel_id=None, module_id=None):
        """登記一張表（冪等，channel_id + module_id + table_name unique）

        db_file = db 檔名（question.db）——由 taxonomy 權威反查 module。
        2026-10-26：module_scope 保留兼容（新表冇呢個概念，忽略）。
        channel_id / module_id 傳入就唔用 db_file 反查（by_id）。
        """
        if channel_id is None or module_id is None:
            pair = self._module_pair_for_db(db_file)
            if not pair:
                raise ValueError(f"db_file 冇對應 module: {db_file}")
            channel_id, module_id = pair
        self.conn.execute(
            "INSERT INTO structure_db_table"
            " (channel_id, module_id, table_name, description)"
            " SELECT ?, ?, ?, ? WHERE NOT EXISTS"
            " (SELECT 1 FROM structure_db_table"
            "  WHERE channel_id = ? AND module_id = ? AND table_name = ?)",
            (channel_id, module_id, table_name, description or "",
             channel_id, module_id, table_name))
        self.conn.commit()
        r = self.conn.execute(
            "SELECT id FROM structure_db_table"
            " WHERE channel_id = ? AND module_id = ? AND table_name = ?",
            (channel_id, module_id, table_name)).fetchone()
        return r["id"] if r else None

    def _default_for(self, db_field_type_id):
        """由 default_value 表攞呢個型別嘅預設值（冇 = None）

        2026-10-26（用戶要求）：default 由表定義（唔係 code if/else）。
        value -> SQL 片段 mapping（唯一留喺 code 嘅語法位）：
            NOW    -> datetime('now')
            其他   -> 原樣（0 / [] / 'untitled' ...）
        """
        if not db_field_type_id:
            return None
        row = self.conn.execute(
            "SELECT value FROM default_value"
            " WHERE db_field_type_id = ? AND is_active = 1",
            (db_field_type_id,)).fetchone()
        if not row:
            return None
        v = row["value"]
        if v == "NOW":
            return "datetime('now')"
        return v

    # ---------- default_value 管理（2026-10-26：表驅動，唔寫 code） ----------
    def default_values(self, active_only=True):
        """列出全部 default_value（JOIN 型別名）"""
        sql = """SELECT dv.id, dv.db_field_type_id, t.meta AS type_name,
                        dv.value, dv.is_active, dv.created_at, dv.updated_at
                 FROM default_value dv
                 LEFT JOIN db_field_type t ON t.id = dv.db_field_type_id"""
        if active_only:
            sql += " WHERE dv.is_active = 1"
        sql += " ORDER BY dv.id"
        return [dict(r) for r in self.conn.execute(sql)]

    def add_default_value(self, db_field_type_id, value):
        """登記一個型別嘅預設值（冪等：同 type 更新，唔重複行）

        同時將 db_field_type.default_value 標記 = 1（呢個型別有預設）。
        返回 default_value 行 id。
        """
        if not db_field_type_id:
            raise ValueError("db_field_type_id 必填")
        if value is None or str(value) == "":
            raise ValueError("value 必填（例如 0 / NOW / [] / 'untitled'）")
        self.conn.execute(
            "INSERT INTO default_value (db_field_type_id, value)"
            " SELECT ?, ? WHERE NOT EXISTS"
            " (SELECT 1 FROM default_value WHERE db_field_type_id = ?)",
            (db_field_type_id, str(value), db_field_type_id))
        self.conn.execute(
            "UPDATE default_value SET value = ?"
            " WHERE db_field_type_id = ? AND value != ?",
            (str(value), db_field_type_id, str(value)))
        self.conn.execute(
            "UPDATE db_field_type SET default_value = 1"
            " WHERE id = ? AND default_value != 1", (db_field_type_id,))
        self.conn.commit()
        r = self.conn.execute(
            "SELECT id FROM default_value WHERE db_field_type_id = ?",
            (db_field_type_id,)).fetchone()
        return r["id"] if r else None

    def remove_default_value(self, db_field_type_id):
        """移除一個型別嘅預設值（冪等）

        同時將 db_field_type.default_value 標記 = 0。
        返回 True = 真刪到。
        """
        cur = self.conn.execute(
            "DELETE FROM default_value WHERE db_field_type_id = ?",
            (db_field_type_id,))
        self.conn.execute(
            "UPDATE db_field_type SET default_value = 0"
            " WHERE id = ? AND default_value != 0", (db_field_type_id,))
        self.conn.commit()
        return cur.rowcount > 0

    def table_columns(self, db_table_stucture_id, active_only=True):
        """列出一個表定義嘅欄位（按 id 排序）

        2026-10-26 redesign：淨結構描述（field_name + description）。
        型別由 db_table_setting 通用模板（按 column_name 對應）補充，
        冇對應 -> TEXT（型別權威 = resource.db db_field 實例）。
        """
        sql = """SELECT tc.id, tc.field_name,
                        tc.db_field_check_id,
                        tc.description, tc.is_active, tc.created_at
                 FROM structure_db_field tc
                 WHERE tc.structure_db_table_id = ?"""
        args = (db_table_stucture_id,)
        if active_only:
            sql += " AND tc.is_active = 1"
        sql += " ORDER BY tc.id"
        rows = [dict(r) for r in self.conn.execute(sql, args)]
        # 型別 + 性質補充：db_table_setting 通用模板（column_name -> type）
        # + 預設性質（id=pk / is_active=NOT NULL / created_at=NOW ...）
        type_by_name = {}
        type_id_by_name = {}
        prop_by_name = {}
        try:
            for r in self.conn.execute(
                    "SELECT d.meta_key, ft.meta AS type_name,"
                    " d.db_field_type_id"
                    " FROM db_table_setting d"
                    " LEFT JOIN db_field_type ft ON ft.id = d.db_field_type_id"
                    " WHERE d.is_active = 1"):
                type_by_name[r["meta_key"]] = r["type_name"] or "TEXT"
                type_id_by_name[r["meta_key"]] = r["db_field_type_id"]
            # 性質：db_table_setting 冇掛 property -> 用 _default_property_id
            # 對應 format token（有才補）
            for r in self.conn.execute("SELECT meta_key FROM db_table_setting"):
                pid = self._default_property_id(r["meta_key"])
                if pid:
                    prop_by_name[r["meta_key"]] = pid
        except Exception:
            pass
        for d in rows:
            d["column_name"] = d["field_name"]
            d["type_name"] = type_by_name.get(d["field_name"], "TEXT")
            d["db_field_type_id"] = type_id_by_name.get(d["field_name"])
            props = []
            pid = prop_by_name.get(d["field_name"])
            if pid:
                props = [x[0] for x in self.conn.execute(
                    """SELECT ff.format FROM db_field_property pr
                       JOIN db_field_format ff ON ff.id = pr.db_field_format_id
                       WHERE pr.id = ?""", (pid,))]
            # SQLite 語意：primary_key 隱含 unique + NOT NULL + auto
            is_pk = 1 if "primary_key" in props else 0
            is_uniq = 1 if ("unique" in props or is_pk) else 0
            is_nn = 1 if ("NOT NULL" in props or is_pk) else 0
            is_ai = 1 if ("auto_increment" in props or is_pk) else 0
            d["not_null"] = is_nn
            d["is_primary_key"] = is_pk
            d["is_unique"] = is_uniq
            d["auto_increment"] = is_ai
            d["_props"] = props
            d["unique"] = is_uniq
        return rows

    def db_fields(self, db_table_stucture_id, active_only=True):
        """（新名）列出一個表定義嘅欄位 —— alias of table_columns"""
        return self.table_columns(db_table_stucture_id, active_only)

    def add_db_field(self, db_file, table_name, column_name, setting_pattern,
                     position_id=None, description=None):
        """（新名）加一欄去一個表定義 —— alias of add_table_column"""
        return self.add_table_column(
            db_file, table_name, column_name, setting_pattern,
            position_id=position_id, description=description)

    def add_table_column(self, db_file, table_name, column_name, setting_pattern,
                         position_id=None, description=None):
        """加一欄去一個表定義（冪等：structure_db_table_id + field_name）

        2026-10-26 redesign：淨存 field_name + description；
        setting_pattern / position_id 保留兼容（忽略，型別由 resource 管）。
        """
        pair = self._module_pair_for_db(db_file)
        if not pair:
            raise ValueError(f"db_file 冇對應 module: {db_file}")
        channel_id, module_id = pair
        tdef = self.conn.execute(
            "SELECT id FROM structure_db_table"
            " WHERE channel_id = ? AND module_id = ? AND table_name = ?",
            (channel_id, module_id, table_name)).fetchone()
        if not tdef:
            raise ValueError(
                f"表定義唔存在: {db_file}.{table_name}（先 add_table_definition）")
        self.conn.execute(
            "INSERT INTO structure_db_field"
            " (structure_db_table_id, field_name, description)"
            " SELECT ?, ?, ? WHERE NOT EXISTS"
            " (SELECT 1 FROM structure_db_field"
            "  WHERE structure_db_table_id = ? AND field_name = ?)",
            (tdef["id"], column_name, description or "",
             tdef["id"], column_name))
        self.conn.commit()
        r = self.conn.execute(
            "SELECT id FROM structure_db_field"
            " WHERE structure_db_table_id = ? AND field_name = ?",
            (tdef["id"], column_name)).fetchone()
        return r["id"] if r else None

    def _default_property_id(self, column_name):
        """按欄位名攞預設 db_field_property.id（冇 -> None）

        權威 mapping（2026-10-25）：id=INTEGER×pk、meta_key=INTEGER×unique、
        description=TEXT×NOT NULL、is_active=BOOLEAN×NOT NULL、
        created_at=DATETIME×NOW、updated_at=DATETIME×localtime。
        """
        tmeta = {
            "id": "INTEGER", "meta_key": "INTEGER", "seq": "INTEGER",
            "description": "TEXT", "is_active": "BOOLEAN",
            "created_at": "DATETIME", "updated_at": "DATETIME",
        }.get(column_name)
        fmt = {
            "id": "primary_key", "meta_key": "unique", "seq": "NOT NULL",
            "description": "NOT NULL", "is_active": "NOT NULL",
            "created_at": "NOW", "updated_at": "localtime",
        }.get(column_name)
        if not tmeta or not fmt:
            return None
        r = self.conn.execute(
            "SELECT pr.id FROM db_field_property pr"
            " JOIN db_field_type ft ON ft.id = pr.db_field_type_id"
            " JOIN db_field_format ff ON ff.id = pr.db_field_format_id"
            " WHERE ft.meta = ? AND ff.format = ?",
            (tmeta, fmt)).fetchone()
        return r["id"] if r else None

    def _template_props(self, meta_key, type_id):
        """db_table_setting 通用模板嘅性質（由 dict 查，唔再掛行）

        meta_key = 欄位名（id/description/is_active/created_at/updated_at）
        type_id  = db_field_type.id
        返回 format token 清單（例如 ['primary_key', 'unique', ...]）。
        """
        main_fmt = {
            "id": "primary_key", "meta_key": "unique", "seq": "NOT NULL",
            "description": "NOT NULL", "is_active": "NOT NULL",
            "created_at": "NOW", "updated_at": "localtime",
        }.get(meta_key)
        if not main_fmt:
            return []
        # property 字典：type×format 存在先算
        r = self.conn.execute(
            "SELECT 1 FROM db_field_property"
            " WHERE db_field_type_id = ?"
            " AND db_field_format_id ="
            " (SELECT id FROM db_field_format WHERE format = ?)",
            (type_id, main_fmt)).fetchone()
        if not r:
            return []
        props = [main_fmt]
        # 加 implicit 性質（id 加 pk/unique/auto；時間加 NOT NULL）
        if meta_key == "id":
            props = ["primary_key", "auto_increment"]
        elif meta_key in ("created_at", "updated_at"):
            props = [main_fmt, "NOT NULL"]
        return props

    def table_setting_pattern_id(self, pattern):
        """由欄位名 / format 攞 db_field_type.id（型別 id；唔存在 None）

        2026-10-25：column_name 優先查 db_field_unique（欄位名描述字典），
        對應唔到先 fallback token->型別。
        """
        try:
            r = self.conn.execute(
                "SELECT id FROM db_field_unique WHERE value = ?",
                (pattern,)).fetchone()
            if r:
                # 欄位名對應固定型別
                meta = {
                    "id": "INTEGER", "meta_key": "TEXT",
                    "is_active": "BOOLEAN", "created_at": "DATETIME",
                    "updated_at": "DATETIME",
                }.get(pattern)
                if not meta:
                    return None
                tr = self.conn.execute(
                    "SELECT id FROM db_field_type WHERE meta = ?",
                    (meta,)).fetchone()
                return tr["id"] if tr else None
            return self._type_id(pattern)
        except Exception:
            return None

    def _type_id(self, pattern):
        """由型別名 / format token 查 db_field_type.id（唔存在 None）"""
        # 直接型別名
        r = self.conn.execute(
            "SELECT id FROM db_field_type WHERE meta = ?",
            (pattern,)).fetchone()
        if r:
            return r["id"]
        # 舊 pattern 名 alias -> 型別
        alias_type = {
            "text_optional": "TEXT", "text_required": "TEXT",
            "text_unique": "TEXT",
            "int_optional": "INTEGER", "int_required": "INTEGER",
            "real_optional": "REAL", "real_required": "REAL",
            "bool_optional": "BOOLEAN", "bool_required": "BOOLEAN",
            "datetime_optional": "DATETIME",
            "datetime_required": "DATETIME",
            "int_required_pk_unique_auto": "INTEGER",
            "NULL": None, "primary_key": None, "unique": None,
            "auto_increment": None, "NOW": None, "localtime": None,
            "NOT NULL": None,
        }
        meta = alias_type.get(pattern)
        if not meta:
            return None
        r = self.conn.execute(
            "SELECT id FROM db_field_type WHERE meta = ?",
            (meta,)).fetchone()
        return r["id"] if r else None

    def db_field_uniques(self, active_only=True):
        """列出 unique 欄位名字典（db_field_unique）

        2026-10-25 rebuild 2：id + value（冇 is_active 欄）。
        """
        sql = "SELECT * FROM db_field_unique WHERE 1=1"
        sql += " ORDER BY id"
        return [dict(r) for r in self.conn.execute(sql)]

    def db_field_xxxxs(self, active_only=True):
        """列出欄位規格（structure_db_field，舊名 alias）

        db_field_settings 個名已讓畀「欄位設定字典」（db_field_setting 表，
        2026-10-26 用戶要求）。呢個方法直接讀真表欄位。
        """
        sql = """SELECT tc.id, tc.structure_db_table_id,
                        tc.field_name AS column_name, tc.description,
                        tc.db_field_unique_id, tc.db_field_check_id
                 FROM structure_db_field tc
                 WHERE 1=1"""
        if active_only:
            sql += " AND tc.is_active = 1"
        sql += " ORDER BY tc.id"
        rows = [dict(r) for r in self.conn.execute(sql)]
        uniq = {r["id"]: r["value"] for r in self.conn.execute(
            "SELECT id, value FROM db_field_unique")}
        for d in rows:
            d["unique_name"] = uniq.get(d["db_field_unique_id"])
            d["type_name"] = "TEXT"
            d["properties"] = []
        return rows

    def db_field_checks(self, db_field_stucture_id=None, active_only=True):
        """列出 CHECK 約束（db_field_check，2026-10-26 redesign）

        新格式：id | structure_db_table_id | structure_db_field_id | total | json。
        每行 = 一個真表欄位嘅真實值域。
        """
        sql = """SELECT c.id, c.structure_db_table_id,
                        c.structure_db_field_id, c.total, c.json,
                        f.field_name
                 FROM db_field_check c
                 LEFT JOIN structure_db_field f
                        ON f.id = c.structure_db_field_id
                 WHERE 1=1"""
        args = ()
        conds = []
        if db_field_stucture_id:
            conds.append("c.structure_db_field_id = ?")
            args = args + (db_field_stucture_id,)
        if conds:
            sql += " AND " + " AND ".join(conds)
        sql += " ORDER BY c.id"
        try:
            return [dict(r) for r in self.conn.execute(sql, args)]
        except Exception:
            return []

    def add_db_field_check(self, db_field_stucture_id, boolean_id=None, json=None):
        """加一個 CHECK 約束（冪等：structure_db_field_id）

        2026-10-26 redesign：一行 = 一個真表欄位嘅值域。
        json 冇傳 -> 由真資料推導（_sync_db_field_checks 全站掃描）。
        """
        if json is None:
            return self._sync_db_field_checks()
        # 揾 structure_db_field 嘅所屬表
        r = self.conn.execute(
            "SELECT structure_db_table_id FROM structure_db_field WHERE id = ?",
            (db_field_stucture_id,)).fetchone()
        if not r:
            return None
        try:
            vals = json  # 傳入已係 list -> 直接
        except Exception:
            return None
        total = len(vals)
        j = json.dumps(vals) if not isinstance(json, str) else json
        # 真實值 -> total 一致
        cur = self.conn.execute(
            "INSERT INTO db_field_check"
            " (structure_db_table_id, structure_db_field_id, total, json)"
            " SELECT ?, ?, ?, ? WHERE NOT EXISTS"
            " (SELECT 1 FROM db_field_check WHERE structure_db_field_id = ?)",
            (r["structure_db_table_id"], db_field_stucture_id, total, j,
             db_field_stucture_id))
        self.conn.commit()
        return cur.lastrowid if cur.rowcount else None

    def _unique_name_for(self, column_name):
        """column_name -> db_field_unique 檢索（冇 -> 原字串）

        2026-10-25（用戶）：CHECK formula 用 <db_field_unique_id> placeholder，
        執行時由 column_name 反查 db_field_unique.id；搵唔到就當欄位名。
        """
        r = self.conn.execute(
            "SELECT id FROM db_field_unique WHERE value = ?",
            (column_name,)).fetchone()
        if r:
            # 有對應 unique id -> 用欄位名（公式 placeholder 代表「欄位名」）
            return column_name
        return column_name

    def generate_table_ddl(self, db_file, table_name):
        """由 table_definition 生成一張表嘅 CREATE TABLE DDL

        db_file    = 邊個 DB（question.db / terminology.db...）
        table_name = 表名（question / test ...）
        有 table_definition 定義 -> 用定義（table_column JOIN pattern）
        冇定義 -> fallback db_table_setting 通用模板（5 欄）

        返回 CREATE TABLE 字串；生成唔到 -> 空字串。
        """
        from .function import build_column_definitions

        # SQLite 實際存法：DATETIME/DATE/TIME/UUID 存做 TEXT（真表全部用 TEXT）
        _SQL_TYPE_MAP = {"DATETIME": "TEXT", "DATE": "TEXT",
                         "TIME": "TEXT", "UUID": "TEXT"}

        def _sql_type(t):
            return _SQL_TYPE_MAP.get(t, t)

        def _quoted(name):
            if name[0].isdigit() or not name.replace("_", "").isalnum():
                return f'"{name}"'
            return name

        tdef = None
        if db_file:
            pair = self._module_pair_for_db(db_file)
            if pair:
                tdef = self.conn.execute(
                    "SELECT * FROM structure_db_table"
                    " WHERE channel_id = ? AND module_id = ?"
                    "  AND table_name = ? AND is_active = 1",
                    (pair[0], pair[1], table_name)).fetchone()
        if tdef:
            cols = self.table_columns(tdef["id"])
            # CHECK 值域（db_field_check；json = 真實值清單，by structure_db_field_id）
            check_map = {}
            for ck in self.db_field_checks():
                # 每個真欄位嘅 check -> 記低 json 允許值
                if ck.get("structure_db_field_id"):
                    check_map[ck["structure_db_field_id"]] = ck.get("json")
            # option 值域（option.db table_field_option，按 structure_db_field_id）
            # 2026-10-25：option 表定義「field ABC 嘅允許值」-> 生成 CHECK
            option_map = {}
            try:
                import sqlite3 as _sq3
                _oc = _sq3.connect(
                    f"file:{r'C:\projects\meta\option\option.db'}?mode=ro", uri=True)
                _oc.row_factory = _sq3.Row
                for orow in _oc.execute(
                        "SELECT structure_db_field_id, value"
                        " FROM table_field_option"
                        " WHERE structure_db_field_id IS NOT NULL"
                        " AND is_active = 1 ORDER BY id"):
                    option_map.setdefault(
                        orow["structure_db_field_id"], []).append(orow["value"])
                _oc.close()
            except Exception:
                pass
            settings = []
            # DDL 生成規則（value 表；2026-10-25 用戶要求 formula 入表）
            check_formula = None
            for v in self.values():
                if v.get("type") == "check" and v.get("formula"):
                    check_formula = v["formula"]
                    break
            for c in cols:
                import json as _json
                props = c.get("_props") or []
                # check 值域優先次序：option 表（field id）> db_field_check.json
                # 生成方式：value.formula 模板 -> 填 placeholder
                chk = None
                opt_vals = option_map.get(c.get("id"))
                if opt_vals:
                    # option 值 -> 填公式（<db_field_unique_id> 反查欄位名）
                    qvals = []
                    for v in opt_vals:
                        try:
                            fv = _json.loads(v)  # 數字 -> 唔加引號
                            qvals.append(str(fv))
                        except Exception:
                            qvals.append(f"'{v}'")
                    if check_formula:
                        chk = check_formula \
                            .replace("<db_field_unique_id>",
                                     self._unique_name_for(c["column_name"])) \
                            .replace("<db_field_check.json_id>",
                                     ", ".join(qvals))
                    else:
                        chk = f"{c['column_name']} IN ({', '.join(qvals)})"
                elif c.get("id") in check_map:
                    j = check_map[c["id"]]
                    if j:
                        try:
                            vals = _json.loads(j)
                            # 字串值 -> 加引號；數字 -> 唔加
                            qvals = []
                            for v in vals:
                                if isinstance(v, str):
                                    qvals.append(f"'{v}'")
                                else:
                                    qvals.append(str(v))
                            val_str = ", ".join(qvals)
                            if check_formula:
                                chk = check_formula \
                                    .replace(
                                        "<db_field_unique_id>",
                                        self._unique_name_for(
                                            c["column_name"])) \
                                    .replace(
                                        "<db_field_check.json_id>", val_str)
                            else:
                                chk = f"{c['column_name']} IN ({val_str})"
                        except Exception:
                            chk = None
                    else:
                        chk = f"{c['column_name']} IN (0, 1)"
                # 預設值：由 default_value 表話事（2026-10-26，取代 if/else）
                dv = self._default_for(c.get("db_field_type_id"))
                settings.append({
                    "meta_key": c["column_name"],
                    "type_name": _sql_type(c["type_name"] or "TEXT"),
                    "not_null": c["not_null"],
                    "is_pk": c["is_primary_key"],
                    "is_unique": c["is_unique"] and not c["is_primary_key"],
                    "unique": c["is_unique"] and not c["is_primary_key"],
                    "auto_increment": c["auto_increment"],
                    "check_expr": chk,
                    "default_value": dv,
                })
            if settings:
                col_ddl = build_column_definitions(settings)
                return (f"CREATE TABLE IF NOT EXISTS {_quoted(table_name)} (\n"
                        f"    {col_ddl}\n)")
        # fallback：通用模板（db_table_setting）
        cols = self.conn.execute(
            """SELECT d.meta_key, d.id AS ts_id,
                      ft.meta AS type_name, d.db_field_type_id
               FROM db_table_setting d
               LEFT JOIN db_field_type ft ON ft.id = d.db_field_type_id
               WHERE d.is_active = 1
               ORDER BY d.seq_id""").fetchall()
        settings = []
        for c in cols:
            props = self._template_props(c["meta_key"], c["db_field_type_id"])
            dv = self._default_for(c["db_field_type_id"])
            settings.append({
                "meta_key": c["meta_key"],
                "type_name": _sql_type(c["type_name"] or "TEXT"),
                "not_null": 1 if "NOT NULL" in props else 0,
                "is_pk": 1 if "primary_key" in props else 0,
                "is_unique": 1 if "unique" in props else 0,
                "auto_increment": 1 if "auto_increment" in props else 0,
                "check_expr": None,
                "default_value": dv,
            })
        if not settings:
            return ""
        col_ddl = build_column_definitions(settings)
        return (f"CREATE TABLE IF NOT EXISTS {_quoted(table_name)} (\n"
                f"    {col_ddl}\n)")

    def db_table_settings(self, active_only=True):
        """列出通用欄位模板（db_table_setting）"""
        sql = "SELECT * FROM db_table_setting"
        args = ()
        conds = []
        if active_only:
            conds.append("is_active = 1")
        if conds:
            sql += " WHERE " + " AND ".join(conds)
        sql += " ORDER BY seq_id, id"
        return [dict(r) for r in self.conn.execute(sql, args)]

    def add_db_table_setting(self, meta_key,
                             db_field_format_id, seq_id=None):
        """加一個通用欄位定義（冪等）

        meta_key            = 欄位名（id / meta / created_at ...）
        db_field_format_id  = db_field_type.id（型別）／format token（alias）
        seq_id              = common.seq.id（欄位次序）
        2026-10-25：型別直接存；性質按 meta_key 自動 seed（db_field_property）。
        """
        tid = self._type_id(db_field_format_id)
        if tid is None:
            raise ValueError(f"型別唔存在: {db_field_format_id}")
        # 冪等：唔撞先插（唔燒 sqlite_sequence）
        self.conn.execute(
            "INSERT INTO db_table_setting"
            " (meta_key, db_field_type_id, seq_id)"
            " SELECT ?, ?, ? WHERE NOT EXISTS"
            " (SELECT 1 FROM db_table_setting WHERE meta_key = ?)",
            (meta_key, tid, seq_id, meta_key))
        self.conn.commit()
        r = self.conn.execute(
            "SELECT id FROM db_table_setting WHERE meta_key = ?",
            (meta_key,)).fetchone()
        return r["id"] if r else None

    def _seed_properties_for(self, field_id, column_name):
        """按欄位名 seed 性質（冪等）

        2026-10-25 rebuild 2：db_field_property 係字典（type×format），
        欄位用 db_field_property_id 指住——呢個函數回填 column_name 對應嘅
        property_id（field_id = structure_db_field.id 或 db_table_setting.id）。
        """
        tmeta = {
            "id": "INTEGER", "meta_key": "INTEGER", "seq": "INTEGER",
            "description": "TEXT", "is_active": "BOOLEAN",
            "created_at": "DATETIME", "updated_at": "DATETIME",
        }.get(column_name)
        fmt = {
            "id": "primary_key", "meta_key": "unique", "seq": "NOT NULL",
            "description": "NOT NULL", "is_active": "NOT NULL",
            "created_at": "NOT NULL", "updated_at": "NOT NULL",
        }.get(column_name)
        if not tmeta or not fmt:
            return None
        r = self.conn.execute(
            "SELECT pr.id FROM db_field_property pr"
            " JOIN db_field_type ft ON ft.id = pr.db_field_type_id"
            " JOIN db_field_format ff ON ff.id = pr.db_field_format_id"
            " WHERE ft.meta = ? AND ff.format = ?",
            (tmeta, fmt)).fetchone()
        if not r:
            return None
        try:
            self.conn.execute(
                "UPDATE structure_db_field SET db_field_property_id = ?"
                " WHERE id = ? AND db_field_property_id IS NULL",
                (r["id"], field_id))
        except Exception:
            pass
        self.conn.commit()
        return r["id"]

    def set_position(self, setting_id, seq_id):
        """設定一個欄位定義嘅次序（by_id）

        setting_id = db_table_setting.id
        seq_id = common.seq.id（欄位次序；None = 排最後）
        """
        self.conn.execute(
            "UPDATE db_table_setting SET seq_id = ?,"
            " updated_at = datetime('now', 'localtime') WHERE id = ?",
            (seq_id, setting_id))
        self.conn.commit()
        return self.conn.execute(
            "SELECT seq_id FROM db_table_setting WHERE id = ?",
            (setting_id,)).fetchone() is not None

    def positions(self, active_only=True):
        """列出位置字典（seq 喺 common.db，2026-10-23 中央化；
        2026-10-27 position -> seq）"""
        sql = "SELECT * FROM cmmdb.seq"
        if active_only:
            sql += " WHERE is_active = 1"
        sql += " ORDER BY CAST(meta AS INTEGER), id"
        return [dict(r) for r in self.conn.execute(sql)]

    def seqs(self, active_only=True):
        """列出 seq 字典（common.db，2026-10-27 用戶要求）"""
        return self.positions(active_only)

    def data_types(self, status=None):
        """列出欄位規格字典（db_field_property JOIN type + format）

        2026-10-25 rebuild 2：db_field_property = 字典（type×format）。
        status 參數保留相容（冇 status 欄 -> 忽略）。
        """
        sql = """SELECT pr.id, pr.db_field_type_id,
                        ft.meta AS type_name,
                        ff.format AS format
                 FROM db_field_property pr
                 LEFT JOIN db_field_type ft ON ft.id = pr.db_field_type_id
                 LEFT JOIN db_field_format ff ON ff.id = pr.db_field_format_id
                 WHERE 1=1"""
        args = ()
        if status:
            pass
        sql += " ORDER BY pr.id"
        rows = [dict(r) for r in self.conn.execute(sql, args)]
        for d in rows:
            d["properties"] = [d["format"]] if d.get("format") else []
            d["unique"] = 1 if d.get("format") == "unique" else 0
        return rows

    # 狀態管理（2026-10-25：db_field_type 已移除，保留空殼相容）
    def set_type_status(self, type_id, status):
        """（已廢棄）db_field_type 由 db_field_setting 取代"""
        return 0

    def cleanup_types(self, status="dead"):
        """（已廢棄）db_field_type 由 db_field_setting 取代"""
        return 0

    # ============ structure_type（2026-10-25：由 definition 搬入） ============
    def structure_types(self, active_only=True):
        """列出實體類型字典（1=package 2=file 3=db_table 4=db_field 5=db 6=root）"""
        sql = "SELECT * FROM structure_type WHERE 1=1"
        args = ()
        if active_only:
            sql += " AND is_active = 1"
        sql += " ORDER BY id"
        return [dict(r) for r in self.conn.execute(sql, args)]

    def structure_addresses(self, active_only=True):
        """列出實體地址（3 張分層表：root/module/skill）

        JOIN structure_type（實體類型名）。每行有自己層表 id + 父鍵。
        """
        stypes = {r["id"]: r["meta"] for r in self.conn.execute(
            "SELECT id, meta FROM structure_type")}
        rows = []
        cond = "WHERE is_active = 1" if active_only else ""
        for r in self.conn.execute(f"SELECT *, 'root' AS lvl"
                                   f" FROM structure_root {cond}"
                                   f" ORDER BY id"):
            d = dict(r)
            d["level"] = "root"
            d["structure_type"] = stypes.get(d["structure_type_id"], "?")
            rows.append(d)
        for r in self.conn.execute(f"SELECT *, 'module' AS lvl"
                                   f" FROM structure_module {cond}"
                                   f" ORDER BY id"):
            d = dict(r)
            d["level"] = "module"
            d["structure_type"] = stypes.get(d["structure_type_id"], "?")
            rows.append(d)
        for r in self.conn.execute(f"SELECT *, 'skill' AS lvl"
                                   f" FROM structure_skill {cond}"
                                   f" ORDER BY id"):
            d = dict(r)
            d["level"] = "skill"
            d["structure_type"] = stypes.get(d["structure_type_id"], "?")
            rows.append(d)
        return rows

    def structure_taxonomies(self, active_only=True):
        """列出樹層 ↔ 實體類型映射（structure_taxonomy）

        JOIN taxonomy.tree（層名）+ structure_type（實體類型名）。
        """
        tmap = {}
        try:
            tmap = {r["id"]: r["meta_key"] for r in self.conn.execute(
                "SELECT id, meta_key FROM taxdb.tree")}
        except Exception:
            pass
        stypes = {r["id"]: r["meta"] for r in self.conn.execute(
            "SELECT id, meta FROM structure_type")}
        sql = "SELECT * FROM structure_taxonomy WHERE 1=1"
        args = ()
        if active_only:
            sql += " AND is_active = 1"
        sql += " ORDER BY tree_id, structure_type_id"
        rows = []
        for r in self.conn.execute(sql, args):
            d = dict(r)
            d["tree"] = tmap.get(d["tree_id"], "?")
            d["structure_type"] = stypes.get(d["structure_type_id"], "?")
            rows.append(d)
        return rows

    # structure_file 表已移除（2026-10-26）—— file 層直接用真檔名：
    #   structure_module (structure_type_id=file) 一行一個實體 .py 檔。
    def structure_files(self, module_id=None, active_only=True):
        """列出實體檔案（file 層 = structure_module 真檔名，可按 module 篩選）"""
        sql = ("SELECT sm.id, sm.module_id, sm.value AS file_name,"
               "       2 AS file_type_id, NULL AS file_type,"
               "       sm.is_active, sm.created_at"
               " FROM structure_module sm"
               " JOIN structure_type st ON st.id = sm.structure_type_id"
               " WHERE st.meta = 'file'")
        args = []
        if active_only:
            sql += " AND sm.is_active = 1"
        if module_id:
            sql += " AND sm.module_id = ?"
            args.append(module_id)
        sql += " ORDER BY sm.module_id, sm.value"
        return [dict(r) for r in self.conn.execute(sql, args)]

    def insert_structure_file(self, module_id, file_name, file_type_id=None):
        """登記一個實體檔案（冪等）—— file 層行（structure_module）

        file_type_id 冇意義（2026-10-26 移除 file_type），保留參數相容。
        root_id 用第一個 root（同 _backfill_structure_tables 一致）。
        """
        root = self.conn.execute(
            "SELECT id FROM structure_root WHERE is_active = 1"
            " ORDER BY id LIMIT 1").fetchone()
        if not root:
            return None
        root_id = root["id"]
        fid = self.conn.execute(
            "SELECT id FROM structure_type WHERE meta = 'file'"
            " LIMIT 1").fetchone()
        if not fid:
            return None
        cur = self.conn.execute(
            "INSERT INTO structure_module"
            " (structure_type_id, root_id, module_id, value)"
            " SELECT ?, ?, ?, ? WHERE NOT EXISTS"
            " (SELECT 1 FROM structure_module"
            "  WHERE structure_type_id = ? AND root_id = ?"
            "  AND module_id = ? AND value = ?)",
            (fid["id"], root_id, module_id, file_name,
             fid["id"], root_id, module_id, file_name))
        self.conn.commit()
        r = self.conn.execute(
            "SELECT id FROM structure_module"
            " WHERE structure_type_id = ? AND root_id = ?"
            " AND module_id = ? AND value = ?",
            (fid["id"], root_id, module_id, file_name)).fetchone()
        return r["id"] if r else cur.lastrowid

    # ---------- package 自動生成（by definition 定義表） ----------
    def package_tables_ddl(self, package_meta):
        """由 taxonomy 定義自動生成 CREATE TABLE DDL

        package_meta = package 名（例如 module_base / value_chain / 具體 module 名）

        2026-10-23：package_setting 已移除（taxonomy.package 先係 package 權威）。
        2026-10-26（用戶要求）：taxonomy.package 表已移除 ——
        module 清單 = taxonomy.taxonomy（tree = module），
        db_file 由 structure_module db 層行攞（真實檔名，例如 code_gen.db）。

        返回 {表名: CREATE TABLE 語句}（例如 {"sweep_activity": "CREATE TABLE..."}）
        """
        from .function import build_column_definitions

        # 1. module 名 -> taxonomy.registry.id -> structure_module db 層行（真實 db 檔名）
        tx = sqlite3.connect(r"C:\projects\meta\taxonomy\taxonomy.db")
        tx.row_factory = sqlite3.Row
        try:
            row = tx.execute(
                "SELECT t.id, t.meta FROM registry t"
                " JOIN tree tr ON tr.id = t.tree_id"
                " WHERE tr.meta_key = 'module' AND t.meta = ?"
                " AND t.is_active = 1",
                (package_meta,)).fetchone()
            if not row:
                return {}
            mid = row["id"]
            folder = row["meta"]
        finally:
            tx.close()
        # structure_module db 層行（真實 db 檔名）
        db_row = self.conn.execute(
            "SELECT sm.value AS db_file"
            " FROM structure_module sm"
            " JOIN structure_type st ON st.id = sm.structure_type_id"
            " WHERE st.meta = 'db' AND sm.module_id = ?"
            " AND sm.is_active = 1 LIMIT 1", (mid,)).fetchone()
        db_file = db_row["db_file"] if db_row else f"{folder}.db"
        # 掃 DB 嘅表（除咗 guard / sqlite 內部表）
        # 2026-10-26：db 實體放 module 自己資料夾（root + folder\db_file）
        db_path = os.path.join(r"C:\projects\meta", folder, db_file)
        if not os.path.exists(db_path):
            return {}
        conn = sqlite3.connect(db_path)
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
            " AND name NOT IN ('_guard', 'guard_activity', 'sqlite_sequence')"
            " ORDER BY name")]
        conn.close()

        # 2. 通用欄位模板（db_table_setting）
        cols = self.conn.execute(
            """SELECT d.meta_key, d.id AS ts_id,
                      ft.meta AS type_name, d.db_field_type_id
               FROM db_table_setting d
               LEFT JOIN db_field_type ft ON ft.id = d.db_field_type_id
               WHERE d.is_active = 1
               ORDER BY d.seq_id""").fetchall()
        settings = []
        for c in cols:
            props = self._template_props(c["meta_key"], c["db_field_type_id"])
            settings.append({
                "meta_key": c["meta_key"],
                "type_name": c["type_name"] or "TEXT",
                "not_null": 1 if "NOT NULL" in props else 0,
                "is_pk": 1 if "primary_key" in props else 0,
                "is_unique": 1 if "unique" in props else 0,
                "auto_increment": 1 if "auto_increment" in props else 0,
            })
        col_ddl = build_column_definitions(settings)
        out = {}
        for table_meta in tables:
            out[table_meta] = (
                f"CREATE TABLE IF NOT EXISTS {table_meta} (\n"
                f"    {col_ddl}\n)")
        return out

    def commit(self):
        self.conn.commit()

    def close(self):
        self.conn.close()