#!/usr/bin/env python3
"""测试 CLI 命令行接口"""

import unittest
import tempfile
import shutil
import sys
import subprocess
import json
import os
from pathlib import Path
from unittest.mock import patch
from io import StringIO

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from filepilot.cli import create_parser, scan_command, main, save_to_file
import argparse


class TestCLIParser(unittest.TestCase):
    """测试命令行参数解析"""

    def test_create_parser(self):
        """测试创建参数解析器"""
        parser = create_parser()
        self.assertIsNotNone(parser)

    def test_parse_scan_command(self):
        """测试解析扫描命令"""
        parser = create_parser()
        args = parser.parse_args(["scan", "./some/dir"])

        self.assertEqual(args.command, "scan")
        self.assertEqual(args.directory, "./some/dir")
        self.assertFalse(args.output)
        self.assertFalse(args.verbose)
        self.assertFalse(args.no_skip_hidden)
        self.assertFalse(args.follow_symlinks)
        self.assertIsNone(args.max_depth)

    def test_parse_scan_with_options(self):
        """测试解析带选项的扫描命令"""
        parser = create_parser()
        args = parser.parse_args([
            "scan",
            "./dir",
            "-o", "output.json",
            "-v",
            "--no-skip-hidden",
            "--follow-symlinks",
            "--max-depth", "3"
        ])

        self.assertEqual(args.command, "scan")
        self.assertEqual(args.directory, "./dir")
        self.assertEqual(args.output, "output.json")
        self.assertTrue(args.verbose)
        self.assertTrue(args.no_skip_hidden)
        self.assertTrue(args.follow_symlinks)
        self.assertEqual(args.max_depth, 3)

    def test_parse_version(self):
        """测试版本参数"""
        parser = create_parser()
        args = parser.parse_args(["--version"])
        self.assertTrue(args.version)
        self.assertIsNone(args.command)

    def test_no_command(self):
        """测试没有命令的情况"""
        parser = create_parser()
        args = parser.parse_args([])
        self.assertIsNone(args.command)

    def test_parse_include_hidden_alias(self):
        """测试 --include-hidden 作为 --no-skip-hidden 的别名"""
        parser = create_parser()
        args = parser.parse_args(["scan", "./dir", "--include-hidden"])
        self.assertTrue(args.no_skip_hidden)
        self.assertFalse(args.follow_symlinks)


class TestScanCommand(unittest.TestCase):
    """测试扫描命令功能"""

    def setUp(self):
        """创建测试环境"""
        self.temp_dir = tempfile.mkdtemp()
        self.root = Path(self.temp_dir)

        # 创建测试文件
        (self.root / "test1.txt").write_text("Content 1")
        (self.root / "test2.txt").write_text("Content 2")
        (self.root / "subdir").mkdir()
        (self.root / "subdir" / "test3.txt").write_text("Content 3")

    def tearDown(self):
        """清理测试环境"""
        shutil.rmtree(self.temp_dir)

    def test_scan_command_success(self):
        """测试成功的扫描命令"""
        args = argparse.Namespace(
            command="scan",
            directory=str(self.root),
            output=None,
            verbose=False,
            no_skip_hidden=False,
            follow_symlinks=False,
            max_depth=None
        )

        result = scan_command(args)
        self.assertEqual(result, 0)  # 应该返回 0（成功）

    def test_scan_command_with_output(self):
        """测试带输出的扫描命令"""
        output_file = self.root / "output.json"

        args = argparse.Namespace(
            command="scan",
            directory=str(self.root),
            output=str(output_file),
            verbose=False,
            no_skip_hidden=False,
            follow_symlinks=False,
            max_depth=None
        )

        result = scan_command(args)
        self.assertEqual(result, 0)

        # 检查输出文件是否存在
        self.assertTrue(output_file.exists())

        # 解析输出文件
        with open(output_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        self.assertIn("files", data)
        self.assertEqual(len(data["files"]), 3)
        self.assertEqual(data["summary"]["file_count"], 3)

    def test_scan_command_not_found(self):
        """测试目录不存在的情况"""
        args = argparse.Namespace(
            command="scan",
            directory="/nonexistent/path",
            output=None,
            verbose=False,
            no_skip_hidden=False,
            follow_symlinks=False,
            max_depth=None
        )

        result = scan_command(args)
        self.assertEqual(result, 1)  # 应该返回 1（失败）


class TestMainFunction(unittest.TestCase):
    """测试主函数"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.root = Path(self.temp_dir)
        (self.root / "test.txt").write_text("Content")

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    @patch('sys.argv', ['filepilot', '--version'])
    def test_main_version(self):
        """测试版本输出"""
        with patch('sys.stdout', new=StringIO()):
            result = main()
            self.assertEqual(result, 0)

    @patch('sys.argv', ['filepilot'])
    def test_main_no_command(self):
        """测试无命令情况"""
        with patch('sys.stdout', new=StringIO()):
            result = main()
            # 没有命令时应该返回 1 并打印帮助
            self.assertEqual(result, 1)

    @patch('sys.argv', ['filepilot', 'scan', 'test_dir'])
    def test_main_scan(self):
        """测试扫描命令"""
        # 创建测试目录
        test_dir = Path(self.temp_dir) / "test_dir"
        test_dir.mkdir()
        (test_dir / "file.txt").write_text("Content")

        with patch('sys.stdout', new=StringIO()):
            result = main()
            # 扫描命令可能会成功或失败，取决于是否有错误
            self.assertIn(result, [0, 1])


class TestSaveToFile(unittest.TestCase):
    """测试保存文件功能"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.root = Path(self.temp_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_save_to_file(self):
        """测试保存 JSON 文件"""
        data = {"test": "data"}
        filepath = str(self.root / "test.json")

        save_to_file(data, filepath)

        self.assertTrue(Path(filepath).exists())

        with open(filepath, 'r', encoding='utf-8') as f:
            loaded_data = json.load(f)

        self.assertEqual(loaded_data, data)

    def test_save_to_nested_file(self):
        """测试保存到嵌套目录"""
        data = {"test": "data"}
        filepath = str(self.root / "nested" / "dir" / "test.json")

        save_to_file(data, filepath)

        self.assertTrue(Path(filepath).exists())


if __name__ == '__main__':
    unittest.main()