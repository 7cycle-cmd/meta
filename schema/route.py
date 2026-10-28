"""route.py — schema CLI 入口

用法：
    python -m schema <command>
    registries [run_id] [plan_id] [skill_id]
    add <run_id> [plan_id] [skill_id]
    check <run_id> [plan_id] [skill_id]
    count
"""

import sys

from .api import Schema


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help", "help"):
        print("可用命令（schema）:")
        for m in ['registries', 'add', 'check', 'count']:
            print(f"    {m}")
        return 0
    cmd = argv[0]
    if cmd not in ['registries', 'add', 'check', 'count']:
        print(f"未知命令: {cmd}")
        return 1
    obj = Schema()
    try:
        if cmd == "registries":
            run_id = int(argv[1]) if len(argv) > 1 else None
            plan_id = int(argv[2]) if len(argv) > 2 else None
            skill_id = int(argv[3]) if len(argv) > 3 else None
            for x in obj.registries(run_id=run_id, plan_id=plan_id,
                                    skill_id=skill_id):
                print(f"{x['id']}\t{x['run_id']}\t{x['plan_id'] or ''}"
                      f"\t{x['skill_id'] or ''}")
        elif cmd == "add":
            if len(argv) < 2:
                print("需要 run_id")
                return 1
            run_id = int(argv[1])
            plan_id = int(argv[2]) if len(argv) > 2 else None
            skill_id = int(argv[3]) if len(argv) > 3 else None
            print("registry id:", obj.add_registry(run_id, plan_id, skill_id))
        elif cmd == "check":
            if len(argv) < 2:
                print("需要 run_id")
                return 1
            run_id = int(argv[1])
            plan_id = int(argv[2]) if len(argv) > 2 else None
            skill_id = int(argv[3]) if len(argv) > 3 else None
            r = obj.check_schema(run_id, plan_id, skill_id)
            print("ready:", r["ready"])
            for c in r["checks"]:
                print(f"  {'✓' if c['passed'] else '✗'} {c['name']}"
                      f" — {c['detail']}")
        elif cmd == "count":
            print(obj.count())
    finally:
        obj.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
