"""route.py — guard CLI

用法：
    python -m guard.route tokens                列出全部 token
    python -m guard.route valid TOKEN           驗證一個 token
    python -m guard.route register TOKEN MODULE_ID [FILE_ID]   登記 token
"""

import sys

from .api import Guard

USAGE = """用法：
    python -m guard.route [command]

commands:
    tokens                    列出全部 token
    valid <token>             驗證一個 token（true/false）
    register <token> <module_id> [file_id]   登記 token
    count                     統計
"""


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print(USAGE)
        return 1
    g = Guard()
    try:
        cmd = argv[0]
        if cmd == "tokens":
            for t in g.tokens():
                print(f"[{t['id']}] {t['token_id']:<25}"
                      f" module={t['module_id']}"
                      f" file={t['file_id'] or '-'}"
                      f" active={t['is_active']}")
        elif cmd == "valid":
            if len(argv) < 2:
                print("用法: valid <token>")
                return 1
            ok = g.valid(argv[1])
            print(f"{argv[1]}: {'有效' if ok else '無效'}")
            return 0 if ok else 2
        elif cmd == "register":
            if len(argv) < 3:
                print("用法: register <token> <module_id> [file_id]")
                return 1
            file_id = int(argv[3]) if len(argv) > 3 else None
            rid = g.register(argv[1], int(argv[2]), file_id)
            print(f"✅ token 已登記 id={rid}")
        elif cmd == "count":
            print(f"活躍 token: {g.count()}")
        else:
            print(USAGE)
            return 1
    finally:
        g.close()
    return 0


if __name__ == "__main__":
    main()
