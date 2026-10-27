"""function.py — sweep 核心業務邏輯層

由 api.py / sql.py 搬遷：META, DB_FILES, _guarded, _owner_conn, _readonly, _discover_dbs, _fk_graph, _row_count, _last_active, _connection_proof
（7 檔標準：__init__/function/api/route/schema/sql/skill）
"""

import glob

import os

import sqlite3

from .sql import SqlStore

def _guarded(db_path):
    """開一條連線（2026-10-26：guard 已刪除，直接 sqlite3.connect）

    之前：帶守衛 token 嘅連線（guard.connect）
    而家：直接 connect（全站唔再需要 token）
    """
    c = sqlite3.connect(db_path)
    c.row_factory = sqlite3.Row
    return c

def _owner_conn(db_path):
    """開目標 DB 連線（2026-10-26：guard 已刪除，直接 connect）

    之前：經擁有者 module 嘅 SqlStore（guard.owner）
    而家：全站直接 sqlite3.connect，sweep 寫入目標 DB 可以直接開。
    返回 (conn, store)——store 係 dummy（有 close()，方便 caller 統一處理）。
    """
    c = sqlite3.connect(db_path)
    c.row_factory = sqlite3.Row
    return c, _DummyStore(c)

class _DummyStore:
    """dummy store：只提供 close()（真 store 已唔需要）"""
    def __init__(self, conn):
        self.conn = conn
    def close(self):
        self.conn.close()

def _readonly(db_path):
    """唯讀連線（唔需要 token，唔會寫入）"""
    c = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    c.row_factory = sqlite3.Row
    return c

def _discover_dbs():
    """動態掃描所有 DB 檔案（唔硬編碼）"""
    dbs = {}
    for p in glob.glob(os.path.join(META, "*.db")):
        name = os.path.basename(p)
        # 排除備份檔
        if ".bak" in name:
            continue
        dbs[name] = p
    return dbs

def _fk_graph(path):
    """分析一個 DB 嘅 FK 關係圖

    返回 {"tables": [...], "references": {table: [被邊啲表引用]},
          "outgoing": {table: [引用邊啲表]}}
    """
    c = sqlite3.connect(path)
    c.row_factory = sqlite3.Row
    try:
        tables = [r[0] for r in c.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
            " AND name NOT LIKE 'sqlite_%'")]
        references = {t: [] for t in tables}   # 邊啲表 FK 引用 t
        outgoing = {t: [] for t in tables}     # t FK 引用邊啲表
        for t in tables:
            try:
                fks = c.execute(f'PRAGMA foreign_key_list("{t}")').fetchall()
                for fk in fks:
                    ref = fk["table"]
                    if ref in tables:
                        references[ref].append(t)
                        outgoing[t].append(ref)
            except sqlite3.Error:
                pass
        return {"tables": tables, "references": references, "outgoing": outgoing}
    finally:
        c.close()

def _row_count(path, table):
    """數一個表嘅行數"""
    c = sqlite3.connect(path)
    try:
        return c.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
    except sqlite3.Error:
        return 0
    finally:
        c.close()

def _last_active(path, table):
    """攞一張表嘅最後活躍時間

    由表入面嘅 created_at / updated_at 欄位推斷（有邊個用邊個）。
    返回 ISO 時間字串，或者 None（表冇時間欄位 / 空表）。
    """
    c = sqlite3.connect(path)
    c.row_factory = sqlite3.Row
    try:
        cols = [r[1] for r in c.execute(f'PRAGMA table_info("{table}")')]
        # 優先 updated_at，其次 created_at
        for col in ("updated_at", "created_at"):
            if col in cols:
                r = c.execute(
                    f'SELECT MAX("{col}") AS m FROM "{table}"').fetchone()
                if r and r["m"]:
                    return r["m"]
        return None
    except sqlite3.Error:
        return None
    finally:
        c.close()

def _connection_proof(path, table, graph):
    """雙向連接證明：唔單止「有人引用」，仲要證明引用嗰邊都活躍

    返回 {"connected": bool, "proof": str}
        connected = True  -> 引用者本身有資料（活躍），連接成立
        connected = False -> 引用者都係空/孤島，連接唔成立（可以一齊 drop）
    """
    refs = graph["references"][table]
    if not refs:
        return {"connected": False, "proof": "冇人引用"}
    # 檢查每個引用者：有資料 = 活躍 = 連接成立
    alive_refs = []
    dead_refs = []
    for ref in refs:
        if _row_count(path, ref) > 0:
            alive_refs.append(ref)
        else:
            dead_refs.append(ref)
    if alive_refs:
        return {"connected": True,
                "proof": f"引用者活躍: {alive_refs}（有資料）"}
    return {"connected": False,
            "proof": f"引用者全部空/孤島: {dead_refs}，連接唔成立"}

def _find_islands(path):
    """搵孤島：空表 + 冇人 FK 引用 + 冇 FK 引用人（完全孤立）

    返回 list of table names
    """
    graph = _fk_graph(path)
    islands = []
    for t in graph["tables"]:
        if _row_count(path, t) > 0:
            continue  # 有資料，唔係孤島
        if graph["references"][t]:
            # 有人引用 -> 檢查連接證明（引用者活躍先算連接）
            proof = _connection_proof(path, t, graph)
            if proof["connected"]:
                continue  # 連接成立，唔係孤島
        if graph["outgoing"][t]:
            continue  # 佢引用人，唔係孤島
        islands.append(t)
    return islands

def _has_identity(db_name, table_name):
    """檢查一張表有冇身份證明（identity.db 有登記）

    有身份（kind + name 對應） = 證明到身份 = 唔可以刪
    冇身份 = 證明唔到 = sweep 可以 drop
    """
    try:
        from identity import Identity
        ident = Identity()
        try:
            # kind = db 名（例如 flow.db -> flow），name = 表名
            kind = db_name.replace(".db", "")
            r = ident.lookup(kind, table_name)
            return r is not None
        finally:
            ident.close()
    except Exception:
        return False

def _conn(path):
    c = sqlite3.connect(path)
    c.row_factory = sqlite3.Row
    return c

META = r"C:\projects\meta"

DB_FILES = _discover_dbs()

__all__ = ['META', 'DB_FILES', '_guarded', '_owner_conn', '_readonly', '_discover_dbs', '_fk_graph', '_row_count', '_last_active', '_connection_proof', '_find_islands', '_has_identity', '_conn']
