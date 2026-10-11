"""engine.py
主执行引擎：加载规则 → 扫描 → 执行 → 记录历史。
"""

import os
from typing import List, Optional, Tuple

from filepilot.actions import Action, ActionRecord, DeleteAction, MoveAction
from filepilot.executor import ActionExecutor
from filepilot.exceptions import RuleParseError
from filepilot.history import HistoryManager
from filepilot.models import load_config
from filepilot.rules import RegexRule

ACTION_REGISTRY = {
    "delete": DeleteAction,
    "move": MoveAction,
}

def create_action(name: str) -> Action:
    if name not in ACTION_REGISTRY:
        raise RuleParseError(f"Unknown action: {name}")
    return ACTION_REGISTRY[name]()

def build_rules(config: dict) -> List[RegexRule]:
    if not isinstance(config, dict) or not isinstance(config.get("rules", []), list):
        raise RuleParseError("配置必须包含 rules 数组")
    rules: List[RegexRule] = []
    for rule_cfg in config.get("rules", []):
        if not isinstance(rule_cfg, dict):
            raise RuleParseError(f"规则必须是对象：{rule_cfg!r}")
        pattern = rule_cfg.get("pattern")
        action_name = rule_cfg.get("action")
        if not pattern or not action_name:
            raise RuleParseError(f"规则缺少 pattern 或 action:{rule_cfg}")
        try:
            params = rule_cfg.get("params", {})
            if not isinstance(params, dict):
                raise RuleParseError(f"规则 params 必须是对象：{rule_cfg}")
            rules.append(RegexRule(
                pattern=pattern,
                action=create_action(action_name),
                params=params,
            ))
        except (TypeError, ValueError) as e:
            raise RuleParseError(f"规则无效：{rule_cfg} ({e})") from e
    return rules

def iter_files(root:str) -> List[str]:
    out:List[str] = []
    for dirpath,_,filenames in os.walk(root):
        for n in filenames:
            out.append(os.path.abspath(os.path.join(dirpath,n)))
    return out

def build_actions(root: str, rules: List[RegexRule]) -> List[Tuple[Action, str, dict]]:
    actions: List[Tuple[Action, str, dict]] = []
    for filepath in iter_files(root):
        filename = os.path.basename(filepath)
        for rule in rules:
            if rule.applies_to(filename):
                actions.append((rule.action, filepath, rule.params))
                break
    return actions

def run_engine(
        root: str,
        config_path: str,
        dry_run: bool = True,
        history_file: Optional[str] = None,
) -> Tuple[List[ActionRecord],HistoryManager]:
    """主执行流程

    Returns:
        (records,history)
    """
    if not os.path.isdir(root):
        raise RuleParseError(f"整理目录不存在或不是目录：{root}")
    try:
        config = load_config(config_path)
    except (OSError, ValueError) as e:
        raise RuleParseError(f"无法读取规则配置 {config_path}：{e}") from e
    rules = build_rules(config)
    actions = build_actions(root, rules)

    executor = ActionExecutor(dry_run=dry_run)
    records = executor.run(actions)

    history = (HistoryManager.load(history_file)
               if history_file and os.path.exists(history_file)
               else HistoryManager(history_file=history_file))
    if not dry_run:
        for r in records:
            if r.status == "executed":
                history.add_record(r)
        if history_file:
            history.save()

    return records, history
