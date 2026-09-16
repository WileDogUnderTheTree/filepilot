#!/usr/bin/env python3
"""测试 Scanner 类的各种功能"""

import unittest
import tempfile
import shutil
import os
import sys
from pathlib import Path
from unittest.mock import patch

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from filepilot.scanner import Scanner
from filepilot.exceptions import DirectoryNotFoundError, FileAccessError


class TestScannerBasic(unittest.TestCase):
    """测试 Scanner 的基本功能"""

    def setUp(self):
        """创建测试环境"""
        self.temp_dir = tempfile.mkdtemp()
        self.root = Path(self.temp_dir)

        # 创建测试文件结构
        self.create_test_structure()

    def tearDown(self):
        """清理测试环境"""
        shutil.rmtree(self.temp_dir)

    def create_test_structure(self):
        """创建测试目录结构"""
        # 1. 顶层文件
        (self.root / "file1.txt").write_text("Content 1")
        (self.root / "file2.jpg").write_bytes(b"fake_jpg_data")
        (self.root / "file3.py").write_text("print('hello')")

        # 2. 子目录
        sub_dir1 = self.root / "sub1"
        sub_dir1.mkdir()
        (sub_dir1 / "nested1.txt").write_text("Nested 1")
        (sub_dir1 / "nested2.log").write_text("Log entry")

        # 3. 更深层子目录
        sub_dir2 = self.root / "sub1" / "sub2"
        sub_dir2.mkdir()
        (sub_dir2 / "deep1.txt").write_text("Deep 1")
        (sub_dir2 / "deep2.md").write_text("# Markdown")

        # 4. 隐藏文件（Unix-like 系统）
        (self.root / ".hidden_file").write_text("Hidden")
        (self.root / ".hidden_dir").mkdir()
        (self.root / ".hidden_dir" / "hidden.txt").write_text("Hidden file")

        # 5. 空目录
        (self.root / "empty_dir").mkdir()

    def test_scan_basic(self):
        """测试基本扫描 - 跳过隐藏文件"""
        scanner = Scanner(self.root)
        files = scanner.scan()

        # 应该找到的文件（不包含隐藏文件）
        expected_files = 7  # file1.txt, file2.jpg, file3.py, 
        # sub1/nested1.txt, sub1/nested2.log,
        # sub1/sub2/deep1.txt, sub1/sub2/deep2.md

        self.assertEqual(len(files), expected_files)
        self.assertEqual(scanner.file_count, expected_files)

    def test_scan_no_skip_hidden(self):
        """测试不跳过隐藏文件"""
        scanner = Scanner(self.root, skip_hidden=False)
        files = scanner.scan()

        # 应该多找到 .hidden_file 和 .hidden_dir/hidden.txt
        expected_files = 9  # 7 + 2 个隐藏文件

        self.assertEqual(len(files), expected_files)

    def test_scan_max_depth(self):
        """测试最大深度限制"""
        # 限制深度为 1（只扫描顶层目录）
        scanner = Scanner(self.root, max_depth=1)
        files = scanner.scan()

        # 只应该找到顶层的3个文件
        self.assertEqual(len(files), 3)

        # 限制深度为 2
        scanner = Scanner(self.root, max_depth=2)
        files = scanner.scan()

        # 应该找到顶层 + sub1 下的文件
        self.assertEqual(len(files), 5)  # 3 + 2

        # 不限制深度
        scanner = Scanner(self.root, max_depth=None)
        files = scanner.scan()
        self.assertEqual(len(files), 7)

    def test_scan_size_calculation(self):
        """测试文件大小统计"""
        scanner = Scanner(self.root)
        scanner.scan()

        # 手动计算预期大小
        expected_size = 0
        for file_path in self.root.rglob('*'):
            if file_path.is_file() and not any(part.startswith('.') for part in file_path.parts):
                expected_size += file_path.stat().st_size

        self.assertEqual(scanner.total_size, expected_size)

    def test_directory_not_found(self):
        """测试目录不存在"""
        with self.assertRaises(DirectoryNotFoundError):
            scanner = Scanner(Path("/nonexistent/path"))
            scanner.scan()

    def test_file_as_root(self):
        """测试将文件作为根目录"""
        file_path = self.root / "file1.txt"
        with self.assertRaises(Exception):
            scanner = Scanner(file_path)
            scanner.scan()

    def test_scan_statistics(self):
        """测试扫描统计信息"""
        scanner = Scanner(self.root)
        files = scanner.scan()

        summary = scanner.get_report()
        self.assertIn("summary", summary)
        self.assertEqual(summary["summary"]["file_count"], 7)
        self.assertEqual(summary["summary"]["error_count"], 0)


class TestScannerEdgeCases(unittest.TestCase):
    """测试 Scanner 的边界情况"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.root = Path(self.temp_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_empty_directory(self):
        """测试空目录"""
        scanner = Scanner(self.root)
        files = scanner.scan()
        self.assertEqual(len(files), 0)
        self.assertEqual(scanner.total_size, 0)

    def test_single_file_directory(self):
        """测试只有一个文件的目录"""
        file_path = self.root / "only.txt"
        file_path.write_text("only file")

        scanner = Scanner(self.root)
        files = scanner.scan()
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0].path, file_path)

    @patch('pathlib.Path.stat')
    def test_permission_error(self, mock_stat):
        """测试权限错误处理"""
        # 创建测试文件
        file_path = self.root / "test.txt"
        file_path.write_text("content")

        # 模拟权限错误
        mock_stat.side_effect = PermissionError("Permission denied")

        scanner = Scanner(self.root)
        files = scanner.scan()

        # 应该有错误记录，但程序不应该崩溃
        self.assertEqual(len(files), 0)
        self.assertEqual(len(scanner.errors), 1)
        self.assertEqual(scanner.errors[0].error_type, "access")

    def test_symlinks(self):
        """测试符号链接处理"""
        # 创建测试文件
        real_file = self.root / "real.txt"
        real_file.write_text("Real content")

        # 创建符号链接
        symlink = self.root / "link.txt"
        try:
            symlink.symlink_to(real_file)

            # 不跟随符号链接（默认）
            scanner = Scanner(self.root, follow_symlinks=False)
            files = scanner.scan()
            self.assertEqual(len(files), 1)  # 只找到 real.txt

            # 跟随符号链接
            scanner = Scanner(self.root, follow_symlinks=True)
            files = scanner.scan()
            self.assertEqual(len(files), 2)  # 找到 real.txt 和 link.txt

        except (OSError, NotImplementedError):
            self.skipTest("符号链接在此平台上不可用")

    def test_many_files_performance(self):
        """测试大量文件的性能"""
        import time

        # 创建 1000 个文件
        for i in range(1000):
            (self.root / f"file_{i}.txt").write_text(f"Content {i}")

        start_time = time.time()
        scanner = Scanner(self.root)
        files = scanner.scan()
        elapsed = time.time() - start_time

        self.assertEqual(len(files), 1000)
        # 设置合理的时间限制（例如 5 秒）
        self.assertLess(elapsed, 5, f"扫描 1000 个文件花费了 {elapsed} 秒")