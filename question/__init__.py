"""question — 問題層：test（測試維度）× 5W2H（提問框架） package

模組分工：
    sql.py       資料庫存取層（test / "5W2H" / question / flow / step / run / answer / status 表）
    api.py       對外 API（Question 類）
    route.py     命令行入口（CLI）

表：
    test              測試維度字典（speech / word / spec / industry / source / proof / single word / symbol）
    "5W2H"            提問框架字典（what / where / when / who / why / how / how much）
    operator          operator 字典（點比：== / >= / <= / != / > / <）+ expression（判斷表達式）
    expected          期望值字典（比幾多：pass_value）
    value             提交值字典（submit xxx 去驗證）
    question          test × 5W2H 組合 + 判斷條件（operator_id + expected_id）
    flow            驗證鏈（flow_name）
    step            驗證鏈步驟（flow_id + seq + question_id）
    run             執行記錄（flow_id + value_id + step_id + status_id）
    answer          每個問題嘅原始答案 + is_pass（證明）
    status            狀態字典（approved / rejected / NA）

判斷條件 vs 判斷結果：
    question.operator_id + question.expected_id = 判斷條件（DB 控制）
    answer.is_pass                 = 判斷結果（執行時由 _judge 判斷出嚟）

用法：
    from question import Question
    q = Question()
    q.add_question(test_id=1, w5h2_id=1, calc_meta="==", pass_value="1")
    q.close()
"""

from .api import Question

__all__ = ["Question"]
__version__ = "1.0.0"