"""route.py — skill CLI

用法：
    python -m skill <command>
    registry                列出技能
    add <name> [resource_formula_id] [resource_structure_id]   登記技能
    count                   技能數量
"""

import sys

from .api import Skill


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help", "help"):
        print("可用命令（skill）:")
        for m in ['registry', 'add', 'count']:
            print(f"    {m}")
        return 0
    cmd = argv[0]
    if cmd not in ['registry', 'add', 'count']:
        print(f"未知命令: {cmd}")
        return 1
    obj = Skill()
    try:
        if cmd == "registry":
            for x in obj.registry():
                print(f"{x['id']}\t{x['name']}"
                      f"\t{x['resource_formula_id'] or ''}"
                      f"\t{x['resource_structure_id'] or ''}")
        elif cmd == "add":
            if len(argv) < 2:
                print("需要 name")
                return 1
            name = argv[1]
            rfi = int(argv[2]) if len(argv) > 2 else None
            rsi = int(argv[3]) if len(argv) > 3 else None
            print("skill id:", obj.register(name, rfi, rsi))
        elif cmd == "count":
            print(len(obj.registry()))
    finally:
        obj.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
