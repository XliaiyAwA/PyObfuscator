# Python 代码混淆器 \(PyObfuscator\)

一个功能强大的 Python 源代码混淆工具，基于 AST（抽象语法树）转换技术，能够在保持代码功能完全不变的前提下，大幅提升代码的阅读难度，有效防止简单的代码逆向和抄袭。

## ✨ 主要特性

- \*\*标识符混淆\*\*：随机重命名变量、函数、类名、参数，生成无意义名称

- \*\*字符串加密\*\*：将字符串常量编码为 Base64，运行时动态解码

- \*\*数字混淆\*\*：将简单数字常量替换为等效算术表达式（如 \`42\` → \`21 \* 2\`）

- \*\*垃圾代码注入\*\*：插入永不执行的无用代码，干扰静态分析

- \*\*注释与文档字符串移除\*\*：自动清除所有注释和文档字符串

- \*\*导入保护\*\*：自动识别并保留导入的模块名，避免破坏外部依赖

- \*\*可重现混淆\*\*：支持设置随机种子，便于调试和版本控制

- \*\*灵活配置\*\*：提供丰富的命令行选项，可自由组合混淆策略

## 📦 环境要求

- Python 3\.8 或更高版本

- 无需安装第三方库（仅使用标准库 \`ast\`, \`base64\`, \`random\`, \`argparse\` 等）

## 🚀 快速开始

```bash
# 指定输出文件
python obfuscator.py example.py -o output.py

# 固定随机种子（可重现混淆）
python obfuscator.py example.py --seed 2024

# 轻度混淆（仅重命名，不加密字符串、不注入垃圾代码）
python obfuscator.py example.py --no-encode-strings --no-junk

# 保留文档字符串
python obfuscator.py example.py --keep-docstrings

# 基础混淆（默认配置，生成原文件名_obfuscated.py）
python obfuscator.py example.py
```

## 📖 命令行参数详解

|参数|简写|说明|
|---|---|---|
|input|\-|必需，输入的 Python 文件路径|
|\-\-output|\-o|输出文件路径（默认：原文件名\_obfuscated\.py）|
|\-\-no\-rename\-vars|\-|禁用变量名混淆|
|\-\-no\-rename\-funcs|\-|禁用函数名混淆|
|\-\-no\-rename\-classes|\-|禁用类名混淆|
|\-\-no\-encode\-strings|\-|禁用字符串编码|
|\-\-encode\-numbers|\-|启用数字常量混淆（实验性）|
|\-\-no\-junk|\-|禁用垃圾代码注入|
|\-\-keep\-docstrings|\-|保留文档字符串|
|\-\-seed SEED|\-|设置随机种子（整数），保证混淆结果可重现|

## 📝 使用示例

### 原始代码 \(example\.py\)

```python
def calculate_sum(a, b):
    """计算两数之和"""
    result = a + b
    print(f"The sum is: {result}")
    return result

if __name__ == "__main__":
    calculate_sum(10, 20)
```

### 混淆后代码 \(example\_obfuscated\.py\)

```python
def f_lkasjdfh(a_qwezx, a_tyuip):
    _junk_4821 = 73
    if 1 > 2:
        pass
    for _ in range(0):
        pass
    v_aeoruy = a_qwezx + a_tyuip
    print(__import__('base64').b64decode('VGhlIHN1bSBpczog').decode() + str(v_aeoruy))
    return v_aeoruy

if __name__ == '__main__':
    f_lkasjdfh(10, 20)
```

💡 运行结果：混淆后的代码执行结果与原代码完全一致。

## 🛡️ 保护机制说明

### 不会被混淆的名称

以下名称会被自动识别并保留原样，确保代码正常运行：

- Python 关键字（if, for, while, def, class 等）

- 内置函数与异常（print, len, range, TypeError 等）

- 特殊方法（\_\_init\_\_, \_\_str\_\_, \_\_call\_\_ 等）

- 导入的模块名（import os 中的 os）

### 字符串编码

所有字符串字面量（除文档字符串）会被转换为：

```python
__import__('base64').b64decode('...').decode()
```

运行时动态解码，静态分析工具无法直接获取原文。

### 数字混淆（可选）

开启 \-\-encode\-numbers 后，简单整数常量会被替换为随机拆分表达式：

```python
# 原始: 42
# 混淆后: 19 + 23  或 84 // 2
```

## ⚠️ 注意事项

- 务必保留原始代码：混淆是不可逆过程，混淆后的代码无法恢复为原始形式。

- 功能测试：混淆后请务必运行一次程序，确保功能完整。

- 动态特性兼容性：如果代码使用了 eval\(\), exec\(\), getattr\(\), inspect 等动态特性，建议关闭名称混淆选项。

- 性能影响：字符串编码会略微增加运行开销，对性能要求极高的场景可禁用该选项。

- 分发限制：本工具仅用于合法目的，请遵守相关软件许可协议。

## 🔧 技术原理

- AST 解析与转换：使用 Python 标准库 ast 将源代码解析为抽象语法树，通过自定义 NodeTransformer 修改节点。

- 名称映射：维护原始标识符到混淆名称的映射表，确保同一变量在作用域内命名一致。

- 作用域感知：追踪函数和类的作用域，避免跨作用域名称冲突。

- Base64 编码：字符串在混淆时编码，运行时通过内置 base64 模块解码。

## 📄 许可证

本项目仅供学习、研究及合法用途。使用本工具产生的任何后果由使用者自行承担。

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！改进建议包括但不限于：

- 增加更多混淆策略（控制流扁平化、不透明谓词等）

- 优化性能

- 完善单元测试

⚠️ 免责声明：本工具旨在帮助开发者保护自己的代码知识产权，禁止用于任何恶意目的或违反软件许可协议的行为。使用者应遵守当地法律法规。

> （注：文档部分内容可能由 AI 生成）

