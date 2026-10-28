"""route.py — version CLI

用法：
    python -m version.route booleans      列出 yes/no 值表（0 = 否 / 1 = 是）
    python -m version.route versions      列出註冊版本（registry）
    python -m version.route registries    列出 registry 原始行
    python -m version.route values        列出版本值（value 表）
    python -m version.route githubs       列出 GitHub 操作記錄
    python -m version.route ignores       列出忽略規則（yes/no）
    python -m version.route gitignore     由 github_ignore 表生成 .gitignore
"""

import sys


def _simple(method):
    from .api import Version
    v = Version()
    try:
        for r in getattr(v, method)():
            print(r)
        return 0
    finally:
        v.close()


def _ignores():
    from .api import Version
    v = Version()
    try:
        rows = v.github_ignores()
        print(f"{len(rows)} 條忽略規則：")
        for r in rows:
            action = r.get("action")
            if not action:
                v2 = r.get("boolean_value")
                action = "with" if v2 == 1 else ("without" if v2 == 0 else "?")
            desc = r.get("description") or ""
            print(f"  {r['pattern']:<18} {action:<8} {desc}")
        return 0
    finally:
        v.close()


def _gitignore():
    from .api import Version
    v = Version()
    try:
        print(f"已生成 {v.write_gitignore()}")
        return 0
    finally:
        v.close()


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    cmd = argv[0] if argv else ""
    if cmd == "booleans":
        return _simple("booleans")
    if cmd == "versions":
        return _simple("list")
    if cmd == "registries":
        return _simple("registries")
    if cmd == "values":
        return _simple("values")
    if cmd == "githubs":
        return _simple("githubs")
    if cmd == "ignores":
        return _ignores()
    if cmd == "gitignore":
        return _gitignore()
    print("python -m version.route <booleans|versions|registries|values|"
          "githubs|ignores|gitignore>")
    return 0


if __name__ == "__main__":
    sys.exit(main())
