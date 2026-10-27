"""route.py — common.db CLI"""

import sys

from .api import Common

USAGE = """用法：
    python -m common.route [command]

commands:
    actions                 列出全部動作字典
    statuses                列出全部狀態字典
    booleans                列出全部布林字典（value 0/1）
    positions               列出全部位置字典（seq 表）
    seqs                    列出全部 seq 字典
    action-id META          由名攞 action id
    status-id META          由名攞 status id
"""


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print(USAGE)
        return 1
    c = Common()
    try:
        cmd = argv[0]
        if cmd == "actions":
            for a in c.list_actions():
                print(f"[{a['id']}] {a['meta']}")
        elif cmd == "statuses":
            for s in c.list_statuses():
                print(f"[{s['id']}] {s['meta']}")
        elif cmd == "booleans":
            for b in c.list_booleans():
                print(f"[{b['id']}] value={b['value']}"
                      f" {b.get('description') or ''}")
        elif cmd in ("positions", "seqs"):
            for p in c.list_positions():
                print(f"[{p['id']}] meta={p['meta']}"
                      f" value={p.get('value') or ''}")
        elif cmd == "action-id":
            print(c.action_id(argv[1]))
        elif cmd == "status-id":
            print(c.status_id(argv[1]))
        else:
            print(USAGE)
            return 1
    finally:
        c.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
