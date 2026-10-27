"""route.py — Sweep CLI"""

import sys

from .api import Sweep

USAGE = """用法：
    python -m sweep.route check          # dry-run：睇有咩可以清理（唔真刪）
    python -m sweep.route run            # 真刪 + 寫 proof
    python -m sweep.route history        # 睇清理歷史（proof）
"""


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print(USAGE)
        return 1
    c = Sweep()
    try:
        cmd = argv[0]
        if cmd == "check":
            result = c.run(dry_run=True)
            print(f"搵到 {len(result['found'])} 張殘留空表（dry-run，未刪）")
            for item in result["found"]:
                print(f"  ⚠️ {item['db']}.{item['table']}")
        elif cmd == "run":
            result = c.run(dry_run=False)
            print(f"已刪除 {result['deleted_count']} 張空表 + 寫入 proof:")
            for d in result["deleted"]:
                print(f"  ✅ {d}")
        elif cmd == "history":
            for r in c.history(50):
                print(f"  [{r['id']}] {r['run_at']} {r['db_name']}.{r['table_name']} {r['action']}: {r['reason']}")
        else:
            print(USAGE)
            return 1
    finally:
        c.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())