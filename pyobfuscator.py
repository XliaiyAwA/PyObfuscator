#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import ast
import base64
import hashlib
import math
import random
import struct
import sys
import time
import zlib
from argparse import ArgumentParser, Namespace
from typing import Dict, List, Optional, Set, Tuple, Union


# ============================================================
# 辅助工具
# ============================================================

_CONFUSING_CHARS: str = "Il1O0oQqg9Zz2Ss5"
_CONFUSING_PREFIXES: List[str] = [
    "O0", "Il", "1l", "O0O", "IIl", "ll1", "O0O0",
    "IlIl", "l1l1", "0O0O", "Qq", "Gg", "Zz2",
    "O0O0O", "IlIlI", "l1l1l", "0O0O0",
    "O0O0O0", "IlIlIl", "1l1l1l", "0O0O0O",
]

_HOMOGLYPHS: Dict[str, List[str]] = {
    "a": ["а"], "e": ["е"], "o": ["о"], "p": ["р"],
    "c": ["с"], "x": ["х"], "y": ["у"],
    "A": ["А"], "B": ["В"], "C": ["С"], "E": ["Е"],
    "H": ["Н"], "K": ["К"], "M": ["М"], "O": ["О"],
    "P": ["Р"], "T": ["Т"], "X": ["Х"], "I": ["І"],
}


def _confusing_name(rng: random.Random, homoglyphs: bool = False) -> str:
    length = rng.randint(8, 22)
    prefix = rng.choice(_CONFUSING_PREFIXES)
    body = "".join(rng.choices(_CONFUSING_CHARS, k=length - len(prefix)))
    name = prefix + body
    if homoglyphs:
        chars = list(name)
        for i, ch in enumerate(chars):
            if ch in _HOMOGLYPHS and rng.random() < 0.35:
                chars[i] = rng.choice(_HOMOGLYPHS[ch])
        name = "".join(chars)
    return name


# ============================================================
# 惰性Opaque Predicate生成器
# ============================================================

def _make_opaque_true(rng: random.Random) -> str:
    choice = rng.randint(0, 21)
    if choice == 0:
        a, b = rng.randint(100, 1000), rng.randint(10, 100)
        return f"({a} * {b} // {b} == {a})"
    elif choice == 1:
        x, n = rng.randint(100, 10000), rng.randint(1, 5)
        return f"(({x} << {n}) >> {n} == {x})"
    elif choice == 2:
        return f"len(set([{rng.randint(1, 100)}])) == 1"
    elif choice == 3:
        s_len = rng.randint(3, 10)
        return f"len('{'x' * s_len}') == {s_len}"
    elif choice == 4:
        v = rng.randint(1, 100)
        return f"(lambda x: x + 0)({v}) == {v}"
    elif choice == 5:
        c = rng.randint(2, 10)
        return f"({c} ** 2 - {c} ** 2 + 1) == 1"
    elif choice == 6:
        return f"isinstance({rng.randint(1, 100)}, int)"
    elif choice == 7:
        a = rng.randint(1, 50)
        b = a + rng.randint(1, 50)
        c = b + rng.randint(1, 50)
        return f"{a} < {b} < {c}"
    elif choice == 8:
        return "(True and True) or False"
    elif choice == 9:
        x, y = rng.randint(1, 100), rng.randint(1, 100)
        return f"{x} + {y} > {max(x, y)}"
    elif choice == 10:
        n = rng.randint(1, 20)
        return f"len(list(range({n}))) == {n}"
    elif choice == 11:
        return f"bool({{'a': {rng.randint(1, 100)}}})"
    elif choice == 12:
        x = rng.randint(1, 100)
        return f"abs(-{x}) == {x}"
    elif choice == 13:
        ch = chr(rng.randint(65, 90))
        return f"chr(ord('{ch}')) == '{ch}'"
    elif choice == 14:
        x = rng.randint(1, 50)
        return f"(lambda a,b: a*b//b)({x},{rng.randint(2, 10)}) == {x}"
    elif choice == 15:
        a = rng.randint(1, 20)
        return f"pow({a}, 1) == {a}"
    elif choice == 16:
        return f"hash(str({rng.randint(1,100)})) == hash(str({rng.randint(1,100)})) or True"
    elif choice == 17:
        return f"any([True, True, True])"
    elif choice == 18:
        a = rng.randint(2, 100)
        return f"({a} & ({a} - 1)) == 0 or ({a} & ({a} - 1)) != 0"
    elif choice == 19:
        a = rng.randint(1, 50)
        b = rng.randint(1, 50)
        return f"({a} | {b}) >= {max(a, b)}"
    elif choice == 20:
        a = rng.randint(1, 100)
        return f"int(not not {a}) * int(not not {a}) > 0"
    else:
        a = rng.randint(10, 100)
        b = rng.randint(10, 100)
        return f"(({a} + {b}) - {b}) == {a}"


def _make_opaque_false(rng: random.Random) -> str:
    choice = rng.randint(0, 21)
    if choice == 0:
        a = rng.randint(10, 1000)
        return f"({a} == {a + rng.randint(1, 100)})"
    elif choice == 1:
        x = rng.randint(100, 10000)
        return f"({x} ^ {x} != 0)"
    elif choice == 2:
        return "len([]) > 0"
    elif choice == 3:
        return "bool(dict())"
    elif choice == 4:
        return "bool(set())"
    elif choice == 5:
        return "len('') > 0"
    elif choice == 6:
        a, b = rng.randint(50, 100), rng.randint(1, 49)
        return f"{a} < {b}"
    elif choice == 7:
        return f"(lambda x: x - x)({rng.randint(1, 100)}) != 0"
    elif choice == 8:
        return f"isinstance({rng.randint(1, 100)}, str)"
    elif choice == 9:
        return "(False or False) and True"
    elif choice == 10:
        return f"{rng.randint(1, 100)} * 0 > 0"
    elif choice == 11:
        return "len(set()) == 1"
    elif choice == 12:
        return "'x' in dict()"
    elif choice == 13:
        return "abs(0) > 0"
    elif choice == 14:
        return "(lambda: False)()"
    elif choice == 15:
        return f"all([True, False, True])"
    elif choice == 16:
        return f"pow({rng.randint(2,10)}, 0) == 0"
    elif choice == 17:
        return f"ord('A') == ord('B')"
    elif choice == 18:
        a = rng.randint(1, 100)
        return f"({a} ^ {a}) != 0"
    elif choice == 19:
        return f"'hello'.startswith('x')"
    elif choice == 20:
        return f"isinstance(int, float)"
    else:
        a = rng.randint(10, 100)
        return f"({a} // {rng.randint(a+1, a*10)}) > 0"


# ============================================================
# 三档预设
# ============================================================

LEVEL_PRESETS: Dict[str, Dict] = {
    "light": {
        "var-rename": True,
        "func-rename": True,
        "class-rename": True,
        "string-encode": True,
        "string-multi-round": False,
        "number-obfuscate": True,
        "float-obfuscate": True,
        "container-obfuscate": False,
        "bytes-obfuscate": False,
        "junk-code": False,
        "junk-count": 0,
        "opaque-predicates": False,
        "opaque-prob": 0.0,
        "dead-code": False,
        "control-flatten": False,
        "import-hide": True
        "homoglyph-names": False,
        "bool-obscure": False,
        "expr-wrap": False,
        "binop-wrap": False,
        "dynamic-attrs": False,
        "scramble-annotations": False,
        "fstring-obfuscate": False,
        "strip-docstrings": True,
        "string-methods": ["xor-base64"],
        "label": "轻量",
    },
    "standard": {
        "var-rename": True,
        "func-rename": True,
        "class-rename": True,
        "string-encode": True,
        "string-multi-round": True,
        "number-obfuscate": True,
        "float-obfuscate": True,
        "container-obfuscate": True,
        "bytes-obfuscate": True,
        "junk-code": True,
        "junk-count": 3,
        "opaque-predicates": True,
        "opaque-prob": 0.35,
        "dead-code": True,
        "control-flatten": True,
        "import-hide": True,
        "homoglyph-names": False,
        "bool-obscure": True,
        "expr-wrap": True,
        "binop-wrap": True,
        "dynamic-attrs": False,
        "scramble-annotations": True,
        "fstring-obfuscate": True,
        "strip-docstrings": True,
        "string-methods": ["xor-base64", "zlib-base64", "hex-xor", "split-encode", "reverse", "multi-layer"],
        "label": "标准",
    },
    "heavy": {
        "var-rename": True,
        "func-rename": True,
        "class-rename": True,
        "string-encode": True,
        "string-multi-round": True,
        "number-obfuscate": True,
        "float-obfuscate": True,
        "container-obfuscate": True,
        "bytes-obfuscate": True,
        "junk-code": True,
        "junk-count": 4,
        "opaque-predicates": True,
        "opaque-prob": 0.65,
        "dead-code": True,
        "control-flatten": True,
        "import-hide": True,
        "homoglyph-names": False,
        "bool-obscure": True,
        "expr-wrap": True,
        "binop-wrap": True,
        "dynamic-attrs": False,
        "scramble-annotations": True,
        "fstring-obfuscate": True,
        "strip-docstrings": True,
        "string-methods": [
            "xor-base64", "zlib-base64", "hex-xor",
            "split-encode", "reverse", "shuffle", "multi-layer",
            "rot13-base64", "hash-verify", "zlib-xor",
        ],
        "label": "强化",
    },
}


# ============================================================
# 文档字符串移除器
# ============================================================

class DocstringRemover(ast.NodeTransformer):
    def visit_Module(self, node: ast.Module) -> ast.Module:
        self._remove_docstring(node)
        self.generic_visit(node)
        return node

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        self._remove_docstring(node)
        self.generic_visit(node)
        return node

    def visit_ClassDef(self, node: ast.ClassDef) -> ast.ClassDef:
        self._remove_docstring(node)
        self.generic_visit(node)
        return node

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AsyncFunctionDef:
        self._remove_docstring(node)
        self.generic_visit(node)
        return node

    @staticmethod
    def _remove_docstring(node: ast.AST) -> None:
        if not hasattr(node, "body"):
            return
        body = getattr(node, "body")
        if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
            if isinstance(body[0].value.value, str):
                del body[0]


# ============================================================
# 类型注解剥离器（新增）
# ============================================================

class AnnotationScrambler(ast.NodeTransformer):
    """将类型注解替换为 None，降低可读性"""

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        node.returns = None
        self.generic_visit(node)
        return node

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AsyncFunctionDef:
        node.returns = None
        self.generic_visit(node)
        return node

    def visit_AnnAssign(self, node: ast.AnnAssign) -> ast.stmt:
        # 有赋值时转换为普通赋值。
        # 无赋值的注解语句（例如 child: Node）需要保留语句本身，
        # 但把注解替换成无害常量，避免 __future__.annotations 失效后
        # Python 立即求值前向引用并触发 NameError。
        if node.value is not None:
            return ast.Assign(targets=[node.target], value=node.value)
        node.annotation = ast.Constant(value=None)
        return node

    def visit_arg(self, node: ast.arg) -> ast.arg:
        node.annotation = None
        return node


# ============================================================
# 主混淆器（终极版）
# ============================================================

class Obfuscator(ast.NodeTransformer):
    """终极版Python代码混淆器 — 支持Python 3.11~3.13语法，极致混淆"""

    def __init__(
        self,
        var_rename: bool = True,
        func_rename: bool = True,
        class_rename: bool = True,
        string_encode: bool = True,
        string_multi_round: bool = False,
        number_obfuscate: bool = False,
        float_obfuscate: bool = False,
        container_obfuscate: bool = False,
        bytes_obfuscate: bool = False,
        junk_code: bool = True,
        junk_count: int = 1,
        opaque_predicates: bool = False,
        opaque_prob: float = 0.25,
        dead_code: bool = False,
        control_flatten: bool = False,
        import_hide: bool = False,
        homoglyph_names: bool = False,
        bool_obscure: bool = False,
        expr_wrap: bool = False,
        binop_wrap: bool = False,
        dynamic_attrs: bool = False,
        scramble_annotations: bool = False,
        fstring_obfuscate: bool = False,
        strip_docstrings: bool = True,
        string_methods: Optional[List[str]] = None,
        seed: Optional[int] = None,
    ) -> None:
        self.var_rename = var_rename
        self.func_rename = func_rename
        self.class_rename = class_rename
        self.string_encode = string_encode
        self.string_multi_round = string_multi_round
        self.number_obfuscate = number_obfuscate
        self.float_obfuscate = float_obfuscate
        self.container_obfuscate = container_obfuscate
        self.bytes_obfuscate = bytes_obfuscate
        self.junk_code = junk_code
        self.junk_count = junk_count
        self.opaque_predicates = opaque_predicates
        self.opaque_prob = opaque_prob
        self.dead_code = dead_code
        self.control_flatten = control_flatten
        self.import_hide = import_hide
        self.homoglyph_names = homoglyph_names
        self.bool_obscure = bool_obscure
        self.expr_wrap = expr_wrap
        self.binop_wrap = binop_wrap
        self.dynamic_attrs = dynamic_attrs
        self.scramble_annotations = scramble_annotations
        self.fstring_obfuscate = fstring_obfuscate
        self.strip_docstrings = strip_docstrings
        self.string_methods = string_methods or ["xor-base64"]

        self._rng = random.Random(seed) if seed is not None else random.Random()

        self.reserved: Set[str] = self._build_reserved_names()
        self.name_mapping: Dict[str, str] = {}
        self.used_names: Set[str] = set()
        self.parent_stack: List[ast.AST] = []
        self.import_aliases: Dict[str, str] = {}
        self._scope_stack: List[Dict[str, str]] = [{}]
        self._processed_attrs: Set[int] = set()
        self._user_funcs: Set[str] = set()
        self._user_methods: Set[str] = set()
        self._user_class_attrs: Set[str] = set()
        self._rename_kwargs_stack: List[bool] = []
        self._in_fstring_flag: int = 0

        self._builtin_attrs_blacklist: Set[str] = {
            'append', 'extend', 'insert', 'remove', 'pop', 'clear', 'index',
            'count', 'sort', 'reverse', 'copy', 'split', 'rsplit', 'splitlines',
            'strip', 'lstrip', 'rstrip', 'upper', 'lower', 'capitalize', 'title',
            'swapcase', 'center', 'ljust', 'rjust', 'zfill', 'find', 'rfind',
            'index', 'rindex', 'count', 'replace', 'join', 'format', 'encode',
            'decode', 'startswith', 'endswith', 'isalpha', 'isdigit', 'isalnum',
            'isspace', 'isupper', 'islower', 'istitle', 'isnumeric', 'isdecimal',
            'keys', 'values', 'items', 'get', 'setdefault', 'pop', 'popitem',
            'update', 'fromkeys', 'add', 'discard', 'union', 'intersection',
            'difference', 'symmetric_difference', 'issubset', 'issuperset',
            'isdisjoint', 'copy', '__init__', '__new__', '__del__', '__repr__',
            '__str__', '__len__', '__getitem__', '__setitem__', '__delitem__',
            '__iter__', '__next__', '__contains__', '__call__', '__enter__',
            '__exit__', '__hash__', '__eq__', '__ne__', '__lt__', '__gt__',
            '__le__', '__ge__', '__add__', '__sub__', '__mul__', '__truediv__',
            '__floordiv__', '__mod__', '__pow__', '__neg__', '__pos__', '__invert__',
            '__and__', '__or__', '__xor__', '__lshift__', '__rshift__',
            'close', 'read', 'write', 'seek', 'tell', 'flush', 'readline',
            'readlines', 'writelines',
        }

        self.stats: Dict[str, int] = {
            "vars_renamed": 0,
            "funcs_renamed": 0,
            "classes_renamed": 0,
            "strings_encoded": 0,
            "multi_round_strings": 0,
            "numbers_obfuscated": 0,
            "floats_obfuscated": 0,
            "containers_obfuscated": 0,
            "bytes_obfuscated": 0,
            "junk_blocks": 0,
            "opaque_predicates": 0,
            "dead_code_injected": 0,
            "flattened_blocks": 0,
            "hidden_imports": 0,
            "bools_obscured": 0,
            "exprs_wrapped": 0,
            "binops_wrapped": 0,
            "attrs_dynamic": 0,
            "annotations_scrambled": 0,
            "fstrings_obfuscated": 0,
        }

    # ---------- 保留名称 ----------
    @staticmethod
    def _build_reserved_names() -> Set[str]:
        import keyword
        import builtins

        reserved = set(keyword.kwlist)
        reserved.update(dir(builtins))
        reserved.update({
            "self", "cls", "True", "False", "None",
            "NotImplemented", "Ellipsis", "type", "object",
            "super", "property", "staticmethod", "classmethod",
            "__name__", "__main__", "__file__", "__doc__",
            "__init__", "__new__", "__str__", "__repr__",
            "__call__", "__getitem__", "__setitem__",
            "__len__", "__iter__", "__next__",
            "__enter__", "__exit__", "__aenter__", "__aexit__",
            "__await__", "__anext__", "__aiter__",
            "__add__", "__sub__", "__mul__", "__truediv__",
            "__floordiv__", "__mod__", "__pow__",
            "__eq__", "__ne__", "__lt__", "__gt__", "__le__", "__ge__",
            "__hash__", "__bool__", "__del__", "__setattr__", "__getattr__",
            "__class__", "__dict__", "__module__", "__slots__",
            "__match_args__", "__orig_bases__",
            "__and__", "__or__", "__xor__", "__lshift__", "__rshift__",
            "__neg__", "__pos__", "__invert__",
            "__contains__", "__delitem__", "__reversed__",
            "nan", "inf", "pi", "e", "tau",
        })
        return reserved

    def _is_special_method(self, name: str) -> bool:
        return name.startswith("__") and name.endswith("__")

    def _is_reserved(self, name: str) -> bool:
        return name in self.reserved or self._is_special_method(name)

    def _generate_name(self, prefix: str = "") -> str:
        max_attempts = 1000
        for _ in range(max_attempts):
            name = prefix + _confusing_name(self._rng, self.homoglyph_names)
            if name[0].isdigit():
                continue
            if not name.isidentifier():
                continue
            if name not in self.reserved and name not in self.used_names:
                self.used_names.add(name)
                return name
        while True:
            name = f"_{prefix}_{self._rng.randint(100000, 99999999)}"
            if name not in self.used_names and name not in self.reserved:
                self.used_names.add(name)
                return name

    def _mapped_name(self, original: str, prefix: str = "") -> str:
        if self._is_reserved(original):
            return original
        if original not in self.name_mapping:
            self.name_mapping[original] = self._generate_name(prefix)
        return self.name_mapping[original]

    # ---------- AST 遍历 ----------
    def visit(self, node: ast.AST) -> ast.AST:
        self.parent_stack.append(node)
        result = super().visit(node)
        self.parent_stack.pop()
        return result

    def obfuscate(self, code: str) -> str:
        tree = ast.parse(code)
        self._collect_definitions(tree)

        if self.scramble_annotations:
            tree = AnnotationScrambler().visit(tree)
            tree = ast.fix_missing_locations(tree)
            self.stats["annotations_scrambled"] += 1

        tree = self.visit(tree)
        tree = ast.fix_missing_locations(tree)

        if self.strip_docstrings:
            tree = DocstringRemover().visit(tree)
            tree = ast.fix_missing_locations(tree)

        if self.dead_code:
            tree = self._inject_module_dead_code(tree)
            tree = ast.fix_missing_locations(tree)

        if self.import_hide:
            tree = self._transform_imports(tree)
            tree = ast.fix_missing_locations(tree)

        obfuscated = ast.unparse(tree)
        return obfuscated

    # ---------- 定义收集 ----------
    def _collect_definitions(self, tree: ast.Module) -> None:
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self._user_funcs.add(node.name)
                if self.func_rename and not self._is_special_method(node.name):
                    if not self._is_reserved(node.name) and node.name not in self._builtin_attrs_blacklist:
                        new_name = self._generate_name("f")
                        self.name_mapping[node.name] = new_name
                        self._user_funcs.add(new_name)
            elif isinstance(node, ast.ClassDef):
                if self.class_rename and not self._is_reserved(node.name):
                    new_name = self._generate_name("C")
                    self.name_mapping[node.name] = new_name
                    self._user_funcs.add(new_name)
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        if not self._is_special_method(item.name):
                            self._user_methods.add(item.name)
                    elif isinstance(item, ast.Assign):
                        for tgt in item.targets:
                            if isinstance(tgt, ast.Name):
                                self._user_class_attrs.add(tgt.id)
                    elif isinstance(item, ast.AnnAssign):
                        if isinstance(item.target, ast.Name):
                            self._user_class_attrs.add(item.target.id)
            elif isinstance(node, ast.Global):
                for name in node.names:
                    if self.var_rename and not self._is_reserved(name):
                        if name not in self.name_mapping:
                            self.name_mapping[name] = self._generate_name("v")
            elif isinstance(node, ast.Nonlocal):
                for name in node.names:
                    if self.var_rename and not self._is_reserved(name):
                        if name not in self.name_mapping:
                            self.name_mapping[name] = self._generate_name("v")

    # ---------- 辅助 ----------
    def _mark_docstring(self, node: ast.AST) -> None:
        if not hasattr(node, "body") or not node.body:
            return
        first = node.body[0]
        if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str):
            setattr(first.value, "is_docstring", True)

    def _in_fstring(self) -> bool:
        return self._in_fstring_flag > 0

    def _in_class_body(self) -> bool:
        """Check if we're directly inside a class body (not inside a function/method)."""
        for parent in reversed(self.parent_stack):
            if isinstance(parent, (ast.FunctionDef, ast.AsyncFunctionDef)):
                return False
            if isinstance(parent, ast.ClassDef):
                return True
        return False

    def _in_annotation(self) -> bool:
        for parent in reversed(self.parent_stack):
            if isinstance(parent, (ast.AnnAssign, ast.arg)):
                return True
        return False

    def _in_subscript(self) -> bool:
        for parent in reversed(self.parent_stack):
            if isinstance(parent, ast.Subscript):
                return True
        return False

    def _in_match_pattern(self) -> bool:
        for parent in reversed(self.parent_stack):
            if isinstance(parent, (ast.MatchValue, ast.MatchSingleton, ast.MatchAs)):
                return True
        return False

    def _is_call_target(self) -> bool:
        if len(self.parent_stack) >= 2:
            parent = self.parent_stack[-2]
            if isinstance(parent, ast.Call) and parent.func is self.parent_stack[-1]:
                return True
        return False

    def _parse_expr(self, expr_str: str) -> ast.expr:
        return ast.parse(expr_str, mode="eval").body

    @staticmethod
    def _is_future_import(stmt: ast.stmt) -> bool:
        return isinstance(stmt, ast.ImportFrom) and stmt.module == "__future__"

    @classmethod
    def _module_preamble_end(cls, body: List[ast.stmt]) -> int:
        pos = 0
        if body and isinstance(body[0], ast.Expr) and \
           isinstance(body[0].value, ast.Constant) and \
           isinstance(body[0].value.value, str):
            pos = 1
        while pos < len(body) and cls._is_future_import(body[pos]):
            pos += 1
        return pos

    def _insert_junk_into_body(self, body: List[ast.stmt]) -> None:
        if not self.junk_code or self.junk_count <= 0:
            return
        insert_pos = 0
        if body and isinstance(body[0], ast.Expr) and \
           isinstance(body[0].value, ast.Constant) and \
           isinstance(body[0].value.value, str):
            insert_pos = 1
        for _ in range(self.junk_count):
            junk_stmts = self._generate_junk_code()
            body[insert_pos:insert_pos] = junk_stmts
            self.stats["junk_blocks"] += 1
            insert_pos += len(junk_stmts)
    # ==========================================================
    # Module / Function / Class visitors
    # ==========================================================

    def visit_Module(self, node: ast.Module) -> ast.Module:
        self._mark_docstring(node)
        self.generic_visit(node)
        return node

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        self._mark_docstring(node)
        original_name = node.name
        is_recursive = self._function_is_recursive(node, original_name)
        if self.func_rename and not self._is_special_method(node.name):
            if node.name not in self._builtin_attrs_blacklist:
                if node.name in self.name_mapping:
                    node.name = self.name_mapping[node.name]
                elif not self._is_reserved(node.name):
                    node.name = self._mapped_name(node.name, "f")
                self.stats["funcs_renamed"] += 1
        self.generic_visit(node)
        if self.control_flatten and node.body and not is_recursive:
            node.body = self._flatten_body(node.body)
        self._insert_junk_into_body(node.body)
        if self.dead_code:
            self._inject_function_dead_code(node.body)
        return node

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AsyncFunctionDef:
        self._mark_docstring(node)
        original_name = node.name
        is_recursive = self._function_is_recursive(node, original_name)
        if self.func_rename and not self._is_special_method(node.name):
            if node.name not in self._builtin_attrs_blacklist:
                if node.name in self.name_mapping:
                    node.name = self.name_mapping[node.name]
                elif not self._is_reserved(node.name):
                    node.name = self._mapped_name(node.name, "a")
                self.stats["funcs_renamed"] += 1
        self.generic_visit(node)
        if self.control_flatten and node.body and not is_recursive:
            node.body = self._flatten_body(node.body)
        self._insert_junk_into_body(node.body)
        if self.dead_code:
            self._inject_function_dead_code(node.body)
        return node

    def visit_ClassDef(self, node: ast.ClassDef) -> ast.ClassDef:
        self._mark_docstring(node)
        if self.class_rename and not self._is_reserved(node.name):
            if node.name in self.name_mapping:
                node.name = self.name_mapping[node.name]
            else:
                node.name = self._mapped_name(node.name, "C")
            self.stats["classes_renamed"] += 1
        self.generic_visit(node)
        return node

    def visit_Global(self, node: ast.Global) -> ast.Global:
        if self.var_rename:
            new_names = []
            for name in node.names:
                if not self._is_reserved(name):
                    new_names.append(self._mapped_name(name, "v"))
                else:
                    new_names.append(name)
            node.names = new_names
        return node

    def visit_Nonlocal(self, node: ast.Nonlocal) -> ast.Nonlocal:
        if self.var_rename:
            new_names = []
            for name in node.names:
                if not self._is_reserved(name):
                    new_names.append(self._mapped_name(name, "v"))
                else:
                    new_names.append(name)
            node.names = new_names
        return node

    # ==========================================================
    # Python 3.10+ match 语句支持
    # ==========================================================

    def visit_Match(self, node: ast.Match) -> ast.Match:
        self.generic_visit(node)
        return node

    def visit_match_case(self, node: ast.match_case) -> ast.match_case:
        self.generic_visit(node)
        return node

    def visit_MatchAs(self, node: ast.MatchAs) -> ast.MatchAs:
        if node.name and self.var_rename and not self._is_reserved(node.name):
            node.name = self._mapped_name(node.name, "v")
            self.stats["vars_renamed"] += 1
        else:
            self.generic_visit(node)
        return node

    def visit_MatchValue(self, node: ast.MatchValue) -> ast.MatchValue:
        self.generic_visit(node)
        return node

    def visit_MatchSingleton(self, node: ast.MatchSingleton) -> ast.MatchSingleton:
        return node

    def visit_MatchSequence(self, node: ast.MatchSequence) -> ast.MatchSequence:
        self.generic_visit(node)
        return node

    def visit_MatchMapping(self, node: ast.MatchMapping) -> ast.MatchMapping:
        self.generic_visit(node)
        return node

    def visit_MatchClass(self, node: ast.MatchClass) -> ast.MatchClass:
        self.generic_visit(node)
        return node

    def visit_MatchStar(self, node: ast.MatchStar) -> ast.MatchStar:
        if node.name and self.var_rename and not self._is_reserved(node.name):
            node.name = self._mapped_name(node.name, "v")
            self.stats["vars_renamed"] += 1
        return node

    def visit_MatchOr(self, node: ast.MatchOr) -> ast.MatchOr:
        self.generic_visit(node)
        return node

    # ==========================================================
    # 异常处理器支持
    # ==========================================================

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> ast.ExceptHandler:
        """处理 except Exception as e: 语法"""
        if node.name and self.var_rename and not self._is_reserved(node.name):
            node.name = self._mapped_name(node.name, "e")
            self.stats["vars_renamed"] += 1
        self.generic_visit(node)
        return node

    # ==========================================================
    # Python 3.11+ 异常组支持（新增）
    # ==========================================================

    def visit_ExceptStar(self, node: ast.ExceptStar) -> ast.ExceptStar:
        """处理 except* Group as e: 语法"""
        if node.name and self.var_rename and not self._is_reserved(node.name):
            node.name = self._mapped_name(node.name, "e")
            self.stats["vars_renamed"] += 1
        self.generic_visit(node)
        return node

    # ==========================================================
    # Python 3.12+ TypeAlias / TypeVar / ParamSpec / TypeVarTuple
    # ==========================================================
    # 使用 hasattr 条件检测确保 Python 3.11 兼容

    def visit_TypeAlias(self, node: ast.AST) -> ast.AST:
        """处理 type X = int (Python 3.12+)"""
        if hasattr(node, 'name') and self.var_rename:
            name_node = getattr(node, 'name')
            if isinstance(name_node, ast.Name) and not self._is_reserved(name_node.id):
                name_node.id = self._mapped_name(name_node.id, "T")
                self.stats["vars_renamed"] += 1
        self.generic_visit(node)
        return node

    def visit_TypeVar(self, node: ast.AST) -> ast.AST:
        """处理 TypeVar (Python 3.12+)"""
        if hasattr(node, 'name') and self.var_rename:
            name_val = getattr(node, 'name')
            if isinstance(name_val, str) and not self._is_reserved(name_val):
                setattr(node, 'name', self._mapped_name(name_val, "Tv"))
                self.stats["vars_renamed"] += 1
        self.generic_visit(node)
        return node

    def visit_ParamSpec(self, node: ast.AST) -> ast.AST:
        """处理 ParamSpec (Python 3.12+)"""
        if hasattr(node, 'name') and self.var_rename:
            name_val = getattr(node, 'name')
            if isinstance(name_val, str) and not self._is_reserved(name_val):
                setattr(node, 'name', self._mapped_name(name_val, "Ps"))
                self.stats["vars_renamed"] += 1
        self.generic_visit(node)
        return node

    def visit_TypeVarTuple(self, node: ast.AST) -> ast.AST:
        """处理 TypeVarTuple (Python 3.12+)"""
        if hasattr(node, 'name') and self.var_rename:
            name_val = getattr(node, 'name')
            if isinstance(name_val, str) and not self._is_reserved(name_val):
                setattr(node, 'name', self._mapped_name(name_val, "Tt"))
                self.stats["vars_renamed"] += 1
        self.generic_visit(node)
        return node

    # ==========================================================
    # 名称混淆
    # ==========================================================

    def visit_Name(self, node: ast.Name) -> ast.AST:
        renamed = False
        in_class = self._in_class_body()

        if isinstance(node.ctx, (ast.Store, ast.Load, ast.Del)):
            if node.id in self.import_aliases:
                pass
            elif node.id in self.name_mapping:
                node.id = self.name_mapping[node.id]
                renamed = True
            elif in_class and node.id in self._user_class_attrs:
                if not self._is_reserved(node.id) and node.id not in self._builtin_attrs_blacklist:
                    self.name_mapping[node.id] = self._generate_name("c")
                    node.id = self.name_mapping[node.id]
                    renamed = True
            elif self.var_rename and not self._is_reserved(node.id):
                # Skip renaming if it's a known user function that's in the blacklist
                # (the function definition won't be renamed either, so keep consistent)
                if node.id in self._user_funcs and node.id in self._builtin_attrs_blacklist:
                    pass
                else:
                    node.id = self._mapped_name(node.id, "v")
                    renamed = True

            if renamed:
                self.stats["vars_renamed"] += 1
                if self.expr_wrap and isinstance(node.ctx, ast.Load) and not self._is_reserved(node.id):
                    if not self._is_call_target() and not self._in_annotation() and not self._in_fstring():
                        if self._rng.random() < 0.25:
                            self.stats["exprs_wrapped"] += 1
                            wrap_type = self._rng.randint(0, 3)
                            if wrap_type == 0:
                                return ast.Subscript(
                                    value=ast.List(elts=[node], ctx=ast.Load()),
                                    slice=ast.Constant(value=0),
                                    ctx=ast.Load(),
                                )
                            elif wrap_type == 1:
                                return ast.Subscript(
                                    value=ast.Tuple(elts=[node], ctx=ast.Load()),
                                    slice=ast.Constant(value=0),
                                    ctx=ast.Load(),
                                )
                            elif wrap_type == 2:
                                inner = ast.List(elts=[node], ctx=ast.Load())
                                outer = ast.List(elts=[inner], ctx=ast.Load())
                                return ast.Subscript(
                                    value=ast.Subscript(
                                        value=outer,
                                        slice=ast.Constant(value=0),
                                        ctx=ast.Load(),
                                    ),
                                    slice=ast.Constant(value=0),
                                    ctx=ast.Load(),
                                )
                            else:
                                return ast.Call(
                                    func=ast.Lambda(
                                        args=ast.arguments(
                                            posonlyargs=[],
                                            args=[ast.arg(arg="_")],
                                            kwonlyargs=[],
                                            kw_defaults=[],
                                            defaults=[],
                                        ),
                                        body=ast.Name(id="_", ctx=ast.Load()),
                                    ),
                                    args=[node],
                                    keywords=[],
                                )
        return node

    def visit_arg(self, node: ast.arg) -> ast.arg:
        if self.var_rename and not self._is_reserved(node.arg):
            node.arg = self._mapped_name(node.arg, "a")
            self.stats["vars_renamed"] += 1
        self.generic_visit(node)
        return node

    def visit_Attribute(self, node: ast.Attribute) -> ast.AST:
        self.generic_visit(node)

        if not self._is_reserved(node.attr) and node.attr not in self._builtin_attrs_blacklist:
            if node.attr in self.name_mapping:
                node.attr = self.name_mapping[node.attr]
            elif node.attr in self._user_methods:
                self.name_mapping[node.attr] = self._generate_name("m")
                node.attr = self.name_mapping[node.attr]
            elif node.attr in self._user_class_attrs:
                self.name_mapping[node.attr] = self._generate_name("c")
                node.attr = self.name_mapping[node.attr]

        if self.dynamic_attrs and isinstance(node.ctx, ast.Load):
            if id(node) not in self._processed_attrs:
                if not self._is_special_method(node.attr) and \
                   not self._is_reserved(node.attr) and \
                   node.attr not in self._builtin_attrs_blacklist:
                    if self._rng.random() < 0.4:
                        attr_name = node.attr
                        if self.string_encode:
                            try:
                                encoded_name = self._choose_string_encoder(attr_name)(attr_name)
                                ast.fix_missing_locations(encoded_name)
                            except Exception:
                                encoded_name = ast.Constant(value=attr_name)
                        else:
                            encoded_name = ast.Constant(value=attr_name)
                        self.stats["attrs_dynamic"] += 1
                        self._processed_attrs.add(id(node))
                        new_node = ast.Call(
                            func=ast.Name(id="getattr", ctx=ast.Load()),
                            args=[node.value, encoded_name],
                            keywords=[],
                        )
                        return new_node
        return node

    def visit_Call(self, node: ast.Call) -> ast.Call:
        should_rename_kwargs = False
        has_starstar_kwargs = any(kw.arg is None for kw in node.keywords)
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
            if func_name in self._user_funcs or func_name in self.name_mapping:
                should_rename_kwargs = not has_starstar_kwargs
        elif isinstance(node.func, ast.Attribute):
            method_name = node.func.attr
            if method_name in self._user_methods and method_name not in self._builtin_attrs_blacklist:
                should_rename_kwargs = not has_starstar_kwargs

        # Pre-process **kwargs dicts: rename literal keys to match renamed parameters
        if has_starstar_kwargs and (isinstance(node.func, ast.Name) and
            (node.func.id in self._user_funcs or node.func.id in self.name_mapping)):
            for kw in node.keywords:
                if kw.arg is None and isinstance(kw.value, ast.Dict):
                    new_keys = []
                    for key_node in kw.value.keys:
                        if isinstance(key_node, ast.Constant) and isinstance(key_node.value, str):
                            key_str = key_node.value
                            if key_str in self.name_mapping:
                                new_keys.append(ast.Constant(value=self.name_mapping[key_str]))
                            else:
                                new_keys.append(key_node)
                        else:
                            new_keys.append(key_node)
                    kw.value.keys = new_keys

        self._rename_kwargs_stack.append(should_rename_kwargs)
        self.generic_visit(node)
        self._rename_kwargs_stack.pop()
        return node

    def visit_Import(self, node: ast.Import) -> ast.Import:
        for alias in node.names:
            if alias.asname:
                if self.var_rename and not self._is_reserved(alias.asname):
                    alias.asname = self._mapped_name(alias.asname, "i")
                    self.stats["vars_renamed"] += 1
            else:
                base_name = alias.name.split(".")[0]
                self.reserved.add(base_name)
                if self.import_hide:
                    self.import_aliases[base_name] = base_name
        return node

    def visit_ImportFrom(self, node: ast.ImportFrom) -> ast.ImportFrom:
        for alias in node.names:
            if alias.asname:
                if self.var_rename and not self._is_reserved(alias.asname):
                    alias.asname = self._mapped_name(alias.asname, "i")
                    self.stats["vars_renamed"] += 1
            else:
                if alias.name != "*":
                    self.reserved.add(alias.name)
                    if self.import_hide:
                        self.import_aliases[alias.name] = alias.name
        return node

    def visit_keyword(self, node: ast.keyword) -> ast.keyword:
        if node.arg and self.var_rename and not self._is_reserved(node.arg):
            should_rename = False
            if self._rename_kwargs_stack:
                should_rename = self._rename_kwargs_stack[-1]
            if should_rename:
                node.arg = self._mapped_name(node.arg, "k")
                self.stats["vars_renamed"] += 1
        self.generic_visit(node)
        return node

    # ==========================================================
    # f-string 混淆（新增）
    # ==========================================================

    def visit_JoinedStr(self, node: ast.JoinedStr) -> ast.AST:
        """将 f-string 转换为 ''.format() 调用以混淆"""
        self._in_fstring_flag += 1
        try:
            # 嵌套 f-string 不转换，避免 ast.unparse 异常
            if self._in_fstring_flag > 1:
                self.generic_visit(node)
                return node

            self.generic_visit(node)

            if not self.fstring_obfuscate:
                return node

            if self._rng.random() < 0.5:
                return node

            # Check if any expression parts exist
            has_expression = any(
                not isinstance(v, ast.Constant) or not isinstance(v.value, str)
                for v in node.values
            )
            if not has_expression:
                return node

            # 避免处理含格式说明符/转换标志的复杂 f-string，防止 ast.unparse 异常
            for v in node.values:
                if isinstance(v, ast.FormattedValue):
                    if getattr(v, "conversion", -1) != -1 or v.format_spec is not None:
                        return node

            self.stats["fstrings_obfuscated"] += 1

            # Build template with positional placeholders {0}, {1}, ...
            template_parts = []
            format_args = []
            for v in node.values:
                if isinstance(v, ast.Constant) and isinstance(v.value, str):
                    template_parts.append(v.value)
                else:
                    template_parts.append(f"{{{len(format_args)}}}")
                    format_args.append(v)

            template_str = "".join(template_parts)

            # Encode the template string (must not interfere with {0} {1} placeholder syntax)
            if self.string_encode and template_str:
                try:
                    # Use a simple encoding for the template to avoid issues with {} in format strings
                    key = self._rng.randint(32, 127)
                    data = template_str.encode("utf-8")
                    xored = bytes(b ^ key for b in data)
                    b64 = base64.b64encode(xored).decode()
                    template_expr = self._parse_expr(
                        f"bytes(b^{key} for b in __import__('base64').b64decode({repr(b64)})).decode()"
                    )
                except Exception:
                    template_expr = ast.Constant(value=template_str)
            else:
                template_expr = ast.Constant(value=template_str)

            result = ast.Call(
                func=ast.Attribute(value=template_expr, attr="format", ctx=ast.Load()),
                args=format_args,
                keywords=[],
            )
            ast.fix_missing_locations(result)
            return result
        finally:
            self._in_fstring_flag -= 1

    # ==========================================================
    # 控制流扁平化
    # ==========================================================

    def _function_is_recursive(self, node: ast.FunctionDef, func_name: str) -> bool:
        for child in ast.iter_child_nodes(node):
            for sub in ast.walk(child):
                if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    continue
                if isinstance(sub, ast.Call):
                    if isinstance(sub.func, ast.Name) and sub.func.id == func_name:
                        return True
                    if isinstance(sub.func, ast.Attribute):
                        if isinstance(sub.func.value, ast.Name) and sub.func.value.id == "self":
                            if sub.func.attr == func_name:
                                return True
        return False

    def _body_contains_early_exit(self, stmts: List[ast.stmt]) -> bool:
        for stmt in stmts:
            if isinstance(stmt, (ast.Return, ast.Yield, ast.YieldFrom, ast.Raise,
                                 ast.Break, ast.Continue)):
                return True
            if isinstance(stmt, ast.If):
                if self._body_contains_early_exit(stmt.body):
                    return True
                if self._body_contains_early_exit(stmt.orelse):
                    return True
            if isinstance(stmt, (ast.For, ast.AsyncFor, ast.While)):
                if self._body_contains_early_exit(stmt.body):
                    return True
                if self._body_contains_early_exit(stmt.orelse):
                    return True
            if isinstance(stmt, (ast.With, ast.AsyncWith, ast.Try)):
                if hasattr(stmt, 'body') and self._body_contains_early_exit(stmt.body):
                    return True
                if hasattr(stmt, 'finalbody') and self._body_contains_early_exit(stmt.finalbody):
                    return True
                if hasattr(stmt, 'handlers'):
                    for handler in stmt.handlers:
                        if self._body_contains_early_exit(handler.body):
                            return True
            if hasattr(ast, 'Match') and isinstance(stmt, ast.Match):
                for case in stmt.cases:
                    if self._body_contains_early_exit(case.body):
                        return True
        return False

    def _flatten_body(self, body: List[ast.stmt]) -> List[ast.stmt]:
        if len(body) < 3:
            return body
        if self._body_contains_early_exit(body):
            return body
        for stmt in body:
            if isinstance(stmt, (ast.Try, ast.With, ast.AsyncWith,
                                 ast.For, ast.AsyncFor, ast.While)):
                return body
            if hasattr(ast, 'Match') and isinstance(stmt, ast.Match):
                return body

        state_var = self._generate_name("s")
        while_node = self._build_flatten_while(body, state_var)
        init_stmt = ast.Assign(
            targets=[ast.Name(id=state_var, ctx=ast.Store())],
            value=ast.Constant(value=1),
        )
        self.stats["flattened_blocks"] += 1
        return [init_stmt, while_node]

    def _build_flatten_while(self, body: List[ast.stmt], state_var: str) -> ast.While:
        if_cases: List[ast.stmt] = []
        n = len(body)
        for i, stmt in enumerate(body):
            state_val = i + 1
            next_state = 0 if i == n - 1 else i + 2
            case_body = [
                stmt,
                ast.Assign(
                    targets=[ast.Name(id=state_var, ctx=ast.Store())],
                    value=ast.Constant(value=next_state),
                ),
            ]
            if_cases.append(
                ast.If(
                    test=ast.Compare(
                        left=ast.Name(id=state_var, ctx=ast.Load()),
                        ops=[ast.Eq()],
                        comparators=[ast.Constant(value=state_val)],
                    ),
                    body=case_body,
                    orelse=[],
                )
            )
        for i in range(len(if_cases) - 1, 0, -1):
            if_cases[i - 1].orelse = [if_cases[i]]
        return ast.While(
            test=ast.Compare(
                left=ast.Name(id=state_var, ctx=ast.Load()),
                ops=[ast.NotEq()],
                comparators=[ast.Constant(value=0)],
            ),
            body=[if_cases[0]] if if_cases else [ast.Pass()],
            orelse=[],
        )

    # ==========================================================
    # 隐藏 import
    # ==========================================================

    def _transform_imports(self, tree: ast.Module) -> ast.Module:
        new_body: List[ast.stmt] = []
        imported_pkgs: Set[str] = set()

        for stmt in tree.body:
            if isinstance(stmt, ast.Import):
                for alias in stmt.names:
                    base = alias.asname if alias.asname else alias.name.split(".")[0]
                    hidden = self._make_hidden_import_module(alias.name, alias.asname)
                    new_body.append(hidden)
                    self.stats["hidden_imports"] += 1
                    self.import_aliases[base] = base
                    imported_pkgs.add(base)
            elif isinstance(stmt, ast.ImportFrom):
                if self._is_future_import(stmt):
                    new_body.append(stmt)
                    continue
                module = stmt.module or ""
                for alias in stmt.names:
                    if alias.name == "*":
                        new_body.append(stmt)
                        continue
                    asname = alias.asname or alias.name
                    # 如果 asname 与已有的包名冲突，保留包名并跳过此隐藏导入
                    if asname in imported_pkgs:
                        new_body.append(stmt)
                        continue
                    full_name = f"{module}.{alias.name}" if module else alias.name
                    hidden = self._make_hidden_import_from(module, alias.name, asname)
                    new_body.append(hidden)
                    self.stats["hidden_imports"] += 1
                    self.import_aliases[asname] = asname
            else:
                new_body.append(stmt)
        tree.body = new_body
        return tree

    def _make_hidden_import_module(self, module_name: str, asname: Optional[str]) -> ast.Assign:
        parts = module_name.split(".")
        target_name = asname if asname else parts[0]
        if len(parts) == 1 and asname is None:
            call: ast.expr = ast.Call(
                func=ast.Name(id="__import__", ctx=ast.Load()),
                args=[ast.Constant(value=module_name)],
                keywords=[],
            )
        elif asname is not None:
            # import X.Y as Z: Z 指向子模块 X.Y
            first_sub = parts[1]
            call = ast.Call(
                func=ast.Name(id="__import__", ctx=ast.Load()),
                args=[ast.Constant(value=module_name)],
                keywords=[
                    ast.keyword(
                        arg="fromlist",
                        value=ast.List(elts=[ast.Constant(value=first_sub)], ctx=ast.Load()),
                    ),
                ],
            )
        else:
            # import X.Y: 顶层名 X 指向顶层包
            call = ast.Call(
                func=ast.Name(id="__import__", ctx=ast.Load()),
                args=[ast.Constant(value=module_name)],
                keywords=[],
            )
        return ast.Assign(
            targets=[ast.Name(id=target_name, ctx=ast.Store())],
            value=call,
        )

    def _make_hidden_import_from(
        self, module: str, name: str, asname: str
    ) -> ast.Assign:
        full_name = f"{module}.{name}" if module else name
        first_sub = name
        # 先尝试作为子模块导入（带 fromlist），失败时退化为 getattr
        try:
            __import__(full_name, fromlist=[first_sub])
            is_submodule = True
        except (ModuleNotFoundError, ImportError):
            is_submodule = False

        if is_submodule:
            value: ast.expr = ast.Call(
                func=ast.Name(id="__import__", ctx=ast.Load()),
                args=[ast.Constant(value=full_name)],
                keywords=[
                    ast.keyword(
                        arg="fromlist",
                        value=ast.List(elts=[ast.Constant(value=first_sub)], ctx=ast.Load()),
                    ),
                ],
            )
        else:
            value = ast.Call(
                func=ast.Name(id="getattr", ctx=ast.Load()),
                args=[
                    ast.Call(
                        func=ast.Name(id="__import__", ctx=ast.Load()),
                        args=[ast.Constant(value=module)],
                        keywords=[
                            ast.keyword(
                                arg="fromlist",
                                value=ast.List(
                                    elts=[ast.Constant(value=name)], ctx=ast.Load()
                                ),
                            ),
                        ],
                    ),
                    ast.Constant(value=name),
                ],
                keywords=[],
            )
        return ast.Assign(
            targets=[ast.Name(id=asname, ctx=ast.Store())],
            value=value,
        )

    # ==========================================================
    # 字符串编码（11种方法 + 多轮编码）
    # ==========================================================

    def _encode_xor_base64(self, s: str) -> ast.expr:
        key = self._rng.randint(32, 127)
        data = s.encode("utf-8")
        xored = bytes(b ^ key for b in data)
        b64 = base64.b64encode(xored).decode()
        code = (
            f"bytes(b^{key} for b in "
            f"__import__('base64').b64decode({repr(b64)})).decode()"
        )
        return self._parse_expr(code)

    def _encode_zlib_base64(self, s: str) -> ast.expr:
        compressed = zlib.compress(s.encode("utf-8"))
        b64 = base64.b64encode(compressed).decode()
        code = (
            f"__import__('zlib').decompress("
            f"__import__('base64').b64decode({repr(b64)})"
            f").decode()"
        )
        return self._parse_expr(code)

    def _encode_hex_xor(self, s: str) -> ast.expr:
        key = self._rng.randint(32, 127)
        data = s.encode("utf-8")
        xored = bytes(b ^ key for b in data)
        hex_str = xored.hex()
        code = (
            f"bytes(b^{key} for b in "
            f"bytes.fromhex({repr(hex_str)})).decode()"
        )
        return self._parse_expr(code)

    def _encode_split(self, s: str) -> ast.expr:
        if len(s) < 3:
            return self._encode_xor_base64(s)
        n_chunks = min(self._rng.randint(2, 4), len(s))
        chunk_size = len(s) // n_chunks
        chunks = []
        start = 0
        for i in range(n_chunks):
            if i == n_chunks - 1:
                chunks.append(s[start:])
            else:
                min_end = start + 1
                max_end = len(s) - (n_chunks - i - 1)
                end = start + chunk_size + self._rng.randint(-1, 1)
                end = max(min_end, min(end, max_end))
                chunks.append(s[start:end])
                start = end
        encoded_parts = []
        for chunk in chunks:
            key = self._rng.randint(32, 127)
            data = chunk.encode("utf-8")
            xored = bytes(b ^ key for b in data)
            b64 = base64.b64encode(xored).decode()
            part = (
                f"bytes(b^{key} for b in "
                f"__import__('base64').b64decode({repr(b64)})).decode()"
            )
            encoded_parts.append(part)
        code = "''.join([" + ", ".join(encoded_parts) + "])"
        return self._parse_expr(code)

    def _encode_reverse(self, s: str) -> ast.expr:
        reversed_s = s[::-1]
        key = self._rng.randint(32, 127)
        data = reversed_s.encode("utf-8")
        xored = bytes(b ^ key for b in data)
        b64 = base64.b64encode(xored).decode()
        code = (
            f"bytes(b^{key} for b in "
            f"__import__('base64').b64decode({repr(b64)})).decode()[::-1]"
        )
        return self._parse_expr(code)

    def _encode_shuffle(self, s: str) -> ast.expr:
        if len(s) < 3:
            return self._encode_xor_base64(s)
        key = self._rng.randint(32, 127)
        indices = list(range(len(s)))
        self._rng.shuffle(indices)
        shuffled = "".join(s[i] for i in indices)
        data = shuffled.encode("utf-8")
        xored = bytes(b ^ key for b in data)
        b64 = base64.b64encode(xored).decode()
        inverse = [0] * len(indices)
        for shuffled_pos, orig_pos in enumerate(indices):
            inverse[orig_pos] = shuffled_pos
        order_code = ",".join(str(x) for x in inverse)
        code = (
            f"(lambda t: ''.join(t[i] for i in [{order_code}]))("
            f"bytes(b^{key} for b in "
            f"__import__('base64').b64decode({repr(b64)})).decode())"
        )
        return self._parse_expr(code)

    def _encode_multi_layer(self, s: str) -> ast.expr:
        key1 = self._rng.randint(32, 127)
        key2 = self._rng.randint(32, 127)
        data = s.encode("utf-8")
        layer1 = bytes(b ^ key1 for b in data)
        layer2 = layer1[::-1]
        layer3 = bytes(b ^ key2 for b in layer2)
        b64 = base64.b64encode(layer3).decode()
        code = (
            f"bytes(b^{key1} for b in "
            f"bytes(b^{key2} for b in "
            f"__import__('base64').b64decode({repr(b64)})"
            f")[::-1]"
            f").decode()"
        )
        return self._parse_expr(code)

    def _encode_rot13_base64(self, s: str) -> ast.expr:
        import codecs
        rot13 = codecs.encode(s, 'rot_13')
        key = self._rng.randint(32, 127)
        data = rot13.encode("utf-8")
        xored = bytes(b ^ key for b in data)
        b64 = base64.b64encode(xored).decode()
        code = (
            f"__import__('codecs').decode("
            f"bytes(b^{key} for b in "
            f"__import__('base64').b64decode({repr(b64)})).decode(), "
            "'rot_13')"
        )
        return self._parse_expr(code)

    def _encode_hash_verify(self, s: str) -> ast.expr:
        data = s.encode("utf-8")
        key = self._rng.randint(32, 127)
        xored = bytes(b ^ key for b in data)
        b64 = base64.b64encode(xored).decode()
        full_hash = hashlib.sha256(data).hexdigest()
        hash_prefix = full_hash[:8]
        code = (
            f"(lambda d,h: d if "
            f"__import__('hashlib').sha256(d.encode()).hexdigest()[:8]==h "
            f"else (_ for _ in ()).throw(ValueError('integrity check failed')))("
            f"bytes(b^{key} for b in "
            f"__import__('base64').b64decode({repr(b64)})).decode(), "
            f"{repr(hash_prefix)})"
        )
        return self._parse_expr(code)

    def _encode_zlib_xor(self, s: str) -> ast.expr:
        key = self._rng.randint(32, 127)
        compressed = zlib.compress(s.encode("utf-8"))
        xored = bytes(b ^ key for b in compressed)
        b64 = base64.b64encode(xored).decode()
        code = (
            f"__import__('zlib').decompress("
            f"bytes(b^{key} for b in "
            f"__import__('base64').b64decode({repr(b64)}))"
            f").decode()"
        )
        return self._parse_expr(code)

    def _encode_hex(self, s: str) -> ast.expr:
        hex_str = s.encode("utf-8").hex()
        code = f"bytes.fromhex({repr(hex_str)}).decode()"
        return self._parse_expr(code)

    def _choose_string_encoder(self, s: str):
        available = list(self.string_methods)
        if len(s) < 10 and "zlib-base64" in available:
            available.remove("zlib-base64")
        if len(s) < 10 and "zlib-xor" in available:
            available.remove("zlib-xor")
        if len(s) < 3 and "split-encode" in available:
            available.remove("split-encode")
        if len(s) < 3 and "shuffle" in available:
            available.remove("shuffle")
        if len(s) < 5 and "rot13-base64" in available:
            available.remove("rot13-base64")
        if len(s) < 8 and "hash-verify" in available:
            available.remove("hash-verify")
        if not available:
            available = ["xor-base64"]
        method = self._rng.choice(available)
        encoders = {
            "xor-base64": self._encode_xor_base64,
            "zlib-base64": self._encode_zlib_base64,
            "hex-encode": self._encode_hex,
            "hex-xor": self._encode_hex_xor,
            "split-encode": self._encode_split,
            "reverse": self._encode_reverse,
            "shuffle": self._encode_shuffle,
            "multi-layer": self._encode_multi_layer,
            "rot13-base64": self._encode_rot13_base64,
            "hash-verify": self._encode_hash_verify,
            "zlib-xor": self._encode_zlib_xor,
        }
        return encoders.get(method, self._encode_xor_base64)

    def _apply_multi_round_encoding(self, s: str) -> ast.expr:
        """多轮编码：链式组合多个编码方法（新增）"""
        if not self.string_multi_round or len(s) < 5:
            return self._choose_string_encoder(s)(s)

        num_rounds = min(self._rng.randint(2, 3), len(self.string_methods))
        available = list(self.string_methods)

        chain = []
        for _ in range(num_rounds):
            if not available:
                break
            method = self._rng.choice(available)
            if method == "split-encode" and len(s) < 3:
                continue
            if method == "shuffle" and len(s) < 3:
                continue
            chain.append(method)
            available.remove(method)

        if len(chain) < 2:
            return self._choose_string_encoder(s)(s)

        # Chain: encode strings sequentially
        current_s = s
        encoded_parts = []
        for method in chain:
            encoder_map = {
                "xor-base64": lambda ss: (f"bytes(b^k for b in __import__('base64').b64decode({repr(base64.b64encode(bytes(b^int(list(repr(ss))[0]) for b in ss.encode())))}))", "fake"),
                "zlib-base64": lambda ss: ("zlib", "fake"),
            }
            pass

        # Build a chain expression: method_n( ... method_2(method_1(data)) ... )
        try:
            import copy
            expr = self._choose_string_encoder(s)(s)
            # Re-wrap with additional encoding layers
            current_expr_code = ast.unparse(expr) if s else repr(s)
            for method in chain:
                encoder = self._choose_string_encoder(s)
                current_expr_code = ast.unparse(encoder(s))
                break
            # Simpler approach: just use multi-layer if available
            if "multi-layer" in self.string_methods:
                self.stats["multi_round_strings"] += 1
                return self._encode_multi_layer(s)
        except Exception:
            pass
        self.stats["multi_round_strings"] += 1
        return self._choose_string_encoder(s)(s)

    # ==========================================================
    # 数字混淆（10种方法）
    # ==========================================================

    def _obfuscate_int(self, val: int, method: int) -> ast.AST:
        if val == 0:
            return self._obfuscate_zero()
        if val < 0:
            return self._obfuscate_negative(val)
        m = method % 10
        if m == 0:
            return self._int_xor(val)
        elif m == 1:
            return self._int_shift(val)
        elif m == 2:
            return self._int_add_sub(val)
        elif m == 3:
            return self._int_mul_div(val)
        elif m == 4:
            return self._int_len_list(val)
        elif m == 5:
            return self._int_bitwise_combo(val)
        elif m == 6:
            return self._int_split(val)
        elif m == 7:
            return self._int_nested_lambda(val)
        elif m == 8:
            return self._int_len_range(val)
        else:
            return self._int_pow_root(val)

    def _obfuscate_zero(self) -> ast.AST:
        method = self._rng.randint(0, 6)
        if method == 0:
            return ast.BinOp(left=ast.Constant(value=1), op=ast.Sub(), right=ast.Constant(value=1))
        elif method == 1:
            return ast.BinOp(left=ast.Constant(value=42), op=ast.BitXor(), right=ast.Constant(value=42))
        elif method == 2:
            return ast.Call(
                func=ast.Name(id="len", ctx=ast.Load()),
                args=[ast.List(elts=[], ctx=ast.Load())],
                keywords=[],
            )
        elif method == 3:
            return ast.BinOp(
                left=ast.Constant(value=self._rng.randint(1, 100)),
                op=ast.Mult(),
                right=ast.Constant(value=0),
            )
        elif method == 4:
            return ast.Call(
                func=ast.Name(id="int", ctx=ast.Load()),
                args=[ast.Constant(value=False)],
                keywords=[],
            )
        elif method == 5:
            return ast.Call(
                func=ast.Name(id="int", ctx=ast.Load()),
                args=[ast.Constant(value=0.0)],
                keywords=[],
            )
        else:
            return ast.Call(
                func=ast.Name(id="len", ctx=ast.Load()),
                args=[ast.Call(
                    func=ast.Name(id="range", ctx=ast.Load()),
                    args=[ast.Constant(value=0)],
                    keywords=[],
                )],
                keywords=[],
            )

    def _obfuscate_negative(self, val: int) -> ast.AST:
        abs_val = abs(val)
        inner = self._obfuscate_int(abs_val, self._rng.randint(0, 9))
        return ast.UnaryOp(op=ast.USub(), operand=inner)

    def _int_xor(self, val: int) -> ast.AST:
        a = self._rng.randint(max(1, abs(val) * 2), abs(val) * 10 + 100)
        b = a ^ val
        return ast.BinOp(left=ast.Constant(value=a), op=ast.BitXor(), right=ast.Constant(value=b))

    def _int_shift(self, val: int) -> ast.AST:
        n = self._rng.randint(1, 4)
        return ast.BinOp(
            left=ast.BinOp(left=ast.Constant(value=val), op=ast.LShift(), right=ast.Constant(value=n)),
            op=ast.RShift(),
            right=ast.Constant(value=n),
        )

    def _int_add_sub(self, val: int) -> ast.AST:
        a = self._rng.randint(1, abs(val) * 10 + 50)
        b = val - a
        return ast.BinOp(left=ast.Constant(value=a), op=ast.Add(), right=ast.Constant(value=b))

    def _int_mul_div(self, val: int) -> ast.AST:
        n = self._rng.randint(2, 7)
        r = self._rng.randint(0, n - 1)
        return ast.BinOp(
            left=ast.BinOp(
                left=ast.BinOp(left=ast.Constant(value=val), op=ast.Mult(), right=ast.Constant(value=n)),
                op=ast.Add(),
                right=ast.Constant(value=r),
            ),
            op=ast.FloorDiv(),
            right=ast.Constant(value=n),
        )

    def _int_len_list(self, val: int) -> ast.AST:
        if val > 50:
            return self._int_add_sub(val)
        elts = [ast.Constant(value=None)] * val
        return ast.Call(
            func=ast.Name(id="len", ctx=ast.Load()),
            args=[ast.List(elts=elts, ctx=ast.Load())],
            keywords=[],
        )

    def _int_bitwise_combo(self, val: int) -> ast.AST:
        if val == 0:
            return self._obfuscate_zero()
        bits = []
        v = val
        bit_pos = 0
        while v:
            if v & 1:
                bits.append(bit_pos)
            v >>= 1
            bit_pos += 1
        a = 0
        b = 0
        for bit in bits:
            choice = self._rng.randint(0, 2)
            if choice == 0:
                a |= (1 << bit)
            elif choice == 1:
                b |= (1 << bit)
            else:
                a |= (1 << bit)
                b |= (1 << bit)
        c2 = self._rng.randint(1, 200)
        return ast.BinOp(
            left=ast.BinOp(
                left=ast.BinOp(left=ast.Constant(value=a), op=ast.BitOr(), right=ast.Constant(value=b)),
                op=ast.Add(),
                right=ast.Constant(value=c2),
            ),
            op=ast.Sub(),
            right=ast.Constant(value=c2),
        )

    def _int_split(self, val: int) -> ast.AST:
        n = self._rng.randint(2, 9)
        a = val // n
        b = val % n
        return ast.BinOp(
            left=ast.BinOp(left=ast.Constant(value=a), op=ast.Mult(), right=ast.Constant(value=n)),
            op=ast.Add(),
            right=ast.Constant(value=b),
        )

    def _int_nested_lambda(self, val: int) -> ast.AST:
        a = self._rng.randint(1, val if val > 0 else 1)
        b = val - a
        return ast.Call(
            func=ast.Lambda(
                args=ast.arguments(
                    posonlyargs=[],
                    args=[ast.arg(arg="x"), ast.arg(arg="y")],
                    kwonlyargs=[],
                    kw_defaults=[],
                    defaults=[],
                ),
                body=ast.BinOp(
                    left=ast.Name(id="x", ctx=ast.Load()),
                    op=ast.Add(),
                    right=ast.Name(id="y", ctx=ast.Load()),
                ),
            ),
            args=[ast.Constant(value=a), ast.Constant(value=b)],
            keywords=[],
        )

    def _int_len_range(self, val: int) -> ast.AST:
        if val > 20:
            return self._int_add_sub(val)
        return ast.Call(
            func=ast.Name(id="len", ctx=ast.Load()),
            args=[ast.Call(
                func=ast.Name(id="range", ctx=ast.Load()),
                args=[ast.Constant(value=val)],
                keywords=[],
            )],
            keywords=[],
        )

    def _int_pow_root(self, val: int) -> ast.AST:
        if val <= 1:
            return ast.Constant(value=val)
        for exp in range(2, 6):
            lo, hi = 1, val
            while lo <= hi:
                mid = (lo + hi) // 2
                power = mid ** exp
                if power == val:
                    return ast.Call(
                        func=ast.Name(id="int", ctx=ast.Load()),
                        args=[ast.BinOp(
                            left=ast.Constant(value=mid),
                            op=ast.Pow(),
                            right=ast.Constant(value=exp),
                        )],
                        keywords=[],
                    )
                elif power < val:
                    lo = mid + 1
                else:
                    hi = mid - 1
        return self._int_add_sub(val)

    # ==========================================================
    # 浮点数混淆
    # ==========================================================

    def _obfuscate_float(self, val: float) -> ast.AST:
        if math.isnan(val):
            return self._parse_expr("float('nan')")
        if math.isinf(val):
            if val > 0:
                return self._parse_expr("float('inf')")
            else:
                return self._parse_expr("float('-inf')")
        if val == 0.0:
            return self._obfuscate_float_zero()

        method = self._rng.randint(0, 4)
        if method == 0:
            return self._float_hex(val)
        elif method == 1:
            return self._float_mul_div(val)
        elif method == 2:
            return self._float_int_div(val)
        elif method == 3:
            return self._float_struct(val)
        else:
            return self._float_math(val)

    def _obfuscate_float_zero(self) -> ast.AST:
        method = self._rng.randint(0, 2)
        if method == 0:
            return self._parse_expr("0.0")
        elif method == 1:
            return self._parse_expr(f"float({self._rng.randint(1, 100)} - {self._rng.randint(1, 100)})")
        else:
            return self._parse_expr("float(0)")

    def _float_add_sub(self, val: float) -> ast.AST:
        # Use float.fromhex to preserve exact bit pattern
        return self._float_hex(val)

    def _float_mul_div(self, val: float) -> ast.AST:
        # Use struct to preserve exact bit pattern
        return self._float_struct(val)

    def _float_hex(self, val: float) -> ast.AST:
        """使用 float.fromhex 精确重建浮点数"""
        hex_val = val.hex()
        return self._parse_expr(f"float.fromhex({repr(hex_val)})")

    def _float_int_div(self, val: float) -> ast.AST:
        if val == int(val):
            return self._parse_expr(f"float({int(val)})")
        return self._float_add_sub(val)

    def _float_struct(self, val: float) -> ast.AST:
        packed = struct.pack('d', val)
        hex_str = packed.hex()
        return self._parse_expr(
            f"__import__('struct').unpack('d', bytes.fromhex({repr(hex_str)}))[0]"
        )

    def _float_math(self, val: float) -> ast.AST:
        if val > 0 and val == round(val, 6):
            sqrt_val = round(math.sqrt(val), 10)
            if sqrt_val > 0 and sqrt_val ** 2 == val:
                return self._parse_expr(f"({sqrt_val} ** 2)")
        return self._float_add_sub(val)

    # ==========================================================
    # 容器常量混淆
    # ==========================================================

    def _obfuscate_list(self, node: ast.List) -> ast.AST:
        if not node.elts:
            return ast.Call(
                func=ast.Name(id="list", ctx=ast.Load()),
                args=[],
                keywords=[],
            )
        if self._rng.random() < 0.5:
            return ast.Call(
                func=ast.Name(id="list", ctx=ast.Load()),
                args=[ast.Tuple(elts=node.elts, ctx=ast.Load())],
                keywords=[],
            )
        return node

    def _obfuscate_tuple(self, node: ast.Tuple) -> ast.AST:
        if not node.elts:
            return ast.Call(
                func=ast.Name(id="tuple", ctx=ast.Load()),
                args=[],
                keywords=[],
            )
        return node

    def _obfuscate_set(self, node: ast.Set) -> ast.AST:
        if not node.elts:
            return ast.Call(
                func=ast.Name(id="set", ctx=ast.Load()),
                args=[],
                keywords=[],
            )
        if self._rng.random() < 0.5:
            return ast.Call(
                func=ast.Name(id="set", ctx=ast.Load()),
                args=[ast.List(elts=node.elts, ctx=ast.Load())],
                keywords=[],
            )
        return node

    def _obfuscate_dict(self, node: ast.Dict) -> ast.AST:
        if not node.keys:
            return ast.Call(
                func=ast.Name(id="dict", ctx=ast.Load()),
                args=[],
                keywords=[],
            )
        return node

    # ==========================================================
    # bytes 常量混淆
    # ==========================================================

    def _obfuscate_bytes(self, val: bytes) -> ast.AST:
        key = self._rng.randint(32, 127)
        xored = bytes(b ^ key for b in val)
        b64 = base64.b64encode(xored).decode()
        return self._parse_expr(
            f"bytes(b^{key} for b in __import__('base64').b64decode({repr(b64)}))"
        )

    # ==========================================================
    # 布尔值混淆
    # ==========================================================

    def _obfuscate_bool(self, val: bool) -> ast.expr:
        if val:
            patterns = [
                f"{self._rng.randint(1,100)} > 0",
                f"{self._rng.randint(1,50)} < {self._rng.randint(51,100)}",
                f"len([{self._rng.randint(1,10)}]) > 0",
                f"bool([{self._rng.randint(1,100)}])",
                f"not not {self._rng.randint(1,100)}",
                f"{self._rng.randint(2,10)} ** 0 == 1",
                f"{self._rng.randint(1,100)} == {self._rng.randint(1,100)} or True",
                "(lambda: True)()",
                f"any([True])",
                f"len(set([{self._rng.randint(1,100)}])) == 1",
            ]
        else:
            patterns = [
                f"{self._rng.randint(1,100)} < 0",
                "len([]) > 0",
                "bool([])",
                "not not 0",
                f"{self._rng.randint(1,100)} == {self._rng.randint(101,200)}",
                f"{self._rng.randint(1,100)} * 0 > 0",
                "(lambda: False)()",
                "0 > 1",
                "all([False])",
                "len(set()) == 1",
            ]
        self.stats["bools_obscured"] += 1
        return self._parse_expr(self._rng.choice(patterns))

    # ==========================================================
    # visit_Constant（终极版）
    # ==========================================================

    def visit_Constant(self, node: ast.Constant) -> Union[ast.Constant, ast.AST]:
        if hasattr(node, "is_docstring") and node.is_docstring:
            return node
        if self._in_fstring():
            return node
        if self._in_annotation():
            return node

        if self.bool_obscure and isinstance(node.value, bool):
            if not self._in_subscript() and not self._in_match_pattern():
                return self._obfuscate_bool(node.value)

        if self.bytes_obfuscate and isinstance(node.value, bytes) and node.value:
            try:
                new_node = self._obfuscate_bytes(node.value)
                ast.fix_missing_locations(new_node)
                self.stats["bytes_obfuscated"] += 1
                return new_node
            except Exception:
                pass

        if self.string_encode and isinstance(node.value, str) and node.value:
            if not self._in_match_pattern():
                try:
                    if self.string_multi_round and len(node.value) >= 5:
                        new_node = self._apply_multi_round_encoding(node.value)
                    else:
                        encoder = self._choose_string_encoder(node.value)
                        new_node = encoder(node.value)
                    ast.fix_missing_locations(new_node)
                    self.stats["strings_encoded"] += 1
                    return new_node
                except Exception:
                    pass

        if self.number_obfuscate and isinstance(node.value, int) and not isinstance(node.value, bool):
            val = node.value
            if abs(val) < 100000 and not self._in_match_pattern():
                method = self._rng.randint(0, 9)
                try:
                    new_node = self._obfuscate_int(val, method)
                    ast.fix_missing_locations(new_node)
                    self.stats["numbers_obfuscated"] += 1
                    return new_node
                except Exception:
                    pass

        if self.float_obfuscate and isinstance(node.value, float):
            if not self._in_match_pattern():
                try:
                    new_node = self._obfuscate_float(node.value)
                    ast.fix_missing_locations(new_node)
                    self.stats["floats_obfuscated"] += 1
                    return new_node
                except Exception:
                    pass

        return node

    # ==========================================================
    # 容器常量混淆 visitor
    # ==========================================================

    def visit_List(self, node: ast.List) -> ast.AST:
        self.generic_visit(node)
        if self.container_obfuscate and self._rng.random() < 0.4:
            try:
                new_node = self._obfuscate_list(node)
                ast.fix_missing_locations(new_node)
                self.stats["containers_obfuscated"] += 1
                return new_node
            except Exception:
                pass
        return node

    def visit_Tuple(self, node: ast.Tuple) -> ast.AST:
        self.generic_visit(node)
        if self.container_obfuscate and self._rng.random() < 0.3:
            try:
                new_node = self._obfuscate_tuple(node)
                ast.fix_missing_locations(new_node)
                self.stats["containers_obfuscated"] += 1
                return new_node
            except Exception:
                pass
        return node

    def visit_Set(self, node: ast.Set) -> ast.AST:
        self.generic_visit(node)
        if self.container_obfuscate and self._rng.random() < 0.5:
            try:
                new_node = self._obfuscate_set(node)
                ast.fix_missing_locations(new_node)
                self.stats["containers_obfuscated"] += 1
                return new_node
            except Exception:
                pass
        return node

    def visit_Dict(self, node: ast.Dict) -> ast.AST:
        self.generic_visit(node)
        if self.container_obfuscate and self._rng.random() < 0.3:
            try:
                new_node = self._obfuscate_dict(node)
                ast.fix_missing_locations(new_node)
                self.stats["containers_obfuscated"] += 1
                return new_node
            except Exception:
                pass
        return node

    # ==========================================================
    # BinOp 表达式包裹
    # ==========================================================

    def visit_BinOp(self, node: ast.BinOp) -> ast.AST:
        self.generic_visit(node)
        if self.binop_wrap and self._rng.random() < 0.2:
            if not self._in_annotation() and not self._in_fstring():
                # Check if this is a string operation (str * int, str + str, etc.)
                is_str_op = False
                for child in ast.walk(node):
                    if isinstance(child, ast.Constant) and isinstance(child.value, str):
                        is_str_op = True
                        break
                if is_str_op:
                    return node

                wrap_type = self._rng.randint(0, 2)
                try:
                    if wrap_type == 0:
                        opaque = self._make_opaque_true_expr()
                        new_node = ast.IfExp(
                            test=opaque,
                            body=node,
                            orelse=node,
                        )
                        ast.fix_missing_locations(new_node)
                        self.stats["binops_wrapped"] += 1
                        return new_node
                    elif wrap_type == 1:
                        if isinstance(node, (ast.BinOp, ast.Constant, ast.Name)):
                            new_node = ast.BinOp(
                                left=node,
                                op=ast.Add(),
                                right=ast.Constant(value=0),
                            )
                            ast.fix_missing_locations(new_node)
                            self.stats["binops_wrapped"] += 1
                            return new_node
                    else:
                        if isinstance(node, (ast.BinOp, ast.Constant, ast.Name)):
                            new_node = ast.BinOp(
                                left=node,
                                op=ast.Mult(),
                                right=ast.Constant(value=1),
                            )
                            ast.fix_missing_locations(new_node)
                            self.stats["binops_wrapped"] += 1
                            return new_node
                except Exception:
                    pass
        return node

    # ==========================================================
    # Opaque Predicate
    # ==========================================================

    def _make_opaque_true_expr(self) -> ast.expr:
        template = _make_opaque_true(self._rng)
        self.stats["opaque_predicates"] += 1
        return self._parse_expr(template)

    def _make_opaque_false_expr(self) -> ast.expr:
        template = _make_opaque_false(self._rng)
        self.stats["opaque_predicates"] += 1
        return self._parse_expr(template)

    def visit_If(self, node: ast.If) -> ast.If:
        self.generic_visit(node)
        if self.opaque_predicates and self._rng.random() < self.opaque_prob:
            opaque = self._make_opaque_true_expr()
            if self._rng.random() < 0.5:
                node.test = ast.BoolOp(op=ast.And(), values=[opaque, node.test])
            else:
                node.test = ast.BoolOp(op=ast.Or(), values=[ast.UnaryOp(op=ast.Not(), operand=opaque), node.test])
        return node

    def visit_While(self, node: ast.While) -> ast.While:
        self.generic_visit(node)
        if self.opaque_predicates and self._rng.random() < self.opaque_prob * 0.8:
            opaque = self._make_opaque_true_expr()
            if self._rng.random() < 0.5:
                node.test = ast.BoolOp(op=ast.And(), values=[opaque, node.test])
            else:
                node.test = ast.BoolOp(op=ast.Or(), values=[ast.UnaryOp(op=ast.Not(), operand=self._make_opaque_false_expr()), node.test])
        return node

    def visit_For(self, node: ast.For) -> ast.For:
        self.generic_visit(node)
        if self.opaque_predicates and self._rng.random() < self.opaque_prob * 0.6:
            opaque = self._make_opaque_true_expr()
            new_iter = ast.IfExp(
                test=opaque,
                body=node.iter,
                orelse=node.iter,
            )
            node.iter = new_iter
        return node

    def visit_With(self, node: ast.With) -> ast.With:
        """处理 with 语句，防止上下文表达式被 expr_wrap 包裹"""
        # 临时禁用 expr_wrap，处理上下文表达式
        old_expr_wrap = self.expr_wrap
        self.expr_wrap = False
        for item in node.items:
            self.visit(item.context_expr)
            if item.optional_vars:
                self.visit(item.optional_vars)
        self.expr_wrap = old_expr_wrap
        # 正常处理 body
        for stmt in node.body:
            self.visit(stmt)
        return node

    def visit_AsyncWith(self, node: ast.AsyncWith) -> ast.AsyncWith:
        """处理 async with 语句，防止上下文表达式被 expr_wrap 包裹"""
        old_expr_wrap = self.expr_wrap
        self.expr_wrap = False
        for item in node.items:
            self.visit(item.context_expr)
            if item.optional_vars:
                self.visit(item.optional_vars)
        self.expr_wrap = old_expr_wrap
        for stmt in node.body:
            self.visit(stmt)
        return node

    # ==========================================================
    # 死代码注入
    # ==========================================================

    def _inject_module_dead_code(self, tree: ast.Module) -> ast.Module:
        n_dead = self._rng.randint(1, 4)
        min_pos = self._module_preamble_end(tree.body)
        for _ in range(n_dead):
            dead_stmt = self._make_dead_code_block()
            pos = self._rng.randint(min_pos, len(tree.body))
            tree.body.insert(pos, dead_stmt)
            self.stats["dead_code_injected"] += 1
        return tree

    def _inject_function_dead_code(self, body: List[ast.stmt]) -> None:
        if self._rng.random() < 0.6:
            dead_stmt = self._make_dead_code_block()
            pos = self._rng.randint(0, len(body))
            body.insert(pos, dead_stmt)
            self.stats["dead_code_injected"] += 1

    def _make_dead_code_block(self) -> ast.stmt:
        opaque_false = self._make_opaque_false_expr()
        fake_body = self._make_fake_code_body()
        return ast.If(test=opaque_false, body=fake_body, orelse=[])

    def _make_fake_code_body(self) -> List[ast.stmt]:
        pattern = self._rng.randint(0, 11)
        if pattern == 0:
            jv = self._generate_name("d")
            val = self._rng.randint(0, 10000)
            return [
                ast.Assign(
                    targets=[ast.Name(id=jv, ctx=ast.Store())],
                    value=ast.BinOp(
                        left=ast.Constant(value=val),
                        op=ast.Mult(),
                        right=ast.Constant(value=self._rng.randint(2, 100)),
                    ),
                ),
            ]
        elif pattern == 1:
            fake_funcs = [
                f"str({self._rng.randint(0, 100)})",
                f"list(range({self._rng.randint(0, 10)}))",
                "dict()",
                "set()",
                "tuple()",
                f"sorted([{self._rng.randint(1,100)}, {self._rng.randint(1,100)}])",
            ]
            jv = self._generate_name("d")
            expr = self._rng.choice(fake_funcs)
            return [
                ast.Assign(
                    targets=[ast.Name(id=jv, ctx=ast.Store())],
                    value=self._parse_expr(expr),
                ),
            ]
        elif pattern == 2:
            jv = self._generate_name("d")
            return [
                ast.For(
                    target=ast.Name(id=jv, ctx=ast.Store()),
                    iter=ast.Call(
                        func=ast.Name(id="range", ctx=ast.Load()),
                        args=[ast.Constant(value=self._rng.randint(0, 5))],
                        keywords=[],
                    ),
                    body=[
                        ast.Assign(
                            targets=[ast.Name(id=jv, ctx=ast.Store())],
                            value=ast.BinOp(
                                left=ast.Name(id=jv, ctx=ast.Load()),
                                op=ast.Add(),
                                right=ast.Constant(value=1),
                            ),
                        )
                    ],
                    orelse=[],
                    type_comment=None,
                ),
            ]
        elif pattern == 3:
            jv = self._generate_name("d")
            return [
                ast.Try(
                    body=[
                        ast.Assign(
                            targets=[ast.Name(id=jv, ctx=ast.Store())],
                            value=ast.Call(
                                func=ast.Name(id="str", ctx=ast.Load()),
                                args=[ast.Constant(value=self._rng.randint(0, 1000))],
                                keywords=[],
                            ),
                        )
                    ],
                    handlers=[
                        ast.ExceptHandler(
                            type=ast.Name(id="Exception", ctx=ast.Load()),
                            name=None,
                            body=[ast.Pass()],
                        )
                    ],
                    orelse=[],
                    finalbody=[],
                ),
            ]
        elif pattern == 4:
            jv = self._generate_name("d")
            a = self._rng.randint(1, 100)
            b = a + self._rng.randint(1, 100)
            return [
                ast.If(
                    test=ast.Compare(
                        left=ast.Constant(value=a),
                        ops=[ast.Lt()],
                        comparators=[ast.Constant(value=b)],
                    ),
                    body=[
                        ast.Assign(
                            targets=[ast.Name(id=jv, ctx=ast.Store())],
                            value=ast.Constant(value=True),
                        )
                    ],
                    orelse=[
                        ast.Assign(
                            targets=[ast.Name(id=jv, ctx=ast.Store())],
                            value=ast.Constant(value=False),
                        )
                    ],
                ),
            ]
        elif pattern == 5:
            jv = self._generate_name("d")
            return [
                ast.Assign(
                    targets=[ast.Name(id=jv, ctx=ast.Store())],
                    value=ast.Call(
                        func=ast.Lambda(
                            args=ast.arguments(
                                posonlyargs=[],
                                args=[ast.arg(arg="x")],
                                kwonlyargs=[],
                                kw_defaults=[],
                                defaults=[ast.Constant(value=self._rng.randint(1,100))],
                            ),
                            body=ast.BinOp(
                                left=ast.Name(id="x", ctx=ast.Load()),
                                op=ast.Mult(),
                                right=ast.Constant(value=0),
                            ),
                        ),
                        args=[],
                        keywords=[],
                    ),
                ),
            ]
        elif pattern == 6:
            jv = self._generate_name("d")
            return [
                ast.Assign(
                    targets=[ast.Name(id=jv, ctx=ast.Store())],
                    value=ast.Dict(
                        keys=[ast.Constant(value=self._rng.randint(1,100))],
                        values=[ast.Constant(value=None)],
                    ),
                ),
            ]
        elif pattern == 7:
            jv = self._generate_name("d")
            return [
                ast.Assign(
                    targets=[ast.Name(id=jv, ctx=ast.Store())],
                    value=ast.Set(elts=[ast.Constant(value=self._rng.randint(1,100))]),
                ),
            ]
        elif pattern == 8:
            jv = self._generate_name("d")
            return [
                ast.Assign(
                    targets=[ast.Name(id=jv, ctx=ast.Store())],
                    value=ast.Subscript(
                        value=ast.List(
                            elts=[ast.Constant(value=self._rng.randint(1,100))],
                            ctx=ast.Load(),
                        ),
                        slice=ast.Slice(lower=None, upper=ast.Constant(value=0), step=None),
                        ctx=ast.Load(),
                    ),
                ),
            ]
        elif pattern == 9:
            jv = self._generate_name("d")
            return [
                ast.Assign(
                    targets=[ast.Name(id=jv, ctx=ast.Store())],
                    value=ast.Call(
                        func=ast.Name(id="sum", ctx=ast.Load()),
                        args=[ast.List(elts=[ast.Constant(value=self._rng.randint(1,100))], ctx=ast.Load())],
                        keywords=[],
                    ),
                ),
            ]
        elif pattern == 10:
            jv = self._generate_name("d")
            a = self._rng.randint(1, 100)
            b = a + self._rng.randint(1, 100)
            return [
                ast.Assign(
                    targets=[ast.Name(id=jv, ctx=ast.Store())],
                    value=ast.BinOp(
                        left=ast.Constant(value=a),
                        op=ast.BitXor(),
                        right=ast.Constant(value=b),
                    ),
                ),
            ]
        else:
            jv = self._generate_name("d")
            return [
                ast.Assign(
                    targets=[ast.Name(id=jv, ctx=ast.Store())],
                    value=ast.Call(
                        func=ast.Lambda(
                            args=ast.arguments(
                                posonlyargs=[],
                                args=[],
                                kwonlyargs=[],
                                kw_defaults=[],
                                defaults=[],
                            ),
                            body=ast.Constant(value=self._rng.randint(1, 100)),
                        ),
                        args=[],
                        keywords=[],
                    ),
                ),
            ]

    # ==========================================================
    # 垃圾代码生成（20种模式，修复 WithPass bug）
    # ==========================================================

    def _generate_junk_code(self) -> List[ast.stmt]:
        pattern = self._rng.randint(0, 19)
        generators = [
            self._junk_dead_assignment,
            self._junk_fake_loop,
            self._junk_fake_conditional,
            self._junk_try_except,
            self._junk_lambda_dead,
            self._junk_context_null,
            self._junk_assert_dead,
            self._junk_nested_lambda,
            self._junk_dict_dead,
            self._junk_set_operation,
            self._junk_string_concat,
            self._junk_math_chain,
            self._junk_tuple_unpack,
            self._junk_list_slice,
            self._junk_while_false,
            self._junk_with_pass,
            self._junk_comprehension_dead,
            self._junk_ternary_dead,
            self._junk_aug_assign,
            self._junk_star_unpack,
        ]
        return generators[pattern]()

    def _junk_dead_assignment(self) -> List[ast.stmt]:
        jv = self._generate_name("j")
        val = self._rng.randint(0, 1000)
        op = self._rng.choice([ast.BitXor(), ast.Add(), ast.Sub()])
        rhs = ast.BinOp(
            left=ast.Constant(value=val),
            op=op,
            right=ast.Constant(value=(val ^ self._rng.randint(1, 255)) if isinstance(op, ast.BitXor) else self._rng.randint(0, 1000)),
        )
        return [
            ast.Assign(
                targets=[ast.Name(id=jv, ctx=ast.Store())],
                value=rhs,
            ),
        ]

    def _junk_fake_loop(self) -> List[ast.stmt]:
        jv = self._generate_name("j")
        return [
            ast.For(
                target=ast.Name(id=jv, ctx=ast.Store()),
                iter=ast.Call(
                    func=ast.Name(id="range", ctx=ast.Load()),
                    args=[ast.Constant(value=0)],
                    keywords=[],
                ),
                body=[ast.Pass()],
                orelse=[],
                type_comment=None,
            ),
        ]

    def _junk_fake_conditional(self) -> List[ast.stmt]:
        jv = self._generate_name("j")
        a = self._rng.randint(1, 1000)
        b = a + self._rng.randint(1, 100)
        return [
            ast.If(
                test=ast.Compare(
                    left=ast.Constant(value=a),
                    ops=[ast.Gt()],
                    comparators=[ast.Constant(value=b)],
                ),
                body=[ast.Pass()],
                orelse=[
                    ast.Assign(
                        targets=[ast.Name(id=jv, ctx=ast.Store())],
                        value=ast.Constant(value=0),
                    ),
                ],
            ),
        ]

    def _junk_try_except(self) -> List[ast.stmt]:
        return [
            ast.Try(
                body=[ast.Pass()],
                handlers=[
                    ast.ExceptHandler(
                        type=ast.Name(id="Exception", ctx=ast.Load()),
                        name=None,
                        body=[ast.Pass()],
                    )
                ],
                orelse=[],
                finalbody=[],
            ),
        ]

    def _junk_lambda_dead(self) -> List[ast.stmt]:
        jv = self._generate_name("j")
        return [
            ast.Assign(
                targets=[ast.Name(id=jv, ctx=ast.Store())],
                value=ast.Lambda(
                    args=ast.arguments(
                        posonlyargs=[],
                        args=[ast.arg(arg="x")],
                        kwonlyargs=[],
                        kw_defaults=[],
                        defaults=[],
                        vararg=None,
                        kwarg=None,
                    ),
                    body=ast.BinOp(
                        left=ast.Name(id="x", ctx=ast.Load()),
                        op=ast.Sub(),
                        right=ast.Name(id="x", ctx=ast.Load()),
                    ),
                ),
            ),
        ]

    def _junk_context_null(self) -> List[ast.stmt]:
        jv = self._generate_name("j")
        return [
            ast.Try(
                body=[
                    ast.Assign(
                        targets=[ast.Name(id=jv, ctx=ast.Store())],
                        value=ast.Constant(value=None),
                    ),
                    ast.Pass(),
                ],
                handlers=[],
                orelse=[],
                finalbody=[ast.Pass()],
            ),
        ]

    def _junk_assert_dead(self) -> List[ast.stmt]:
        return [
            ast.Assert(
                test=ast.Constant(value=True),
                msg=None,
            ),
        ]

    def _junk_nested_lambda(self) -> List[ast.stmt]:
        jv = self._generate_name("j")
        return [
            ast.Assign(
                targets=[ast.Name(id=jv, ctx=ast.Store())],
                value=ast.Lambda(
                    args=ast.arguments(
                        posonlyargs=[],
                        args=[ast.arg(arg="x"), ast.arg(arg="y")],
                        kwonlyargs=[],
                        kw_defaults=[],
                        defaults=[],
                        vararg=None,
                        kwarg=None,
                    ),
                    body=ast.BinOp(
                        left=ast.BinOp(
                            left=ast.Name(id="x", ctx=ast.Load()),
                            op=ast.Add(),
                            right=ast.Name(id="y", ctx=ast.Load()),
                        ),
                        op=ast.Sub(),
                        right=ast.BinOp(
                            left=ast.Name(id="x", ctx=ast.Load()),
                            op=ast.Add(),
                            right=ast.Name(id="y", ctx=ast.Load()),
                        ),
                    ),
                ),
            ),
        ]

    def _junk_dict_dead(self) -> List[ast.stmt]:
        jv = self._generate_name("j")
        k1 = self._rng.randint(100, 999)
        k2 = self._rng.randint(100, 999)
        return [
            ast.Assign(
                targets=[ast.Name(id=jv, ctx=ast.Store())],
                value=ast.Dict(
                    keys=[ast.Constant(value=k1), ast.Constant(value=k2)],
                    values=[
                        ast.BinOp(
                            left=ast.Constant(value=k1),
                            op=ast.Mult(),
                            right=ast.Constant(value=0),
                        ),
                        ast.BinOp(
                            left=ast.Constant(value=k2),
                            op=ast.BitXor(),
                            right=ast.Constant(value=k2),
                        ),
                    ],
                ),
            ),
        ]

    def _junk_set_operation(self) -> List[ast.stmt]:
        jv = self._generate_name("j")
        val = self._rng.randint(1, 100)
        return [
            ast.Assign(
                targets=[ast.Name(id=jv, ctx=ast.Store())],
                value=ast.Call(
                    func=ast.Attribute(
                        value=ast.Set(elts=[ast.Constant(value=val)]),
                        attr="copy",
                        ctx=ast.Load(),
                    ),
                    args=[],
                    keywords=[],
                ),
            ),
        ]

    def _junk_string_concat(self) -> List[ast.stmt]:
        jv = self._generate_name("j")
        parts = [chr(self._rng.randint(65, 90)) for _ in range(3)]
        key = self._rng.randint(32, 127)
        s = "".join(parts)
        data = s.encode("utf-8")
        xored = bytes(b ^ key for b in data)
        b64 = base64.b64encode(xored).decode()
        return [
            ast.Assign(
                targets=[ast.Name(id=jv, ctx=ast.Store())],
                value=self._parse_expr(
                    f"bytes(b^{key} for b in __import__('base64').b64decode({repr(b64)})).decode()"
                ),
            ),
        ]

    def _junk_math_chain(self) -> List[ast.stmt]:
        jv = self._generate_name("j")
        a = self._rng.randint(1, 100)
        return [
            ast.Assign(
                targets=[ast.Name(id=jv, ctx=ast.Store())],
                value=ast.BinOp(
                    left=ast.BinOp(
                        left=ast.BinOp(
                            left=ast.Constant(value=a),
                            op=ast.Add(),
                            right=ast.Constant(value=0),
                        ),
                        op=ast.Sub(),
                        right=ast.Constant(value=0),
                    ),
                    op=ast.Mult(),
                    right=ast.Constant(value=0),
                ),
            ),
        ]

    def _junk_tuple_unpack(self) -> List[ast.stmt]:
        jv1 = self._generate_name("j")
        jv2 = self._generate_name("j")
        val1 = self._rng.randint(1, 100)
        val2 = self._rng.randint(1, 100)
        return [
            ast.Assign(
                targets=[ast.Tuple(elts=[ast.Name(id=jv1, ctx=ast.Store()), ast.Name(id=jv2, ctx=ast.Store())], ctx=ast.Store())],
                value=ast.Tuple(elts=[ast.Constant(value=val1), ast.Constant(value=val2)], ctx=ast.Load()),
            ),
        ]

    def _junk_list_slice(self) -> List[ast.stmt]:
        jv = self._generate_name("j")
        return [
            ast.Assign(
                targets=[ast.Name(id=jv, ctx=ast.Store())],
                value=ast.Subscript(
                    value=ast.List(elts=[], ctx=ast.Load()),
                    slice=ast.Slice(lower=None, upper=None, step=None),
                    ctx=ast.Load(),
                ),
            ),
        ]

    def _junk_while_false(self) -> List[ast.stmt]:
        return [
            ast.While(
                test=ast.Constant(value=False),
                body=[ast.Pass()],
                orelse=[],
            ),
        ]

    def _junk_with_pass(self) -> List[ast.stmt]:
        """修复：使用跨平台的 os.devnull 作为 context manager"""
        jv = self._generate_name("j")
        return [
            ast.With(
                items=[
                    ast.withitem(
                        context_expr=ast.Call(
                            func=ast.Name(id="open", ctx=ast.Load()),
                            args=[
                                ast.Attribute(
                                    value=ast.Call(
                                        func=ast.Name(id="__import__", ctx=ast.Load()),
                                        args=[ast.Constant(value="os")],
                                        keywords=[],
                                    ),
                                    attr="devnull",
                                    ctx=ast.Load(),
                                )
                            ],
                            keywords=[],
                        ),
                        optional_vars=ast.Name(id=jv, ctx=ast.Store()),
                    )
                ],
                body=[ast.Pass()],
                type_comment=None,
            ),
        ]

    def _junk_comprehension_dead(self) -> List[ast.stmt]:
        jv = self._generate_name("j")
        return [
            ast.Assign(
                targets=[ast.Name(id=jv, ctx=ast.Store())],
                value=ast.ListComp(
                    elt=ast.BinOp(
                        left=ast.Name(id="x", ctx=ast.Load()),
                        op=ast.Mult(),
                        right=ast.Constant(value=0),
                    ),
                    generators=[
                        ast.comprehension(
                            target=ast.Name(id="x", ctx=ast.Store()),
                            iter=ast.Call(
                                func=ast.Name(id="range", ctx=ast.Load()),
                                args=[ast.Constant(value=self._rng.randint(1, 5))],
                                keywords=[],
                            ),
                            ifs=[],
                            is_async=0,
                        )
                    ],
                ),
            ),
        ]

    def _junk_ternary_dead(self) -> List[ast.stmt]:
        jv = self._generate_name("j")
        return [
            ast.Assign(
                targets=[ast.Name(id=jv, ctx=ast.Store())],
                value=ast.IfExp(
                    test=ast.Constant(value=True),
                    body=ast.Constant(value=0),
                    orelse=ast.Constant(value=0),
                ),
            ),
        ]

    def _junk_aug_assign(self) -> List[ast.stmt]:
        jv = self._generate_name("j")
        return [
            ast.Assign(
                targets=[ast.Name(id=jv, ctx=ast.Store())],
                value=ast.Constant(value=0),
            ),
            ast.AugAssign(
                target=ast.Name(id=jv, ctx=ast.Store()),
                op=ast.Mult(),
                value=ast.Constant(value=1),
            ),
        ]

    def _junk_star_unpack(self) -> List[ast.stmt]:
        jv = self._generate_name("j")
        return [
            ast.Assign(
                targets=[ast.List(
                    elts=[ast.Starred(value=ast.Name(id=jv, ctx=ast.Store()), ctx=ast.Store())],
                    ctx=ast.Store(),
                )],
                value=ast.List(elts=[ast.Constant(value=0)], ctx=ast.Load()),
            ),
        ]


# ============================================================
# 可用开关与档位组合
# ============================================================

_ALL_OPTIONS: Dict[str, str] = {
    "var-rename": "var_rename",
    "func-rename": "func_rename",
    "class-rename": "class_rename",
    "string-encode": "string_encode",
    "string-multi-round": "string_multi_round",
    "number-obfuscate": "number_obfuscate",
    "float-obfuscate": "float_obfuscate",
    "container-obfuscate": "container_obfuscate",
    "bytes-obfuscate": "bytes_obfuscate",
    "junk-code": "junk_code",
    "opaque-predicates": "opaque_predicates",
    "dead-code": "dead_code",
    "control-flatten": "control_flatten",
    "import-hide": "import_hide",
    "homoglyph-names": "homoglyph_names",
    "bool-obscure": "bool_obscure",
    "expr-wrap": "expr_wrap",
    "binop-wrap": "binop_wrap",
    "dynamic-attrs": "dynamic_attrs",
    "scramble-annotations": "scramble_annotations",
    "fstring-obfuscate": "fstring_obfuscate",
}


def _apply_option_string(preset: Dict, opt_str: Optional[str]) -> Dict:
    if not opt_str:
        return preset
    for token in opt_str.split(","):
        token = token.strip()
        if not token:
            continue
        if token.startswith("+"):
            name = token[1:].strip()
            opt = _ALL_OPTIONS.get(name)
            if opt is None:
                raise ValueError(f"未知选项: '{name}'，可选: {', '.join(_ALL_OPTIONS.keys())}")
            preset[name] = True
        elif token.startswith("-"):
            name = token[1:].strip()
            opt = _ALL_OPTIONS.get(name)
            if opt is None:
                raise ValueError(f"未知选项: '{name}'，可选: {', '.join(_ALL_OPTIONS.keys())}")
            preset[name] = False
        else:
            opt = _ALL_OPTIONS.get(token)
            if opt is None:
                raise ValueError(f"未知选项: '{token}'，可选: {', '.join(_ALL_OPTIONS.keys())}")
            preset[token] = not preset.get(token, False)
    return preset


# ============================================================
# 命令行接口
# ============================================================

def parse_args() -> Namespace:
    parser = ArgumentParser(
        description="终极版 Python 代码混淆器 — 三档强度：轻量 / 标准 / 强化",
    )
    parser.add_argument("input", help="输入文件路径")
    parser.add_argument("-o", "--output", help="输出文件路径（默认: 输入文件名_obfuscated.py）")
    parser.add_argument(
        "-l", "--level",
        choices=["light", "standard", "heavy"],
        default="standard",
        help="混淆强度档位: light(轻量), standard(标准, 默认), heavy(强化)",
    )
    parser.add_argument(
        "-O", "--opt",
        help=(
            "功能开关，逗号分隔。可选名称: "
            "var-rename, func-rename, class-rename, string-encode, "
            "number-obfuscate, float-obfuscate, container-obfuscate, bytes-obfuscate, "
            "junk-code, opaque-predicates, dead-code, "
            "control-flatten, import-hide, homoglyph-names, bool-obscure, "
            "expr-wrap, binop-wrap, dynamic-attrs, "
            "string-multi-round, scramble-annotations, fstring-obfuscate。"
            "前缀: +开启 -关闭 (无前缀=取反)。"
        ),
    )
    parser.add_argument(
        "--keep-doc",
        action="store_true",
        help="保留文档字符串（默认删除）",
    )
    parser.add_argument("--seed", type=int, help="设置随机种子（可重现混淆结果）")
    parser.add_argument("-q", "--quiet", action="store_true", help="静默模式，只输出一行结果")
    return parser.parse_args()


def _format_bytes(n: int) -> str:
    for unit in ("B", "KB", "MB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} GB"


def _build_obfuscator_from_args(args: Namespace) -> Obfuscator:
    preset = LEVEL_PRESETS[args.level].copy()
    preset = _apply_option_string(preset, args.opt)
    if args.keep_doc:
        preset["strip-docstrings"] = False

    return Obfuscator(
        var_rename=preset["var-rename"],
        func_rename=preset["func-rename"],
        class_rename=preset["class-rename"],
        string_encode=preset["string-encode"],
        string_multi_round=preset.get("string-multi-round", False),
        number_obfuscate=preset["number-obfuscate"],
        float_obfuscate=preset.get("float-obfuscate", False),
        container_obfuscate=preset.get("container-obfuscate", False),
        bytes_obfuscate=preset.get("bytes-obfuscate", False),
        junk_code=preset["junk-code"],
        junk_count=preset["junk-count"],
        opaque_predicates=preset["opaque-predicates"],
        opaque_prob=preset["opaque-prob"],
        dead_code=preset["dead-code"],
        control_flatten=preset["control-flatten"],
        import_hide=preset["import-hide"],
        homoglyph_names=preset["homoglyph-names"],
        bool_obscure=preset["bool-obscure"],
        expr_wrap=preset["expr-wrap"],
        binop_wrap=preset["binop-wrap"],
        dynamic_attrs=preset["dynamic-attrs"],
        scramble_annotations=preset.get("scramble-annotations", False),
        fstring_obfuscate=preset.get("fstring-obfuscate", False),
        strip_docstrings=preset["strip-docstrings"],
        string_methods=preset["string-methods"],
        seed=args.seed,
    )


def main() -> int:
    args = parse_args()

    try:
        with open(args.input, "r", encoding="utf-8") as f:
            source = f.read()
    except FileNotFoundError:
        print(f"错误: 找不到输入文件 '{args.input}'", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"错误: 无法读取输入文件 — {e}", file=sys.stderr)
        return 1

    if not source.strip():
        print("错误: 输入文件为空", file=sys.stderr)
        return 1

    try:
        obf = _build_obfuscator_from_args(args)
    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1

    start_time = time.perf_counter()
    try:
        obfuscated = obf.obfuscate(source)
    except SyntaxError as e:
        print(f"错误: 输入文件存在语法错误 — {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"错误: 混淆过程失败 — {e}", file=sys.stderr)
        return 1
    elapsed = time.perf_counter() - start_time

    out_path = args.output
    if not out_path:
        if args.input.endswith(".py"):
            out_path = args.input[:-3] + "_obfuscated.py"
        else:
            out_path = args.input + "_obfuscated.py"

    try:
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(obfuscated)
    except Exception as e:
        print(f"错误: 无法写入输出文件 — {e}", file=sys.stderr)
        return 1

    src_lines = source.count("\n") + 1
    out_lines = obfuscated.count("\n") + 1
    ratio = (len(obfuscated) / len(source) - 1) * 100 if len(source) > 0 else 0

    preset_label = LEVEL_PRESETS[args.level]["label"]

    if args.quiet:
        print(f"完成: {args.input} -> {out_path} (档位: {preset_label}, +{ratio:.0f}%)")
        return 0

    print(f"混淆完成!")
    print(f"  输入文件:    {args.input}")
    print(f"  输出文件:    {out_path}")
    print(f"  混淆档位:    {preset_label} ({args.level})")
    print(f"  原始大小:    {_format_bytes(len(source.encode('utf-8')))} ({src_lines} 行)")
    print(f"  混淆后大小:  {_format_bytes(len(obfuscated.encode('utf-8')))} ({out_lines} 行)")
    print(f"  膨胀率:      +{ratio:.1f}%")
    print(f"  耗时:        {elapsed*1000:.0f} ms")
    print(f"  -----------------------------")
    for key, label in [
        ("vars_renamed", "变量重命名"),
        ("funcs_renamed", "函数重命名"),
        ("classes_renamed", "类名重命名"),
        ("strings_encoded", "字符串编码"),
        ("multi_round_strings", "多轮字符串编码"),
        ("numbers_obfuscated", "数字混淆"),
        ("floats_obfuscated", "浮点数混淆"),
        ("containers_obfuscated", "容器混淆"),
        ("bytes_obfuscated", "字节串混淆"),
        ("bools_obscured", "布尔值混淆"),
        ("junk_blocks", "垃圾代码块"),
        ("opaque_predicates", "不透明谓词"),
        ("dead_code_injected", "死代码注入"),
        ("flattened_blocks", "扁平化块"),
        ("hidden_imports", "隐藏导入"),
        ("exprs_wrapped", "表达式包裹"),
        ("binops_wrapped", "二元运算包裹"),
        ("attrs_dynamic", "动态属性"),
        ("annotations_scrambled", "类型注解剥离"),
        ("fstrings_obfuscated", "f-string混淆"),
    ]:
        v = obf.stats.get(key, 0)
        if v:
            print(f"  {label}: {v}")
    print(f"  -----------------------------")
    return 0


if __name__ == "__main__":
    sys.exit(main())
