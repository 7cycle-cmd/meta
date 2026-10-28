"""route.py — rule CLI 入口

用法：
    python -m rule <command>
    rules [taxonomy_id] [flow_id]
    add <taxonomy_id> <flow_id> <step_id> [parameter]
    count
"""

import sys

from .api import Rule


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help", "help"):
        print("可用命令（rule）:")
        for m in ['rules', 'add', 'count']:
            print(f"    {m}")
        return 0
    cmd = argv[0]
    if cmd not in ['rules', 'add', 'count']:
        print(f"未知命令: {cmd}")
        return 1
    obj = Rule()
    try:
        if cmd == "rules":
            taxonomy_id = int(argv[1]) if len(argv) > 1 else None
            flow_id = int(argv[2]) if len(argv) > 2 else None
            for x in obj.rules(taxonomy_id=taxonomy_id, flow_id=flow_id):
                print(f"{x['id']}\t{x['taxonomy_id']}\t{x['flow_id']}"
                      f"\t{x['step_id']}\t{x['parameter'] or ''}")
        elif cmd == "add":
            if len(argv) < 4:
                print("需要 taxonomy_id + flow_id + step_id")
                return 1
            taxonomy_id = int(argv[1])
            flow_id = int(argv[2])
            step_id = int(argv[3])
            parameter = argv[4] if len(argv) > 4 else None
            print("rule id:", obj.add_rule(taxonomy_id, flow_id, step_id,
                                           parameter))
        elif cmd == "count":
            print(obj.count())
    finally:
        obj.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())