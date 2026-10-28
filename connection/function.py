"""function.py — connection 核心業務邏輯層

由 api.py / sql.py 搬遷：META, _discover_dbs, _fk_graph, _row_count, _get_resource_id
（7 檔標準：__init__/function/api/route/schema/sql/skill）
"""

import glob

import os

import sqlite3

from .sql import SqlStore

def _discover_dbs():
    """動態掃描所有 DB 檔案（唔硬編碼）"""
    dbs = {}
    for p in glob.glob(os.path.join(META, "*.db")):
        name = os.path.basename(p)
        if ".bak" in name:
            continue
        dbs[name] = p
    return dbs

def _fk_graph(path):
    """分析一個 DB 嘅 FK 關係圖"""
    c = sqlite3.connect(path)
    c.row_factory = sqlite3.Row
    try:
        tables = [r[0] for r in c.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
            " AND name NOT LIKE 'sqlite_%'")]
        references = {t: [] for t in tables}
        outgoing = {t: [] for t in tables}
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

def _get_resource_id(resource_name, identity_id=None):
    """透過 resource module 嘅 API 攞數字 resource_id

    唔會喺 connection 自己編號 —— 統一由 resource.db 管。
    2026-10-28：resource module 未重建（空殼）-> 返回 None（等重建）。
    """
    try:
        from resource import Resource
    except ImportError:
        return None
    r = Resource()
    try:
        return r.register(resource_name, identity_id=identity_id)
    finally:
        r.close()

META = r"C:\projects\meta"

__all__ = ['META', '_discover_dbs', '_fk_graph', '_row_count', '_get_resource_id']
