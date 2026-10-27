"""function.py — question 核心業務邏輯層

呢個 module 嘅核心邏輯全部喺 api.py class 方法內（真實業務邏輯）：

    Question: add_test, tests, remove_test, add_5w2h, list_5w2h, add_question, set_expected, add_operator, operators, set_operator, set_all_operators, add_expected, set_expected_value, expecteds, add_value, values, questions, add_flow, flows, add_step, flow_steps, run_flow, flow_runs, run_terminology, count

（7 檔標準：__init__/function/api/route/schema/sql/skill 全部 required）
呢個檔案係業務邏輯嘅「統一入口標記」—— class 方法 = 業務邏輯，
api.py 係對外介面；function.py 係邏輯清單。
"""
