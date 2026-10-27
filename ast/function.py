"""function.py — ast 嘅核心業務邏輯（AST 分析）"""

import importlib.util
import os

# 標準庫 ast（module 名撞名：cwd 有 ast package，直接 load 標準庫 ast.py）
_ast = importlib.util.spec_from_file_location(
    "_stdlib_ast", os.path.join(os.path.dirname(os.__file__), "ast.py"))
_ast = importlib.util.module_from_spec(_ast)
_ast.__loader__.exec_module(_ast)


def parse_functions(source, filename="<unknown>"):
    """AST 解析 source，抽出 function（module 級 + class 級）

    返回 [{"name": ..., "class": ...}, ...]
    """
    tree = _ast.parse(source, filename=filename)
    out = []
    # class 名 -> 佢嘅 method 集合
    class_methods = {}
    for node in _ast.walk(tree):
        if isinstance(node, _ast.ClassDef):
            class_methods[node.name] = {
                child.name for child in node.body
                if isinstance(child, (_ast.FunctionDef, _ast.AsyncFunctionDef))
            }
    for node in _ast.walk(tree):
        if isinstance(node, (_ast.FunctionDef, _ast.AsyncFunctionDef)):
            if node.name.startswith("_"):
                continue
            cls = None
            for cname, methods in class_methods.items():
                if node.name in methods:
                    cls = cname
                    break
            out.append({"name": node.name, "class": cls})
    return out


def scan_file(path):
    """AST 掃描一個 .py 檔，抽出 function"""
    with open(path, "r", encoding="utf-8") as f:
        source = f.read()
    return parse_functions(source, filename=path)


def parse_formula_decorators(source, filename="<unknown>"):
    """AST 解析 source，抽出 @formula_def(name) 裝飾器位置

    返回 [{"decorator": name, "line": lineno}]
    配合 template decorator 表：內容由表話事（table-driven），
    ast 只提供「邊個 file 邊一行用咗邊個裝飾器」。
    """
    tree = _ast.parse(source, filename=filename)
    out = []
    for node in _ast.walk(tree):
        if isinstance(node, (_ast.FunctionDef, _ast.AsyncFunctionDef)):
            for deco in node.decorator_list:
                # @formula_def("name") / @formula_def('name')
                if (isinstance(deco, _ast.Call)
                        and isinstance(deco.func, _ast.Name)
                        and deco.func.id == "formula_def"
                        and deco.args
                        and isinstance(deco.args[0], _ast.Constant)
                        and isinstance(deco.args[0].value, str)):
                    out.append({"decorator": deco.args[0].value,
                                "line": node.lineno})
    return out


def scan_formula_decorators(path):
    """AST 掃描一個 .py 檔，抽出 @formula_def 裝飾器"""
    with open(path, "r", encoding="utf-8") as f:
        source = f.read()
    return parse_formula_decorators(source, filename=path)
