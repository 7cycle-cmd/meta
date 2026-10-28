"""sql.py — source.db 存取層

source = 來源字典（每個來源一行，其他表用 source_id 指過嚟）
例如：Anthropic spec、ISO/IEC 9075、Wikipedia: Identifier
provider = 提供者字典（例如 Anthropic、ISO/IEC、IETF）
authority_level = 權威等級（官方 2 / 權威參考 1 / 非官方 0）
industry = 行業字典（例如 information technology）
"""

import sqlite3

from .schema import *  # noqa: F401,E402
DB_PATH = r"C:\projects\meta\source\source.db"






class SqlStore:
    def __init__(self, db_path=DB_PATH):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute(SOURCE_TABLE_DDL)
        self.conn.execute(PROVIDER_TABLE_DDL)
        self.conn.execute(API_TYPE_DDL)
        self.conn.execute(API_DDL)
        self.conn.execute(API_PROOF_DDL)
        self.conn.execute(FLOW_DDL)
        self.conn.execute(SEQ_DDL)
        self.conn.execute(STEP_DDL)
        self.conn.execute(STATUS_DDL)
        self.conn.execute(RUN_DDL)
        self.conn.execute(RESULT_DDL)
        self.conn.execute(SOURCE_PROOF_DDL)
        self.conn.execute(VALUE_DDL)
        # 2026-10-28：Postman 真實數據表（官方 API 拉取證據）
        self.conn.execute(POSTMAN_SYNC_DDL)
        self.conn.execute(POSTMAN_MOCK_DDL)
        self.conn.execute(POSTMAN_MOCK_SERVER_DDL)
        self.conn.execute(POSTMAN_MOCK_EXEC_DDL)
        self.conn.execute(POSTMAN_RUN_DDL)
        # 2026-10-24p：字典表（symbol/english/INT/language/data_format/
        # industry/authority_level）已搬去 terminology —— source 唔再建
        self._migrate_word_source_rename()
        self.conn.commit()
        self._seed_flow_steps()
        self._seed_status()
        self._migrate_word_source()
        self._seed_apis()
        self._seed_api_refs()
        self._migrate_api_proven()   # 2026-10-28：api.proven 欄
        self.conn.commit()
        # 2026-10-28（用戶要求）：structure_resource 要登記齊全部資源
        # （api/schema/function/tool），唔可以淨係 schema
        self._register_structure_resources()
        # 2026-10-28（用戶設計）：migration 審計日誌
        self._record_migration_audit()

    def _record_migration_audit(self):
        """記錄 source 啟動嘅 migration 審計（migration module，冪等）

        用戶設計（2026-10-28）：migration = module 啟動時改 schema/資料
        嘅動作記錄。source 而家啟動時做咗：
            api + proven 欄（schema）
            api_proof 表（schema）
            structure_resource 登記（sync）
        全部經 migration module 記低（taxonomy_id 反查，零 hardcode）。
        """
        try:
            from migration import Migration as _M
            _m = _M()
            try:
                _m.record("source", table="api", migration_type="schema",
                          description="api 加 proven 欄（0=pending 1=pass 證據）")
                _m.record("source", table="api_proof",
                          migration_type="schema",
                          description="api_proof 表（pass/fail 0/1 證據）")
                _m.record("source", table="api", migration_type="sync",
                          description="structure_resource 資源登記（AST）")
                _m.record("source", table="postman_mock_exec",
                          migration_type="sync",
                          description="postman 真實執行證據同步")
                _m.record("source", table="api_proof", migration_type="sync",
                          description="postman mock execution 證據寫入")
            finally:
                _m.close()
        except Exception:
            pass

    def _register_structure_resources(self):
        """登記 source 全部資源入 structure_resource（冪等）

        用戶要求（2026-10-28）：structure module 係所有資源嘅統一登記處，
        唔可以淨係 type=schema。呢度登記 4 類：
            api      = source.db api 表 13 條（真實，唔 hardcode）
            schema   = schema.py *_DDL（AST 掃）
            function = 全部 .py public function/class（AST 掃，零 hardcode）
            tool     = tool.db registry（module_id -> taxonomy 名）

        冪等：add_structure_resource 內部 WHERE NOT EXISTS。
        """
        try:
            from structure import Structure as _S
            _st = _S()
            try:
                import sqlite3 as _sq
                # structure ids（source module_id = taxonomy.registry 12）
                _c = _sq.connect(r"C:\projects\meta\structure\structure.db")
                _c.row_factory = _sq.Row
                try:
                    cmp = _c.execute(
                        "SELECT sm.id, sm.value FROM structure_module sm"
                        " JOIN structure_type t ON t.id = sm.structure_type_id"
                        " WHERE sm.module_id = ? AND t.meta = 'package'"
                        " LIMIT 1", (12,)).fetchone()
                    pkg_id = cmp["id"] if cmp else None
                    files = {r["value"]: r["id"] for r in _c.execute(
                        "SELECT sm.id, sm.value FROM structure_module sm"
                        " JOIN structure_type t ON t.id = sm.structure_type_id"
                        " WHERE sm.module_id = ? AND t.meta = 'file'", (12,))}
                finally:
                    _c.close()
                if not pkg_id:
                    return
                n = {"api": 0, "schema": 0, "function": 0, "tool": 0}
                # 1. api（source.db api 表）
                for a in self.apis():
                    _st.add_structure_resource(
                        _st.store.resource_type_id("api"),
                        f"{a['api_type']} {a['api']}", pkg_id)
                    n["api"] += 1
                # 2. schema + function（AST 掃，零 hardcode）
                lines = self._ast_scan_source()
                seen_fn = set()
                for fn, name, line, kind in lines:
                    fid = files.get(fn)
                    if kind == "schema":
                        _st.add_structure_resource(
                            _st.store.resource_type_id("schema"), name,
                            pkg_id, line_number=line, file_id=fid)
                        n["schema"] += 1
                    elif kind in ("function", "class"):
                        key = (fn, name)
                        if key in seen_fn:
                            continue
                        seen_fn.add(key)
                        _st.add_structure_resource(
                            _st.store.resource_type_id("function"),
                            f"{fn}:{name}", pkg_id,
                            line_number=line, file_id=fid)
                        n["function"] += 1
                # 3. tool（tool.db registry -> taxonomy 名）
                # 2026-10-28：中央 scanner（structure.scan_all）負責 tool 登記，
                # source 唔再自己登（避免雙重）
                n["tool"] = 0
                print(f"[source] structure_resource 登記："
                      f"api={n['api']} schema={n['schema']}"
                      f" function={n['function']} tool={n['tool']}")
            finally:
                _st.close()
        except Exception:
            pass

    def _ast_scan_source(self):
        """AST 掃 source module：返回 [(file, name, line, kind)]（零 hardcode）

        2026-10-28（收斂）：schema 只掃 schema.py（DDL 唯一來源）；
        function/class 掃全部公開 .py（每個 symbol 一個 file 首現）。
        """
        import os as _os
        import importlib.util as _ilu
        _ast_sp = _ilu.spec_from_file_location(
            "_stdlib_ast", _os.path.join(_os.path.dirname(_os.__file__), "ast.py"))
        _ast_m = _ilu.module_from_spec(_ast_sp)
        _ast_sp.loader.exec_module(_ast_m)
        out = []
        folder = _os.path.join(_os.path.dirname(
            _os.path.dirname(_os.path.abspath(__file__))), "source")
        # schema：只掃 schema.py（避免 sql.py/api.py 重複 reference）
        schema_path = _os.path.join(folder, "schema.py")
        try:
            with open(schema_path, "r", encoding="utf-8") as f:
                tree = _ast_m.parse(f.read(), filename=schema_path)
            for node in _ast_m.walk(tree):
                if isinstance(node, _ast_m.Assign):
                    for t in node.targets:
                        if isinstance(t, _ast_m.Name) and t.id.endswith("_DDL"):
                            out.append(("schema.py", t.id, node.lineno, "schema"))
        except (SyntaxError, OSError):
            pass
        # function/class：掃全部公開 .py（每 symbol 第一出現）
        seen = set()
        for fn in sorted(_os.listdir(folder)):
            if not fn.endswith(".py") or fn.startswith("_"):
                continue
            path = _os.path.join(folder, fn)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    tree = _ast_m.parse(f.read(), filename=path)
            except (SyntaxError, OSError):
                continue
            for node in _ast_m.walk(tree):
                if isinstance(node, (_ast_m.FunctionDef, _ast_m.AsyncFunctionDef)):
                    if node.name.startswith("_"):
                        continue
                    if (fn, node.name) in seen:
                        continue
                    seen.add((fn, node.name))
                    out.append((fn, node.name, node.lineno, "function"))
                elif isinstance(node, _ast_m.ClassDef):
                    if node.name.startswith("_"):
                        continue
                    if (fn, node.name) in seen:
                        continue
                    seen.add((fn, node.name))
                    out.append((fn, node.name, node.lineno, "class"))
        return out

    def _migrate_api_proven(self):
        """遷移（幂等）：api 加 proven 欄（2026-10-28 用戶要求）

        proven = 0（pending）—— 之前 seed 嘅 api 全部未證明，
        要 record_api_proof 之後 prove_api 先至 proven=1。
        唔可以自動填 1（要真實證據）。
        """
        cols = {c[1] for c in self.conn.execute(
            "PRAGMA table_info('api')")}
        if "proven" not in cols:
            self.conn.execute(
                "ALTER TABLE api ADD COLUMN proven INTEGER NOT NULL DEFAULT 0")
            # 有 API_PROOF 證據嘅行 -> proven=1（冪等）
            self.conn.execute(
                "UPDATE api SET proven = 1 WHERE id IN"
                " (SELECT DISTINCT api_id FROM api_proof)")
            self.conn.commit()
            print("[migrate] api + proven 欄（預設 0 = pending proof）")
        # api_proof 表加 is_pass / module_version（2026-10-28）
        pcols = {c[1] for c in self.conn.execute(
            "PRAGMA table_info('api_proof')")}
        if "is_pass" not in pcols:
            self.conn.execute(
                "ALTER TABLE api_proof ADD COLUMN is_pass INTEGER"
                " NOT NULL DEFAULT 1")
            # 回填：http_status 200-299 -> pass
            self.conn.execute(
                "UPDATE api_proof SET is_pass = 1"
                " WHERE http_status BETWEEN 200 AND 299")
            self.conn.execute(
                "UPDATE api_proof SET is_pass = 0"
                " WHERE http_status < 200 OR http_status >= 300")
            self.conn.commit()
            print("[migrate] api_proof + is_pass 欄（回填完成）")
        if "module_version" not in pcols:
            self.conn.execute(
                "ALTER TABLE api_proof ADD COLUMN module_version TEXT")
            self.conn.commit()
            print("[migrate] api_proof + module_version 欄")

    # ---------- api_proof（2026-10-28：真實執行證據先可以註冊 api）----------
    def api_by_path_method(self, path, method):
        """搵 api.id（path + method 配對，冪等）

        2026-10-28：支援 <id> pattern —— /sources/15 自動對應
        註冊嘅 /sources/<id>（數字段換 <id> 再查）。
        """
        tr = self.conn.execute(
            "SELECT id FROM api_type WHERE value = ?", (method,)).fetchone()
        if not tr:
            return None
        r = self.conn.execute(
            "SELECT id FROM api WHERE api = ? AND api_type_id = ?",
            (path, tr["id"])).fetchone()
        if r:
            return r["id"]
        # pattern 配對：/sources/15 -> /sources/<id>（數字段 -> <id>）
        import re
        pat = re.sub(r"/\d+", "/<id>", path)
        if pat != path:
            r = self.conn.execute(
                "SELECT id FROM api WHERE api = ? AND api_type_id = ?",
                (pat, tr["id"])).fetchone()
            if r:
                return r["id"]
        return None

    def record_api_proof(self, path, method, http_status, is_pass=None,
                         proof_type="live_http", ref_id=None,
                         module_version=None, x_srv_trace=None):
        """記錄一條 api 嘅真實執行證據（pass + fail 都要記）

        path/method  = 執行嘅真實 API
        http_status  = HTTP 結果（200-299 = pass）
        is_pass      = None -> 自動由 http_status 計（200-299=1 其他=0）
        proof_type   = postman_mock_exec / live_http / ...
        ref_id       = 證據來源（postman_mock_exec.id / postman_sync.id）
        module_version = 邊個 module version 證明（例如 source 1.0.0）

        pass 證據存在 -> api.proven=1（自動）
        fail 證據只記錄（唔影響 proven）
        """
        api_id = self.api_by_path_method(path, method)
        if api_id is None:
            raise ValueError(
                f"api '{method} {path}' 未註冊 —— 先 add_api 先可以記錄證據")
        if is_pass is None:
            is_pass = 1 if 200 <= http_status < 300 else 0
        if ref_id is not None:
            # 冪等：同一 (api_id, proof_type, ref_id) 唔重複（例如 postman exec）
            exists = self.conn.execute(
                "SELECT id FROM api_proof WHERE api_id = ?"
                " AND proof_type = ? AND ref_id = ?",
                (api_id, proof_type, ref_id)).fetchone()
            if exists:
                pid = exists["id"]
                self.conn.execute(
                    "UPDATE api_proof SET http_status = ?, is_pass = ?,"
                    " module_version = ? WHERE id = ?",
                    (http_status, is_pass, module_version, pid))
            else:
                cur = self.conn.execute(
                    "INSERT INTO api_proof"
                    " (api_id, proof_type, ref_id, method, path, http_status,"
                    "  is_pass, module_version, x_srv_trace)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (api_id, proof_type, ref_id, method, path, http_status,
                     is_pass, module_version, x_srv_trace))
                pid = cur.lastrowid
        else:
            # 冇 ref_id（live_http 每次執行 = 新證據，全部保留）
            cur = self.conn.execute(
                "INSERT INTO api_proof"
                " (api_id, proof_type, ref_id, method, path, http_status,"
                "  is_pass, module_version, x_srv_trace)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (api_id, proof_type, None, method, path, http_status,
                 is_pass, module_version, x_srv_trace))
            pid = cur.lastrowid
        # 有 PASS 證據 -> proven=1（fail 唔會）
        if is_pass == 1:
            self.conn.execute(
                "UPDATE api SET proven = 1 WHERE id = ?", (api_id,))
        self.conn.commit()
        return pid

    def api_resource_map(self):
        """source api ↔ structure_resource 對照（api_id <-> resource_id）

        用戶要求（2026-10-28）：api_proof 證據要連返 structure_resource。
        DB 驅動：由 structure.db 攞 source package 嘅 api 型資源。
        返回：[{"api_id", "api", "method", "resource_id", "proven"}]
        """
        import sqlite3 as _sq
        out = []
        try:
            sc = _sq.connect(r"C:\projects\meta\structure\structure.db")
            sc.row_factory = _sq.Row
            try:
                rows = sc.execute(
                    "SELECT sr.id AS resource_id, sr.value"
                    " FROM structure_resource sr"
                    " LEFT JOIN resource_type rt ON rt.id = sr.resource_type_id"
                    " LEFT JOIN structure_module sm ON sm.id = sr.package_id"
                    " WHERE rt.value = 'api' AND sm.module_id = ?"
                    " AND sr.is_active = 1",
                    (12,)).fetchall()
                for r in rows:
                    method, _, path = r["value"].partition(" ")
                    api_id = self.api_by_path_method(path, method)
                    proven = 0
                    if api_id:
                        p = self.conn.execute(
                            "SELECT proven FROM api WHERE id = ?",
                            (api_id,)).fetchone()
                        proven = p["proven"] if p else 0
                    out.append({
                        "api_id": api_id,
                        "api": path,
                        "method": method,
                        "resource_id": r["resource_id"],
                        "proven": proven,
                    })
            finally:
                sc.close()
        except Exception:
            pass
        return out

    def api_proofs(self, api_id=None):
        """列出執行證據（可按 api 篩選）"""
        sql = ("SELECT ap.*, a.api, t.value AS api_type"
               " FROM api_proof ap"
               " LEFT JOIN api a ON a.id = ap.api_id"
               " LEFT JOIN api_type t ON t.id = a.api_type_id")
        args = ()
        if api_id is not None:
            sql += " WHERE ap.api_id = ?"
            args = (api_id,)
        sql += " ORDER BY ap.id"
        return [dict(r) for r in self.conn.execute(sql, args)]

    def apis_with_proof(self, proven_only=False):
        sql = ("SELECT a.id, a.api, t.value AS api_type,"
               " a.flow_id, f.flow_name, a.description, a.status_id,"
               " a.proven, a.is_active, a.created_at,"
               " (SELECT COUNT(*) FROM api_proof ap WHERE ap.api_id = a.id"
               "  AND ap.is_pass = 1) AS pass_count,"
               " (SELECT COUNT(*) FROM api_proof ap WHERE ap.api_id = a.id"
               "  AND ap.is_pass = 0) AS fail_count"
               " FROM api a"
               " LEFT JOIN api_type t ON t.id = a.api_type_id"
               " LEFT JOIN flow f ON f.id = a.flow_id")
        if proven_only:
            sql += " WHERE a.proven = 1"
        sql += " ORDER BY t.id, a.api"
        return [dict(r) for r in self.conn.execute(sql)]

    def _seed_api_refs(self):
        """seed api 表參考（value_id + status_id + flow_id）—— 唔可以 NULL

        2026-10-24n（用戶要求）：api 表唔可以有 NULL。
        每條 API 消耗嘅值（value 表）+ 狀態（status 表）+ flow。
        """
        # value 字典（每條 API 處理嘅實體）
        values = ["source", "provider", "industry", "health",
                  "charset", "language", "data_format",
                  "authority_level"]
        vid = {}
        for v in values:
            self.conn.execute(
                "INSERT INTO value (value) SELECT ? WHERE NOT EXISTS"
                " (SELECT 1 FROM value WHERE value = ?)", (v, v))
            r = self.conn.execute(
                "SELECT id FROM value WHERE value = ?", (v,)).fetchone()
            vid[v] = r["id"]
        # status id
        sid_approved = self.conn.execute(
            "SELECT id FROM status WHERE status = 'approved'").fetchone()
        sid_approved = sid_approved["id"] if sid_approved else 1
        # 每條 api -> value + status + flow
        api_values = {
            "/sources": "source",
            "/sources/<id>": "source",
            "/providers": "provider",
            "/providers/<id>": "provider",
            "/levels": "authority_level",
            "/industries": "industry",
            "/health": "health",
            "/charsets": "charset",
            "/languages": "language",
            "/data-formats": "data_format",
        }
        api_flows = {
            "/sources": "source",
            "/sources/<id>": "source",
            "/providers": "provider",
            "/providers/<id>": "provider",
            "/levels": "authority",
            "/industries": "industry",
            "/health": "health",
            "/charsets": "charsets",
            "/languages": "languages",
            "/data-formats": "charsets",
        }
        # flow id lookup
        flow_ids = {}
        for r in self.conn.execute("SELECT id, flow_name FROM flow"):
            flow_ids[r["flow_name"]] = r["id"]
        for api, val in api_values.items():
            fid = flow_ids.get(api_flows.get(api))
            self.conn.execute(
                "UPDATE api SET value_id = ?, status_id = ?, flow_id = ?"
                " WHERE api = ?",
                (vid[val], sid_approved, fid, api))
        # 其餘（POST 同 GET 重複）按 api 名
        for api, val in api_values.items():
            fid = flow_ids.get(api_flows.get(api))
            self.conn.execute(
                "UPDATE api SET value_id = ?, status_id = ?, flow_id = ?"
                " WHERE api = ? AND value_id IS NULL",
                (vid[val], sid_approved, fid, api))
        self.conn.commit()
        # 驗證冇 NULL
        n = self.conn.execute(
            "SELECT COUNT(*) n FROM api WHERE value_id IS NULL OR status_id IS NULL"
        ).fetchone()["n"]
        if n:
            print(f"⚠️ 仲有 {n} 條 api 未填")
        self.conn.commit()

    def _migrate_word_source_rename(self):
        """遷移（幂等）：word_source 表改名 source_proof（2026-10-24m）

        2026-10-24m（用戶要求）：word_source -> source_proof。
        舊表有資料（90 行）-> RENAME 保留；新表由 CREATE IF NOT EXISTS
        可能已建立（空表）-> 掉咗先改名。
        """
        has_old = self.conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='word_source'").fetchone()
        if not has_old:
            return
        has_new = self.conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='source_proof'").fetchone()
        if has_new:
            n = self.conn.execute(
                "SELECT COUNT(*) n FROM source_proof").fetchone()["n"]
            if n == 0:
                self.conn.execute("DROP TABLE source_proof")
        self.conn.execute("ALTER TABLE word_source RENAME TO source_proof")
        self.conn.commit()

    def _seed_status(self):
        """seed 狀態字典（approved / rejected / NA，同 question 一樣）"""
        for s in ("approved", "rejected", "NA"):
            self.conn.execute(
                "INSERT INTO status (status) SELECT ? WHERE NOT EXISTS"
                " (SELECT 1 FROM status WHERE status = ?)", (s, s))
        self.conn.commit()

    def _migrate_word_source(self):
        """遷移（幂等）：詞 → source 證明由 terminology.db 搬嚟

        2026-10-24j（用戶要求）：proof source 由 module : source 擁有。
        terminology.db is_english.source_id / is_industry_spec.source_id
        -> source.db source_proof（word, source_id, proof）。

        搬一次就 OK（source_proof 有行 -> skip），舊表刪除後都唔影響。
        """
        n = self.conn.execute(
            "SELECT COUNT(*) n FROM source_proof").fetchone()["n"]
        if n > 0:
            return  # 已搬過（冪等）
        import sqlite3 as _sq
        try:
            tc = _sq.connect(r"C:\projects\meta\terminology\terminology.db")
            tc.row_factory = _sq.Row
            try:
                # is_english -> word + source_id
                for r in tc.execute(
                        "SELECT meta, source_id FROM is_english"
                        " WHERE source_id IS NOT NULL"
                        " AND source_id != '' AND source_id != '0'"):
                    self.conn.execute(
                        "INSERT INTO source_proof (word, source_id, description)"
                        " SELECT ?, ?, ? WHERE NOT EXISTS"
                        " (SELECT 1 FROM source_proof WHERE word = ?)",
                        (r["meta"], int(r["source_id"]),
                         "由 is_english 遷移", r["meta"]))
                # is_industry_spec -> word + source_id + proof
                for r in tc.execute(
                        "SELECT meta, source_id, proof FROM is_industry_spec"
                        " WHERE source_id IS NOT NULL"
                        " AND source_id != '' AND source_id != '0'"):
                    self.conn.execute(
                        "INSERT INTO source_proof"
                        " (word, source_id, proof, description)"
                        " SELECT ?, ?, ?, ? WHERE NOT EXISTS"
                        " (SELECT 1 FROM source_proof WHERE word = ?)",
                        (r["meta"], int(r["source_id"]), r["proof"],
                         "由 is_industry_spec 遷移", r["meta"]))
            finally:
                tc.close()
        except Exception:
            pass  # terminology.db 無咗/冇表 -> 由 source 自己慢慢註冊
        self.conn.commit()

    def source_proof(self, word):
        """詞嘅 source 證明（source_proof 表）

        返回 {"has": bool, "url": str|None, "source": str|None,
               "provider": str|None, "proof": str|None, "explain": str}
        """
        r = self.conn.execute(
            "SELECT ws.word, ws.source_id, ws.proof,"
            " s.source, p.meta AS provider, p.official_url"
            " FROM source_proof ws"
            " LEFT JOIN source s ON s.id = ws.source_id"
            " LEFT JOIN provider p ON p.id = s.provider_id"
            " WHERE ws.word = ? AND ws.is_active = 1", (word,)).fetchone()
        if not r:
            return {"has": False, "url": None, "source": None,
                    "provider": None, "proof": None,
                    "explain": f"'{word}' 喺 source_proof 冇證明"}
        url = r["official_url"]
        ok = url is not None and str(url).strip() != ""
        return {
            "has": ok,
            "url": str(url).strip() if ok else None,
            "source": r["source"],
            "provider": r["provider"],
            "proof": r["proof"],
            "explain": (f"來源證明：{r['source']}"
                        f"（{r['provider']} → {url}）" if ok else
                        f"來源 {r['source']} 冇 official_url"),
        }

    def add_source_proof(self, word, source_id=None, proof=None,
                         description=None, registered_by=None, run_id=None):
        """登記詞 → source 證明（冪等；source_id 非空）

        2026-10-24l（用戶要求）：caller 記錄 ——
        registered_by = 邊個 caller 批准註冊（verify / system...）
        run_id        = source flow run.id（批准嗰次驗證證明）

        word      = 詞
        source_id = source.id（證明來源）—— 冇 = 拒絕
        """
        if source_id is None:
            raise ValueError(f"word '{word}' 一定要有 source_id（證明來源）")
        # 確保舊表有 caller 欄（遷移）
        cols = [c[1] for c in self.conn.execute(
            "PRAGMA table_info('source_proof')")]
        if "registered_by" not in cols:
            self.conn.execute(
                "ALTER TABLE source_proof ADD COLUMN registered_by TEXT")
        if "run_id" not in cols:
            self.conn.execute(
                "ALTER TABLE source_proof ADD COLUMN run_id INTEGER")
        self.conn.execute(
            "INSERT INTO source_proof"
            " (word, source_id, proof, description, registered_by, run_id)"
            " SELECT ?, ?, ?, ?, ?, ? WHERE NOT EXISTS"
            " (SELECT 1 FROM source_proof WHERE word = ?)",
            (word, source_id, proof, description, registered_by, run_id,
             word))
        self.conn.execute(
            "UPDATE source_proof SET source_id = ?, proof = ?,"
            " registered_by = COALESCE(?, registered_by),"
            " run_id = COALESCE(?, run_id)"
            " WHERE word = ?",
            (source_id, proof, registered_by, run_id, word))
        self.conn.commit()
        r = self.conn.execute(
            "SELECT id FROM source_proof WHERE word = ?", (word,)).fetchone()
        return r["id"] if r else None



    def _seed_flow_steps(self):
        """預填 flow + seq + step（同 question module 一樣設計）

        2026-10-24（用戶要求）：source 都要有 flow + step，
        令 api.flow_id 有實際目標。每一步 = 檢查邊個 source。

        預設 flow：
            source      驗證鏈（provider 有 official_url 先算完整）
            charsets    字符集字典（ISO 符號集 / OED 字母 / IEEE 數字）
            languages   程式語言（VSCode 證明）
        2026-10-24o（用戶要求）：每條 api 都要有 flow ——
            provider / industry / authority / health / word_proof
        """
        # seq（1-10）
        for n in range(1, 11):
            self.conn.execute(
                "INSERT INTO seq (seq) SELECT ? WHERE NOT EXISTS"
                " (SELECT 1 FROM seq WHERE seq = ?)", (n, n))
        # flow
        flows = ["source", "charsets", "languages",
                 "provider", "industry", "authority", "health",
                 "word proof"]
        flow_ids = {}
        for fn in flows:
            self.conn.execute(
                "INSERT INTO flow (flow_name) SELECT ? WHERE NOT EXISTS"
                " (SELECT 1 FROM flow WHERE flow_name = ?)", (fn, fn))
            r = self.conn.execute(
                "SELECT id FROM flow WHERE flow_name = ?", (fn,)).fetchone()
            flow_ids[fn] = r["id"]
        # step（flow_id, source_id, seq_id）
        # 搵 source id 嘅 helper
        def _sid(name):
            r = self.conn.execute(
                "SELECT id FROM source WHERE source = ?", (name,)).fetchone()
            return r["id"] if r else None
        source_steps = [
            ("ISO/IEC 9075", 1),   # SQL 標準
            ("RFC 8259", 2),       # JSON
            ("Oxford English Dictionary", 3),  # 詞典
            ("IEEE 754", 4),       # 數字標準
            ("RFC 3986", 5),       # URI
            ("VSCode", 6),         # 開發環境
        ]
        charsets_steps = [
            ("ISO/IEC 9075", 1),   # symbol 集
            ("Oxford English Dictionary", 2),  # english 集
            ("IEEE 754", 3),       # INT 集
        ]
        languages_steps = [
            ("VSCode", 1),         # 語言註冊來源
            ("RFC 8259", 2),       # 數據格式來源（JSON）
        ]
        provider_steps = [
            ("Anthropic spec", 1),  # provider 有 URL 證明
            ("RFC 9110", 2),        # IETF
            ("Oxford English Dictionary", 3),  # 詞典官方
        ]
        industry_steps = [
            ("RFC 3986", 1),        # 行業字典
            ("VSCode", 2),          # 開發環境
        ]
        authority_steps = [
            ("ISO/IEC 9075", 1),    # 權威等級官方
            ("RFC 9110", 2),
        ]
        health_steps = [
            ("VSCode", 1),          # 健康 = 服務存在
        ]
        word_proof_steps = [
            ("Anthropic spec", 1),  # source_proof 證明鏈
            ("Cambridge Dictionary", 2),
            ("Oxford English Dictionary", 3),
        ]
        for flow_name, steps in (("source", source_steps),
                                 ("charsets", charsets_steps),
                                 ("languages", languages_steps),
                                 ("provider", provider_steps),
                                 ("industry", industry_steps),
                                 ("authority", authority_steps),
                                 ("health", health_steps),
                                 ("word proof", word_proof_steps)):
            fid = flow_ids.get(flow_name)
            if not fid:
                continue
            for sname, seq_n in steps:
                sid = _sid(sname)
                if sid is None:
                    continue
                sq = self.conn.execute(
                    "SELECT id FROM seq WHERE seq = ?", (seq_n,)).fetchone()
                if not sq:
                    continue
                self.conn.execute(
                    "INSERT INTO step (flow_id, source_id, seq_id)"
                    " SELECT ?, ?, ? WHERE NOT EXISTS"
                    " (SELECT 1 FROM step WHERE flow_id = ? AND seq_id = ?)",
                    (fid, sid, sq["id"], fid, sq["id"]))
        self.conn.commit()

    def _seed_apis(self):
        """seed 對外 API 註冊（api_type + api 表）

        2026-10-24（用戶要求）：module 之間點樣 work together 要有表管理。
        source module 對外開放嘅 REST API 全部註冊喺呢度（DB 控制）：
            GET  /sources /sources/<id> /providers /providers/<id>
                 /levels /industries /health /charsets /languages
                 /data-formats
            POST /sources /providers /industries
        flow_id / value_id：呢條 API 屬於邊條 flow、消耗邊種 value
        （跨 module 合作點 —— 例如 /languages 俾 question 用）。
        """
        # api_type（GET / POST）
        for t, desc in (("GET", "讀取"), ("POST", "寫入"),
                        ("PUT", "更新"), ("DELETE", "刪除")):
            self.conn.execute(
                "INSERT INTO api_type (value, description)"
                " SELECT ?, ? WHERE NOT EXISTS"
                " (SELECT 1 FROM api_type WHERE value = ?)",
                (t, desc, t))
        # flow id lookup
        flow_ids = {}
        for r in self.conn.execute("SELECT id, flow_name FROM flow"):
            flow_ids[r["flow_name"]] = r["id"]
        # api 註冊（path, type, flow_name, 描述）—— 全部有 flow（2026-10-24o）
        apis = [
            ("/sources", "GET", "source", "列出全部 source"),
            ("/sources/<id>", "GET", "source", "攞一個 source"),
            ("/providers", "GET", "provider", "列出全部 provider"),
            ("/providers/<id>", "GET", "provider", "攞一個 provider"),
            ("/levels", "GET", "authority", "列出全部 authority_level"),
            ("/industries", "GET", "industry", "列出全部 industry"),
            ("/health", "GET", "health", "健康檢查"),
            ("/charsets", "GET", "charsets", "字符集字典（symbol/english/INT）"),
            ("/languages", "GET", "languages", "程式語言 + 符號集"),
            ("/data-formats", "GET", "charsets", "數據格式 + 符號集"),
            ("/sources", "POST", "source", "註冊 source"),
            ("/providers", "POST", "provider", "註冊 provider"),
            ("/industries", "POST", "industry", "註冊 industry"),
        ]
        for path, typ, flow_name, desc in apis:
            tr = self.conn.execute(
                "SELECT id FROM api_type WHERE value = ?", (typ,)).fetchone()
            if not tr:
                continue
            fid = flow_ids.get(flow_name) if flow_name else None
            self.conn.execute(
                "INSERT INTO api (api, api_type_id, flow_id, description)"
                " SELECT ?, ?, ?, ? WHERE NOT EXISTS"
                " (SELECT 1 FROM api WHERE api = ? AND api_type_id = ?)",
                (path, tr["id"], fid, desc, path, tr["id"]))
            # 已存在 -> 補 flow_id（冪等）
            self.conn.execute(
                "UPDATE api SET flow_id = ? WHERE api = ? AND api_type_id = ?"
                " AND flow_id IS NULL", (fid, path, tr["id"]))
        self.conn.commit()

    def apis(self, active_only=True):
        """列出對外 API 註冊（含 type 名同 flow 名）"""
        sql = ("SELECT a.id, a.api, t.value AS api_type,"
               " a.flow_id, f.flow_name, a.value_id, a.description,"
               " a.status_id, a.is_active, a.created_at"
               " FROM api a"
               " LEFT JOIN api_type t ON t.id = a.api_type_id"
               " LEFT JOIN flow f ON f.id = a.flow_id")
        if active_only:
            sql += " WHERE a.is_active = 1"
        sql += " ORDER BY t.id, a.api"
        return [dict(r) for r in self.conn.execute(sql)]

    # ---------- flow / step（同 question 一樣設計） ----------
    def flows(self, active_only=True):
        sql = "SELECT * FROM flow"
        if active_only:
            sql += " WHERE is_active = 1"
        sql += " ORDER BY id"
        return [dict(r) for r in self.conn.execute(sql)]

    def flow_by_name(self, flow_name):
        r = self.conn.execute(
            "SELECT * FROM flow WHERE flow_name = ?", (flow_name,)).fetchone()
        return dict(r) if r else None

    def add_flow(self, flow_name):
        """建立一條驗證鏈（冪等）"""
        self.conn.execute(
            "INSERT INTO flow (flow_name) SELECT ? WHERE NOT EXISTS"
            " (SELECT 1 FROM flow WHERE flow_name = ?)", (flow_name, flow_name))
        self.conn.commit()
        r = self.conn.execute(
            "SELECT id FROM flow WHERE flow_name = ?", (flow_name,)).fetchone()
        return r["id"] if r else None

    def add_step(self, flow_name, source_id, seq):
        """建立一個 step（冪等：同一 flow + seq 更新）

        flow_name = 驗證鏈名
        source_id = source.id（檢查邊個來源）
        seq       = 第幾步（1, 2, 3...）
        """
        fid = self.add_flow(flow_name)
        sq = self.conn.execute(
            "SELECT id FROM seq WHERE seq = ?", (seq,)).fetchone()
        if not sq:
            self.conn.execute(
                "INSERT INTO seq (seq) SELECT ? WHERE NOT EXISTS"
                " (SELECT 1 FROM seq WHERE seq = ?)", (seq, seq))
            self.conn.commit()
            sq = self.conn.execute(
                "SELECT id FROM seq WHERE seq = ?", (seq,)).fetchone()
        seq_id = sq["id"]
        self.conn.execute(
            """INSERT INTO step (flow_id, seq_id, source_id)
               VALUES (?, ?, ?)
               ON CONFLICT(flow_id, seq_id) DO UPDATE SET
                   source_id = excluded.source_id,
                   updated_at = datetime('now', 'localtime')""",
            (fid, seq_id, source_id))
        self.conn.commit()
        r = self.conn.execute(
            "SELECT id FROM step WHERE flow_id = ? AND seq_id = ?",
            (fid, seq_id)).fetchone()
        return r["id"] if r else None

    def flow_steps(self, flow_name, active_only=True):
        """列出一個 flow 嘅全部 steps（按 seq 排序，JOIN source 名）"""
        sql = """SELECT s.id, s.flow_id, s.seq_id, sq.seq AS seq,
                        s.source_id, src.source AS source_name,
                        src.provider_id, p.meta AS provider_name,
                        p.official_url
                 FROM step s
                 JOIN flow f ON f.id = s.flow_id
                 LEFT JOIN seq sq ON sq.id = s.seq_id
                 LEFT JOIN source src ON src.id = s.source_id
                 LEFT JOIN provider p ON p.id = src.provider_id
                 WHERE f.flow_name = ?"""
        args = (flow_name,)
        if active_only:
            sql += " AND s.is_active = 1"
        sql += " ORDER BY s.seq_id"
        return [dict(r) for r in self.conn.execute(sql, args)]

    # ---------- run / result（同 question 一樣，flow 執行驗證） ----------
    def run_flow(self, flow_name="source", save=True):
        """行一條 source 驗證鏈（同 question.run_flow 一樣設計）

        2026-10-24i（用戶要求）：source 要有 run + result —
        register 之前，先經 flow steps 驗證「每個 step 嘅 source
        有 provider + official_url」，全部 pass 先算 approved。

        每一步嘅「證明」：
            has_provider = source.provider_id 非空（0/1）
            has_url      = provider.official_url 非空（0/1）
        全部 pass -> approved（status_id=1）
        第一個 fail -> 停喺嗰步 -> rejected（status_id=2）

        返回 {"status_id": n, "steps": [...], "ended_at": seq,
              "step_id": n, "results": [...], "run_id": n}
        """
        steps = self.flow_steps(flow_name)
        if not steps:
            return {"status_id": 3, "steps": [], "ended_at": None,
                    "step_id": None, "results": [], "run_id": None}
        visited = []
        results = []
        stopped_step = None
        all_pass = True
        for s in steps:
            visited.append(s["seq"])
            has_provider = s.get("provider_id") is not None
            has_url = bool(s.get("official_url"))
            ok = has_provider and has_url
            results.append({
                "step_id": s["id"],
                "step_seq": s["seq"],
                "source_id": s["source_id"],
                "source": s["source_name"],
                "provider": s["provider_name"],
                "official_url": s["official_url"],
                "has_provider": 1 if has_provider else 0,
                "has_url": 1 if has_url else 0,
                "is_pass": ok,
            })
            if not ok:
                all_pass = False
                stopped_step = s["id"]
                break
        status_id = 1 if all_pass else 2
        run_id = None
        if save:
            fid = self.conn.execute(
                "SELECT id FROM flow WHERE flow_name = ?",
                (flow_name,)).fetchone()
            cur = self.conn.execute(
                "INSERT INTO run (flow_id, step_id, status_id)"
                " VALUES (?, ?, ?)",
                (fid["id"] if fid else None, stopped_step, status_id))
            run_id = cur.lastrowid
            for r in results:
                self.conn.execute(
                    "INSERT OR IGNORE INTO result"
                    " (run_id, step_id, source_id, has_provider, has_url,"
                    "  status_id)"
                    " VALUES (?, ?, ?, ?, ?, ?)",
                    (run_id, r["step_id"], r["source_id"],
                     r["has_provider"], r["has_url"],
                     1 if r["is_pass"] else 2))
            self.conn.commit()
        return {"status_id": status_id, "steps": visited,
                "ended_at": visited[-1] if visited else None,
                "step_id": stopped_step, "results": results,
                "run_id": run_id}

    def runs(self, limit=20):
        """列出 run 記錄（JOIN flow + step + status + result 證明）"""
        rows = [dict(r) for r in self.conn.execute(
            """SELECT r.id, r.flow_id, f.flow_name,
                      r.step_id, sq.seq AS step_seq,
                      r.status_id, s.status, r.created_at
               FROM run r
               LEFT JOIN flow f ON f.id = r.flow_id
               LEFT JOIN step st ON st.id = r.step_id
               LEFT JOIN seq sq ON sq.id = st.seq_id
               LEFT JOIN status s ON s.id = r.status_id
               ORDER BY r.id DESC LIMIT ?""", (limit,))]
        for r in rows:
            r["results"] = [dict(x) for x in self.conn.execute(
                """SELECT rs.id, rs.run_id, rs.step_id, rs.source_id,
                          src.source, rs.has_provider, rs.has_url,
                          rs.status_id, st2.status AS result_status
                   FROM result rs
                   LEFT JOIN source src ON src.id = rs.source_id
                   LEFT JOIN status st2 ON st2.id = rs.status_id
                   WHERE rs.run_id = ?
                   ORDER BY rs.id""", (r["id"],))]
        return rows

    def count(self):
        return self.conn.execute(
            "SELECT COUNT(*) FROM source WHERE is_active = 1").fetchone()[0]

    # ---------- source 表 ----------
    def sources(self, active_only=True):
        sql = "SELECT * FROM source WHERE 1=1"
        args = ()
        if active_only:
            sql += " AND is_active = 1"
        sql += " ORDER BY id"
        return [dict(r) for r in self.conn.execute(sql, args)]

    def source(self, source_id):
        return self.conn.execute(
            "SELECT * FROM source WHERE id = ?", (source_id,)).fetchone()

    def find_by_source(self, source):
        return self.conn.execute(
            "SELECT * FROM source WHERE source = ?", (source,)).fetchone()

    def insert_source(self, source, description=None, provider_id=None):
        cur = self.conn.execute(
            "INSERT OR IGNORE INTO source (source, description, provider_id)"
            " VALUES (?, ?, ?)",
            (source, description, provider_id))
        return cur.lastrowid

    def update_source(self, source_id, source=None, description=None, provider_id=None):
        sets, args = [], []
        if source is not None:
            sets.append("source = ?"); args.append(source)
        if description is not None:
            sets.append("description = ?"); args.append(description)
        if provider_id is not None:
            sets.append("provider_id = ?"); args.append(provider_id)
        if not sets:
            return
        args.append(source_id)
        self.conn.execute(f"UPDATE source SET {', '.join(sets)} WHERE id = ?", args)

    def deactivate(self, source_id):
        self.conn.execute("UPDATE source SET is_active = 0 WHERE id = ?", (source_id,))

    # ---------- authority_level 表（字典歸 terminology，唯讀代理） ----------
    # 2026-10-24p：authority_level 已搬去 terminology.db —— 呢度只讀
    def _term_conn(self):
        import sqlite3 as _sq
        tc = _sq.connect(r"C:\projects\meta\terminology\terminology.db")
        tc.row_factory = _sq.Row
        return tc

    def authority_levels(self, active_only=True):
        tc = self._term_conn()
        try:
            sql = "SELECT * FROM authority_level WHERE 1=1"
            args = ()
            if active_only:
                sql += " AND is_active = 1"
            sql += " ORDER BY level DESC"
            return [dict(r) for r in tc.execute(sql, args)]
        finally:
            tc.close()

    def authority_level(self, level_id):
        tc = self._term_conn()
        try:
            return tc.execute(
                "SELECT * FROM authority_level WHERE id = ?", (level_id,)).fetchone()
        finally:
            tc.close()

    def find_authority_level_by_meta(self, meta):
        tc = self._term_conn()
        try:
            return tc.execute(
                "SELECT * FROM authority_level WHERE meta = ?", (meta,)).fetchone()
        finally:
            tc.close()

    def find_authority_level_by_value(self, level):
        tc = self._term_conn()
        try:
            return tc.execute(
                "SELECT * FROM authority_level WHERE level = ?", (level,)).fetchone()
        finally:
            tc.close()

    # ---------- provider 表 ----------
    def providers(self, active_only=True):
        sql = "SELECT * FROM provider WHERE 1=1"
        args = ()
        if active_only:
            sql += " AND is_active = 1"
        sql += " ORDER BY id"
        return [dict(r) for r in self.conn.execute(sql, args)]

    def provider(self, provider_id):
        return self.conn.execute(
            "SELECT * FROM provider WHERE id = ?", (provider_id,)).fetchone()

    def find_provider_by_meta(self, meta):
        return self.conn.execute(
            "SELECT * FROM provider WHERE meta = ?", (meta,)).fetchone()

    def insert_provider(self, meta, authority_level_id=None, industry_id=None, official_url=None, description=None):
        cur = self.conn.execute(
            "INSERT OR IGNORE INTO provider (meta, authority_level_id, industry_id, official_url, description)"
            " VALUES (?, ?, ?, ?, ?)",
            (meta, authority_level_id, industry_id, official_url, description))
        return cur.lastrowid

    def update_provider(self, provider_id, meta=None, authority_level_id=None, industry_id=None, official_url=None, description=None):
        sets, args = [], []
        if meta is not None:
            sets.append("meta = ?"); args.append(meta)
        if authority_level_id is not None:
            sets.append("authority_level_id = ?"); args.append(authority_level_id)
        if industry_id is not None:
            sets.append("industry_id = ?"); args.append(industry_id)
        if official_url is not None:
            sets.append("official_url = ?"); args.append(official_url)
        if description is not None:
            sets.append("description = ?"); args.append(description)
        if not sets:
            return
        args.append(provider_id)
        self.conn.execute(f"UPDATE provider SET {', '.join(sets)} WHERE id = ?", args)

    def deactivate_provider(self, provider_id):
        self.conn.execute("UPDATE provider SET is_active = 0 WHERE id = ?", (provider_id,))

    def count_providers(self):
        return self.conn.execute(
            "SELECT COUNT(*) FROM provider WHERE is_active = 1").fetchone()[0]

    # ---------- industry 表（字典歸 terminology，唯讀代理） ----------
    def industries(self, active_only=True):
        tc = self._term_conn()
        try:
            sql = "SELECT * FROM industry WHERE 1=1"
            args = ()
            if active_only:
                sql += " AND is_active = 1"
            sql += " ORDER BY id"
            return [dict(r) for r in tc.execute(sql, args)]
        finally:
            tc.close()

    def industry(self, industry_id):
        tc = self._term_conn()
        try:
            return tc.execute(
                "SELECT * FROM industry WHERE id = ?", (industry_id,)).fetchone()
        finally:
            tc.close()

    def find_industry_by_meta(self, meta):
        tc = self._term_conn()
        try:
            return tc.execute(
                "SELECT * FROM industry WHERE meta = ?", (meta,)).fetchone()
        finally:
            tc.close()

    # ---------- Postman 真實數據（2026-10-28） ----------
    def postman_syncs(self, limit=50):
        """原始拉取記錄（證據本身）"""
        return [dict(r) for r in self.conn.execute(
            "SELECT * FROM postman_sync ORDER BY id DESC LIMIT ?",
            (limit,)).fetchall()]

    def postman_mock_logs(self, limit=50):
        """Mock Server 平台執行 log（真實請求/回應）"""
        return [dict(r) for r in self.conn.execute(
            "SELECT * FROM postman_mock ORDER BY id DESC LIMIT ?",
            (limit,)).fetchall()]

    def postman_runs(self, limit=50):
        """Runner / Cloud run 真實執行結果"""
        return [dict(r) for r in self.conn.execute(
            "SELECT * FROM postman_run ORDER BY id DESC LIMIT ?",
            (limit,)).fetchall()]

    def postman_mock_servers(self, active_only=True):
        """mock server 實體清單（owner + 定義）"""
        sql = "SELECT * FROM postman_mock_server"
        if active_only:
            sql += " WHERE is_public = 1"
        sql += " ORDER BY id"
        return [dict(r) for r in self.conn.execute(sql)]

    def postman_mock_execs(self, limit=100):
        """真實執行記錄（x_srv_trace 證明）"""
        return [dict(r) for r in self.conn.execute(
            "SELECT * FROM postman_mock_exec ORDER BY id DESC LIMIT ?",
            (limit,)).fetchall()]

    def postman_stats(self):
        """證據統計（sync / mock / run 各自幾多條）"""
        out = {}
        for name, table in (("sync", "postman_sync"),
                            ("mock_server", "postman_mock_server"),
                            ("mock_exec", "postman_mock_exec"),
                            ("mock", "postman_mock"),
                            ("run", "postman_run")):
            c = self.conn.execute(
                f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            out[name] = c
        return out

    def commit(self):
        self.conn.commit()

    def close(self):
        self.conn.close()