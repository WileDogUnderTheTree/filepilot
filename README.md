# FilePilot

FilePilot 是一个使用 Python 标准库编写的本地文件整理 CLI 工具。它按照 JSON 规则匹配文件名，预览或执行移动、删除操作，并保存操作历史，方便之后撤销。

当前版本：`v0.2.0`。

## 这个项目有什么用

当下载目录、临时文件目录或照片目录越来越乱时，可以把整理规则写成配置文件，让 FilePilot 自动完成重复性的文件操作：

- 用正则表达式匹配文件名；
- 按规则移动文件到目标目录；
- 将删除操作先移动到 `.filepilot_trash`，而不是直接永久删除；
- 默认使用 dry-run，只展示计划，不修改文件；
- 使用操作历史恢复已经执行的移动或删除；
- 用 `scan` 先生成目录清单，检查扫描结果。

项目也演示了抽象基类、策略模式、闭包、JSON 配置、异常处理和可测试的文件操作流程。

## 安装

需要 Python 3.10 或更高版本，不依赖第三方库：

```bash
git clone https://github.com/WileDogUnderTheTree/filepilot.git
cd filepilot
pip install -e .
```

不安装也可以在项目根目录运行：

```bash
python -m filepilot --version
```

## 怎么操作

### 1. 先扫描目录

```bash
python -m filepilot scan ./downloads -o reports/files.json -v
```

默认跳过隐藏文件和隐藏目录。需要包含隐藏内容时使用：

```bash
python -m filepilot scan ./downloads --include-hidden
```

`scan` 输出包含 `files`、`summary` 和 `errors` 的 JSON 报告；使用 `-o` 时会自动创建父目录。

### 2. 编写规则

规则按顺序匹配，每个文件只执行第一条匹配成功的规则：

```json
{
  "rules": [
    {
      "pattern": "\\.(jpg|jpeg|png)$",
      "action": "move",
      "params": {"target_dir": "./整理后/图片"}
    },
    {
      "pattern": "\\.tmp$",
      "action": "delete",
      "params": {"trash_dir": "./.filepilot_trash"}
    }
  ]
}
```

可用动作：

- `move`：移动到 `target_dir`，目标目录不存在时自动创建；
- `delete`：移动到 `trash_dir`，默认使用当前目录下的 `.filepilot_trash`；
- `overwrite`：移动规则可在 `params` 中设置为 `true`，默认不覆盖已有文件。

正则表达式匹配的是文件名，例如 `photo.png`，不是完整路径。JSON 中的反斜杠需要写成 `\\`。

### 3. 先 dry-run，再实际执行

```bash
# 只显示计划，不改文件（默认行为）
python -m filepilot organize ./downloads -c examples/rules.json

# 真正执行，并保存历史
python -m filepilot organize ./downloads \
  --config examples/rules.json \
  --apply \
  --history .filepilot_history.json
```

执行输出中的状态含义：`PLANNED` 是预览，`EXECUTED` 是已完成，`SKIPPED` 是源文件不存在、目标已存在或目标冲突，`FAILED` 是操作失败。

### 4. 撤销操作

```bash
# 撤销最近一条已执行操作
python -m filepilot undo --history .filepilot_history.json

# 按倒序撤销所有已执行操作
python -m filepilot undo --history .filepilot_history.json --all
```

撤销要求目标文件或回收站备份仍然存在，并且原始路径没有被新文件占用。

## Python API 示例

除了 CLI，也可以在 Python 中直接使用规则和引擎：

```python
from filepilot.engine import run_engine

records, history = run_engine(
    root="./downloads",
    config_path="./rules.json",
    dry_run=True,                         # 先预览
    history_file="./.filepilot_history.json",
)

for record in records:
    print(record.status, record.source_path, record.target_path)
```

正则闭包可以单独使用：

```python
from filepilot.models import make_regex_filter

is_image = make_regex_filter(r"\.(jpg|jpeg|png)$")
assert is_image("holiday.jpg")
assert not is_image("notes.txt")
```

## 项目结构

```text
filepilot/
├── actions.py     # MoveAction、DeleteAction、ActionRecord
├── engine.py      # 读取配置、构建规则、组织执行流程
├── executor.py    # 批量执行与目标冲突检测
├── history.py     # 历史持久化与 undo
├── models.py      # FileItem、JSON 配置、正则闭包
├── rules.py       # Rule 抽象基类与 RegexRule
├── scanner.py     # 目录扫描
└── cli.py         # scan、organize、undo 命令
```

## 测试

```bash
python -m unittest discover tests -v
python -m pytest tests -q       # 已安装 pytest 时
python tests/smoke_e2e.py
```

测试重点覆盖扫描、规则匹配、dry-run、移动、删除恢复、历史文件、目标冲突和 CLI 退出码。

## 注意事项

- `organize` 默认是 dry-run；只有显式添加 `--apply` 才会修改文件。
- 建议先备份重要目录，并先查看 dry-run 输出。
- 相对的 `target_dir` 和 `trash_dir` 按启动命令时的当前工作目录解释。
- `scan` 的退出码为 `0` 表示无扫描错误，`1` 表示目录或扫描存在问题；命令行参数错误由 `argparse` 返回 `2`。

## 许可证

本项目基于 MIT License 发布，详见 [LICENSE](LICENSE)。
