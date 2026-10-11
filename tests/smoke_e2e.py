#!/usr/bin/env python3
"""FilePilot 端到端（E2E）冒烟测试

以子进程方式真实调用 `python -m filepilot ...`，验证 CLI 的输出契约：
    python tests/smoke_e2e.py

说明：
    * 子进程的 stdout/stderr 重定向到临时文件（不用管道），避免沙箱/管道限制；
    * 不依赖 unittest，退出码 0 表示全部通过，1 表示有失败。
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
EXPECTED_VERSION = "0.2.0"


class CheckFailure(Exception):
    """单条断言失败"""


class SmokeRunner:
    def __init__(self) -> None:
        self.passed = 0
        self.failed: list[tuple[str, str]] = []
        self.temp_dir = Path(tempfile.mkdtemp(prefix="filepilot_e2e_"))
        self.log_dir = self.temp_dir / "_logs"
        self.log_dir.mkdir()

    # ---------- 基础设施 ----------

    def check(self, name: str) -> "SmokeRunner":
        """上下文管理器风格的检查项"""
        return _CheckContext(self, name)

    def run_cli(self, *args: str) -> tuple[int, str, str]:
        """运行 CLI，返回 (退出码, stdout, stderr)"""
        index = len(list(self.log_dir.glob("*.out")))
        out_path = self.log_dir / f"{index}.out"
        err_path = self.log_dir / f"{index}.err"

        env = os.environ.copy()
        env["PYTHONPATH"] = str(PROJECT_ROOT) + os.pathsep + env.get("PYTHONPATH", "")
        env["PYTHONIOENCODING"] = "utf-8"

        with open(out_path, "wb") as out_file, open(err_path, "wb") as err_file:
            proc = subprocess.run(
                [sys.executable, "-m", "filepilot", *args],
                cwd=str(PROJECT_ROOT),
                stdout=out_file,
                stderr=err_file,
                env=env,
                stdin=subprocess.DEVNULL,
            )

        stdout = out_path.read_text(encoding="utf-8", errors="replace")
        stderr = err_path.read_text(encoding="utf-8", errors="replace")
        return proc.returncode, stdout, stderr

    # ---------- 测试数据 ----------

    def build_fixture(self) -> tuple[Path, dict]:
        """创建目录树并返回 (根目录, 期望值)"""
        root = self.temp_dir / "downloads"
        root.mkdir()

        (root / "photo.jpg").write_bytes(b"J" * 2048)
        (root / "notes.txt").write_text("hello filepilot", encoding="utf-8")
        (root / "script.py").write_text("print(1)", encoding="utf-8")

        sub = root / "sub"
        sub.mkdir()
        (sub / "deep.log").write_text("ERROR boom", encoding="utf-8")
        (sub / "data.json").write_text("{}", encoding="utf-8")

        deeper = sub / "deeper"
        deeper.mkdir()
        (deeper / "deeper.md").write_text("# md", encoding="utf-8")

        (root / "empty_dir").mkdir()

        # 隐藏文件 / 隐藏目录
        (root / ".secret").write_text("hidden", encoding="utf-8")
        hidden_dir = root / ".hidden_dir"
        hidden_dir.mkdir()
        (hidden_dir / "inside.txt").write_text("hidden inside", encoding="utf-8")

        visible_files = [
            root / "photo.jpg",
            root / "notes.txt",
            root / "script.py",
            sub / "deep.log",
            sub / "data.json",
            deeper / "deeper.md",
        ]
        expected = {
            "root": root,
            "visible_count": len(visible_files),
            "visible_size": sum(p.stat().st_size for p in visible_files),
            "with_hidden_count": len(visible_files) + 2,
            "top_level_count": 3,
        }
        return root, expected

    def cleanup(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)


class _CheckContext:
    def __init__(self, runner: SmokeRunner, name: str) -> None:
        self.runner = runner
        self.name = name

    def __enter__(self) -> "_CheckContext":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        if exc_type is None:
            self.runner.passed += 1
            print(f"[PASS] {self.name}")
        elif issubclass(exc_type, CheckFailure):
            self.runner.failed.append((self.name, str(exc)))
            print(f"[FAIL] {self.name}: {exc}")
        else:  # 非预期异常，同样记录为失败
            self.runner.failed.append((self.name, f"{exc_type.__name__}: {exc}"))
            print(f"[FAIL] {self.name}: {exc_type.__name__}: {exc}")
        return True  # 吞掉异常，继续跑后面的检查


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise CheckFailure(message)


def main() -> int:
    runner = SmokeRunner()
    print("=" * 60)
    print("FilePilot CLI 端到端冒烟测试")
    print("=" * 60)

    try:
        root, exp = runner.build_fixture()

        # 1. 扫描到 JSON 文件
        out_json = runner.temp_dir / "out" / "files.json"  # 父目录故意不存在
        with runner.check("scan -o 写出 JSON（自动创建父目录）"):
            code, out, err = runner.run_cli("scan", str(root), "-o", str(out_json), "-v")
            expect(code == 0, f"退出码应为 0，实际 {code}；stderr={err.strip()}")
            expect(out_json.exists(), "输出 JSON 不存在")
            data = json.loads(out_json.read_text(encoding="utf-8"))
            for key in ("metadata", "summary", "files", "errors"):
                expect(key in data, f"缺少顶层字段 {key}")
            expect(data["metadata"]["tool"] == "filepilot", "metadata.tool 不正确")
            expect(data["metadata"]["version"] == EXPECTED_VERSION, "metadata.version 不正确")
            expect(data["summary"]["file_count"] == exp["visible_count"],
                   f"file_count 应为 {exp['visible_count']}，实际 {data['summary']['file_count']}")
            expect(len(data["files"]) == exp["visible_count"], "files 数量与 file_count 不一致")
            expect(data["summary"]["total_size"] == exp["visible_size"],
                   f"total_size 应为 {exp['visible_size']}，实际 {data['summary']['total_size']}")
            expect(data["summary"]["error_count"] == 0, "正常目录不应有错误")
            expect(data["errors"] == [], "errors 应为空列表")
            expect(".log" in {f["extension"] for f in data["files"]}, "未识别 .log 扩展名")

        # 2. summary 字段与文件条目结构
        with runner.check("JSON 报告字段完整（file_count/error_count/ISO 时间）"):
            from datetime import datetime
            for item in data["files"]:
                for key in ("path", "absolute_path", "name", "size", "extension", "modified_time"):
                    expect(key in item, f"文件条目缺少 {key}")
                datetime.fromisoformat(item["modified_time"])  # 解析失败会抛异常

        # 3. --no-skip-hidden
        with runner.check("--no-skip-hidden 会把隐藏文件算进来"):
            code, out, err = runner.run_cli("scan", str(root), "--no-skip-hidden")
            expect(code == 0, f"退出码应为 0，实际 {code}")
            data_hidden = json.loads(out)
            expect(data_hidden["summary"]["file_count"] == exp["with_hidden_count"],
                   f"应为 {exp['with_hidden_count']}，实际 {data_hidden['summary']['file_count']}")

        # 4. --include-hidden（--no-skip-hidden 的别名）
        with runner.check("--include-hidden 与 --no-skip-hidden 等价"):
            code, out, err = runner.run_cli("scan", str(root), "--include-hidden")
            expect(code == 0, f"退出码应为 0，实际 {code}")
            data_alias = json.loads(out)
            expect(data_alias["summary"]["file_count"] == exp["with_hidden_count"],
                   f"应为 {exp['with_hidden_count']}，实际 {data_alias['summary']['file_count']}")

        # 5. --max-depth 1
        with runner.check("--max-depth 1 只扫描顶层"):
            code, out, err = runner.run_cli("scan", str(root), "--max-depth", "1")
            expect(code == 0, f"退出码应为 0，实际 {code}")
            data_depth = json.loads(out)
            expect(data_depth["summary"]["file_count"] == exp["top_level_count"],
                   f"应为 {exp['top_level_count']}，实际 {data_depth['summary']['file_count']}")

        # 5. 不传 -o 时 JSON 打到 stdout
        with runner.check("不带 -o 时把 JSON 打印到 stdout"):
            code, out, err = runner.run_cli("scan", str(root))
            expect(code == 0, f"退出码应为 0，实际 {code}")
            expect(json.loads(out)["summary"]["file_count"] == exp["visible_count"],
                   "stdout 的 JSON 内容不正确")

        # 6. 目录不存在 → 退出码 1
        with runner.check("目录不存在时退出码为 1 且提示原因"):
            code, out, err = runner.run_cli("scan", str(runner.temp_dir / "not_exists"))
            expect(code == 1, f"退出码应为 1，实际 {code}")
            expect("目录不存在" in err, f"stderr 未提示目录不存在：{err.strip()}")

        # 7. --version
        with runner.check("--version 输出版本号"):
            code, out, err = runner.run_cli("--version")
            expect(code == 0, f"退出码应为 0，实际 {code}")
            expect(EXPECTED_VERSION in out, f"未输出版本号：{out.strip()}")

        # 8. 无子命令 → 打印帮助并返回 1
        with runner.check("无子命令时打印帮助并返回 1"):
            code, out, err = runner.run_cli()
            expect(code == 1, f"退出码应为 1，实际 {code}")
            expect("usage" in (out + err).lower(), "未打印帮助信息")

        # 9. 子命令后再写 -v（子解析器参数）
        with runner.check("scan 子命令后可使用 -v"):
            code, out, err = runner.run_cli("scan", str(root), "-v")
            expect(code == 0, f"退出码应为 0，实际 {code}")
            expect("扫描完成" in out, "verbose 统计信息未输出")

    finally:
        runner.cleanup()

    print("-" * 60)
    print(f"通过 {runner.passed} 项，失败 {len(runner.failed)} 项")
    for name, reason in runner.failed:
        print(f"  - {name}: {reason}")
    print("=" * 60)
    return 1 if runner.failed else 0


if __name__ == "__main__":
    sys.exit(main())
