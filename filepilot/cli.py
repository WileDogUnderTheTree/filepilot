# 命令行接口
"""FilePilot CLI 入口"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

from filepilot.scanner import Scanner
from filepilot.models import FileItem
from filepilot.exceptions import FilePilotError, DirectoryNotFoundError

__version__ = "0.1.0"

def main() -> int:
    """主入口函数"""
    parser = create_parser()
    args = parser.parse_args()

    try:
        if args.version:
            print(f"filepilot {__version__}")
            return 0
        elif args.command == "scan":
            return scan_command(args)
        else:
            parser.print_help()
            return 1
    except KeyboardInterrupt:
        print("\n操作被用户中断", file=sys.stderr)
        return 130
    except FilePilotError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"意外错误: {e}", file=sys.stderr)
        return 1


def create_parser() -> argparse.ArgumentParser:
    """创建命令行参数解析器"""
    parser = argparse.ArgumentParser(
        prog="filepilot",
        description="文件整理、去重与日志分析 CLI 工具",
        epilog="示例: filepilot scan ./ --output files.json"
    )

    # 全局参数
    parser.add_argument(
        "--version",
        action="store_true",
        help="显示版本信息"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="详细输出"
    )

    # 子命令
    subparsers = parser.add_subparsers(
        dest="command",
        help="可用命令"
    )

    # scan命令
    scan_parser = subparsers.add_parser(
        "scan",
        help="扫描目录并生成文件清单"
    )
    scan_parser.add_argument(
        "directory",
        type=str,
        help="要扫描的目录文件"
    )
    scan_parser.add_argument(
    "-o","--output",
    type=str,
    help="输出 JSON 文件路径"
    )
    scan_parser.add_argument(
        "--no-skip-hidden",
        "--include-hidden",
        dest="no_skip_hidden",
        action="store_true",
        help="不跳过隐藏文件（别名：--include-hidden）"
    )
    scan_parser.add_argument(
        "--follow-symlinks",
        action="store_true",
        help="跟随符号链接"
    )
    scan_parser.add_argument(
        "--max-depth",
        type=int,
        default=None,
        help="最大扫描深度"
    )
    # 允许把 -v 写在子命令后面：filepilot scan ./dir -v
    scan_parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="详细输出"
    )

    return parser

def scan_command(args:argparse.Namespace) -> int:
    # 处理scan命令
    try:
        # 验证目录
        directory = Path(args.directory)
        if not directory.exists():
            raise DirectoryNotFoundError(directory)

        # 创建扫描器
        # 注意：--no-skip-hidden 表示“不跳过隐藏文件”，所以要取反
        scan = Scanner(
            root=directory,
            skip_hidden=not args.no_skip_hidden,
            follow_symlinks=args.follow_symlinks,
            max_depth=args.max_depth
        )

        # 执行扫描
        files = scan.scan()

        # 准备输出数据
        output_data = {
            "metadata":{
                "tool":"filepilot",
                "version":__version__,
                "scan_time":datetime.now().isoformat()
            },
            "summary":{
            "root":str(directory),
            "file_count":scan.file_count,
            "total_size":scan.total_size,
            "error_count":len(scan.errors)
            },
            "files": [f.to_dict() for f in files],
            "errors":[e.to_dict() for e in scan.errors]
        }

        # 输出结果
        if args.output:
            save_to_file(output_data, args.output)
        else:
            print(json.dumps(output_data, indent=2,ensure_ascii=False))

        # 打印统计信息
        if args.verbose:
            print(f"\n扫描完成：{scan.file_count}个文件,{len(scan.errors)}个错误")

        return 0 if not scan.errors else 1

    except DirectoryNotFoundError as e:
        print(f"错误: 目录不存在: {e.path}", file=sys.stderr)
        return 1
    except PermissionError as e:
        print(f"错误：没有权限: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"扫描失败： {e}", file=sys.stderr)
        return 1

def save_to_file(data: Dict[str, Any], file_path: Path) -> None:
    # 保存数据到JSON文件
    try:
        output_path = Path(file_path)
        # 输出路径的父目录不存在时自动创建
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"结果已保存到：{output_path}")
    except OSError as e:
        raise FilePilotError(f"无法保存文件{file_path}:{e}") from e

if __name__ == "__main__":
    sys.exit(main())






