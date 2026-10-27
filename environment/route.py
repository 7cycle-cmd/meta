"""route.py — environment.db CLI"""

import sys

from .api import Environment

USAGE = """用法：
    python -m environment.route [command]

commands:
    types                 列出環境類型
    identities [type_id]  列出實際環境
    settings              列出環境設定
    hotkeys [setting_id]  列出熱鍵對應
    buttons               列出鍵盤按鈕
    options               列出設定選項
    values [setting_id]   列出設定值
"""


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print(USAGE)
        return 1
    e = Environment()
    try:
        cmd = argv[0]
        if cmd == "types":
            for r in e.list_types():
                print(f"{r['id']}\t{r['type']}\t{r['description'] or ''}")
        elif cmd == "identities":
            tid = int(argv[1]) if len(argv) > 1 else None
            for r in e.list_identities(tid):
                print(f"{r['id']}\t[{r['type_name']}]\t{r['name']}")
        elif cmd == "settings":
            for r in e.list_settings():
                print(f"{r['id']}\t{r['setting']}\t{r['description'] or ''}")
        elif cmd == "hotkeys":
            sid = int(argv[1]) if len(argv) > 1 else None
            for r in e.list_hotkeys(sid):
                print(f"{r['id']}\t{r['setting']}\t{r['keyboard_button']}")
        elif cmd == "buttons":
            for r in e.list_buttons():
                print(f"{r['id']}\t{r['keyboard_button']}")
        elif cmd == "options":
            for r in e.list_options():
                print(f"{r['id']}\t{r['option']}")
        elif cmd == "values":
            sid = int(argv[1]) if len(argv) > 1 else None
            for r in e.list_setting_values(sid):
                print(f"{r['id']}\t{r['setting']}\t{r['option']}")
        else:
            print(USAGE)
            return 1
    finally:
        e.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
