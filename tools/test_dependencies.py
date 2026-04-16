"""
测试依赖是否正确安装
"""

import sys

def test_imports():
    """测试必要的导入"""
    print("=== 测试依赖包 ===\n")

    # Python标准库
    try:
        import sqlite3
        print("✓ sqlite3 (Python标准库)")
    except ImportError:
        print("✗ sqlite3 不可用")
        return False

    # 第三方库
    deps = [
        ("PIL", "Pillow - 图片处理"),
        ("bs4", "BeautifulSoup4 - HTML解析"),
        ("sqlalchemy", "SQLAlchemy - 数据库ORM"),
    ]

    all_ok = True
    for module, description in deps:
        try:
            __import__(module)
            print(f"✓ {description}")
        except ImportError:
            print(f"✗ {description} - 未安装")
            all_ok = False

    if all_ok:
        print("\n=== 所有依赖已就绪 ===")
    else:
        print("\n=== 请运行: pip install -r requirements.txt ===")

    return all_ok

if __name__ == "__main__":
    ok = test_imports()
    sys.exit(0 if ok else 1)
