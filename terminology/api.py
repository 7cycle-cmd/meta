"""api.py — terminology.db 對外 API"""

from .sql import SqlStore


class Terminology:
    """術語（terminology.db）嘅對外介面

    data_collect：每個 resource_id 嘅真實 value（text / number ... 全部）
    用法：
        t.collect(42, "750000")      # 記錄 resource 42 嘅 value
        t.value_of(42)               # 攞返
        t.collected()                # 全部已收集 value
    """

    def __init__(self, db_path=None):
        self.store = SqlStore(db_path) if db_path else SqlStore()

    def list_terms(self):
        return self.store.terms()

    def get(self, term_id):
        r = self.store.term(term_id)
        return dict(r) if r else None

    def lookup(self, meta):
        r = self.store.find_by_meta(meta)
        return dict(r) if r else None

    def register(self, meta, description):
        existing = self.store.find_by_meta(meta)
        if existing:
            return existing["id"], False
        tid = self.store.insert_term(meta, description)
        self.store.commit()
        return tid, True

    def update(self, term_id, **fields):
        self.store.update_term(term_id, **fields)
        self.store.commit()

    def deactivate(self, term_id):
        self.store.deactivate(term_id)
        self.store.commit()

    def count(self):
        return self.store.count()

    def add_value(self, value, taxonomy_id=None):
        """新增 / 攞一個提交值嘅 id（冪等；taxonomy_id = 邊個 module 登記）"""
        return self.store.add_value(value, taxonomy_id=taxonomy_id)

    def values(self, limit=50):
        """列出 value 表（含 taxonomy_id + module 名，由 taxonomy.db 查）"""
        rows = [dict(r) for r in self.store.conn.execute(
            "SELECT id, value, taxonomy_id FROM value"
            " ORDER BY id DESC LIMIT ?", (limit,))]
        # module 名：taxonomy.db registry JOIN
        try:
            import sqlite3 as _sq
            tc = _sq.connect(r"C:\projects\meta\taxonomy\taxonomy.db")
            tc.row_factory = _sq.Row
            try:
                mods = {r["id"]: r["meta"] for r in tc.execute(
                    "SELECT id, meta FROM registry"
                    " WHERE tree_id = 2 AND is_active = 1")}
            finally:
                tc.close()
        except Exception:
            mods = {}
        for d in rows:
            d["module_name"] = mods.get(d.get("taxonomy_id"))
        return rows

    # ---- data_collect ----

    def collect(self, resource_id, value):
        """記錄一個 resource 嘅真實 value（重複記錄 = 更新）"""
        self.store.collect_value(resource_id, value)
        self.store.commit()

    def collect_table(self, db_table_id, value):
        """記錄一張表（resource.db db_table.id）嘅真實 value"""
        self.store.collect_table_value(db_table_id, value)
        self.store.commit()

    def collect_field(self, db_field_id, value):
        """記錄一個欄位（resource.db db_field.id）嘅真實 value"""
        self.store.collect_field_value(db_field_id, value)
        self.store.commit()

    def collect_many(self, pairs):
        """一次過記錄多個 (resource_id, value)"""
        for resource_id, value in pairs:
            self.store.collect_value(resource_id, value)
        self.store.commit()

    def value_of(self, resource_id):
        r = self.store.value_of(resource_id)
        return dict(r) if r else None

    def table_value_of(self, db_table_id):
        r = self.store.table_value_of(db_table_id)
        return dict(r) if r else None

    def field_value_of(self, db_field_id):
        r = self.store.field_value_of(db_field_id)
        return dict(r) if r else None

    def collected(self, active_only=True):
        return self.store.collected(active_only)

    def update_collected(self, resource_id, value=None, is_active=None):
        self.store.update_collected(resource_id, value=value, is_active=is_active)
        self.store.commit()

    def deactivate_collected(self, resource_id):
        self.store.deactivate_collected(resource_id)
        self.store.commit()

    def count_collected(self):
        return self.store.count_collected()

    # ---------- evidence（通用證據表，2026-10-25 用戶要求） ----------

    def record_evidence(self, value, run_id, condition_meta,
                        status_id=1, source_id=None):
        """寫一條證據：值（value）喺 run 通過咗 condition 判斷（冪等）"""
        return self.store.record_evidence(value, run_id, condition_meta,
                                          status_id, source_id)

    def evidence_of(self, value, condition_meta=None, active_only=True):
        """一個值嘅全部證據（可 filter condition）"""
        return self.store.evidence_of(value, condition_meta, active_only)

    def word_industries(self, value, active_only=True):
        """一個詞嘅 industry 證據（有 PASS 證據 = 屬行業）"""
        return self.store.word_industries(value, active_only)

    def unbind_evidence(self, value, run_id, condition_meta=None):
        """解除證據（冪等）"""
        return self.store.unbind_evidence(value, run_id, condition_meta)

    def unbind_word_industry(self, value, run_id):
        """解除一個詞嘅 industry 證據（冪等）"""
        return self.store.unbind_word_industry(value, run_id)

    # ---------- flow（驗證鏈執行引擎，自己擁有） ----------

    def flows(self, active_only=True):
        """列出驗證鏈"""
        return self.store.flows(active_only)

    def flow_completeness(self, flow_name=None):
        """測量：每條 flow 喺 5W2H 7 維度嘅完整度（2026-10-28 用戶設計）"""
        return self.store.flow_completeness(flow_name)

    # ---------- expected_source / step_output（2026-10-28 用戶設計）----------

    def set_expected_source(self, question_id, formula_id=None,
                            formula_cutter_id=None, value=None,
                            output_format="1,0"):
        """設定一條 question 嘅期望值來源（Table-driven，冪等）"""
        return self.store.set_expected_source(
            question_id, formula_id, formula_cutter_id, value, output_format)

    def build_expected_sources(self, source_module=None):
        """由 question 逐個建 expected_source（step_input 表話事攞 *_id）"""
        return self.store._build_expected_sources(source_module)

    def expected_sources(self, question_id=None):
        """列出 expected_source（可按 question 篩選）"""
        return self.store.expected_sources(question_id)

    # ---------- question_template（2026-10-28 用戶要求）----------
    def add_question_template(self, value_id=0, condition_id=None,
                              operator_id=None, expected_source_id=None):
        """新增一條 question_template（可重用提問）"""
        return self.store.add_question_template(
            value_id, condition_id, operator_id, expected_source_id)

    def question_templates(self, active_only=True, limit=100):
        """列出 question_template"""
        return self.store.question_templates(active_only, limit)

    def count_question_templates(self):
        """question_template 總數"""
        return self.store.count_question_templates()

    def record_step_output(self, step_id, run_id, question_id, value,
                           expert_id=None, output_format="1,0"):
        """記錄一步嘅實際輸出（1,0）"""
        return self.store.record_step_output(
            step_id, run_id, question_id, value, expert_id, output_format)

    def step_outputs(self, run_id=None, step_id=None):
        """列出 step_output（可按 run / step 篩選）"""
        return self.store.step_outputs(run_id, step_id)

    def output_completeness(self, flow_name=None):
        """測量：每條 flow 嘅輸出完整度"""
        return self.store.output_completeness(flow_name)

    # ---------- output_by / output_type / hardcode_value（2026-10-28）----------

    def output_types(self, active_only=True):
        """列出 output_type（code / db_table）"""
        return self.store.output_types(active_only)

    def set_output_by(self, output_id, output_type_meta):
        """記錄一個 output 嘅來源方式（code / db_table，冪等）"""
        return self.store.set_output_by(output_id, output_type_meta)

    def output_bys(self, output_type_meta=None):
        """列出 output_by（可按來源方式篩選）"""
        return self.store.output_bys(output_type_meta)

    def add_hardcode_value(self, value_id, package_id=None, file_id=None,
                           taxonomy_id=None, skill_id=None):
        """標記一個硬編碼值（冇 db_table/db_field 出處）"""
        return self.store.add_hardcode_value(
            value_id, package_id, file_id, taxonomy_id, skill_id)

    def hardcode_values(self, active_only=True):
        """列出硬編碼值"""
        return self.store.hardcode_values(active_only)

    def hardcode_monitor(self):
        """監控：全站硬編碼值統計"""
        return self.store.hardcode_monitor()

    def scan_hardcodes(self, module_name):
        """AST 掃描一個 module：自動登記 hardcode_value（2026-10-28）"""
        return self.store.scan_hardcodes(module_name)

    # ---------- flow_branch / next_flow（分支決策，0 hardcode） ----------

    def add_branch_rule(self, flow_name, condition_meta, status_id,
                        target_flow_name):
        """加一條分支規則（冪等）

        flow_name        = 邊條 flow 跑完分叉
        condition_meta   = 用邊個 condition
        status_id        = 結果（1=PASS 0=FAIL）
        target_flow_name = 呢個結果 -> 去邊條 flow
        """
        return self.store.add_branch_rule(flow_name, condition_meta,
                                          status_id, target_flow_name)

    def branches(self, run_id=None, limit=50):
        """列出 flow_branch 記錄（runtime 判斷結果）"""
        sql = """SELECT fb.id, fb.run_id, fb.value_id, v.value,
                        fb.condition_id, c.meta AS condition_meta,
                        fb.status_id, fb.created_at
                 FROM flow_branch fb
                 LEFT JOIN value v ON v.id = fb.value_id
                 LEFT JOIN condition c ON c.id = fb.condition_id"""
        args = ()
        if run_id is not None:
            sql += " WHERE fb.run_id = ?"
            args = (run_id,)
        sql += " ORDER BY fb.id DESC LIMIT ?"
        return [dict(r) for r in self.store.conn.execute(sql, args + (limit,))]

    def next_flows(self, limit=50):
        """列出 next_flow 規則"""
        return [dict(r) for r in self.store.conn.execute(
            """SELECT nf.id, nf.flow_id, f.flow_name,
                      nf.condition_id, c.meta AS condition_meta,
                      nf.status_id,
                      nf.flow_target_id AS target_flow_id,
                      tf.flow_name AS target_flow,
                      nf.is_active, nf.created_at
               FROM next_flow nf
               LEFT JOIN flow f ON f.id = nf.flow_id
               LEFT JOIN condition c ON c.id = nf.condition_id
               LEFT JOIN flow tf ON tf.id = nf.flow_target_id
               ORDER BY nf.id DESC LIMIT ?""", (limit,))]

    def flow_steps(self, flow_name, active_only=True):
        """列出一個 flow 嘅 steps"""
        return self.store.flow_steps(flow_name, active_only)

    def run_flow(self, flow_name, answers=None, value=None,
                 value_id=None, save=True, role_id=None, rule_id=None):
        """行一個驗證鏈（線性，第一個 FAIL 就停）

        answers = {question_id: 原始答案}（operator / expected 由 DB 控制）
        value    = 提交去檢查嘅值（自動入 value 表）
        role_id  = role.db registry.id（邊個角色執行，2026-10-27）
        rule_id  = rule.db rule.id（跟邊條規則，2026-10-27e）
        全部 PASS -> status_id=1（approved）；第一個 FAIL -> 2（rejected）
        """
        return self.store.run_flow(flow_name, answers, value,
                                   value_id, save, 0, role_id, rule_id)

    def run_flow_ids(self, flow_ids, value=None, value_id=None,
                     save=True, role_id=None, rule_id=None):
        """揀 flow id 組合順序執行（1,4,67,7 重用；FAIL 即刻停）"""
        return self.store.run_flow_ids(flow_ids, value, value_id,
                                       save, role_id, rule_id)

    def flow_runs(self, limit=20):
        """列出執行記錄（證明）"""
        return self.store.flow_runs(limit)

    def word_proof(self, word):
        """一個 word 嘅完整證明（registry + 證據鏈 + 來源）

        word_category 有行 = 被 approved 過（terminology registry 證明）。
        返回 {"registered", "word_category", "evidence", "source", "runs"}
        """
        return self.store.word_proof(word)

    # ---------- source_register（2026-10-27：表話事，零 hardcode） ----------
    def set_source_for_word(self, word, source_id, registered_by="api"):
        """設定一個詞用邊個 source 證明（source_register 表，冪等）

        source_id = source.db source.id（一定要存在）。
        之後 source_register flow 會用呢個 source 登記新詞。
        """
        if not word or not source_id:
            raise ValueError("word + source_id 必填")
        # source_id 一定要存在
        import sqlite3 as _sq
        _c = _sq.connect(r"C:\projects\meta\source\source.db")
        try:
            has = _c.execute(
                "SELECT 1 FROM source WHERE id = ?", (source_id,)).fetchone()
        finally:
            _c.close()
        if not has:
            raise ValueError(f"source_id={source_id} 唔存在（source.db 查無）")
        self.store.conn.execute(
            "INSERT INTO source_register"
            " (word, source_id, registered_by)"
            " SELECT ?, ?, ? WHERE NOT EXISTS"
            " (SELECT 1 FROM source_register WHERE LOWER(word) = LOWER(?))",
            (str(word).lower(), source_id, registered_by, word))
        self.store.conn.execute(
            "UPDATE source_register SET source_id = ?,"
            " registered_by = ?, updated_at = datetime('now','localtime')"
            " WHERE LOWER(word) = LOWER(?)",
            (source_id, registered_by, word))
        self.store.conn.commit()
        r = self.store.conn.execute(
            "SELECT id FROM source_register WHERE LOWER(word) = LOWER(?)",
            (word,)).fetchone()
        return r["id"] if r else None

    def source_register_rows(self, active_only=True):
        """列出 source_register 全部（word -> source 選擇）"""
        sql = "SELECT * FROM source_register WHERE 1=1"
        if active_only:
            sql += " AND is_active = 1"
        sql += " ORDER BY id"
        return [dict(r) for r in self.store.conn.execute(sql)]

    def get_source(self, word=None):
        """一個詞用邊個 source（source_register 表話事；冇 word = 後備 source）"""
        return self.store.get_source(word)

    def verify_source(self, word):
        """驗證一個詞嘅 source 證明（有冇效）"""
        return self.store.source_proof_of(word)

    def proof_source(self, word):
        """證明一個詞嘅 source（行 source_register flow 登記；返 word_proof 全貌）"""
        return self.word_proof(word)

    def close(self):
        self.store.close()