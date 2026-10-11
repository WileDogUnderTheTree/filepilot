import os
from typing import List, Tuple

from filepilot.actions import Action, ActionRecord, MoveAction


class ActionExecutor:
    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run
        self.results: List[ActionRecord] = []
        self.planned_targets: set[str] = set()     # 必须是 set

    def run(self, actions: List[Tuple[Action, str, dict]]) -> List[ActionRecord]:
        for action, filepath, params in actions:
            # 先计算目标再执行，避免第二个动作已经完成移动后才发现冲突。
            if isinstance(action, MoveAction):
                planned_target = action.target_path(filepath, params)
                key = os.path.abspath(planned_target)
                if key in self.planned_targets:
                    self.results.append(ActionRecord(
                        "move", filepath, planned_target, "skipped",
                        f"目标冲突：{planned_target} 已被本批次占用",
                        dry_run=self.dry_run,
                    ))
                    continue

            record = action.execute(filepath, params, dry_run=self.dry_run)

            # 同批次目标冲突检测（只对 move 有意义）
            if (record.action_type == "move"
                    and record.target_path
                    and record.status in ("planned", "executed")):
                key = os.path.abspath(record.target_path)
                if key in self.planned_targets:
                    record.status = "skipped"
                    record.reason = f"目标冲突：{record.target_path} 已被本批次占用"
                else:
                    self.planned_targets.add(key)

            self.results.append(record)            # 之前忘了 append

        return self.results

    def summary(self) -> dict:
        def count(status: str) -> int:
            return sum(1 for r in self.results if r.status == status)
        return {
            "dry_run": self.dry_run,
            "planned": count("planned"),
            "executed": count("executed"),
            "skipped": count("skipped"),
            "failed": count("failed"),
        }
