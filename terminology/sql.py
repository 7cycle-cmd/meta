"""sql.py — terminology.db 存取層

terminology = 術語層：term（名稱登記）+ data_collect（真實 value）
              + question 字典 clone（answer / expected / operator /
                status / boolean —— 2026-10-24s clone，字典 seed 同 question 一致）

字典表（全部註冊，冪等）：
    boolean      真/假字典（0=假 1=真，id = value）
    answer       答案字典（boolean_id：真/有、假/冇）
    expected     期望值字典（boolean_id：比幾多）
    operator     operator 字典（點比：meta + expression）
    status       狀態字典（boolean_id：approved / rejected）
"""

import sqlite3

# 2026-10-28（用戶要求）：import 都要 permit —— worker 唔可以靠 import 逃工。
# `from .schema import *` 係 wildcard，permit 系統唔可以睇到佢攞咗咩。
# 而家：顯式列出全部 symbol（逐個可 permit）+ 啟動時檢查 permit。
from .schema import (  # noqa: F401  （逐個 symbol，permit 化）
    INDUSTRY_DDL, EVIDENCE_DDL, CONDITION_DDL, W5H2_DDL,
    REGISTRY_DDL, RUN_DDL, FLOW_DDL, STEP_DDL, STEP_INPUT_DDL,
    FLOW_BRANCH_DDL, NEXT_FLOW_DDL,
    EXPECTED_DDL, OPERATOR_DDL, ANSWER_DDL, BOOLEAN_DDL,
    QUESTION_DDL, SEQ_DDL, STATUS_DDL,
    EXPECTED_SOURCE_DDL, STEP_OUTPUT_DDL,
    OUTPUT_TYPE_DDL, OUTPUT_BY_DDL, HARDCODE_VALUE_DDL,
    WORD_CATEGORY_DDL, SOURCE_REGISTER_DDL,
    QUESTION_TEMPLATE_DDL,
)

DB_PATH = r"C:\projects\meta\terminology\terminology.db"

# 預設字典（seed，冪等）—— 同 question module 一致
# boolean：id = value = 0/1（固定，唔係 AUTOINCREMENT）
DEFAULT_BOOLEANS = [
    (0, "假 / no / rejected"),
    (1, "真 / yes / approved"),
]

# answer：答案字典（1=真/有，0=假/冇）
DEFAULT_ANSWERS = [
    (1, "真/有"),
    (0, "假/冇"),
]

# expected：期望值字典（比幾多）
DEFAULT_EXPECTEDS = [
    (1, "期望值 1（真）"),
    (0, "期望值 0（假）"),
]

# status：狀態字典（approved / rejected）
DEFAULT_STATUSES = [
    (1, "approved"),
    (0, "rejected"),
]

# operator：operator 字典（點比）—— 同 question/sql.py DEFAULT_OPERATORS
DEFAULT_OPERATORS = [
    ("==", "float(answer) == float(pass_value)", "答案 == 期望值（數值）"),
    ("!=", "float(answer) != float(pass_value)", "答案 != 期望值（數值）"),
    (">=", "float(answer) >= float(pass_value)", "答案 >= 期望值（數值）"),
    ("<=", "float(answer) <= float(pass_value)", "答案 <= 期望值（數值）"),
    (">", "float(answer) > float(pass_value)", "答案 > 期望值（數值）"),
    ("<", "float(answer) < float(pass_value)", "答案 < 期望值（數值）"),
    ("is_true", "answer is True",
     "答案係 True（嚴格 bool；1 唔算）"),
    ("is_false", "answer is False",
     "答案係 False（嚴格 bool；0 唔算）"),
    ("bool_eq",
     "(str(answer).strip().lower() in ('yes', 'true', '1')) =="
     " (str(pass_value).strip().lower() in ('yes', 'true', '1'))",
     "答案嘅真假 == 期望值嘅真假（yes/no/true/false/1/0 都通）"),
    ("eq", "str(answer) == str(pass_value)",
     "文字答案 == 期望值（字串比較，唔做數值轉換）"),
    ("ne", "str(answer) != str(pass_value)",
     "文字答案 != 期望值（字串比較，唔做數值轉換）"),
]


def import_permit_check(module_name, imported, symbols="*"):
    """檢查 module 有冇權 import（2026-10-28 用戶：worker 唔可以靠 import 逃工）

    呢個係全局 helper：任何 module 啟動時都可以呼叫，
    檢查「自己 import 嘅嘢」喺 permit.db import_permit 表有冇 allowlist。
    冇 permit = 擋（返回 allowed=False）。

    module_name = taxonomy.registry.meta（邊個 module）
    imported    = 被 import 嘅嘢（'.schema' / 'sqlite3' / '.api' ...）
    symbols     = import 嘅 symbols（'*' = wildcard）

    返回 {"allowed": bool, "reason": str, "registry_id": n|None}
    """
    try:
        import sqlite3 as _sq
        _c = _sq.connect(r"C:\projects\meta\permit\permit.db")
        try:
            _c.row_factory = _sq.Row
            # module_id 反查（taxonomy.registry）
            module_id = None
            try:
                _t = _sq.connect(r"C:\projects\meta\taxonomy\taxonomy.db")
                try:
                    _t.row_factory = _sq.Row
                    r = _t.execute(
                        "SELECT id FROM registry WHERE tree_id = 2"
                        " AND meta = ? AND is_active = 1",
                        (module_name,)).fetchone()
                    module_id = r["id"] if r else None
                finally:
                    _t.close()
            except Exception:
                pass
            # allowlist 查：module 級 permit（module_id = 自己）或 全局（NULL）
            # 兩種形式都准：symbols 精準 match / permit symbols='ALL'
            # （'ALL' = module 自己嘅 schema 全部 symbol 准，顯式 import）
            row = _c.execute(
                "SELECT id FROM import_permit"
                " WHERE imported = ? AND is_active = 1"
                "   AND ((symbols = ?) OR (symbols = 'ALL'))"
                "   AND (module_id IS NULL OR module_id = ?) LIMIT 1",
                (imported, symbols, module_id)).fetchone()
            if row:
                return {"allowed": True,
                        "reason": f"import_permit({imported} {symbols})",
                        "registry_id": row["id"]}
            # wildcard 冇 permit -> 擋
            if symbols == "*":
                return {"allowed": False,
                        "reason": f"wildcard import '{imported} *' 冇 permit ——"
                                  " 全部 symbol 要入表 + permit 先准",
                        "registry_id": None}
            return {"allowed": False,
                    "reason": f"import '{imported} {symbols}' 冇 permit ——"
                              " 要喺 import_permit 表登記",
                    "registry_id": None}
        finally:
            _c.close()
    except Exception:
        return {"allowed": True, "reason": "permit 系統未 ready（首次初始化）",
                "registry_id": None}


class SqlStore:
    def __init__(self, db_path=DB_PATH):
        # 2026-10-28（用戶要求）：import 都要 permit ——
        # module 唔可以自己決定「申請咗就照行」。
        # module 只知道「佢冇 permit」（have not）；
        # 有冇得批係用戶 / tool / monitor 嘅決定（give to user）。
        # 冇 permit = 擋住啟動 + 呈報用戶，等批先可以行。
        #
        # 2026-10-28（用戶：ALL 唔准）：唔再申請 `.schema ALL`。
        # 改為對 schema_registry 26 個真 symbol 逐個 check（by id），
        # 冇 permit 嘅一個一個申請（每個 request 帶 schema_id + reason）。
        # 全批先可以啟動；有 pending 一樣擋（等 tool / monitor 決定）。
        _ok = True
        _pending = []
        _granted = 0
        try:
            from permit import Permit as _P
            _pp = _P()
            try:
                # 逐個 symbol check（by id，唔准 ALL）
                for sr in _pp.schema_symbols(module_name="terminology"):
                    sid = sr["id"]
                    chk = _pp.check_import_permit(
                        "terminology", ".schema", sr["symbol"])
                    if chk["allowed"]:
                        _granted += 1
                        continue
                    # 冇 permit：逐個申請（每個都要 reason + schema_id）
                    req = _pp.request_import(
                        "terminology", ".schema", schema_id=sid,
                        symbol=sr["symbol"],
                        reason=f"terminology 啟動需要 schema symbol"
                               f" {sr['symbol']}（建表 DDL）")
                    _pending.append(
                        (sr["symbol"], req.get("request_id"),
                         req.get("status")))
            finally:
                _pp.close()
        except Exception:
            pass
        if _pending:
            _ok = False
            print(f"[permit] terminology 有 {len(_pending)} 個 symbol"
                  f" 冇 permit（{_granted} 個已有）：")
            for sym, rid, st in _pending:
                print(f"    {sym}: request_id={rid} status={st}")
            print("[permit] 未有批准之前唔會啟動 ——"
                  " 請用 permit.approve_import(request_id,"
                  " 證明鏈...) 逐個批准後再啟動")
        elif not _granted:
            _ok = False
            print("[permit] terminology 冇任何 .schema permit，"
                  "且 schema_registry 未有 symbol 註冊 —— 唔可以啟動？")
        if not _ok:
            raise PermissionError(
                "[permit] terminology 有未批准嘅 .schema import 申請"
                "（by id）—— 唔可以啟動。請 approve（give to user / tool"
                " / monitor 決定）之後再試")
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        # 2026-10-27（用戶要求）：value 表升做獨立 module（value.db）
        # terminology 唔再擁有 value 表 —— ATTACH value.db 做 vdb（SSOT）
        self._attach_value_db()
        self._migrate_drop_value_table()
        self._migrate_registry_schema()
        # 建表（全部 IF NOT EXISTS，冪等）+ 字典 seed
        # 注意：VALUE_DDL 唔再喺呢度建（value 表由 value module 擁有）
        self.conn.executescript(";\n".join([
            INDUSTRY_DDL, EVIDENCE_DDL,
            REGISTRY_DDL,
            CONDITION_DDL, W5H2_DDL, RUN_DDL, FLOW_DDL, STEP_DDL,
            STEP_INPUT_DDL,
            EXPECTED_SOURCE_DDL, STEP_OUTPUT_DDL,
            OUTPUT_TYPE_DDL, OUTPUT_BY_DDL, HARDCODE_VALUE_DDL,
            FLOW_BRANCH_DDL, NEXT_FLOW_DDL,
            EXPECTED_DDL, OPERATOR_DDL, ANSWER_DDL, BOOLEAN_DDL,
            QUESTION_DDL, SEQ_DDL, STATUS_DDL,
            WORD_CATEGORY_DDL, SOURCE_REGISTER_DDL,
            QUESTION_TEMPLATE_DDL,
        ]))
        self.conn.commit()
        # 2026-10-28（用戶設計：resource 2 表接實體位置）——
        # 真實登記「terminology 用咗邊啲 schema」（由已批 import_permit 逐個
        # 寫入 resource.registry + structure_resource，AST 掃真實行號）。
        self._register_resource_schemas()
        self._register_resource_functions()

    # ---------- resource.registry / structure_resource 真實登記（2026-10-28）----------
    # terminology 啟動建表 = 真係用咗呢 26 個 schema symbol（有 import permit）。
    # 由 permit.db import_permit（by id 已批）逐個登記：
    #   resource.registry    = (type=schema, name=symbol 名,
    #                            bind_target_id=schema_registry.id,
    #                            source_file, source_line_start=AST 行號)
    #   structure_resource   = (resource_type_id=schema, value=symbol 名,
    #                            package_id, file_id,
    #                            line_number=AST 掃真實行號)
    # 零 hardcode：symbol -> 行號由 AST 掃 schema.py；schema_registry_id 由
    # permit.db import_permit 真表攞。冪等（全部 WHERE NOT EXISTS）。

    def _register_resource_schemas(self):
        """登記已用 schema 到 resource.registry + structure_resource（冪等）

        2026-10-28（用戶 redesign）：resource = 2 張表（type + registry）。
        resource.registry 登記：
            type = schema（id 1）
            name = DDL symbol 名（e.g. ANSWER_DDL）
            bind_target_id = schema.db schema_registry.id
            source_file = terminology/schema.py
            source_line_start = AST 掃到嘅真實行號
        """
        try:
            from permit import Permit as _P
            _pp = _P()
            try:
                permits = _pp.import_permits()
            finally:
                _pp.close()
        except Exception:
            return
        # 只揀自己 module（module_id = taxonomy.registry.id 4）+ .schema
        # （module_id NULL = 全局 permit，一樣係「用咗」）
        import sqlite3 as _sq
        mid = None
        try:
            _t = _sq.connect(r"C:\projects\meta\taxonomy\taxonomy.db")
            try:
                _t.row_factory = _sq.Row
                r = _t.execute(
                    "SELECT id FROM registry WHERE tree_id = 2"
                    " AND meta = 'terminology' AND is_active = 1"
                ).fetchone()
                mid = r["id"] if r else None
            finally:
                _t.close()
        except Exception:
            pass
        if not mid:
            return
        # 物理位置：AST 掃 schema.py 攞每個 DDL 嘅真實行號
        lines = self._schema_symbol_lines()
        try:
            from resource import Resource as _R
            _rs = _R()
            try:
                from structure import Structure as _S
                _st = _S()
                try:
                    n = 0
                    for perm in permits:
                        if perm.get("schema_id") is None:
                            continue  # 唔係 by-id permit，唔登記
                        if perm.get("imported") != ".schema":
                            continue
                        if perm.get("module_id") not in (None, mid):
                            continue
                        symbol = perm.get("symbols")
                        line = lines.get(symbol)
                        # resource.registry（type=schema，bind schema_registry.id）
                        _rs.register(
                            "schema", symbol,
                            bind_target_id=perm["schema_id"],
                            source_file="terminology/schema.py",
                            source_line_start=line)
                        # structure_resource（物理位置：package + file +
                        # 行號 AST；type='schema'，value=symbol 名）
                        package_id = self._structure_module_id(mid, None)
                        file_id = self._structure_module_id(mid, "schema.py")
                        if package_id:
                            _st.add_structure_resource(
                                _st.resource_type_id("schema"),
                                symbol, package_id,
                                line_number=line, file_id=file_id)
                        n += 1
                finally:
                    _st.close()
            finally:
                _rs.close()
        except Exception:
            return
        if n:
            print(f"[terminology] resource.registry 真實登記：{n} 個 schema"
                  f"（by permit.db import_permit）")

    def _schema_symbol_lines(self):
        """AST 掃 schema.py 攞 DDL symbol -> 真實行號（零 hardcode）"""
        import os as _os
        import importlib.util as _ilu
        _ast_sp = _ilu.spec_from_file_location(
            "_stdlib_ast",
            _os.path.join(_os.path.dirname(_os.__file__), "ast.py"))
        _ast_m = _ilu.module_from_spec(_ast_sp)
        _ast_sp.loader.exec_module(_ast_m)
        out = {}
        try:
            with open(r"C:\projects\meta\terminology\schema.py", "r",
                      encoding="utf-8") as f:
                tree = _ast_m.parse(f.read())
        except (OSError, SyntaxError):
            return out
        for node in tree.body:
            if isinstance(node, _ast_m.Assign):
                for t in node.targets:
                    if isinstance(t, _ast_m.Name) and \
                            t.id.endswith("_DDL"):
                        out[t.id] = node.lineno
        return out

    def _structure_module_id(self, module_id, value):
        """structure.db structure_module.id by module_id + value（package/file層）

        value=None -> package 層（structure_type.meta='package'）；
        value='schema.py' -> file 層（structure_type.meta='file'）。
        """
        try:
            import sqlite3 as _sq
            _c = _sq.connect(r"C:\projects\meta\structure\structure.db")
            try:
                _c.row_factory = _sq.Row
                if value is None:
                    r = _c.execute(
                        "SELECT sm.id FROM structure_module sm"
                        " JOIN structure_type st ON st.id = sm.structure_type_id"
                        " WHERE sm.module_id = ?"
                        " AND st.meta = 'package' LIMIT 1",
                        (module_id,)).fetchone()
                else:
                    r = _c.execute(
                        "SELECT sm.id FROM structure_module sm"
                        " JOIN structure_type st ON st.id = sm.structure_type_id"
                        " WHERE sm.module_id = ? AND sm.value = ?"
                        " AND st.meta = 'file' ORDER BY sm.id LIMIT 1",
                        (module_id, value)).fetchone()
                return r["id"] if r else None
            finally:
                _c.close()
        except Exception:
            return None

    def _register_resource_functions(self):
        """登記已用 function 到 resource.registry + structure_resource（冪等）

        2026-10-28（用戶要求）：expected_source 嘅 function 都要 registry——
        terminology 用緊嘅 function（set_expected_source / build_expected_sources /
        add_value / expected_sources 等）同 schema 一樣要喺
        resource.registry（type=function）+ structure_resource（type=function）
        有物理位置（AST 掃 sql.py 真實行號）。
        """
        try:
            import sqlite3 as _sq
            import os as _os
            import importlib.util as _ilu
            _ast_sp = _ilu.spec_from_file_location(
                "_stdlib_ast",
                _os.path.join(_os.path.dirname(_os.__file__), "ast.py"))
            _ast_m = _ilu.module_from_spec(_ast_sp)
            _ast_sp.loader.exec_module(_ast_m)
        except Exception:
            return
        # taxonomy module id（terminology）
        mid = self._taxonomy_id_of("terminology")
        if not mid:
            return
        # AST 掃 terminology/sql.py + api.py 攞 public function -> 真實行號
        # （頂層 function + class 方法都算——set_expected_source 等係 class 方法）
        funcs = {}          # name -> (line, file)
        for pyfile in ("sql.py", "api.py"):
            try:
                with open(rf"C:\projects\meta\terminology\{pyfile}", "r",
                          encoding="utf-8") as f:
                    tree = _ast_m.parse(f.read())
                for node in _ast_m.walk(tree):
                    if isinstance(node, (_ast_m.FunctionDef,
                                         _ast_m.AsyncFunctionDef)):
                        if node.name.startswith("_"):
                            continue
                        # 方法名 -> (行號, 檔名)（class 方法都記）
                        if node.name not in funcs:
                            funcs[node.name] = (node.lineno, pyfile)
            except (OSError, SyntaxError):
                continue
        try:
            from resource import Resource as _R
            _rs = _R()
            try:
                from structure import Structure as _S
                _st = _S()
                try:
                    package_id = self._structure_module_id(mid, None)
                    file_id_sql = self._structure_module_id(mid, "sql.py")
                    file_id_api = self._structure_module_id(mid, "api.py")
                    n = 0
                    for fname, (line, pyfile) in funcs.items():
                        # resource.registry（type=function）
                        _rs.register(
                            "function", f"{pyfile}:{fname}",
                            source_file=f"terminology/{pyfile}",
                            source_line_start=line)
                        # structure_resource（type=function，真實 file_id）
                        if package_id:
                            fid = file_id_api if pyfile == "api.py" \
                                else file_id_sql
                            _st.add_structure_resource(
                                _st.resource_type_id("function"),
                                fname, package_id,
                                line_number=line, file_id=fid)
                        n += 1
                finally:
                    _st.close()
            finally:
                _rs.close()
        except Exception:
            return
        if n:
            print(f"[terminology] resource.registry 真實登記：{n} 個 function"
                  f"（AST 掃 sql.py + api.py）")

    def _taxonomy_id_of(self, meta):
        """taxonomy.registry.id by meta（零 hardcode）"""
        try:
            import sqlite3 as _sq
            _c = _sq.connect(r"C:\projects\meta\taxonomy\taxonomy.db")
            try:
                _c.row_factory = _sq.Row
                r = _c.execute(
                    "SELECT id FROM registry WHERE tree_id = 2"
                    " AND meta = ? AND is_active = 1", (meta,)).fetchone()
                return r["id"] if r else None
            finally:
                _c.close()
        except Exception:
            return None

    def _attach_value_db(self):
        """ATTACH value.db 做 vdb（SSOT：值資產由 value module 擁有）

        冪等：已 ATTACH 就唔再 ATTACH。
        """
        try:
            self.conn.execute("ATTACH DATABASE ? AS vdb",
                              (r"C:\projects\meta\value\value.db",))
        except sqlite3.OperationalError:
            pass  # 已 ATTACH
        self._migrate_drop_removed_tables()
        self._migrate_test_condition()
        self._migrate_flow_run_rename()
        self._migrate_step_drop_child_flow()
        self._migrate_step_action_columns()
        self._migrate_run_answer_id()
        self._migrate_question_condition_id()
        self._migrate_question_operator_id()
        self._migrate_parent_flow_rename()
        self._migrate_branch_tables()
        self._migrate_word_industry_evidence()
        self._migrate_run_evidence_id()
        self._migrate_run_role_id()
        self._migrate_proof_flows()
        self._migrate_split_flow()
        self._migrate_migrate_audit_flow()
        self._migrate_migration_flows()
        self._migrate_questions_6x2()
        self._repair_dangling_steps()
        self._migrate_expected_source_value_id()
        self._migrate_step_output_value()
        self._migrate_drop_formula_cutter_id()
        self._migrate_expected_source_formula()
        self._migrate_question_expected_source_id()
        self._seed_step_input()
        self._migrate_source_register_defaults()
        self._migrate_value_taxonomy_id()
        self._seed()

    def _migrate_run_role_id(self):
        """遷移（幂等）：run 加 role_id 欄（2026-10-27 用戶要求）

        proof / verify 係 flow（唔係 module）—— 執行記錄喺 run 表，
        role_id = role.db registry.id（邊個角色執行）。
        """
        cols = {c[1] for c in self.conn.execute(
            "PRAGMA table_info('run')")}
        if "role_id" not in cols:
            self.conn.execute("ALTER TABLE run ADD COLUMN role_id INTEGER")
            self.conn.commit()
            print("[terminology] run 表加 role_id 欄")
        if "rule_id" not in cols:
            self.conn.execute("ALTER TABLE run ADD COLUMN rule_id INTEGER")
            self.conn.commit()
            print("[terminology] run 表加 rule_id 欄")

    def _migrate_drop_value_table(self):
        """遷移（幂等）：drop 舊遺留 value 表（2026-10-28 用戶確認）

        value 係獨立 module（value.db SSOT），terminology ATTACH 做 vdb。
        呢張表係 clone 時代遺留（27 行測試垃圾，無 FK 引用）—— 直接 drop。
        """
        has = self.conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='value'"
        ).fetchone()
        if not has:
            return
        n = self.conn.execute("SELECT COUNT(*) c FROM value").fetchone()["c"]
        self.conn.execute("DROP TABLE value")
        self.conn.commit()
        print(f"[migrate] terminology drop 舊遺留 value 表（{n} 行測試資料）")

    def _migrate_registry_schema(self):
        """重建舊 registry 定義；非空舊表無法無損映射時明確停止。"""
        cols = {r[1] for r in self.conn.execute(
            "PRAGMA table_info('registry')")}
        if not cols or cols == {"id", "value_id", "modele_skill_id",
                                "flow_pass_id"}:
            return
        count = self.conn.execute("SELECT COUNT(*) FROM registry").fetchone()[0]
        if count:
            raise ValueError(
                "舊 registry 有資料，無法自動轉成 value_id/modele_skill_id/"
                "flow_pass_id；請先手動遷移")
        self.conn.execute("DROP TABLE registry")
        self.conn.commit()

    def _migrate_run_evidence_id(self):
        """遷移（幂等）：run 加 evidence_id 欄（2026-10-25 用戶要求）

        run.evidence_id = 證據鏈頭（evidence.id；FAIL run = NULL）
        """
        cols = [c[1] for c in self.conn.execute("PRAGMA table_info('run')")]
        if "evidence_id" in cols:
            return
        self.conn.execute("ALTER TABLE run ADD COLUMN evidence_id INTEGER")
        self.conn.commit()
        print("[migrate] run 加 evidence_id 欄")

    def _migrate_proof_flows(self):
        """遷移（幂等）：evidence / proof / verify 三條證明 flow（2026-10-27 用戶要求）

        flow 表 + condition 表各加 3 個值：
            evidence / proof / verify
        每條 flow 4 個 STEP（5W2H 框架）：
            what   -> 邊個 id（evidence_id / version_id / verify_id）
            where  -> 喺邊個 module（module=evidence / version / verify）
            where  -> 喺邊張表（registry / verify）
            how    -> 點證明（formula_id，formula_type=evidence/proof/verify，status=1）

        冪等：flow_name UNIQUE + condition.meta UNIQUE + step UNIQUE(flow_id, seq_id)
        -> 全部 WHERE NOT EXISTS，重跑唔重複。
        """
        # 1. condition 加 3 個值（meta UNIQUE -> 冪等）
        for meta in ("evidence", "proof", "verify", "source_register"):
            self.conn.execute(
                "INSERT INTO condition (meta)"
                " SELECT ? WHERE NOT EXISTS"
                " (SELECT 1 FROM condition WHERE meta = ?)",
                (meta, meta))
        # 2. flow 加 3 條（flow_name UNIQUE -> 冪等）
        for fname in ("evidence", "proof", "verify", "source_register"):
            self.conn.execute(
                "INSERT INTO flow (flow_name)"
                " SELECT ? WHERE NOT EXISTS"
                " (SELECT 1 FROM flow WHERE flow_name = ?)",
                (fname, fname))
        self.conn.commit()
        # 3. 每條 flow 建 4 個 STEP（what / where / where / how）
        #    question 唔需要新行 —— step 直接指 condition（question_id 用
        #    condition 對應嘅現有 question；冇就建一個淨 condition 嘅 question）
        #    5W2H id：1=what 2=where 6=how
        #    expected：1=真（期望 PASS）
        exp_true = self.conn.execute(
            "SELECT id FROM expected WHERE boolean_id = 1"
            " ORDER BY id LIMIT 1").fetchone()
        exp_id = exp_true["id"] if exp_true else None
        op_eq = self.conn.execute(
            "SELECT id FROM operator WHERE meta = '=='"
            " ORDER BY id LIMIT 1").fetchone()
        op_id = op_eq["id"] if op_eq else None
        w_what, w_where, w_how = 1, 2, 6
        # 每個 flow 嘅 4 步定義（condition_meta, 5w2h_id）
        steps_def = {
            "evidence": [
                ("evidence", w_what),   # what == evidence_id
                ("evidence", w_where),  # where == module=evidence
                ("evidence", w_where),  # where == table=registry
                ("evidence", w_how),    # how == formula_id, type=evidence, status=1
            ],
            "proof": [
                ("proof", w_what),      # what == version_id
                ("proof", w_where),     # where == module=version
                ("proof", w_where),     # where == table=registry
                ("proof", w_how),       # how == formula_id, type=proof, status=1
            ],
            "verify": [
                ("verify", w_what),     # what == verify_id
                ("verify", w_where),    # where == module=verify
                ("verify", w_where),    # where == table=verify
                ("verify", w_how),      # how == formula_id, type=verify, status=1
            ],
            "source_register": [
                ("source_register", w_what),   # what == 詞（word）
                ("source_register", w_where),  # where == source（邊個來源）
                ("source_register", w_where),  # where == source_proof 表
                ("source_register", w_how),    # how == 登記（add_source_proof）
            ],
        }
        for fname, steps in steps_def.items():
            frow = self.conn.execute(
                "SELECT id FROM flow WHERE flow_name = ?", (fname,)).fetchone()
            if not frow:
                continue
            fid = frow["id"]
            for seq, (cmeta, w5) in enumerate(steps, start=1):
                # 已有 step（flow_id + seq_id UNIQUE）-> 跳過
                has = self.conn.execute(
                    "SELECT 1 FROM step WHERE flow_id = ? AND seq_id = ?",
                    (fid, seq)).fetchone()
                if has:
                    continue
                crow = self.conn.execute(
                    "SELECT id FROM condition WHERE meta = ?",
                    (cmeta,)).fetchone()
                if not crow:
                    continue
                # question：condition + 5w2h + expected 組合（UNIQUE 冪等）
                qrow = self.conn.execute(
                    "SELECT id FROM question WHERE condition_id = ?"
                    ' AND "5w2h_id" = ? AND expected_id = ?',
                    (crow["id"], w5, exp_id)).fetchone()
                if qrow:
                    qid = qrow["id"]
                else:
                    cur = self.conn.execute(
                        "INSERT INTO question"
                        " (condition_id, \"5w2h_id\", operator_id, expected_id)"
                        " SELECT ?, ?, ?, ? WHERE NOT EXISTS"
                        " (SELECT 1 FROM question WHERE condition_id = ?"
                        '  AND "5w2h_id" = ? AND expected_id = ?)',
                        (crow["id"], w5, op_id, exp_id,
                         crow["id"], w5, exp_id))
                    qid = cur.lastrowid if cur.rowcount else None
                    if qid is None:
                        qr = self.conn.execute(
                            "SELECT id FROM question WHERE condition_id = ?"
                            ' AND "5w2h_id" = ? AND expected_id = ?',
                            (crow["id"], w5, exp_id)).fetchone()
                        qid = qr["id"] if qr else None
                if not qid:
                    continue
                self.conn.execute(
                    "INSERT INTO step (flow_id, question_id, seq_id)"
                    " SELECT ?, ?, ? WHERE NOT EXISTS"
                    " (SELECT 1 FROM step WHERE flow_id = ? AND seq_id = ?)",
                    (fid, qid, seq, fid, seq))
        self.conn.commit()
        print("[migrate] evidence/proof/verify flow + condition + step 就緒")

    def _migrate_migrate_audit_flow(self):
        """遷移（幂等）：migrate_audit flow（2026-10-28 用戶設計，10-28 晚正名）

        用戶：「all start = migrate」—— flow 統一 `migrate_*` 開頭，
        佢之前叫 migration_audit（唔合規），而家正名 migrate_audit。
        同時跟 1 action = 1 condition 規格：
            3 步 -> 3 conditions（migrate_audit:value / :run / :evidence）
        run_id = terminology.run —— migration 記錄一定要有真 run：
            what   -> value 存在（提交值）
            where  -> run 記錄存在（migration_log 有 row）
            how    -> evidence 產生咗（PASS = 有證據）
        冪等：flow_name UNIQUE + condition.meta UNIQUE + step UNIQUE。
        """
        # 1. 正名（migration_audit -> migrate_audit，冪等）
        old = self.conn.execute(
            "SELECT id FROM flow WHERE flow_name = 'migration_audit'"
        ).fetchone()
        new = self.conn.execute(
            "SELECT id FROM flow WHERE flow_name = 'migrate_audit'").fetchone()
        if old and not new:
            self.conn.execute(
                "UPDATE flow SET flow_name = 'migrate_audit'"
                " WHERE id = ?", (old["id"],))
            self.conn.commit()
            self.conn.execute(
                "DELETE FROM step WHERE flow_id = ?", (old["id"],))
            self.conn.commit()
            print("[migrate] migration_audit -> migrate_audit 正名")
        # 2. flow
        self.conn.execute(
            "INSERT INTO flow (flow_name)"
            " SELECT 'migrate_audit' WHERE NOT EXISTS"
            " (SELECT 1 FROM flow WHERE flow_name = 'migrate_audit')")
        self.conn.commit()
        frow = self.conn.execute(
            "SELECT id FROM flow WHERE flow_name = 'migrate_audit'"
        ).fetchone()
        if not frow:
            return
        fid = frow["id"]
        exp_true = self.conn.execute(
            "SELECT id FROM expected WHERE boolean_id = 1"
            " ORDER BY id LIMIT 1").fetchone()
        exp_id = exp_true["id"] if exp_true else None
        op_eq = self.conn.execute(
            "SELECT id FROM operator WHERE meta = '=='"
            " ORDER BY id LIMIT 1").fetchone()
        op_id = op_eq["id"] if op_eq else None
        if not exp_id or not op_id:
            return
        # 3. 3 步（what=1 / where=2 / how=6），每步一個 condition
        # 2026-10-28（用戶）：flow 已代表 migrate_audit，condition 唔重複前綴，
        # 淨係 action 名（value / run / evidence；撞名共享——evidence 指 condition 21）
        steps_def = [
            ("value", 1, "提交值", "value 存在（migration 值）"),
            ("run", 2, "run 狀態", "run 記錄存在（migration_log 有 row）"),
            ("evidence", 6, "證據", "evidence 產生（PASS = 有證據）"),
        ]
        for seq, (act, w5, inp, out) in enumerate(steps_def, start=1):
            cmeta = act
            self.conn.execute(
                "INSERT INTO condition (meta)"
                " SELECT ? WHERE NOT EXISTS"
                " (SELECT 1 FROM condition WHERE meta = ?)",
                (cmeta, cmeta))
            crow = self.conn.execute(
                "SELECT id FROM condition WHERE meta = ?",
                (cmeta,)).fetchone()
            if not crow:
                continue
            cid = crow["id"]
            qrow = self.conn.execute(
                "SELECT id FROM question WHERE condition_id = ?"
                ' AND "5w2h_id" = ? AND expected_id = ?',
                (cid, w5, exp_id)).fetchone()
            if qrow:
                qid = qrow["id"]
            else:
                cur = self.conn.execute(
                    "INSERT INTO question"
                    " (condition_id, \"5w2h_id\", operator_id, expected_id)"
                    " SELECT ?, ?, ?, ? WHERE NOT EXISTS"
                    " (SELECT 1 FROM question WHERE condition_id = ?"
                    '  AND "5w2h_id" = ? AND expected_id = ?)',
                    (cid, w5, op_id, exp_id, cid, w5, exp_id))
                qid = cur.lastrowid if cur.rowcount else None
                if qid is None:
                    qr = self.conn.execute(
                        "SELECT id FROM question WHERE condition_id = ?"
                        ' AND "5w2h_id" = ? AND expected_id = ?',
                        (cid, w5, exp_id)).fetchone()
                    qid = qr["id"] if qr else None
            if not qid:
                continue
            has = self.conn.execute(
                "SELECT 1 FROM step WHERE flow_id = ? AND seq_id = ?",
                (fid, seq)).fetchone()
            if has:
                self.conn.execute(
                    "UPDATE step SET action = ?, input_desc = ?,"
                    "  output_desc = ? WHERE flow_id = ? AND seq_id = ?",
                    (act, inp, out, fid, seq))
                continue
            self.conn.execute(
                "INSERT INTO step (flow_id, question_id, seq_id,"
                "  action, input_desc, output_desc)"
                " SELECT ?, ?, ?, ?, ?, ? WHERE NOT EXISTS"
                " (SELECT 1 FROM step WHERE flow_id = ? AND seq_id = ?)",
                (fid, qid, seq, act, inp, out, fid, seq))
        self.conn.commit()
        print("[migrate] migrate_audit flow + 3 conditions + steps 就緒")

    def _migrate_split_flow(self):
        """遷移（幂等）：split_value flow + 7 步（5W2H，2026-10-28 用戶要求）

        flow：split_value —— 值拆分嘅證明鏈
        7 步（5W2H 完整 7 維度，缺一不可）：
            what      -> 拆咩（value_id）
            where     -> 邊個 db（value.db）
            when      -> 幾時拆（created_at）
            who       -> 邊個拆（identity）
            why       -> 點解拆（lineage / permit）
            how       -> 點拆（taxonomy × schema × tool + rest_api）
            how much  -> 拆幾多份（split_total）
        冪等：flow_name UNIQUE + step UNIQUE(flow_id, seq_id)
        """
        # 1. flow
        self.conn.execute(
            "INSERT INTO flow (flow_name)"
            " SELECT 'split_value' WHERE NOT EXISTS"
            " (SELECT 1 FROM flow WHERE flow_name = 'split_value')")
        frow = self.conn.execute(
            "SELECT id FROM flow WHERE flow_name = 'split_value'").fetchone()
        if not frow:
            return
        fid = frow["id"]
        # 2. expected + operator
        exp_true = self.conn.execute(
            "SELECT id FROM expected WHERE boolean_id = 1"
            " ORDER BY id LIMIT 1").fetchone()
        exp_id = exp_true["id"] if exp_true else None
        op_eq = self.conn.execute(
            "SELECT id FROM operator WHERE meta = '=='"
            " ORDER BY id LIMIT 1").fetchone()
        op_id = op_eq["id"] if op_eq else None
        if not exp_id or not op_id:
            return
        # 3. 7 步定義（condition_id 用 split_value condition；5w2h_id 1-7）
        crow = self.conn.execute(
            "SELECT id FROM condition WHERE meta = 'split_value'"
        ).fetchone()
        if not crow:
            cur = self.conn.execute(
                "INSERT INTO condition (meta)"
                " SELECT 'split_value' WHERE NOT EXISTS"
                " (SELECT 1 FROM condition WHERE meta = 'split_value')")
            self.conn.commit()
            crow = self.conn.execute(
                "SELECT id FROM condition WHERE meta = 'split_value'").fetchone()
        if not crow:
            return
        cid = crow["id"]
        # 5W2H id 1-7：what/where/when/who/why/how/how much（完整 7 維度）
        # 修正（2026-10-28 用戶目測）：舊版 [1,2,2,3,4,5,7] 缺 how(6) -> 改完整
        w_ids = [1, 2, 3, 4, 5, 6, 7]
        # 4. 修復（冪等閘）：只得「維度唔齊」先刪舊 steps 重建
        #    （舊 bug：dimension 缺 how(6) -> 直接重建；齊 7 維就唔郁）
        dim_covered = {x[0] for x in self.conn.execute(
            "SELECT DISTINCT q.\"5w2h_id\" FROM step s"
            " JOIN question q ON q.id = s.question_id"
            " WHERE s.flow_id = ? AND s.is_active = 1", (fid,))}
        if dim_covered and dim_covered != set(w_ids):
            self.conn.execute("DELETE FROM step WHERE flow_id = ?", (fid,))
            self.conn.commit()
            print("[migrate] split_value 舊 step 維度唔齊 -> 重建")
        # 5. 建 step（每步一個 question：condition × 5w2h × expected）
        for seq, w5 in enumerate(w_ids, start=1):
            has = self.conn.execute(
                "SELECT 1 FROM step WHERE flow_id = ? AND seq_id = ?",
                (fid, seq)).fetchone()
            if has:
                continue
            qrow = self.conn.execute(
                "SELECT id FROM question WHERE condition_id = ?"
                ' AND "5w2h_id" = ? AND expected_id = ?',
                (cid, w5, exp_id)).fetchone()
            if qrow:
                qid = qrow["id"]
            else:
                cur = self.conn.execute(
                    "INSERT INTO question"
                    " (condition_id, \"5w2h_id\", operator_id, expected_id)"
                    " SELECT ?, ?, ?, ? WHERE NOT EXISTS"
                    " (SELECT 1 FROM question WHERE condition_id = ?"
                    '  AND "5w2h_id" = ? AND expected_id = ?)',
                    (cid, w5, op_id, exp_id, cid, w5, exp_id))
                qid = cur.lastrowid if cur.rowcount else None
                if qid is None:
                    qr = self.conn.execute(
                        "SELECT id FROM question WHERE condition_id = ?"
                        ' AND "5w2h_id" = ? AND expected_id = ?',
                        (cid, w5, exp_id)).fetchone()
                    qid = qr["id"] if qr else None
            if not qid:
                continue
            self.conn.execute(
                "INSERT INTO step (flow_id, question_id, seq_id)"
                " SELECT ?, ?, ? WHERE NOT EXISTS"
                " (SELECT 1 FROM step WHERE flow_id = ? AND seq_id = ?)",
                (fid, qid, seq, fid, seq))
        self.conn.commit()
        print("[migrate] split_value flow + 7 步就緒")

    def _migrate_migration_flows(self):
        """遷移（幂等）：5 條 migrate_* flow 入 terminology.db（2026-10-28 用戶要求）

        用戶：「i found flow and step at module migration not at terminology!!」
        之前 5 條 flow（schema/seed/sync/cutover/other × 30 步）只喺 migration.db，
        terminology.db 得 migration_audit 1 條 -> worker 揀唔到 flow。

        2026-10-28 用戶修正：
            -> 每個 action **一個 condition**（1 action = 1 condition，唔共享）
            -> action/input_desc/output_desc 全部落 step 表（表係 main，零 hardcode）
        """
        # 5 條 flow：flow_name -> [(action, 5w2h dimension, input, output)]
        # 全部用真實 5W2H 7 維度（what/where/when/who/why/how/how much）
        # 每個 action 一個 condition（meta = f"{flow}_" + action 或 action 名）
        flows = {
            "migrate_schema": [
                ("inspect_table", "what", "table 名", "現有欄位清單（PRAGMA table_info）"),
                ("check_column", "where", "欄位名", "欄位存在/唔存在（0/1）"),
                ("add_column", "how", "欄位名 + 型別", "ALTER TABLE 完成"),
                ("backfill_column", "who", "舊資料 + 新欄", "回填行數"),
                ("verify_column", "why", "新欄位名", "PRAGMA 確認欄位存在"),
                ("verify_rowcount", "how much", "表名", "行數零損失確認"),
                ("report", "when", "全部結果", "migration 報告"),
            ],
            "migrate_seed": [
                ("check_dictionary", "what", "字典表名", "現有值清單"),
                ("check_symbol", "where", "symbol 名", "已存在/未存在（0/1）"),
                ("insert_symbol", "how", "symbol + description", "INSERT 完成（冪等）"),
                ("verify_symbol", "why", "symbol 名", "SELECT 確認存在"),
                ("report", "when", "全部結果", "seed 報告"),
            ],
            "migrate_sync": [
                ("check_source", "what", "來源名", "現有記錄"),
                ("fetch_external", "where", "外部 API URL", "原始返回（raw_json）"),
                ("map_to_local", "how", "原始數據", "本地結構映射"),
                ("upsert_local", "who", "映射後數據", "INSERT/UPDATE 完成（冪等）"),
                ("verify_count", "how much", "表名", "新增/更新行數"),
                ("report", "when", "全部結果", "sync 報告"),
            ],
            "migrate_cutover": [
                ("backup_table", "what", "表名", "備份完成"),
                ("create_new_table", "where", "新 DDL", "新表建立"),
                ("copy_rows", "how", "舊表 -> 新表", "複製行數"),
                ("verify_rowcount", "how much", "新舊表", "行數對比（零損失）"),
                ("swap_table", "who", "新表名", "RENAME 完成"),
                ("verify_foreign_keys", "why", "表名", "foreign_key_check 乾淨"),
                ("report", "when", "全部結果", "cutover 報告"),
            ],
            "migrate_other": [
                ("inspect", "what", "描述", "現狀"),
                ("action", "how", "輸入", "輸出"),
                ("verify", "how much", "預期", "實際"),
                ("report", "when", "全部結果", "報告"),
            ],
        }
        exp_true = self.conn.execute(
            "SELECT id FROM expected WHERE boolean_id = 1"
            " ORDER BY id LIMIT 1").fetchone()
        exp_id = exp_true["id"] if exp_true else None
        op_eq = self.conn.execute(
            "SELECT id FROM operator WHERE meta = '=='"
            " ORDER BY id LIMIT 1").fetchone()
        op_id = op_eq["id"] if op_eq else None
        if not exp_id or not op_id:
            return
        # 清理舊版：migrate_* steps 指住共享 condition「migration」-> 刪，改用
        # 每個 action 一個 condition（1 action = 1 condition，2026-10-28 用戶修正）
        # 2026-10-28（用戶再修正）：flow 已代表 migrate_xxx，condition 唔重複前綴——
        # 淨係 action 名，撞名共享（例如 5 個 flow 嘅 report 用同一個 condition）。
        shared = self.conn.execute(
            "SELECT id FROM condition WHERE meta = 'migration'").fetchone()
        if shared:
            self.conn.execute(
                "DELETE FROM step WHERE flow_id IN ("
                "  SELECT id FROM flow WHERE flow_name LIKE 'migrate_%')"
                " AND question_id IN ("
                "  SELECT q.id FROM question q"
                "  JOIN condition c ON c.id = q.condition_id"
                "  WHERE c.id = ?)", (shared["id"],))
            self.conn.commit()
        # 清理舊 migrate_*:xxx condition（有前綴嗰啲——由 step 先拆開再刪）
        self.conn.execute(
            "DELETE FROM step WHERE flow_id IN ("
            "  SELECT id FROM flow WHERE flow_name LIKE 'migrate_%')"
            " AND question_id IN ("
            "  SELECT q.id FROM question q"
            "  JOIN condition c ON c.id = q.condition_id"
            "  WHERE c.meta LIKE 'migrate_%:%')")
        self.conn.commit()
        for fname, steps in flows.items():
            # flow
            self.conn.execute(
                "INSERT INTO flow (flow_name)"
                " SELECT ? WHERE NOT EXISTS"
                " (SELECT 1 FROM flow WHERE flow_name = ?)",
                (fname, fname))
            frow = self.conn.execute(
                "SELECT id FROM flow WHERE flow_name = ?", (fname,)).fetchone()
            if not frow:
                continue
            fid = frow["id"]
            # step：每步一個 condition（1 action = 1 condition）+ action/input/output 落表
            for seq, (action, w5name, inp, out) in enumerate(steps, start=1):
                w5row = self.conn.execute(
                    'SELECT id FROM "5W2H" WHERE meta = ?', (w5name,)).fetchone()
                if not w5row:
                    continue
                w5 = w5row["id"]
                # condition meta = action 名（flow 已代表 migrate_xxx，唔重複）
                # 撞名共享：e.g. report（5 個 flow 都係同一個 condition）
                cmeta = action
                self.conn.execute(
                    "INSERT INTO condition (meta)"
                    " SELECT ? WHERE NOT EXISTS"
                    " (SELECT 1 FROM condition WHERE meta = ?)",
                    (cmeta, cmeta))
                crow = self.conn.execute(
                    "SELECT id FROM condition WHERE meta = ?",
                    (cmeta,)).fetchone()
                if not crow:
                    continue
                cid = crow["id"]
                # question（each condition × 5w2h × expected）
                qrow = self.conn.execute(
                    "SELECT id FROM question WHERE condition_id = ?"
                    ' AND "5w2h_id" = ? AND expected_id = ?',
                    (cid, w5, exp_id)).fetchone()
                if qrow:
                    qid = qrow["id"]
                else:
                    cur = self.conn.execute(
                        "INSERT INTO question"
                        " (condition_id, \"5w2h_id\", operator_id, expected_id)"
                        " SELECT ?, ?, ?, ? WHERE NOT EXISTS"
                        " (SELECT 1 FROM question WHERE condition_id = ?"
                        '  AND "5w2h_id" = ? AND expected_id = ?)',
                        (cid, w5, op_id, exp_id, cid, w5, exp_id))
                    qid = cur.lastrowid if cur.rowcount else None
                    if qid is None:
                        qr = self.conn.execute(
                            "SELECT id FROM question WHERE condition_id = ?"
                            ' AND "5w2h_id" = ? AND expected_id = ?',
                            (cid, w5, exp_id)).fetchone()
                        qid = qr["id"] if qr else None
                if not qid:
                    continue
                # step（action/input/output 落表）
                has = self.conn.execute(
                    "SELECT 1 FROM step WHERE flow_id = ? AND seq_id = ?",
                    (fid, seq)).fetchone()
                if has:
                    self.conn.execute(
                        "UPDATE step SET action = ?, input_desc = ?,"
                        "  output_desc = ? WHERE flow_id = ? AND seq_id = ?",
                        (action, inp, out, fid, seq))
                    continue
                self.conn.execute(
                    "INSERT INTO step (flow_id, question_id, seq_id,"
                    "  action, input_desc, output_desc)"
                    " SELECT ?, ?, ?, ?, ?, ? WHERE NOT EXISTS"
                    " (SELECT 1 FROM step WHERE flow_id = ? AND seq_id = ?)",
                    (fid, qid, seq, action, inp, out, fid, seq))
        self.conn.commit()
        print("[migrate] 5 條 migrate_* flow 入 terminology 就緒"
              "（1 action = 1 condition，表話事）")

    def _migrate_questions_6x2(self):
        """遷移（幂等）：每個 condition 6 維度 × 2 operator == != = 12 條 question

        用戶要求（2026-10-28）：
            5W2H = all condition must have 6 question
                （what / where / when / who / why / how）
            每條 question 都要 value_id（expected_source.value -> proof at DB）
            yes and not = operator == and != -> 6 × 2 = 12
            how much = measure unit（攞 *_id）—— 唔係提問維度

        只用 6 維度（what/where/when/who/why/how）；how much(7) 由
        step_input（source_table/source_column）做 measure unit 來源。
        冪等：UNIQUE(condition_id, "5w2h_id", operator_id, expected_id)。
        """
        # 2026-10-28 修正：上版誤加 how much -> 刪除維度 7 question
        c_del = self.conn.execute("DELETE FROM question WHERE \"5w2h_id\" = 7")
        if c_del.rowcount:
            self.conn.commit()
            print(f"[migrate] 移除誤加 how much question：{c_del.rowcount} 條")
        op_eq = self.conn.execute(
            "SELECT id FROM operator WHERE meta = '==' ORDER BY id LIMIT 1"
        ).fetchone()
        op_ne = self.conn.execute(
            "SELECT id FROM operator WHERE meta = '!=' ORDER BY id LIMIT 1"
        ).fetchone()
        if not op_eq or not op_ne:
            return
        op_eq, op_ne = op_eq["id"], op_ne["id"]
        exp_true = self.conn.execute(
            "SELECT id FROM expected WHERE boolean_id = 1"
            " ORDER BY id LIMIT 1").fetchone()
        exp_false = self.conn.execute(
            "SELECT id FROM expected WHERE boolean_id = 0"
            " ORDER BY id LIMIT 1").fetchone()
        if not exp_true or not exp_false:
            return
        exp_t, exp_f = exp_true["id"], exp_false["id"]
        # 6 維度（what=1 where=2 when=3 who=4 why=5 how=6）
        dims = [1, 2, 3, 4, 5, 6]
        rows = []
        for cid in [r["id"] for r in self.conn.execute(
                "SELECT id FROM condition WHERE is_active = 1")]:
            for w5 in dims:
                for op, exp in ((op_eq, exp_t), (op_ne, exp_f)):
                    has = self.conn.execute(
                        "SELECT 1 FROM question WHERE condition_id = ?"
                        ' AND "5w2h_id" = ? AND operator_id = ?'
                        " AND expected_id = ?",
                        (cid, w5, op, exp)).fetchone()
                    if has:
                        continue
                    rows.append((cid, w5, op, exp))
        for cid, w5, op, exp in rows:
            self.conn.execute(
                "INSERT INTO question"
                " (condition_id, \"5w2h_id\", operator_id, expected_id)"
                " SELECT ?, ?, ?, ? WHERE NOT EXISTS"
                " (SELECT 1 FROM question WHERE condition_id = ?"
                '  AND "5w2h_id" = ? AND operator_id = ?'
                "  AND expected_id = ?)",
                (cid, w5, op, exp, cid, w5, op, exp))
        self.conn.commit()
        print(f"[migrate] question 6×2 seed：+{len(rows)} 條"
              "（每個 condition 6 維度 × ==/!= = 12）")

    def _repair_dangling_steps(self):
        """遷移（幂等）：修 dangling step（question_id 指住唔存在嘅 question）

        問題（2026-10-28）：刪 how_much(7) question 之後，step 仲指住舊
        question（例如 step159 -> question 91，但 91 已刪）。
        修法：step 嘅 condition（由 action 名查）-> 攞該 condition 第一條
        有效 question（6 維度）補返。how much 累計由 _save_step_outputs
        （flow 行完先寫），唔靠 step 指住 how_much question。
        """
        rows = self.conn.execute(
            "SELECT s.id, s.question_id, s.action FROM step s").fetchall()
        n = 0
        for s in rows:
            q = self.conn.execute(
                "SELECT id FROM question WHERE id = ?",
                (s["question_id"],)).fetchone()
            if q:
                continue  # 有效
            # condition：由 action 名（condition meta = action 名）
            cr = self.conn.execute(
                "SELECT id FROM condition WHERE meta = ?",
                (s["action"],)).fetchone()
            if not cr:
                continue
            # 攞該 condition 第一條有效 question（== op, expected=1, 6 維度）
            rep = self.conn.execute(
                "SELECT q.id FROM question q"
                " JOIN operator o ON o.id = q.operator_id"
                " WHERE q.condition_id = ? AND o.meta = '=='"
                " AND q.expected_id IS NOT NULL"
                " AND q.\"5w2h_id\" != 7"
                " ORDER BY q.id LIMIT 1", (cr["id"],)).fetchone()
            if not rep:
                continue
            self.conn.execute(
                "UPDATE step SET question_id = ? WHERE id = ?",
                (rep["id"], s["id"]))
            n += 1
        self.conn.commit()
        if n:
            print(f"[migrate] 修 dangling step：{n} 個（question_id 補返）")

    def _migrate_expected_source_value_id(self):
        """遷移（幂等）：expected_source 加 value_id 欄（2026-10-28 用戶要求）

        用戶：「with value_id」—— expected_source 嘅期望值要有 value.db
        證明（proof at db），唔淨係文字。
        """
        cols = {c[1] for c in self.conn.execute(
            "PRAGMA table_info('expected_source')")}
        if "value_id" not in cols:
            self.conn.execute(
                "ALTER TABLE expected_source ADD COLUMN value_id INTEGER")
            self.conn.commit()
            print("[migrate] expected_source + value_id 欄")
            # 回填：現有 value -> value.db 登記
            rows = self.conn.execute(
                "SELECT id, value FROM expected_source"
                " WHERE value IS NOT NULL AND value_id IS NULL").fetchall()
            for r in rows:
                vid = self.add_value(r["value"])
                self.conn.execute(
                    "UPDATE expected_source SET value_id = ? WHERE id = ?",
                    (vid, r["id"]))
            self.conn.commit()
            print(f"[migrate] expected_source value_id 回填：{len(rows)} 行")

    def _migrate_drop_formula_cutter_id(self):
        """遷移（幂等）：expected_source 移除 formula_cutter_id 欄（2026-10-28 用戶）

        SQLite 唔支援 DROP COLUMN（舊版）—— 重建表（有資料保留，
        formula_cutter_id 全 NULL 可安全重建）。
        """
        cols = {c[1] for c in self.conn.execute(
            "PRAGMA table_info('expected_source')")}
        if "formula_cutter_id" not in cols:
            return
        rows = [dict(r) for r in self.conn.execute(
            "SELECT * FROM expected_source ORDER BY id")]
        self.conn.execute("DROP TABLE expected_source")
        self.conn.execute(EXPECTED_SOURCE_DDL)
        for r in rows:
            self.conn.execute(
                "INSERT INTO expected_source"
                " (id, question_id, formula_id, value, value_id,"
                "  output_format, is_active, created_at, updated_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (r["id"], r["question_id"], r["formula_id"], r["value"],
                 r.get("value_id"), r.get("output_format", "1,0"),
                 r.get("is_active", 1), r.get("created_at"),
                 r.get("updated_at") or r.get("created_at")))
        self.conn.commit()
        print(f"[migrate] expected_source 重建（移除 formula_cutter_id）："
              f"{len(rows)} 行保留")

    def _migrate_expected_source_formula(self):
        """遷移（幂等）：expected_source 加 formula 欄（2026-10-28 用戶要求）

        用戶：「+field : formula, so i can see what it is now」
        直接睇到 formula 內容（唔使 JOIN template.db）。
        回填：formula_id 已有 -> 由 template.db formula.full 抄入。
        """
        cols = {c[1] for c in self.conn.execute(
            "PRAGMA table_info('expected_source')")}
        if "formula" not in cols:
            self.conn.execute(
                "ALTER TABLE expected_source ADD COLUMN formula TEXT")
            self.conn.commit()
            print("[migrate] expected_source + formula 欄")
        # 回填：formula_id -> template.db formula.full
        rows = self.conn.execute(
            "SELECT id, formula_id FROM expected_source"
            " WHERE formula_id IS NOT NULL AND formula IS NULL").fetchall()
        if rows:
            try:
                import sqlite3 as _sq
                fc = _sq.connect(r"C:\projects\meta\template\template.db")
                try:
                    fc.row_factory = _sq.Row
                    for r in rows:
                        fr = fc.execute(
                            "SELECT full FROM formula WHERE id = ?",
                            (r["formula_id"],)).fetchone()
                        if fr:
                            self.conn.execute(
                                "UPDATE expected_source SET formula = ?"
                                " WHERE id = ?", (fr["full"], r["id"]))
                    self.conn.commit()
                finally:
                    fc.close()
            except Exception:
                pass
            print(f"[migrate] expected_source formula 回填：{len(rows)} 行")

    def _migrate_step_output_value(self):
        """遷移（幂等）：step_output 加 output_value 欄（2026-10-28 用戶要求）

        how much 累計（flow + step）寫入 output_value（snapshot），
        value 保持 0/1（CHECK 唔畀寫大數）。
        """
        cols = {c[1] for c in self.conn.execute(
            "PRAGMA table_info('step_output')")}
        if "output_value" not in cols:
            self.conn.execute(
                "ALTER TABLE step_output ADD COLUMN output_value TEXT")
            self.conn.commit()
            print("[migrate] step_output + output_value 欄（how much 累計）")

    def _migrate_question_expected_source_id(self):
        """遷移（幂等）：question 加 expected_source_id 欄（2026-10-28 用戶要求）

        用戶：「table : question + field : expected_source_id」
        question 直接指住期望值來源（expected_source.id），
        唔再靠 expected_source.question_id 反查。
        回填：現有 expected_source（有 question_id 嘅）寫返落 question。
        """
        cols = {c[1] for c in self.conn.execute(
            "PRAGMA table_info('question')")}
        if "expected_source_id" not in cols:
            self.conn.execute(
                "ALTER TABLE question ADD COLUMN expected_source_id INTEGER")
            self.conn.commit()
            print("[migrate] question + expected_source_id 欄")
        # 回填：expected_source.question_id -> question.expected_source_id
        rows = self.conn.execute(
            "SELECT es.id AS esid, es.question_id FROM expected_source es"
            " WHERE es.question_id IS NOT NULL").fetchall()
        n = 0
        for r in rows:
            cur = self.conn.execute(
                "UPDATE question SET expected_source_id = ?"
                " WHERE id = ? AND expected_source_id IS NULL",
                (r["esid"], r["question_id"]))
            n += cur.rowcount
        self.conn.commit()
        if n:
            print(f"[migrate] question.expected_source_id 回填：{n} 行")

    def _seed_step_input(self):
        """遷移（幂等）：step_input seed（2026-10-28 用戶設計）

        每個 condition 期望有 7 行 step_input（5W2H 全維度）：
            what      -> value.id
            where     -> (module db 位置)
            when      -> created_at / permit
            who       -> identity.id
            why       -> lineage.id
            how       -> taxonomy/schema/tool id
            how much  -> split_total.id
        source_table / source_column = 呢個維度個 id 喺邊度攞（DB driven）。
        冪等：UNIQUE(condition_id, "5w2h_id")。
        """
        # 確保表存在（全新 DB：建表喺 _attach_value_db 之後先執行）
        self.conn.execute(STEP_INPUT_DDL)
        # 2026-10-28（用戶修正）：source_table/source_column 用「真實表欄」——
        # 表話事，build expected_source 時直接查呢個 db.表.欄 攞 *_id
        #   表名    欄位    對應 5W2H（7 維度）
        rows = [
            (1, "value", "value.id"),            # what      -> 提交值 id
            (2, "module", "module.db"),          # where     -> module db
            (3, "permit", "permit.id"),          # when      -> permit id
            (4, "identity", "identity.id"),      # who       -> identity id
            (5, "lineage", "lineage.id"),        # why       -> lineage id
            (6, "taxonomy", "taxonomy.id"),      # how       -> taxonomy id
            (7, "value", "split_total.id"),      # how much  -> split_total id
        ]
        # 舊格式遷移：source_table 冇「.」嘅舊行 -> 改「db.表」
        for r in self.conn.execute(
                "SELECT id, source_table FROM step_input"
                " WHERE source_table NOT LIKE '%.%'"):
            old = r["source_table"]
            if old in ("value", "module", "permit", "identity", "lineage",
                       "taxonomy", "split_total", "source", "structure",
                       "rule", "role", "worker", "terminology"):
                new = old if old in ("value", "module", "permit", "identity",
                                     "lineage", "taxonomy", "source",
                                     "structure", "rule", "role", "worker",
                                     "terminology") else f"{old}.{old}"
                self.conn.execute(
                    "UPDATE step_input SET source_table = ? WHERE id = ?",
                    (f"{old}.{old}", r["id"]))
        for w5, dbm, spec in rows:
            tbl, col = spec.split(".")
            # 每 condition（例如 split_value）都要有 7 行
            for cid in [r["id"] for r in self.conn.execute(
                    "SELECT id FROM condition WHERE is_active = 1")]:
                self.conn.execute(
                    "INSERT INTO step_input (condition_id, \"5w2h_id\","
                    " source_table, source_column)"
                    " SELECT ?, ?, ?, ? WHERE NOT EXISTS"
                    " (SELECT 1 FROM step_input WHERE condition_id = ?"
                    '  AND "5w2h_id" = ?)',
                    (cid, w5, f"{dbm}.{tbl}", col, cid, w5))
        self.conn.commit()
        print("[migrate] step_input 7 維度 seed 就緒（真實表欄）")

    def flow_completeness(self, flow_name=None):
        """測量：每條 flow 喺 5W2H 7 維度嘅完整度（2026-10-28 用戶設計）

        概念：flow = 6 維度（what/who/why/when/where/how）× how much
              = 12 格 × (期望/實際 yes-no) = 24 格
        度法：實際 step 用咗邊啲 5w2h_id ⨯ step_input 期望有邊啲

        返回：
        {"flows": [{"flow_id", "flow", "step_count", "input_rows",
                     "missing": [5w2h 名...], "wrong_define": [5w2h 名...],
                     "score_n"/"score_d", "score_pct"}],
         "dims": {"total": 7, "used": n, "missing": [...], "wrong": [...]}}
        """
        q = ("SELECT f.id AS fid, f.flow_name,"
             "  COUNT(DISTINCT s.id) AS step_count,"
             "  COUNT(DISTINCT q.\"5w2h_id\") AS dims_used,"
             "  COUNT(DISTINCT si.id) AS input_rows"
             " FROM flow f"
             " LEFT JOIN step s ON s.flow_id = f.id AND s.is_active = 1"
             " LEFT JOIN question q ON q.id = s.question_id"
             " LEFT JOIN step_input si ON si.condition_id = q.condition_id"
             " WHERE f.is_active = 1")
        args = []
        if flow_name:
            q += " AND f.flow_name = ?"
            args.append(flow_name)
        q += " GROUP BY f.id ORDER BY f.id"
        rows = [dict(r) for r in self.conn.execute(q, args)]

        # 7 維度名（5W2H id 1-7）
        w = {r["id"]: r["meta"] for r in self.conn.execute(
            'SELECT id, meta FROM "5W2H"')}
        dims = [str(x) for x in range(1, 8)]

        out = []
        for r in rows:
            fid = r["fid"]
            # 實際 flow 用咗邊啲維度（由 step -> question -> 5w2h_id）
            used = {x[0] for x in self.conn.execute(
                "SELECT DISTINCT q.\"5w2h_id\" FROM step s"
                " JOIN question q ON q.id = s.question_id"
                " WHERE s.flow_id = ? AND s.is_active = 1", (fid,))}
            # step_input 期望有邊啲（condition -> step_input）
            expected = {x[0] for x in self.conn.execute(
                "SELECT DISTINCT si.\"5w2h_id\" FROM step s"
                " JOIN question q ON q.id = s.question_id"
                " JOIN step_input si ON si.condition_id = q.condition_id"
                " WHERE s.flow_id = ? AND s.is_active = 1", (fid,))}
            missing = sorted(expected - used, key=int)   # 期望有但 flow 冇
            wrong = sorted(used - expected, key=int)    # flow 有用但 step_input 冇
            n = len(used & expected)
            d = len(expected) or 1
            out.append({
                "flow_id": fid,
                "flow": r["flow_name"],
                "step_count": r["step_count"] or 0,
                "input_rows": r["input_rows"] or 0,
                "missing": [w.get(int(x), x) for x in missing],
                "wrong_define": [w.get(int(x), x) for x in wrong],
                "score_n": n, "score_d": d,
                "score_pct": round(100.0 * n / d, 1),
            })
        dims_used = {int(x) for x in
                     [d for r in rows for d in r.get("missing", [])]}
        # dims_used 嘅計法要由 rows 度攞（上面 missing 已係名）——
        # 呢度直接重掃一次，確保總計準確
        all_used = set()
        all_exp = set()
        for r in self.conn.execute("SELECT id FROM flow WHERE is_active = 1"):
            fid = r["id"]
            all_used |= {x[0] for x in self.conn.execute(
                "SELECT DISTINCT q.\"5w2h_id\" FROM step s"
                " JOIN question q ON q.id = s.question_id"
                " WHERE s.flow_id = ? AND s.is_active = 1", (fid,))}
            all_exp |= {x[0] for x in self.conn.execute(
                "SELECT DISTINCT si.\"5w2h_id\" FROM step s"
                " JOIN question q ON q.id = s.question_id"
                " JOIN step_input si ON si.condition_id = q.condition_id"
                " WHERE s.flow_id = ? AND s.is_active = 1", (fid,))}
        return {
            "flows": out,
            "dims": {
                "total": 7,
                "used": len(all_used),
                "missing": sorted(
                    [w.get(int(x), x) for x in (all_exp - all_used)], key=str),
                "wrong": sorted(
                    [w.get(int(x), x) for x in (all_used - all_exp)], key=str),
            },
        }

    # ============ expected_source / step_output（2026-10-28 用戶設計）============
    # step_input = 輸入測量；step_output = 輸出測量。
    # 鏈：value -> condition × 5W2H × operator(yes>==, no>!=)
    #          -> expected_source -> output_format = 1,0

    def _build_expected_sources(self, source_module=None):
        """由 question 逐個建 expected_source（2026-10-28 用戶要求）

        用戶：「before you need to have code for each condition 1 by 1,
               now your job is to base on the question to have expect_source,
               as it is *_id, method is which table and which field」

        方法（表話事，零 hardcode）：
            1. 每個 condition 喺 step_input 有 source_table/source_column
               （例如 value.id / module.db / permit.id / identity.id）
            2. source_table 係「模組名」，對應真實 DB：
               value -> value.db、permit -> permit.db、identity -> identity.db、
               module -> module.db、taxonomy -> taxonomy.db、lineage -> lineage.db
            3. 每個 question 由呢個 source 真查 DB 攞 *_id
            4. 寫 expected_source（value = 攞到嘅 *_id，value_id 登記 value.db）

        返回 {"created": n, "skipped": n, "by_module": {...}}
        """
        # step_input: condition -> (5w2h -> source_table/source_column)
        rows = self.conn.execute(
            "SELECT condition_id, \"5w2h_id\", source_table, source_column"
            " FROM step_input WHERE is_active = 1").fetchall()
        src_map = {}
        for r in rows:
            src_map.setdefault(r["condition_id"], {})[r["5w2h_id"]] = (
                r["source_table"], r["source_column"])
        # 模組名 -> (DB 檔, 表名)（source_table = 「db.表」；表話事）
        import os
        META = r"C:\projects\meta"
        def db_of(tblspec):
            """source_table「db.表」 -> (db 路徑, 表名)；攞唔到 -> (None, None)"""
            tblspec = (tblspec or "").strip()
            if "." in tblspec:
                dbm, tbl = tblspec.split(".", 1)
            else:
                dbm, tbl = tblspec, tblspec
            dbm = dbm.strip().lower()
            tbl = tbl.strip()
            if not dbm or not tbl:
                return None, None
            # taxonomy 嘅 id 喺 registry 表
            if dbm == "taxonomy" and tbl == "taxonomy":
                tbl = "registry"
            # identity 嘅 id 喺 registry 表（identity.db 冇 identity 表）
            if dbm == "identity" and tbl == "identity":
                tbl = "registry"
            # split_total 喺 value.db
            if tbl == "split_total":
                return os.path.join(META, "value", "value.db"), "split_total"
            # module 冇 db 檔（where = db 檔名概念，跳過）
            if dbm == "module":
                return None, None
            return os.path.join(META, dbm, f"{dbm}.db"), tbl
        created = skipped = 0
        by_module = {}
        qs = self.conn.execute(
            "SELECT id, condition_id, \"5w2h_id\" FROM question"
            " WHERE is_active = 1 ORDER BY condition_id, \"5w2h_id\"").fetchall()
        for q in qs:
            src = src_map.get(q["condition_id"], {}).get(q["5w2h_id"])
            if not src:
                skipped += 1
                continue
            table, column = src
            # 2026-10-28（用戶修正）：how much（5w2h_id=7）唔係一步攞到——
            # 係 flow + step 累計結果（verify_count / verify_rowcount 步驟先計到）。
            # 呢度唔建 expected_source（點對點證明 = 成條 flow 行完先準確）。
            if q["5w2h_id"] == 7:
                skipped += 1
                continue
            # 已經有 expected_source -> 跳過（冪等）
            has = self.conn.execute(
                "SELECT id FROM expected_source WHERE question_id = ?",
                (q["id"],)).fetchone()
            if has:
                skipped += 1
                continue
            # 真查 DB 攞 *_id
            sid = None
            try:
                import sqlite3 as _sq
                dbp, tbl = db_of(table)
                if dbp and os.path.isfile(dbp):
                    c = _sq.connect(dbp)
                    try:
                        c.row_factory = _sq.Row
                        # column 可能係「id」；攞第一行個 id
                        rr = c.execute(
                            f"SELECT {column} AS v FROM {tbl} LIMIT 1"
                        ).fetchone()
                        sid = rr["v"] if rr else None
                    finally:
                        c.close()
            except Exception:
                sid = None
            if sid is None:
                skipped += 1
                continue
            # formula：準確格式（限 output by id，指明 db_file/表/condition/維度，
            # 唔 select *）—— condition × 5W2H 維度都要指明先精準
            db_file = os.path.basename(dbp) if dbp else ""
            ftext = (f'xxx=<select id from "{tbl}" '
                     f'where condition_id = "{q["condition_id"]}" '
                     f'and "5w2h_id" = "{q["5w2h_id"]}">')
            # 寫 expected_source（value = *_id，value_id 自動登記 + formula 真 id）
            try:
                esid = self.set_expected_source(q["id"], value=str(sid),
                                                formula=ftext)
                # formula 表補 db_file（指明邊個 db，令 formula 更準確）
                if esid:
                    self._formula_db_file(ftext, db_file)
                # 同步 question.expected_source_id（直接指住）
                self.conn.execute(
                    "UPDATE question SET expected_source_id = ? WHERE id = ?",
                    (esid, q["id"]))
                by_module[table] = by_module.get(table, 0) + 1
                created += 1
            except Exception:
                skipped += 1
        self.conn.commit()
        return {"created": created, "skipped": skipped,
                "by_module": by_module}

    def _formula_db_file(self, formula_text, db_file):
        """template.formula 補 db_file 欄（指明邊個 db，零 hardcode）"""
        if not formula_text or not db_file:
            return
        try:
            import sqlite3 as _sq
            fc = _sq.connect(r"C:\projects\meta\template\template.db")
            try:
                fc.row_factory = _sq.Row
                r = fc.execute(
                    "SELECT id FROM formula WHERE full IS ?",
                    (formula_text,)).fetchone()
                if r:
                    fc.execute(
                        "UPDATE formula SET db_file = ? WHERE id = ?"
                        " AND db_file IS NULL", (db_file, r["id"]))
                    fc.commit()
            finally:
                fc.close()
        except Exception:
            pass

    def set_expected_source(self, question_id, formula_id=None,
                            value=None, output_format="1,0", value_id=None,
                            formula=None):
        """設定一條 question 嘅期望值來源（Table-driven，冪等）

        question_id   = terminology.question.id
        formula_id    = template.formula.id（blackbox 公式，執行出期望）
        formula       = formula 內容（直接睇；有內容 -> 自動登記 formula 表攞真 id）
        value         = 期望值（formula 執行結果 / 直接值）
        value_id      = value.db value.id（proof at db；value 自動登記）
        output_format = 輸出格式（1,0 boolean）
        """
        if value_id is None and value is not None:
            value_id = self.add_value(value)
        # formula 內容 -> 登記 template.db 攞真 id（冇傳 formula_id 時）
        formula_text = formula
        if formula_id is None and formula_text:
            try:
                import sqlite3 as _sq
                fc = _sq.connect(r"C:\projects\meta\template\template.db")
                try:
                    fc.row_factory = _sq.Row
                    r = fc.execute(
                        "SELECT id FROM formula WHERE full IS ?",
                        (formula_text,)).fetchone()
                    if r:
                        formula_id = r["id"]
                    else:
                        cur = fc.execute(
                            "INSERT INTO formula (full) SELECT ?"
                            " WHERE NOT EXISTS"
                            " (SELECT 1 FROM formula WHERE full IS ?)",
                            (formula_text, formula_text))
                        fc.commit()
                        r2 = fc.execute(
                            "SELECT id FROM formula WHERE full IS ?",
                            (formula_text,)).fetchone()
                        formula_id = r2["id"] if r2 else cur.lastrowid
                finally:
                    fc.close()
            except Exception:
                pass
        # 已有 -> 更新
        has = self.conn.execute(
            "SELECT id FROM expected_source WHERE question_id = ?"
            " AND formula_id IS ?", (question_id, formula_id)).fetchone()
        if has:
            self.conn.execute(
                "UPDATE expected_source SET"
                " value = ?, value_id = ?, output_format = ?,"
                " formula = COALESCE(?, formula), updated_at ="
                " datetime('now','localtime') WHERE id = ?",
                (value, value_id, output_format, formula_text, has["id"]))
            rid = has["id"]
        else:
            cur = self.conn.execute(
                "INSERT INTO expected_source"
                " (question_id, formula_id, formula, value,"
                "  value_id, output_format)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (question_id, formula_id, formula_text, value,
                 value_id, output_format))
            rid = cur.lastrowid
        self.conn.commit()
        return rid

    def expected_sources(self, question_id=None):
        """列出 expected_source（可按 question 篩選）"""
        sql = ("SELECT es.*, q.condition_id, q.\"5w2h_id\","
               " c.meta AS condition_meta, w.meta AS w5w2h,"
               " op.meta AS operator_meta, e.description AS expected_desc"
               " FROM expected_source es"
               " LEFT JOIN question q ON q.id = es.question_id"
               " LEFT JOIN condition c ON c.id = q.condition_id"
               ' LEFT JOIN "5W2H" w ON w.id = q."5w2h_id"'
               " LEFT JOIN operator op ON op.id = q.operator_id"
               " LEFT JOIN expected e ON e.id = q.expected_id")
        args = ()
        if question_id is not None:
            sql += " WHERE es.question_id = ?"
            args = (question_id,)
        sql += " ORDER BY es.id"
        return [dict(r) for r in self.conn.execute(sql, args)]

    # ---------- question_template（2026-10-28 用戶要求） ----------
    # 每行 = 一條可重用提問定義：value_id | condition_id | operator_id |
    #        expected_source_id | is_active
    def add_question_template(self, value_id=0, condition_id=None,
                              operator_id=None, expected_source_id=None):
        """新增一條 question_template（冪等：UNIQUE 5 鍵）"""
        if condition_id is None or operator_id is None:
            raise ValueError("condition_id / operator_id 至少一個")
        self.conn.execute(
            "INSERT INTO question_template"
            " (value_id, condition_id, operator_id, expected_source_id)"
            " SELECT ?, ?, ?, ? WHERE NOT EXISTS"
            " (SELECT 1 FROM question_template"
            "  WHERE value_id = ? AND condition_id = ? AND operator_id = ?"
            "    AND expected_source_id IS ?)",
            (value_id, condition_id, operator_id, expected_source_id,
             value_id, condition_id, operator_id, expected_source_id))
        self.conn.commit()
        r = self.conn.execute(
            "SELECT id FROM question_template"
            " WHERE value_id = ? AND condition_id = ? AND operator_id = ?"
            "   AND expected_source_id IS ? ORDER BY id DESC LIMIT 1",
            (value_id, condition_id, operator_id, expected_source_id
             )).fetchone()
        return r["id"] if r else None

    def question_templates(self, active_only=True, limit=100):
        """列出 question_template（JOIN condition/operator/expected_source）"""
        sql = ("SELECT qt.*, c.meta AS condition_meta,"
               " op.meta AS operator_meta, es.value AS expected_value,"
               " es.value_id AS expected_value_id"
               " FROM question_template qt"
               " LEFT JOIN condition c ON c.id = qt.condition_id"
               " LEFT JOIN operator op ON op.id = qt.operator_id"
               " LEFT JOIN expected_source es ON es.id = qt.expected_source_id")
        if active_only:
            sql += " WHERE qt.is_active = 1"
        sql += " ORDER BY qt.id DESC LIMIT ?"
        return [dict(r) for r in self.conn.execute(sql, (limit,))]

    def count_question_templates(self):
        return self.conn.execute(
            "SELECT COUNT(*) c FROM question_template").fetchone()["c"]

    def record_step_output(self, step_id, run_id, question_id, value,
                           expert_id=None, output_format="1,0"):
        """記錄一步嘅實際輸出（2026-10-28 用戶設計）

        step_id   = step.id
        run_id    = run.id（邊次執行）
        question_id = question.id
        value     = 實際輸出（1 或 0，output_format 化）
        expert_id = 邊個判斷（identity / skill.id）
        冪等：UNIQUE(run_id, step_id, question_id)
        """
        # expected_id：由 question 攞（expected 1/0）
        q = self.conn.execute(
            "SELECT expected_id FROM question WHERE id = ?",
            (question_id,)).fetchone()
        exp_id = q["expected_id"] if q else None
        v = 1 if str(value).strip().lower() in ("1", "true", "yes", "pass") \
            else 0
        self.conn.execute(
            "INSERT INTO step_output"
            " (step_id, run_id, question_id, expert_id, expected_id, value,"
            "  output_format)"
            " SELECT ?, ?, ?, ?, ?, ?, ? WHERE NOT EXISTS"
            " (SELECT 1 FROM step_output WHERE run_id = ?"
            "  AND step_id = ? AND question_id = ?)",
            (step_id, run_id, question_id, expert_id, exp_id, v,
             output_format, run_id, step_id, question_id))
        self.conn.commit()
        return v

    def step_outputs(self, run_id=None, step_id=None):
        """列出 step_output（可按 run / step 篩選）"""
        sql = ("SELECT so.*, s.seq_id, f.flow_name,"
               " c.meta AS condition_meta, w.meta AS w5w2h,"
               " e.description AS expected_desc"
               " FROM step_output so"
               " LEFT JOIN step s ON s.id = so.step_id"
               " LEFT JOIN flow f ON f.id = s.flow_id"
               " LEFT JOIN question q ON q.id = so.question_id"
               " LEFT JOIN condition c ON c.id = q.condition_id"
               ' LEFT JOIN "5W2H" w ON w.id = q."5w2h_id"'
               " LEFT JOIN expected e ON e.id = so.expected_id")
        args = ()
        if run_id is not None:
            sql += " WHERE so.run_id = ?"
            args = (run_id,)
        elif step_id is not None:
            sql += " WHERE so.step_id = ?"
            args = (step_id,)
        sql += " ORDER BY so.id"
        return [dict(r) for r in self.conn.execute(sql, args)]

    def output_completeness(self, flow_name=None):
        """測量：每條 flow 嘅輸出完整度（step_output / expected_source 對比）

        回傳每 flow：
          output_rows    = step_output 實際記錄咗幾行
          expected_rows  = 應有幾多（step × expected_source）
          missing        = 冇 expected_source 嘅 question
          score_n/d/pct
        """
        q = ("SELECT f.id AS fid, f.flow_name,"
             " COUNT(DISTINCT s.id) AS step_count,"
             " COUNT(DISTINCT s.question_id) AS question_count"
             " FROM flow f"
             " LEFT JOIN step s ON s.flow_id = f.id AND s.is_active = 1"
             " WHERE f.is_active = 1")
        args = ()
        if flow_name:
            q += " AND f.flow_name = ?"
            args = (flow_name,)
        q += " GROUP BY f.id ORDER BY f.id"
        rows = [dict(r) for r in self.conn.execute(q, args)]
        out = []
        for r in rows:
            fid = r["fid"]
            # 呢條 flow 用到嘅 questions
            qids = [x[0] for x in self.conn.execute(
                "SELECT DISTINCT q.id FROM step s"
                " JOIN question q ON q.id = s.question_id"
                " WHERE s.flow_id = ? AND s.is_active = 1", (fid,))]
            # 有 expected_source 嘅（期望）
            exp_ids = {x[0] for x in self.conn.execute(
                "SELECT question_id FROM expected_source"
                " WHERE is_active = 1")}
            missing = [qid for qid in qids if qid not in exp_ids]
            # 實際 output 行數
            on = self.conn.execute(
                "SELECT COUNT(*) c FROM step_output so"
                " JOIN step s ON s.id = so.step_id"
                " WHERE s.flow_id = ?", (fid,)).fetchone()["c"]
            n = len(qids) - len(missing)
            d = len(qids) or 1
            out.append({
                "flow_id": fid,
                "flow": r["flow_name"],
                "step_count": r["step_count"] or 0,
                "question_count": r["question_count"] or 0,
                "output_rows": on or 0,
                "missing_expected": len(missing),
                "score_n": n, "score_d": d,
                "score_pct": round(100.0 * n / d, 1),
            })
        return {"flows": out}

    # ---------- output_by / output_type / hardcode_value（2026-10-28 用戶設計）----------
    # 分辨「設計 by code 定 by table」：
    #   db_field_check / db_field_option（structure.db）已標明
    #   id 來源 = 邊張 db_table 邊個 db_field。
    #   未經呢條路（寫死值）= hardcode -> hardcode_value 表記錄。

    def output_types(self, active_only=True):
        """列出 output_type（code / db_table）"""
        sql = "SELECT * FROM output_type"
        if active_only:
            sql += " WHERE is_active = 1"
        sql += " ORDER BY id"
        return [dict(r) for r in self.conn.execute(sql)]

    def output_type_id(self, meta):
        """output_type.id by meta（code / db_table）"""
        r = self.conn.execute(
            "SELECT id FROM output_type WHERE meta = ?", (meta,)).fetchone()
        return r["id"] if r else None

    def set_output_by(self, output_id, output_type_meta):
        """記錄一個 output 嘅來源方式（code / db_table，冪等）"""
        tid = self.output_type_id(output_type_meta)
        if not tid:
            raise ValueError(f"output_type 唔存在: {output_type_meta!r}")
        self.conn.execute(
            "INSERT INTO output_by (output_id, output_type_id)"
            " SELECT ?, ? WHERE NOT EXISTS"
            " (SELECT 1 FROM output_by WHERE output_id = ?"
            "  AND output_type_id = ?)",
            (output_id, tid, output_id, tid))
        self.conn.commit()
        return tid

    def output_bys(self, output_type_meta=None):
        """列出 output_by（可按來源方式篩選）"""
        sql = ("SELECT ob.*, ot.meta AS output_type, so.question_id,"
               " so.value AS output_value, so.run_id, so.step_id"
               " FROM output_by ob"
               " LEFT JOIN output_type ot ON ot.id = ob.output_type_id"
               " LEFT JOIN step_output so ON so.id = ob.output_id")
        args = ()
        if output_type_meta:
            sql += " WHERE ot.meta = ?"
            args = (output_type_meta,)
        sql += " ORDER BY ob.id"
        return [dict(r) for r in self.conn.execute(sql, args)]

    def add_hardcode_value(self, value_id, package_id=None, file_id=None,
                          taxonomy_id=None, skill_id=None):
        """標記一個硬編碼值（冇 db_table/db_field 出處，冪等）"""
        self.conn.execute(
            "INSERT INTO hardcode_value"
            " (value_id, package_id, file_id, taxonomy_id, skill_id)"
            " SELECT ?, ?, ?, ?, ? WHERE NOT EXISTS"
            " (SELECT 1 FROM hardcode_value WHERE value_id = ?"
            "  AND package_id IS ? AND file_id IS ? AND taxonomy_id IS ?"
            "  AND skill_id IS ?)",
            (value_id, package_id, file_id, taxonomy_id, skill_id,
             value_id, package_id, file_id, taxonomy_id, skill_id))
        self.conn.commit()
        # 攞返 id（剛插入或已有）
        r = self.conn.execute(
            "SELECT id FROM hardcode_value WHERE value_id = ?"
            " AND package_id IS ? AND file_id IS ?"
            " AND taxonomy_id IS ? AND skill_id IS ?",
            (value_id, package_id, file_id, taxonomy_id, skill_id)).fetchone()
        return r["id"] if r else None

    def hardcode_values(self, active_only=True):
        """列出硬編碼值（JOIN value db 攞值文字）"""
        sql = ("SELECT hv.*, vdb.value AS value_text"
               " FROM hardcode_value hv"
               " LEFT JOIN vdb.value v ON v.id = hv.value_id")
        if active_only:
            sql += " WHERE hv.is_active = 1"
        sql += " ORDER BY hv.id"
        return [dict(r) for r in self.conn.execute(sql)]

    def hardcode_monitor(self):
        """監控：全站硬編碼值統計（by package / by skill）"""
        # package_id / skill_id 係外站 id（taxonomy.db / skill.db），
        # 呢度淨係統計 id 分佈（DB driven：id 就係身份，名稱由外站解）
        by_pkg = [dict(r) for r in self.conn.execute(
            "SELECT hv.package_id, COUNT(*) AS total"
            " FROM hardcode_value hv"
            " WHERE hv.is_active = 1"
            " GROUP BY hv.package_id ORDER BY total DESC")]
        by_skill = [dict(r) for r in self.conn.execute(
            "SELECT hv.skill_id, COUNT(*) AS total"
            " FROM hardcode_value hv"
            " WHERE hv.is_active = 1"
            " GROUP BY hv.skill_id ORDER BY total DESC")]
        total = self.conn.execute(
            "SELECT COUNT(*) c FROM hardcode_value WHERE is_active = 1"
        ).fetchone()["c"]
        return {"total": total, "by_package": by_pkg, "by_skill": by_skill}

    def scan_hardcodes(self, module_name):
        """AST 掃描一個 module：自動登記 hardcode_value（2026-10-28）

        流程：
            1. 掃 <META>/<module_name>/*.py 嘅 AST（標準庫 ast，唔係 cwd ast）
            2. 每個 Constant 字面值（str/int）：
               - 喺 structure.db db_field_option 允許值入面（任何真欄位）
                 -> 唔係 hardcode（由 table 出）
               - 唔喺 -> hardcode -> 登記：
                   value_id    = value.db value（自動 add）
                   package_id  = taxonomy.registry.id（module）
                   file_id     = structure.module.id（file 層）
                   taxonomy_id = taxonomy.registry.id（分類）
                   skill_id    = skill.registry.id（skill，冇 -> None）
            3. 冪等：hardcode_value UNIQUE + value add 都有 WHERE NOT EXISTS

        返回 {"module", "values", "hardcodes", "files", "skipped"}
        """
        import os as _os
        # 標準庫 ast（cwd 有 ast package shadow -> 直接 load 標準庫 ast.py）
        import importlib.util as _ilu
        _ast_sp = _ilu.spec_from_file_location(
            "_stdlib_ast",
            _os.path.join(_os.path.dirname(_os.__file__), "ast.py"))
        _ast_m = _ilu.module_from_spec(_ast_sp)
        _ast_sp.loader.exec_module(_ast_m)
        _stdlib_ast = _ast_m
        _meta_root = r"C:\projects\meta"

        folder = _os.path.join(_meta_root, module_name)
        if not _os.path.isdir(folder):
            return {"module": module_name, "values": 0, "hardcodes": 0,
                    "files": 0, "error": "資料夾唔存在"}
        py_files = sorted(f for f in _os.listdir(folder)
                          if f.endswith(".py") and not f.startswith("_"))

        # 攞 structure / taxonomy / skill id
        package_id, file_ids = self._scan_structure_ids(module_name)

        # 允許值集合（structure.db db_field_option）
        allowed = self._scan_allowed_values()

        n_val = 0
        n_hard = 0
        skipped = []
        for fn in py_files:
            path = _os.path.join(folder, fn)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    tree = _stdlib_ast.parse(f.read(), filename=path)
            except (SyntaxError, UnicodeDecodeError, OSError) as e:
                skipped.append(f"{fn}: {e}")
                continue
            file_id = file_ids.get(fn)
            # docstring = module/class/function 第一個 Constant 字串
            docstrings = set()
            for dnode in _stdlib_ast.walk(tree):
                if isinstance(dnode, (_stdlib_ast.Module,
                                      _stdlib_ast.FunctionDef,
                                      _stdlib_ast.AsyncFunctionDef,
                                      _stdlib_ast.ClassDef)):
                    body = getattr(dnode, "body", [])
                    if body and isinstance(body[0], _stdlib_ast.Expr) \
                            and isinstance(body[0].value,
                                           _stdlib_ast.Constant) \
                            and isinstance(body[0].value.value, str):
                        docstrings.add(id(body[0].value))
            _sql_kw = ("select ", "insert ", "update ", "delete ",
                       "create ", "drop ", "pragma ", "alter ", "attach ",
                       "begin ", "commit", " rollback", " from ", " where ")
            for node in _stdlib_ast.walk(tree):
                if not isinstance(node, _stdlib_ast.Constant):
                    continue
                if id(node) in docstrings:
                    continue
                val = node.value
                if isinstance(val, bool) or val is None:
                    continue
                if isinstance(val, int):
                    continue  # int 太雜（行號/次數），唔當 hardcode 值
                if not isinstance(val, str):
                    continue
                text = val.strip()
                if len(text) < 2 or len(text) > 60:
                    continue  # 太短/太長唔算硬編碼值
                low = text.lower()
                if low.startswith(_sql_kw) or any(k in low for k in
                                                 (" from ", " where ",
                                                  "select ", "insert ",
                                                  "update ", "delete ")):
                    continue  # SQL 字串 = code 本身，唔係資料值
                if text in allowed:
                    continue  # 表驅動（db_field_option 允許值）-> 唔係 hardcode
                # 登記 value + hardcode（counter 跟實際插入，唔係掃描命中）
                vid = self.add_value_from_scan(text)
                if self._insert_hardcode(vid, package_id, file_id):
                    n_hard += 1
                n_val += 1
        self.conn.commit()
        return {"module": module_name, "values": n_val,
                "hardcodes": n_hard, "files": len(py_files),
                "skipped": skipped}

    # ---------- scan_hardcodes helpers ----------
    def _scan_structure_ids(self, module_name):
        """攞 module 嘅 package_id + 每個 file 嘅 structure.module.id"""
        import sqlite3 as _sq
        package_id = None
        file_ids = {}
        # taxonomy.registry.id（tree = module）
        try:
            _c = _sq.connect(r"C:\projects\meta\taxonomy\taxonomy.db")
            _c.row_factory = _sq.Row
            r = _c.execute(
                "SELECT id FROM registry WHERE tree_id ="
                " (SELECT id FROM tree WHERE meta_key = 'module')"
                " AND meta = ?", (module_name,)).fetchone()
            if r:
                package_id = r["id"]
            _c.close()
        except Exception:
            pass
        # structure.db structure_module（type=file 層）
        try:
            _c = _sq.connect(r"C:\projects\meta\structure\structure.db")
            _c.row_factory = _sq.Row
            rows = _c.execute(
                "SELECT sm.id, sm.value FROM structure_module sm"
                " JOIN structure_type st ON st.id = sm.structure_type_id"
                " WHERE st.value = 'file' AND sm.module_id = ?",
                (package_id,)).fetchall() if package_id else []
            for r in rows:
                file_ids[r["value"]] = r["id"]
            _c.close()
        except Exception:
            pass
        return package_id, file_ids

    def _scan_allowed_values(self):
        """structure.db db_field_option 全部允許值（集合）"""
        import sqlite3 as _sq
        try:
            _c = _sq.connect(r"C:\projects\meta\structure\structure.db")
            vals = {r[0] for r in _c.execute(
                "SELECT DISTINCT value FROM db_field_option")}
            _c.close()
            return vals
        except Exception:
            return set()

    def add_value_from_scan(self, text, taxonomy_id=None):
        """value.db add（冪等）—— 掃描到嘅字面值登記做 value"""
        r = self.conn.execute(
            "SELECT id FROM vdb.value WHERE value = ?", (text,)).fetchone()
        if r:
            return r["id"]
        cur = self.conn.execute(
            "INSERT INTO vdb.value (value, taxonomy_id) SELECT ?, ?"
            " WHERE NOT EXISTS (SELECT 1 FROM vdb.value WHERE value = ?)",
            (text, taxonomy_id, text))
        self.conn.commit()
        r2 = self.conn.execute(
            "SELECT id FROM vdb.value WHERE value = ?", (text,)).fetchone()
        return r2["id"] if r2 else cur.lastrowid

    def _insert_hardcode(self, value_id, package_id, file_id):
        """插入 hardcode row；返回 True = 實際插入（False = 已存在）"""
        cur = self.conn.execute(
            "INSERT INTO hardcode_value (value_id, package_id, file_id)"
            " SELECT ?, ?, ? WHERE NOT EXISTS"
            " (SELECT 1 FROM hardcode_value WHERE value_id = ?"
            " AND package_id IS ? AND file_id IS ?)",
            (value_id, package_id, file_id, value_id, package_id, file_id))
        self.conn.commit()
        return cur.rowcount > 0

    def _migrate_word_industry_evidence(self):
        """遷移（幂等）：word_industry -> 通用 evidence 表（2026-10-25）

        word_industry 舊版（spec_id / industry_id 一行）-> 拆做兩條
        evidence 行（condition_id = spec / industry 各自一條）。
        source_id 由 source.db source_proof 查（詞 -> source.id）。
        冇 source 證明 = 冇得寫證據（證據一定要有來源）。

        唔夠 source 證明嘅舊行直接唔搬（唔可以整假資料）。

        新版：evidence（id, value_id, run_id, condition_id,
                         source_id, status_id）
        """
        cols = [c[1] for c in self.conn.execute(
            "PRAGMA table_info('word_industry')")]
        if not cols or "spec_id" not in cols:
            return  # 已經新版 / 唔存在
        rows = [dict(r) for r in self.conn.execute(
            "SELECT * FROM word_industry ORDER BY id")]
        # 舊證據行 -> 拆兩條 evidence（spec / industry），source 要查得到
        n = 0
        for r in rows:
            sp = self.conn.execute(
                "SELECT c.id FROM condition c WHERE c.id = ?",
                (r["spec_id"],)).fetchone()
            ip = self.conn.execute(
                "SELECT c.id FROM condition c WHERE c.id = ?",
                (r["industry_id"],)).fetchone()
            if not sp or not ip:
                continue
            # source_id：由 source.db 查詞 -> source_proof -> source.id
            vid = r["value_id"]
            v = self.conn.execute(
                "SELECT value FROM vdb.value WHERE id = ?", (vid,)).fetchone()
            if not v or v["value"] is None:
                continue
            src = self._source_id_for(v["value"])
            if not src:
                continue
            for cid, status in ((sp["id"], 1), (ip["id"], 1)):
                self.conn.execute(
                    "INSERT INTO evidence"
                    " (value_id, run_id, condition_id, source_id, status_id)"
                    " SELECT ?, ?, ?, ?, ? WHERE NOT EXISTS"
                    " (SELECT 1 FROM evidence WHERE value_id = ?"
                    "  AND run_id = ? AND condition_id = ?)",
                    (vid, r["run_id"], cid, src, status,
                     vid, r["run_id"], cid))
                n += 1
        self.conn.execute("DROP TABLE word_industry")
        self.conn.commit()
        print(f"[migrate] word_industry -> evidence：{len(rows)} 行拆"
              f" {n} 條證據，冇 source 證明嘅唔搬")

    def _source_id_for(self, value):
        """由 source.db 查一個詞嘅 source.id（冇證明返回 None）

        2026-10-27：大小楷唔敏感（source_proof.word 統一細楷比較）。
        零 hardcode：evidence.source_id 一定要指向真實 source。
        """
        try:
            import sqlite3 as _sq
            _c = _sq.connect(r"C:\projects\meta\source\source.db")
            try:
                _c.row_factory = _sq.Row
                r = _c.execute(
                    "SELECT sp.source_id FROM source_proof sp"
                    " WHERE LOWER(sp.word) = LOWER(?) AND sp.is_active = 1"
                    " ORDER BY sp.id LIMIT 1", (value,)).fetchone()
                return r["source_id"] if r else None
            finally:
                _c.close()
        except Exception:
            return None

    def _migrate_source_register_defaults(self):
        """遷移（幂等）：後備 source 入 db_field_option（2026-10-27）

        後備 source（source_register 表未設定詞時用）入 structure.db
        db_field_option（表話事，唔 hardcode）：
            掛喺 structure_db_table='source_register' +
            structure_db_field='source_id' 嘅 option 行。
        冇呢對真表/欄位 -> skip（source_register 表照用）。
        """
        # 搵後備 source_id：source.db 第一個有 official_url 嘅 source
        fallback_src = None
        try:
            import sqlite3 as _sq
            _c = _sq.connect(r"C:\projects\meta\source\source.db")
            try:
                _c.row_factory = _sq.Row
                r = _c.execute(
                    "SELECT s.id FROM source s"
                    " JOIN provider p ON p.id = s.provider_id"
                    " WHERE p.official_url IS NOT NULL"
                    " AND p.official_url != ''"
                    " ORDER BY s.id LIMIT 1").fetchone()
                fallback_src = r["id"] if r else None
            finally:
                _c.close()
        except Exception:
            pass
        if fallback_src is None:
            return
        # 寫入 structure.db db_field_option
        try:
            import sqlite3 as _sq
            sc = _sq.connect(r"C:\projects\meta\structure\structure.db")
            try:
                # 搵 structure_db_table row（table_name='source_register'）
                tr = sc.execute(
                    "SELECT id FROM structure_db_table"
                    " WHERE table_name = 'source_register' LIMIT 1").fetchone()
                fr = sc.execute(
                    "SELECT id FROM structure_db_field"
                    " WHERE field_name = 'source_id' LIMIT 1").fetchone()
                if tr and fr:
                    sc.execute(
                        "INSERT INTO db_field_option"
                        " (structure_db_table_id, structure_db_field_id,"
                        "  db_field_type_id, value, description)"
                        " SELECT ?, ?, ty.id, ?,"
                        "        'source_register fallback source_id'"
                        " FROM db_field_type ty WHERE ty.meta = 'INTEGER'"
                        " WHERE NOT EXISTS"
                        " (SELECT 1 FROM db_field_option"
                        "  WHERE structure_db_table_id = ?"
                        "  AND structure_db_field_id = ? AND value = ?)",
                        (tr[0], fr[0], str(fallback_src),
                         tr[0], fr[0], str(fallback_src)))
                    sc.commit()
            finally:
                sc.close()
        except Exception:
            pass

    def _fallback_source_id(self):
        """後備 source：source_register 表冇設定時用邊個 source（2026-10-27 改名）

        查「source_register 表 + source_id 欄」嘅 db_field_option 值；
        搵唔到 -> 由 source.db 第一個有 official_url 嘅 source 兜底。
        零 hardcode（唔再寫死 8）。
        """
        try:
            import sqlite3 as _sq
            sc = _sq.connect(
                f"file:{r'C:\projects\meta\structure\structure.db'}?mode=ro",
                uri=True)
            try:
                sc.row_factory = _sq.Row
                r = sc.execute(
                    "SELECT o.value FROM db_field_option o"
                    " JOIN structure_db_table t ON t.id = o.structure_db_table_id"
                    " JOIN structure_db_field f ON f.id = o.structure_db_field_id"
                    " WHERE t.table_name = 'source_register'"
                    " AND f.field_name = 'source_id'"
                    " ORDER BY o.id LIMIT 1").fetchone()
                if r:
                    try:
                        return int(r["value"])
                    except Exception:
                        pass
            finally:
                sc.close()
        except Exception:
            pass
        # 兜底：source.db 第一個有 official_url 嘅 source
        try:
            import sqlite3 as _sq
            _c = _sq.connect(r"C:\projects\meta\source\source.db")
            try:
                _c.row_factory = _sq.Row
                r = _c.execute(
                    "SELECT s.id FROM source s"
                    " JOIN provider p ON p.id = s.provider_id"
                    " WHERE p.official_url IS NOT NULL"
                    " AND p.official_url != ''"
                    " ORDER BY s.id LIMIT 1").fetchone()
                return r["id"] if r else None
            finally:
                _c.close()
        except Exception:
            return None

    def get_source(self, word):
        """一個詞用邊個 source（source_register 表話事，2026-10-27）

        優先：source_register 表（word -> source_id，人/API 設定）
        兜底：後備 source（db_field_option / source.db 第一個有 url）
        再兜底：None（唔可以 fake）
        """
        if word:
            r = self.conn.execute(
                "SELECT source_id FROM source_register"
                " WHERE LOWER(word) = LOWER(?) AND is_active = 1"
                " ORDER BY id DESC LIMIT 1", (word,)).fetchone()
            if r and r["source_id"]:
                return r["source_id"]
        return self._fallback_source_id()

    def source_proof_of(self, word):
        """驗證一個詞嘅 source 證明（有冇效，source.db 查）

        返回 {"has": bool, "source_id": n|None, "source": str|None,
              "provider": str|None, "official_url": str|None}
        """
        try:
            from source import Source as _S
            s2 = _S()
            try:
                p = s2.source_proof(str(word or "").lower())
                sid = self._source_id_of_proof(str(word or ""))
                return {"has": p["has"], "source_id": sid,
                        "source": p.get("source"),
                        "provider": p.get("provider"),
                        "official_url": p.get("url")}
            finally:
                s2.close()
        except Exception:
            return {"has": False, "source_id": None, "source": None,
                    "provider": None, "official_url": None}

    def _source_id_of_proof(self, word):
        """由 source_proof 攞一個詞已登記嘅 source_id（冇 = None）"""
        try:
            import sqlite3 as _sq
            _c = _sq.connect(
                f"file:{r'C:\projects\meta\source\source.db'}?mode=ro",
                uri=True)
            try:
                _c.row_factory = _sq.Row
                r = _c.execute(
                    "SELECT source_id FROM source_proof"
                    " WHERE LOWER(word) = LOWER(?) AND is_active = 1"
                    " LIMIT 1", (word,)).fetchone()
                return r["source_id"] if r else None
            finally:
                _c.close()
        except Exception:
            return None

    def _migrate_branch_tables(self):
        """遷移（幂等）：舊 flow_setting/flow_branch 4欄版 -> 新版

        舊 flow_setting（run_id/value_id/condition_id/status_id）
            -> 改名 flow_branch（就係 runtime 記錄表）
        舊 flow_branch（flow/condition/status/next_flow_id）
            -> 改名 next_flow？唔得，結構唔同。
            為避免撞名：舊 flow_branch 存在 -> drop + 等新表重建。
        """
        # 1. flow_setting -> flow_branch（如果 flow_setting 存在而 flow_branch 唔存在）
        has_fs = self.conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='flow_setting'"
        ).fetchone()
        if has_fs:
            has_fb = self.conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='flow_branch'"
            ).fetchone()
            if not has_fb:
                self.conn.execute(
                    "ALTER TABLE flow_setting RENAME TO flow_branch")
                self.conn.commit()
            else:
                # 兩者都有 -> 掉舊 flow_setting（唔要）
                self.conn.execute("DROP TABLE flow_setting")
                self.conn.commit()
        # 2. 舊版 flow_branch（有 next_flow_id 欄 = 規則版）-> 唔啱新版，
        #    但如果佢係 runtime 版（run_id 欄）就保留
        cols = [c[1] for c in self.conn.execute(
            "PRAGMA table_info('flow_branch')")] if self.conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='flow_branch'"
            ).fetchone() else []
        if cols and "next_flow_id" in cols:
            # 之前實作錯咗嘅規則版 -> drop，等新 FLOW_BRANCH_DDL 重建
            self.conn.execute("DROP TABLE flow_branch")
            self.conn.execute(FLOW_BRANCH_DDL)
            self.conn.commit()
        if cols and "run_id" not in cols and cols:
            # 舊規則版冇 run_id 但已經有新版 runtime 欄 -> 保留
            pass
        # 3. next_flow.flow_branch_id 欄 -> flow_target_id（2026-10-25 用戶要求）
        has_nf = self.conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='next_flow'"
        ).fetchone()
        if has_nf:
            ncols = [c[1] for c in self.conn.execute(
                "PRAGMA table_info('next_flow')")]
            if "flow_branch_id" in ncols:
                rows = [dict(r) for r in self.conn.execute(
                    "SELECT * FROM next_flow ORDER BY id")]
                self.conn.execute("DROP TABLE next_flow")
                self.conn.execute(NEXT_FLOW_DDL)
                for r in rows:
                    self.conn.execute(
                        "INSERT INTO next_flow"
                        " (id, flow_id, condition_id, status_id,"
                        "  flow_target_id, is_active, created_at, updated_at)"
                        " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (r["id"], r["flow_id"], r["condition_id"],
                         r["status_id"], r["flow_branch_id"],
                         r.get("is_active", 1), r.get("created_at"),
                         r.get("updated_at") or r.get("created_at")))
                self.conn.commit()
            if "flow_target_id" not in ncols and "flow_branch_id" not in ncols:
                # 空表/新表 -> 冇問題
                pass

    def _migrate_question_condition_id(self):
        """遷移（幂等）：question.test_id 欄 -> condition_id（2026-10-25 用戶要求）

        test 表已改名 condition，欄位 test_id 同步改 condition_id。
        UNIQUE(test_id,...) 引用欄 -> rebuild（保留資料 + id）。
        """
        cols = [c[1] for c in self.conn.execute(
            "PRAGMA table_info('question')")]
        if "test_id" not in cols:
            return
        rows = [dict(r) for r in self.conn.execute(
            "SELECT * FROM question ORDER BY id")]
        self.conn.execute("DROP TABLE question")
        self.conn.execute(QUESTION_DDL)
        for r in rows:
            if r.get("test_id") is None:
                raise ValueError(
                    f"question id={r['id']} test_id 係 NULL —— 唔准")
            self.conn.execute(
                "INSERT INTO question"
                " (id, condition_id, \"5w2h_id\", operator_id, expected_id,"
                "  is_active, created_at, updated_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (r["id"], r["test_id"], r["5w2h_id"],
                 r.get("operator_id"), r.get("expected_id"),
                 r.get("is_active", 1), r.get("created_at"),
                 r.get("updated_at") or r.get("created_at")))
        self.conn.commit()

    def _migrate_drop_removed_tables(self):
        """遷移（幂等）：移除 4 張唔要嘅表（2026-10-25 用戶要求）

        term / data_collect / authority_level / result 全部移除。
        """
        for tbl in ("term", "data_collect", "authority_level", "result"):
            has = self.conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                (tbl,)).fetchone()
            if has:
                self.conn.execute(f'DROP TABLE "{tbl}"')
                self.conn.commit()

    def _migrate_test_condition(self):
        """遷移（幂等）：test 表 -> condition 表（2026-10-25 用戶要求）

        舊 test 表存在 -> RENAME 做 condition（保留 id + 資料）。
        幂等：第二次跑（冇 test 表）-> 跳過。
        """
        has_old = self.conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='test'"
        ).fetchone()
        if not has_old:
            return
        has_new = self.conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='condition'"
        ).fetchone()
        if has_new:
            n = self.conn.execute(
                "SELECT COUNT(*) FROM condition").fetchone()[0]
            if n == 0:
                self.conn.execute("DROP TABLE condition")
            else:
                raise ValueError(
                    "condition 表已存在且有資料，唔可以自動合併（需要人手處理）")
        self.conn.execute("ALTER TABLE test RENAME TO condition")
        self.conn.commit()

    def _migrate_flow_run_rename(self):
        """遷移（幂等）：flow_run/run_flow/run_parent 表全部移除

        2026-10-25（用戶要求）：run_parent 都唔要 ——
        子 flow 執行關係由 flow_branch（runtime 判斷記錄）+ run 表攞，
        唔需要獨立父子表。
        """
        for tbl in ("flow_run", "run_flow", "run_parent"):
            has = self.conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                (tbl,)).fetchone()
            if has:
                self.conn.execute(f'DROP TABLE "{tbl}"')
                self.conn.commit()

    def _migrate_step_drop_child_flow(self):
        """遷移（幂等）：step 移除 child_flow_id 欄（2026-10-25 用戶要求）

        flow 做 step 由 condition 名決定（condition.meta = flow 名），
        唔再需要 child_flow_id。rebuild 表（SQLite 唔畀 DROP 有 index 引用嘅欄）。
        """
        cols = [c[1] for c in self.conn.execute(
            "PRAGMA table_info('step')")]
        if "child_flow_id" not in cols:
            return
        rows = [dict(r) for r in self.conn.execute(
            "SELECT * FROM step ORDER BY id")]
        self.conn.execute("DROP TABLE step")
        self.conn.execute(STEP_DDL)
        for r in rows:
            self.conn.execute(
                "INSERT INTO step"
                " (id, flow_id, question_id, seq_id, is_active,"
                "  created_at, updated_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                (r["id"], r["flow_id"], r["question_id"], r["seq_id"],
                 r.get("is_active", 1), r.get("created_at"),
                 r.get("updated_at") or r.get("created_at")))
        self.conn.commit()

    def _migrate_step_action_columns(self):
        """遷移（幂等）：step 加 action / input_desc / output_desc 欄（2026-10-28）

        用戶：「table is main for setting」—— flow/step 嘅動作定義要落表，
        唔可以淨係喺 coding。呢三欄就係表話事嘅動作定義。
        """
        cols = {c[1] for c in self.conn.execute(
            "PRAGMA table_info('step')")}
        if "action" not in cols:
            self.conn.execute("ALTER TABLE step ADD COLUMN action TEXT")
        if "input_desc" not in cols:
            self.conn.execute("ALTER TABLE step ADD COLUMN input_desc TEXT")
        if "output_desc" not in cols:
            self.conn.execute("ALTER TABLE step ADD COLUMN output_desc TEXT")
        self.conn.commit()

    def _migrate_run_answer_id(self):
        """遷移（幂等）：run 表加 answer_id / expected_id 欄 + 全部欄 NOT NULL

        2026-10-25（用戶要求）：
            - run 加 answer_id
            - run 加 expected_id
            - all table 唔可以有 NULL -> rebuild run 表套 NOT NULL
        """
        cols = [c[1] for c in self.conn.execute(
            "PRAGMA table_info('run')")]
        need_rebuild = "answer_id" not in cols or "expected_id" not in cols
        if not need_rebuild:
            infos = self.conn.execute(
                "PRAGMA table_info('run')").fetchall()
            nn = {r[1]: r[3] for r in infos}
            need_rebuild = any(
                nn.get(c) == 0 for c in
                ("value_id", "step_id", "status_id", "answer_id",
                 "expected_id"))
        if not need_rebuild:
            return
        rows = [dict(r) for r in self.conn.execute(
            "SELECT * FROM run ORDER BY id")]
        # 確保冇 NULL（防 rebuild 失敗）
        for r in rows:
            if r.get("value_id") is None or r.get("step_id") is None or \
               r.get("status_id") is None or r.get("answer_id") is None:
                raise ValueError(
                    f"run id={r['id']} 仲有 NULL 欄 ——"
                    f" 先修好資料（value_id/step_id/status_id/answer_id）")
        # expected_id 回填：按 answer_id（1=真 -> expected boolean 1；2=假 -> 0）
        exp_map = {}
        for e in self.conn.execute("SELECT id, boolean_id FROM expected"):
            if e["boolean_id"] not in exp_map:
                exp_map[e["boolean_id"]] = e["id"]
        self.conn.execute("DROP TABLE run")
        self.conn.execute(RUN_DDL)
        for r in rows:
            aid = r["answer_id"]
            expected_id = r.get("expected_id")
            if expected_id is None:
                bid = 1 if aid == 1 else 0
                expected_id = exp_map.get(bid)
            if expected_id is None:
                raise ValueError(
                    f"run id={r['id']} 搵唔到 expected（answer_id={aid}）——"
                    f" expected 表要有 boolean 0 同 1")
            self.conn.execute(
                "INSERT INTO run"
                " (id, flow_id, value_id, step_id, status_id, answer_id,"
                "  expected_id, is_active, created_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (r["id"], r["flow_id"], r["value_id"], r["step_id"],
                 r["status_id"], r["answer_id"], expected_id,
                 r.get("is_active", 1), r.get("created_at")))
        self.conn.commit()

    def _migrate_parent_flow_rename(self):
        """遷移（幂等）：parent_flow / flow_parent 表全部移除

        2026-10-25（用戶要求）：flow_parent 都唔要 ——
        flow 子流程關係由 step.condition = flow 名判斷，唔需要獨立父子表。
        """
        for tbl in ("parent_flow", "flow_parent"):
            has = self.conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                (tbl,)).fetchone()
            if has:
                self.conn.execute(f'DROP TABLE "{tbl}"')
                self.conn.commit()

    def _migrate_calculation_operator(self):
        """遷移（幂等）：calculation 表 -> operator 表

        2026-10-24（用戶要求）：操作符字典改名 operator（同 question 一致）。
        舊表存在 -> RENAME（保留 id + 資料）。
        幂等：第二次跑（冇 calculation 表）-> 跳過。
        """
        has_old = self.conn.execute(
            "SELECT 1 FROM sqlite_master"
            " WHERE type='table' AND name='calculation'"
        ).fetchone()
        if not has_old:
            return
        has_new = self.conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='operator'"
        ).fetchone()
        if has_new:
            n = self.conn.execute(
                "SELECT COUNT(*) FROM operator").fetchone()[0]
            if n == 0:
                self.conn.execute("DROP TABLE operator")
            else:
                raise ValueError(
                    "operator 表已存在且有資料，唔可以自動合併（需要人手處理）")
        self.conn.execute("ALTER TABLE calculation RENAME TO operator")
        self.conn.commit()

    def _migrate_question_operator_id(self):
        """遷移（幂等）：question.calculation_id 欄 -> operator_id

        2026-10-24（用戶要求）：同 question 一致，欄位名 operator_id。
        幂等：第二次跑（冇 calculation_id 欄）-> 跳過。
        """
        qcols = [c[1] for c in self.conn.execute(
            "PRAGMA table_info('question')")]
        if "calculation_id" not in qcols:
            return
        self.conn.execute(
            "ALTER TABLE question RENAME COLUMN calculation_id TO operator_id")
        self.conn.commit()

    def _seed(self):
        """預設字典（冪等，唔燒 AUTOINCREMENT 號）

        用 `INSERT ... WHERE NOT EXISTS` 而唔係 `INSERT OR IGNORE`：
        實測（2026-10-23）`INSERT OR IGNORE` 撞 UNIQUE 衝突時
        **仍然會遞增 sqlite_sequence** -> 每次開連線都燒號。
        `WHERE NOT EXISTS` 撞時完全唔寫入 -> 唔燒號。
        """
        # boolean（id = value，固定 ID 0/1）
        for bid, desc in DEFAULT_BOOLEANS:
            self.conn.execute(
                "INSERT INTO boolean (id, value, description)"
                " SELECT ?, ?, ? WHERE NOT EXISTS"
                " (SELECT 1 FROM boolean WHERE id = ?)",
                (bid, bid, desc, bid))
        # answer（boolean_id 1=真/有，0=假/冇）
        for bid, desc in DEFAULT_ANSWERS:
            self.conn.execute(
                "INSERT INTO answer (boolean_id, description)"
                " SELECT ?, ? WHERE NOT EXISTS"
                " (SELECT 1 FROM answer WHERE boolean_id IS ?)",
                (bid, desc, bid))
        # expected（boolean_id 1=期望真，0=期望假）
        for bid, desc in DEFAULT_EXPECTEDS:
            self.conn.execute(
                "INSERT INTO expected (boolean_id, description)"
                " SELECT ?, ? WHERE NOT EXISTS"
                " (SELECT 1 FROM expected WHERE boolean_id IS ?)",
                (bid, desc, bid))
        # status（boolean_id 1=approved，0=rejected）
        for bid, desc in DEFAULT_STATUSES:
            self.conn.execute(
                "INSERT INTO status (boolean_id)"
                " SELECT ? WHERE NOT EXISTS"
                " (SELECT 1 FROM status WHERE boolean_id IS ?)",
                (bid, bid))
        # operator（meta UNIQUE；已存在 -> 更新 expression，冪等）
        for meta, expr, desc in DEFAULT_OPERATORS:
            self.conn.execute(
                "INSERT INTO operator (meta, expression, description)"
                " SELECT ?, ?, ? WHERE NOT EXISTS"
                " (SELECT 1 FROM operator WHERE meta = ?)",
                (meta, expr, desc, meta))
            self.conn.execute(
                "UPDATE operator SET expression = ? WHERE meta = ?",
                (expr, meta))
        # 5W2H（7 步：what/where/when/who/why/how/how much，2026-10-28）
        for wmeta in ("what", "where", "when", "who", "why", "how",
                      "how much"):
            self.conn.execute(
                'INSERT INTO "5W2H" (meta)'
                " SELECT ? WHERE NOT EXISTS"
                ' (SELECT 1 FROM "5W2H" WHERE meta = ?)',
                (wmeta, wmeta))
        # output_type（code / db_table，2026-10-28 用戶設計）
        # 確保表存在（建表喺 _attach_value_db 之後先執行 _seed）
        self.conn.execute(OUTPUT_TYPE_DDL)
        for tmeta, desc in (("code", "由程式邏輯產生（blackbox）"),
                            ("db_table", "由真表/欄位查詢產生（data-driven）")):
            self.conn.execute(
                "INSERT INTO output_type (meta, description)"
                " SELECT ?, ? WHERE NOT EXISTS"
                " (SELECT 1 FROM output_type WHERE meta = ?)",
                (tmeta, desc, tmeta))
        self.conn.commit()

    def terms(self, active_only=True):
        sql = "SELECT * FROM term WHERE 1=1"
        args = ()
        if active_only:
            sql += " AND is_active = 1"
        sql += " ORDER BY id"
        return [dict(r) for r in self.conn.execute(sql, args)]

    def term(self, term_id):
        return self.conn.execute(
            "SELECT * FROM term WHERE id = ?", (term_id,)).fetchone()

    def find_by_meta(self, meta):
        return self.conn.execute(
            "SELECT * FROM term WHERE meta = ?", (meta,)).fetchone()

    def insert_term(self, meta, description):
        cur = self.conn.execute(
            "INSERT INTO term (meta, description) VALUES (?, ?)",
            (meta, description))
        return cur.lastrowid

    def update_term(self, term_id, description=None, meta=None):
        sets, args = [], []
        if description is not None:
            sets.append("description = ?"); args.append(description)
        if meta is not None:
            sets.append("meta = ?"); args.append(meta)
        if not sets:
            return
        args.append(term_id)
        self.conn.execute(f"UPDATE term SET {', '.join(sets)} WHERE id = ?", args)

    def deactivate(self, term_id):
        self.conn.execute("UPDATE term SET is_active = 0 WHERE id = ?", (term_id,))

    def count(self):
        return self.conn.execute(
            "SELECT COUNT(*) FROM term WHERE is_active = 1").fetchone()[0]

    # ---- data_collect：每個 resource_id 嘅真實 value ----

    def collect_value(self, resource_id, value):
        """記錄 / 更新一個 resource 嘅 value（upsert，唔整重複行）"""
        old = self.conn.execute(
            "SELECT id FROM data_collect WHERE resource_id = ?",
            (resource_id,)).fetchone()
        if old:
            self.conn.execute(
                "UPDATE data_collect SET value = ?, is_active = 1,"
                " updated_at = datetime('now', 'localtime') WHERE id = ?",
                (value, old["id"]))
        else:
            self.conn.execute(
                "INSERT INTO data_collect (resource_id, value) VALUES (?, ?)",
                (resource_id, value))

    def collect_table_value(self, db_table_id, value):
        """記錄 / 更新一張表（resource.db db_table.id）嘅 value"""
        old = self.conn.execute(
            "SELECT id FROM data_collect WHERE db_table_id = ?",
            (db_table_id,)).fetchone()
        if old:
            self.conn.execute(
                "UPDATE data_collect SET value = ?, is_active = 1,"
                " updated_at = datetime('now', 'localtime') WHERE id = ?",
                (value, old["id"]))
        else:
            self.conn.execute(
                "INSERT INTO data_collect (db_table_id, value) VALUES (?, ?)",
                (db_table_id, value))

    def collect_field_value(self, db_field_id, value):
        """記錄 / 更新一個欄位（resource.db db_field.id）嘅 value"""
        old = self.conn.execute(
            "SELECT id FROM data_collect WHERE db_field_id = ?",
            (db_field_id,)).fetchone()
        if old:
            self.conn.execute(
                "UPDATE data_collect SET value = ?, is_active = 1,"
                " updated_at = datetime('now', 'localtime') WHERE id = ?",
                (value, old["id"]))
        else:
            self.conn.execute(
                "INSERT INTO data_collect (db_field_id, value) VALUES (?, ?)",
                (db_field_id, value))

    def value_of(self, resource_id):
        return self.conn.execute(
            "SELECT * FROM data_collect WHERE resource_id = ? AND is_active = 1",
            (resource_id,)).fetchone()

    def table_value_of(self, db_table_id):
        return self.conn.execute(
            "SELECT * FROM data_collect WHERE db_table_id = ? AND is_active = 1",
            (db_table_id,)).fetchone()

    def field_value_of(self, db_field_id):
        return self.conn.execute(
            "SELECT * FROM data_collect WHERE db_field_id = ? AND is_active = 1",
            (db_field_id,)).fetchone()

    def collected(self, active_only=True):
        sql = "SELECT * FROM data_collect WHERE 1=1"
        args = ()
        if active_only:
            sql += " AND is_active = 1"
        sql += " ORDER BY resource_id"
        return [dict(r) for r in self.conn.execute(sql, args)]

    def update_collected(self, resource_id, value=None, is_active=None):
        sets, args = [], []
        if value is not None:
            sets.append("value = ?"); args.append(value)
        if is_active is not None:
            sets.append("is_active = ?"); args.append(is_active)
        if not sets:
            return
        sets.append("updated_at = datetime('now', 'localtime')")
        args.append(resource_id)
        self.conn.execute(
            f"UPDATE data_collect SET {', '.join(sets)} WHERE resource_id = ?",
            args)

    def deactivate_collected(self, resource_id):
        self.conn.execute(
            "UPDATE data_collect SET is_active = 0,"
            " updated_at = datetime('now', 'localtime')"
            " WHERE resource_id = ?", (resource_id,))

    def count_collected(self):
        return self.conn.execute(
            "SELECT COUNT(*) FROM data_collect WHERE is_active = 1").fetchone()[0]

    # ---------- evidence（通用證據表，2026-10-25） ----------
    def record_evidence(self, value, run_id, condition_meta, status_id=1,
                        source_id=None):
        """寫一條證據：值（value）喺 run 入面通過咗 condition 判斷

        value          = 提交值（e.g. mcp）-> value.id
        run_id         = 證明 run（嗰次 flow 執行，唔可以 fake）
        condition_meta = 通過咗邊個判斷（condition.meta，e.g. spec/industry）
        status_id      = 判斷結果（1=PASS 0=FAIL，boolean.id）
        source_id      = 證明來源（source.db source.id；冇自動查 source_proof）
        返回 evidence.id（INT，已存在 = 攞返舊嗰條）
        """
        vid = self.add_value(value)
        cr = self.conn.execute(
            "SELECT id FROM condition WHERE meta = ?",
            (condition_meta,)).fetchone()
        if not cr:
            raise ValueError(f"condition 唔存在: {condition_meta!r}")
        if source_id is None:
            source_id = self._source_id_for(value)
        if source_id is None:
            raise ValueError(
                f"value {value!r} 冇 source 證明 —— 證據一定要有來源"
                f"（source_id 唔可以 NULL）")
        self.conn.execute(
            "INSERT INTO evidence"
            " (value_id, run_id, condition_id, source_id, status_id)"
            " SELECT ?, ?, ?, ?, ? WHERE NOT EXISTS"
            " (SELECT 1 FROM evidence WHERE value_id = ?"
            "  AND run_id = ? AND condition_id = ?)",
            (vid, run_id, cr["id"], source_id, status_id,
             vid, run_id, cr["id"]))
        self.conn.commit()
        r = self.conn.execute(
            "SELECT id FROM evidence WHERE value_id = ?"
            " AND run_id = ? AND condition_id = ?",
            (vid, run_id, cr["id"])).fetchone()
        return r["id"] if r else None

    def evidence_of(self, value, condition_meta=None, active_only=True):
        """一個值嘅全部證據（可 filter condition）

        返回 rows（JOIN condition 攞 meta；source_id 係 source.db 嘅 id，
        要 source 名自己用 source module 查 —— terminology 唔 clone source）
        """
        vid = self._value_id(value)
        if not vid:
            return []
        sql = ("SELECT e.id AS evidence_id, e.value_id, v.value, e.run_id,"
               " e.condition_id, c.meta AS condition,"
               " e.source_id, e.status_id,"
               " e.is_active, e.created_at"
               " FROM evidence e"
               " LEFT JOIN vdb.value v ON v.id = e.value_id"
               " LEFT JOIN condition c ON c.id = e.condition_id"
               " WHERE LOWER(v.value) = LOWER(?)")
        args = [value]
        if condition_meta:
            sql += " AND c.meta = ?"
            args.append(condition_meta)
        if active_only:
            sql += " AND e.is_active = 1"
        sql += " ORDER BY e.id"
        return [dict(r) for r in self.conn.execute(sql, args)]

    def word_industries(self, value, active_only=True):
        """一個值嘅 industry 證據（冇 PASS 證據 = 唔算行業成員）

        保持 API 名（industry 判斷用）：返回 evidence rows，
        condition.meta='industry' 且 status_id=1。
        """
        return self.evidence_of(value, condition_meta="industry",
                                active_only=active_only)

    def unbind_evidence(self, value, run_id, condition_meta=None):
        """移除證據（幂等）—— 返回 True = 真刪到"""
        vid = self._value_id(value)
        if not vid:
            return False
        if condition_meta:
            cr = self.conn.execute(
                "SELECT id FROM condition WHERE meta = ?",
                (condition_meta,)).fetchone()
            if not cr:
                return False
            cur = self.conn.execute(
                "DELETE FROM evidence WHERE value_id = ? AND run_id = ?"
                " AND condition_id = ?",
                (vid, run_id, cr["id"]))
        else:
            cur = self.conn.execute(
                "DELETE FROM evidence WHERE value_id = ? AND run_id = ?",
                (vid, run_id))
        self.conn.commit()
        return cur.rowcount > 0

    def unbind_word_industry(self, value, run_id):
        """移除一個值嘅 industry 證據（幂等）"""
        return self.unbind_evidence(value, run_id,
                                    condition_meta="industry")

    def _value_id(self, value):
        """由值攞 value.id（唔存在返回 None；value 表喺 value.db）"""
        r = self.conn.execute(
            "SELECT id FROM vdb.value WHERE value IS ?", (value,)).fetchone()
        return r["id"] if r else None

    def _source_id_for(self, value):
        """由 source.db 查一個詞嘅 source.id（冇證明返回 None）

        2026-10-27：大小楷唔敏感（source_proof.word 統一細楷比較）。
        零 hardcode：evidence.source_id 一定要指向真實 source。
        """
        try:
            import sqlite3 as _sq
            _c = _sq.connect(r"C:\projects\meta\source\source.db")
            try:
                _c.row_factory = _sq.Row
                r = _c.execute(
                    "SELECT sp.source_id FROM source_proof sp"
                    " WHERE LOWER(sp.word) = LOWER(?) AND sp.is_active = 1"
                    " ORDER BY sp.id LIMIT 1", (value,)).fetchone()
                return r["source_id"] if r else None
            finally:
                _c.close()
        except Exception:
            return None

    def _industry_of(self, value):
        """由證明鏈查 word 屬邊個行業（零 hardcode，全 DB 查）

        鏈：word -> source_proof -> source -> provider -> industry_id
          -> terminology.industry（跨 DB：source.db 攞 provider.industry_id，
             terminology.db 攞 industry 行）
        證明 = provider 聲稱 + official_url（source 可驗證）。

        返回 {"industry_id", "meta", "description", "source_id",
              "provider", "provider_url"} 如果鏈完整；否則 None
        """
        try:
            import sqlite3 as _sq
            _c = _sq.connect(r"C:\projects\meta\source\source.db")
            try:
                _c.row_factory = _sq.Row
                sp = _c.execute(
                    "SELECT source_id FROM source_proof sp"
                    " WHERE LOWER(sp.word) = LOWER(?) AND sp.is_active = 1"
                    " ORDER BY sp.id LIMIT 1", (value,)).fetchone()
                if not sp:
                    return None
                src = _c.execute(
                    "SELECT provider_id FROM source WHERE id = ?",
                    (sp["source_id"],)).fetchone()
                if not src or not src["provider_id"]:
                    return None
                prov = _c.execute(
                    "SELECT meta, industry_id, official_url"
                    " FROM provider WHERE id = ?",
                    (src["provider_id"],)).fetchone()
                if not prov or not prov["industry_id"]:
                    return None
                ind = self.conn.execute(
                    "SELECT id, meta, description FROM industry WHERE id = ?",
                    (prov["industry_id"],)).fetchone()
                if not ind:
                    return None
                return {"industry_id": ind["id"], "meta": ind["meta"],
                        "description": ind["description"],
                        "source_id": sp["source_id"],
                        "provider": prov["meta"],
                        "provider_url": prov["official_url"]}
            finally:
                _c.close()
        except Exception:
            return None

    def _save_evidence(self, run_id, value_id, steps, judged):
        """flow 全 PASS 時自動寫證據（每步一條 evidence）

        一個 value 全 PASS -> 每個 step 嘅 condition 一條證據：
            (value_id, run_id, condition_id, source_id, status_id=1)
        source_id：由 source.db source_proof 查（詞 -> source.id）。
        冇 source 證明 -> 唔寫該條（證據一定要有來源，唔可以 fake）。

        返回第一個證據 id（evidence_id，run 鏈頭）
        """
        if not judged:
            return None
        if not all(j["is_pass"] for j in judged):
            return None
        vid = self.conn.execute(
            "SELECT value FROM vdb.value WHERE id = ?", (value_id,)).fetchone()
        v = vid["value"] if vid else None
        if v is None:
            return None
        first_id = None
        for s, j in zip(steps, judged):
            if not j["is_pass"]:
                continue
            cr = self.conn.execute(
                "SELECT id FROM condition WHERE meta = ?",
                (s["test"],)).fetchone()
            if not cr:
                continue
            src = self._source_id_for(v)
            if not src:
                continue
            self.conn.execute(
                "INSERT INTO evidence"
                " (value_id, run_id, condition_id, source_id, status_id)"
                " SELECT ?, ?, ?, ?, ? WHERE NOT EXISTS"
                " (SELECT 1 FROM evidence WHERE value_id = ?"
                "  AND run_id = ? AND condition_id = ?)",
                (value_id, run_id, cr["id"], src, 1,
                 value_id, run_id, cr["id"]))
            if first_id is None:
                r = self.conn.execute(
                    "SELECT id FROM evidence WHERE value_id = ?"
                    " AND run_id = ? AND condition_id = ?",
                    (value_id, run_id, cr["id"])).fetchone()
                first_id = r["id"] if r else None
        self.conn.commit()
        return first_id

    def _save_step_outputs(self, run_id, value_id, steps, judged):
        """flow 行完寫 step_output（每步實際輸出 1/0）—— how much = 累計

        用戶（2026-10-28）：how much 唔係一步攞到，係 flow + step 累計。
        - 每步輸出 = 實際判斷（PASS=1 / FAIL=0）入 step_output
        - how much 維度（verify_count / verify_rowcount 累計 steps）：
          flow 行完先寫累計（總 PASS 步數 / 真行數），唔係一步攞。
        冪等：UNIQUE(run_id, step_id, question_id)。
        """
        if not judged:
            return
        total_pass = sum(1 for j in judged if j["is_pass"])
        for s, j in zip(steps, judged):
            qid = s["question_id"]
            # 呢步實際輸出（PASS=1 FAIL=0）
            self.conn.execute(
                "INSERT INTO step_output"
                " (step_id, run_id, question_id, value)"
                " SELECT ?, ?, ?, ? WHERE NOT EXISTS"
                " (SELECT 1 FROM step_output"
                "  WHERE run_id = ? AND step_id = ? AND question_id = ?)",
                (s["id"], run_id, qid, 1 if j["is_pass"] else 0,
                 run_id, s["id"], qid))
            # how much 維度（verify_rowcount / verify_count = 累計 step）：
            # flow 行完先寫累計（總 PASS 步數做 snapshot，value 保持 0/1）
            action = s.get("action") or ""
            if action in ("verify_rowcount", "verify_count") or \
                    s.get("w5w2h") == "how much":
                self.conn.execute(
                    "UPDATE step_output SET output_value = ?"
                    " WHERE run_id = ? AND step_id = ? AND question_id = ?",
                    (str(total_pass), run_id, s["id"], qid))
        self.conn.commit()

    # ---------- word_category（2026-10-26：approved word 自動登記） ----------
    def _register_word_category(self, word):
        """一個 word 全 PASS 之後自動 upsert word_category（真 registry）

        分類欄（全部由真判斷推導，零假資料）：
            english     = 全英文字母（letter 表）
            symbol      = 有冇符號（character symbol 表）
            INT         = 全數字
            single_word = 冇 _ 冇空格
            speech      = 係英文單詞（全字母）
            industry    = 有 industry 證據
            spec        = 有 source 證明
            has_proof   = 有 source 證明（source_proof）

        返回 word_category.id（已存在 = 攞返舊嗰條冪等更新）
        """
        if not word:
            return None
        w = str(word).upper()  # 2026-10-27（用戶要求）：word_category 只存大楷
        # 分類：由 character / source 真查（graceful，唔 crash）
        english = int(w.isalpha() and w.isascii())
        only_int = int(w.isdigit())
        single = int("_" not in w and " " not in w and bool(w))
        has_symbol = 0
        try:
            from character import Character
            _ch = Character()
            try:
                chars = _ch.symbols()
                has_symbol = int(any(c in w for c in chars))
            finally:
                _ch.close()
        except Exception:
            pass
        has_proof = 1 if self._source_id_for(w) else 0
        # industry / spec：evidence 真查
        industry = 1 if self.word_industries(w) else 0
        self.conn.execute(
            "INSERT INTO word_category"
            " (word, english, speech, symbol, INT, single_word,"
            "  industry, spec, has_proof)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
            " ON CONFLICT(word) DO UPDATE SET"
            " english=excluded.english, speech=excluded.speech,"
            " symbol=excluded.symbol, INT=excluded.INT,"
            " single_word=excluded.single_word, industry=excluded.industry,"
            " spec=excluded.spec, has_proof=excluded.has_proof,"
            " updated_at=datetime('now','localtime')",
            (w, english, english, has_symbol, only_int, single,
             industry, has_proof, has_proof))
        self.conn.commit()
        r = self.conn.execute(
            "SELECT id FROM word_category WHERE word = ?", (w,)).fetchone()
        return r["id"] if r else None

    def word_proof(self, word):
        """一個 word 嘅完整證明（registry + 證據鏈 + 來源）

        word_category = 有呢行 = word 被 approved 過（registry 證明）
        evidence      = 通過咗邊啲 condition（value_id + run_id + source_id）
        source        = source.db source 名 + provider + official_url
        runs          = 相關 run（approved/rejected 歷史）

        返回 {"registered": bool, "word_category": {...}, "evidence": [...],
              "source": {...}|None, "runs": [...]}
        """
        w = str(word or "")
        # 2026-10-27（用戶要求）：查證明前先登記 value 表 ——
        # 受查嘅詞一定要有 value row（word_proof 唔可以淨係 SELECT）
        vid = self.add_value(w)
        # 2026-10-27（用戶要求）：proof = 行 flow 產生 run（pass/fail 都有
        # run_id）。word_proof flow 存在 -> 每次查都跑一次（記錄證明）；
        # flow 唔存在 / 失敗 -> 照樣返歷史 runs（graceful）。
        try:
            frow = self.conn.execute(
                "SELECT id, flow_name FROM flow WHERE flow_name = ?"
                " AND is_active = 1", ("word_proof",)).fetchone()
            if frow:
                self.run_flow("word_proof", value=w, save=True)
        except Exception as exc:
            print(f"[terminology] word_proof flow 執行失敗: {exc}")
        cat = self.conn.execute(
            "SELECT * FROM word_category WHERE LOWER(word) = LOWER(?)",
            (w,)).fetchone()
        cat_row = dict(cat) if cat else None
        ev = self.evidence_of(w)
        runs = [dict(r) for r in self.conn.execute(
            """SELECT r.id AS run_id, r.flow_id, f.flow_name, r.status_id,
                      r.status_id AS status, r.created_at
               FROM run r
               JOIN vdb.value v ON v.id = r.value_id
               LEFT JOIN flow f ON f.id = r.flow_id
               WHERE LOWER(v.value) = LOWER(?) ORDER BY r.id DESC LIMIT 10""", (w,))]
        for _r in runs:
            _r["status"] = "approved" if _r["status_id"] == 1 else "rejected"
        # source：由 source.db 攞名（graceful）
        source = None
        try:
            import sqlite3 as _sq
            _c = _sq.connect(r"C:\projects\meta\source\source.db")
            try:
                _c.row_factory = _sq.Row
                sp = _c.execute(
                    "SELECT source_id FROM source_proof"
                    " WHERE LOWER(word) = LOWER(?) AND is_active = 1"
                    " ORDER BY id LIMIT 1", (w,)).fetchone()
                if sp:
                    src = _c.execute(
                        "SELECT s.id, s.source, s.provider_id,"
                        " p.meta AS provider, p.official_url"
                        " FROM source s LEFT JOIN provider p"
                        " ON p.id = s.provider_id WHERE s.id = ?",
                        (sp["source_id"],)).fetchone()
                    if src:
                        source = dict(src)
            finally:
                _c.close()
        except Exception:
            pass
        return {"registered": cat_row is not None,
                "value_id": vid,
                "word_category": cat_row,
                "evidence": ev,
                "source": source,
                "runs": runs}

    # ---------- flow（驗證鏈）—— 自己擁有執行引擎，唔 import question ----------
    def flows(self, active_only=True):
        """列出驗證鏈"""
        sql = "SELECT * FROM flow"
        if active_only:
            sql += " WHERE is_active = 1"
        sql += " ORDER BY id"
        return [dict(r) for r in self.conn.execute(sql)]

    # ---------- flow_branch / next_flow（分支決策，2026-10-25） ----------
    def add_branch_rule(self, flow_name, condition_meta, status_id,
                        target_flow_name):
        """加一條分支規則（冪等，0 hardcode）

        flow_name        = 邊條 flow 跑完分叉（source flow）
        condition_meta   = 用邊個 condition 判斷
        status_id        = 結果（1=PASS 0=FAIL）
        target_flow_name = 呢個結果 -> 去邊條 flow

        next_flow.flow_target_id = 目標 flow id（DB 定義，唔 hardcode）。
        執行時：runtime flow_branch 記錄（run/value/condition/status）
        -> 查 next_flow (flow, condition, status) -> flow_target_id =
        目標 flow -> 自動跑。
        """
        # 檢查 flow / condition 存在
        fr = self.conn.execute(
            "SELECT id FROM flow WHERE flow_name = ?",
            (flow_name,)).fetchone()
        cr = self.conn.execute(
            "SELECT id FROM condition WHERE meta = ?",
            (condition_meta,)).fetchone()
        tr = self.conn.execute(
            "SELECT id FROM flow WHERE flow_name = ?",
            (target_flow_name,)).fetchone()
        if not fr or not cr or not tr:
            raise ValueError(
                f"flow={flow_name!r} condition={condition_meta!r}"
                f" target={target_flow_name!r} 有唔存在")
        # 冪等
        existing = self.conn.execute(
            "SELECT id FROM next_flow WHERE flow_id = ?"
            " AND condition_id = ? AND status_id = ?",
            (fr["id"], cr["id"], status_id)).fetchone()
        if existing:
            return existing["id"]
        self.conn.execute(
            "INSERT INTO next_flow"
            " (flow_id, condition_id, status_id, flow_target_id)"
            " VALUES (?, ?, ?, ?)",
            (fr["id"], cr["id"], status_id, tr["id"]))
        self.conn.commit()
        r = self.conn.execute(
            "SELECT id FROM next_flow WHERE flow_id = ?"
            " AND condition_id = ? AND status_id = ?",
            (fr["id"], cr["id"], status_id)).fetchone()
        return r["id"] if r else None

    def flow_steps(self, flow_name, active_only=True):
        """列出一個 flow 嘅 steps（JOIN condition / operator / expected）

        flow 連結由 next_flow（_do_branch）統一處理 —— step 全係 condition。
        """
        sql = """SELECT s.id, s.flow_id, s.seq_id, sq.seq,
                        s.question_id,
                        s.action,
                        q.condition_id, t.meta AS test,
                        t.meta AS condition_meta,
                        q."5w2h_id", w.meta AS w5w2h,
                        q.operator_id, cz.meta AS operator_meta,
                        cz.expression AS operator_expression,
                        q.expected_id, e.boolean_id AS expected_boolean_id,
                        e.description AS expected_description,
                        q.expected_source_id, es.value AS expected_source_value,
                        es.value_id AS expected_source_value_id
                 FROM step s
                 JOIN flow f ON f.id = s.flow_id
                 LEFT JOIN seq sq ON sq.id = s.seq_id
                 LEFT JOIN question q ON q.id = s.question_id
                 LEFT JOIN condition t ON t.id = q.condition_id
                 LEFT JOIN "5W2H" w ON w.id = q."5w2h_id"
                 LEFT JOIN operator cz ON cz.id = q.operator_id
                 LEFT JOIN expected e ON e.id = q.expected_id
                 LEFT JOIN expected_source es ON es.id = q.expected_source_id
                 WHERE f.flow_name = ?"""
        args = (flow_name,)
        if active_only:
            sql += " AND s.is_active = 1"
        sql += " ORDER BY s.seq_id"
        return [dict(r) for r in self.conn.execute(sql, args)]

    def add_value(self, value, taxonomy_id=None):
        """新增 / 攞一個提交值嘅 id（冪等；value 表喺 value.db）

        taxonomy_id = taxonomy.registry.id（邊個 module 登記，2026-10-27）
        """
        r = self.conn.execute(
            "SELECT id FROM vdb.value WHERE value IS ?", (value,)).fetchone()
        if r:
            # 補 taxonomy_id（第一次登記冇填 -> 而家填）
            if taxonomy_id is not None:
                self.conn.execute(
                    "UPDATE vdb.value SET taxonomy_id = ?"
                    " WHERE id = ? AND taxonomy_id IS NULL",
                    (taxonomy_id, r["id"]))
                self.conn.commit()
            return r["id"]
        cur = self.conn.execute(
            "INSERT INTO vdb.value (value, taxonomy_id) VALUES (?, ?)",
            (value, taxonomy_id))
        self.conn.commit()
        return cur.lastrowid

    def _migrate_value_taxonomy_id(self):
        """遷移（幂等）：value 加 taxonomy_id 欄 + 回填（2026-10-27 用戶要求）

        回填：由 run JOIN flow 反查每個 value 嘅 flow_name，
        flow_name -> taxonomy.registry.meta（module 名）-> taxonomy_id。
        搵唔到 -> NULL（唔假造）。
        value 表而家喺 value.db（vdb）。
        """
        cols = {c[1] for c in self.conn.execute(
            "PRAGMA vdb.table_info('value')")}
        if "taxonomy_id" not in cols:
            self.conn.execute(
                "ALTER TABLE vdb.value ADD COLUMN taxonomy_id INTEGER")
            self.conn.commit()
            print("[migrate] value + taxonomy_id 欄")
        # 回填：value ->（run -> flow_name）-> taxonomy.module id
        n = 0
        try:
            import sqlite3 as _sq
            tc = _sq.connect(r"C:\projects\meta\taxonomy\taxonomy.db")
            tc.row_factory = _sq.Row
            mods = {}
            try:
                for r in tc.execute(
                        "SELECT id, meta FROM registry"
                        " WHERE tree_id = 2 AND is_active = 1"):
                    mods[r["meta"]] = r["id"]
            finally:
                tc.close()
        except Exception:
            mods = {}
        rows = self.conn.execute(
            "SELECT v.id, v.value FROM vdb.value v"
            " WHERE v.taxonomy_id IS NULL").fetchall()
        for r in rows:
            # 由 run 搵 flow_name（最近一次）
            fr = self.conn.execute(
                "SELECT f.flow_name FROM run r"
                " JOIN flow f ON f.id = r.flow_id"
                " JOIN vdb.value v ON v.id = r.value_id"
                " WHERE v.id = ? ORDER BY r.id DESC LIMIT 1",
                (r["id"],)).fetchone()
            if not fr:
                continue
            tid = mods.get(fr["flow_name"])
            if tid:
                self.conn.execute(
                    "UPDATE vdb.value SET taxonomy_id = ? WHERE id = ?",
                    (tid, r["id"]))
                n += 1
        self.conn.commit()
        if n:
            print(f"[migrate] value.taxonomy_id 回填：{n} 行")
        return n

    def _judge(self, expression, pass_value, answer):
        """由 operator expression 判斷（自己 eval，自己擁有）

        expression = operator.expression（answer = 答案，pass_value = 期望值）
        """
        expr = expression or \
            "answer is not None and answer != '' and answer != 0"
        safe = {"int": int, "float": float, "str": str, "bool": bool,
                "len": len, "abs": abs}
        try:
            return bool(eval(expr, {"__builtins__": safe}, {
                "answer": answer, "pass_value": pass_value}))
        except Exception:
            return False

    def _auto_answers(self, flow_name, value):
        """由值 + flow steps 自動計 answers（自己擁有，唔靠 question）

        flow 做 step（condition.meta 係 flow 名）-> 唔填（遞歸時子 flow 再自己計）。
        每個 condition 一個判斷（字符集由 character / source 提供）：
            symbol       -> 值有冇符號（character symbol 表）
            spec         -> 值有 source 證明（source_proof）
            industry     -> 值有 industry 證據（evidence 表）
            letter       -> 值全部係英文字母
            single word  -> 值冇 _ 冇空格
            speech       -> 值係英文單詞（全字母）
            spelling     -> 值喺 word_category
            approved     -> 值有 approved run 記錄（chain of proof）
            proof/source -> 值有 source 證明（source_proof）
            其他         -> 有嘢 = 1
        """
        answers = {}
        # 2026-10-25：子 flow 由 next_flow 分支處理（唔再喺 step 判斷）
        for s in self.flow_steps(flow_name):
            test = s["test"]
            v = value or ""
            # 2026-10-27（用戶要求）：判斷唔分大小楷 ——
            # 查 source / word_category / run / evidence 全部 LOWER 比較
            vl = v.lower()
            if test == "symbol":
                try:
                    from character import Character
                    ch = Character()
                    try:
                        chars = ch.symbols()
                        answers[s["question_id"]] = \
                            1 if any(c in v for c in chars) else 0
                    finally:
                        ch.close()
                except Exception:
                    answers[s["question_id"]] = 0
            elif test == "spec":
                try:
                    from source import Source as _S
                    s2 = _S()
                    try:
                        p = s2.source_proof(vl)
                        answers[s["question_id"]] = 1 if p["has"] else 0
                    finally:
                        s2.close()
                except Exception:
                    answers[s["question_id"]] = 0
            elif test == "industry":
                # 證明鏈判斷：word -> source_proof -> source -> provider
                #   -> industry_id -> industry（零 hardcode，全 DB 查）
                ind = self._industry_of(v)
                answers[s["question_id"]] = 1 if ind else 0
            elif test == "letter":
                answers[s["question_id"]] = 1 if v.isalpha() else 0
            elif test == "single word":
                answers[s["question_id"]] = \
                    1 if ("_" not in v and " " not in v and v) else 0
            elif test == "speech":
                answers[s["question_id"]] = 1 if v.isalpha() else 0
            elif test == "spelling":
                # 2026-10-26：spelling =「呢個 word 係真詞」——
                # 證明 = source.db source_proof 有行（有來源證明 = 真詞）。
                # 唔可以查 word_category / value（佢哋係結果，查自己 = 雞蛋問題）。
                try:
                    from source import Source as _S
                    _s2 = _S()
                    try:
                        _p = _s2.source_proof(vl)
                        answers[s["question_id"]] = 1 if _p["has"] else 0
                    finally:
                        _s2.close()
                except Exception:
                    answers[s["question_id"]] = 0
            elif test == "approved":
                # chain of proof：值有冇 approved run
                r = self.conn.execute(
                    "SELECT 1 FROM run r"
                    " JOIN vdb.value v ON v.id = r.value_id"
                    " WHERE LOWER(v.value) = ? AND r.status_id = 1"
                    " AND r.is_active = 1", (vl,)).fetchone()
                answers[s["question_id"]] = 1 if r else 0
            elif test in ("proof", "source"):
                try:
                    from source import Source as _S
                    s2 = _S()
                    try:
                        p = s2.source_proof(vl)
                        answers[s["question_id"]] = 1 if p["has"] else 0
                    finally:
                        s2.close()
                except Exception:
                    answers[s["question_id"]] = 0
            elif test in ("evidence", "proof", "verify"):
                # 2026-10-27（用戶要求）：證明 flow 嘅 condition ——
                # 判斷 = 呢個值有冇對應嘅證明記錄：
                #   evidence -> evidence 表有行（value_id 對應）
                #   proof    -> run 有 approved（chain of proof）
                #   verify   -> word_category 有行（已驗證）
                if test == "evidence":
                    r = self.conn.execute(
                        "SELECT 1 FROM evidence e"
                        " JOIN vdb.value v ON v.id = e.value_id"
                        " WHERE LOWER(v.value) = ? AND e.is_active = 1"
                        " LIMIT 1", (vl,)).fetchone()
                    answers[s["question_id"]] = 1 if r else 0
                elif test == "proof":
                    r = self.conn.execute(
                        "SELECT 1 FROM run r"
                        " JOIN vdb.value v ON v.id = r.value_id"
                        " WHERE LOWER(v.value) = ? AND r.status_id = 1"
                        " AND r.is_active = 1 LIMIT 1", (vl,)).fetchone()
                    answers[s["question_id"]] = 1 if r else 0
                else:  # verify
                    r = self.conn.execute(
                        "SELECT 1 FROM word_category WHERE LOWER(word) = ?",
                        (vl,)).fetchone()
                    answers[s["question_id"]] = 1 if r else 0
            elif test == "source_register":
                # 2026-10-27（用戶要求）：source_register flow ——
                # 判斷 = 詞有冇 source 證明；冇 -> 自動登記。
                # source_id 由表話事（零 hardcode）：
                #   source_register 表（word -> source_id）優先
                #   db_field_option（structure.db）後備
                # 登記成功 = PASS（呢條 flow 嘅目的就係「第一次查 -> 登記」）
                try:
                    from source import Source as _S
                    s2 = _S()
                    try:
                        p = s2.source_proof(vl)
                        if p["has"]:
                            answers[s["question_id"]] = 1
                        else:
                            src_id = self.get_source(vl)
                            if src_id is None:
                                answers[s["question_id"]] = 0
                            else:
                                res = s2.try_register(
                                    vl, source_id=src_id,
                                    proof="auto-register",
                                    caller="terminology.source_register")
                                # 記錄入 source_register 表（表話事）
                                if res["registered"]:
                                    self.conn.execute(
                                        "INSERT INTO source_register"
                                        " (word, source_id, registered_by)"
                                        " SELECT ?, ?, ? WHERE NOT EXISTS"
                                        " (SELECT 1 FROM source_register"
                                        "  WHERE LOWER(word) = LOWER(?))",
                                        (vl, src_id,
                                         "terminology.source_register", vl))
                                    self.conn.commit()
                                answers[s["question_id"]] = \
                                    1 if res["registered"] else 0
                    finally:
                        s2.close()
                except Exception:
                    answers[s["question_id"]] = 0
            else:
                answers[s["question_id"]] = 1 if v else 0
        return answers

    def run_flow(self, flow_name, answers=None, value=None,
                 value_id=None, save=True, _depth=0, role_id=None,
                 rule_id=None):
        """行一個驗證鏈（線性，第一個 FAIL 就停）—— 自己擁有

        answers = None -> 按 value 自動判斷（_auto_answers）
        value    = 提交去檢查嘅值（自動入 value 表）
        role_id  = role.db registry.id（邊個角色執行，2026-10-27）
        rule_id  = rule.db rule.id（跟邊條規則，2026-10-27e）
        全部 PASS -> status_id=1（approved）；第一個 FAIL -> 2（rejected）

        flow 連結 / 分支：由 next_flow（_do_branch）統一處理 ——
        跑完之後按 flow_branch（runtime 判斷）+ next_flow（規則）自動跑下一條。

        返回 {"status_id", "steps", "step_id", "answers", "run_id",
              "value", "value_id"}  （可能含 "branch"）
        """
        if _depth > 8:
            raise ValueError(f"flow 鏈太深（>8）：{flow_name}")
        # 2026-10-28：value_id -> 反查 value（重用時要用真值判斷）
        if value_id is not None and value is None:
            vr = self.conn.execute(
                "SELECT value FROM vdb.value WHERE id = ?",
                (value_id,)).fetchone()
            value = vr["value"] if vr else None
        # 2026-10-25：子 flow / 分支由 next_flow（_do_branch）統一處理
        if answers is None:
            answers = self._auto_answers(flow_name, value)
        answers = answers or {}
        if value_id is None and value is not None:
            value_id = self.add_value(value)
        steps = self.flow_steps(flow_name)
        if not steps:
            return {"status_id": None, "steps": [], "step_id": None,
                    "answers": [], "run_id": None,
                    "value": value, "value_id": value_id}
        judged = []
        stopped = None
        all_pass = True
        for s in steps:
            qid = s["question_id"]
            # 2026-10-25：子 flow / 分支由 next_flow（_do_branch）統一處理，
            # 呢度所有 step 都係普通 condition
            raw = answers.get(qid)
            # expected boolean_id（0/1）做 pass_value
            if s.get("expected_boolean_id") is not None:
                pv = str(s["expected_boolean_id"])
            else:
                pv = "1"
            ok = self._judge(s["operator_expression"], pv, raw)
            judged.append({
                "step_id": s["id"], "seq": s["seq"],
                "question_id": qid, "test": s["test"],
                "w5w2h": s["w5w2h"], "operator": s["operator_meta"],
                "expected_boolean_id": s["expected_boolean_id"],
                "answer": raw, "is_pass": ok,
            })
            if not ok:
                all_pass = False
                stopped = s["id"]
                break
        status_id = 1 if all_pass else 2
        run_id = None
        branch = None
        evidence_id = None
        if save:
            run_id = self._save_run(flow_name, value_id, stopped,
                                    status_id, judged, role_id, rule_id)
            # step_output：每步實際輸出（how much = flow 累計 PASS 步數）
            self._save_step_outputs(run_id, value_id, steps, judged)
            # 證據：全 PASS -> 每個 PASS step 寫一條 evidence；失敗 run = 冇
            if status_id == 1 and value_id:
                evidence_id = self._save_evidence(run_id, value_id,
                                                  steps, judged)
                # run.evidence_id = 證據鏈頭
                if evidence_id is not None:
                    self.conn.execute(
                        "UPDATE run SET evidence_id = ? WHERE id = ?",
                        (evidence_id, run_id))
                    self.conn.commit()
                # word_category 登記（2026-10-26：approved word = registry 證明）
                # word 有 source 證明先登記（has_proof 由 source_proof 查）
                if value is not None:
                    self._register_word_category(value)
            # flow_branch 決策：寫 flow_branch（每個 condition 實際結果）
            # -> 查 next_flow（flow + condition + status）-> 自動跑 target flow
            branch = self._do_branch(flow_name, run_id, value_id,
                                     steps, judged, save, _depth, role_id,
                                     rule_id)
        out = {"status_id": status_id,
               "steps": [j["seq"] for j in judged],
               "step_id": stopped, "answers": judged, "run_id": run_id,
               "value": value, "value_id": value_id,
               "evidence_id": evidence_id}
        if branch is not None:
            out["branch"] = branch
        return out

    def run_flow_ids(self, flow_ids, value=None, value_id=None,
                     save=True, role_id=None, rule_id=None):
        """揀 flow id 組合順序執行（2026-10-28 用戶要求）

        flow_ids = [1, 4, 67, 7] 組合（可以重用），逐條 run_flow：
            - 每條 flow 用同一個 value/value_id
            - 每條傳番 prev run_id 落去（chain）
            - 全部 PASS 先繼續；FAIL 即刻停
        返回 {"runs": [...]} 每條 flow 一個 run 記錄
        """
        if not flow_ids:
            raise ValueError("flow_ids 唔可以空")
        runs = []
        prev_run_id = None
        for fid in flow_ids:
            fr = self.conn.execute(
                "SELECT flow_name FROM flow WHERE id = ?", (fid,)).fetchone()
            if not fr:
                raise ValueError(f"flow id {fid} 唔存在")
            out = self.run_flow(fr["flow_name"], value=value,
                                value_id=value_id, save=save,
                                role_id=role_id, rule_id=rule_id)
            out = dict(out)
            out["flow_id"] = fid
            out["flow_name"] = fr["flow_name"]
            out["prev_run_id"] = prev_run_id
            runs.append(out)
            prev_run_id = out.get("run_id")
            if out.get("status_id") != 1:
                break  # FAIL：行完已記錄，唔再跑
        return {"runs": runs}

    def _do_branch(self, flow_name, run_id, value_id, steps, judged,
                   save, _depth, role_id=None, rule_id=None):
        """執行分支決策（0 hardcode）

        1. 為每個 step 嘅 condition 寫 flow_branch（runtime 記錄：
           run_id, value_id, condition_id, status_id = 實際判斷 PASS/FAIL）
        2. 查 next_flow 規則（flow + condition + status）
           -> flow_branch_id -> 攞目標 flow_branch 行嘅 flow_id = 下一條 flow
        3. 自動跑下一條 flow（role_id 傳落去）

        返回 {"condition", "status_id", "next_flow", "next_run_id"}
              如果 has 分支；否則 None
        """
        if _depth > 8:
            raise ValueError(f"flow 鏈太深（>8）：{flow_name}")
        fr = self.conn.execute(
            "SELECT id FROM flow WHERE flow_name = ?",
            (flow_name,)).fetchone()
        fid = fr["id"] if fr else None
        if not fid:
            return None
        # 1. 寫 flow_branch（runtime：每個 step 一個 condition 結果）
        for s, j in zip(steps, judged):
            cond_r = self.conn.execute(
                "SELECT id FROM condition WHERE meta = ?",
                (s["test"],)).fetchone()
            if not cond_r:
                continue
            self.conn.execute(
                "INSERT OR IGNORE INTO flow_branch"
                " (run_id, value_id, condition_id, status_id)"
                " VALUES (?, ?, ?, ?)",
                (run_id, value_id, cond_r["id"],
                 1 if j["is_pass"] else 0))
        self.conn.commit()
        # 2. 查 next_flow 規則 -> 目標 flow（flow_target_id = 目標 flow id）
        rows = self.conn.execute(
            """SELECT c.meta AS condition_meta, fb.status_id,
                      tf.flow_name AS next_flow
               FROM flow_branch fb
               JOIN condition c ON c.id = fb.condition_id
               JOIN next_flow nf
                 ON nf.flow_id = ? AND nf.condition_id = c.id
                AND nf.status_id = fb.status_id AND nf.is_active = 1
               JOIN flow tf ON tf.id = nf.flow_target_id
               WHERE fb.run_id = ? AND fb.is_active = 1
               ORDER BY nf.id""", (fid, run_id)).fetchall()
        if not rows:
            return None
        # 3. 跑下一條 flow
        out = []
        vrow = self.conn.execute(
            "SELECT value FROM vdb.value WHERE id = ?", (value_id,)).fetchone()
        v = vrow["value"] if vrow else None
        for r in rows:
            sub = self.run_flow(r["next_flow"], answers=None, value=v,
                                save=save, _depth=_depth + 1, role_id=role_id,
                                rule_id=rule_id)
            out.append({"condition": r["condition_meta"],
                        "status_id": r["status_id"],
                        "next_flow": r["next_flow"],
                        "next_run_id": sub["run_id"]})
        return out[0] if len(out) == 1 else out

    def _save_run(self, flow_name, value_id, step_id, status_id, judged,
                  role_id=None, rule_id=None):
        """寫入 run（證明）—— 全部欄 NOT NULL（2026-10-25 用戶要求）

        value_id = None（冇提交值）-> 指向 value 表 ''（空值行）
        step_id  = None（全 PASS 冇停步）-> 最後一步
        answer_id = 最終答案（全部 PASS -> 1 真，有 FAIL -> 2 假）
        role_id  = role.db registry.id（邊個角色執行，2026-10-27）
        rule_id  = rule.db rule.id（跟邊條規則，2026-10-27e）
        """
        fr = self.conn.execute(
            "SELECT id FROM flow WHERE flow_name = ?",
            (flow_name,)).fetchone()
        fid = fr["id"] if fr else None
        # value_id 缺 -> 空值行（`value = ''`，喺 value.db）
        if value_id is None:
            self.conn.execute(
                "INSERT INTO vdb.value (value) SELECT '' WHERE NOT EXISTS"
                " (SELECT 1 FROM vdb.value WHERE value = '')")
            value_id = self.conn.execute(
                "SELECT id FROM vdb.value WHERE value = ''").fetchone()["id"]
        # step_id 缺（全 PASS）-> 最後一步（唔可以 NULL）
        if step_id is None and fid:
            last = self.conn.execute(
                "SELECT s.id FROM step s WHERE s.flow_id = ?"
                " ORDER BY s.seq_id DESC LIMIT 1", (fid,)).fetchone()
            step_id = last["id"] if last else None
        if step_id is None:
            raise ValueError(
                f"flow '{flow_name}' 冇任何 step —— 唔可以寫 run（step_id 唔可以 NULL）")
        # 最終答案：全部 PASS -> 1（真），有 FAIL -> 2（假）
        final_ok = all(j["is_pass"] for j in judged) if judged else False
        answer_id = 1 if final_ok else 2
        # expected_id：最後一步嘅期望（judged 最後 entry 嘅 expected_boolean_id）
        expected_id = None
        if judged:
            last_exp = judged[-1].get("expected_boolean_id")
            if last_exp is not None:
                e = self.conn.execute(
                    "SELECT id FROM expected WHERE boolean_id IS ?",
                    (last_exp,)).fetchone()
                expected_id = e["id"] if e else None
        if expected_id is None:
            # fallback：按 answer（真 -> boolean 1，假 -> boolean 0）
            bid = 1 if answer_id == 1 else 0
            e = self.conn.execute(
                "SELECT id FROM expected WHERE boolean_id IS ?",
                (bid,)).fetchone()
            expected_id = e["id"] if e else None
        if expected_id is None:
            raise ValueError(
                "expected 表要有 boolean 0 同 1 —— 寫唔到 run（expected_id 唔可以 NULL）")
        cur = self.conn.execute(
            "INSERT INTO run"
            " (flow_id, value_id, step_id, status_id, answer_id, expected_id,"
            "  role_id, rule_id)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (fid, value_id, step_id, status_id, answer_id, expected_id,
             role_id, rule_id))
        run_id = cur.lastrowid
        self.conn.commit()
        return run_id

    def flow_runs(self, limit=20):
        """列出執行記錄（JOIN flow + value + status）"""
        return [dict(r) for r in self.conn.execute(
            """SELECT r.id, r.flow_id, f.flow_name,
                      r.value_id, v.value,
                      r.step_id, sq.seq AS step_seq,
                      r.status_id, b.value AS status, r.role_id, r.rule_id,
                      r.created_at
               FROM run r
               LEFT JOIN flow f ON f.id = r.flow_id
               LEFT JOIN vdb.value v ON v.id = r.value_id
               LEFT JOIN step st ON st.id = r.step_id
               LEFT JOIN seq sq ON sq.id = st.seq_id
               LEFT JOIN status s ON s.id = r.status_id
               LEFT JOIN boolean b ON b.id = s.boolean_id
               ORDER BY r.id DESC LIMIT ?""", (limit,))]

    def commit(self):
        self.conn.commit()

    def close(self):
        self.conn.close()