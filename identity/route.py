"""route.py — identity CLI"""

import sys

from .api import Identity

USAGE = """用法：
    python -m identity.route [command]

commands:
    register <value_id> <condition_id> <flow_id> <step_id> [permit_id]   登記一個身份
    lookup <value_id> [condition_id] [flow_id] [step_id]                按 value 查
    list [value_id]                                                     列出全部（可按 value 篩選）
"""


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print(USAGE)
        return 1
    i = Identity()
    try:
        cmd = argv[0]
        if cmd == "register":
            if len(argv) < 5:
                print("需要 value_id + condition_id + flow_id + step_id")
                return 1
            value_id = int(argv[1])
            condition_id = int(argv[2])
            flow_id = int(argv[3])
            step_id = int(argv[4])
            permit_id = int(argv[5]) if len(argv) > 5 else None
            rid = i.register(value_id, condition_id, flow_id, step_id,
                             permit_id=permit_id)
            print(f"✅ 已登記身份（value={value_id} condition={condition_id}"
                  f" flow={flow_id} step={step_id}）-> identity id={rid}")
        elif cmd == "lookup":
            if len(argv) < 2:
                print("需要 value_id")
                return 1
            value_id = int(argv[1])
            condition_id = int(argv[2]) if len(argv) > 2 else None
            flow_id = int(argv[3]) if len(argv) > 3 else None
            step_id = int(argv[4]) if len(argv) > 4 else None
            for r in i.lookup(value_id, condition_id, flow_id, step_id):
                print(f"{r['id']}\tvalue={r['value_id']}"
                      f"\tcondition={r['condition_id']}"
                      f"\tflow={r['flow_id']}\tstep={r['step_id']}"
                      f"\tpermit_id={r.get('permit_id') or ''}"
                      f"\t{r['description'] or ''}")
        elif cmd == "list":
            value_id = int(argv[1]) if len(argv) > 1 else None
            for r in i.list_all(value_id=value_id):
                print(f"{r['id']}\tvalue={r['value_id']}"
                      f"\tcondition={r['condition_id']}"
                      f"\tflow={r['flow_id']}\tstep={r['step_id']}"
                      f"\tpermit_id={r.get('permit_id') or ''}"
                      f"\t{r['description'] or ''}")
        else:
            print(USAGE)
            return 1
    finally:
        i.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
