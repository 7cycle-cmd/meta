"""schema.py — taxonomy 權威 DDL 入口（唯一 schema 來源）

由 sql.py 搬遷：TREE_DDL, TAXONOMY_DDL, PACKAGE_DDL
（8 檔標準：__init__/function/api/route/schema/sql/registry/rest_api）

2026-10-23 修訂：保持 current design（tree_id FK + tree 表）。
唔改 taxonomy 表結構。

2026-10-23（package）：system.package 嘅 db_file 搬過嚟 ——
加新表 `package`（tree_id + meta + db_file），唔郁 taxonomy 表。
"""

TREE_DDL = """
CREATE TABLE IF NOT EXISTS tree (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    meta_key   TEXT    NOT NULL UNIQUE,
    is_active  BOOLEAN NOT NULL DEFAULT 0 CHECK (is_active IN (0,1)),
    seq        INTEGER NOT NULL,
    created_at TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

# registry 表：分類項目本表（2026-10-27 由 taxonomy 改名）
# 2026-10-27（用戶要求）：taxonomy -> registry（名稱註冊表）；
REGISTRY_DDL = """
CREATE TABLE IF NOT EXISTS registry (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    tree_id     INTEGER NOT NULL,          -- FK -> tree.id（channel / module / skill）
    meta        TEXT    NOT NULL,          -- 分類項目名（codegen / fill_value / cli ...）
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (tree_id, meta)
);
"""

# TAXONOMY_DDL 舊名 alias（2026-10-27：實際表 = registry）
TAXONOMY_DDL = REGISTRY_DDL

# physical_path 表：每個實體嘅路徑鏈（2026-10-26 用戶要求）
# 1 張表 + tree_id（taxonomy.tree 係層字典權威）：
#   tree_id = taxonomy.tree.id（channel / module / skill）
# 層次序（階層）由 taxonomy.tree.seq 話事：
#   channel > module > skill
# 每行 = 一層一個實體嘅完整路徑鏈：
#   module    = module 名（鏈嘅第 2 段；channel 層 = root）
#   full_path = 完整實體路徑
#   path_json = 路徑鏈 JSON（root -> module -> <層實體>）
# 例（module 層，db 實體）：
#   [{"type":"root","value":"C:\\projects\\meta"},
#    {"type":"module","value":"system_setting"},
#    {"type":"db","value":"system_setting.db"}]
# 例（skill 層）：
#   [{"type":"root","value":"C:\\projects\\meta"},
#    {"type":"module","value":"system_setting"},
#    {"type":"skill","value":"system_setting"}]
PHYSICAL_PATH_DDL = """
CREATE TABLE IF NOT EXISTS physical_path (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    tree_id     INTEGER NOT NULL,          -- taxonomy.tree.id（channel / module / skill）
    module      TEXT    NOT NULL,           -- module 名（system_setting；channel 層 = root）
    full_path   TEXT    NOT NULL,           -- 完整實體路徑
    path_json   TEXT    NOT NULL,           -- 路徑鏈 JSON（root -> module -> <層實體>）
    is_active   BOOLEAN NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (tree_id, module)
);
"""

# path_definition 表：路徑定義權威（2026-10-26 用戶要求）
# 每行 = 一個 module 喺一個層嘅路徑定義：
#   tree_id   = taxonomy.tree.id（層；db 位置定義屬 module 層）
#   root      = 根目錄（C:\\projects\\meta）
#   module_id = taxonomy.taxonomy.id（module 權威武 by_id，tree = module）
# physical_path 嘅 full_path / path_json 全部由呢度生成：
#   full_path = os.path.join(root, folder, db_file)
#              = C:\\projects\\meta\\api_module\\api_module.db
#   path_json = [{"type":"root","value":root},
#                {"type":"module","value":<module>},
#                {"type":"db","value":<db_file>}]
# 2026-10-26（用戶要求）：path_definition / package 已移除 ——
# 路徑權威改由 structure.db 3 張分層表（structure_root / structure_module /
# structure_skill）提供，physical_path 直接由嗰度重建。
PATH_DEFINITION_DDL = ""

__all__ = ['TREE_DDL', 'REGISTRY_DDL', 'TAXONOMY_DDL',
           'PHYSICAL_PATH_DDL', 'PATH_DEFINITION_DDL']
