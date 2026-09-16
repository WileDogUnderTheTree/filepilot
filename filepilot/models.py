# 数据模型
from dataclasses import dataclass
from pathlib import Path
import json
from datetime import datetime

@dataclass
class FileItem:
    # 文本信息类
    path: Path
    size: int
    extension: str
    modified_time: float

    @classmethod
    def from_path(cls, path:Path)->'FileItem':
        # 从路径创建 FileItem 实例
        try:
            stat = path.stat()
            return cls(
                path=path,
                size=stat.st_size,
                extension=path.suffix.lower(),
                modified_time=stat.st_mtime
            )
        except OSError as e:
            from filepilot.exceptions import FileAccessError
            raise FileAccessError(path, str(e)) from e

    def to_dict(self) -> dict:
        # 转换为字典，便于 JSON 序列化
        return {
            "path": str(self.path),
            "absolute_path": str(self.path.absolute()),
            "name":self.path.name,
            "size":self.size,
            "extension":self.extension,
            "modified_time":datetime.fromtimestamp(self.modified_time).isoformat()
        }

    def __str__(self) -> str:
        # 正常显示
        return f"{self.path.name}({self._format_size()}, {self.extension})"

    def _format_size(self) -> str:
        # 格式化文件大小，例如 0 -> "0.0B"、1024 -> "1.0KB"
        size = float(self.size)
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f}{unit}"
            size /= 1024
        return f"{size:.1f}TB"

# 测试
# if __name__ == "__main__":
#     p = Path("D:\photo\微信图片_20260911234809_1_32.jpg")
#     item = FileItem.from_path(p)
#     print(item)
#     print(item.to_dict())


