# FilePilot

## 📄 License

本项目基于 MIT License 发布。详见 [LICENSE](LICENSE)。

> 一个用 Python 标准库手敲出来的本地文件整理、扫描与日志分析 CLI 工具。  
> v0.1.0 先完成最小闭环：**扫描目录 → 收集文件信息 → 输出 JSON**。

![Version](https://img.shields.io/badge/version-v0.1.0-blue)
![Python](https://img.shields.io/badge/python-3.10%2B-3776AB)
![License](https://img.shields.io/badge/license-MIT-green)
![Tests](https://img.shields.io/badge/tests-34%20passed%20%7C%201%20skipped-brightgreen)
![Status](https://img.shields.io/badge/status-early%20preview-orange)

---

## 📌 项目简介

FilePilot 是一个学习驱动、逐步迭代的 Python 实战项目。

它不是一下子做成“大而全”的工具，而是按照版本推进：

- **v0.1.0**：目录扫描 + 文件信息收集 + JSON 输出
- **v0.2.0**：规则引擎 + 文件整理 + dry-run + undo
- **v0.3.0**：重复文件检测 + 线程 / 进程并发
- **v0.4.0**：日志分析 + 协程 + 报告生成
- **v1.0.0**：测试、CI、打包、发布

当前版本是 **v0.1.0**，开发时间：**2026.09.14 - 2026.09.16**。

---

## ✨ v0.1.0 特性

- [x] 递归扫描指定目录（`os.walk` 生成器，不一次性载入内存）
- [x] 默认跳过隐藏文件和隐藏目录（Windows 下同时识别“隐藏”属性，跨平台识别 `.` 前缀）
- [x] `--include-hidden` / `--no-skip-hidden` 扫描隐藏内容
- [x] `--follow-symlinks` 控制是否跟随符号链接（默认跳过）
- [x] `--max-depth` 限制扫描深度
- [x] 收集文件信息：路径、绝对路径、名称、后缀、大小、修改时间
- [x] 读取 / 权限错误不崩溃，统一记录到 `errors`；无法进入的目录也会被收集
- [x] 输出 JSON（缩进 + `ensure_ascii=False`）；`-o` 写文件（父目录自动创建），否则打印到 stdout
- [x] `-v / --verbose` 打印扫描统计
- [x] `--version` 输出版本号，提供清晰退出码

> v0.1.0 不包含：正则规则、文件移动、删除、去重、线程、进程、协程、undo。  
> 这些会在后续版本逐步加入。

---

## 🚀 快速开始

### 环境要求

- Python 3.10+（`scanner.py` 使用了 `int | None` 写法）
- 无第三方依赖，纯标准库实现（跑测试用 `unittest` 即可，`pytest` 可选）

### 克隆项目

```bash
git clone https://github.com/WileDogUnderTheTree/filepilot.git
cd filepilot
```

### 直接运行

```bash
python -m filepilot scan . --output files.json
```

如果你已经配置了 `pyproject.toml`，也可以：

```bash
pip install -e .
filepilot scan . --output files.json
```

---

## 🧭 命令用法

```bash
python -m filepilot scan <directory> [options]
python -m filepilot --version
```

### 参数说明

| 参数 | 说明 | 默认值 |
|---|---|---|
| `directory` | 要扫描的目录 | 必填 |
| `-o, --output` | JSON 输出文件路径（父目录不存在会自动创建） | 不传则打印到 stdout |
| `--no-skip-hidden` | 不跳过隐藏文件 / 隐藏目录 | 关闭（即默认跳过） |
| `--include-hidden` | 同上，别名 | 关闭 |
| `--follow-symlinks` | 跟随符号链接 | 关闭（即默认跳过符号链接） |
| `--max-depth N` | 最大扫描深度，根目录深度为 0 | 不限 |
| `-v, --verbose` | 打印“扫描完成：N 个文件，M 个错误” | 关闭 |
| `--version` | 打印 `filepilot 0.1.0` | — |
| `-h, --help` | 帮助信息 | — |

> `-v` 既可写在子命令前（`filepilot -v scan .`），也可写在子命令后（`filepilot scan . -v`）。

### 示例

```bash
# 扫描当前目录，JSON 打印到 stdout
python -m filepilot scan .

# 指定输出文件（嵌套目录会自动创建）
python -m filepilot scan ./downloads -o reports/files.json -v

# 包含隐藏文件和隐藏目录
python -m filepilot scan . --include-hidden

# 只扫描顶层
python -m filepilot scan . --max-depth 1

# 跟随符号链接
python -m filepilot scan . --follow-symlinks
```

---

## 📤 输出示例

```json
{
  "metadata": {
    "tool": "filepilot",
    "version": "0.1.0",
    "scan_time": "2026-09-16T20:14:14.370367"
  },
  "summary": {
    "root": "D:\\FilePilot CLI\\filepilot",
    "file_count": 3,
    "total_size": 9421,
    "error_count": 1
  },
  "files": [
    {
      "path": "D:\\FilePilot CLI\\filepilot\\cli.py",
      "absolute_path": "D:\\FilePilot CLI\\filepilot\\cli.py",
      "name": "cli.py",
      "size": 5673,
      "extension": ".py",
      "modified_time": "2026-09-16T20:14:14.367846"
    }
  ],
  "errors": [
    {
      "path": "D:\\FilePilot CLI\\private",
      "error_type": "access",
      "message": "[WinError 5] 拒绝访问。"
    }
  ]
}
```

- `summary.root` / `files[].path`：传入什么路径就原样输出（相对路径不会被强制转绝对路径）
- `files[].extension`：后缀统一小写；无后缀或 `.` 开头的隐藏文件为 `""`
- `files[].modified_time`：本地时间的 ISO 8601 字符串
- `errors[].error_type`：`access`（权限 / 读取失败）或 `unknown`

---

## 🚦 退出码

| 退出码 | 含义 |
|---|---|
| `0` | 扫描成功，没有错误 |
| `1` | 目录不存在 / 不是目录；或扫描过程中存在读取错误；或未提供子命令（打印帮助） |
| `2` | 命令行参数错误（argparse 默认行为，例如未知参数） |
| `130` | 用户 Ctrl+C 中断 |

> 注意：**目录不存在返回 1**（不是 2），这一点由 `tests/test_cli.py::test_scan_command_not_found` 锁定。

---

## 🗂️ 项目结构

```text
FilePilot CLI/
├── filepilot/
│   ├── __init__.py        # 版本与作者信息
│   ├── __main__.py        # python -m filepilot 入口
│   ├── cli.py             # argparse 解析 + scan 子命令 + JSON 输出
│   ├── exceptions.py      # FilePilotError / DirectoryNotFoundError / FileAccessError / ScanError
│   ├── models.py          # FileItem 数据类（from_path / to_dict / 大小格式化）
│   └── scanner.py         # Scanner：遍历目录、跳过隐藏项、收集错误
├── tests/
│   ├── test_cli.py        # CLI 参数解析、scan 命令、保存文件
│   ├── test_models.py     # FileItem 属性、扩展名、格式化
│   ├── test_scanner.py    # 扫描、隐藏项、深度、权限、符号链接、性能
│   ├── run_tests.py       # unittest 运行器（可只跑单个模块/用例）
│   ├── smoke_e2e.py       # 端到端冒烟测试（真实调用 python -m filepilot）
│   └── run_all_tests.ps1  # 一键跑 unittest + pytest + E2E
├── docs/
│   └── 题目.txt            # 项目需求与路线图
├── pyproject.toml
└── README.md
```

> 计划中但**尚未创建**：`LICENSE`、`.gitignore`、`examples/`、`filepilot/utils/`、GitHub Actions。  
> 这些属于 v1.0.0 的发布清单，先不写进“已完成”。

---

## 🧱 设计概览

v0.1.0 的核心链路非常短：

```text
CLI（argparse） → Scanner → FileItem → dict → JSON（stdout / 文件）
```

### 核心类

| 类 | 职责 |
|---|---|
| `FileItem` | 描述单个文件：路径、大小、后缀、修改时间；`from_path()` 读 stat，`to_dict()` 供 JSON 序列化 |
| `Scanner` | 递归遍历目录、跳过隐藏项 / 符号链接 / 超深目录，把读取失败收集进 `errors`，维护 `file_count` 与 `total_size` |
| `ScanError` | 单条扫描错误：`path` / `error_type` / `message`，带 `to_dict()` 便于写 JSON |
| `FilePilotError` | 项目基础异常（`DirectoryNotFoundError`、`FileAccessError` 等继承它） |

### 设计原则

- 默认安全：v0.1.0 只读，不修改任何文件
- 错误可追踪：权限 / 读取问题不崩溃，统一写入 `errors`，并用退出码表达结果
- 输出可消费：JSON 方便后续版本做规则引擎和报告
- 纯标准库：降低依赖，专注 Python 基础

---

## 🧪 测试与验证

### 怎么跑

```bash
# 1) unittest：全部测试（零依赖）
python tests/run_tests.py

# 也可以只跑某个模块 / 某个用例
python tests/run_tests.py scanner
python tests/run_tests.py test_models.TestFileItem.test_str_method

# 2) pytest（如果装了）
python -m pytest tests -q

# 3) 端到端冒烟测试：真实调用 python -m filepilot，校验 JSON 契约与退出码
python tests/smoke_e2e.py

# 4) 一键跑上面全部（Windows PowerShell）
powershell -ExecutionPolicy Bypass -File tests/run_all_tests.ps1
#   想跳过 pytest：-SkipPytest
```

> `run_all_tests.ps1` 必须保存为 **UTF-8 with BOM**：Windows PowerShell 5.1 默认按 ANSI 读取 `.ps1`，
> 没有 BOM 时中文会被误解码，直接抛 `ParserError`。

### 最近一次实测结果

| 阶段 | 命令 | 结果 |
|---|---|---|
| 导入自检 | `python -c "import filepilot, filepilot.cli"` | ✅ `import ok, version 0.1.0` |
| unittest | `python -m unittest discover tests -v` | ✅ `Ran 35 tests` → `OK (skipped=1)` |
| pytest | `python -m pytest tests -q` | ✅ `34 passed, 1 skipped, 9 subtests passed` |
| 端到端 | `python tests/smoke_e2e.py` | ✅ 10 项检查全部 PASS |
| 一键脚本 | `tests/run_all_tests.ps1` | ✅ 退出码 0，输出“全部测试通过” |

唯一跳过的用例是 `test_scanner.py::test_symlinks`：Windows 创建符号链接需要开发者模式或管理员权限，
拿不到权限时用例会 `skipTest`，不算失败。

### 本次修复记录（v0.1.0 从 14 failed / 6 errors 到全绿）

| # | 问题 | 后果 |
|---|---|---|
| 1 | `scanner.py` 的 `return files` 缩进在 `for` 循环体内 | 只返回第一个文件，5 个扫描用例失败 |
| 2 | `Scanner` 属性叫 `files_count`，测试与报告要 `file_count`；`get_report()` 缺 `error_count` | `KeyError: 'file_count'` |
| 3 | Windows 隐藏判定只看文件属性，不认 `.` 前缀 | 隐藏文件被计入，7 变 8 |
| 4 | 子解析器没定义 `--follow-symlinks` | `scan_command` 读 `args.follow_symlinks` 抛 `AttributeError` |
| 5 | `-v` 只注册在主解析器 | `scan ./dir -v` 报 `unrecognized arguments`（退出码 2） |
| 6 | `skip_hidden=args.no_skip_hidden` 逻辑写反 | `--no-skip-hidden` 反而跳过隐藏文件 |
| 7 | 报告字段名 `files_count`、`errors` 直接用 `e.__dict__` | 与测试契约不符；`Path` 无法 JSON 序列化（潜在 `TypeError`） |
| 8 | `save_to_file` 不创建父目录 | 保存到嵌套路径抛 `FileNotFoundError` |
| 9 | `models.__str__` 没用格式化后的大小；`_format_size` 没做除法、格式多了空格 | `str(item)` 丢单位；`"0.0 B" != "0.0B"` |
| 10 | `ScanError(error="access")` 关键字参数名写错 | 权限分支自身抛 `TypeError` |
| 11 | 用 `Path.exists()/is_dir()` 做根目录校验 | stat 失败时直接抛 `PermissionError`，而不是收集错误 |

修复后：`unittest` 35 个用例全绿（1 个符号链接用例按平台跳过），`pytest` 34 passed，E2E 10 项全 PASS。

---

## ⚠️ 已知限制

- 仅支持 `scan` 命令；不会移动、重命名、复制或删除文件
- 没有 `--pretty`：JSON 始终缩进输出
- `-o` 没有默认文件名：不传 `-o` 时打印到 stdout
- `FileItem` 不记录 `is_symlink` 与哈希（哈希属于 v0.3.0）
- CLI 默认跳过符号链接（`--follow-symlinks` 才跟随）；直接使用 `Scanner` 类时默认值相反（`follow_symlinks=True`）
- 隐藏文件识别：`.` 前缀全平台有效；Windows “隐藏”属性仅在 Windows 生效
- 单线程 `os.walk`，超大目录性能一般
- 仓库还没有 `LICENSE`、`.gitignore`、`examples/`、CI
- JSON 输出尚未做 schema 版本管理

---

## 🛣️ Roadmap

| 版本 | 目标 | 主要知识点 |
|---|---|---|
| v0.1.0 | 扫描目录并输出 JSON | argparse、pathlib、os、json、dataclasses |
| v0.2.0 | 规则引擎、整理、dry-run、undo | 面向对象、正则、闭包、文件操作 |
| v0.3.0 | 重复文件检测、并发哈希 | 线程、进程、hashlib |
| v0.4.0 | 日志分析、Markdown 报告 | asyncio、正则、异常处理 |
| v1.0.0 | 测试、CI、打包、发布 | pytest、GitHub Actions、工程化 |

---

## 🤝 贡献

欢迎提 Issue、讨论设计或提交 PR。

如果你想参与：

1. Fork 本仓库
2. 创建分支：`git checkout -b feature/your-feature`
3. 提交修改：`git commit -m "feat: add your feature"`
4. 推送分支：`git push origin feature/your-feature`
5. 打开 Pull Request

---

## 📄 License

本项目基于 MIT License 发布（`LICENSE` 文件待 v1.0.0 发布时补充）。

---

## 🙏 致谢

- Python 标准库
- DeepSeek harness：辅助定位 v0.1.0 测试失败原因并做回归验证
- Claude：辅助代码 review 与设计讨论
- 所有正在从“学完基础”走向“真正做项目”的开发者

---

## ⭐ 最后

FilePilot 的目标不是一次性写完，而是把 Python 基础、面向对象、文件操作、正则、并发、异常处理和工程化实践，串成一个能持续迭代的真实项目。

如果这个项目对你有帮助，欢迎点一个 Star。
