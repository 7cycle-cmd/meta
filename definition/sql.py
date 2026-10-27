"""sql.py — definition.db 存取層"""

import sqlite3

from .function import *  # noqa: F401,E402

from .schema import *  # noqa: F401,E402

DB_PATH = r"C:\projects\meta\definition\definition.db"
STRUCT_DB = r"C:\projects\meta\structure\structure.db"

# (表名, definition 文字)
# 2026-10-22：table_template / column_template 已移除，
# 欄位實例唯一擁有者 = resource.db db_field（+ db_field_setting 提供約束）
# db_table_type 已移除 definition 欄位（type -> meta，加 updated_at）

# column_definition 嘅擁有者 = structure.db（唔喺 definition.db 重複建立）

# table_definition 表：表定義連接（db_table -> db_table_type）
# subject = resource.db db_table.id（表實例）
# object  = structure.db db_table_type.id（表型別）
# proof   = is_active


# structure 表：結構層級（package > table > column > physical_package > physical_file）

# ------------------------------------------------------------------
# 檔案必需規則（2026-10-26：file_required 表移除，改由呢個 code 常數提供）
#
# 2026-10-22 補：之前 file_type 表**冇 DDL owner** —— 只存在於 live DB，
# fresh definition.db 完全冇 file_type，`ModuleFile.required_types()`
# 會靜靜回 []（等於「冇任何必要檔」），`check_complete()` 永遠報齊。
# 教訓：DDL 一定要有 code 擁有者（同 resource_ref 同一個坑）。
# 2026-10-26：file_type / structure_file / file_required 表全部移除 ——
# 檔案層（file 行 = 真檔名）喺 structure.db；必需規則 = 呢度（code 常數）。
# ------------------------------------------------------------------

# 預設檔案類型：(meta, description, seq, required)
# required：True = 每個 module 都必須有
#   必需：__init__.py / function.py / api.py / route.py / schema.py /
#   sql.py / registry.py / rest_api.py
# 2026-10-25：api_server.py 移除（rest_api.py 取代，統一命名）
DEFAULT_FILE_TYPES = [
    ("__init__.py", "module 入口（export 對外 API）", 1, True),
    ("function.py", "核心業務邏輯", 2, True),
    ("api.py", "對外 API（class + 方法）", 3, True),
    ("route.py", "CLI 入口", 4, True),
    ("schema.py", "權威 DDL（唯一 schema 來源）", 5, True),
    ("sql.py", "資料庫存取層（所有 SQL 集中）", 6, True),
    # 2026-10-24：skill 移除 —— registry 取代（名註冊表係 module 基礎）
    ("registry.py", "名稱註冊表", 10, True),
    # 2026-10-25：rest_api.py 必需（用戶要求）—— REST 對外接口
    ("rest_api.py", "REST API 入口（http.server，統一 pattern）", 20, True),
    ("map.py", "映射管理", 11, False),
    ("proof.py", "證據記錄", 12, False),
    ("sweep.py", "校驗器", 13, False),
    ("train.py", "訓練器", 14, False),
    ("scaffold.py", "scaffold 產生", 15, False),
    ("scaffold_templates.py", "scaffold 模板", 16, False),
    ("sync.py", "同步", 17, False),
    # 2026-10-22 加：MCP server 入口（mcp_hub/python_server.py 等）
    ("server.py", "MCP server 入口（FastMCP，stdio transport）", 18, False),
]


class SqlStore:
    def __init__(self, db_path=DB_PATH):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        # ATTACH structure.db（db_table_setting / db_field_setting 喺 structure）
        self.conn.execute(f"ATTACH DATABASE ? AS structdb", (STRUCT_DB,))
        # ATTACH taxonomy.db（package 權威）
        self.conn.execute(f"ATTACH DATABASE ? AS taxdb",
                          (r"C:\projects\meta\taxonomy\taxonomy.db",))
        # required 關係表（v2：字典喺 structure，by API）
        # 2026-10-25：file_type / structure_type 搬去 structure，
        #   definition 只保留 required 關係（db_*_required / structure_required）。
        # 2026-10-26：file_required 移除（檔案必需規則改由 structure.db
        #   file_required 表定義 —— 結構層先係實體嘅家）。
        self.conn.executescript(
            DB_TABLE_REQUIRED_DDL + DB_FIELD_REQUIRED_DDL
            + STRUCTURE_REQUIRED_DDL)
        self.conn.commit()
        self._migrate_seq_to_position()     # seq -> position_id（2026-10-25 舊版）
        self._migrate_position_to_seq()     # position_id -> seq_id（2026-10-27）
        self._migrate_db_table_required()   # v1 -> v2（meta 版 -> id 版）
        self._seed_required_tables()        # by structure API
        self._seed_structure_required()
        self._drop_moved_tables()           # 搬走咗嘅舊表（file_required / file_type / structure）
        self._sync_physical()
        # 條件定義（code_condition + subject / operator / expected_def 三字典）
        # 2026-10-24：純定義零執行 —— 邊個 subject 對邊個 operator 期望咩
        self.conn.executescript(
            SUBJECT_DDL + OPERATOR_DDL + EXPECTED_DEF_DDL + CODE_CONDITION_DDL)
        self.conn.commit()
        self._seed_condition_dicts()

    def _seed_condition_dicts(self):
        """預填條件字典（冪等）

        operator：必須 / 唔可以 / 至少一次（定義層固定三個）
        subject / expected_def：唔預填（由 add_subject / add_expected_def 註冊）
        唔燒 AUTOINCREMENT（用 WHERE NOT EXISTS）。
        """
        for v, d in (("必須", "一定要有"), ("唔可以", "一定唔可以有"),
                     ("至少一次", "最少出現一次")):
            self.conn.execute(
                "INSERT INTO operator (value, description)"
                " SELECT ?, ? WHERE NOT EXISTS"
                " (SELECT 1 FROM operator WHERE value = ?)", (v, d, v))
        self.conn.commit()

    # ---------- subject（主體字典） ----------
    def subjects(self, active_only=True):
        sql = "SELECT * FROM subject"
        if active_only:
            sql += " WHERE is_active = 1"
        sql += " ORDER BY id"
        return [dict(r) for r in self.conn.execute(sql)]

    def add_subject(self, value, description=None, resource_id=None):
        """登記一個主體（幂等）"""
        cur = self.conn.execute(
            "INSERT INTO subject (value, description, resource_id)"
            " SELECT ?, ?, ? WHERE NOT EXISTS"
            " (SELECT 1 FROM subject WHERE value = ?)",
            (value, description, resource_id, value))
        self.conn.commit()
        r = self.conn.execute(
            "SELECT id FROM subject WHERE value = ?", (value,)).fetchone()
        return r["id"] if r else None

    # ---------- operator（條件運算字典：必須 / 唔可以 / 至少一次） ----------
    def operators(self, active_only=True):
        sql = "SELECT * FROM operator"
        if active_only:
            sql += " WHERE is_active = 1"
        sql += " ORDER BY id"
        return [dict(r) for r in self.conn.execute(sql)]

    def add_operator(self, value, description=None, resource_id=None):
        """登記一個條件運算（幂等）"""
        cur = self.conn.execute(
            "INSERT INTO operator (value, description, resource_id)"
            " SELECT ?, ?, ? WHERE NOT EXISTS"
            " (SELECT 1 FROM operator WHERE value = ?)",
            (value, description, resource_id, value))
        self.conn.commit()
        r = self.conn.execute(
            "SELECT id FROM operator WHERE value = ?", (value,)).fetchone()
        return r["id"] if r else None

    # ---------- expected_def（期望值字典） ----------
    def expected_defs(self, active_only=True):
        sql = "SELECT * FROM expected_def"
        if active_only:
            sql += " WHERE is_active = 1"
        sql += " ORDER BY id"
        return [dict(r) for r in self.conn.execute(sql)]

    def add_expected_def(self, value, description=None, resource_id=None):
        """登記一個期望值（幂等）"""
        cur = self.conn.execute(
            "INSERT INTO expected_def (value, description, resource_id)"
            " SELECT ?, ?, ? WHERE NOT EXISTS"
            " (SELECT 1 FROM expected_def WHERE value = ?)",
            (value, description, resource_id, value))
        self.conn.commit()
        r = self.conn.execute(
            "SELECT id FROM expected_def WHERE value = ?", (value,)).fetchone()
        return r["id"] if r else None

    # ---------- code_condition（定義表：subject × operator × expected） ----------
    def code_conditions(self, active_only=True):
        """列出全部條件定義（JOIN 三張字典表攞名）"""
        sql = """SELECT cc.id,
                        cc.subject_id, s.value AS subject,
                        cc.operator_id, o.value AS operator,
                        cc.expected_id, e.value AS expected,
                        cc.description, cc.is_active, cc.created_at,
                        cc.updated_at
                 FROM code_condition cc
                 LEFT JOIN subject s ON s.id = cc.subject_id
                 LEFT JOIN operator o ON o.id = cc.operator_id
                 LEFT JOIN expected_def e ON e.id = cc.expected_id"""
        if active_only:
            sql += " WHERE cc.is_active = 1"
        sql += " ORDER BY cc.id"
        return [dict(r) for r in self.conn.execute(sql)]

    def add_code_condition(self, subject, operator, expected,
                           description=None):
        """建立一條條件定義（幂等）

        subject   = subject.value（例如 api.py 嘅 do_GET）
        operator  = operator.value（必須 / 唔可以 / 至少一次）
        expected  = expected_def.value（例如 /health 一定要有 route）
        三邊都自動註冊字典（唔存在就建立）。
        """
        sid = self.add_subject(subject)
        oid = self.add_operator(operator)
        eid = self.add_expected_def(expected)
        self.conn.execute(
            "INSERT OR IGNORE INTO code_condition"
            " (subject_id, operator_id, expected_id, description)"
            " VALUES (?, ?, ?, ?)", (sid, oid, eid, description))
        self.conn.commit()
        r = self.conn.execute(
            "SELECT id FROM code_condition"
            " WHERE subject_id = ? AND operator_id = ? AND expected_id = ?",
            (sid, oid, eid)).fetchone()
        return r["id"] if r else None

    def commit(self):
        self.conn.commit()

    def close(self):
        self.conn.close()

    def _seq_id(self, seq_value):
        """由數值攞 common.seq.id（by common REST api / Python API）

        seq_value = 位置數值（1-100）。唔存在 -> 自動登記。
        2026-10-27：position -> seq（舊 position 表已遷移去 seq）。
        """
        try:
            from common import Common
            cm = Common()
            try:
                return cm.seq_id(str(seq_value))
            finally:
                cm.close()
        except Exception:
            # fallback：common.db 直接查（REST 服務未必開）
            try:
                import sqlite3 as _sq
                _c = _sq.connect(r"C:\projects\meta\common\common.db")
                try:
                    r = _c.execute(
                        "SELECT id FROM seq WHERE meta = ?",
                        (str(seq_value),)).fetchone()
                    if r:
                        return r[0]
                    cur = _c.execute(
                        "INSERT OR IGNORE INTO seq (meta, value)"
                        " VALUES (?, ?)",
                        (str(seq_value), int(seq_value)))
                    _c.commit()
                    r = _c.execute(
                        "SELECT id FROM seq WHERE meta = ?",
                        (str(seq_value),)).fetchone()
                    return r[0] if r else cur.lastrowid
                finally:
                    _c.close()
            except Exception:
                return None

    def _position_id(self, position_value):
        """兼容 alias：_seq_id（2026-10-27 position -> seq）"""
        return self._seq_id(position_value)

    def _migrate_position_to_seq(self):
        """遷移（幂等）：required 表 position_id 欄 -> seq_id（2026-10-27 用戶要求）

        舊版 position_id（common.position.id）-> seq_id（common.seq.id）。
        值唔郁（common 已將 position 表 rename 做 seq，id 兼容）。
        """
        for tbl in ("db_table_required", "db_field_required"):
            cols = [c[1] for c in self.conn.execute(
                "PRAGMA table_info(%s)" % tbl)]
            if "position_id" not in cols:
                continue
            if "seq_id" not in cols:
                self.conn.execute(
                    "ALTER TABLE %s RENAME COLUMN position_id TO seq_id" % tbl)
                self.conn.commit()
                print(f"[definition] {tbl}.position_id -> seq_id")

    def _migrate_seq_to_position(self):
        """遷移（幂等）：required 表 seq -> position_id（2026-10-25 用戶要求）

        seq（直接數字）-> common.position.id（by common API），然後 drop seq。
        2026-10-27：position 已改名 seq —— 呢個遷移係舊版（seq 欄存嘅
        直接數字），照舊執行然後畀 _migrate_position_to_seq 收尾。
        """
        for tbl in ("db_table_required", "db_field_required"):
            cols = [c[1] for c in self.conn.execute(
                "PRAGMA table_info(%s)" % tbl)]
            if "seq" not in cols:
                continue
            # 1. 未加 position_id -> 加欄 + 搬值
            if "position_id" not in cols and "seq_id" not in cols:
                self.conn.execute(
                    "ALTER TABLE %s ADD COLUMN position_id INTEGER" % tbl)
                self.conn.commit()
                rows = self.conn.execute(
                    "SELECT id, seq FROM %s WHERE seq IS NOT NULL" % tbl
                ).fetchall()
                for r in rows:
                    pid = self._position_id(r["seq"] or 1)
                    if pid:
                        self.conn.execute(
                            "UPDATE %s SET position_id = ? WHERE id = ?" % tbl,
                            (pid, r["id"]))
                self.conn.commit()
                print(f"[definition] {tbl} seq -> position_id：{len(rows)} 行")
            # 2. drop seq（2026-10-25：position_id 取代）
            self.conn.execute(
                "ALTER TABLE %s DROP COLUMN seq" % tbl)
            self.conn.commit()
            print(f"[definition] {tbl} 移除 seq 欄（position_id 取代）")

    def _drop_moved_tables(self):
        """搬遷後 drop 舊表（2026-10-25 / 2026-10-26）

        file_type / structure_type / structure_file / file_required 已
        移除／搬去 structure module。physical_package 已移除。
        呢啲喺 definition 唔再係權威 -> drop。
        """
        for tbl in ("file_type", "structure_type", "structure_file",
                    "file_required", "physical_package"):
            has = self.conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                (tbl,)).fetchone()
            if has:
                self.conn.execute("DROP TABLE %s" % tbl)
                self.conn.commit()
                print(f"[definition] {tbl} 表移除（已搬去 structure / 由 system_setting 取代）")

    def _migrate_db_table_required(self):
        """遷移（幂等）：db_table_required 舊版（meta 直寫）-> table_definition_id

        v2（2026-10-25 用戶要求）：字典喺 structure（by API）。
        舊結構（meta / reference_table 欄）-> drop 重建（新 DDL），
        required 資料由 _seed_required_tables（structure API）重建。
        """
        cols = [c[1] for c in self.conn.execute(
            "PRAGMA table_info('db_table_required')")]
        if "meta" in cols:
            self.conn.execute("DROP TABLE db_table_required")
            self.conn.execute(DB_TABLE_REQUIRED_DDL)
            self.conn.commit()
            print("[definition] db_table_required v1 表 drop 重建（id 版）")
        cols = [c[1] for c in self.conn.execute(
            "PRAGMA table_info('db_field_required')")]
        if "reference_table" in cols:
            self.conn.execute("DROP TABLE db_field_required")
            self.conn.execute(DB_FIELD_REQUIRED_DDL)
            self.conn.commit()
            print("[definition] db_field_required v1 表 drop 重建（id 版）")

    def _migrate_structure_rename(self):
        """遷移（幂等）：physical_type/required/file -> structure_* 改名（2026-10-25）

        用戶要求：physical_type -> structure_type、physical_required ->
        structure_required、physical_file -> structure_file。
        FK 欄：physical_required.physical_type_id -> structure_type_id。
        """
        # 1. physical_type -> structure_type
        has = self.conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table'"
            " AND name='physical_type'").fetchone()
        if has:
            cnt = self.conn.execute(
                "SELECT COUNT(*) c FROM structure_type").fetchone()["c"]
            if cnt == 0:
                self.conn.execute(
                    "INSERT INTO structure_type (id, meta, description,"
                    " is_active, created_at)"
                    " SELECT id, meta, description, is_active, created_at"
                    " FROM physical_type")
                self.conn.commit()
            self.conn.execute("DROP TABLE physical_type")
            self.conn.commit()
            print("[definition] physical_type -> structure_type（rename）")
        # 2. physical_required -> structure_required（FK 欄 rename）
        has = self.conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table'"
            " AND name='physical_required'").fetchone()
        if has:
            cnt = self.conn.execute(
                "SELECT COUNT(*) c FROM structure_required").fetchone()["c"]
            if cnt == 0:
                self.conn.execute(
                    "INSERT INTO structure_required"
                    " (id, tree_id, structure_type_id, is_active, created_at)"
                    " SELECT id, tree_id, physical_type_id, is_active,"
                    "        created_at FROM physical_required")
                self.conn.commit()
            self.conn.execute("DROP TABLE physical_required")
            self.conn.commit()
            print("[definition] physical_required -> structure_required（rename）")

    def _drop_physical_package(self):
        """移除 physical_package 表（2026-10-25）

        位置由 structure 分層地址表取代（權威單一）。
        """
        has = self.conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table'"
            " AND name='physical_package'").fetchone()
        if not has:
            return
        self.conn.execute("DROP TABLE physical_package")
        self.conn.commit()
        print("[definition] physical_package 表移除（structure 取代）")

    def _module_id_map(self):
        """module 名 -> id（taxonomy.registry 權威，tree = module）

        2026-10-26（用戶要求）：taxonomy.package 表已移除 ——
        module 清單 = registry 表（tree = module；2026-10-27 rename）。
        """
        try:
            import sqlite3 as _sq
            tc = _sq.connect(r"C:\projects\meta\taxonomy\taxonomy.db")
            tc.row_factory = _sq.Row
            try:
                return {r["meta"]: r["id"] for r in tc.execute(
                    "SELECT t.id, t.meta FROM registry t"
                    " JOIN tree tr ON tr.id = t.tree_id"
                    " WHERE tr.meta_key = 'module' AND t.is_active = 1")}
            finally:
                tc.close()
        except Exception:
            return {}

    def _structure_type_id(self, meta):
        """由 structure_type.meta 攞 id（冇 -> None）"""
        try:
            from structure import Structure
            st = Structure()
            try:
                for t in st.list_structure_types(active_only=False):
                    if t["meta"] == meta:
                        return t["id"]
                return None
            finally:
                st.close()
        except Exception:
            return None

    def _sync_physical(self):
        """自動登記 physical_file（掃 C:\\projects\\meta 資料夾）

        2026-10-25（v2）：physical_package 已移除 ——
        module_id 由 taxonomy.package（權威，2026-10-26 取代 system_setting）攞。
        掃每個 module 資料夾（有 __init__.py 嘅），
        存在嘅 .py 檔自動入 physical_file（file_type_id 由 file_type 字典）。
        缺 file_required 必需檔 -> 自動生成（_scaffold_missing）。
        """
        import os
        meta_dir = r"C:\projects\meta"
        if not os.path.isdir(meta_dir):
            return
        # module_id 權威：taxonomy.package（name -> id）
        mid_by_name = self._module_id_map()
        # 掃頂層 module 資料夾（有 __init__.py = package）
        for entry in sorted(os.listdir(meta_dir)):
            folder = os.path.join(meta_dir, entry)
            if not os.path.isdir(folder):
                continue
            if entry.startswith("_"):
                continue  # 臨時 / 備份資料夾唔當 module
            if not os.path.isfile(os.path.join(folder, "__init__.py")):
                continue
            # 新 module -> 自動生成缺失嘅必需檔（file_required 規則）
            self._scaffold_missing(folder, entry)
            mid = mid_by_name.get(entry)
            if mid is None:
                continue  # system_setting 未有 location -> 唔算 module
            # 掃 .py 檔 -> structure_file（by structure API）
            try:
                from structure import Structure
                st = Structure()
            except Exception:
                st = None
            if st is None:
                return
            try:
                for fn in sorted(os.listdir(folder)):
                    if not fn.endswith(".py"):
                        continue
                    st.register_structure_file(mid, fn)
            finally:
                st.close()
        # 由 structure API 統一 sync（唔喺 definition 寫）
        # self.conn.commit()  # structure_file 唔喺 definition

    def _scaffold_missing(self, folder, module_name):
        """新 module 自動生成缺失嘅必需檔（file_required 規則 = 新 module 唔可以有問題）

        2026-10-24（用戶要求）：新 module 出現應該自動有齊必需檔，
        有 missing = BUG。呢個方法讀 file_required（存在即必需），
        遇到缺檔案就寫標準 skeleton（唔可以 import 嘅檔唔生成）。

        2026-10-26：file_required 表移除 —— 檔案必需規則由 structure.db
        file_required 表定義（結構層先係實體嘅家），required_file_types()
        by structure API 攞（file_type_id -> file_name）。
        """
        import os
        req = [r["meta"] for r in self.required_file_types()]
        generated = []
        for meta in req:
            if not meta.endswith(".py"):
                continue
            path = os.path.join(folder, meta)
            if os.path.isfile(path):
                continue
            content = self._scaffold_content(module_name, meta)
            if content is None:
                continue
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)
                generated.append(meta)
            except OSError:
                pass
        # 2026-10-24：新 module scaffold 完 -> 即刻開 DB 建表
        #（唔可以等「第一次 RegistryStore() 先 CREATE」—— db_table 要即刻存在）
        if generated:
            self._init_module_db(module_name)

    def _init_module_db(self, module_name):
        """新 module 初始化 DB：db_table_required 表即刻建好（definition.db 權威）

        scaffold 只生成 .py 檔；呢度讀 db_table_required（存在即必需）
        攞表名（by structure API），用 structure generate_table_ddl 生成 DDL
        建表 —— 零 hardcode。
        """
        import os
        # 2026-10-26：db 實體放 module 自己資料夾（唔可以喺 root）
        db_path = os.path.join(r"C:\projects\meta", module_name,
                               f"{module_name}.db")
        try:
            from structure.api import Structure
            s = Structure()
            try:
                # 權威 = db_table_required（definition.db）+ structure 字典
                rows = self.conn.execute(
                    "SELECT table_definition_id FROM db_table_required"
                    " WHERE is_active = 1 ORDER BY seq_id, id").fetchall()
                if not rows:
                    return
                # by structure API 攞表名（table_definition）
                tds = {t["id"]: t for t in
                       s.store.table_definitions(active_only=True)}
                conn = _g(db_path, module=module_name, file="registry.py")
                for r in rows:
                    td = tds.get(r["table_definition_id"])
                    if not td:
                        continue
                    ddl = s.generate_table_ddl(td["db_file"], td["table_name"])
                    if ddl:
                        conn.executescript(ddl)
                conn.commit()
                conn.close()
            finally:
                s.close()
        except Exception:
            pass  # DB 初始化失敗唔阻塞 scaffold（下次 RegistryStore() 會重試）

    def _gen_table_ddl(self, table_name):
        """由 table_definition 權威生成一張表嘅 DDL（唔 hardcode）

        table_name = 表名（例如 registry）
        經 Structure().generate_table_ddl()（structure.db 表定義權威）。
        冇定義 -> None（唔生成）。
        """
        try:
            from structure.api import Structure
            s = Structure()
            try:
                return s.generate_table_ddl("definition.db", table_name)
            finally:
                s.close()
        except Exception:
            return None

    def _scaffold_content(self, module_name, fname):
        """標準 skeleton 內容（由 file_type 決定寫咩）

        生成嘅檔案：function / api / route / schema / sql / registry
        __init__.py 唔生成（module 有 __init__.py 先算 module）。
        registry 嘅表 DDL 由 table_definition 權威生成（唔 hardcode）。
        """
        if fname == "registry.py":
            ddl = self._gen_table_ddl("registry")
            if ddl is None:
                return None
        if fname == "function.py":
            return f'''"""function.py — {module_name} 核心業務邏輯層

（標準檔：__init__/function/api/route/schema/sql/registry/rest_api 全部 required）
核心邏輯喺 api.py {module_name}.api 類方法內。
"""
'''
        if fname == "api.py":
            return f'''"""api.py — {module_name} 對外 API"""

from .sql import SqlStore


class {module_name.capitalize()}:
    """{module_name} 對外介面"""

    def __init__(self, db_path=None):
        self.store = SqlStore(db_path) if db_path else SqlStore()

    def close(self):
        self.store.close()
'''
        if fname == "rest_api.py":
            return f'''"""rest_api.py — {module_name} REST API 入口

標準 http.server（冇第三方依賴）；統一 pattern：
    127.0.0.1:PORT  -> 每個 module 一個 REST 接口

啟動：
    python -m {module_name}.rest_api --port 9500
"""

import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class _Handler(BaseHTTPRequestHandler):
    def _send(self, code, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass

    def do_GET(self):
        path = self.path.split("?", 1)[0].rstrip("/")
        if path in ("/health", ""):
            self._send(200, {{"status": "ok",
                              "module": "{module_name}",
                              "api": "{module_name}.rest_api"}})
        else:
            self._send(404, {{"error": f"唔知 route: {{path}}"}})


def main(port=9500):
    print(f"{{module_name}} rest_api @ http://127.0.0.1:{{port}}")
    ThreadingHTTPServer(("127.0.0.1", port), _Handler).serve_forever()


if __name__ == "__main__":
    _port = 9500
    if "--port" in sys.argv:
        _port = int(sys.argv[sys.argv.index("--port") + 1])
    main(_port)
'''
        if fname == "route.py":
            return f'''"""route.py — {module_name} CLI"""

import sys


def main(argv=None):
    print("python -m {module_name} <command>")
    return 0


if __name__ == "__main__":
    sys.exit(main())
'''
        if fname == "schema.py":
            return f'''"""schema.py — {module_name} 權威 DDL 入口（唯一 schema 來源）"""

# DDL 由 sql.py 管理（此檔案為 schema 擁有者標記）
__all__ = []
'''
        if fname == "sql.py":
            return f'''"""sql.py — {module_name} 資料庫存取層"""

import sqlite3

DB_PATH = "C:/projects/meta/{module_name}/{module_name}.db"


class SqlStore:
    def __init__(self, db_path=DB_PATH):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row

    def close(self):
        self.conn.close()
'''
        if fname == "registry.py":
            # DDL 由 table_definition 權威生成（唔 hardcode）
            ddl = self._gen_table_ddl("registry")
            return f'''# registry.py — {module_name} package 嘅名稱註冊表（SSOT）
# 每個 module 自己嘅資源註冊（meta UNIQUE）
# 表結構 = table_definition 權威（structure generate_table_ddl）

import sqlite3

DB_PATH = "C:/projects/meta/{module_name}/{module_name}.db"


class RegistryStore:
    def __init__(self, db_path=DB_PATH):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        ddl = """{ddl}"""
        self.conn.executescript(ddl)
        self.conn.commit()

    def list_registry(self, active_only=True):
        sql = "SELECT * FROM registry WHERE 1=1"
        if active_only:
            sql += " AND is_active = 1"
        sql += " ORDER BY id"
        return [dict(r) for r in self.conn.execute(sql)]

    def register(self, meta, description=None):
        """登記一個名稱（冪等）"""
        self.conn.execute(
            "INSERT INTO registry (meta, description)"
            " SELECT ?, ? WHERE NOT EXISTS"
            " (SELECT 1 FROM registry WHERE meta = ?)",
            (meta, description, meta))
        self.conn.commit()
        r = self.conn.execute(
            "SELECT id FROM registry WHERE meta = ?", (meta,)).fetchone()
        return r["id"] if r else None

    def close(self):
        self.conn.close()
'''
        return None

    def _seed_required_tables(self):
        """預填 db_table_required + db_field_required（冪等，唔燒號）

        2026-10-25（用戶要求）：字典喺 structure（by API）——
        table_definition（module_scope=1）+ db_field 係權威，
        definition 只記 required 關係（存在 = 每個 module 都要有）。
        """
        try:
            from structure import Structure
            st = Structure()
        except Exception:
            return  # structure 未 ready -> 唔阻塞
        try:
            try:
                tables = st.store.table_definitions(active_only=True)
            except Exception:
                tables = []
            for td in tables:
                if not td.get("module_scope"):
                    continue
                pid = self._position_id(td.get("id", 0) or 1)
                if not pid:
                    continue
                self.conn.execute(
                    "INSERT INTO db_table_required"
                    " (table_definition_id, seq_id)"
                    " SELECT ?, ? WHERE NOT EXISTS"
                    " (SELECT 1 FROM db_table_required"
                    "  WHERE table_definition_id = ?)",
                    (td["id"], pid, td["id"]))
                # 欄位：該表全部 db_field
                try:
                    fields = st.store.db_fields(td["id"], active_only=True)
                except Exception:
                    fields = []
                for f in fields:
                    # f.seq_id 已經係 common.seq.id -> 直接用
                    fpid = f.get("seq_id") or f.get("position_id")
                    if not fpid:
                        continue
                    self.conn.execute(
                        "INSERT INTO db_field_required"
                        " (table_definition_id, db_field_id, seq_id)"
                        " SELECT ?, ?, ? WHERE NOT EXISTS"
                        " (SELECT 1 FROM db_field_required"
                        "  WHERE table_definition_id = ? AND db_field_id = ?)",
                        (td["id"], f["id"], fpid,
                         td["id"], f["id"]))
            self.conn.commit()
        finally:
            st.close()

    def file_types(self, active_only=True):
        """列出檔案類型字典（2026-10-26：file_type 表移除，用 code 常數）

        file_type / structure_file 已刪 —— 檔案類型改成直接由
        DEFAULT_FILE_TYPES（definition/sql.py 權威）提供。
        """
        rows = []
        for i, (meta, desc, _seq, _req) in enumerate(DEFAULT_FILE_TYPES,
                                                     start=1):
            rows.append({
                "id": i, "meta": meta, "description": desc,
                "is_active": 1,
                "created_at": "", "updated_at": "",
            })
        return rows

    def _seed_structure_types(self):
        """（已搬去 structure module，2026-10-25）—— 保留空殼防止舊 call 爆"""
        pass

    def _migrate_package_required(self):
        """遷移（幂等）：package_required -> structure_required（2026-10-25 rename）

        舊表（package_required）存在 -> 搬資料去新表 -> drop 舊表。
        新 rows（用戶要求 2026-10-25）由 _seed_structure_required 負責。
        """
        has_old = self.conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table'"
            " AND name='package_required'").fetchone()
        if not has_old:
            return
        n = self.conn.execute(
            "SELECT COUNT(*) c FROM structure_required").fetchone()["c"]
        if n == 0:
            self.conn.execute(
                "INSERT INTO structure_required (tree_id, structure_type_id)"
                " SELECT tree_id, physical_type_id FROM package_required"
                " WHERE is_active = 1")
            self.conn.commit()
        self.conn.execute("DROP TABLE IF EXISTS package_required")
        self.conn.commit()
        print("[definition] package_required -> structure_required（rename）")

    def _seed_structure_required(self):
        """預填 structure_required（冪等）—— 每個大類必須有咩實體

        2026-10-25（用戶要求，全部大類都要有齊）：
            channel    -> package（channel 都要有套件）
            module     -> package + db_table + db_field + db（module 有表 + 欄位 + 自己嘅 .db）
            skill      -> package + file
            （2026-10-27：能力由 skill 表達 —— 三大類 required 齊全）

        關係同 taxonomy > tree 一樣：tree_id 指返 taxonomy.tree.id。
        tree table（taxonomy.db）：1=channel 2=module 3=skill
        """
        # tree_id 透過 taxdb（ATTACH）攞，唔 hardcode
        rows = [
            ("channel", "package"),      # channel 一定要有 package
            ("module", "package"),       # module 一定要有 package
            ("module", "db_table"),      # module 一定要有 db_table
            ("module", "db_field"),      # module 一定要有 db_field（2026-10-25 用戶+）
            ("module", "db"),            # module 一定要有 db（2026-10-25 用戶+，.db 檔）
            ("skill", "package"),        # skill 一定要有 package
            ("skill", "file"),           # skill 一定要有 file
        ]
        for tree_meta, ptype_meta in rows:
            tree = self.conn.execute(
                "SELECT id FROM taxdb.tree WHERE meta_key = ?",
                (tree_meta,)).fetchone()
            stid = self._structure_type_id(ptype_meta)  # by structure API
            if not tree or not stid:
                continue
            self.conn.execute(
                "INSERT INTO structure_required (tree_id, structure_type_id)"
                " SELECT ?, ? WHERE NOT EXISTS"
                " (SELECT 1 FROM structure_required"
                "  WHERE tree_id = ? AND structure_type_id = ?)",
                (tree["id"], stid, tree["id"], stid))
        # 執行時：db_field 要求（module）—— 舊 db_table soft delete 保留
        self.conn.commit()

    def file_requireds(self, active_only=True):
        """列出必須檔案（2026-10-26：file_required 表移除，用 code 常數）

        required=True 嘅檔（DEFAULT_FILE_TYPES 標記）先係「必須」。
        """
        rows = []
        for i, (meta, desc, seq, req) in enumerate(DEFAULT_FILE_TYPES,
                                                   start=1):
            if req:
                rows.append({
                "id": i, "file_type_id": i, "seq_id": seq,
                "is_active": 1, "created_at": "",
                "meta": meta, "description": desc,
            })
        return rows

    def required_file_types(self):
        """必須有嘅檔案類型（required=True 嘅 DEFAULT_FILE_TYPES）"""
        rows = []
        for i, (meta, desc, seq, req) in enumerate(DEFAULT_FILE_TYPES,
                                                   start=1):
            if req:
                rows.append({
                    "id": i, "file_type_id": i, "seq_id": seq,
                    "meta": meta, "description": desc,
                })
        return rows

    # ---------- db_table_required / db_field_required（必需表/欄位） ----------
    # 字典（table_definition / db_field）喺 structure —— by API 攞。
    def _structure_tables(self):
        """由 structure API 攞全部 table_definition（module_scope=1 先算必需）"""
        try:
            from structure import Structure
            st = Structure()
            try:
                return [t for t in st.store.table_definitions(active_only=True)
                        if t.get("module_scope")]
            finally:
                st.close()
        except Exception:
            return []

    def db_table_requireds(self, active_only=True):
        """列出必需表（JOIN structure table_definition）"""
        sql = """SELECT dtr.id, dtr.table_definition_id, dtr.seq_id,
                        dtr.is_active, dtr.created_at
                 FROM db_table_required dtr WHERE 1=1"""
        if active_only:
            sql += " AND dtr.is_active = 1"
        sql += " ORDER BY dtr.seq_id, dtr.id"
        rows = [dict(r) for r in self.conn.execute(sql)]
        # by API：補 table_name / db_file（structure 字典）
        tables = {t["id"]: t for t in self._structure_tables()}
        for d in rows:
            td = tables.get(d["table_definition_id"])
            d["table_name"] = td["table_name"] if td else None
            d["db_file"] = td["db_file"] if td else None
        return rows

    def required_tables(self):
        """必須有嘅表（db_table_required 存在即必需）"""
        return self.db_table_requireds(active_only=True)

    def add_db_table_required(self, table_name, db_file="*.db",
                              position=1):
        """登記一張必需表（冪等）—— by structure API 搵 table_definition

        table_name = structure table_definition.table_name
        db_file    = 屬邊個 db（table_definition.db_file）
        position   = 位置數值（common.position，by REST api）
        """
        try:
            from structure import Structure
            st = Structure()
            try:
                td = st.store.table_definition(db_file, table_name,
                                               active_only=True)
            finally:
                st.close()
        except Exception:
            td = None
        if not td:
            raise ValueError(
                f"table_definition 唔存在: {db_file}.{table_name}"
                f"（要先喺 structure 註冊）")
        pid = self._position_id(position)
        if not pid:
            raise ValueError(f"position 唔存在: {position}")
        self.conn.execute(
            "INSERT INTO db_table_required (table_definition_id, seq_id)"
            " SELECT ?, ? WHERE NOT EXISTS"
            " (SELECT 1 FROM db_table_required"
            "  WHERE table_definition_id = ?)",
            (td["id"], pid, td["id"]))
        self.conn.commit()
        r = self.conn.execute(
            "SELECT id FROM db_table_required WHERE table_definition_id = ?",
            (td["id"],)).fetchone()
        return r["id"] if r else None

    def db_field_requireds(self, table_definition_id=None, active_only=True):
        """列出必需欄位（JOIN structure db_field，可按表篩選）"""
        sql = """SELECT dfr.id, dfr.table_definition_id, dfr.db_field_id,
                        dfr.seq_id, dfr.is_active, dfr.created_at
                 FROM db_field_required dfr WHERE 1=1"""
        args = []
        if table_definition_id:
            sql += " AND dfr.table_definition_id = ?"
            args.append(table_definition_id)
        if active_only:
            sql += " AND dfr.is_active = 1"
        sql += " ORDER BY dfr.seq_id, dfr.id"
        rows = [dict(r) for r in self.conn.execute(sql, args)]
        # by API：補 column_name / 表名（structure 字典）
        try:
            from structure import Structure
            st = Structure()
            try:
                tds_all = st.store.table_definitions(active_only=True)
                fields = {}
                for t in tds_all:
                    for f in st.store.db_fields(t["id"], active_only=True):
                        fields[f["id"]] = f
                tds = {t["id"]: t for t in tds_all}
            finally:
                st.close()
        except Exception:
            fields, tds = {}, {}
        for d in rows:
            f = fields.get(d["db_field_id"])
            d["column_name"] = f["column_name"] if f else None
            td = tds.get(d["table_definition_id"])
            d["table_name"] = td["table_name"] if td else None
        return rows

    def add_db_field_required(self, table_name, column_name, db_file="*.db",
                              position=1):
        """登記一個必需欄位（冪等）—— by structure API

        table_name  = structure table_definition.table_name
        column_name = structure db_field.column_name
        position    = 位置數值（common.position，by REST api）
        """
        try:
            from structure import Structure
            st = Structure()
            try:
                td = st.store.table_definition(db_file, table_name,
                                               active_only=True)
                if not td:
                    raise ValueError(f"table 唔存在: {db_file}.{table_name}")
                f = st.store.db_field_by_column(td["id"], column_name,
                                                active_only=True)
            finally:
                st.close()
        except Exception:
            f = None
        if not f:
            raise ValueError(
                f"db_field 唔存在: {table_name}.{column_name}"
                f"（要先喺 structure 註冊）")
        td_id = f["table_definition_id"]
        pid = self._position_id(position)
        if not pid:
            raise ValueError(f"position 唔存在: {position}")
        self.conn.execute(
            "INSERT INTO db_field_required"
            " (table_definition_id, db_field_id, seq_id)"
            " SELECT ?, ?, ? WHERE NOT EXISTS"
            " (SELECT 1 FROM db_field_required"
            "  WHERE table_definition_id = ? AND db_field_id = ?)",
            (td_id, f["id"], pid, td_id, f["id"]))
        self.conn.commit()
        r = self.conn.execute(
            "SELECT id FROM db_field_required"
            " WHERE table_definition_id = ? AND db_field_id = ?",
            (td_id, f["id"])).fetchone()
        return r["id"] if r else None

    # ---------- package（taxonomy.registry 權威；structure 已移除 package 表） ----------
    def package_settings(self, active_only=True):
        """列出 package × 表（由 taxonomy.registry 攞，tree = module）

        2026-10-23：package_setting 已移除（structure.db），
        package 權威 = taxonomy.package（db_file 對應 DB）。
        2026-10-26（用戶要求）：taxonomy.package 表已移除 ——
        module 清單 = registry 表（tree = module；2026-10-27 rename），
        db_file = {meta}.db。
        """
        sql = ("SELECT t.id, t.meta, t.meta AS folder,"
               "       t.meta || '.db' AS db_file, t.is_active"
               " FROM taxdb.registry t"
               " JOIN taxdb.tree tr ON tr.id = t.tree_id"
               " WHERE tr.meta_key = 'module'")
        args = ()
        if active_only:
            sql += " AND t.is_active = 1"
        sql += " ORDER BY t.meta"
        return [dict(r) for r in self.conn.execute(sql, args)]

    # db_table_setting（通用欄位模板，structure.db）
    def table_settings(self, active_only=True):
        """列出通用欄位模板（一行 = 一個欄位）"""
        sql = "SELECT * FROM structdb.db_table_setting"
        args = ()
        conds = []
        if active_only:
            conds.append("is_active = 1")
        if conds:
            sql += " WHERE " + " AND ".join(conds)
        sql += " ORDER BY seq_id, id"
        return [dict(r) for r in self.conn.execute(sql, args)]

    # ---------- structure_file（字典喺 structure，2026-10-25 搬遷） ----------
    # physical_package 已移除（system_setting.physical_location 取代）
    def structure_files(self, module_id=None, active_only=True):
        """列出實體檔案（by structure API）"""
        try:
            from structure import Structure
            st = Structure()
            try:
                return st.list_structure_files(module_id, active_only)
            finally:
                st.close()
        except Exception:
            return []

    def insert_structure_file(self, module_id, file_name, file_type_id=None):
        """登記一個實體檔案（by structure API，冪等）"""
        try:
            from structure import Structure
            st = Structure()
            try:
                return st.register_structure_file(module_id, file_name,
                                                  file_type_id)
            finally:
                st.close()
        except Exception:
            return None

    def modules_files(self, module_name=None, active_only=True):
        """列出 module 嘅檔案（由 taxonomy.package 攞 module_id + module 名）"""
        mid_by_name = self._module_id_map()
        rows = self.structure_files(active_only=active_only)
        for d in rows:
            d["module"] = next(
                (n for n, mid in mid_by_name.items()
                 if mid == d["module_id"]), None)
        if module_name:
            mid = mid_by_name.get(module_name)
            if mid is None:
                return []
            rows = [r for r in rows if r["module_id"] == mid]
        return rows

    # ---------- structure_type（字典喺 structure，2026-10-25 搬遷） ----------
    def structure_types(self, active_only=True):
        """列出實體類型字典（by structure API）"""
        try:
            from structure import Structure
            st = Structure()
            try:
                return st.list_structure_types(active_only)
            finally:
                st.close()
        except Exception:
            return []

    def structure_requireds(self, tree_meta=None, active_only=True):
        """列出每個大類必須有咩實體（JOIN taxonomy.tree；type 名 by structure API）

        tree_meta = taxonomy.tree.meta_key（channel / module / skill）
        """
        sql = """SELECT pr.id, pr.tree_id, tr.meta_key AS tree,
                        pr.structure_type_id,
                        pr.is_active, pr.created_at
                 FROM structure_required pr
                 LEFT JOIN taxdb.tree tr ON tr.id = pr.tree_id
                 WHERE 1=1"""
        args = []
        if tree_meta:
            sql += " AND tr.meta_key = ?"
            args.append(tree_meta)
        if active_only:
            sql += " AND pr.is_active = 1"
        sql += " ORDER BY pr.tree_id, pr.structure_type_id"
        rows = [dict(r) for r in self.conn.execute(sql, args)]
        # by structure API 補 type 名
        stypes = {t["id"]: t["meta"] for t in self.structure_types(False)}
        for d in rows:
            d["structure_type"] = stypes.get(d["structure_type_id"])
        return rows

    # rule
    def rules(self):
        return [dict(r) for r in self.conn.execute(
            "SELECT * FROM rule WHERE enabled = 1 ORDER BY id")]

    def commit(self):
        self.conn.commit()

    def close(self):
        self.conn.close()