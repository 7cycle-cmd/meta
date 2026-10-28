"""sql.py — taxonomy.db 存取層（tree / registry / physical_path）

表：
    tree           分類樹（meta_key | seq | is_active）—— 舊名 type
    registry       分類項目（tree_id | meta | is_active）—— 2026-10-27 由 taxonomy 改名
    physical_path  實體路徑鏈（tree_id | module | full_path | path_json）—— 2026-10-26

2026-10-23 修訂：保持 current design（tree_id FK），唔改表結構。
tree 表係 taxonomy.db 自己嘅表（唔係孤島 —— 佢係分類大類字典）。
2026-10-26（physical_path）：每個 module 一條路徑鏈，層次序 = tree.seq。
2026-10-26（用戶要求）：package / path_definition 表已移除 ——
路徑權威改由 structure.db root/module/skill 三張分層表提供。
2026-10-27（用戶要求）：taxonomy 表改名做 registry；tree 三大類 =
channel / module / skill。

用法：
    from taxonomy.sql import SqlStore
    s = SqlStore()
    s.items("module")
    s.insert_item("module", "codegen")
    s.physical_paths()
    s.close()
"""

import json as _json
import os
import sqlite3

from .schema import *  # noqa: F401,E402

DB_PATH = r"C:\projects\meta\taxonomy\taxonomy.db"
# structure.db 新佈局（2026-10-26：{module}\\{module}.db；route 用緊呢份）
STRUCT_DB = r"C:\projects\meta\structure\structure.db"


class SqlStore:
    def __init__(self, db_path=DB_PATH):
        db_path = db_path or DB_PATH  # 顯式傳 None 都用預設
        # 2026-10-23：明示 module/file（唔靠 stack 偵測，保證 api_id 推到）
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        # 2026-10-26：誤建嘅 3 張分表 drop（用戶要求：1 表 + tree_id）
        for _t in ("physical_path_channel", "physical_path_module",
                   "physical_path_skill"):
            _has = self.conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table'"
                " AND name=?", (_t,)).fetchone()
            if _has:
                self.conn.execute(f"DROP TABLE {_t}")
                self.conn.commit()
        # 2026-10-26（用戶要求）：package / path_definition 表移除
        # —— 舊表存在就 drop（路徑由 structure.db 重建）。
        # 2026-10-27：**registry 唔可以喺呢度 drop** —— registry 表名已由
        # taxonomy rename 佔用（分類項目本表），drop 會清空資料。
        for _t in ("package", "path_definition"):
            _has = self.conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table'"
                " AND name=?", (_t,)).fetchone()
            if _has:
                self.conn.execute(f"DROP TABLE {_t}")
                self.conn.commit()
        # 2026-10-27（用戶要求）：taxonomy -> registry（rename，保資料）
        self._rename_taxonomy_to_registry()
        # 2026-10-27（用戶要求）：rest_api / rest_api_rule 表移除
        # taxonomy 唔做 API 註冊 —— READ 中心 = monitor，WRITE 中心 = tool
        self._migrate_drop_rest_api_tables()
        self.conn.executescript(TREE_DDL + REGISTRY_DDL
                                + PHYSICAL_PATH_DDL + PATH_DEFINITION_DDL)
        self.conn.commit()
        self._rollback_new_style()
        self._sync_dicts()
        if not self.tree_id("module"):
            self.insert_category("module", 2, 1)
        for _module in ("terminology", "version", "skill", "value",
                        "lineage", "role", "rule", "preflight", "plan",
                        "task", "tool"):
            self.insert_item("module", _module)
        self._rebuild_physical_paths()

    def _rename_taxonomy_to_registry(self):
        """遷移（幂等）：taxonomy -> registry（2026-10-27 用戶要求）

        舊表存在 -> RENAME（保留 id + 資料）。registry 已存在 -> 唔郁。
        """
        has_old = self.conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table'"
            " AND name='taxonomy'").fetchone()
        if not has_old:
            return  # 已新版
        has_new = self.conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table'"
            " AND name='registry'").fetchone()
        if has_new:
            # 兩者都有（新表 = REGISTRY_DDL 建立嘅空表）-> 掉空新表先 RENAME
            n = self.conn.execute(
                "SELECT COUNT(*) FROM registry").fetchone()[0]
            if n == 0:
                self.conn.execute("DROP TABLE registry")
            else:
                # 兩邊都有資料（異常）-> 新表資料保留，舊表唔郁兼報錯
                raise ValueError(
                    "registry 表已存在且有資料，唔可以自動合併（需要人手處理）")
        self.conn.execute("ALTER TABLE taxonomy RENAME TO registry")
        self.conn.commit()
        print("[taxonomy] taxonomy -> registry（rename，保資料）")

    def _migrate_drop_rest_api_tables(self):
        """遷移（幂等）：drop 舊 rest_api / rest_api_rule 表（2026-10-27）

        用戶要求：taxonomy 唔做 API 註冊
        READ 中心 = monitor（rest_api_READ）
        WRITE 中心 = tool（rest_api_WRITE）
        """
        for t in ("rest_api", "rest_api_rule"):
            has = self.conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table'"
                " AND name=?", (t,)).fetchone()
            if has:
                self.conn.execute(f"DROP TABLE {t}")
                self.conn.commit()
                print(f"[taxonomy] drop 舊表 {t}")

    def _structure_addresses(self):
        """由 structure.db 攞實體地址（3 張分層表）

        返回（by_level, addr_by_id）：
            by_level['root'/'module'/'skill'] = [ row... ]
                每 row: {id, structure_type_id, type_meta, value,
                         parent_id（父層表 id）}
            addr_by_id[(level, id)] = row
        path_json 段存該層表 id，value 由呢度 JOIN 攞返（零 hardcode）。
        """
        by_level, addr_by_id = {}, {}
        try:
            src = sqlite3.connect(STRUCT_DB)
            src.row_factory = sqlite3.Row
            try:
                tables = [("structure_root", "root", None),
                          ("structure_module", "module", "root_id"),
                          ("structure_skill", "skill",
                           "structure_module_id")]
                for tbl, lvl, parent_col in tables:
                    for r in src.execute(
                            f"SELECT s.*, typ.meta AS type_meta"
                            f" FROM {tbl} s"
                            f" JOIN structure_type typ"
                            f"   ON typ.id = s.structure_type_id"
                            f" WHERE s.is_active = 1"):
                        row = dict(r)
                        row["level"] = lvl
                        row["parent_id"] = (row.get(parent_col)
                                            if parent_col else None)
                        by_level.setdefault(lvl, []).append(row)
                        addr_by_id[(lvl, row["id"])] = row
            finally:
                src.close()
        except Exception:
            pass
        return by_level, addr_by_id

    def _full_path_from_chain(self, chain, addr_by_id):
        r"""由 path_json 逐段推導 full_path（2026-10-26 用戶要求）

        path_json 每段 = {"type": ..., "level": ..., "id": N}，
        value 由 3 張分層表（addr_by_id[(level, id)]）攞回，唔 hardcode。
        規則：root 段 = 起點；module 層 package 段 = folder（join）；
        skill 層 package 段 = 身份（技能，唔係 folder，
        唔 join 落路徑）；db 段 = 檔名（終點，join 後停）；
        file 段 = 實體類型要求（唔影響物理路徑）。
        例子：[root(C:\projects\meta), package(api_module), db(api_module.db)]
              -> C:\projects\meta\api_module\api_module.db
        """
        def _val(seg):
            rec = addr_by_id.get((seg.get("level"), seg.get("id")))
            return rec["value"] if rec else (seg.get("value") or "")
        parts = []
        for seg in chain:
            t = seg.get("type")
            lvl = seg.get("level")
            if t == "root":
                parts = [_val(seg)]
            elif t == "package" and lvl == "module":
                v = _val(seg)
                if v:
                    parts.append(v)
            elif t == "db":
                parts.append(_val(seg))
                break  # db 檔 = 實體終點
            # file / skill 唔影響物理路徑
        if not parts:
            return ""
        return os.path.join(*parts)

    def _tree_id(self, meta_key):
        r = self.conn.execute(
            "SELECT id FROM tree WHERE meta_key = ?", (meta_key,)).fetchone()
        return r["id"] if r else None

    # 共用 db 檔所屬 module 資料夾（2026-10-26：db 實體喺 module 自己資料夾）
    _DB_OWNER_FOLDER = {
        "qc.db": "preflight", "mcp.db": "mcp_hub", "code_gen.db": "codegen",
        "task.db": "guard", "resource.db": "resource", "structure.db": "structure",
    }

    def _by_db_file(self, db_file):
        """由 db 檔名搵完整路徑（共用 db 用擁有者資料夾）"""
        owner = self._DB_OWNER_FOLDER.get(
            db_file, db_file[:-3] if db_file.endswith(".db") else db_file)
        return os.path.join(r"C:\projects\meta", owner, db_file)

    def _rebuild_physical_paths(self):
        r"""由 structure.db 3 張分層表重建 physical_path（冪等，零 hardcode）

        full_path = 由 path_json 每段（level + id）JOIN 3 張分層表推導
        path_json 段 =
            {"type": <structure_type.meta>, "level": <層>, "id": <該層表 id>}
        3 張分層表（structure.db）：
            structure_root / structure_module / structure_skill，
            父鍵鏈：root > module > skill
        channel 層 = root 一段。
        資料全部嚟自 structure_taxonomy + 3 張分層表（冇寫死 value）。
        """
        trees = {r["id"]: r["meta_key"] for r in self.conn.execute(  # id->名
            "SELECT id, meta_key FROM tree")}
        seqs = {r["id"]: r["seq"] for r in self.conn.execute(
            "SELECT id, seq FROM tree")}
        by_level, addr_by_id = self._structure_addresses()
        # structure_taxonomy 映射：tree_id -> [structure_type.meta...]
        st_map = {}
        try:
            src = sqlite3.connect(STRUCT_DB)
            src.row_factory = sqlite3.Row
            try:
                for r in src.execute(
                        "SELECT st.tree_id, typ.meta AS type_meta"
                        " FROM structure_taxonomy st"
                        " JOIN structure_type typ ON typ.id = st.structure_type_id"
                        " WHERE st.is_active = 1"):
                    st_map.setdefault(r["tree_id"], []).append(r["type_meta"])
            finally:
                src.close()
        except Exception:
            pass
        # 4 表索引（quick lookup）
        roots = by_level.get("root") or []
        mods = by_level.get("module") or []
        skills = by_level.get("skill") or []
        mod_by_id = {m["id"]: m for m in mods}     # structure_module.id -> row
        # structure_module.module_id（taxonomy.package.id 舊鍵）-> module 名。
        # package 表已移除（2026-10-26 用戶要求）—— module 名由
        # registry 表（tree=module）反查，folder 由 structure_module 攞。
        mid_to_meta = {}
        try:
            for r in self.conn.execute(
                    "SELECT id, meta FROM registry WHERE tree_id = ?"
                    " AND is_active = 1", (self._tree_id("module"),)):
                mid_to_meta[r["id"]] = r["meta"]
        except Exception:
            pass

        rows = []

        def _seg(t, lvl, rec):
            """path_json 一段 = type + level + 該層表 id"""
            seg = {"type": t, "level": lvl}
            if rec:
                seg["id"] = rec["id"]
            return seg

        root = roots[0] if roots else None
        root_seg = _seg("root", "root", root)
        # module 層：每 module 一行（package / db / file 段）
        # 唯一來源 = structure_module（package 行 = folder；db 行 = db 檔）
        pkg_mods = [m for m in mods if m.get("type_meta") == "package"]
        for m in pkg_mods:
            module = mid_to_meta.get(m.get("module_id"))
            if not module:
                continue
            folder = m["value"] or module
            # db 行（同 root + module_id）
            db_row = None
            if root:
                cand = [x for x in mods
                        if x.get("root_id") == root["id"]
                        and x.get("module_id") == m.get("module_id")
                        and x["type_meta"] == "db"]
                db_row = cand[0] if cand else None
            db_file = db_row["value"] if db_row else f"{module}.db"
            # 2026-10-26：共用 db 用擁有者資料夾（qc.db -> preflight/ 等）
            try:
                db_full = self._by_db_file(db_file)
            except Exception:
                db_full = (os.path.join(root["value"], folder, db_file)
                           if root else "")
            chain = [root_seg,
                     _seg("package", "module", m)]
            for tm in ("file", "db"):
                if tm not in st_map.get(2, []):  # module 層 tree_id=2
                    continue
                rec = None
                if root:
                    if tm == "db":
                        # 共用 db 用 db_full 直接做 db 段（唔 match 錯 folder）
                        cand = [x for x in mods
                                if x.get("root_id") == root["id"]
                                and x.get("module_id") == m.get("module_id")
                                and x["type_meta"] == "db"
                                and x["value"] == (db_file
                                                   if db_full == os.path.join(
                                                       root["value"], folder,
                                                       db_file)
                                                   else os.path.basename(db_full))]
                    else:
                        # file 層 = 真實 .py 檔（2026-10-26 用戶要求：
                        # 每個 .py 檔一行，唔係 folder 名）。path_json 用
                        # 第一個 file 行做代表（by module_id，唔靠 value）。
                        cand = [x for x in mods
                                if x.get("root_id") == root["id"]
                                and x["type_meta"] == "file"
                                and x.get("module_id") == m.get("module_id")]
                    rec = cand[0] if cand else None
                chain.append(_seg(tm, "module", rec))
            row_full = self._full_path_from_chain(chain, addr_by_id)
            # 共用 db：full_path 直接用 db_full（權威武）
            if db_full and "db" in st_map.get(2, []):
                row_full = db_full
            rows.append((2, module, row_full, chain))
        # skill 層：每技能一行（父 = module package 行）
        skill_tid = next((tid for tid, lvl in trees.items()
                          if lvl == "skill"), None)
        if skill_tid and "package" in st_map.get(skill_tid, []):
            for s in skills:
                mod_pkg = mod_by_id.get(s.get("structure_module_id"))
                if not mod_pkg:
                    continue
                module = mid_to_meta.get(mod_pkg.get("module_id"))
                if not module:
                    continue
                chain = [root_seg,
                         _seg("package", "module", mod_pkg),
                         _seg("package", "skill", s)]
                row_full = self._full_path_from_chain(chain, addr_by_id)
                rows.append((skill_tid, module, row_full, chain))
        # channel 層
        c_tid = next((tid for tid, lvl in trees.items() if lvl == "channel"),
                     None)
        if c_tid:
            roots_r = by_level.get("root") or []
            if roots_r:
                # 2026-10-26：channel 段 = root 本身（C:\projects\meta），
                # 唔再 join "module"（module/ 目錄已移除，DB 分佈喺各 module folder）
                c_full = roots_r[0]["value"]
                rows.append((c_tid, "root", c_full,
                             [_seg("root", "root", roots_r[0])]))
        # 全量重建（清 + 插，冪等同義因為唯一來源係 path_definition）
        self.conn.execute("DELETE FROM physical_path")
        for tid, module, full, chain in rows:
            self.conn.execute(
                "INSERT INTO physical_path (tree_id, module, full_path,"
                " path_json) VALUES (?, ?, ?, ?)",
                (tid, module, full,
                 _json.dumps(chain, ensure_ascii=False)))
        self.conn.commit()

    def physical_paths(self, module=None):
        """列出實體路徑鏈（1 表 + tree_id，可按 module 篩選）

        返回行帶 level 名（channel / module / skill，
        由 taxonomy.tree 補名）。
        """
        tmap = {r["id"]: r["meta_key"] for r in self.conn.execute(
            "SELECT id, meta_key FROM tree")}
        sql = "SELECT * FROM physical_path WHERE is_active = 1"
        args = []
        if module:
            sql += " AND module = ?"
            args.append(module)
        sql += " ORDER BY tree_id, id"
        rows = []
        for r in self.conn.execute(sql, args):
            d = dict(r)
            d["level"] = tmap.get(d["tree_id"], "?")
            rows.append(d)
        return rows

    def _sync_dicts(self):
        """由 definition 分類字典 sync 入 registry（channel / skill）

        2026-10-23：definition.db 有 channel / skill_dict 兩張字典表
        （定義層）。taxonomy.tree 呢兩類一直空 ——
        sync 佢哋入 registry 表（tree_id = channel/skill）。

        冪等：已存在就唔加；大類 inactive 都照 sync（項目 active）。
        """
        def_db = r"C:\projects\meta\definition\definition.db"
        if not os.path.exists(def_db):
            return
        src = sqlite3.connect(def_db)
        src.row_factory = sqlite3.Row
        try:
            # (tree 名, definition 字典表, meta 欄位)
            for tree_name, table, col in (
                    ("channel", "channel", "meta"),
                    ("skill", "skill_dict", "meta")):
                tid = self.tree_id(tree_name)
                if not tid:
                    # 確保大類存在（保持原 seed 狀態：inactive 都開返？唔好，
                    # 保持 inactive —— 但要有項目要開返 active？）
                    # 用戶要求：定義咗就要有 -> 開返 active
                    tid = self.insert_category(tree_name, {
                        "channel": 1, "skill": 3,
                    }.get(tree_name, 0), 1)
                    self.conn.execute(
                        "UPDATE tree SET is_active = 1 WHERE id = ?", (tid,))
                try:
                    rows = src.execute(
                        f"SELECT {col} AS meta FROM {table}"
                        f" WHERE is_active = 1").fetchall()
                except sqlite3.Error:
                    continue
                for r in rows:
                    if not r["meta"]:
                        continue
                    cur = self.conn.execute(
                        "INSERT OR IGNORE INTO registry"
                        " (tree_id, meta, is_active)"
                        " VALUES (?, ?, 1)", (tid, r["meta"]))
            self.conn.commit()
        finally:
            src.close()

    def _rollback_new_style(self):
        """如果之前畀「tree 字串」版本改過 -> 回滾返 tree_id（保留資料）

        2026-10-23：我哋試過將 tree 併入 taxonomy（tree 欄位），
        用戶要求「move to taxonomy = + table，唔改 current design」——
        所以還原返 tree_id + tree 表。呢個函數處理已經中招嘅 DB。
        2026-10-27：表名改用 registry（taxonomy rename），常數 TAXONOMY_DDL
        = REGISTRY_DDL（新表建 registry）。
        """
        cols = {r[1] for r in self.conn.execute("PRAGMA table_info(registry)")}
        if "tree_id" in cols:
            return  # 已經係舊版

        # 確保 tree 表有 3 個預設大類
        self.conn.execute("""CREATE TABLE IF NOT EXISTS tree (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            meta_key TEXT NOT NULL UNIQUE,
            is_active BOOLEAN NOT NULL DEFAULT 0 CHECK (is_active IN (0,1)),
            seq INTEGER NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
        )""")
        for i, (name, active, seq) in enumerate([
                ("channel", 0, 1), ("module", 1, 2),
                ("skill", 0, 3)], start=1):
            self.conn.execute(
                "INSERT OR IGNORE INTO tree (id, meta_key, is_active, seq)"
                " VALUES (?, ?, ?, ?)", (i, name, active, seq))

        # 12-step 回滾：tree 欄位 -> tree_id
        self.conn.execute("ALTER TABLE registry RENAME TO registry_newstyle")
        self.conn.execute(REGISTRY_DDL)
        name2id = {r["meta_key"]: r["id"] for r in
                   self.conn.execute("SELECT id, meta_key FROM tree")}
        rows = self.conn.execute(
            "SELECT id, tree, meta, is_active, created_at, updated_at"
            " FROM registry_newstyle").fetchall()
        for r in rows:
            tid = name2id.get(r["tree"], 2)
            self.conn.execute(
                "INSERT OR IGNORE INTO registry"
                " (id, tree_id, meta, is_active, created_at, updated_at)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (r["id"], tid, r["meta"], r["is_active"],
                 r["created_at"], r["updated_at"]))
        self.conn.execute("DROP TABLE registry_newstyle")
        self.conn.commit()

    # ---------- 大類（tree 表）----------
    def categories(self, active_only=False):
        sql = "SELECT * FROM tree WHERE 1=1"
        if active_only:
            sql += " AND is_active = 1"
        sql += " ORDER BY seq, id"
        return [dict(row) for row in self.conn.execute(sql)]

    def insert_category(self, meta_key, seq, is_active=0):
        cur = self.conn.execute(
            "INSERT OR IGNORE INTO tree (meta_key, seq, is_active) VALUES (?,?,?)",
            (meta_key, seq, is_active))
        if cur.rowcount == 0:
            self.conn.execute(
                "UPDATE tree SET seq = ?, is_active = ? WHERE meta_key = ?",
                (seq, is_active, meta_key))
        self.conn.commit()
        row = self.conn.execute(
            "SELECT id FROM tree WHERE meta_key = ?", (meta_key,)).fetchone()
        return row["id"] if row else cur.lastrowid

    def deactivate_category(self, category_id):
        self.conn.execute("UPDATE tree SET is_active = 0 WHERE id = ?", (category_id,))
        self.conn.commit()

    # ---------- registry（分類項目，2026-10-27 由 taxonomy 改名）----------
    def tree_id(self, meta_key):
        """由 tree.meta_key 攞 tree_id（唔存在返回 None）"""
        row = self.conn.execute(
            "SELECT id FROM tree WHERE meta_key = ?", (meta_key,)).fetchone()
        return row["id"] if row else None

    def registry_id(self, tree, meta):
        """由 tree.meta_key + meta 攞 registry.id（唔存在返回 None）"""
        row = self.conn.execute(
            "SELECT r.id FROM registry r"
            " JOIN tree tr ON tr.id = r.tree_id"
            " WHERE tr.meta_key = ? AND r.meta = ?",
            (tree, meta)).fetchone()
        return row["id"] if row else None

    def items(self, tree=None, active_only=True):
        """列出分類項目（可按 tree.meta_key 篩選）"""
        sql = ("SELECT t.*, tr.meta_key AS tree FROM registry t"
               " JOIN tree tr ON tr.id = t.tree_id WHERE 1=1")
        params = []
        if tree:
            sql += " AND tr.meta_key = ?"
            params.append(tree)
        if active_only:
            sql += " AND t.is_active = 1"
        sql += " ORDER BY t.tree_id, t.id"
        return [dict(row) for row in self.conn.execute(sql, params)]

    def insert_item(self, tree, meta, is_active=1):
        """登記一個分類項目（冪等：已存在就更新 is_active / updated_at）

        tree = tree.meta_key（channel / module / skill）
        """
        tid = self.tree_id(tree)
        if not tid:
            raise ValueError(f"tree '{tree}' 唔存在於 tree 表")
        cur = self.conn.execute(
            "INSERT OR IGNORE INTO registry (tree_id, meta, is_active)"
            " VALUES (?, ?, ?)", (tid, meta, is_active))
        if cur.rowcount == 0:
            self.conn.execute(
                "UPDATE registry SET is_active = ?," 
                " updated_at = datetime('now', 'localtime')"
                " WHERE tree_id = ? AND meta = ?", (is_active, tid, meta))
        self.conn.commit()
        row = self.conn.execute(
            "SELECT id FROM registry WHERE tree_id = ? AND meta = ?",
            (tid, meta)).fetchone()
        return row["id"] if row else cur.lastrowid

    def deactivate_item(self, item_id):
        self.conn.execute(
            "UPDATE registry SET is_active = 0,"
            " updated_at = datetime('now', 'localtime') WHERE id = ?", (item_id,))
        self.conn.commit()

    def delete_item(self, item_id):
        """真正移除一個分類項目（唔係 soft delete）"""
        cur = self.conn.execute(
            "DELETE FROM registry WHERE id = ?", (item_id,))
        self.conn.commit()
        return cur.rowcount

    def sync_items_from_registry(self):
        """由 resource.db registry 匯入缺少嘅 module 分類項目。

        2026-10-26：resource module 已 drop -> 回報未重建，唔爆。
        """
        try:
            from resource import Resource
        except ImportError:
            return {"added": 0,
                    "error": "resource module 已 drop（2026-10-26），待重建"}

        res = Resource()
        try:
            # module type id（動態查，唔硬寫 12）
            module_type_id = res.type_id("module")
            resources = res.list_registries(type_id=module_type_id)
            existing = {row["meta"] for row in self.items("module")}
            added = 0
            for resource in resources:
                prefix = resource["meta"].split(".")[0]
                if prefix not in existing:
                    self.insert_item("module", prefix)
                    existing.add(prefix)
                    added += 1
            return {"added": added, "total": len(existing)}
        finally:
            res.close()

    # ---------- JSON 批量登記 / 搜尋 / dump（由 registry.py 搬入）----------
    TREES = ("module", "skill", "channel")

    def register_json(self, data):
        if not isinstance(data, dict):
            return {"status": "error", "message": "JSON 頂層必須係物件"}
        unsupported = set(data) - {
            "module", "modules", "skill", "skills",
            "channel", "channels",
        }
        if unsupported:
            keys = ", ".join(sorted(unsupported))
            return {"status": "error", "message": f"不支援嘅 key: {keys}"}

        if "modules" in data:
            if not isinstance(data["modules"], list) or any(
                    not isinstance(module, dict) or not module.get("name")
                    or set(module) != {"name"}
                    for module in data["modules"]):
                return {
                    "status": "error",
                    "message": "modules 必須係只包含 name 嘅物件清單",
                }
            results = [
                self.register_json({"module": module["name"]})
                for module in data["modules"]
            ]
            return {"status": "ok", "count": len(results), "results": results}

        if "module" in data and data["module"]:
            item_id = self.insert_item("module", data["module"])
            return {"status": "ok", "count": 1,
                    "results": [{"module": data["module"],
                                 "module_id": item_id}]}

        # ---------- skill / channel ----------
        for single, plural in (("skill", "skills"),
                               ("channel", "channels")):
            if plural in data:
                items = data[plural]
                if not isinstance(items, list) or any(
                        not isinstance(item, dict) or not item.get(single)
                        or set(item) != {single}
                        for item in items):
                    return {
                        "status": "error",
                        "message": f"{plural} 必須係只包含 {single} 嘅物件清單",
                    }
                results = []
                for item in items:
                    item_id = self.insert_item(single, item[single])
                    results.append({single: item[single],
                                    single + "_id": item_id})
                return {"status": "ok", "count": len(results),
                        "results": results}
            if single in data and data[single]:
                item_id = self.insert_item(single, data[single])
                return {"status": "ok", "count": 1,
                        "results": [{single: data[single],
                                     single + "_id": item_id}]}

        return {
            "status": "error",
            "message": "需要 module / modules / skill / skills /"
                       " channel / channels key",
        }

    def register_json_str(self, json_str):
        try:
            data = _json.loads(json_str)
        except _json.JSONDecodeError as exc:
            return {"status": "error", "message": f"JSON 解析失敗: {exc}"}
        return self.register_json(data)

    def search(self, query):
        if not isinstance(query, dict):
            raise ValueError("搜尋條件必須係 JSON 物件")
        result = {"query": query}
        for tree in self.TREES:
            rows = self.items(tree)
            keyword = query.get(tree)
            if keyword:
                rows = [row for row in rows if keyword in row["meta"]]
            result[tree + "s"] = rows
        return result

    def dump(self):
        return {
            "categories": self.categories(),
            "modules": self.items("module"),
            "skills": self.items("skill"),
            "channels": self.items("channel"),
        }

    def commit(self):
        self.conn.commit()

    def close(self):
        self.conn.close()
