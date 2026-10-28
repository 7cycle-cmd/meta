"""route.py — task CLI 入口

用法：
    python -m task <command>
    tasks [preflight_id] [schema_id] [plan_id] [role_id] [rule_id] [tool_id] [value_id]
    add <preflight_id> <schema_id> <run_id> [plan_id] [role_id] [rule_id] [tool_id] [value_id]
    count
"""

import sys

from .api import Task


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help", "help"):
        print("可用命令（task）:")
        for m in ['tasks', 'add', 'count']:
            print(f"    {m}")
        return 0
    cmd = argv[0]
    if cmd not in ['tasks', 'add', 'count']:
        print(f"未知命令: {cmd}")
        return 1
    obj = Task()
    try:
        if cmd == "tasks":
            preflight_id = int(argv[1]) if len(argv) > 1 else None
            schema_id = int(argv[2]) if len(argv) > 2 else None
            plan_id = int(argv[3]) if len(argv) > 3 else None
            role_id = int(argv[4]) if len(argv) > 4 else None
            rule_id = int(argv[5]) if len(argv) > 5 else None
            tool_id = int(argv[6]) if len(argv) > 6 else None
            value_id = int(argv[7]) if len(argv) > 7 else None
            for x in obj.tasks(preflight_id=preflight_id, schema_id=schema_id,
                               plan_id=plan_id, role_id=role_id,
                               rule_id=rule_id, tool_id=tool_id,
                               value_id=value_id):
                print(f"{x['id']}\t{x['preflight_id']}\t{x['schema_id']}"
                      f"\t{x['plan_id'] or ''}\t{x['role_id'] or ''}"
                      f"\t{x['rule_id'] or ''}\t{x['tool_id'] or ''}"
                      f"\t{x['value_id'] or ''}\t{x['run_id']}")
        elif cmd == "add":
            if len(argv) < 4:
                print("需要 preflight_id + schema_id + run_id")
                return 1
            preflight_id = int(argv[1])
            schema_id = int(argv[2])
            run_id = int(argv[3])
            plan_id = int(argv[4]) if len(argv) > 4 else None
            role_id = int(argv[5]) if len(argv) > 5 else None
            rule_id = int(argv[6]) if len(argv) > 6 else None
            tool_id = int(argv[7]) if len(argv) > 7 else None
            value_id = int(argv[8]) if len(argv) > 8 else None
            print("task id:", obj.add_task(preflight_id, schema_id, run_id,
                                           plan_id, role_id, rule_id,
                                           tool_id, value_id))
        elif cmd == "count":
            print(obj.count())
    finally:
        obj.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())