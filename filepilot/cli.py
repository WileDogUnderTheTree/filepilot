"""FilePilot 命令行入口。"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from filepilot.actions import ActionRecord
from filepilot.engine import run_engine
from filepilot.exceptions import DirectoryNotFoundError, FilePilotError
from filepilot.executor import ActionExecutor
from filepilot.history import HistoryManager
from filepilot.scanner import Scanner

__version__ = "0.2.0"


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="filepilot",
        description="按规则整理本地文件，并生成可撤销的操作历史",
        epilog="示例：filepilot organize ./downloads -c rules.json",
    )
    parser.add_argument("--version", action="store_true", help="显示版本信息")
    parser.add_argument("-v", "--verbose", action="store_true", help="详细输出")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    scan_parser = subparsers.add_parser("scan", help="扫描目录并生成文件清单")
    scan_parser.add_argument("directory", help="要扫描的目录")
    scan_parser.add_argument("-o", "--output", help="输出 JSON 文件路径")
    scan_parser.add_argument(
        "--no-skip-hidden", "--include-hidden", dest="no_skip_hidden",
        action="store_true", help="不跳过隐藏文件和目录（别名：--include-hidden）",
    )
    scan_parser.add_argument("--follow-symlinks", action="store_true", help="跟随符号链接")
    scan_parser.add_argument("--max-depth", type=int, default=None, help="最大扫描深度")
    scan_parser.add_argument(
        "-v", "--verbose", dest="verbose", action="store_true",
        default=argparse.SUPPRESS, help="详细输出",
    )

    organize_parser = subparsers.add_parser("organize", help="按 JSON 规则整理文件")
    organize_parser.add_argument("directory", help="待整理的目录")
    organize_parser.add_argument("-c", "--config", required=True, help="规则 JSON 路径")
    organize_parser.add_argument("--apply", action="store_true", help="实际执行（默认只预览）")
    organize_parser.add_argument(
        "--history", default=".filepilot_history.json", help="操作历史 JSON 路径",
    )

    undo_parser = subparsers.add_parser("undo", help="撤销已执行的整理操作")
    undo_parser.add_argument("--history", default=".filepilot_history.json", help="历史 JSON 路径")
    undo_parser.add_argument("--all", action="store_true", help="撤销全部可撤销操作")
    return parser


def scan_command(args: argparse.Namespace) -> int:
    directory = Path(args.directory)
    try:
        if not directory.exists():
            raise DirectoryNotFoundError(directory)
        scanner = Scanner(
            root=directory,
            skip_hidden=not args.no_skip_hidden,
            follow_symlinks=args.follow_symlinks,
            max_depth=args.max_depth,
        )
        files = scanner.scan()
        output_data = {
            "metadata": {
                "tool": "filepilot",
                "version": __version__,
                "scan_time": datetime.now().isoformat(),
            },
            "summary": {
                "root": str(directory),
                "file_count": scanner.file_count,
                "total_size": scanner.total_size,
                "error_count": len(scanner.errors),
            },
            "files": [item.to_dict() for item in files],
            "errors": [error.to_dict() for error in scanner.errors],
        }
        if args.output:
            save_to_file(output_data, args.output)
        else:
            print(json.dumps(output_data, indent=2, ensure_ascii=False))
        if getattr(args, "verbose", False):
            print(f"\n扫描完成：{scanner.file_count} 个文件，{len(scanner.errors)} 个错误")
        return 0 if not scanner.errors else 1
    except DirectoryNotFoundError as e:
        print(f"错误：目录不存在：{e.path}", file=sys.stderr)
        return 1
    except PermissionError as e:
        print(f"错误：没有权限：{e}", file=sys.stderr)
        return 1
    except (FilePilotError, ValueError) as e:
        print(f"扫描失败：{e}", file=sys.stderr)
        return 1


def save_to_file(data: Dict[str, Any], file_path: str | Path) -> None:
    output_path = Path(file_path)
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except OSError as e:
        raise FilePilotError(f"无法保存文件 {file_path}：{e}") from e
    print(f"结果已保存到：{output_path}")


def run_organize(root: str, actions: list[tuple[Any, str, dict]], dry_run: bool = True) -> list[ActionRecord]:
    """执行已经构建好的动作，保留为 Python API 方便复用。"""
    results = ActionExecutor(dry_run=dry_run).run(actions)
    for record in results:
        print(f"[{record.status.upper():<8}] {record.reason}")
    return results


def organize_command(args: argparse.Namespace) -> int:
    records, _ = run_engine(
        root=args.directory,
        config_path=args.config,
        dry_run=not args.apply,
        history_file=args.history,
    )
    for record in records:
        print(f"[{record.status.upper():<8}] {record.reason}")
    failed = sum(record.status == "failed" for record in records)
    print(f"\n汇总：planned={sum(r.status == 'planned' for r in records)}, "
          f"executed={sum(r.status == 'executed' for r in records)}, "
          f"skipped={sum(r.status == 'skipped' for r in records)}, "
          f"failed={failed}, total={len(records)}")
    return 1 if failed else 0


def undo_command(args: argparse.Namespace) -> int:
    history = HistoryManager.load(args.history)
    undone = history.undo_all() if args.all else []
    if not args.all:
        record = history.undo_last()
        if record:
            undone.append(record)
    for record in undone:
        print(f"已撤销：{record.action_type}  {record.source_path}")
    history.save()
    print(f"共撤销 {len(undone)} 条")
    return 0


def main() -> int:
    parser = create_parser()
    args = parser.parse_args()
    try:
        if args.version:
            print(f"filepilot {__version__}")
            return 0
        if args.command == "scan":
            return scan_command(args)
        if args.command == "organize":
            return organize_command(args)
        if args.command == "undo":
            return undo_command(args)
        parser.print_help()
        return 1
    except KeyboardInterrupt:
        print("\n操作被用户中断", file=sys.stderr)
        return 130
    except FilePilotError as e:
        print(f"错误：{e}", file=sys.stderr)
        return 1
    except (OSError, ValueError, json.JSONDecodeError) as e:
        print(f"错误：{e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
