"""route.py — register.db CLI"""

import sys

from .api import Register

USAGE = """用法：
    python -m register.route [command]

commands:
    rest-apis [module]      列出 REST API 註冊
    sync [module]           執行規則 -> 自動註冊
    reset [module]          清空註冊
    count                   註冊數量
"""


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print(USAGE)
        return 1
    reg = Register()
    try:
        cmd = argv[0]
        if cmd == "rest-apis":
            mod = argv[1] if len(argv) > 1 else None
            for x in reg.list_rest_apis(module=mod):
                print(f"{x['id']}\t{x['module']}\t{x['type']}\t{x['api']}")
        elif cmd == "sync":
            mod = argv[1] if len(argv) > 1 else None
            print(reg.sync_rest_apis(mod))
        elif cmd == "reset":
            mod = argv[1] if len(argv) > 1 else None
            print("reset:", reg.reset(mod))
        elif cmd == "count":
            print(reg.count())
        else:
            print(USAGE)
            return 1
    finally:
        reg.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
