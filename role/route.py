"""route.py — role CLI 入口

用法：
    python -m role <command>
    roles [taxonomy_id]
    add <taxonomy_id> <meta>
    count
"""

import sys

from .api import Role


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help", "help"):
        print("可用命令（role）:")
        for m in ['roles', 'add', 'count']:
            print(f"    {m}")
        return 0
    cmd = argv[0]
    if cmd not in ['roles', 'add', 'count']:
        print(f"未知命令: {cmd}")
        return 1
    obj = Role()
    try:
        if cmd == "roles":
            taxonomy_id = int(argv[1]) if len(argv) > 1 else None
            for x in obj.roles(taxonomy_id=taxonomy_id):
                print(f"{x['id']}\t{x['taxonomy_id']}\t{x['meta']}")
        elif cmd == "add":
            if len(argv) < 3:
                print("需要 taxonomy_id + meta")
                return 1
            taxonomy_id = int(argv[1])
            meta = argv[2]
            print("role id:", obj.add_role(taxonomy_id, meta))
        elif cmd == "count":
            print(obj.count())
    finally:
        obj.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())