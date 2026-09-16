#!/usr/bin/env python3
"""运行测试（标准库 unittest，无需额外依赖）

用法：
    python tests/run_tests.py                      # 跑全部测试
    python tests/run_tests.py test_scanner          # 只跑某个模块
    python tests/run_tests.py test_cli.TestCLIParser  # 只跑某个类
    python tests/run_tests.py test_models.TestFileItem.test_str_method  # 只跑某个用例
"""

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def build_suite(targets: list[str]) -> unittest.TestSuite:
    loader = unittest.TestLoader()
    tests_dir = Path(__file__).resolve().parent

    if not targets:
        return loader.discover(start_dir=str(tests_dir), pattern='test_*.py', top_level_dir=str(PROJECT_ROOT))

    suite = unittest.TestSuite()
    for target in targets:
        name = target.strip()
        # 允许简写：scanner -> test_scanner -> tests.test_scanner
        if not name.startswith('tests.'):
            if not name.startswith('test_'):
                name = f'test_{name}'
            name = f'tests.{name}'
        suite.addTests(loader.loadTestsFromName(name))
    return suite


def main(argv: list[str]) -> int:
    # 保证 `import filepilot` 可用
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))

    try:
        suite = build_suite(argv)
    except Exception as e:  # 目标写错时给出友好提示
        print(f"无法加载测试目标 {argv}: {e}", file=sys.stderr)
        return 2

    if getattr(suite, 'countTestCases', lambda: 0)() == 0:
        print("没有发现任何测试用例", file=sys.stderr)
        return 2

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("-" * 60)
    print(f"运行 {result.testsRun} 个用例 | "
          f"失败 {len(result.failures)} | 错误 {len(result.errors)} | 跳过 {len(result.skipped)}")
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
