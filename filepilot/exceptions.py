from pathlib import Path

# 自定义异常
class FilePilotError(Exception):
    """基础异常类"""
    pass

class DirectoryNotFoundError(FilePilotError):
    """目录不存在异常"""
    def __init__(self, path: Path):
        self.path = path
        super().__init__(f"目录不存在: {path}")

class FileAccessError(FilePilotError):
    """文件访问异常"""
    def __init__(self, path: Path, message: str = ""):
        self.path = path
        super().__init__(f"无法访问文件 {path}: {message}")

class ScanError(FilePilotError):
    # 扫描中遇到的错误
    def __init__(self, path: Path, error_type: str, message: str):
        # error_type: 'access', 'not_found', 'encoding', 'unknown'
        self.path = path
        self.error_type = error_type
        self.message = message
        super().__init__(f"{error_type}:{path} - {message}")

    def to_dict(self) -> dict:
        # 便于写入 JSON 报告（Path 不能直接序列化）
        return {
            "path": str(self.path),
            "error_type": self.error_type,
            "message": self.message,
        }

class RuleParseError(FilePilotError):
    """JSON规则配置解析失败"""
    pass

class FileOperationError(FilePilotError):
    """文件移动/重命名操作异常"""
    pass

class UndoError(FilePilotError):
    """撤销操作失败异常"""
    pass

# exceptions.py
__all__ = [
    "FilePilotError",
    "DirectoryNotFoundError",
    "FileAccessError",
    "ScanError",
    "RuleParseError",
    "FileOperationError",
    "UndoError",
]