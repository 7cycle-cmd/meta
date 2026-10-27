"""route.py — terminology.db CLI"""

import sys

from .api import Terminology

USAGE = """用法：
    python -m terminology.route list
    python -m terminology.route add --meta META --desc DESC
    python -m terminology.route lookup META
    python -m terminology.route count
    python -m terminology.route collect RESOURCE_ID VALUE
    python -m terminology.route collect-table DB_TABLE_ID VALUE
    python -m terminology.route collect-field DB_FIELD_ID VALUE
    python -m terminology.route collected
    python -m terminology.route flows
    python -m terminology.route flow-steps --flow <名>
    python -m terminology.route run --flow <名> --answers '<json>' [--value <值>]
    python -m terminology.route runs
"""



def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print(USAGE)
        return 1
    return _main(argv)


def _main(argv):
    t = Terminology()
    try:
        cmd = argv[0]
        if cmd == "list":
            for r in t.list_terms():
                print(f"[{r['id']}] {r['meta']}  <- {r['description']}")
        elif cmd == "add":
            meta = argv[argv.index("--meta") + 1]
            desc = argv[argv.index("--desc") + 1]
            tid, created = t.register(meta, desc)
            print(f"{'✅ 新增' if created else '⚠️ 已存在'} id={tid} {meta}")
        elif cmd == "lookup":
            r = t.lookup(argv[1])
            print(dict(r) if r else "唔存在")
        elif cmd == "count":
            print(f"總數: {t.count()}")
        elif cmd == "collect":
            t.collect(int(argv[1]), argv[2])
            print(f"✅ 已收集 resource_id={argv[1]} value={argv[2]}")
        elif cmd == "collect-table":
            t.collect_table(int(argv[1]), argv[2])
            print(f"✅ 已收集 db_table_id={argv[1]} value={argv[2]}")
        elif cmd == "collect-field":
            t.collect_field(int(argv[1]), argv[2])
            print(f"✅ 已收集 db_field_id={argv[1]} value={argv[2]}")
        elif cmd == "collected":
            for r in t.collected():
                print(f"{r}")
        elif cmd == "flows":
            for r in t.flows():
                print(f"[{r['id']}] {r['flow_name']}")
        elif cmd == "flow-steps":
            import io as _io
            name = argv[argv.index("--flow") + 1] \
                if "--flow" in argv else "spec"
            for r in t.flow_steps(name):
                print(f"  seq={r['seq']}  {r['test']:12s}"
                      f" op={r['operator_meta']}"
                      f" exp={r['expected_boolean_id']}")
        elif cmd == "run":
            import json as _json
            name = argv[argv.index("--flow") + 1] \
                if "--flow" in argv else "spec"
            answers = {}
            if "--answers" in argv:
                answers = _json.loads(
                    argv[argv.index("--answers") + 1])
            value = argv[argv.index("--value") + 1] \
                if "--value" in argv else None
            res = t.run_flow(name, answers, value=value)
            print(f"flow={name} status_id={res['status_id']}"
                  f" run_id={res['run_id']}")
            for j in res["answers"]:
                print(f"  seq={j['seq']} {j['test']:12s} answer={j['answer']!r}"
                      f" -> {'PASS' if j['is_pass'] else 'FAIL'}")
        elif cmd == "runs":
            for r in t.flow_runs():
                print(f"[{r['id']}] {r['flow_name']:8s}"
                      f" value={r['value']!r:20s} status={r['status']}")
        else:
            print(USAGE)
            return 1
    finally:
        t.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())