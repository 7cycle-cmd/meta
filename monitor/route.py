"""route.py — monitor CLI"""

import sys

from .api import Monitor

USAGE = """用法：
    python -m monitor.route [command]

commands:
    refresh                更新兩張快照表（current_structure / current_taxonomy）
    current-structure      列出 structure 各實體類型當前行數
    current-taxonomy       列出 taxonomy 各樹層當前行數
"""


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print(USAGE)
        return 1
    m = Monitor()
    try:
        cmd = argv[0]
        if cmd == "refresh":
            res = m.refresh()
            print(f"current_structure：新增 {res['structure'][0]} 行 / 共 {res['structure'][1]} 類型")
            print(f"current_taxonomy：新增 {res['taxonomy'][0]} 行 / 共 {res['taxonomy'][1]} 層")
        elif cmd == "current-structure":
            for r in m.list_current_structure():
                print(f"  {r['structure_type_id']}\t{r.get('structure_type') or '?'}\t{r['total']}")
        elif cmd == "current-taxonomy":
            for r in m.list_current_taxonomy():
                print(f"  {r['tree_id']}\t{r.get('tree') or '?'}\t{r['total']}")
        else:
            print(USAGE)
            return 1
    finally:
        m.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
