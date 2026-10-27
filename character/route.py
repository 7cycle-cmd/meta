"""route.py — character CLI"""


def main(argv=None):
    """CLI 入口（統一標記；具體命令由業務決定）"""
    import sys
    sys.argv = argv or sys.argv
    print("python -m character <command>  （character CLI）")
    return 0


if __name__ == "__main__":
    main()
