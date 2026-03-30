#!/usr/bin/env python
"""测试运行脚本 - 运行所有测试"""
import subprocess
import sys


def run_tests():
    """运行所有测试"""
    print("=" * 60)
    print("运行 MyBook 测试套件")
    print("=" * 60)
    
    # 运行 pytest
    result = subprocess.run(
        ["pytest", "-v", "--tb=short"],
        cwd="backend",
        capture_output=False
    )
    
    return result.returncode


if __name__ == "__main__":
    sys.exit(run_tests())
