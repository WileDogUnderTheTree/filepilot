import re
from abc import ABC, abstractmethod
from filepilot.actions import Action, ActionRecord
from filepilot.exceptions import RuleParseError
from filepilot.models import make_regex_filter

class Rule(ABC):
    def __init__(self, pattern: str):
        self.pattern = pattern
        self.filter = make_regex_filter(pattern)

    @abstractmethod
    def applies_to(self, filename: str) -> bool:
        """判断文件名是否匹配此规则"""
        return self.filter(filename)

    @abstractmethod
    def apply(self, filepath: str, dry_run: bool = False) -> ActionRecord:
        """执行动作，返回操作记录"""
        pass

class RegexRule(Rule):
    def __init__(self, pattern: str, action: Action, params: dict):
        try:
            super().__init__(pattern)  # 基类已设置 pattern 和 filter
        except re.error as e:
            raise RuleParseError(f"正则表达式无效：{pattern!r} ({e})") from e
        self.action = action
        self.params = dict(params or {})

    def applies_to(self, filename: str) -> bool:
        """判断文件名是否匹配本规则"""
        return self.filter(filename)

    def apply(self, filepath: str, dry_run: bool = False) -> ActionRecord:
        """执行动作，传入完整文件路径"""
        return self.action.execute(filepath, self.params, dry_run)
