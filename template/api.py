"""api.py — template.db 對外 API"""

from .sql import SqlStore


class Template:
    """模板層（template.db）嘅對外介面

    2026-10-26：完全獨立 module（唔 clone question）。
    自己 12 張表（字典表 seed + runtime 表空），用作開新 module 嘅藍本。
    2026-10-27：自有 flow 執行引擎（唔 import question）。
    """

    def __init__(self, db_path=None):
        self.store = SqlStore(db_path) if db_path else SqlStore()

    def tables(self):
        """列出全部表"""
        return self.store.tables()

    def table_counts(self):
        """每張表嘅行數"""
        return {t: self.store.table_count(t) for t in self.store.tables()}

    def table(self, name, limit=100):
        """攞一張表嘅內容"""
        return self.store.query(
            f'SELECT * FROM "{name}" ORDER BY 1 LIMIT ?', (limit,))

    # ---------- flow 執行引擎（2026-10-27：template 自己 build） ----------
    def flows(self):
        """列出全部 flow"""
        return self.store.flows()

    def add_flow(self, flow_name, steps):
        """定義一條 flow（冪等）

        steps = [(condition, 5W2H, operator, expected_bool, seq), ...]
        例如 [("symbol", "what", "==", 1, 1), ...]
        """
        return self.store._add_flow(flow_name, steps)

    def flow_steps(self, flow_name):
        """列出一個 flow 嘅 steps"""
        return self.store.flow_steps(flow_name)

    def run_flow(self, flow_name, value, save=True):
        """行一條 flow（逐步判斷，寫 run）"""
        return self.store.run_flow(flow_name, value, save)

    def flow_runs(self, limit=20):
        """列出執行記錄"""
        return self.store.flows_runs(limit)

    # ---------- Proof 系統（2026-10-27 用戶設計） ----------
    def formulas(self):
        """列出全部 formula"""
        return self.store.formulas()

    def formula(self, formula_id):
        """攞一條 formula 連 cuter / proof / tables / conditions"""
        return self.store.formula(formula_id)

    def cut_formula(self, formula_id):
        """將 formula.full 切粒入 formula_cuter"""
        return self.store._cut_formula(formula_id)

    def execute_formula(self, formula_id, params=None):
        """執行一條 formula 嘅 SQL（真表查詢）"""
        return self.store.execute_formula(formula_id, params)

    def proof_for_flow(self, flow_name):
        """搵一個 flow 嘅 proof formula step"""
        return self.store.proof_formula_for_flow(flow_name)

    # ---------- Evidence（2026-10-27：formula 生成證據，唔 replace SSOT） ----------
    def gen_evidence_formulas(self, targets=None):
        """由 SSOT 自動生成 evidence formulas 並執行（寫 evidence 表）

        targets = 可選表名；冇 = 全自動偵測（structure.db 真表 + 字典表）。
        唔郁任何 SSOT 表。
        """
        return self.store.gen_evidence_formulas(targets)

    def evidences(self, limit=50):
        """列出 evidence 記錄"""
        return self.store.evidences(limit=limit)

    def evidence_summary(self):
        """evidence 摘要（total / match / mismatch）"""
        return self.store.evidence_summary()

    def close(self):
        self.store.close()