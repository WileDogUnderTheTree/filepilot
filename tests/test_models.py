#!/usr/bin/env python3
"""测试 FileItem 数据模型"""

import unittest
import tempfile
import os
from pathlib import Path
from datetime import datetime
import sys
import time

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from filepilot.models import FileItem
from filepilot.exceptions import FileAccessError


class TestFileItem(unittest.TestCase):
    """测试 FileItem 类的各种功能"""

    def setUp(self):
        """每个测试前运行"""
        # 创建临时目录
        self.temp_dir = tempfile.mkdtemp()
        self.root = Path(self.temp_dir)

        # 创建测试文件
        self.test_file = self.root / "test.txt"
        self.test_file.write_text("Hello, World!")

        # 创建子目录和文件
        self.sub_dir = self.root / "subdir"
        self.sub_dir.mkdir()
        self.nested_file = self.sub_dir / "nested.py"
        self.nested_file.write_text("print('hello')")

        # 保存固定的修改时间
        self.fixed_time = 1609459200  # 2021-01-01 00:00:00 UTC
        os.utime(self.test_file, (self.fixed_time, self.fixed_time))

    def tearDown(self):
        """每个测试后运行"""
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_create_file_item(self):
        """测试创建 FileItem"""
        item = FileItem.from_path(self.test_file)

        # 检查基本属性
        self.assertEqual(item.path, self.test_file)
        self.assertGreater(item.size, 0)  # 文件大小应该大于0
        self.assertEqual(item.extension, '.txt')
        self.assertAlmostEqual(item.modified_time, self.fixed_time, delta=1)

    def test_file_item_attributes(self):
        """测试 FileItem 的属性"""
        item = FileItem.from_path(self.test_file)

        # 测试 to_dict 方法
        data = item.to_dict()
        self.assertIn("path", data)
        self.assertIn("name", data)
        self.assertIn("size", data)
        self.assertIn("extension", data)
        self.assertIn("modified_time", data)

        # 测试 name 属性
        self.assertEqual(data["name"], "test.txt")

        # 测试路径格式
        self.assertEqual(data["path"], str(self.test_file))

    def test_extension_detection(self):
        """测试扩展名识别"""
        # 测试常见文件类型
        test_cases = [
            ("file.txt", ".txt"),
            ("image.JPG", ".jpg"),  # 应该转为小写
            ("archive.tar.gz", ".gz"),  # 只取最后一部分
            ("no_extension", ""),  # 无扩展名
            (".hidden_file", ""),  # 隐藏文件
        ]

        for filename, expected_ext in test_cases:
            with self.subTest(filename=filename):
                file_path = self.root / filename
                file_path.write_text("test")
                item = FileItem.from_path(file_path)
                self.assertEqual(item.extension, expected_ext)

    def test_size_formatting(self):
        """测试大小格式化"""
        # 直接测试 _format_size 方法
        item = FileItem.from_path(self.test_file)

        # 测试不同大小
        sizes = [
            (1024, "1.0KB"),
            (1024 ** 2, "1.0MB"),
            (1024 ** 3, "1.0GB"),
            (500, "500.0B"),
        ]

        for size, expected in sizes:
            with self.subTest(size=size):
                # 临时修改 size 属性测试
                item.size = size
                formatted = item._format_size()
                # 检查格式（部分匹配）
                self.assertIn(expected.split('.')[0], formatted)

    def test_str_method(self):
        """测试字符串表示"""
        item = FileItem.from_path(self.test_file)
        str_repr = str(item)

        # 应该包含文件名和大小信息
        self.assertIn("test.txt", str_repr)
        self.assertIn("B", str_repr)  # 至少包含大小单位

    def test_non_existent_file(self):
        """测试不存在的文件"""
        non_existent = self.root / "nonexistent.txt"
        with self.assertRaises(FileAccessError):
            FileItem.from_path(non_existent)

    def test_directory_as_file(self):
        """测试将目录当作文件处理"""
        # 目录应该能被创建 FileItem，但 size 可能为 0
        item = FileItem.from_path(self.sub_dir)
        self.assertEqual(item.size, 0)
        self.assertEqual(item.extension, "")


class TestFileItemEdgeCases(unittest.TestCase):
    """测试 FileItem 的边界情况"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.root = Path(self.temp_dir)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_empty_file(self):
        """测试空文件"""
        empty_file = self.root / "empty.txt"
        empty_file.touch()  # 创建空文件

        item = FileItem.from_path(empty_file)
        self.assertEqual(item.size, 0)

        # 格式化后应该是 0.0B
        self.assertEqual(item._format_size(), "0.0B")

    def test_large_number_files(self):
        """测试大量文件时的性能"""
        # 创建 100 个文件
        for i in range(100):
            (self.root / f"file_{i}.txt").write_text("x" * 1000)

        # 批量创建 FileItem
        items = []
        for file_path in self.root.iterdir():
            item = FileItem.from_path(file_path)
            items.append(item)

        self.assertEqual(len(items), 100)