"""route.py — lineage.db CLI"""

import sys

from .api import Lineage

USAGE = """用法：
    python -m lineage.route [command]

commands:
    list [value_id]     列出運行時條件
    add <value_id> [run_id] [flow_id] [step_id]  記錄條件
    count               條件數量
"""


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print(USAGE)
        return 1
    lg = Lineage()
    try:
        cmd = argv[0]
        if cmd == "list":
            vid = int(argv[1]) if len(argv) > 1 else None
            for x in lg.list(value_id=vid):
                print(f"{x['id']}\t{x['value_id'] or ''}\t"
                      f"{x['run_id'] or ''}\t{x['flow_id'] or ''}\t"
                      f"{x['step_id'] or ''}\t{x['value'] or ''}")
        elif cmd == "add":
            if len(argv) < 2:
                print("需要 value_id")
                return 1
            vid = int(argv[1])
            run_id = int(argv[2]) if len(argv) > 2 else None
            flow_id = int(argv[3]) if len(argv) > 3 else None
            step_id = int(argv[4]) if len(argv) > 4 else None
            print("lineage id:", lg.add(vid, run_id, flow_id, step_id))
        elif cmd == "count":
            print(lg.count())
        else:
            print(USAGE)
            return 1
    finally:
        lg.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())