#!/usr/bin/env python3
"""
Python 代码混淆器（优化版）
支持多种高级混淆技术，增强抗反编译能力。
"""

import ast
import base64
import random
import string
import sys
from argparse import ArgumentParser, Namespace
from typing import Dict, List, Optional, Set, Union


class Obfuscator(ast.NodeTransformer):
    """增强版 Python 代码混淆器"""

    def __init__(
        self,
        rename_vars: bool = True,
        rename_funcs: bool = True,
        rename_classes: bool = True,
        rename_attrs: bool = True,
        encode_strings: bool = True,
        encode_numbers: bool = False,
        add_junk: bool = True,
        flatten_control: bool = False,
        remove_comments: bool = True,
        remove_docstrings: bool = True,
        seed: Optional[int] = None,
    ) -> None:
        self.rename_vars = rename_vars
        self.rename_funcs = rename_funcs
        self.rename_classes = rename_classes
        self.rename_attrs = rename_attrs
        self.encode_strings = encode_strings
        self.encode_numbers = encode_numbers
        self.add_junk = add_junk
        self.flatten_control = flatten_control
        self.remove_comments = remove_comments
        self.remove_docstrings = remove_docstrings

        if seed is not None:
            random.seed(seed)

        self.reserved: Set[str] = self._build_reserved_names()
        self.name_mapping: Dict[str, str] = {}
        self.used_names: Set[str] = set()
        self.scope_stack: List[Set[str]] = []
        self.parent_stack: List[ast.AST] = []  # 父节点栈，用于判断上下文

    # ---------- 保留名称处理 ----------
    def _build_reserved_names(self) -> Set[str]:
        import keyword
        import builtins

        reserved = set(keyword.kwlist)
        reserved.update(dir(builtins))
        reserved.update(
            {
                "self",
                "cls",
                "True",
                "False",
                "None",
                "__name__",
                "__main__",
                "__file__",
                "__doc__",
                "__init__",
                "__new__",
                "__str__",
                "__repr__",
                "__call__",
                "__getitem__",
                "__setitem__",
                "__len__",
                "__iter__",
                "__next__",
                "__enter__",
                "__exit__",
                "List",
                "Dict",
                "Set",
                "Tuple",
                "Optional",
                "Union",
                "Any",
            }
        )
        return reserved

    def _is_special_method(self, name: str) -> bool:
        return name.startswith("__") and name.endswith("__")

    def _is_reserved(self, name: str) -> bool:
        return name in self.reserved or self._is_special_method(name)

    def _generate_name(self, prefix: str = "") -> str:
        while True:
            length = random.randint(8, 16)
            chars = string.ascii_letters + "_"
            name = prefix + "".join(random.choices(chars, k=length))
            if name[0].isdigit():
                continue
            if name not in self.reserved and name not in self.used_names:
                self.used_names.add(name)
                return name

    def _mapped_name(self, original: str, prefix: str = "") -> str:
        if self._is_reserved(original):
            return original
        if original not in self.name_mapping:
            self.name_mapping[original] = self._generate_name(prefix)
        return self.name_mapping[original]

    # ---------- AST 遍历主入口 ----------
    def visit(self, node: ast.AST) -> ast.AST:
        """重写 visit 以维护父节点栈"""
        self.parent_stack.append(node)
        result = super().visit(node)
        self.parent_stack.pop()
        return result

    def obfuscate(self, code: str) -> str:
        tree = ast.parse(code)
        tree = self.visit(tree)
        tree = ast.fix_missing_locations(tree)
        if self.remove_docstrings:
            tree = DocstringRemover().visit(tree)
            tree = ast.fix_missing_locations(tree)
        obfuscated = ast.unparse(tree)
        if self.remove_comments:
            lines = [line for line in obfuscated.splitlines() if line.strip() != ""]
            obfuscated = "\n".join(lines)
        return obfuscated

    # ---------- 辅助方法：标记文档字符串 ----------
    def _mark_docstring(self, node: ast.AST) -> None:
        if not hasattr(node, "body") or not node.body:
            return
        first = node.body[0]
        if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str):
            first.value.is_docstring = True

    def _in_fstring(self) -> bool:
        """检查当前节点是否位于 f-string (JoinedStr) 内部"""
        for parent in reversed(self.parent_stack):
            if isinstance(parent, ast.JoinedStr):
                return True
        return False

    # ---------- 名称混淆 ----------
    def visit_Module(self, node: ast.Module) -> ast.Module:
        self._mark_docstring(node)
        self.generic_visit(node)
        return node

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        self._mark_docstring(node)
        if self.rename_funcs and not self._is_special_method(node.name):
            node.name = self._mapped_name(node.name, "f_")
        self.scope_stack.append(set())
        self.generic_visit(node)
        self.scope_stack.pop()
        if self.add_junk:
            junk_stmts = self._generate_junk_code()
            insert_pos = 0
            if node.body and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant) and isinstance(node.body[0].value.value, str):
                insert_pos = 1
            node.body[insert_pos:insert_pos] = junk_stmts
        return node

    def visit_ClassDef(self, node: ast.ClassDef) -> ast.ClassDef:
        self._mark_docstring(node)
        if self.rename_classes and not self._is_reserved(node.name):
            node.name = self._mapped_name(node.name, "C_")
        self.scope_stack.append(set())
        self.generic_visit(node)
        self.scope_stack.pop()
        return node

    def visit_Name(self, node: ast.Name) -> ast.Name:
        if not self.rename_vars:
            return node
        if isinstance(node.ctx, (ast.Store, ast.Load, ast.Del)):
            if not self._is_reserved(node.id):
                node.id = self._mapped_name(node.id, "v_")
        return node

    def visit_arg(self, node: ast.arg) -> ast.arg:
        if self.rename_vars and not self._is_reserved(node.arg):
            node.arg = self._mapped_name(node.arg, "a_")
        return node

    def visit_Attribute(self, node: ast.Attribute) -> ast.Attribute:
        if self.rename_attrs and not self._is_reserved(node.attr):
            pass  # 保守策略，暂不重命名
        self.generic_visit(node)
        return node

    def visit_Import(self, node: ast.Import) -> ast.Import:
        for alias in node.names:
            if alias.asname:
                if self.rename_vars and not self._is_reserved(alias.asname):
                    alias.asname = self._mapped_name(alias.asname, "imp_")
            else:
                base_name = alias.name.split(".")[0]
                self.reserved.add(base_name)
        return node

    def visit_ImportFrom(self, node: ast.ImportFrom) -> ast.ImportFrom:
        for alias in node.names:
            if alias.asname:
                if self.rename_vars and not self._is_reserved(alias.asname):
                    alias.asname = self._mapped_name(alias.asname, "imp_")
            else:
                if alias.name != "*":
                    self.reserved.add(alias.name)
        return node

    # ---------- 字符串与数字编码 ----------
    def visit_Constant(self, node: ast.Constant) -> Union[ast.Constant, ast.Expr]:
        # 跳过文档字符串
        if hasattr(node, "is_docstring") and node.is_docstring:
            return node
        # 跳过 f-string 内的字符串
        if self._in_fstring():
            return node
        # 字符串编码
        if self.encode_strings and isinstance(node.value, str) and node.value:
            encoded = base64.b64encode(node.value.encode()).decode()
            new_node = ast.parse(
                f"__import__('base64').b64decode({repr(encoded)}).decode()"
            ).body[0].value
            ast.fix_missing_locations(new_node)
            return new_node
        # 数字编码
        if self.encode_numbers and isinstance(node.value, (int, float)):
            val = node.value
            if isinstance(val, int) and abs(val) < 10000:
                a = random.randint(1, val - 1) if val > 0 else random.randint(val, -1)
                b = val - a
                new_node = ast.BinOp(
                    left=ast.Constant(value=a), op=ast.Add(), right=ast.Constant(value=b)
                )
                ast.fix_missing_locations(new_node)
                return new_node
        return node

    # ---------- 垃圾代码生成 ----------
    def _generate_junk_code(self) -> List[ast.stmt]:
        junk_var = f"_junk_{random.randint(1000, 9999)}"
        return [
            ast.Assign(
                targets=[ast.Name(id=junk_var, ctx=ast.Store())],
                value=ast.Constant(value=random.randint(0, 100)),
            ),
            ast.If(
                test=ast.Compare(
                    left=ast.Constant(value=1), ops=[ast.Gt()], comparators=[ast.Constant(value=2)]
                ),
                body=[ast.Pass()],
                orelse=[],
            ),
            ast.For(
                target=ast.Name(id="_", ctx=ast.Store()),
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

    def _remove_docstring(self, node: ast.AST) -> None:
        if not hasattr(node, "body"):
            return
        body = getattr(node, "body")
        if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
            if isinstance(body[0].value.value, str):
                del body[0]


# ---------- 命令行接口 ----------
def parse_args() -> Namespace:
    parser = ArgumentParser(description="Python 代码混淆器（优化版）")
    parser.add_argument("input", help="输入文件路径")
    parser.add_argument("-o", "--output", help="输出文件路径")
    parser.add_argument("--no-rename-vars", action="store_true", help="不重命名变量")
    parser.add_argument("--no-rename-funcs", action="store_true", help="不重命名函数")
    parser.add_argument("--no-rename-classes", action="store_true", help="不重命名类名")
    parser.add_argument("--no-encode-strings", action="store_true", help="不编码字符串")
    parser.add_argument("--encode-numbers", action="store_true", help="混淆数字常量（实验性）")
    parser.add_argument("--no-junk", action="store_true", help="不添加垃圾代码")
    parser.add_argument("--keep-docstrings", action="store_true", help="保留文档字符串")
    parser.add_argument("--seed", type=int, help="设置随机种子（可重现混淆结果）")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        with open(args.input, "r", encoding="utf-8") as f:
            source = f.read()
    except Exception as e:
        print(f"✗ 无法读取输入文件: {e}", file=sys.stderr)
        return 1

    obf = Obfuscator(
        rename_vars=not args.no_rename_vars,
        rename_funcs=not args.no_rename_funcs,
        rename_classes=not args.no_rename_classes,
        encode_strings=not args.no_encode_strings,
        encode_numbers=args.encode_numbers,
        add_junk=not args.no_junk,
        remove_docstrings=not args.keep_docstrings,
        seed=args.seed,
    )

    try:
        obfuscated = obf.obfuscate(source)
    except Exception as e:
        print(f"✗ 混淆过程出错: {e}", file=sys.stderr)
        return 1

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
        print(f"✗ 无法写入输出文件: {e}", file=sys.stderr)
        return 1

    print(f"✓ 混淆完成!")
    print(f"  输入: {args.input}")
    print(f"  输出: {out_path}")
    print(f"  原始大小: {len(source)} 字节")
    print(f"  混淆后大小: {len(obfuscated)} 字节")
    return 0


if __name__ == "__main__":
    sys.exit(main())