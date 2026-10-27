"""route.py — question.db CLI

用法：
    python -m question.route list                    # 列出全部問題（JOIN 名）
    python -m question.route tests                   # 列出測試維度
    python -m question.route test-add --meta <名>     # 新增維度（--meta "" = 空 row）
    python -m question.route test-remove --meta <名>  # 移除維度
    python -m question.route 5w2h                    # 列出提問框架
    python -m question.route add --test 1 --5w2h 1 [--operator ==] [--pass-value 1]  # 建立問題
    python -m question.route expected --question 1 --operator == [--pass-value 1]  # 設定判斷條件
    python -m question.route expecteds              # 列出期望值 + operator 字典
    python -m question.route expected-set --id 4 --value YES   # 設定期望值
    python -m question.route expected-remove --id 7            # 移除期望值
    python -m question.route calculations            # 只列 operator 字典
    python -m question.route op-all --operator ==   # 全部 question 用 == 判斷
    python -m question.route flow-add --name 5w2h    # 建立驗證鏈
    python -m question.route step-add --flow 5w2h --question 1 --seq 1 [--pass-next <id>] [--fail-next <id>] [--pass-status 1] [--fail-status 2]
    python -m question.route flow [--name 5w2h]      # 列出驗證鏈（含步驟）
    python -m question.route run --name 5w2h --answers '{"1": true, "2": true, "3": true}' [--test 1] [--register-meta <資源名>]
    python -m question.route runs                    # 列出執行記錄（含答案）
    python -m question.route terms [--limit 10]      # 批量處理 terminology 嘅 single words
    python -m question.route tq-add --flow <id> [--tree 2]  # 綁定驗證鏈去 module 大類
    python -m question.route tqs [--tree 2]          # 列出 module 大類嘅問題
    python -m question.route count                    # 總數
"""

import sys

from .api import Question

USAGE = """用法：
    python -m question.route list
    python -m question.route tests
    python -m question.route test-add --meta <維度名>
    python -m question.route test-remove --meta <維度名>
    python -m question.route 5w2h
    python -m question.route add --test <id> --5w2h <id> [--operator <op>] [--pass-value <值>]
    python -m question.route expected --question <id> --operator <op> [--pass-value <值>]
    python -m question.route expecteds
    python -m question.route expected-set --id <id> --value <值>
    python -m question.route expected-remove --id <id>
    python -m question.route operators
    python -m question.route op-all --operator <op>
    python -m question.route flow-add --name <flow名>
    python -m question.route step-add --flow <flow名> --question <id> --seq <n>
    python -m question.route flow [--name <flow名>]
    python -m question.route run --name <flow名> --answers '<json>' [--value <提交值>]
    python -m question.route runs
    python -m question.route terms [--limit <n>]
    python -m question.route tq-add --flow <id> [--tree 2]
    python -m question.route tqs [--tree 2]
    python -m question.route count
"""


def _arg(argv, name, default=None):
    """攞 --flag 後面嘅值（越界返回 default）

    PowerShell 會剝掉結尾空字串（`--meta ""` 變成 `--meta`），
    所以 index 越界要當「空值」而唔係 crash。
    """
    if name in argv:
        i = argv.index(name) + 1
        if i < len(argv):
            return argv[i]
        return "" if default is None else default
    return default



def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print(USAGE)
        return 1
        return _main(argv)


def _main(argv):
    q = Question()
    try:
        cmd = argv[0]
        if cmd == "list":
            for r in q.questions():
                print(f"[{r['id']}] {r['test']} × {r['w5w2h']}"
                      f"  (operator={r['calc_meta']}"
                      f" pass_value={r['pass_value']})")
        elif cmd == "tests":
            for r in q.tests():
                print(f"[{r['id']}] {r['meta']}")
        elif cmd == "test-add":
            # --meta 可以係空字串（要空 row）—— 所以唔可以用 None 判斷
            if "--meta" not in argv:
                print("需要 --meta <維度名>（要空 row 就 --meta \"\"）")
                return 1
            meta = _arg(argv, "--meta", "")
            tid_new = q.add_test(meta)
            print(f"✅ test id={tid_new}（meta={meta!r}）")
        elif cmd == "test-remove":
            if "--meta" not in argv:
                print("需要 --meta <維度名>")
                return 1
            meta = _arg(argv, "--meta", "")
            ok = q.remove_test(meta)
            print(f"✅ 已移除 test meta={meta!r}" if ok
                  else f"（冇搵到 test meta={meta!r}）")
        elif cmd == "5w2h":
            for r in q.list_5w2h():
                print(f"[{r['id']}] {r['meta']}")
        elif cmd == "add":
            t = int(_arg(argv, "--test", 0))
            w = int(_arg(argv, "--5w2h", 0))
            if not t or not w:
                print("需要 --test <id> --5w2h <id>")
                return 1
            qid = q.add_question(t, w,
                                 calc_meta=_arg(argv, "--operator"),
                                 pass_value=_arg(argv, "--pass-value"))
            print(f"✅ 問題 id={qid}（test={t} × 5W2H={w}）")
        elif cmd == "expected":
            qid = int(_arg(argv, "--question", 0))
            op = _arg(argv, "--operator")
            if not qid:
                print("需要 --question <id> --operator <operator名>"
                      " [--pass-value <值>]")
                return 1
            q.set_expected(qid, calc_meta=op,
                           pass_value=_arg(argv, "--pass-value"))
            print(f"✅ 判斷條件: question={qid} -> operator={op}"
                  f" pass_value={_arg(argv, '--pass-value')}")
        elif cmd == "expecteds":
            print("-- expected（期望值字典）--")
            for r in q.expecteds():
                print(f"  [{r['id']}] pass_value={r['pass_value']}"
                      f" <- {r['description'] or ''}")
            print("-- operators（operator 字典）--")
            for r in q.operators():
                print(f"  [{r['id']}] {r['meta']:6s}"
                      f" {r['expression'] or '':45s}"
                      f" <- {r['description'] or ''}")
        elif cmd == "operators":
            for r in q.operators():
                print(f"[{r['id']}] {r['meta']:6s}"
                      f" {r['expression'] or '':45s}"
                      f" <- {r['description'] or ''}")
        elif cmd == "expected-set":
            eid = int(_arg(argv, "--id", 0))
            if not eid or "--value" not in argv:
                print("需要 --id <expected.id> --value <值>")
                return 1
            val = _arg(argv, "--value", "")
            q.set_expected_value(eid, val)
            print(f"✅ expected.id={eid} pass_value={val!r}")
        elif cmd == "expected-remove":
            eid = int(_arg(argv, "--id", 0))
            if not eid:
                print("需要 --id <expected.id>")
                return 1
            ok = q.remove_expected(eid)
            print(f"✅ 已移除 expected.id={eid}" if ok
                  else f"（冇搵到 expected.id={eid}）")
        elif cmd == "op-all":
            op = _arg(argv, "--operator")
            if not op:
                print("需要 --operator <operator名>")
                return 1
            rep = q.set_all_operators(op)
            print(f"✅ 全部 question 嘅 operator -> {rep['calc_meta']}"
                  f"（operator_id={rep['operator_id']}）")
            print(f"   before: {rep['before']}")
            print(f"   affected={rep['affected']} / total={rep['total']}")
            if rep["mismatch"]:
                print(f"   ❌ 未對齊: {rep['mismatch']}")
                return 1
            print("   核對：全部已對齊 ✅")
        elif cmd == "flow-add":
            name = _arg(argv, "--name", "5w2h")
            fid = q.add_flow(name)
            print(f"✅ 驗證鏈 id={fid}（{name}）")
        elif cmd == "step-add":
            flow = _arg(argv, "--flow", "5w2h")
            qid = int(_arg(argv, "--question", 0))
            seq = int(_arg(argv, "--seq", 0))
            if not qid or not seq:
                print("需要 --flow <flow名> --question <id> --seq <n>")
                return 1
            sid = q.add_step(flow, qid, seq)
            print(f"✅ step id={sid}（flow={flow} seq={seq}）")
        elif cmd == "flow":
            for r in q.flow_steps(_arg(argv, "--name", "5w2h")):
                print(f"[{r['id']}] seq={r['seq']} {r['test']} × {r['w5w2h']}"
                      f"  (operator={r['calc_meta']}"
                      f" pass_value={r['pass_value']})")
        elif cmd == "run":
            import json
            answers = json.loads(_arg(argv, "--answers", "{}"))
            r = q.run_flow(_arg(argv, "--name", "5w2h"), answers,
                           value=_arg(argv, "--value"))
            print(f"結果: status_id={r['status_id']}  （行過 steps: {r['steps']}）"
                  f"  run_id={r['run_id']} value_id={r.get('value_id')}"
                  f" resource_id={r['resource_id']}")
            for a in r["answers"]:
                mark = "✅" if a["is_pass"] else "❌"
                print(f"  {mark} {a['test']} × {a['w5w2h']}"
                      f"  (operator={a['calc_meta']})"                   f" 答案={a['answer']!r}")
        elif cmd == "runs":
            for r in q.flow_runs():
                print(f"[{r['id']}] {r['flow_name']}"
                      f" value={r['value']!r} value_id={r['value_id']}"
                      f" -> {r['status']}  (status_id={r['status_id']}"
                      f" step_seq={r['step_seq']} {r['created_at']})")
                for a in r["answers"]:
                    mark = "✅" if a["is_pass"] else "❌"
                    print(f"    {mark} question={a['question_id']}"
                          f" 答案={a['answer']!r}")
        elif cmd == "terms":
            limit = int(_arg(argv, "--limit", 0)) or None
            rep = q.run_terminology(limit=limit)
            print(f"總數: {rep['total']}  approved: {rep['approved']}"
                  f"  rejected: {rep['rejected']}")
            for run in rep["runs"][:20]:
                mark = "✅" if run["status_id"] == 1 else "❌"
                print(f"  {mark} {run['word']:30s}"
                      f" status_id={run['status_id']}"
                      f" resource_id={run['resource_id']}")
        elif cmd == "tq-add":
            fid = int(_arg(argv, "--flow", 0)) or int(_arg(argv, "--question", 0))
            tree = int(_arg(argv, "--tree", 2))
            if not fid:
                print("需要 --flow <flow id> [--tree 2]")
                return 1
            # 2026-10-26：guard/task 已刪除 -> 直接寫入（冇 task 訂單）
            mid = q.add_taxonomy_question(fid, tree)
            print(f"✅ taxonomy 綁定 id={mid}"
                  f"（tree_id={tree} flow={fid}）")
        elif cmd == "tqs":
            tree = int(_arg(argv, "--tree", 2))
            rows = q.taxonomy_questions(tree)
            if not rows:
                print(f"（tree_id={tree} 冇綁定驗證鏈）")
            for r in rows:
                print(f"[{r['taxonomy_id']}] flow={r['flow_id']}"
                      f"  {r['flow_name']}"
                      f"  steps={r['step_count']}")
        elif cmd == "count":
            print(f"總數: {q.count()}")
        else:
            print(USAGE)
            return 1
    finally:
        q.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())