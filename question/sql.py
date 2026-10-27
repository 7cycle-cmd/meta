"""sql.py — question.db 存取層

question = 問題層：test（測試維度）× 5W2H（提問框架）組合出問題
每個問題帶 operator（operator_id）+ 期望值（expected_id）

表：
    test              測試維度字典（speech / word / spec / industry / source / proof / single word / symbol）
    "5W2H"            提問框架字典（what / where / when / who / why / how / how much）
    operator          operator 字典（點比）+ expression（判斷表達式）
    expected          期望值字典（比幾多：pass_value）
    value             提交值字典（submit xxx 去驗證）
    question          test × 5W2H 組合 + 判斷條件（operator_id + expected_id）
    flow            驗證鏈（flow_name）
    step            驗證鏈步驟（flow_id + seq + question_id）
    run             執行記錄（flow_id + value_id + step_id + status_id）
    answer          答案字典（1=真/有，0=假/冇）
    result          每個問題嘅答案 + 狀態（證明）
    status            狀態字典（approved / rejected / NA）

判斷條件 vs 判斷結果：
    question.operator_id + question.expected_id = 判斷條件（DB 控制）
    result.status_id                   = 判斷結果（執行時由 _judge 判斷出嚟）

注意：
    "5W2H" 表名以數字開頭，所有 SQL 都要用 "5W2H" 引號包住。

用法：
    from question.sql import SqlStore
    s = SqlStore()
    s.add_question(test_id=1, w5h2_id=1, calc_meta="==", pass_value="1")
    s.close()
"""

import os
import sqlite3

from .schema import *  # noqa: F401,E402

DB_PATH = r"C:\projects\meta\question\question.db"





# 預設 operator 字典（operator 表，seed，DB 可改）
# expression = 判斷表達式（answer = 答案，pass_value = 期望值，由 _judge eval 執行）
# 用 float() 比較 -> int vs str 唔會錯（answer=1, pass_value='1' 都啱）
#
# 三組 operator：
#   A. 數值比較（float）  ==  !=  >=  <=  >  <        —— answer / pass_value 係數
#   B. Boolean（真假）    is_true  is_false  bool_eq  —— answer 係 True/False/1/0
#   C. 字串比較（str）    eq  ne                      —— answer 係文字（留俾其他用途）
DEFAULT_OPERATORS = [
    # A. 數值比較
    ("==", "float(answer) == float(pass_value)", "答案 == 期望值（數值）"),
    ("!=", "float(answer) != float(pass_value)", "答案 != 期望值（數值）"),
    (">=", "float(answer) >= float(pass_value)", "答案 >= 期望值（數值）"),
    ("<=", "float(answer) <= float(pass_value)", "答案 <= 期望值（數值）"),
    (">", "float(answer) > float(pass_value)", "答案 > 期望值（數值）"),
    ("<", "float(answer) < float(pass_value)", "答案 < 期望值（數值）"),
    # B. Boolean（真假）—— 系統層係 True/False，人類層係 yes/no
    ("is_true", "answer is True",
     "答案係 True（嚴格 bool；1 唔算）"),
    ("is_false", "answer is False",
     "答案係 False（嚴格 bool；0 唔算）"),
    ("bool_eq",
     "(str(answer).strip().lower() in ('yes', 'true', '1')) =="
     " (str(pass_value).strip().lower() in ('yes', 'true', '1'))",
     "答案嘅真假 == 期望值嘅真假（yes/no/true/false/1/0 都通）"),
    # C. 字串比較（留俾其他用途：文字答案）
    ("eq", "str(answer) == str(pass_value)",
     "文字答案 == 期望值（字串比較，唔做數值轉換）"),
    ("ne", "str(answer) != str(pass_value)",
     "文字答案 != 期望值（字串比較，唔做數值轉換）"),
]

# 預設期望值（expected 表，seed）—— 2026-10-24t 用 boolean_id（0/1）
DEFAULT_EXPECTED_VALUES = [
    (1, "期望值 1（真）"),
]

# 冇任何 calculation 可用時嘅預設判斷表達式（code 安全網）
DEFAULT_JUDGE_EXPR = "answer is not None and answer != '' and answer != 0"






# 預設字典（seed，冪等）
DEFAULT_TESTS = [
    "speech", "word", "spec", "industry", "source", "proof",
    "single word", "symbol", "letter", "INT",
]

DEFAULT_W5H2 = [
    "what", "where", "when", "who", "why", "how", "how much",
]

DEFAULT_STATUS = [
    "approved", "rejected",   # 2026-10-24t：NA 移除（status 變兩態 0/1）
]

# 預設 flow（seed，冪等）
DEFAULT_FLOWS = ["5w2h", "english word", "industry spec"]

# 預設序號（seq 表，seed，冪等）
DEFAULT_SEQS = list(range(1, 11))

# 預設 API 快捷路由（shortcut 表，seed，冪等）
# api_url = 路由（/run 係 default，/english /spec 係短名 alias）
DEFAULT_SHORTCUTS = [
    ("/run", "5w2h"),              # default：/run?value= 行 5w2h
    ("/run/5w2h", "5w2h"),
    ("/run/english-word", "english word"),
    ("/run/industry-spec", "industry spec"),
    ("/english", "english word"),   # 短名 alias
    ("/spec", "industry spec"),     # 短名 alias
]


class SqlStore:
    def __init__(self, db_path=DB_PATH):
        # 2026-10-23：明示 module/file（唔靠 stack 偵測，保證 api_id 推到）
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(
            TEST_DDL + W5H2_DDL + EXPECTED_DDL + OPERATOR_DDL + VALUE_DDL
            + QUESTION_DDL
            + FLOW_DDL + SEQ_DDL + STEP_DDL
            + RUN_DDL + ANSWER_DICT_DDL + RESULT_DDL + STATUS_DDL
            + TAXONOMY_DDL + SHORTCUT_DDL
            + API_TYPE_DDL + API_DDL
            + CODE_TYPE_DDL + CODE_CONDITION_DDL + CODE_REGISTRY_DDL
            + CODE_FLOW_DDL + CODE_STEP_DDL
            + VALUE_DEFNE_DDL + UNIQUE_DEFNE_DDL
            + QUESTION_TEXT_DDL + W5W2H_TEXT_DDL)
        self.conn.commit()
        self._migrate_calculation_operator()
        self._migrate_code_condition()
        self._migrate_rename_tables()
        self._migrate_result()
        self._migrate()
        self._migrate_expected_split()
        self._migrate_run_value()
        self._migrate_test_symbol()
        self._migrate_linear_flow()
        self._migrate_taxonomy_flow()
        self._migrate_question_columns()
        self._migrate_question_operator_id()
        self._migrate_step_seq()
        self._migrate_step_columns()
        self._migrate_shortcut()
        self._migrate_code_condition()
        self._seed()

    def _migrate_question_operator_id(self):
        """遷移（幂等）：question.calculation_id 欄 -> operator_id

        2026-10-24（用戶要求）：表 operator + 欄位 operator_id 一致命名。
        SQLite 3.25+ 支援 RENAME COLUMN（保留資料 + 引用）。
        幂等：第二次跑（冇 calculation_id 欄）-> 跳過。
        """
        qcols = [c[1] for c in self.conn.execute(
            "PRAGMA table_info('question')")]
        if "calculation_id" not in qcols:
            return
        self.conn.execute(
            "ALTER TABLE question RENAME COLUMN calculation_id TO operator_id")
        self.conn.commit()

    def _migrate_calculation_operator(self):
        """遷移（幂等）：calculation 表 -> operator 表

        2026-10-24（用戶要求）：操作符字典改名 operator（語意清晰）。
        舊表存在 -> RENAME（保留 id + 資料，question.calculation_id 唔使改）。
        幂等：第二次跑（冇 calculation 表）-> 跳過。
        """
        has_old = self.conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='calculation'"
        ).fetchone()
        if not has_old:
            return  # 已經新版（或者從未有用過舊名）
        has_new = self.conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='operator'"
        ).fetchone()
        if has_new:
            # 兩者都有（新表 = CREATE IF NOT EXISTS 建立嘅空表）-> 掉空新表先 RENAME
            n = self.conn.execute(
                "SELECT COUNT(*) FROM operator").fetchone()[0]
            if n == 0:
                self.conn.execute("DROP TABLE operator")
            else:
                # 兩邊都有資料（異常）-> 新表資料保留，舊表唔郁兼報錯
                raise ValueError(
                    "operator 表已存在且有資料，唔可以自動合併（需要人手處理）")
        self.conn.execute("ALTER TABLE calculation RENAME TO operator")
        self.conn.commit()

    def _migrate_code_condition(self):
        """遷移（幂等）：code_registry.condition 欄 -> condition_id

        2026-10-24c（用戶要求）：condition 獨立成表（code_condition），
        code_registry 用 condition_id（同 code_type_id 一樣 pattern）。
        舊表有 condition 欄 -> 遷移到 code_condition 後 drop 欄。
        如果 reset 又得（新 seed 會重建全部行）。
        """
        # code_condition 表（CREATE IF NOT EXISTS 已執行）
        conds = ["file", "def", "class", "async def", "main"]
        for c in conds:
            self.conn.execute(
                "INSERT INTO code_condition (value) SELECT ? WHERE NOT EXISTS"
                " (SELECT 1 FROM code_condition WHERE value = ?)", (c, c))
        cols = [c[1] for c in self.conn.execute(
            "PRAGMA table_info('code_registry')")]
        if "condition" not in cols:
            return  # 已經新版
        # 舊版 -> 逐行：condition 名 -> condition_id
        rows = [dict(r) for r in self.conn.execute(
            "SELECT * FROM code_registry ORDER BY id")]
        self.conn.execute("DROP TABLE code_registry")
        self.conn.execute(CODE_REGISTRY_DDL)
        for r in rows:
            cond = r.get("condition") or "file"
            cr = self.conn.execute(
                "SELECT id FROM code_condition WHERE value = ?",
                (cond,)).fetchone()
            if not cr:
                continue
            self.conn.execute(
                "INSERT INTO code_registry"
                " (id, code_type_id, condition_id, meta, description,"
                "  filename, mapping_line, is_active, created_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (r["id"], r["code_type_id"], cr["id"], r["meta"],
                 r.get("description"), r["filename"], r["mapping_line"],
                 r.get("is_active", 1), r.get("created_at")))
        self.conn.commit()

    def _migrate_shortcut(self):
        """遷移（幂等）：shortcut.shortcut 欄移除 UNIQUE（多 alias 同一 flow）

        2026-10-24b：/run + /run/5w2h 都指 5w2h flow -> shortcut 欄必須可重複。
        舊表有 UNIQUE -> rebuild。
        """
        idxs = [r[1] for r in self.conn.execute(
            "PRAGMA index_list('shortcut')")]
        # 檢查 shortcut 欄有冇 UNIQUE（autoindex 有 2 個 = api_url + shortcut）
        uniq_cols = []
        for ix in idxs:
            if not ix.startswith("sqlite_autoindex"):
                continue
            cols = [r[2] for r in self.conn.execute(
                f"PRAGMA index_info('{ix}')")]
            if cols == ["shortcut"] or "shortcut" in cols:
                uniq_cols.append(cols)
        if not uniq_cols:
            return
        rows = [dict(r) for r in self.conn.execute(
            "SELECT * FROM shortcut ORDER BY id")]
        self.conn.execute("DROP TABLE shortcut")
        self.conn.execute(SHORTCUT_DDL)
        for r in rows:
            self.conn.execute(
                "INSERT INTO shortcut (id, api_url, shortcut, is_active,"
                " created_at) VALUES (?, ?, ?, ?, ?)",
                (r["id"], r["api_url"], r["shortcut"],
                 r["is_active"], r["created_at"]))
        self.conn.commit()

    def _migrate_rename_tables(self):
        """遷移（幂等）：5 張表改名（2026-10-24，用戶要求）

            question_flow    -> flow
            question_run     -> run
            question_step    -> step
            question_answer  -> answer
            taxonomy_question -> taxonomy
        一定要喺其他遷移之前跑（佢哋全部引用新名）。
        """
        renames = {
            "question_flow": "flow",
            "question_run": "run",
            "question_step": "step",
            "question_answer": "result",
            "taxonomy_question": "taxonomy",
        }
        for old, new in renames.items():
            has_old = self.conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                (old,)).fetchone()
            if not has_old:
                continue
            has_new = self.conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                (new,)).fetchone()
            if has_new:
                # 兩者都有（新表 = CREATE IF NOT EXISTS 建立嘅空表）
                # -> 新表 drop 咗先，先可以 RENAME（保留舊表資料）
                self.conn.execute(f'DROP TABLE "{new}"')
                self.conn.commit()
            self.conn.execute(f'ALTER TABLE "{old}" RENAME TO "{new}"')
            self.conn.commit()
        # 欄位同步（RENAME 只改表名，欄位名要各自遷移）
        # answer 執行記錄 -> result 由 _migrate_result 全權處理（唔喺呢度郁）
        # taxonomy.question_flow_id -> flow_id
        tcols = [c[1] for c in self.conn.execute(
            "PRAGMA table_info('taxonomy')")]
        if "question_flow_id" in tcols and "flow_id" not in tcols:
            self.conn.execute(
                "ALTER TABLE taxonomy RENAME COLUMN question_flow_id TO flow_id")
            self.conn.commit()

    def _migrate_result(self):
        """遷移（幂等）：舊 answer（執行記錄）-> result + 字典 answer 表

        2026-10-24（用戶要求）：
            - 執行記錄表 answer 改名 result
            - result.answer 欄   -> answer_id（指新 answer 字典：1=真 0=假）
            - result.is_pass     -> status_id（1=>approved, 0=>rejected）
            - 新 answer 表 = 字典（value: 1, 0）

        步驟：
            1. 如果有舊 answer（含 run_id 欄）-> rename result + 轉換
            2. 建新 answer 字典表 + seed 1/0
            幂等：冇舊執行記錄表 -> 跳過。
        """
        acols = [c[1] for c in self.conn.execute(
            "PRAGMA table_info('answer')")]
        # 舊執行記錄表特徵 = 有 run_id 欄
        if acols and "run_id" in acols and "question_id" in acols:
            rows = [dict(r) for r in self.conn.execute(
                "SELECT * FROM answer ORDER BY id")]
            self.conn.execute("DROP TABLE answer")
            self.conn.execute(ANSWER_DICT_DDL)  # 新字典表
            self.conn.execute(RESULT_DDL)
            # answer 字典 seed（1 / 0）
            for v, d in (("1", "真/有"), ("0", "假/冇")):
                self.conn.execute(
                    "INSERT INTO answer (value, description)"
                    " SELECT ?, ? WHERE NOT EXISTS"
                    " (SELECT 1 FROM answer WHERE value = ?)", (v, d, v))
            self.conn.commit()
            for r in rows:
                # answer 值 -> answer 字典 id（1='1'真, 2='0'假）
                raw = r.get("answer")
                if raw is None:
                    aid = None
                else:
                    s = str(raw).strip().lower()
                    aid = 1 if s in ("true", "1", "2", "3") else 2
                # is_pass -> status_id（1=approved 2=rejected）
                sid = 1 if r.get("is_pass") else 2
                self.conn.execute(
                    "INSERT INTO result"
                    " (id, run_id, question_id, answer_id, status_id,"
                    "  created_at)"
                    " VALUES (?, ?, ?, ?, ?, ?)",
                    (r["id"], r["run_id"], r["question_id"], aid, sid,
                     r.get("created_at")))
            self.conn.commit()
        # repair（幂等）：answer_id=0 舊錯值 -> 2（字典 id，1='1' 2='0'）
        self.conn.execute(
            "UPDATE result SET answer_id = 2 WHERE answer_id = 0")
        self.conn.commit()

    def _migrate_question_columns(self):
        """遷移（幂等）：question 表重排欄位 + w5h2_id->"5w2h_id" + 加 updated_at

        2026-10-24（用戶要求）：
            欄位順序：id | test_id | "5w2h_id" | operator_id | expected_id
                      | is_active | created_at | updated_at
        SQLite 唔可以改欄位順序 -> rebuild（保留資料 + id）。
        2026-10-24：calculation_id 欄同時改名 operator_id（QUESTION_DDL 已新名）。
        """
        cols = [c[1] for c in self.conn.execute(
            "PRAGMA table_info('question')")]
        if cols and cols[:3] == ["id", "test_id", "w5h2_id"]:
            rows = [dict(r) for r in self.conn.execute(
                "SELECT * FROM question ORDER BY id")]
            self.conn.execute("DROP TABLE question")
            self.conn.execute(QUESTION_DDL)
            for r in rows:
                self.conn.execute(
                    "INSERT INTO question"
                    " (id, test_id, \"5w2h_id\", operator_id,"
                    "  expected_id, is_active, created_at, updated_at)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (r["id"], r["test_id"], r["w5h2_id"],
                     r.get("operator_id") or r.get("calculation_id"),
                     r.get("expected_id"),
                     r.get("is_active", 1), r.get("created_at"),
                     r.get("updated_at") or r.get("created_at")))
            self.conn.commit()

    def _migrate_step_seq(self):
        """遷移（幂等）：step.seq -> step.seq_id（指去 seq 表）

        2026-10-24（用戶要求）：
            新增 seq 表（id | seq 1..10），step.seq 改 seq_id。
        由於 UNIQUE(flow_id, seq) 引用 seq 欄，DROP COLUMN 唔得
        （SQLite 唔肯刪 constraint 引用欄）-> rebuild 表。
        幂等：第二次跑（冇 seq 欄）-> 跳過。
        """
        scols = [c[1] for c in self.conn.execute(
            "PRAGMA table_info('step')")]
        if "seq" not in scols:
            return
        # 1. seed seq 字典 1..10
        for n in DEFAULT_SEQS:
            self.conn.execute(
                "INSERT INTO seq (seq) SELECT ? WHERE NOT EXISTS"
                " (SELECT 1 FROM seq WHERE seq = ?)", (n, n))
        self.conn.commit()
        # 2. 攞舊資料（id, flow_id, seq, question_id, ...）
        rows = [dict(r) for r in self.conn.execute(
            "SELECT * FROM step ORDER BY id")]
        # 3. rebuild step（seq_id 欄）
        self.conn.execute("DROP TABLE step")
        self.conn.execute(STEP_DDL)
        for r in rows:
            sq = self.conn.execute(
                "SELECT id FROM seq WHERE seq = ?", (r["seq"],)).fetchone()
            seq_id = sq["id"] if sq else None
            self.conn.execute(
                "INSERT INTO step"
                " (id, flow_id, seq_id, question_id, is_active, created_at)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (r["id"], r["flow_id"], seq_id, r["question_id"],
                 r["is_active"], r["created_at"]))
        self.conn.commit()

    def _migrate_step_columns(self):
        """遷移（幂等）：step 欄位重排 + 加 updated_at

        2026-10-24b（用戶要求）：
            排序：id | flow_id | question_id | seq_id | is_active
                  | created_at | updated_at
        SQLite 唔可以改欄位順序 -> rebuild（保留資料 + id）。
        """
        cols = [c[1] for c in self.conn.execute(
            "PRAGMA table_info('step')")]
        if cols and cols[:4] == ["id", "flow_id", "seq_id", "question_id"]:
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

    def _migrate_taxonomy_flow(self):
        """遷移（幂等）：taxonomy.question_flow_id -> flow_id

        2026-10-24（用戶要求）：表改名 taxonomy_question -> taxonomy，
        欄位 question_flow_id 同步改 flow_id（一致）。
        """
        cols = [c[1] for c in self.conn.execute(
            "PRAGMA table_info('taxonomy')")]
        if "question_flow_id" in cols and "flow_id" not in cols:
            self.conn.execute(
                "ALTER TABLE taxonomy"
                " RENAME COLUMN question_flow_id TO flow_id")
            self.conn.commit()

    def _migrate_linear_flow(self):
        """遷移（幂等）：step 分支導航 -> 線性 + run.step_id

        2026-10-24（用戶要求）：
            - step 刪 pass_next_id / fail_next_id / pass_status_id /
              fail_status_id（唔再存導航 + status）
            - run 刪 ended_at，加 step_id（停喺邊步）

        步驟：
            1. step 有 4 分支欄位 -> rebuild（保留 id 同資料）
            2. run 有 ended_at -> rebuild（ended_at=seq -> step_id）
            幂等：第二次跑（冇分支欄位）-> 跳過。
        """
        scols = [c[1] for c in self.conn.execute(
            "PRAGMA table_info('step')")]
        if any(c in scols for c in ("pass_next_id", "fail_next_id",
                                    "pass_status_id", "fail_status_id")):
            rows = [dict(r) for r in self.conn.execute(
                "SELECT * FROM step ORDER BY id")]
            self.conn.execute("DROP TABLE step")
            self.conn.execute(STEP_DDL)
            for r in rows:
                self.conn.execute(
                    "INSERT INTO step"
                    " (id, flow_id, seq, question_id, is_active, created_at)"
                    " VALUES (?, ?, ?, ?, ?, ?)",
                    (r["id"], r["flow_id"], r["seq"], r["question_id"],
                     r["is_active"], r["created_at"]))
            self.conn.commit()
        rcols = [c[1] for c in self.conn.execute(
            "PRAGMA table_info('run')")]
        if "ended_at" in rcols:
            rows = [dict(r) for r in self.conn.execute(
                "SELECT * FROM run ORDER BY id")]
            # ended_at（seq）-> 搵對應 step_id
            for r in rows:
                sid = None
                if r.get("ended_at") is not None and r.get("flow_id"):
                    row = self.conn.execute(
                        "SELECT id FROM step"
                        " WHERE flow_id = ? AND seq = ?",
                        (r["flow_id"], r["ended_at"])).fetchone()
                    sid = row["id"] if row else None
                r["step_id"] = sid
            self.conn.execute("DROP TABLE run")
            self.conn.execute(RUN_DDL)
            for r in rows:
                self.conn.execute(
                    "INSERT INTO run"
                    " (id, flow_id, value_id, step_id, status_id,"
                    "  is_active, created_at)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (r["id"], r["flow_id"], r.get("value_id"), r["step_id"],
                     r.get("status_id"), r.get("is_active", 1),
                     r.get("created_at")))
            self.conn.commit()
        elif "step_id" not in [c[1] for c in self.conn.execute(
                "PRAGMA table_info('run')")]:
            self.conn.execute(
                "ALTER TABLE run ADD COLUMN step_id INTEGER")
            self.conn.commit()

    def _migrate_test_symbol(self):
        """遷移（幂等）：test 'with symbol' -> 'symbol'

        2026-10-23f（用戶要求）：`with symbol` 改名做 `symbol`。
        seed 名單已改做 `symbol` —— 如果唔收斂舊名，每次開連線
        都會 seed 多一行 `symbol`（id 跳號），rename 永遠撞名。

        邏輯：
            - DB 有 `with symbol` 而冇 `symbol` -> 直接改名（id 保留）
            - 兩者都有 -> 刪舊名，question.test_id 改指新名（引用安全）
            - 冇 `with symbol` -> 唔做（幂等）
        """
        old = self.conn.execute(
            "SELECT id FROM test WHERE meta = 'with symbol'").fetchone()
        if not old:
            return
        new = self.conn.execute(
            "SELECT id FROM test WHERE meta = 'symbol' AND id != ?",
            (old["id"],)).fetchone()
        if new:
            # 兩者都有 -> 保留新名（id=10 之後），引用改指新名
            self.conn.execute(
                "UPDATE question SET test_id = ? WHERE test_id = ?",
                (new["id"], old["id"]))
            self.conn.execute(
                "DELETE FROM test WHERE id = ?", (old["id"],))
            self.conn.commit()
        else:
            # 得舊名 -> 直接改名（id=8 保留，引用唔使改）
            self.conn.execute(
                "UPDATE test SET meta = 'symbol' WHERE id = ?",
                (old["id"],))
            self.conn.commit()

    def _migrate_expected_split(self):
        """拆表遷移（冪等）：operator 同期望值分家

        2026-10-23c（用戶要求）：
            expected 移除 meta / expression -> 只做「期望值字典」
            calculation 加返 expression        -> 做「operator 字典」
            question 加 calculation_id         -> 指去 operator

        步驟：
            1. calculation 補 expression 欄 + 由舊 expected.meta 回填
            2. question 補 operator_id 欄
            3. question.expected_id（舊 = operator id）-> operator_id
            4. rebuild expected（只留 pass_value + description），
               pass_value = 舊 expected.pass_value（識別用 id 保留）
            5. question.expected_id 指去「有值嘅 expected 列」；
               冇值 -> NULL

        幂等：第二次跑（expected 已經冇 meta 欄）-> 全部跳過。
        """
        ecols = [c[1] for c in self.conn.execute(
            "PRAGMA table_info('expected')")]
        if "meta" not in ecols:
            return  # 已經係新 shape

        # 1. calculation 補 expression（由舊 expected.meta 回填）
        #    （2026-10-24：表已改名 operator，用新名）
        ccols = [c[1] for c in self.conn.execute(
            "PRAGMA table_info('operator')")]
        if "expression" not in ccols:
            self.conn.execute(
                "ALTER TABLE operator ADD COLUMN expression TEXT")
        self.conn.execute(
            "UPDATE operator SET expression = ("
            "  SELECT e.expression FROM expected e WHERE e.meta = operator.meta)"
            " WHERE expression IS NULL")
        self.conn.commit()

        # 2. question 補 operator_id
        qcols = [c[1] for c in self.conn.execute(
            "PRAGMA table_info('question')")]
        if "operator_id" not in qcols:
            if "calculation_id" in qcols:
                # 舊欄位名 -> 改名（保留資料）
                self.conn.execute(
                    "ALTER TABLE question RENAME COLUMN calculation_id"
                    " TO operator_id")
            else:
                self.conn.execute(
                    "ALTER TABLE question ADD COLUMN operator_id INTEGER")
            self.conn.commit()

        # 3. 舊 question.expected_id（= operator id）-> operator_id
        #    （先記住舊 expected 嘅 id -> meta，再查同名 operator id）
        old_ops = {r["id"]: r["meta"] for r in self.conn.execute(
            "SELECT id, meta FROM expected")}
        calc_by_meta = {r["meta"]: r["id"] for r in self.conn.execute(
            "SELECT id, meta FROM operator")}
        for qid, old_eid in self.conn.execute(
                "SELECT id, expected_id FROM question").fetchall():
            meta = old_ops.get(old_eid)
            cid = calc_by_meta.get(meta) if meta else None
            if cid:
                self.conn.execute(
                    "UPDATE question SET operator_id = ? WHERE id = ?",
                    (cid, qid))
        self.conn.commit()

        # 4. rebuild expected -> 只留 pass_value + description
        #    （meta 有 UNIQUE -> SQLite 唔准 DROP COLUMN，一定要 rebuild）
        rows = self.conn.execute(
            "SELECT id, pass_value, description, is_active, created_at"
            " FROM expected ORDER BY id").fetchall()
        self.conn.execute("DROP TABLE expected")
        self.conn.execute(EXPECTED_DDL)
        self.conn.commit()
        for r in rows:
            self.conn.execute(
                "INSERT INTO expected (id, boolean_id, description,"
                " is_active, created_at) VALUES (?, ?, ?, ?, ?)",
                (r["id"], r["pass_value"], r["description"],
                 r["is_active"], r["created_at"]))
        self.conn.commit()

        # 5. question.expected_id 重新指向「有值嘅 expected 列」
        #    舊 id 保留 -> 直接同 id 對得上就用；對唔上就 NULL
        valid_ids = {r["id"] for r in self.conn.execute(
            "SELECT id FROM expected")}
        self.conn.execute(
            "UPDATE question SET expected_id = NULL"
            " WHERE expected_id IS NOT NULL AND expected_id NOT IN"
            f" ({','.join(str(i) for i in valid_ids) or 'NULL'})")
        self.conn.commit()

    def _migrate(self):
        """舊版 -> 新版遷移

        1. 舊 question_flow（內嵌分支）-> 新 question_flow + question_step（分支拆表）
        2. question_run.result -> status_id（由 result 字串轉 status.id）
        3. question_run 加 test_id
        4. 移除 recommend / recommend_map / mission_question 表
        5. judge 表 -> pass 表 -> expected 表（改名，保留資料）
        6. question.judge_op_id / pass_value -> expected_id（由 expected 表反查）
        7. 刪 question.judge_op_id / question_unit_id / pass_value 舊欄位
        """
        # 0. 確保 expected 有 pass_value（舊版遷移要用）
        ecols0 = [c[1] for c in self.conn.execute("PRAGMA table_info('expected')")]
        if ecols0 and "pass_value" not in ecols0:
            self.conn.execute("ALTER TABLE expected ADD COLUMN pass_value TEXT")
            self.conn.commit()
        # 1. flow 遷移（舊版有 question_id = 內嵌分支 -> 拆 step）
        fcols = [c[1] for c in self.conn.execute("PRAGMA table_info('flow')")]
        if "question_id" in fcols:
            old = [dict(r) for r in self.conn.execute(
                "SELECT * FROM flow")]
            self.conn.execute("DROP TABLE flow")
            self.conn.execute(FLOW_DDL)
            self.conn.execute(STEP_DDL)
            # flow_id 對應（flow_name -> 新 flow id）
            flow_ids = {}
            for r in old:
                if r["flow_name"] not in flow_ids:
                    self.conn.execute(
                        "INSERT OR IGNORE INTO flow (flow_name)"
                        " VALUES (?)", (r["flow_name"],))
                    row = self.conn.execute(
                        "SELECT id FROM flow WHERE flow_name = ?",
                        (r["flow_name"],)).fetchone()
                    flow_ids[r["flow_name"]] = row["id"]
            # 舊 step -> 新 step（分支欄位由 _migrate_linear_flow 處理）
            step_ids = {}  # (flow_name, seq) -> 新 step id
            for r in old:
                fid = flow_ids[r["flow_name"]]
                self.conn.execute(
                    """INSERT OR IGNORE INTO step
                       (flow_id, seq, question_id, is_active, created_at)
                       VALUES (?, ?, ?, ?, ?)""",
                    (fid, r["seq"], r["question_id"], r["is_active"],
                     r["created_at"]))
                row = self.conn.execute(
                    "SELECT id FROM step WHERE flow_id = ? AND seq = ?",
                    (fid, r["seq"])).fetchone()
                step_ids[(r["flow_name"], r["seq"])] = row["id"]
            self.conn.commit()
        # 2. run 遷移（result -> status_id + 加 test_id）
        rcols = [c[1] for c in self.conn.execute("PRAGMA table_info('run')")]
        if "result" in rcols:
            rows = [dict(r) for r in self.conn.execute(
                "SELECT * FROM run")]
            self.conn.execute("DROP TABLE run")
            self.conn.execute(RUN_DDL)
            for r in rows:
                res = r.get("result") or ""
                if res in ("registry", "approved", "pass"):
                    sid = 1
                elif res in ("rejected", "fail"):
                    sid = 2
                else:
                    sid = 3
                fid = None
                if r.get("flow_name"):
                    row = self.conn.execute(
                        "SELECT id FROM flow WHERE flow_name = ?",
                        (r["flow_name"],)).fetchone()
                    fid = row["id"] if row else None
                self.conn.execute(
                    """INSERT OR IGNORE INTO run
                       (flow_id, test_id, status_id, ended_at, is_active, created_at)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (fid, r.get("test_id"), sid, r.get("ended_at"),
                     r.get("is_active", 1), r.get("created_at")))
            self.conn.commit()
        elif "test_id" not in [c[1] for c in self.conn.execute(
                "PRAGMA table_info('run')")]:
            self.conn.execute(
                "ALTER TABLE run ADD COLUMN test_id INTEGER")
            self.conn.commit()
        # 3. 移除舊表（recommend / recommend_map / mission_question）
        for tbl in ("recommend", "recommend_map", "mission_question"):
            has = self.conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                (tbl,)).fetchone()
            if has:
                self.conn.execute(f"DROP TABLE {tbl}")
                self.conn.commit()
        # 4. pass 表 -> expected 表（改名，保留資料）
        has_pass = self.conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='pass'"
        ).fetchone()
        if has_pass:
            # expected 表可能已由 CREATE IF NOT EXISTS 建立（空表）-> 掉咗先改名
            has_exp = self.conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='expected'"
            ).fetchone()
            if has_exp:
                n = self.conn.execute(
                    "SELECT COUNT(*) FROM expected").fetchone()[0]
                ecols = [c[1] for c in self.conn.execute(
                    "PRAGMA table_info('expected')")]
                if n == 0:
                    self.conn.execute("DROP TABLE expected")
                elif "meta" in ecols:
                    # 舊 shape（有 meta/expression）-> 合併
                    self.conn.execute(
                        "INSERT OR IGNORE INTO expected (id, meta, expression, pass_value, description, is_active, created_at)"
                        " SELECT id, meta, expression, pass_value, description, is_active, created_at FROM pass")
                    self.conn.execute("DROP TABLE pass")
                    self.conn.commit()
                    return
                else:
                    # 新 shape（只有 pass_value）-> 只搬期望值
                    self.conn.execute(
                        "INSERT OR IGNORE INTO expected (id, pass_value, description, is_active, created_at)"
                        " SELECT id, pass_value, description, is_active, created_at FROM pass")
                    self.conn.execute("DROP TABLE pass")
                    self.conn.commit()
                    return
            self.conn.execute(
                "ALTER TABLE pass RENAME TO expected")
            self.conn.commit()
        # 5. question.pass_id -> expected_id（改名，保留資料）
        qcols = [c[1] for c in self.conn.execute("PRAGMA table_info('question')")]
        if "pass_id" in qcols and "expected_id" not in qcols:
            self.conn.execute(
                "ALTER TABLE question RENAME COLUMN pass_id TO expected_id")
            self.conn.commit()
        # 5b. 舊 question.pass_value -> expected.pass_value（搬入 expected 表）
        qcols = [c[1] for c in self.conn.execute("PRAGMA table_info('question')")]
        if "pass_value" in qcols:
            rows = self.conn.execute(
                """SELECT q.pass_value, e.id AS eid
                   FROM question q
                   LEFT JOIN expected e ON e.id = q.expected_id
                   WHERE q.pass_value IS NOT NULL AND q.pass_value != ''""").fetchall()
            for r in rows:
                if r["eid"]:
                    self.conn.execute(
                        "UPDATE expected SET pass_value = ? WHERE id = ?",
                        (r["pass_value"], r["eid"]))
            self.conn.commit()
        # 6. 刪舊欄位（judge_op_id / question_unit_id / pass_value）
        qcols = [c[1] for c in self.conn.execute("PRAGMA table_info('question')")]
        for col in ("judge_op_id", "question_unit_id", "pass_value"):
            if col in qcols:
                self.conn.execute(f"ALTER TABLE question DROP COLUMN {col}")
                self.conn.commit()

    def _migrate_run_value(self):
        """遷移（幂等）：run.test_id -> value_id

        2026-10-23d（用戶要求）：
            test_id 係「測試維度」—— 但提交去檢查嘅係一個「值」（submit xxx）。
            新增 value 表（id | value），run.test_id -> value_id。

        步驟：
            1. run 加 value_id 欄
            2. 舊 test_id 值 -> 新 value 表一行（value = test.meta），
               value_id 指向它（保留資料）
            3. 刪 run.test_id

        幂等：第二次跑（冇 test_id 欄）-> 跳過。
        """
        cols = [c[1] for c in self.conn.execute(
            "PRAGMA table_info('run')")]
        if not cols or "test_id" not in cols:
            return
        if "value_id" not in cols:
            self.conn.execute(
                "ALTER TABLE run ADD COLUMN value_id INTEGER")
            self.conn.commit()
        # 舊 test_id -> value 表（用 test.meta 做 value 字串）
        rows = self.conn.execute(
            "SELECT r.id AS run_id, t.meta AS test_meta"
            " FROM run r"
            " LEFT JOIN test t ON t.id = r.test_id"
            " WHERE r.test_id IS NOT NULL").fetchall()
        for r in rows:
            val = r["test_meta"]
            if val is None:
                continue
            vid = self._value_id(val)
            if vid is None:
                self.conn.execute(
                    "INSERT INTO value (value) VALUES (?)", (val,))
                vid = self.conn.execute(
                    "SELECT id FROM value WHERE value = ?", (val,)).fetchone()["id"]
            self.conn.execute(
                "UPDATE run SET value_id = ? WHERE id = ?",
                (vid, r["run_id"]))
        self.conn.commit()
        self.conn.execute(
            "ALTER TABLE run DROP COLUMN test_id")
        self.conn.commit()

    def _seed(self):
        """預設字典（冪等，唔燒 AUTOINCREMENT 號）

        用 `INSERT ... WHERE NOT EXISTS` 而唔係 `INSERT OR IGNORE`：
        實測（2026-10-23）`INSERT OR IGNORE` 撞 UNIQUE 衝突時
        **仍然會遞增 sqlite_sequence** -> 每次開連線都燒 24 個號
        （test 8 + 5W2H 7 + status 3 + calculation 6），令 id 由 9 跳到 57。
        `WHERE NOT EXISTS` 撞時完全唔寫入 -> 唔燒號。
        """
        for meta in DEFAULT_TESTS:
            self.conn.execute(
                "INSERT INTO test (meta) SELECT ? WHERE NOT EXISTS"
                " (SELECT 1 FROM test WHERE meta = ?)", (meta, meta))
        for meta in DEFAULT_W5H2:
            self.conn.execute(
                'INSERT INTO "5W2H" (meta) SELECT ? WHERE NOT EXISTS'
                ' (SELECT 1 FROM "5W2H" WHERE meta = ?)', (meta, meta))
        for meta in DEFAULT_STATUS:
            bid = 1 if meta == "approved" else 0
            # 2026-10-24t：status 欄已刪，用 boolean_id 查重 + 寫入
            self.conn.execute(
                "INSERT INTO status (boolean_id) SELECT ?"
                " WHERE NOT EXISTS"
                " (SELECT 1 FROM status WHERE boolean_id = ?)", (bid, bid))
            # 已存在 -> 補 boolean_id（舊行遷移，冪等）
            self.conn.execute(
                "UPDATE status SET boolean_id = ? WHERE boolean_id IS NULL",
                (bid,))
        for fn in DEFAULT_FLOWS:
            self.conn.execute(
                "INSERT INTO flow (flow_name) SELECT ? WHERE NOT EXISTS"
                " (SELECT 1 FROM flow WHERE flow_name = ?)", (fn, fn))
        for n in DEFAULT_SEQS:
            self.conn.execute(
                "INSERT INTO seq (seq) SELECT ? WHERE NOT EXISTS"
                " (SELECT 1 FROM seq WHERE seq = ?)", (n, n))
        for url, name in DEFAULT_SHORTCUTS:
            self.conn.execute(
                "INSERT INTO shortcut (api_url, shortcut)"
                " SELECT ?, ? WHERE NOT EXISTS"
                " (SELECT 1 FROM shortcut WHERE api_url = ?"
                "  OR shortcut = ?)",
                (url, name, url, name))
        for meta, expr, desc in DEFAULT_OPERATORS:
            self.conn.execute(
                "INSERT INTO operator (meta, expression, description)"
                " SELECT ?, ?, ? WHERE NOT EXISTS"
                " (SELECT 1 FROM operator WHERE meta = ?)",
                (meta, expr, desc, meta))
            # 已存在 -> 更新 expression（冪等）
            self.conn.execute(
                "UPDATE operator SET expression = ? WHERE meta = ?",
                (expr, meta))
        for val, desc in DEFAULT_EXPECTED_VALUES:
            self.conn.execute(
                "INSERT INTO expected (boolean_id, description)"
                " SELECT ?, ? WHERE NOT EXISTS ("
                "   SELECT 1 FROM expected WHERE boolean_id IS ?)",
                (val, desc, val))
        self._seed_apis()
        self._seed_question_texts()
        self._seed_code_registry()
        self.conn.commit()

    def _seed_question_texts(self):
        """seed 問題文字（question_text 表，DB 控制）

        2026-10-24h（用戶要求）：code 升級 —— 問題文字唔再淨係
        code dict，搬入 question_text 表（test_id × w5w2h_id）。
        dict 淨係 fallback（首次 seed 用），改文字 = 改表。
        """
        # test meta -> id
        tid = {}
        for r in self.conn.execute("SELECT id, meta FROM test"):
            tid[r["meta"]] = r["id"]
        wid = {}
        for r in self.conn.execute('SELECT id, meta FROM "5W2H"'):
            wid[r["meta"]] = r["id"]
        for tmeta, txt in self.TEST_QUESTION_TEXT.items():
            for wmeta, ask in self.W5W2H_QUESTION_TEXT.items():
                if tmeta not in tid or wmeta not in wid:
                    continue
                full = txt  # 純文字（question_text 唔連 w5w2h，格式化喺 _question_text）
                self.conn.execute(
                    "INSERT INTO question_text (test_id, w5w2h_id, text)"
                    " SELECT ?, ?, ? WHERE NOT EXISTS"
                    " (SELECT 1 FROM question_text"
                    "  WHERE test_id = ? AND w5w2h_id = ?)",
                    (tid[tmeta], wid[wmeta], full,
                     tid[tmeta], wid[wmeta]))
                # 舊完整文字 -> 收斂成純文字（冪等）
                self.conn.execute(
                    "UPDATE question_text SET text = ?"
                    " WHERE test_id = ? AND w5w2h_id = ? AND text != ?",
                    (full, tid[tmeta], wid[wmeta], full))
        # w5w2h 問法都落表（what -> 係咩？）
        for wmeta, ask in self.W5W2H_QUESTION_TEXT.items():
            if wmeta not in wid:
                continue
            self.conn.execute(
                "INSERT INTO w5w2h_text (w5w2h_id, text)"
                " SELECT ?, ? WHERE NOT EXISTS"
                " (SELECT 1 FROM w5w2h_text WHERE w5w2h_id = ?)",
                (wid[wmeta], ask, wid[wmeta]))
            self.conn.execute(
                "UPDATE w5w2h_text SET text = ? WHERE w5w2h_id = ?",
                (ask, wid[wmeta]))
        self.conn.commit()

    def _seed_apis(self):
        """seed 對外 API 註冊（api_type + api 表）

        2026-10-24（用戶要求）：module 之間點樣 work together 要有表管理。
        question module 對外開放嘅 REST API 全部註冊喺呢度（DB 控制），
        包括 shortcut 路由（/run /english /spec -> flow_by_shortcut）。
        flow_id 填返對應 flow（5w2h / english word / industry spec）。
        """
        # api_type（GET / POST）
        for t, desc in (("GET", "讀取"), ("POST", "寫入"),
                        ("PUT", "更新"), ("DELETE", "刪除")):
            self.conn.execute(
                "INSERT INTO api_type (value, description)"
                " SELECT ?, ? WHERE NOT EXISTS"
                " (SELECT 1 FROM api_type WHERE value = ?)",
                (t, desc, t))
        # 攞 flow id（flow_by_shortcut 用）
        flow_ids = {}
        for r in self.conn.execute("SELECT id, flow_name FROM flow"):
            flow_ids[r["flow_name"]] = r["id"]
        # api 註冊（path, type, flow_name, 描述）
        apis = [
            ("/health", "GET", None, "健康檢查"),
            ("/run", "GET", "5w2h", "提交一個值，行 5w2h flow"),
            ("/run/5w2h", "GET", "5w2h", "提交一個值，行 5w2h flow"),
            ("/run/english-word", "GET", "english word", "行 english word flow"),
            ("/run/industry-spec", "GET", "industry spec", "行 industry spec flow"),
            ("/english", "GET", "english word", "短名 alias：english word flow"),
            ("/spec", "GET", "industry spec", "短名 alias：industry spec flow"),
            ("/runs", "GET", None, "最近執行記錄"),
            ("/flow", "GET", None, "列出全部 flow"),
            ("/questions", "GET", None, "問題列表"),
            ("/expecteds", "GET", None, "期望值字典"),
            ("/values", "GET", None, "value 表"),
            ("/tests", "GET", None, "測試維度"),
            ("/shortcuts", "GET", None, "API 快捷路由"),
            ("/dictionaries", "GET", None, "字典總覽（source 資產）"),
            ("/apis", "GET", None, "本 module 對外 API 註冊"),
            ("/codes", "GET", None, "code_registry / flow / 字典定義"),
            ("/skills", "GET", None, "module 能力（skill）"),
            ("/modules", "GET", None, "所有 module 能力總覽"),
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

    @staticmethod
    def _find_parent(tree, node):
        """搵 node 嘅「最近 FunctionDef/ClassDef 祖先」

        ast 冇 parent pointer，一次過 build parent map：
        walk 落去，任何 child node 記低 parent（包括 If/For/With...），
        再沿 parent 鏈搵最近 def/class。呢個先 handle `_b` 呢種
        喺 If block 內嘅 nested function（直接 parent 係 If）。
        """
        from common import stdlib_ast
        _a = stdlib_ast()
        parent_map = {}
        stack = [tree]
        while stack:
            cur = stack.pop()
            for child in _a.iter_child_nodes(cur):
                parent_map[id(child)] = cur
                stack.append(child)
        cur = node
        while cur is not None:
            p = parent_map.get(id(cur))
            if isinstance(p, (_a.ClassDef, _a.FunctionDef,
                              _a.AsyncFunctionDef)):
                return p
            cur = p
        return None

    def _seed_code_registry(self):
        """seed code_type + code_condition + code_registry（module 檔案 + 所有單行）

        2026-10-24（用戶要求）：question module 8 檔註冊。
        2026-10-24b（用戶要求）：可擴展到所有單行（ast 掃描）。
        2026-10-24c（用戶要求）：condition 獨立成表（code_condition），
        code_registry 用 condition_id 管理（同 code_type_id 一樣 pattern）。

        mapping_line = class/def 真行號（ast 攞，唔靠估）。
        """
        # code_type（用戶指定清單 + 可擴展）
        # 2026-10-24d（用戶要求）：加 migration / seed / api_route
        # 2026-10-24f（用戶要求）：if/else 都註冊 -> 加 logic
        types = [
            "preflight", "schema", "mission", "proof", "verify",
            "evidence", "formula", "filling", "output", "fallback",
            "NA", "identity", "audit", "function", "class",
            "migration", "seed", "api_route", "logic",
        ]
        for t in types:
            self.conn.execute(
                "INSERT INTO code_type (value) SELECT ? WHERE NOT EXISTS"
                " (SELECT 1 FROM code_type WHERE value = ?)", (t, t))
        # code_condition（file / def / class / async def / main / method /
        # helper / nested / if / else）—— 2026-10-24d/f 可擴展
        for c in ("file", "def", "class", "async def", "main",
                  "method", "helper", "nested", "if", "else"):
            self.conn.execute(
                "INSERT INTO code_condition (value) SELECT ? WHERE NOT EXISTS"
                " (SELECT 1 FROM code_condition WHERE value = ?)", (c, c))
        # 確保 code_registry 係新版（有 condition_id）
        cols = [c[1] for c in self.conn.execute(
            "PRAGMA table_info('code_registry')")]
        if "condition" in cols:
            self.conn.execute("DROP TABLE code_registry")
            self.conn.execute(CODE_REGISTRY_DDL)
            self.conn.commit()
        # 唔 DELETE（2026-10-24f 用戶要求：唔好重建）——
        # upsert 只加新行 + 更新已存在，id 全部保留
        # 逐個檔案 ast 掃描（全部 .py，唔係白名單）
        from common import stdlib_ast
        _ast = stdlib_ast()
        import os as _os
        fname_type = {
            "schema.py": "schema", "sql.py": "schema", "api.py": "identity",
            "api_server.py": "output",
            "function.py": "proof", "route.py": "preflight",
            "__init__.py": "mission", "skill.py": "formula",
        }
        mod_dir = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)))
        for fname in sorted(_os.listdir(mod_dir)):
            if not fname.endswith(".py"):
                continue
            fpath = _os.path.join(mod_dir, fname)
            try:
                with open(fpath, encoding="utf-8") as f:
                    tree = _ast.parse(f.read(), filename=fname)
            except Exception:
                # 讀唔到 / syntax error -> 都註冊一行（condition=file, type=NA）
                # 等審計知道呢個檔案「有問題」，唔係唔存在
                na = self.conn.execute(
                    "SELECT id FROM code_type WHERE value = 'NA'").fetchone()
                if na:
                    self._upsert_code_reg(
                        na["id"], fname, fname, "唔可以 parse", 1, "file")
                continue  # 唔可以註冊嘅檔案 skip
            ctype = fname_type.get(fname, "NA")
            tr = self.conn.execute(
                "SELECT id FROM code_type WHERE value = ?", (ctype,)).fetchone()
            file_tid = tr["id"] if tr else None
            # 檔案本身一行（line 1）
            if file_tid:
                self._upsert_code_reg(file_tid, fname, fname,
                                      "module 檔案", 1, "file")
            # 每個 top-level def / class 一行（ast.walk：連 class 內 method 都計）
            for node in _ast.walk(tree):
                # if / else 節點都註冊（2026-10-24f 用戶要求）
                if isinstance(node, _ast.If):
                    # If 本身一行
                    ltr = self.conn.execute(
                        "SELECT id FROM code_type WHERE value = 'logic'").fetchone()
                    if ltr:
                        meta = "if:" + _ast.unparse(node.test)[:40]
                        self._upsert_code_reg(
                            ltr["id"], fname, meta, "if 條件",
                            node.lineno, "if")
                    # else（orelse 非空 = 有 else 分支）
                    if node.orelse:
                        self._upsert_code_reg(
                            ltr["id"], fname, f"else:{fname}:{node.lineno}",
                            "else 分支", node.lineno, "else")
                    continue
                if isinstance(node, _ast.FunctionDef):
                    kind, ct = "def", "function"
                elif isinstance(node, _ast.AsyncFunctionDef):
                    kind, ct = "async def", "function"
                elif isinstance(node, _ast.ClassDef):
                    kind, ct = "class", "class"
                else:
                    continue
                # 判斷 condition：class 內 = method，函數內 = nested
                cond = kind  # def / class / async def
                parent = self._find_parent(tree, node)
                if isinstance(parent, _ast.ClassDef):
                    cond = "method" if kind != "class" else "class"
                elif isinstance(parent, (_ast.FunctionDef,
                                         _ast.AsyncFunctionDef)):
                    cond = "nested"
                # code_type：名稱分類（更細定義）
                name = node.name
                if isinstance(node, _ast.ClassDef):
                    ct2 = "class"
                elif name.startswith("_migrate"):
                    ct2 = "migration"
                elif name.startswith("_seed") or name == "_seed":
                    ct2 = "seed"
                elif name.startswith(("do_", "handle_")) or name in (
                        "_send", "_read_body", "_path_parts", "_qs"):
                    ct2 = "api_route"
                elif name.startswith("_") :
                    ct2 = "helper" if cond == "nested" else "function"
                else:
                    ct2 = "function"
                # helper condition 覆蓋 nested（helper 係 nested function）
                if cond == "nested" and ct2 == "function":
                    ct2 = "helper"
                ctr = self.conn.execute(
                    "SELECT id FROM code_type WHERE value = ?", (ct2,)).fetchone()
                if not ctr:
                    ctr = self.conn.execute(
                        "SELECT id FROM code_type WHERE value = 'function'").fetchone()
                if not ctr:
                    continue
                desc = node.name
                self._upsert_code_reg(
                    ctr["id"], fname, node.name, desc, node.lineno, cond)
        # ---- code_flow + code_step（檔案 = flow，函數 = step，按行號排） ----
        self._seed_code_flow_steps()
        self.conn.commit()

    def _seed_code_flow_steps(self):
        """seed code_flow + code_step（定義更清晰）

        2026-10-24e（用戶要求）：code_flow（檔案）+ code_step（函數）
        —— 每個 .py 檔案一條 flow，flow 嘅 step = 檔案內所有函數
        （按 mapping_line 順序 = 執行順序）。
        seq 由 seq 表攞（1,2,3...），每 flow 從 1 開始。
        """
        # 每個檔案 = 一條 flow
        files = [r["filename"] for r in self.conn.execute(
            "SELECT DISTINCT filename FROM code_registry"
            " ORDER BY filename")]
        for fname in files:
            self.conn.execute(
                "INSERT INTO code_flow (flow_name, description)"
                " SELECT ?, ? WHERE NOT EXISTS"
                " (SELECT 1 FROM code_flow WHERE flow_name = ?)",
                (fname, f"{fname} 執行流程", fname))
            fr = self.conn.execute(
                "SELECT id FROM code_flow WHERE flow_name = ?",
                (fname,)).fetchone()
            fid = fr["id"]
            # code_registry 分行（file 行唔當 step —— 淨係 def/class/async def）
            rows = self.conn.execute(
                """SELECT cr.id, cr.mapping_line
                   FROM code_registry cr
                   JOIN code_condition cc ON cc.id = cr.condition_id
                   WHERE cr.filename = ? AND cc.value != 'file'
                   ORDER BY cr.mapping_line""", (fname,)).fetchall()
            # 唔 DELETE（2026-10-24f 用戶要求：唔好重建）
            # 只補「未有 step 嘅 registry 行」—— 已存在嘅 step 保留
            existing = {r["code_registry_id"] for r in self.conn.execute(
                "SELECT code_registry_id FROM code_step WHERE code_flow_id = ?",
                (fid,))}
            new_rows = [r for r in rows if r["id"] not in existing]
            # 確保 seq 表有足夠數值（1..N，唔止 10）
            for n in range(1, len(rows) + 1):
                self.conn.execute(
                    "INSERT INTO seq (seq) SELECT ? WHERE NOT EXISTS"
                    " (SELECT 1 FROM seq WHERE seq = ?)", (n, n))
            # 下一步 seq = 現有最大 + 1
            m = self.conn.execute(
                "SELECT MAX(seq_id) FROM code_step WHERE code_flow_id = ?",
                (fid,)).fetchone()[0] or 0
            for r in new_rows:
                m += 1
                sq = self.conn.execute(
                    "SELECT id FROM seq WHERE seq = ?", (m,)).fetchone()
                if not sq:
                    continue
                self.conn.execute(
                    "INSERT OR IGNORE INTO code_step"
                    " (code_flow_id, code_registry_id, seq_id)"
                    " VALUES (?, ?, ?)", (fid, r["id"], sq["id"]))
        self._seed_value_defne()
        self.conn.commit()

    def _seed_value_defne(self):
        """seed 字典定義（value_defne + unique_defne）

        2026-10-24f（用戶要求）：唔好 array 喺 code ——
        所有「值」入 value_defne（id | value），配對入 unique_defne
        （value = 'left_id=right_id'）。
        2026-10-24g（用戶要求）：變量名=值（aaa=123）都入 value_defne ——
        ast 掃描 Assign node，`name=value` 註冊成 value_defne 一行。

        value_defne 內容：
            code_type 名 / code_condition 名 / 變量=值（aaa=123）
        unique_defne 內容：
            code_type_id=condition_id 配對，例如 '3=2'（function + def）
        """
        # 1. code_type + code_condition 嘅 value -> value_defne
        for tbl, col in (("code_type", "value"), ("code_condition", "value")):
            for r in self.conn.execute(f"SELECT id, {col} AS v FROM {tbl}"):
                self.conn.execute(
                    "INSERT INTO value_defne (value, description)"
                    " SELECT ?, ? WHERE NOT EXISTS"
                    " (SELECT 1 FROM value_defne WHERE value = ?)",
                    (r["v"], f"來自 {tbl}", r["v"]))
        # 2. 配對：code_registry 有幾多種 code_type × condition
        #    （unique_defne.value = '<type_id>=<cond_id>'）
        rows = self.conn.execute(
            """SELECT DISTINCT cr.code_type_id, cr.condition_id
               FROM code_registry cr""").fetchall()
        for r in rows:
            lv = self.conn.execute(
                "SELECT value FROM code_type WHERE id = ?",
                (r["code_type_id"],)).fetchone()
            rv = self.conn.execute(
                "SELECT value FROM code_condition WHERE id = ?",
                (r["condition_id"],)).fetchone()
            if not lv or not rv:
                continue
            # 兩邊都入 value_defne
            for v in (lv["value"], rv["value"]):
                self.conn.execute(
                    "INSERT INTO value_defne (value) SELECT ? WHERE NOT EXISTS"
                    " (SELECT 1 FROM value_defne WHERE value = ?)", (v, v))
            lid = self.conn.execute(
                "SELECT id FROM value_defne WHERE value = ?",
                (lv["value"],)).fetchone()
            rid = self.conn.execute(
                "SELECT id FROM value_defne WHERE value = ?",
                (rv["value"],)).fetchone()
            if not lid or not rid:
                continue
            self.conn.execute(
                "INSERT INTO unique_defne"
                " (value, left_value_id, right_value_id, description)"
                " SELECT ?, ?, ?, ? WHERE NOT EXISTS"
                " (SELECT 1 FROM unique_defne"
                "  WHERE left_value_id = ? AND right_value_id = ?)",
                (f"{lid['id']}={rid['id']}", lid["id"], rid["id"],
                 f"{lv['value']} × {rv['value']} 配對",
                 lid["id"], rid["id"]))
        # 3. 變量 = 值（aaa=123）—— ast 掃描 Assign node（全部 .py）
        from common import stdlib_ast
        _a2 = stdlib_ast()
        import os as _o2
        mod_dir = _o2.path.join(_o2.path.dirname(_o2.path.abspath(__file__)))
        for fname in sorted(_o2.listdir(mod_dir)):
            if not fname.endswith(".py"):
                continue
            fpath = _o2.path.join(mod_dir, fname)
            try:
                with open(fpath, encoding="utf-8") as f:
                    tree = _a2.parse(f.read(), filename=fname)
            except Exception:
                continue
            for node in _a2.walk(tree):
                if not isinstance(node, _a2.Assign):
                    continue
                for target in node.targets:
                    if not isinstance(target, _a2.Name):
                        continue
                    try:
                        val = _a2.literal_eval(node.value)
                    except Exception:
                        val = None
                    if val is None:
                        continue
                    pair = f"{target.id}={val}"
                    self.conn.execute(
                        "INSERT INTO value_defne (value, description)"
                        " SELECT ?, ? WHERE NOT EXISTS"
                        " (SELECT 1 FROM value_defne WHERE value = ?)",
                        (pair, f"{fname}:{node.lineno}", pair))
        self.conn.commit()

    def value_defnes(self, active_only=True):
        """列出字典定義（value_defne）"""
        sql = "SELECT * FROM value_defne"
        if active_only:
            sql += " WHERE is_active = 1"
        sql += " ORDER BY id"
        return [dict(r) for r in self.conn.execute(sql)]

    def unique_defnes(self, active_only=True):
        """列出唯一配對定義（unique_defne，含兩邊 value）"""
        sql = ("SELECT ud.id, ud.value, lv.value AS left_value,"
               " rv.value AS right_value, ud.description, ud.is_active"
               " FROM unique_defne ud"
               " LEFT JOIN value_defne lv ON lv.id = ud.left_value_id"
               " LEFT JOIN value_defne rv ON rv.id = ud.right_value_id")
        if active_only:
            sql += " WHERE ud.is_active = 1"
        sql += " ORDER BY ud.id"
        return [dict(r) for r in self.conn.execute(sql)]

    def code_flows(self, active_only=True):
        """列出 code_flow（含 steps）"""
        flows = []
        sql = "SELECT * FROM code_flow"
        if active_only:
            sql += " WHERE is_active = 1"
        sql += " ORDER BY id"
        for f in self.conn.execute(sql):
            fd = dict(f)
            fd["steps"] = [dict(r) for r in self.conn.execute(
                """SELECT cs.id, cs.seq_id, sq.seq, cr.meta, cr.filename,
                          cr.mapping_line, cc.value AS condition,
                          ct.value AS code_type
                   FROM code_step cs
                   JOIN code_registry cr ON cr.id = cs.code_registry_id
                   LEFT JOIN seq sq ON sq.id = cs.seq_id
                   LEFT JOIN code_condition cc ON cc.id = cr.condition_id
                   LEFT JOIN code_type ct ON ct.id = cr.code_type_id
                   WHERE cs.code_flow_id = ?
                   ORDER BY cs.seq_id""", (fd["id"],))]
            flows.append(fd)
        return flows

    def _condition_id(self, cond):
        """由 condition 名攞 code_condition.id（不存在自動註冊）"""
        self.conn.execute(
            "INSERT INTO code_condition (value) SELECT ? WHERE NOT EXISTS"
            " (SELECT 1 FROM code_condition WHERE value = ?)", (cond, cond))
        r = self.conn.execute(
            "SELECT id FROM code_condition WHERE value = ?", (cond,)).fetchone()
        return r["id"] if r else None

    def _upsert_code_reg(self, code_type_id, filename, meta, desc,
                         line, condition):
        """插入或更新一行 code_registry（冪等：UNIQUE meta+filename+line）

        condition = 條件名（file/def/class）-> 自動轉 condition_id
        """
        cond_id = self._condition_id(condition)
        self.conn.execute(
            "INSERT INTO code_registry"
            " (code_type_id, condition_id, meta, description,"
            "  filename, mapping_line)"
            " SELECT ?, ?, ?, ?, ?, ? WHERE NOT EXISTS"
            " (SELECT 1 FROM code_registry"
            "  WHERE meta = ? AND filename = ? AND mapping_line = ?)",
            (code_type_id, cond_id, meta, desc, filename, line,
             meta, filename, line))
        # 已存在 -> 補 code_type / condition（冪等）
        self.conn.execute(
            "UPDATE code_registry SET code_type_id = ?, condition_id = ?"
            " WHERE meta = ? AND filename = ? AND mapping_line = ?",
            (code_type_id, cond_id, meta, filename, line))

    def code_registries(self, active_only=True):
        """列出 module 檔案註冊（含 code_type 名 + condition 名）"""
        sql = ("SELECT cr.id, ct.value AS code_type,"
               " cc.value AS condition, cr.meta,"
               " cr.description, cr.filename, cr.mapping_line,"
               " cr.is_active, cr.created_at"
               " FROM code_registry cr"
               " LEFT JOIN code_type ct ON ct.id = cr.code_type_id"
               " LEFT JOIN code_condition cc ON cc.id = cr.condition_id")
        if active_only:
            sql += " WHERE cr.is_active = 1"
        sql += " ORDER BY ct.id, cr.meta"
        return [dict(r) for r in self.conn.execute(sql)]

    # ---------- operator（operator 字典：點比，DB 控制） ----------
    def add_operator(self, meta, expression=None, description=None):
        """新增 operator（冪等）

        meta       = operator 名（== / >= / <= / != / > / <）
        expression = 判斷表達式（answer = 答案，pass_value = 期望值）
        """
        self.conn.execute(
            "INSERT INTO operator (meta, expression, description)"
            " SELECT ?, ?, ? WHERE NOT EXISTS"
            " (SELECT 1 FROM operator WHERE meta = ?)",
            (meta, expression, description, meta))
        self.conn.execute(
            "UPDATE operator SET expression = ? WHERE meta = ?",
            (expression, meta))
        self.conn.commit()
        r = self.conn.execute(
            "SELECT id FROM operator WHERE meta = ?", (meta,)).fetchone()
        return r["id"] if r else None

    def operators(self, active_only=True):
        """列出 operator 字典"""
        sql = "SELECT * FROM operator"
        if active_only:
            sql += " WHERE is_active = 1"
        sql += " ORDER BY id"
        return [dict(r) for r in self.conn.execute(sql)]

    def _operator_id(self, meta):
        """由 operator 名攞 operator.id（唔存在返回 None）"""
        r = self.conn.execute(
            "SELECT id FROM operator WHERE meta = ?", (meta,)).fetchone()
        return r["id"] if r else None

    # ---------- expected（期望值字典：比幾多，DB 控制） ----------
    def _bool_value(self, s):
        """字串 -> boolean id（0/1）。'1'/'YES'/'true' -> 1；'0'/'NO'/'false' -> 0"""
        if s is None:
            return None
        v = str(s).strip().lower()
        if v in ("1", "yes", "true"):
            return 1
        if v in ("0", "no", "false"):
            return 0
        return None

    def add_expected(self, pass_value=None, description=None, boolean_id=None):
        """新增期望值（冪等）

        boolean_id = boolean.id（0=假 1=真）—— 2026-10-24t 正式欄位
        pass_value = 舊參數（兼容：'1'/'YES' -> 1，'0'/'NO' -> 0）
        """
        bid = boolean_id if boolean_id is not None else self._bool_value(pass_value)
        # API 層擋垃圾（DB CHECK 之前先有清晰訊息）
        if bid not in (0, 1):
            raise ValueError(
                f"boolean_id 必須係 0 或 1（int），收到：{bid!r}")
        r = self.conn.execute(
            "SELECT id FROM expected WHERE boolean_id IS ?",
            (bid,)).fetchone()
        if r:
            return r["id"]
        self.conn.execute(
            "INSERT INTO expected (boolean_id, description)"
            " VALUES (?, ?)",
            (bid, description))
        self.conn.commit()
        return self.conn.execute(
            "SELECT id FROM expected WHERE boolean_id IS ?",
            (bid,)).fetchone()["id"]

    def set_expected_value(self, expected_id, pass_value=None, boolean_id=None):
        """設定一個期望值列嘅值（DB 控制）"""
        bid = boolean_id if boolean_id is not None else self._bool_value(pass_value)
        if bid not in (0, 1):
            raise ValueError(
                f"boolean_id 必須係 0 或 1（int），收到：{bid!r}")
        self.conn.execute(
            "UPDATE expected SET boolean_id = ? WHERE id = ?",
            (bid, expected_id))
        self.conn.commit()

    def remove_expected(self, expected_id):
        """移除一個期望值列（幂等）

        安全：若有 question 引用該 expected_id -> 拒絕（先清 question）
        返回 True = 真刪到一行
        """
        r = self.conn.execute(
            "SELECT id FROM expected WHERE id = ?", (expected_id,)).fetchone()
        if not r:
            return False
        used = self.conn.execute(
            "SELECT COUNT(*) FROM question WHERE expected_id = ?",
            (expected_id,)).fetchone()[0]
        if used:
            raise ValueError(
                f"expected.id={expected_id} 仍有 {used} 條 question 引用"
                f" — 先清 question 嘅 expected_id（唔准斷引用）")
        self.conn.execute(
            "DELETE FROM expected WHERE id = ?", (expected_id,))
        self.conn.commit()
        return True

    def expecteds(self, active_only=True):
        sql = "SELECT * FROM expected"
        if active_only:
            sql += " WHERE is_active = 1"
        sql += " ORDER BY id"
        return [dict(r) for r in self.conn.execute(sql)]

    def _expected_id(self, pass_value=None, boolean_id=None):
        """由期望值攞 expected.id（唔存在返回 None）

        2026-10-24t：優先用 boolean_id（0/1）查，舊 pass_value 做 fallback
        """
        if boolean_id is not None:
            r = self.conn.execute(
                "SELECT id FROM expected WHERE boolean_id IS ?",
                (boolean_id,)).fetchone()
            if r:
                return r["id"]
        if pass_value is not None:
            r = self.conn.execute(
                "SELECT id FROM expected WHERE pass_value IS ?",
                (pass_value,)).fetchone()
            return r["id"] if r else None
        return None

    # ---------- value（提交值字典：submit xxx 去檢查） ----------
    def add_value(self, value):
        """新增 / 攞一個提交值嘅 id（幂等：同值唔會建兩行）

        value = 提交去檢查嘅值（例如 "Anthropic spec"）
        返回 value.id（INT）
        """
        r = self.conn.execute(
            "SELECT id FROM value WHERE value IS ?", (value,)).fetchone()
        if r:
            return r["id"]
        cur = self.conn.execute(
            "INSERT INTO value (value) VALUES (?)", (value,))
        self.conn.commit()
        return cur.lastrowid

    def values(self, active_only=None):
        """列出全部提交值"""
        return [dict(r) for r in self.conn.execute(
            "SELECT * FROM value ORDER BY id")]

    def _value_id(self, value):
        """由值攞 value.id（唔存在返回 None）"""
        r = self.conn.execute(
            "SELECT id FROM value WHERE value IS ?", (value,)).fetchone()
        return r["id"] if r else None

    # ---------- test ----------
    def add_test(self, meta):
        """新增盲測維度（幂等，唔燒 AUTOINCREMENT 號）

        meta = 維度名（可以係空字串 "" = 空 row；但 UNIQUE 限制只可以一個）
        返回 test.id（INT）或 None
        """
        self.conn.execute(
            "INSERT INTO test (meta) SELECT ? WHERE NOT EXISTS"
            " (SELECT 1 FROM test WHERE meta = ?)", (meta, meta))
        self.conn.commit()
        r = self.conn.execute(
            "SELECT id FROM test WHERE meta = ?", (meta,)).fetchone()
        return r["id"] if r else None

    def remove_test(self, meta):
        """移除一個盲測維度（幂等）

        安全：若有 question 引用該 test_id -> 拒絕（先清 question）
        返回 True = 真刪到一行
        """
        r = self.conn.execute(
            "SELECT id FROM test WHERE meta = ?", (meta,)).fetchone()
        if not r:
            return False
        used = self.conn.execute(
            "SELECT COUNT(*) FROM question WHERE test_id = ?",
            (r["id"],)).fetchone()[0]
        if used:
            raise ValueError(
                f"test {meta!r}（id={r['id']}）仍有 {used} 條 question 引用"
                f" — 先刪 question 或者停用（唔准斷 FK）")
        self.conn.execute("DELETE FROM test WHERE id = ?", (r["id"],))
        self.conn.commit()
        return True

    def rename_test(self, old_meta, new_meta):
        """改名一個盲測維度（幂等）

        安全：
            - 舊名唔存在 -> 返回 False
            - 新名已存在 -> ValueError（唔可以撞名）
            - question.test_id 唔使改（id 唔變，引用自動跟）
        返回 True = 真改到一行
        """
        r = self.conn.execute(
            "SELECT id FROM test WHERE meta = ?", (old_meta,)).fetchone()
        if not r:
            return False
        clash = self.conn.execute(
            "SELECT id FROM test WHERE meta = ? AND id != ?",
            (new_meta, r["id"])).fetchone()
        if clash:
            raise ValueError(
                f"test 名稱撞咗: {new_meta!r}（id={clash['id']}）"
                f" — 唔可以改名做一個已存在嘅名")
        self.conn.execute(
            "UPDATE test SET meta = ? WHERE id = ?", (new_meta, r["id"]))
        self.conn.commit()
        return True

    def tests(self, active_only=True):
        sql = "SELECT * FROM test"
        if active_only:
            sql += " WHERE is_active = 1"
        sql += " ORDER BY id"
        return [dict(r) for r in self.conn.execute(sql)]

    # ---------- 5W2H ----------
    def add_5w2h(self, meta):
        """新增提問框架（幂等，唔燒 AUTOINCREMENT 號）"""
        self.conn.execute(
            'INSERT INTO "5W2H" (meta) SELECT ? WHERE NOT EXISTS'
            ' (SELECT 1 FROM "5W2H" WHERE meta = ?)', (meta, meta))
        self.conn.commit()
        r = self.conn.execute(
            'SELECT id FROM "5W2H" WHERE meta = ?', (meta,)).fetchone()
        return r["id"] if r else None

    def list_5w2h(self, active_only=True):
        sql = 'SELECT * FROM "5W2H"'
        if active_only:
            sql += " WHERE is_active = 1"
        sql += " ORDER BY id"
        return [dict(r) for r in self.conn.execute(sql)]

    # ---------- question ----------
    def add_question(self, test_id, w5h2_id, calc_meta=None, pass_value=None,
                     boolean_id=None):
        """建立一個問題（test × 5W2H 組合 + 判斷條件，冪等）

        calc_meta  = operator 名（== / >= / <= / != / > / <）-> calculation.id
        pass_value = 舊期望值（保留兼容）-> expected.id
        boolean_id = boolean.id（0=假 1=真）—— 2026-10-24t 正式欄位
                     （兩個都唔傳 = 唔判，只記錄問題）
        """
        operator_id = None
        if calc_meta is not None:
            operator_id = self._operator_id(calc_meta)
            if operator_id is None:
                operator_id = self.add_operator(calc_meta)
        expected_id = None
        if pass_value is not None or operator_id is not None or boolean_id is not None:
            expected_id = self._expected_id(pass_value, boolean_id)
            if expected_id is None:
                expected_id = self.add_expected(
                    pass_value, boolean_id=boolean_id)
        self.conn.execute(
            "INSERT INTO question (test_id, \"5w2h_id\", expected_id, operator_id)"
            " SELECT ?, ?, ?, ? WHERE NOT EXISTS"
            " (SELECT 1 FROM question WHERE test_id = ? AND \"5w2h_id\" = ?"
            "  AND expected_id IS ?)",
            (test_id, w5h2_id, expected_id, operator_id,
             test_id, w5h2_id, expected_id))
        # 已存在 -> 更新判斷條件 + updated_at（冪等，只 update 指定 expected 嗰條）
        self.conn.execute(
            "UPDATE question SET operator_id = ?,"
            " updated_at = datetime('now', 'localtime')"
            " WHERE test_id = ? AND \"5w2h_id\" = ? AND expected_id IS ?",
            (operator_id, test_id, w5h2_id, expected_id))
        self.conn.commit()
        r = self.conn.execute(
            "SELECT id FROM question WHERE test_id = ? AND \"5w2h_id\" = ?"
            " AND expected_id IS ?",
            (test_id, w5h2_id, expected_id)).fetchone()
        return r["id"] if r else None

    def set_expected(self, question_id, calc_meta=None, pass_value=None,
                     boolean_id=None):
        """設定一個問題嘅判斷條件（DB 控制，唔係 code）

        calc_meta  = operator 名（必須喺 operator 表存在，唔可以自行發明）
        pass_value = 舊期望值（保留兼容）
        boolean_id = boolean.id（0=假 1=真）—— 2026-10-24t 正式欄位
        """
        operator_id = None
        if calc_meta is not None:
            operator_id = self._operator_id(calc_meta)
            if operator_id is None:
                raise ValueError(
                    f"operator 唔存在於 operator 表: {calc_meta!r}"
                    f"（先 add_operator 註冊，唔可以 blackbox）")
        expected_id = None
        if boolean_id is not None or pass_value is not None:
            expected_id = self._expected_id(pass_value, boolean_id)
            if expected_id is None:
                expected_id = self.add_expected(
                    pass_value, boolean_id=boolean_id)
        self.conn.execute(
            "UPDATE question SET operator_id = ?, expected_id = ?"
            " WHERE id = ?",
            (operator_id, expected_id, question_id))
        self.conn.commit()

    def set_operator(self, question_id, calc_meta):
        """只設定一個問題嘅 operator（唔碰 expected_id）

        calc_meta = operator 名（必須喺 operator 表存在，唔可以自行發明）
        """
        operator_id = self._operator_id(calc_meta)
        if operator_id is None:
            raise ValueError(
                f"operator 唔存在於 operator 表: {calc_meta!r}"
                f"（先 add_operator 註冊，唔可以 blackbox）")
        self.conn.execute(
            "UPDATE question SET operator_id = ? WHERE id = ?",
            (operator_id, question_id))
        self.conn.commit()
        return operator_id

    def set_all_operators(self, calc_meta):
        """將全部問題嘅 operator 設為同一個（只改 operator_id）

        返回 {"calc_meta": str, "operator_id": n, "before": {id: old},
              "affected": n}
        安全：先 snapshot 舊值（回報 + 可審核），再更新，再核對行數。
        """
        operator_id = self._operator_id(calc_meta)
        if operator_id is None:
            raise ValueError(
                f"operator 唔存在於 operator 表: {calc_meta!r}"
                f"（先 add_operator 註冊，唔可以 blackbox）")
        before = {r["id"]: r["operator_id"] for r in self.conn.execute(
            "SELECT id, operator_id FROM question ORDER BY id")}
        total = len(before)
        cur = self.conn.execute(
            "UPDATE question SET operator_id = ?", (operator_id,))
        self.conn.commit()
        after = [dict(r) for r in self.conn.execute(
            "SELECT id, operator_id FROM question"
            " WHERE operator_id IS NOT ?", (operator_id,))]
        return {"calc_meta": calc_meta, "operator_id": operator_id,
                "before": before, "affected": cur.rowcount,
                "total": total, "mismatch": after}

    def set_all_expecteds(self, pass_value=None, boolean_id=None):
        """將全部問題嘅期望值設為同一個（只改 expected_id）

        boolean_id = boolean.id（0=假 1=真）—— 2026-10-24t 正式欄位
        pass_value = 舊期望值（保留兼容）
        返回 {"boolean_id": n, "expected_id": n, "before": {id: old},
              "affected": n}
        安全：先 snapshot 舊值（回報 + 可審核），再更新，再核對行數。
        """
        expected_id = self._expected_id(pass_value, boolean_id)
        if expected_id is None:
            expected_id = self.add_expected(
                pass_value, boolean_id=boolean_id)
        before = {r["id"]: r["expected_id"] for r in self.conn.execute(
            "SELECT id, expected_id FROM question ORDER BY id")}
        total = len(before)
        cur = self.conn.execute(
            "UPDATE question SET expected_id = ?", (expected_id,))
        self.conn.commit()
        after = [dict(r) for r in self.conn.execute(
            "SELECT id, expected_id FROM question"
            " WHERE expected_id IS NOT ?", (expected_id,))]
        return {"pass_value": pass_value, "boolean_id": boolean_id,
                "expected_id": expected_id,
                "before": before, "affected": cur.rowcount,
                "total": total, "mismatch": after}

    def questions(self, active_only=True):
        """列出全部問題（JOIN test + 5W2H + operator + expected 攞名）"""
        sql = """SELECT q.id, q.test_id, t.meta AS test,
                        q."5w2h_id", w.meta AS w5w2h,
                        q.operator_id, cz.meta AS calc_meta,
                        cz.expression AS calc_expression,
                        q.expected_id, e.boolean_id AS expected_boolean_id,
                        q.is_active
                 FROM question q
                 JOIN test t ON t.id = q.test_id
                 JOIN "5W2H" w ON w.id = q."5w2h_id"
                 LEFT JOIN operator cz ON cz.id = q.operator_id
                 LEFT JOIN expected e ON e.id = q.expected_id"""
        if active_only:
            sql += " WHERE q.is_active = 1"
        sql += " ORDER BY q.id"
        rows = [dict(r) for r in self.conn.execute(sql)]
        for r in rows:
            r["question"] = self._question_text(r["test"], r["w5w2h"])
        return rows

    # ---------- taxonomy（module 大類 × flow 關聯） ----------
    def add_taxonomy_question(self, flow_id, tree_id=2):
        """將一個驗證鏈綁定去 module 大類（tree_id=2，幂等）

        flow_id = flow.id（邊條驗證鏈，例如 5w2h）
        tree_id = taxonomy tree.id（=2 module 大類）
        返回 taxonomy.id（INT）
        """
        self.conn.execute(
            "INSERT INTO taxonomy (tree_id, flow_id)"
            " SELECT ?, ? WHERE NOT EXISTS"
            " (SELECT 1 FROM taxonomy"
            "  WHERE tree_id = ? AND flow_id = ?)",
            (tree_id, flow_id, tree_id, flow_id))
        self.conn.commit()
        r = self.conn.execute(
            "SELECT id FROM taxonomy"
            " WHERE tree_id = ? AND flow_id = ?",
            (tree_id, flow_id)).fetchone()
        return r["id"] if r else None

    def taxonomy_questions(self, tree_id=2, active_only=True):
        """列出一個 module 大類嘅全部驗證鏈（JOIN flow + 步驟）"""
        sql = """SELECT m.id AS taxonomy_id, m.tree_id,
                        m.flow_id,
                        f.flow_name, f.is_active AS flow_active,
                        (SELECT COUNT(*) FROM step st
                          WHERE st.flow_id = f.id) AS step_count,
                        m.is_active
                 FROM taxonomy m
                 LEFT JOIN flow f ON f.id = m.flow_id
                 WHERE m.tree_id = ?"""
        if active_only:
            sql += " AND m.is_active = 1"
        sql += " ORDER BY m.id"
        return [dict(r) for r in self.conn.execute(sql, (tree_id,))]

    # ---------- flow（驗證鏈） ----------
    def add_flow(self, flow_name="5w2h"):
        """建立一條驗證鏈（冪等）"""
        self.conn.execute(
            "INSERT INTO flow (flow_name) SELECT ? WHERE NOT EXISTS"
            " (SELECT 1 FROM flow WHERE flow_name = ?)",
            (flow_name, flow_name))
        self.conn.commit()
        r = self.conn.execute(
            "SELECT id FROM flow WHERE flow_name = ?",
            (flow_name,)).fetchone()
        return r["id"] if r else None

    def flows(self, active_only=True):
        sql = "SELECT * FROM flow"
        if active_only:
            sql += " WHERE is_active = 1"
        sql += " ORDER BY id"
        return [dict(r) for r in self.conn.execute(sql)]

    # ---------- step（驗證鏈步驟） ----------
    # ---------- shortcut（API 快捷路由：api_url -> flow_name） ----------
    def add_shortcut(self, api_url, shortcut):
        """建立 API 快捷路由（冪等）

        api_url  = API 路徑（例如 /run/english-word）
        shortcut = 快捷名（例如 english word）
        返回 shortcut.id（INT）
        """
        self.conn.execute(
            "INSERT INTO shortcut (api_url, shortcut)"
            " SELECT ?, ? WHERE NOT EXISTS"
            " (SELECT 1 FROM shortcut WHERE api_url = ? OR shortcut = ?)",
            (api_url, shortcut, api_url, shortcut))
        self.conn.commit()
        r = self.conn.execute(
            "SELECT id FROM shortcut WHERE api_url = ?", (api_url,)).fetchone()
        return r["id"] if r else None

    def shortcuts(self, active_only=True):
        sql = "SELECT * FROM shortcut"
        if active_only:
            sql += " WHERE is_active = 1"
        sql += " ORDER BY id"
        return [dict(r) for r in self.conn.execute(sql)]

    def flow_by_shortcut(self, api_url):
        """由 api_url 攞 flow_name（搵唔到返回 None）

        2026-10-24：多 flow 支援 —— API 唔帶 flow_id，
        而係由 api_url match shortcut 表（唔 hardcode）。
        """
        r = self.conn.execute(
            "SELECT shortcut FROM shortcut WHERE api_url = ?"
            " AND is_active = 1", (api_url,)).fetchone()
        return r["shortcut"] if r else None

    def add_step(self, flow_name, question_id, seq):
        """建立一個 step（冪等：同一 flow + seq_id 更新）

        flow_name   = 驗證鏈名（5w2h / spec ...）
        question_id = question.id（問邊個問題）
        seq         = 第幾步（1, 2, 3...）-> 自動轉 seq.id
        """
        fid = self.add_flow(flow_name)
        # seq 名 -> seq.id（唔存在就自動註冊）
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
            """INSERT INTO step
               (flow_id, seq_id, question_id)
               VALUES (?, ?, ?)
               ON CONFLICT(flow_id, seq_id) DO UPDATE SET
                   question_id = excluded.question_id,
                   updated_at = datetime('now', 'localtime')""",
            (fid, seq_id, question_id))
        self.conn.commit()
        r = self.conn.execute(
            "SELECT id FROM step WHERE flow_id = ? AND seq_id = ?",
            (fid, seq_id)).fetchone()
        return r["id"] if r else None

    def flow_steps(self, flow_name="5w2h", active_only=True):
        """列出一個 flow 嘅全部 steps（按 seq 排序，JOIN 問題名 + 判斷條件）"""
        sql = """SELECT s.id, s.flow_id, s.seq_id, sq.seq AS seq,
                        s.question_id,
                        q.test_id, t.meta AS test,
                        q."5w2h_id", w.meta AS w5w2h,
                        q.operator_id, cz.meta AS calc_meta,
                        cz.expression AS calc_expression,
                        q.expected_id, e.boolean_id AS expected_boolean_id
                 FROM step s
                 JOIN flow f ON f.id = s.flow_id
                 LEFT JOIN seq sq ON sq.id = s.seq_id
                 LEFT JOIN question q ON q.id = s.question_id
                 LEFT JOIN test t ON t.id = q.test_id
                 LEFT JOIN "5W2H" w ON w.id = q."5w2h_id"
                 LEFT JOIN operator cz ON cz.id = q.operator_id
                 LEFT JOIN expected e ON e.id = q.expected_id
                 WHERE f.flow_name = ?"""
        args = (flow_name,)
        if active_only:
            sql += " AND s.is_active = 1"
        sql += " ORDER BY s.seq_id"
        return [dict(r) for r in self.conn.execute(sql, args)]

    # ---------- 判斷（operator 表控制 output） ----------
    # test 維度 -> 人話問題（俾 JSON/api 用，睇得明）
    TEST_QUESTION_TEXT = {
        "speech": "呢個值係咪英文單詞（is_english）？",
        "word": "呢個值係咪一個 word（詞語）？",
        "spec": "呢個值符合 spec（規範）？",
        "industry": "呢個值屬唔屬於 industry（行業字典）？",
        "source": "呢個值有冇證明到嘅來源（source → provider 有 official_url）？",
        "proof": "呢個值有冇證明（proof → provider 有 official_url）？",
        "single word": "呢個值係咪單一詞（冇 _ 冇空格）？",
        "symbol": "呢個值有冇符號（/ . , ; ' 等標點 / emoji，唔計數字）？",
        "letter": "呢個值係咪淨係英文字母（letter 表定義）？",
        "english": "呢個值係咪淨係英文字母（letter 表定義）？",  # 舊名兼容
        "INT": "呢個值係咪整數（INT 表定義，0-9）？",
    }
    # w5w2h 角度 -> 問法
    W5W2H_QUESTION_TEXT = {
        "what": "係咩？",
        "where": "喺邊？",
        "when": "幾時？",
        "who": "邊個？",
        "why": "點解？",
        "how": "點樣？",
        "how much": "幾多？",
    }

    def _question_text(self, test, w5w2h, value=None):
        """test × w5w2h -> 完整人話問題（可代入真實 value）

        2026-10-24h（用戶要求）：code 升級 —— 問題文字同問法
        都由表讀（question_text / w5w2h_text），dict 只係 fallback。
        """
        q = None
        ask = None
        try:
            r = self.conn.execute(
                """SELECT qt.text, t.meta AS test, w.meta AS w5w2h
                   FROM question_text qt
                   LEFT JOIN test t ON t.id = qt.test_id
                   LEFT JOIN "5W2H" w ON w.id = qt.w5w2h_id
                   WHERE t.meta = ? AND w.meta = ?""",
                (test, w5w2h)).fetchone()
            if r:
                q = r["text"]
        except Exception:
            pass
        if q is None:
            q = self.TEST_QUESTION_TEXT.get(test) or f"{test}？"
        try:
            r2 = self.conn.execute(
                """SELECT wt.text FROM w5w2h_text wt
                   LEFT JOIN "5W2H" w ON w.id = wt.w5w2h_id
                   WHERE w.meta = ?""", (w5w2h,)).fetchone()
            if r2:
                ask = r2["text"]
        except Exception:
            pass
        if ask is None:
            ask = self.W5W2H_QUESTION_TEXT.get(w5w2h) or str(w5w2h)
        if value is not None:
            # 代入真實值：'呢個值' -> 'fuck'
            q2 = q.replace("呢個值", repr(value))
            return f"{q2}（{w5w2h} = {ask}）"
        return f"{q}（{w5w2h} = {ask}）"

    def _explain_judge(self, calc_meta, answer, pass_value, ok):
        """由 operator + 值 build 人類可讀解釋（俾 API 返回，方便睇）"""
        def _f(v):
            try:
                return float(v)
            except Exception:
                return None
        fa, fp = _f(answer), _f(pass_value)
        if calc_meta in ("==", "!=", ">=", "<=", ">", "<"):
            if fa is not None and fp is not None:
                txt = (f"float({answer!r}) = {fa}  {calc_meta}"
                       f"  float({pass_value!r}) = {fp}")
            else:
                txt = (f"冇法子 float 轉換：answer={answer!r},"
                       f" pass_value={pass_value!r}")
            return (f"呢步用 {calc_meta} 比較：{txt}"
                    f" -> {'PASS' if ok else 'FAIL'}")
        if calc_meta == "is_true":
            return (f"答案必須係 True：answer={answer!r}"
                    f" (type={type(answer).__name__})"
                    f" -> {'PASS' if ok else 'FAIL'}")
        if calc_meta == "is_false":
            return (f"答案必須係 False：answer={answer!r}"
                    f" (type={type(answer).__name__})"
                    f" -> {'PASS' if ok else 'FAIL'}")
        if calc_meta == "bool_eq":
            def _b(v):
                return str(v).strip().lower() in ("yes", "true", "1")
            return (f"真假比對：answer {answer!r}->{_b(answer)}"
                    f" vs pass_value {pass_value!r}->{_b(pass_value)}"
                    f" -> {'PASS' if ok else 'FAIL'}")
        if calc_meta in ("eq", "ne"):
            return (f"字串比對：str({answer!r}) {calc_meta}"
                    f" str({pass_value!r})"
                    f" -> {'PASS' if ok else 'FAIL'}")
        return (f"{calc_meta} 判斷：answer={answer!r}"
                f" vs pass_value={pass_value!r}"
                f" -> {'PASS' if ok else 'FAIL'}")

    def _judge(self, calc_meta, calc_expression, pass_value, answer):
        """由 operator 表嘅 expression + expected 嘅 pass_value 決定答案 pass 定 fail

        判斷條件拆開兩張表：
            operator  = operator + expression（點比）
            expected    = pass_value（比幾多）
        自訂判斷條件 = 喺 calculation / expected 表加行，唔使改 code。
        """
        expr = calc_expression or DEFAULT_JUDGE_EXPR
        # 執行表達式（answer / pass_value 由表提供）
        # 安全環境：淨係開放 int / float / str / bool / len / abs（唔開放 __import__）
        safe_builtins = {
            "int": int, "float": float, "str": str, "bool": bool,
            "len": len, "abs": abs,
        }
        try:
            return bool(eval(expr, {"__builtins__": safe_builtins}, {
                "answer": answer, "pass_value": pass_value}))
        except Exception:
            return False

    def run_flow(self, flow_name="5w2h", answers=None, save=True,
                 value=None, value_id=None, register_meta=None,
                 register_type="value", register_source="question"):
        """行一個驗證鏈：順序逐個問，第一個 FAIL 就停

        answers = {question_id: 原始答案}（唔係 pass/fail！）
            operator 由 operator 表決定（== / >= / <= / != / > / <）
            期望值由 expected 表決定（pass_value）

        value    = 提交去檢查嘅值（例如 "Anthropic spec"）
                   -> 自動寫入 value 表，value_id 指向它
        value_id = 已有嘅 value.id（同 value 二選一）
        save=True 時寫入 run + answer（證明）。

        2026-10-24（用戶要求）：線性 flow，唔再分支導航。
            全部 PASS -> approved（status_id=1）
            第一個 FAIL -> 停喺嗰步 -> rejected（status_id=2），
            run.step_id 記錄停喺邊步。

        返回 {"status_id": n, "steps": [...], "ended_at": seq,
              "step_id": n, "answers": [...], "run_id": n,
              "resource_id": n, "value": str, "value_id": n}
        """
        answers = answers or {}
        if value_id is None and value is not None:
            value_id = self.add_value(value)
        steps = self.flow_steps(flow_name)
        if not steps:
            return {"status_id": 3, "steps": [], "ended_at": None,
                    "step_id": None, "answers": [],
                    "run_id": None, "resource_id": None}
        visited = []
        judged = []
        stopped_step = None
        all_pass = True
        for s in steps:
            visited.append(s["seq"])
            qid = s["question_id"]
            raw = answers.get(qid)
            # 2026-10-24t：expected 用 boolean_id（0/1）做期望值
            if s.get("expected_boolean_id") is not None:
                pv_raw = str(s["expected_boolean_id"])
            else:
                pv_raw = "1"  # 冇期望值 -> 預設真（舊行為兼容）
            ok = self._judge(s["calc_expression"], s["calc_expression"],
                             pv_raw, raw)
            # pass_value 輸出統一：'1'/'0' -> True/False（同 answer / is_pass 一致）
            pv = pv_raw
            try:
                if pv is not None and str(pv).strip() in ("1", "0"):
                    pv = str(pv).strip() == "1"
            except Exception:
                pass
            # 證明（source / proof test 先有 URL 證明顯示）
            proof = {}
            if s["test"] in ("source", "proof") and value is not None:
                if s["test"] == "source":
                    proof = self._source_proof(value)
                else:
                    proof = self._proof_proof(value)
            judged.append({
                "step_id": s["id"],
                "step_seq": s["seq"],
                "question_id": qid,
                "question": self._question_text(
                    s["test"], s["w5w2h"], value),
                "answer": raw,
                "calc_meta": s["calc_meta"],
                "pass_value": pv,
                "test": s["test"],
                "w5w2h": s["w5w2h"],
                "is_pass": ok,
                "proof": proof or None,
            })
            if not ok:
                all_pass = False
                stopped_step = s["id"]
                break
        status_id = 1 if all_pass else 2
        run_id = None
        resource_id = None
        if save:
            run_id = self._save_run(flow_name, value_id, stopped_step,
                                    status_id, judged)
            # approved -> 自動註冊入 resource.db
            if status_id == 1 and register_meta:
                resource_id = self._register_resource(
                    register_meta, register_type, register_source)
        return {"status_id": status_id, "steps": visited,
                "ended_at": visited[-1], "step_id": stopped_step,
                "answers": judged, "run_id": run_id,
                "resource_id": resource_id, "value": value,
                "value_id": value_id}

    def _register_resource(self, meta, type_name, source_name):
        """自動註冊入 resource.db（經 Resource API，唯一入口）"""
        try:
            from resource import Resource
            r = Resource()
            try:
                return r.register(meta, type_name, source_name)
            finally:
                r.close()
        except Exception:
            return None

    # ---------- 批量處理詞（source_proof，source module 資產） ----------
    def run_terminology(self, flow_name="5w2h",
                        register_type="value", register_source="question",
                        limit=None):
        """用同一條 flow 批量處理詞（source_proof，source module 資產）

        2026-10-24j（用戶要求）：唔再讀 terminology.db term 表 ——
        詞嘅來源由 source.db source_proof 表（word UNIQUE）提供：
            source_proof.word -> 每個詞
        single word   = word 冇 _ 冇空格（例如 build / fill / id ...）

        答案由詞本身自動計算（唔可以 caller 提供，唔可以 fake）：
            symbol?       -> 詞有符號（/ . , ; ' 等標點 / emoji；數字唔算）
            speech?       -> 詞係英文單詞（english 字符集）
            single word?  -> 詞冇 _ 冇空格（== 1）

        每個詞 -> 行同一條 flow -> 寫入 run（證明）
        approved  -> 自動註冊入 resource.db（meta = word:<word>）

        返回 {"total": n, "approved": n, "rejected": n, "runs": [...]}
        """
        try:
            from source import Source as _Source
            _s = _Source()
            try:
                words = [r["word"] for r in _s.store.conn.execute(
                    "SELECT word FROM source_proof"
                    " WHERE is_active = 1"
                    " AND word NOT LIKE '%\\_%' ESCAPE '\\'"
                    " AND word NOT LIKE '% %'"
                    " ORDER BY word")]
            finally:
                _s.close()
        except Exception:
            words = []
        if limit:
            words = words[:limit]
        report = {"total": len(words), "approved": 0, "rejected": 0,
                  "runs": []}
        for word in words:
            # 答案由詞本身自動計算（唔可以 caller 提供）
            answers = self._auto_answers(word, flow_name)
            res = self.run_flow(flow_name, answers,
                                register_meta=f"word:{word}",
                                register_type=register_type,
                                register_source=register_source)
            if res["status_id"] == 1:
                report["approved"] += 1
            else:
                report["rejected"] += 1
            report["runs"].append({
                "word": word, "status_id": res["status_id"],
                "resource_id": res["resource_id"],
            })
        return report

    def _auto_answers(self, word, flow_name="5w2h"):
        """由詞本身自動計算答案（唔可以 caller 提供，唔可以 fake）

        每個問題（step）按 test 維度自動判斷：
            symbol       -> 詞有符號（/ . , ; ' 等標點 / emoji；數字唔算）
            speech       -> 詞係英文單詞（terminology is_english 表）
            single word  -> 詞冇 _ 冇空格（== 1）
            source       -> 詞有冇證明到嘅來源（is_english / is_industry_spec
                             有 source_id = 1；冇 = 0）
            其他         -> 由詞嘅特性判斷（有嘢 = True）

        flow_name = 邊條 flow（2026-10-24：多 flow 支援，
                    唔可以再寫死淨係 5w2h）
        """
        import re as _re
        answers = {}
        for s in self.flow_steps(flow_name):
            qid = s["question_id"]
            test = s["test"]
            if test == "symbol":
                # 有符號：value 入面有任何一個 DB 定義嘅符號字符
                # （symbol 表 —— 唔 hardcode，加符號 = 加表行）
                answers[qid] = self._has_dict_char(word, "symbol")
            elif test == "speech":
                # 係英文單詞（terminology is_english 表）
                answers[qid] = self._is_english_word(word)
            elif test == "single word":
                # 冇 _ 冇空格 = 單一詞（== 1）
                answers[qid] = 1 if ("_" not in word and " " not in word) else 0
            elif test == "source":
                # 有證明到嘅來源：terminology is_english / is_industry_spec
                # 有 source_id 就係有來源（1），冇就 0
                answers[qid] = self._has_source(word)
            elif test == "proof":
                # 有證明：is_industry_spec.proof 有內容
                answers[qid] = self._has_proof(word)
            elif test in ("english", "letter"):
                # 係英文字：value 全部由 DB 定義嘅英文字母組成（letter 表）
                answers[qid] = self._is_english_chars(word)
            elif test in ("INT", "int", "integer"):
                # 係整數：value 全部由 DB 定義嘅數字字符組成（INT 表）
                answers[qid] = self._is_int_chars(word)
            elif not test:
                # （空）test = 值係咪空？
                # is empty = 0 -> pass；is empty = 1 -> fail
                # （配合 exp=6 pass_value='0' + == operator）
                answers[qid] = 1 if str(word or "").strip() != "" else 0
            else:
                # 其他維度：有嘢 = True
                answers[qid] = bool(word)
        return answers

    def _is_english_word(self, word):
        """詞係咪英文單詞

        2026-10-24j（用戶要求）：唔再直接讀 terminology.db is_english ——
        英文判斷用 source 字符集（english 表，source module 資產）：
        全字元都喺 english 字符集 + 有字母 = 英文。
        冇記錄 -> 用簡單規則（全字母 = 英文）。
        """
        if not word:
            return False
        try:
            chars = self._dict_values("english")
            if chars:
                return all(ch in chars for ch in word) and any(
                    ch.isalpha() for ch in word)
        except Exception:
            pass
        return word.isalpha()

    # ---------- 字典表判斷（symbol / letter / INT—— character 資產） ----------
    def _dict_values(self, table, active_only=True):
        """由 character.db 攞字符集（symbol / letter / INT）

        2026-10-24s（用戶要求）：字符定義屬 character module；
        question 係消費者，讀 character.db（唔直接寫）。
        """
        try:
            import sqlite3 as _sq
            conn = _sq.connect(r"C:\projects\meta\character\character.db")
            conn.row_factory = _sq.Row
            try:
                t = table
                # 舊名兼容：english -> letter
                if t == "english":
                    t = "letter"
                if t == "letter":
                    # 每行一個字母（value），format 由 letter_char_format_id 控制
                    rows = conn.execute(
                        "SELECT value FROM letter"
                        " WHERE is_active = 1").fetchall()
                    return {r["value"] for r in rows
                            if r["value"] is not None}
                sql = f'SELECT value FROM "{t}"'
                if active_only:
                    sql += " WHERE is_active = 1"
                return {r["value"] for r in conn.execute(sql)
                        if r["value"] is not None}
            finally:
                conn.close()
        except Exception:
            return set()

    def _has_dict_char(self, word, table):
        """word 入面有冇任何一個 DB 定義嘅字符（symbol/INT...）"""
        if not word:
            return False
        chars = self._dict_values(table)
        return any(ch in word for ch in chars)

    def _is_english_chars(self, word):
        """word 係咪淨係由 DB 定義嘅英文字母組成（english 表）"""
        if word is None or word == "":
            return False
        chars = self._dict_values("english")
        return all(ch in chars for ch in word)

    def _is_int_chars(self, word):
        """word 係咪淨係由 DB 定義嘅整數字符組成（INT 表）"""
        if word is None or word == "":
            return False
        chars = self._dict_values("INT")
        return all(ch in chars for ch in word)

    def _has_source(self, word):
        """詞有冇證明到嘅來源（source == url）—— bool 版本

        2026-10-24（用戶要求）：source module 提供「proofed source」。
        判斷鏈：
            word -> is_english.source_id（terminology.db）
                 -> source.provider_id（source.db）
                 -> provider.official_url 非空（source.db）
        只有條鏈完整（有 URL）先算「有來源 = 1」。
        """
        p = self._source_proof(word)
        return p["has"]

    def _source_proof(self, word):
        """詞嘅來源證明（返回 dict，含 URL 俾 API 顯示）

        2026-10-24f（用戶要求）：JSON 要顯示 source.url 證明。
        2026-10-24j（用戶要求）：proof source 由 module : source 擁有 ——
        question 經 Source().source_proof() 查（唔再直接讀
        terminology.db）。
        返回 {"has": bool, "url": str|None, "source": str|None,
               "provider": str|None, "explain": str}
        """
        try:
            from source import Source as _Source
            s = _Source()
            try:
                return s.source_proof(word)
            finally:
                s.close()
        except Exception as e:
            return {"has": False, "url": None, "source": None,
                    "provider": None,
                    "explain": f"source module 查唔到：{e}"}

    def _has_proof(self, word):
        """詞有冇證明（proof == url）—— bool 版本"""
        return self._proof_proof(word)["has"]

    def _proof_proof(self, word):
        """詞嘅 proof 證明（返回 dict，含 URL 俾 API 顯示）

        2026-10-24f（用戶要求）：JSON 要顯示 proof 嘅 URL。
        2026-10-24j（用戶要求）：proof 由 source module 擁有 ——
        經 Source().source_proof() 查（proof 欄喺 source_proof 表）。
        """
        try:
            from source import Source as _Source
            s = _Source()
            try:
                return s.source_proof(word)
            finally:
                s.close()
        except Exception as e:
            return {"has": False, "url": None, "source": None,
                    "provider": None,
                    "explain": f"source module 查唔到：{e}"}

    def _save_run(self, flow_name, value_id, step_id, status_id, judged):
        """寫入 run + result（證明）

        2026-10-24：ended_at（seq）-> step_id（停喺邊步）
        2026-10-24b：result.answer_id（1/0 字典）+ status_id（1=approved 2=rejected）
        """
        fid = self.add_flow(flow_name)
        cur = self.conn.execute(
            "INSERT INTO run"
            " (flow_id, value_id, step_id, status_id)"
            " VALUES (?, ?, ?, ?)", (fid, value_id, step_id, status_id))
        run_id = cur.lastrowid
        for j in judged:
            # answer -> answer 字典 id（1='1'真/有，2='0'假/冇）
            raw = j["answer"]
            if raw is None:
                aid = None
            else:
                s = str(raw).strip().lower()
                aid = 1 if s in ("true", "1", "2", "3") else 2
            # is_pass -> status_id
            sid = 1 if j["is_pass"] else 2
            self.conn.execute(
                "INSERT OR IGNORE INTO result"
                " (run_id, question_id, answer_id, status_id)"
                " VALUES (?, ?, ?, ?)",
                (run_id, j["question_id"], aid, sid))
        self.conn.commit()
        return run_id

    def flow_runs(self, limit=20):
        """列出執行驗證記錄（JOIN flow + value + step + status + result）"""
        rows = [dict(r) for r in self.conn.execute(
            """SELECT r.id, r.flow_id, f.flow_name,
                      r.value_id, v.value,
                      r.step_id, sq.seq AS step_seq,
                      r.status_id, b.value AS status, r.created_at
               FROM run r
               LEFT JOIN flow f ON f.id = r.flow_id
               LEFT JOIN value v ON v.id = r.value_id
               LEFT JOIN step st ON st.id = r.step_id
               LEFT JOIN seq sq ON sq.id = st.seq_id
               LEFT JOIN status s ON s.id = r.status_id
               LEFT JOIN boolean b ON b.id = s.boolean_id
               ORDER BY r.id DESC LIMIT ?""", (limit,))]
        for r in rows:
            r["answers"] = [dict(x) for x in self.conn.execute(
                """SELECT rs.id, rs.run_id, rs.question_id,
                          rs.answer_id, a.boolean_id AS answer_value,
                          rs.status_id, b2.value AS answer_status
                   FROM result rs
                   LEFT JOIN answer a ON a.id = rs.answer_id
                   LEFT JOIN status st2 ON st2.id = rs.status_id
                   LEFT JOIN boolean b2 ON b2.id = st2.boolean_id
                   WHERE rs.run_id = ?
                   ORDER BY rs.id""", (r["id"],))]
        return rows

    def count(self):
        return self.conn.execute(
            "SELECT COUNT(*) FROM question WHERE is_active = 1").fetchone()[0]

    def commit(self):
        self.conn.commit()

    def close(self):
        self.conn.close()