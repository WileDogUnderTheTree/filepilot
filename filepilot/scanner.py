# 扫描器
"""目录扫描器：递归遍历文件系统，生成 FileItem 列表并收集错误"""

import ctypes
import os
import stat as stat_module
import sys
from pathlib import Path
from typing import Generator, Union, List, Iterator
from .exceptions import (
    DirectoryNotFoundError,
    FileAccessError,
    FilePilotError,
    ScanError,
)
from .models import FileItem

# Windows 文件属性常量
FILE_ATTRIBUTE_HIDDEN = 0x02
INVALID_FILE_ATTRIBUTES = 0xFFFFFFFF


class Scanner:
    """文件扫描器"""

    def __init__(
        self,
        root: Path,
        skip_hidden: bool = True,
        follow_symlinks: bool = True,
        max_depth: int | None = None,
    ):
        """初始化扫描器

        Args:
            root: 要扫描的根目录
            skip_hidden: 跳过隐藏文件 / 目录
            follow_symlinks: 是否跟随符号链接
            max_depth: 最大扫描深度，None 表示无限深
        """
        self.root = Path(root)
        self.skip_hidden = skip_hidden
        self.follow_symlinks = follow_symlinks
        self.max_depth = max_depth
        if max_depth is not None and max_depth < 0:
            raise ValueError("max_depth 不能小于 0")
        self.errors: List[ScanError] = []
        self.file_count = 0
        self.total_size = 0

    def scan(self) -> List[FileItem]:
        """执行扫描，返回文件列表（出错的文件记录到 errors，不中断扫描）"""
        self.errors.clear()
        self.file_count = 0
        self.total_size = 0
        self._check_root()

        files: List[FileItem] = []
        for file_path in self._walk():
            try:
                # 跳过隐藏文件
                if self.skip_hidden and self._is_hidden(file_path):
                    continue

                # 不跟随符号链接时跳过符号链接
                if not self.follow_symlinks and file_path.is_symlink():
                    continue

                # os.walk 只产出文件项；from_path 内部 stat，失败会抛 FileAccessError
                item = FileItem.from_path(file_path)
                files.append(item)
                self.file_count += 1
                self.total_size += item.size

            except FileAccessError as e:
                self._add_error(file_path, "access", str(e))
            except OSError as e:
                # 文件在扫描过程中被删除、被占用等
                self._add_error(file_path, "access", str(e))
            except Exception as e:  # pragma: no cover - 兜底，保证不崩溃
                self._add_error(file_path, "unknown", str(e))

        return files

    def _check_root(self) -> None:
        """校验根目录：不存在 / 不是目录 / 无权限时抛出对应异常"""
        try:
            st = os.stat(self.root)
        except FileNotFoundError:
            raise DirectoryNotFoundError(self.root)
        except OSError as e:
            raise FileAccessError(self.root, str(e))

        if not stat_module.S_ISDIR(st.st_mode):
            raise FilePilotError(f"不是目录：{self.root}")

    def _walk(self) -> Iterator[Path]:
        """遍历文件系统，生成所有文件路径

        使用生成器避免一次性把所有路径读进内存。
        """
        for current_root, dirs, files in os.walk(self.root, onerror=self._on_walk_error):
            current_path = Path(current_root)

            # 计算当前深度（根目录深度为 0）
            current_depth = len(current_path.relative_to(self.root).parts)
            if self.max_depth is not None and current_depth >= self.max_depth:
                dirs.clear()  # 不再向下遍历
                continue

            # 跳过隐藏目录
            if self.skip_hidden:
                dirs[:] = [d for d in dirs if not self._is_hidden(current_path / d)]

            # 产出文件
            for name in files:
                yield current_path / name

    def _on_walk_error(self, error: OSError) -> None:
        """os.walk 遇到无法进入的目录（如权限不足）时记录错误，而不是中断"""
        filename = getattr(error, "filename", None)
        if isinstance(filename, bytes):
            filename = os.fsdecode(filename)
        path = Path(filename) if filename else self.root
        self._add_error(path, "access", str(error))

    def _add_error(self, path: Path, error_type: str, message: str) -> None:
        self.errors.append(ScanError(path=path, error_type=error_type, message=message))

    def _is_hidden(self, path: Path) -> bool:
        """判断是否为隐藏文件 / 目录"""
        # 以 . 开头的名称在各平台都按隐藏处理
        if path.name.startswith('.'):
            return True

        if not sys.platform.startswith('win'):
            return False

        # Windows：检查隐藏属性
        try:
            attrs = ctypes.windll.kernel32.GetFileAttributesW(str(path))
        except Exception:
            return False

        if attrs in (-1, INVALID_FILE_ATTRIBUTES):
            return False
        return bool(attrs & FILE_ATTRIBUTE_HIDDEN)

    def get_report(self) -> dict:
        """获取扫描报告"""
        return {
            "summary": {
                "root": str(self.root),
                "file_count": self.file_count,
                "total_size": self.total_size,
                "error_count": len(self.errors),
            },
            "errors": [e.to_dict() for e in self.errors],
        }

def scan_files(root_dir: Union[str, Path]) -> Generator[FileItem, None, None]:
    """扫描指定目录，逐个产出 FileItem（生成器，节省内存）
    :param root_dir: 要扫描的根文件夹路径
    :yield: FileItem
    """
    root_dir = Path(root_dir)
    if not root_dir.is_dir():
        raise NotADirectoryError(f"目录不存在或不是文件夹：{root_dir}")

    for file_path in root_dir.rglob("*"):
        if file_path.is_file():
            yield FileItem.from_path(file_path)
