"""route.py — schema CLI 入口

用法：
    python -m schema <command>
    checks
    close
"""

import sys

from .api import Schema


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help", "help"):
        print("可用命令（schema）:")
        for m in ['checks', 'close']:
            print(f"    {m}")
        return 0
    cmd = argv[0]
    if cmd not in ['checks', 'close']:
        print(f"未知命令: {cmd}")
        return 1
    obj = Schema()
    try:
        print(getattr(obj, cmd)())
    finally:
        obj.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
