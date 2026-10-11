"""v0.2 规则引擎、动作和历史的回归测试。"""

import json
import tempfile
import unittest
from pathlib import Path

from filepilot.actions import MoveAction
from filepilot.engine import build_rules, run_engine
from filepilot.exceptions import RuleParseError
from filepilot.executor import ActionExecutor
from filepilot.history import HistoryManager
from filepilot.models import make_regex_filter


class TestV02RulesAndEngine(unittest.TestCase):
    def test_regex_filter_returns_bool(self):
        matcher = make_regex_filter(r"\.txt$")
        self.assertIs(matcher("notes.txt"), True)
        self.assertIs(matcher("notes.jpg"), False)

    def test_invalid_regex_is_a_rule_error(self):
        with self.assertRaises(RuleParseError):
            build_rules({"rules": [{"pattern": "[", "action": "move"}]})

    def test_first_matching_rule_wins(self):
        rules = build_rules({"rules": [
            {"pattern": r"\.txt$", "action": "move", "params": {"target_dir": "one"}},
            {"pattern": r".*", "action": "delete", "params": {}},
        ]})
        self.assertTrue(rules[0].applies_to("a.txt"))
        self.assertFalse(rules[0].applies_to("a.jpg"))

    def test_dry_run_does_not_modify_files(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "photo.jpg"
            source.write_text("image", encoding="utf-8")
            config = root / "rules.json"
            config.write_text(json.dumps({"rules": [{
                "pattern": r"\.jpg$", "action": "move",
                "params": {"target_dir": str(root / "images")},
            }]}), encoding="utf-8")
            records, history = run_engine(str(root), str(config), dry_run=True,
                                          history_file=str(root / "history.json"))
            self.assertEqual([r.status for r in records], ["planned"])
            self.assertTrue(source.exists())
            self.assertFalse((root / "images" / "photo.jpg").exists())
            self.assertEqual(history.records, [])

    def test_apply_and_undo_move_and_delete(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "photo.jpg").write_text("image", encoding="utf-8")
            (root / "old.tmp").write_text("temporary", encoding="utf-8")
            config = root / "rules.json"
            history_path = root / "history.json"
            config.write_text(json.dumps({"rules": [
                {"pattern": r"\.jpg$", "action": "move",
                 "params": {"target_dir": str(root / "images")}},
                {"pattern": r"\.tmp$", "action": "delete",
                 "params": {"trash_dir": str(root / "trash")}},
            ]}), encoding="utf-8")

            records, _ = run_engine(str(root), str(config), dry_run=False,
                                    history_file=str(history_path))
            self.assertEqual([r.status for r in records], ["executed", "executed"])
            self.assertTrue((root / "images" / "photo.jpg").exists())
            self.assertFalse((root / "old.tmp").exists())
            self.assertEqual(len(HistoryManager.load(str(history_path)).records), 2)

            history = HistoryManager.load(str(history_path))
            self.assertEqual(len(history.undo_all()), 2)
            self.assertTrue((root / "photo.jpg").exists())
            self.assertTrue((root / "old.tmp").exists())
            history.save()
            self.assertEqual(HistoryManager.load(str(history_path)).summary()["undone"], 2)

    def test_batch_move_conflict_is_detected_before_second_move(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "a").mkdir()
            (root / "b").mkdir()
            first = root / "a" / "same.txt"
            second = root / "b" / "same.txt"
            first.write_text("first", encoding="utf-8")
            second.write_text("second", encoding="utf-8")
            target = root / "target"
            action = MoveAction()
            records = ActionExecutor(dry_run=False).run(
                [(action, str(first), {"target_dir": str(target)}),
                 (action, str(second), {"target_dir": str(target)})]
            )
            self.assertEqual([r.status for r in records], ["executed", "skipped"])
            self.assertTrue(second.exists())


if __name__ == "__main__":
    unittest.main()
