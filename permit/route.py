"""route.py — permit CLI 入口

用法：
    python -m permit <command>
    permits [subject] [permit_type] [object]
    add <subject> <subject_type> <permit_type> <object> <object_type>
    can <subject> <subject_type> <permit_type> <object> <object_type>
    subjects [subject_type]
    objects [object_type]
    count
"""

import sys

from .api import Permit


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help", "help"):
        print("可用命令（permit）:")
        for m in ['permits', 'add', 'can', 'subjects', 'objects', 'count']:
            print(f"    {m}")
        return 0
    cmd = argv[0]
    if cmd not in ['permits', 'add', 'can', 'subjects', 'objects', 'count']:
        print(f"未知命令: {cmd}")
        return 1
    obj = Permit()
    try:
        if cmd == "permits":
            subject = argv[1] if len(argv) > 1 else None
            permit_type = argv[2] if len(argv) > 2 else None
            object = argv[3] if len(argv) > 3 else None
            for x in obj.permits(subject=subject, permit_type=permit_type,
                                 object=object):
                print(f"{x['id']}\t{x['subject']}\t{x['permit_type']}"
                      f"\t{x['object']}\t{x['object_type']}")
        elif cmd == "add":
            if len(argv) < 6:
                print("需要 subject + subject_type + permit_type + object + object_type")
                return 1
            rid = obj.add_permit(argv[1], argv[2], argv[3], argv[4], argv[5])
            print("permit id:", rid)
        elif cmd == "can":
            if len(argv) < 6:
                print("需要 subject + subject_type + permit_type + object + object_type")
                return 1
            print(obj.can(argv[1], argv[2], argv[3], argv[4], argv[5]))
        elif cmd == "subjects":
            for x in obj.subjects(subject_type=argv[1] if len(argv) > 1 else None):
                print(f"{x['id']}\t{x['subject']}\t{x['subject_type']}")
        elif cmd == "objects":
            for x in obj.objects(object_type=argv[1] if len(argv) > 1 else None):
                print(f"{x['id']}\t{x['object']}\t{x['object_type']}")
        elif cmd == "count":
            print(obj.count())
    finally:
        obj.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())