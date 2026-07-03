

一款基于 AST 的 Python 代码混淆工具，支持 Python 3.11 ~ 3.13 语法，提供三档混淆强度预设和 20+ 项可配置选项，通过多维度混淆手段大幅提升代码的逆向分析难度。

---

## 环境需求

- **Python >= 3.11**（使用了 `ast.Match`、`ast.ExceptStar`、`TypeAlias` 等 3.10~3.12 新增 AST 节点）
- 无第三方依赖，仅使用 Python 标准库（`ast`、`base64`、`hashlib`、`zlib`、`struct` 等）

---

## 快速开始

```bash
# 基本用法（默认标准档位）
python obfuscator_ultimate_fixed_v2.py input.py

# 指定输出文件
python obfuscator_ultimate_fixed_v2.py input.py -o output.py

# 使用轻量档位
python obfuscator_ultimate_fixed_v2.py input.py -l light

# 使用强化档位
python obfuscator_ultimate_fixed_v2.py input.py -l heavy

# 在标准档位基础上开启同形字命名和动态属性
python obfuscator_ultimate_fixed_v2.py input.py -O "+homoglyph-names,+dynamic-attrs"

# 在强化档位基础上关闭控制流扁平化
python obfuscator_ultimate_fixed_v2.py input.py -l heavy -O "-control-flatten"

# 保留文档字符串
python obfuscator_ultimate_fixed_v2.py input.py --keep-doc

# 指定随机种子（可重现混淆结果）
python obfuscator_ultimate_fixed_v2.py input.py --seed 42

# 静默模式
python obfuscator_ultimate_fixed_v2.py input.py -q
```

---

## 命令行参数

| 参数 | 说明 |
|------|------|
| `input` | 输入文件路径（必填） |
| `-o`, `--output` | 输出文件路径（默认：`<输入文件名>_obfuscated.py`） |
| `-l`, `--level` | 混淆强度档位：`light`（轻量）、`standard`（标准，默认）、`heavy`（强化） |
| `-O`, `--opt` | 功能开关微调，详见下方 [功能开关详解](#功能开关详解) |
| `--keep-doc` | 保留文档字符串（默认删除） |
| `--seed` | 设置随机种子，用于可重现的混淆输出 |
| `-q`, `--quiet` | 静默模式，只输出一行结果摘要 |

### 功能开关详解

`-O` / `--opt` 用于在当前档位预设的基础上，精细调整单个混淆选项的开关状态。多个选项用逗号分隔，每个选项支持三种写法：

| 写法 | 含义 | 示例 |
|------|------|------|
| `+选项名` | 强制**开启**该选项 | `+homoglyph-names` |
| `-选项名` | 强制**关闭**该选项 | `-dead-code` |
| `选项名`（无前缀） | **取反**该选项（开变关、关变开） | `junk-code` |

可用的选项名与下方一致（即三档预设表中的各选项对应的英文标识）：

```
var-rename, func-rename, class-rename, string-encode,
string-multi-round, number-obfuscate, float-obfuscate,
container-obfuscate, bytes-obfuscate, junk-code,
opaque-predicates, dead-code, control-flatten, import-hide,
homoglyph-names, bool-obscure, expr-wrap, binop-wrap,
dynamic-attrs, scramble-annotations, fstring-obfuscate
```

**使用示例：**

```bash
# 在标准档位基础上，额外开启同形字命名和动态属性
python obfuscator.py input.py -O "+homoglyph-names,+dynamic-attrs"

# 在强化档位基础上，关闭死代码注入和控制流扁平化
python obfuscator.py input.py -l heavy -O "-dead-code,-control-flatten"

# 在轻量档位基础上，开启数字混淆和浮点混淆
python obfuscator.py input.py -l light -O "+number-obfuscate,+float-obfuscate"

# 在标准档位基础上，关闭垃圾代码（标准预设默认开启，取反后关闭）
python obfuscator.py input.py -O "junk-code"

# 同时开启多个选项
python obfuscator.py input.py -l light -O "+number-obfuscate,+float-obfuscate,+bool-obscure,+opaque-predicates"

# 在强化档位基础上关闭导入隐藏，同时开启同形字命名
python obfuscator.py input.py -l heavy -O "-import-hide,+homoglyph-names"
```

> **提示**：`-O` 的修改是在档位预设之上叠加的。先加载预设的所有默认值，再按 `-O` 中的指令逐一调整。因此可以用轻量档位 + 手动开启选项的方式，自定义出任意组合。

---

## 三档预设

| 选项 | 轻量 (light) | 标准 (standard) | 强化 (heavy) |
|------|:---:|:---:|:---:|
| 变量重命名 | ✅ | ✅ | ✅ |
| 函数重命名 | ✅ | ✅ | ✅ |
| 类名重命名 | ✅ | ✅ | ✅ |
| 字符串编码 | ✅ | ✅ | ✅ |
| 多轮字符串编码 | — | ✅ | ✅ |
| 数字混淆 | ✅ | ✅ | ✅ |
| 浮点数混淆 | ✅ | ✅ | ✅ |
| 容器混淆 | — | ✅ | ✅ |
| 字节串混淆 | — | ✅ | ✅ |
| 垃圾代码 | — | ✅ (3块) | ✅ (4块) |
| 不透明谓词 | — | ✅ (35%) | ✅ (65%) |
| 死代码注入 | — | ✅ | ✅ |
| 控制流扁平化 | — | ✅ | ✅ |
| 导入隐藏 | ✅ | ✅ | ✅ |
| 布尔值混淆 | — | ✅ | ✅ |
| 表达式包裹 | — | ✅ | ✅ |
| 二元运算包裹 | — | ✅ | ✅ |
| 类型注解剥离 | — | ✅ | ✅ |
| f-string 混淆 | — | ✅ | ✅ |
| 同形字命名 | — | — | — |
| 动态属性 | — | — | — |
| 文档字符串移除 | ✅ | ✅ | ✅ |

> 同形字命名 (`homoglyph-names`) 和动态属性 (`dynamic-attrs`) 在所有预设中默认关闭，需通过 `-O` 手动开启。

---

## 🛡️选项详解

### 名称混淆

| 选项 | 说明 |
|------|------|
| `var-rename` | 重命名变量为视觉混淆名称（如 `O0Il1l...`），支持 `global`/`nonlocal` 语句 |
| `func-rename` | 重命名用户定义的函数和异步函数（保留魔术方法如 `__init__`） |
| `class-rename` | 重命名用户定义的类 |
| `homoglyph-names` | 使用 Unicode 同形字（西里尔字母替代拉丁字母）进一步混淆标识符，使名称在视觉上几乎相同但编码不同 |

### 字符串与常量混淆

| 选项 | 说明 |
|------|------|
| `string-encode` | 对字符串常量进行编码，支持 **11 种编码方法**：xor-base64、zlib-base64、hex-xor、split-encode、reverse、shuffle、multi-layer、rot13-base64、hash-verify、zlib-xor、hex-encode |
| `string-multi-round` | 多轮链式字符串编码，组合多种编码方法叠加处理，大幅增加解码难度 |
| `number-obfuscate` | 对整数常量进行混淆，支持 **10 种方法**：XOR、位移、加减、乘除、列表长度、位运算组合、拆分、嵌套 lambda、range 长度、幂运算 |
| `float-obfuscate` | 对浮点数常量进行混淆，支持 5 种方法：hex 表示、乘除、整数除法、struct 二进制打包、数学变换。精确保持位模式不变 |
| `container-obfuscate` | 混淆容器字面量（list、tuple、set、dict），如将 `[]` 替换为 `list()`，将 `[1,2]` 包裹为 `list((1,2))` |
| `bytes-obfuscate` | 对 bytes 常量进行 XOR + Base64 编码 |
| `bool-obscure` | 将 `True`/`False` 替换为等价的复杂表达式（如 `1 > 0`、`len([]) > 0`、`(lambda: True)()` 等） |

### 控制流混淆

| 选项 | 说明 |
|------|------|
| `control-flatten` | 将函数体内的顺序语句扁平化为 `while` 循环 + 状态变量 + `if-elif` 链，破坏原始控制流结构。自动跳过递归函数和含提前退出（return/break/continue）的函数 |
| `opaque-predicates` | 在 `if`/`while`/`for` 条件中插入不透明谓词（22 种永真/永假模式），使静态分析无法确定分支走向 |
| `dead-code` | 注入永远不会执行的死代码块（由不透明永假谓词保护），包含 12 种伪造代码模式（赋值、循环、异常处理、条件分支等） |

### 代码注入与结构变换

| 选项 | 说明 |
|------|------|
| `junk-code` | 在函数体中插入垃圾代码块，支持 **20 种模式**：死赋值、空循环、假条件、try-except、lambda 死代码、上下文管理器、断言、字典操作、集合操作、字符串拼接、数学链、元组解包、列表切片、while-false、with-pass、推导式、三元表达式、增强赋值、星号解包等 |
| `import-hide` | 将 `import X` / `from X import Y` 转换为 `__import__()` 动态调用，隐藏模块依赖关系。保留 `__future__` 导入不变 |
| `dynamic-attrs` | 将属性访问 `obj.attr` 随机转换为 `getattr(obj, <encoded_name>)` 动态调用，属性名字符串经过编码处理 |

### 表达式变换

| 选项 | 说明 |
|------|------|
| `expr-wrap` | 对变量引用表达式进行包裹，如 `[x][0]`、`(x,)[0]`、`[[x]][0][0]`、`(lambda _: _)(x)` |
| `binop-wrap` | 对二元运算表达式进行包裹，如添加不透明谓词条件 `expr if <opaque_true> else expr`，或添加 `+ 0`、`* 1` 恒等变换 |
| `fstring-obfuscate` | 将 f-string 转换为 `''.format()` 调用，模板字符串经过 XOR + Base64 编码 |

### 其他

| 选项 | 说明 |
|------|------|
| `scramble-annotations` | 剥离类型注解：函数返回类型注解置空，变量类型注解转为普通赋值或替换为 `None`，参数注解移除 |
| `strip-docstrings` | 移除模块、类、函数、异步函数的文档字符串（默认开启，可通过 `--keep-doc` 关闭） |

---

## 功能特性总览

- **三档强度预设**：轻量 / 标准 / 强化，一键切换，也支持通过 `-O` 精细调控每个选项
- **20+ 混淆选项**：每项可独立开关，`+` 开启 / `-` 关闭 / 无前缀取反
- **11 种字符串编码方法**：XOR+Base64、zlib+Base64、hex+XOR、分段编码、反转、乱序、多层、ROT13+Base64、哈希校验、zlib+XOR、纯 hex
- **10 种整数混淆方法**：XOR、位移、加减、乘除、列表长度、位运算组合、拆分、嵌套 lambda、range 长度、幂运算
- **5 种浮点混淆方法**：hex 精确表示、struct 二进制打包、数学变换等
- **22 种不透明谓词模式**：永真/永假各 22 种，用于条件注入和死代码保护
- **20 种垃圾代码模式**：涵盖赋值、循环、条件、异常、lambda、推导式等多种代码结构
- **12 种死代码伪造模式**：在不透明永假谓词保护下注入逼真的伪代码块
- **控制流扁平化**：将顺序语句转换为 while 循环 + 状态机，破坏结构化控制流
- **完整的新语法支持**：Python 3.10 `match/case`、3.11 异常组 `except*`、3.12 `type` 语句 / `TypeAlias` / `TypeVar` / `ParamSpec` / `TypeVarTuple`
- **智能保护机制**：保留关键字、内建名称、魔术方法、标准库属性名不被误改
- **导入隐藏**：将静态 import 转换为 `__import__()` 动态调用
- **f-string 混淆**：转换为 `.format()` 调用并编码模板
- **类型注解剥离**：移除所有类型注解降低代码可读性
- **可重现输出**：通过 `--seed` 参数设置随机种子
- **详细统计报告**：混淆完成后输出各项操作的执行次数

---

## 输出示例

```
混淆完成!
  输入文件:    example.py
  输出文件:    example_obfuscated.py
  混淆档位:    标准 (standard)
  原始大小:    2.3 KB (85 行)
  混淆后大小:  12.8 KB (342 行)
  膨胀率:      +456.5%
  耗时:        23 ms
  -----------------------------
  变量重命名: 42
  函数重命名: 8
  类名重命名: 2
  字符串编码: 31
  数字混淆: 15
  垃圾代码块: 24
  不透明谓词: 12
  死代码注入: 6
  扁平化块: 5
  隐藏导入: 3
  表达式包裹: 9
  二元运算包裹: 7
  类型注解剥离: 1
  f-string混淆: 4
  -----------------------------
```

---

## ⚠️ 注意事项

1. 混淆后的代码体积会显著膨胀，膨胀率取决于源文件大小和所选档位
2. `homoglyph-names`（同形字命名）可能导致在某些编辑器或终端中显示异常，所有预设中默认关闭
3. `dynamic-attrs`（动态属性）会增加运行时开销，所有预设中默认关闭
4. 控制流扁平化会自动跳过递归函数和包含 `return`/`break`/`continue`/`yield`/`raise` 的函数体
5. 混淆器会自动保留 Python 关键字、内建函数名、魔术方法（`__xxx__`）以及常见标准库属性名
6. 输入文件必须是合法的 Python 源代码

---

## 📄 许可证&免责声明

本项目仅供学习、研究及合法用途。使用本工具产生的任何后果由使用者自行承担。
>⚠️ 免责声明：本工具旨在帮助开发者保护自己的代码知识产权，禁止用于任何恶意目的或违反软件许可协议的行为。使用者应遵守当地法律法规。

> （注：文档部分内容可能由 AI 生成）
