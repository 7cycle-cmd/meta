"""route.py — plan CLI 入口

用法：
    python -m plan <command>
    plans [preflight_id] [role_id] [rule_id] [tool_id] [value_id]
    add <preflight_id> <run_id> [role_id] [rule_id] [tool_id] [value_id]
    count
"""

import sys

from .api import Plan


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help", "help"):
        print("可用命令（plan）:")
        for m in ['plans', 'add', 'count']:
            print(f"    {m}")
        return 0
    cmd = argv[0]
    if cmd not in ['plans', 'add', 'count']:
        print(f"未知命令: {cmd}")
        return 1
    obj = Plan()
    try:
        if cmd == "plans":
            preflight_id = int(argv[1]) if len(argv) > 1 else None
            role_id = int(argv[2]) if len(argv) > 2 else None
            rule_id = int(argv[3]) if len(argv) > 3 else None
            tool_id = int(argv[4]) if len(argv) > 4 else None
            value_id = int(argv[5]) if len(argv) > 5 else None
            for x in obj.plans(preflight_id=preflight_id, role_id=role_id,
                               rule_id=rule_id, tool_id=tool_id,
                               value_id=value_id):
                print(f"{x['id']}\t{x['preflight_id']}\t{x['role_id'] or ''}"
                      f"\t{x['rule_id'] or ''}\t{x['tool_id'] or ''}"
                      f"\t{x['value_id'] or ''}\t{x['run_id']}")
        elif cmd == "add":
            if len(argv) < 3:
                print("需要 preflight_id + run_id")
                return 1
            preflight_id = int(argv[1])
            run_id = int(argv[2])
            role_id = int(argv[3]) if len(argv) > 3 else None
            rule_id = int(argv[4]) if len(argv) > 4 else None
            tool_id = int(argv[5]) if len(argv) > 5 else None
            value_id = int(argv[6]) if len(argv) > 6 else None
            print("plan id:", obj.add_plan(preflight_id, run_id, role_id,
                                           rule_id, tool_id, value_id))
        elif cmd == "count":
            print(obj.count())
    finally:
        obj.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())