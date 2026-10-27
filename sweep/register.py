"""register.py — sweep 全鏈註冊樣本（skill → flow → step → schema → mapping）

2026-10-26：flow / step / mapping / task module 已刪除 ——
呢個全鏈註冊嘅依賴全部唔存在，保留檔作為歷史參考（唔可以跑）。

用法（已失效）：
    python -m sweep.register            # 全部註冊
    python -m sweep.register --verify   # 註冊後驗證
"""


def register_all(verify=True):
    """已失效：flow/step/mapping/task module 已刪（2026-10-26）"""
    return {"skill": 0, "flow": 0, "step": 0,
            "skill_map": 0, "flow_map": 0, "step_map": 0,
            "registry": 0, "schema": 0,
            "error": "flow/step/mapping/task module 已刪（2026-10-26），"
                     "全鏈註冊停用"}


def verify_all_links():
    """已失效：同上"""
    return False


if __name__ == "__main__":
    import sys
    stats = register_all(verify="--verify" in sys.argv)
    print("\n註冊統計:", stats)
    sys.exit(0)
