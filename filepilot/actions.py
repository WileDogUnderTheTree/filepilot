import os
import shutil
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import Optional

from filepilot.exceptions import UndoError

# 操作记录
@dataclass
class ActionRecord:
    """一次操作的记录。可序列化、可撤销。"""
    action_type: str
    source_path: str
    target_path: Optional[str] = None      # move 的目标 / delete 的备份路径
    status: str = "planned"                # planned | executed | skipped | failed | undone
    reason: str = ""
    dry_run: bool = False
    timestamp: str = field(
        default_factory=lambda: datetime.now().isoformat(timespec="seconds")
    )

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "ActionRecord":
        return cls(**data)

    def undo(self) -> bool:
        """执行反向操作。只有 executed 状态才需要/能撤销。"""
        if self.status != "executed":
            return False

        if self.action_type == "move":
            if not self.target_path or not os.path.exists(self.target_path):
                raise UndoError(f"无法撤销 move：目标不存在 {self.target_path}")
            if os.path.exists(self.source_path):
                raise UndoError(f"无法撤销 move：源路径已被占用 {self.source_path}")
            try:
                os.makedirs(os.path.dirname(os.path.abspath(self.source_path)), exist_ok=True)
                shutil.move(self.target_path, self.source_path)
            except OSError as e:
                raise UndoError(f"撤销 move 失败：{e}") from e
            self.status = "undone"
            return True

        if self.action_type == "delete":
            # delete 实际是"移动到回收站"，从回收站搬回来
            if not self.target_path or not os.path.exists(self.target_path):
                raise UndoError(f"无法撤销 delete：备份不存在 {self.target_path}")
            if os.path.exists(self.source_path):
                raise UndoError(f"无法撤销 delete：源路径已被占用 {self.source_path}")
            try:
                os.makedirs(os.path.dirname(os.path.abspath(self.source_path)), exist_ok=True)
                shutil.move(self.target_path, self.source_path)
            except OSError as e:
                raise UndoError(f"恢复删除失败：{e}") from e
            self.status = "undone"
            return True

        raise UndoError(f"不支持撤销的操作类型：{self.action_type}")

    def __repr__(self) -> str:
        return (f"ActionRecord({self.action_type}, {self.source_path} -> "
                f"{self.target_path}, status={self.status}, dry_run={self.dry_run})")


# 动作基类
class Action(ABC):
    @abstractmethod
    def execute(self, filepath: str, params: dict, dry_run: bool = False) -> ActionRecord:
        ...

class DeleteAction(Action):
    DEFAULT_TRASH = ".filepilot_trash"

    def __init__(self, trash_dir: str = DEFAULT_TRASH):
        self.trash_dir = trash_dir

    def execute(self, filepath: str, params: dict, dry_run: bool = False) -> ActionRecord:
        trash_dir = os.path.abspath(params.get("trash_dir", self.trash_dir))

        if not os.path.exists(filepath):
            return ActionRecord("delete", filepath, status="skipped",
                                reason=f"源不存在：{filepath}", dry_run=dry_run)

        backup_path = os.path.join(
            trash_dir, f"{uuid.uuid4().hex}_{os.path.basename(filepath)}"
        )

        if dry_run:
            return ActionRecord("delete", filepath, backup_path, "planned",
                                f"将删除（备份到 {backup_path}）：{filepath}", True)

        try:
            os.makedirs(trash_dir, exist_ok=True)
            shutil.move(filepath, backup_path)
        except OSError as e:
            return ActionRecord("delete", filepath, backup_path, "failed",
                                f"删除失败：{e}", dry_run=dry_run)

        return ActionRecord("delete", filepath, backup_path, "executed",
                            f"已删除（备份到 {backup_path}）")


# 移动
class MoveAction(Action):
    @staticmethod
    def target_path(filepath: str, params: dict) -> str:
        target_dir = params.get("target_dir", ".")
        return os.path.abspath(os.path.join(target_dir, os.path.basename(filepath)))

    def execute(self, filepath: str, params: dict, dry_run: bool = False) -> ActionRecord:
        target_dir = params.get("target_dir", ".")
        target_path = self.target_path(filepath, params)
        overwrite = params.get("overwrite", False)

        if not os.path.exists(filepath):
            return ActionRecord("move", filepath, target_path, "skipped",
                                f"源不存在：{filepath}", dry_run=dry_run)

        if os.path.abspath(filepath) == os.path.abspath(target_path):
            return ActionRecord("move", filepath, target_path, "skipped",
                                "源与目标相同", dry_run=dry_run)

        if os.path.exists(target_path) and not overwrite:
            return ActionRecord("move", filepath, target_path, "skipped",
                                f"目标已存在：{target_path}", dry_run=dry_run)

        if dry_run:
            need_mkdir = not os.path.isdir(target_dir)
            extra = "（将新建目录）" if need_mkdir else ""
            return ActionRecord("move", filepath, target_path, "planned",
                                f"将移动：{filepath} -> {target_path}{extra}", True)

        try:
            os.makedirs(target_dir, exist_ok=True)
            shutil.move(filepath, target_path)
        except OSError as e:
            return ActionRecord("move", filepath, target_path, "failed",
                                f"移动失败：{e}", dry_run=dry_run)

        return ActionRecord("move", filepath, target_path, "executed",
                            f"已移动：{filepath} -> {target_path}")
