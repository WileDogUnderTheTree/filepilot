# 数据模型
import re
from dataclasses import dataclass
from pathlib import Path
import json
from datetime import datetime
from typing import Callable

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

def load_config(config_path: str) -> dict:
    """读取 JSON 配置，规则校验由规则引擎完成。"""
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_config(config_path:str, config:dict) -> None:
    # 将字典写入json文件
    with open(config_path, "w",encoding='utf-8') as f:
        json.dump(config, f,ensure_ascii=False,indent=2)

def make_regex_filter(pattern: str) -> Callable[[str], bool]:
    """返回一个只匹配文件名的正则闭包。"""
    regex = re.compile(pattern)

    def filter_func(filename: str) -> bool:
        return regex.search(filename) is not None

    return filter_func

# # 测试
# if __name__ == "__main__":
#     p = Path(r"D:\photo\asen.jpg")
#     item = FileItem.from_path(p)
#     print(item)
#     print(item.to_dict())


