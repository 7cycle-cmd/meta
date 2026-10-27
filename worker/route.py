"""route.py — worker.db CLI"""

import sys

from .api import Worker

USAGE = """用法：
    python -m worker.route [command]

commands:
    workers                列出全部代理
    abilities              列出能力字典
    identities [worker_id] 列出代理 × 能力
    add <name> [session]    新增代理
    environments           列出執行環境（Local / cloud）
    tokens [worker_id]     列出 token 配額
    add-token <worker_id> <token> [condition_id]  新增 token 配額
    usages [llm_id]        列出 token 用量（逐次，pay for use only）
"""


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print(USAGE)
        return 1
    w = Worker()
    try:
        cmd = argv[0]
        if cmd == "workers":
            for r in w.list_workers():
                print(f"{r['id']}\t{r['name']}\t{r['session_id'] or ''}\tactive={r['is_active']}")
        elif cmd == "abilities":
            for r in w.list_abilities():
                print(f"{r['id']}\t{r['ability']}\t{r['description'] or ''}")
        elif cmd == "identities":
            wid = int(argv[1]) if len(argv) > 1 else None
            for r in w.list_identities(wid):
                print(f"{r['id']}\t{r['worker']}\t{r['ability']}")
        elif cmd == "add":
            name = argv[1]
            session = argv[2] if len(argv) > 2 else None
            wid = w.add_worker(name, session)
            print(f"worker id={wid}")
        elif cmd == "environments":
            for r in w.list_environments():
                print(f"{r['id']}\t{r['meta']}\t{r['description'] or ''}")
        elif cmd == "tokens":
            wid = int(argv[1]) if len(argv) > 1 else None
            for r in w.list_tokens(wid):
                print(f"{r['id']}\t{r['worker']}\tcondition={r['condition_id']}"
                      f"\ttoken={r['token']}\tinput={r['input']}"
                      f"\toutput={r['output']}\tfee={r['fee']}")
        elif cmd == "add-token":
            wid = int(argv[1])
            token = int(argv[2])
            cond = int(argv[3]) if len(argv) > 3 else None
            tid = w.add_token(wid, token, cond)
            print(f"token id={tid}")
        elif cmd == "usages":
            lid = int(argv[1]) if len(argv) > 1 else None
            for r in w.list_token_usages(llm_id=lid):
                print(f"{r['id']}\t[r.task:{r['task_id']}]\t{r['llm']}"
                      f"\t{r['provider']}\tinput={r['input']}"
                      f"\toutput={r['output']}\tfee={r['fee']}")
        else:
            print(USAGE)
            return 1
    finally:
        w.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
