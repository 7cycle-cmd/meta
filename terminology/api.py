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
                 value_id=None, save=True):
        """行一個驗證鏈（線性，第一個 FAIL 就停）

        answers = {question_id: 原始答案}（operator / expected 由 DB 控制）
        value    = 提交去檢查嘅值（自動入 value 表）
        全部 PASS -> status_id=1（approved）；第一個 FAIL -> 2（rejected）
        """
        return self.store.run_flow(flow_name, answers, value,
                                   value_id, save)

    def flow_runs(self, limit=20):
        """列出執行記錄（證明）"""
        return self.store.flow_runs(limit)

    def word_proof(self, word):
        """一個 word 嘅完整證明（registry + 證據鏈 + 來源）

        word_category 有行 = 被 approved 過（terminology registry 證明）。
        返回 {"registered", "word_category", "evidence", "source", "runs"}
        """
        return self.store.word_proof(word)

    def close(self):
        self.store.close()