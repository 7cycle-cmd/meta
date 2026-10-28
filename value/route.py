"""route.py — value.db CLI"""

import sys

from .api import Value

USAGE = """用法：
    python -m value.route [command]

commands:
    list [taxonomy_id]      列出值
    add <value> [taxonomy_id]  新增值
    get <value_id>          攞一個值
    count                   值數量
"""


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print(USAGE)
        return 1
    v = Value()
    try:
        cmd = argv[0]
        if cmd == "list":
            tid = int(argv[1]) if len(argv) > 1 else None
            for x in v.list(taxonomy_id=tid):
                print(f"{x['id']}\t{x['value']}\t{x['taxonomy_id'] or ''}")
        elif cmd == "add":
            if len(argv) < 2:
                print("需要 value")
                return 1
            val = argv[1]
            tid = int(argv[2]) if len(argv) > 2 else None
            print("value id:", v.add(val, tid))
        elif cmd == "get":
            vid = int(argv[1])
            print(v.get(vid))
        elif cmd == "count":
            print(v.count())
        else:
            print(USAGE)
            return 1
    finally:
        v.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())