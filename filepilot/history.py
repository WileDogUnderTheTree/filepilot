import json
from pathlib import Path
from typing import List, Optional

from filepilot.actions import ActionRecord
from filepilot.exceptions import UndoError

class HistoryManager:
    def __init__(self,history_file:Optional[str] = None):
        self.records: List[ActionRecord] = []
        self.history_file = history_file

    # 记录
    def add_record(self,record: ActionRecord) -> None:
        self.records.append(record)

    def add_records(self,records) -> None:
        self.records.extend(records)

    # 撤销
    def undo_last(self) -> Optional[ActionRecord]:
        # 撤销最近一条可撤销（executed）的记录
        for record in reversed(self.records):
            if record.status == "executed":
                record.undo()
                return record
        return None

    def undo_all(self) -> List[ActionRecord]:
        undone:List[ActionRecord] = []
        for record in reversed(self.records):
            if record.status != "executed":
                continue
            try:
                record.undo()
            except UndoError as e:
                print(f"[warn] {e}")
                continue
            undone.append(record)
        return undone

    # 持久化
    def save(self,path:Optional[str]=None) -> None:
        path = path or self.history_file
        if path is None:
            return
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path,'w',encoding="utf-8") as f:
            json.dump([r.to_dict() for r in self.records],f,
                      ensure_ascii=False,indent=2)

    @classmethod
    def load(cls,path:str) -> 'HistoryManager':
        hm = cls(history_file=path)
        p = Path(path)
        if not p.exists():
            return hm
        with open(p, 'r', encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            raise ValueError("历史文件必须是操作记录数组")
        hm.records = [ActionRecord.from_dict(d) for d in data]
        return hm

    def summary(self) -> dict:
        def c(s): return sum(1 for r in self.records if r.status == s)
        return {
            "total":len(self.records),
            "executed":c("executed"),
            "undone":c("undone"),
        }
