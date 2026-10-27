"""api.py — question.db 對外 API

question = 問題層：test（測試維度）× 5W2H（提問框架）組合出問題
每個問題帶 operator（operator_id）+ 期望值（expected_id）

用法：
    from question import Question
    q = Question()
    q.add_question(test_id=1, w5h2_id=1, calc_meta="==", pass_value="1")
    q.close()
"""

from .sql import SqlStore


class Question:
    """問題層（question.db）嘅對外介面"""

    def __init__(self, db_path=None):
        self.store = SqlStore(db_path) if db_path else SqlStore()

    # ---------- value（提交值字典：submit xxx 去檢查） ----------
    def add_value(self, value):
        """新增 / 攞一個提交值嘅 id（幂等）

        value = 提交去檢查嘅值（例如 "Anthropic spec"）
        返回 value.id（INT）
        """
        return self.store.add_value(value)

    def values(self):
        """列出全部提交值"""
        return self.store.values()

    # ---------- test ----------
    def add_test(self, meta):
        """新增盲測維度（幂等）

        meta = 維度名（可以係空字串 "" = 空 row）
        """
        return self.store.add_test(meta)

    def remove_test(self, meta):
        """移除一個盲測維度（幂等）

        安全：若有 question 引用該 test_id -> 掦 ValueError
        """
        return self.store.remove_test(meta)

    def rename_test(self, old_meta, new_meta):
        """改名一個盲測維度（幂等；撞名 -> 掦 ValueError）"""
        return self.store.rename_test(old_meta, new_meta)

    def tests(self, active_only=True):
        return self.store.tests(active_only)

    # ---------- 5W2H ----------
    def add_5w2h(self, meta):
        """新增提問框架（冪等）"""
        return self.store.add_5w2h(meta)

    def list_5w2h(self, active_only=True):
        return self.store.list_5w2h(active_only)

    # ---------- question ----------
    def add_question(self, test_id, w5h2_id, calc_meta=None, pass_value=None):
        """建立一個問題（test × 5W2H 組合 + 判斷條件，冪等）

        calc_meta  = operator 名（== / >= / <= / != / > / <）-> operator.id
        pass_value = 期望值（== 1 / >= 100 ...）-> expected.id
        """
        return self.store.add_question(test_id, w5h2_id, calc_meta, pass_value)

    def set_expected(self, question_id, calc_meta=None, pass_value=None):
        """設定一個問題嘅判斷條件（DB 控制，唔係 code）

        calc_meta  = operator 名（必須喺 operator 表存在，唔可以自行發明）
        pass_value = 期望值（冇就自動註冊入 expected 表）
        """
        return self.store.set_expected(question_id, calc_meta, pass_value)

    def set_operator(self, question_id, calc_meta):
        """只設定一個問題嘅 operator（唔碰 expected_id）"""
        return self.store.set_operator(question_id, calc_meta)

    def set_all_operators(self, calc_meta):
        """將全部問題嘅 operator 設為同一個（只改 operator_id）"""
        return self.store.set_all_operators(calc_meta)

    def set_all_expecteds(self, pass_value):
        """將全部問題嘅期望值設為同一個（只改 expected_id）"""
        return self.store.set_all_expecteds(pass_value)

    # ---------- operator（operator 字典：點比，DB 控制） ----------
    def add_operator(self, meta, expression=None, description=None):
        """新增 operator（冪等）

        meta       = operator 名（== / >= / <= / != / > / <）
        expression = 判斷表達式（answer = 答案，pass_value = 期望值）
        """
        return self.store.add_operator(meta, expression, description)

    def operators(self, active_only=True):
        """列出 operator 字典"""
        return self.store.operators(active_only)

    # ---------- expected（期望值字典：比幾多，DB 控制） ----------
    def add_expected(self, pass_value=None, description=None):
        """新增期望值（冪等）

        pass_value  = 期望值（== 1 / >= 100 ...，由表控制）
        description = 描述
        """
        return self.store.add_expected(pass_value, description)

    def set_expected_value(self, expected_id, pass_value):
        """設定一個期望值列嘅值（DB 控制）"""
        return self.store.set_expected_value(expected_id, pass_value)

    def remove_expected(self, expected_id):
        """移除一個期望值列（幂等；有 question 引用 -> 拒絕）"""
        return self.store.remove_expected(expected_id)

    def expecteds(self, active_only=True):
        """列出判斷條件字典"""
        return self.store.expecteds(active_only)

    def questions(self, active_only=True):
        return self.store.questions(active_only)

    # ---------- taxonomy（module 大類 × flow 關聯） ----------
    def add_taxonomy_question(self, flow_id, tree_id=2):
        """將一個驗證鏈綁定去 module 大類（tree_id=2，幂等）

        flow_id = flow.id（邊條驗證鏈）
        返回 taxonomy.id（INT）
        """
        return self.store.add_taxonomy_question(flow_id, tree_id)

    def taxonomy_questions(self, tree_id=2, active_only=True):
        """列出 module 大類嘅全部問題（JOIN 名）"""
        return self.store.taxonomy_questions(tree_id, active_only)

    # ---------- shortcut（API 快捷路由） ----------
    def add_shortcut(self, api_url, shortcut):
        """建立 API 快捷路由（api_url -> shortcut，幂等）"""
        return self.store.add_shortcut(api_url, shortcut)

    def shortcuts(self, active_only=True):
        """列出快捷路由"""
        return self.store.shortcuts(active_only)

    def flow_by_shortcut(self, api_url):
        """由 api_url 攞 flow_name（唔 hardcode，靠 shortcut 表）"""
        return self.store.flow_by_shortcut(api_url)

    def apis(self, active_only=True):
        """本 module 對外 API 註冊（api 表，DB 管理）"""
        return self.store.apis(active_only)

    def code_registries(self, active_only=True):
        """本 module 檔案註冊（code_registry 表，DB 管理）"""
        return self.store.code_registries(active_only)

    def code_flows(self, active_only=True):
        """程式碼流程（code_flow + code_step，DB 管理）"""
        return self.store.code_flows(active_only)

    def value_defnes(self, active_only=True):
        """字典定義（value_defne 表）"""
        return self.store.value_defnes(active_only)

    def unique_defnes(self, active_only=True):
        """唯一配對定義（unique_defne 表）"""
        return self.store.unique_defnes(active_only)

    # ---------- flow（驗證鏈） ----------
    def add_flow(self, flow_name="5w2h"):
        """建立一條驗證鏈（冪等）"""
        return self.store.add_flow(flow_name)

    def flows(self, active_only=True):
        return self.store.flows(active_only)

    # ---------- step（驗證鏈步驟） ----------
    def add_step(self, flow_name, question_id, seq):
        """建立一個 step（幂等：同一 flow + seq 更新）

        flow_name   = 驗證鏈名（5w2h / spec ...）
        question_id = question.id（問邊個問題）
        seq         = 第幾步（1, 2, 3...）
        2026-10-24：線性 flow，冇分支。
        """
        return self.store.add_step(flow_name, question_id, seq)

    def flow_steps(self, flow_name="5w2h", active_only=True):
        return self.store.flow_steps(flow_name, active_only)

    def run_flow(self, flow_name="5w2h", answers=None, save=True,
                 value=None, value_id=None, register_meta=None,
                 register_type="value", register_source="question"):
        """行一個驗證鏈：逐個問題問，calculation + expected 表決定 pass/fail

        answers  = {question_id: 原始答案}（唔係 pass/fail！）
            operator 由 calculation 表決定（== / >= / <= / != / > / <）
            期望值由 expected 表決定（pass_value）

        value    = 提交去檢查嘅值（例如 "Anthropic spec"）
                   -> 自動寫入 value 表，value_id 指向它
        value_id = 已有嘅 value.id（同 value 二選一）
        status_id == 1（approved）且 register_meta 提供時 -> 自動註冊入 resource.db
        """
        return self.store.run_flow(flow_name, answers, save,
                                   value, value_id, register_meta,
                                   register_type, register_source)

    def flow_runs(self, limit=20):
        """列出驗證鏈執行記錄（JOIN flow + test + status 攞名，含答案）"""
        return self.store.flow_runs(limit)

    # ---------- terminology（我哋嘅 customer：批量處理 single words） ----------
    def run_terminology(self, flow_name="5w2h",
                        register_type="value", register_source="question",
                        limit=None):
        """用同一條 flow 批量處理 terminology.db 嘅所有 single words

        terminology.db = 我哋嘅 customer（所有詞都喺嗰度）
        single word   = get_word 冇 _ 冇空格（例如 build / fill / id ...）

        答案由詞本身自動計算（唔可以 caller 提供，唔可以 fake）：
            symbol?       -> 詞有符號（/ . , ; ' 等標點 / emoji；數字唔算符號）
            speech?       -> 詞係英文單詞（is_english 表）
            single word?  -> 詞冇 _ 冇空格（== 1）

        每個詞 -> 行同一條 flow -> 寫入 run（證明）
                -> 寫入 terminology.db term_flow_run（customer 自己嘅記錄）
        approved  -> 自動註冊入 resource.db（meta = word:<get_word>）

        返回 {"total": n, "approved": n, "rejected": n, "runs": [...]}
        """
        return self.store.run_terminology(
            flow_name, register_type, register_source, limit)

    def count(self):
        return self.store.count()

    def close(self):
        self.store.close()