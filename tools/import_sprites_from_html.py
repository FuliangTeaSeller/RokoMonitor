"""
从精灵图鉴HTML提取数据并导入到数据库

HTML结构分析:
- 精灵卡片: <div class="divsort" data-param1="形态" data-param2="属性" ...>
- 精灵名称: <span class="font-mainfeiziti">...</span>
- 精灵图片: <img class="rocom_prop_icon" srcset="...">
- 属性图标: <img class="rocom_pet_icon" srcset="...">
- 属性名称: data-param2 属性值 (如"光"、"火"、"水"等)
"""

import sqlite3
import os
import shutil
from pathlib import Path
from bs4 import BeautifulSoup
from PIL import Image
import urllib.parse
import re

# 路径配置
PROJECT_ROOT = Path(__file__).parent.parent
HTML_PATH = PROJECT_ROOT / "reference" / "精灵" / "新建文件夹" / "精灵图鉴 - 洛克王国_手游WIKI_BWIKI_哔哩哔哩.html"
HTML_FILES_DIR = PROJECT_ROOT / "reference" / "精灵" / "新建文件夹" / "精灵图鉴 - 洛克王国_手游WIKI_BWIKI_哔哩哔哩_files"
DB_PATH = PROJECT_ROOT / "data" / "roko_monitor.db"
IMAGES_SPRITES_DIR = PROJECT_ROOT / "data" / "images" / "sprites"
IMAGES_ATTRIBUTES_DIR = PROJECT_ROOT / "data" / "images" / "attributes"

# 属性文件名映射 (中文 -> 英文)
ATTRIBUTE_NAME_MAP = {
    "火": "fire",
    "水": "water",
    "草": "grass",
    "冰": "ice",
    "龙": "dragon",
    "电": "electric",
    "毒": "poison",
    "虫": "bug",
    "武": "fighting",
    "翼": "flying",
    "萌": "cute",
    "幽": "ghost",
    "恶": "dark",
    "机械": "machine",
    "幻": "illusion",
    "光": "light",
    "地": "ground",
    "普通": "normal",
}


def ensure_image_dirs():
    """确保图片目录存在"""
    IMAGES_SPRITES_DIR.mkdir(parents=True, exist_ok=True)
    IMAGES_ATTRIBUTES_DIR.mkdir(parents=True, exist_ok=True)
    print(f"图片目录准备完成:")
    print(f"  - {IMAGES_SPRITES_DIR}")
    print(f"  - {IMAGES_ATTRIBUTES_DIR}")


def get_or_create_attribute(cursor, attribute_name):
    """获取或创建属性记录"""
    # 查询属性是否存在
    cursor.execute("SELECT id FROM attribute WHERE name = ?", (attribute_name,))
    result = cursor.fetchone()

    if result:
        return result[0]

    # 创建新属性
    image_filename = f"30px-图标_宠物_属性_{attribute_name}.png"
    source_path = HTML_FILES_DIR / image_filename

    if source_path.exists():
        # 复制属性图片
        english_name = ATTRIBUTE_NAME_MAP.get(attribute_name, attribute_name)
        dest_path = IMAGES_ATTRIBUTES_DIR / f"{english_name}.png"

        # 转换webp到png（如果需要）
        try:
            with Image.open(source_path) as img:
                img.save(dest_path, "PNG")
            db_image_path = f"data/images/attributes/{english_name}.png"
            print(f"  复制属性图片: {attribute_name} -> {db_image_path}")
        except Exception as e:
            print(f"  警告: 无法转换属性图片 {attribute_name}: {e}")
            db_image_path = None
    else:
        db_image_path = None
        print(f"  警告: 未找到属性图片 {image_filename}")

    cursor.execute(
        "INSERT INTO attribute (name, image_path) VALUES (?, ?)",
        (attribute_name, db_image_path)
    )
    return cursor.lastrowid


def extract_sprite_data(sprite_div, sprite_id):
    """解析单个精灵卡片"""
    sprite_data = {}

    # 从data-param2获取属性
    sprite_data["attribute"] = sprite_div.get("data-param2", "")

    # 获取精灵名称
    name_elem = sprite_div.find("span", class_="font-mainfeiziti")
    if name_elem:
        sprite_data["name"] = name_elem.get_text(strip=True)
    else:
        sprite_data["name"] = f"未知精灵_{sprite_id}"

    # 获取精灵图片URL
    icon_elem = sprite_div.find("img", class_="rocom_prop_icon")
    if icon_elem:
        # 从srcset中提取图片URL
        srcset = icon_elem.get("srcset", "")
        if srcset:
            # srcset格式: "url1 1.5x, url2 2x"
            # 我们使用第一个URL
            urls = srcset.split(",")
            if urls:
                sprite_data["image_url"] = urls[0].strip().split()[0]
        else:
            # 如果没有srcset，尝试src
            sprite_data["image_url"] = icon_elem.get("src", "")
    else:
        sprite_data["image_url"] = ""

    return sprite_data


def download_image(url, dest_path):
    """下载并保存图片"""
    try:
        # 如果是本地文件路径
        if url.startswith("./") or url.startswith(".."):
            # 相对于HTML文件的路径
            html_dir = HTML_PATH.parent
            img_path = html_dir / url.lstrip("./")
            if not img_path.exists():
                # 尝试从_files目录查找
                filename = os.path.basename(url)
                img_path = HTML_FILES_DIR / filename

            if img_path.exists():
                with Image.open(img_path) as img:
                    img.save(dest_path, "PNG")
                return True
        elif url.startswith("http"):
            # 如果是网络URL，使用urllib下载
            import urllib.request
            urllib.request.urlretrieve(url, dest_path)
            with Image.open(dest_path) as img:
                img.save(dest_path, "PNG")
            return True
        return False
    except Exception as e:
        print(f"  下载图片失败: {e}")
        return False


def import_sprites():
    """从HTML导入精灵到数据库"""
    print("=== 开始导入精灵数据 ===\n")

    # 确保图片目录存在
    ensure_image_dirs()

    # 连接数据库
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 读取HTML文件
    print(f"读取HTML文件: {HTML_PATH}")
    with open(HTML_PATH, "r", encoding="utf-8") as f:
        html_content = f.read()

    soup = BeautifulSoup(html_content, "html.parser")

    # 查找所有精灵卡片
    sprite_divs = soup.find_all("div", class_="divsort")
    print(f"找到 {len(sprite_divs)} 个精灵\n")

    # 导入精灵
    imported_count = 0
    skipped_count = 0

    for idx, sprite_div in enumerate(sprite_divs, start=1):
        sprite_data = extract_sprite_data(sprite_div, idx)

        # 检查精灵是否已存在
        cursor.execute("SELECT id FROM sprite WHERE name = ?", (sprite_data["name"],))
        if cursor.fetchone():
            print(f"[{idx}] 跳过已存在精灵: {sprite_data['name']}")
            skipped_count += 1
            continue

        # 获取或创建属性
        attribute_name = sprite_data["attribute"]
        if not attribute_name:
            print(f"[{idx}] 警告: 精灵 '{sprite_data['name']}' 没有属性，跳过")
            skipped_count += 1
            continue

        attribute_id = get_or_create_attribute(cursor, attribute_name)

        # 处理精灵图片
        image_url = sprite_data["image_url"]
        db_image_path = None

        if image_url:
            dest_path = IMAGES_SPRITES_DIR / f"{idx}.png"

            # 尝试获取图片文件名
            filename = os.path.basename(image_url)

            # 尝试从本地_files目录查找
            source_path = HTML_FILES_DIR / filename
            if not source_path.exists():
                # 尝试解码URL编码的文件名
                decoded_filename = urllib.parse.unquote(filename)
                source_path = HTML_FILES_DIR / decoded_filename

            if source_path.exists():
                try:
                    with Image.open(source_path) as img:
                        img.save(dest_path, "PNG")
                    db_image_path = f"data/images/sprites/{idx}.png"
                except Exception as e:
                    print(f"[{idx}] 警告: 无法转换精灵图片 {filename}: {e}")
            else:
                print(f"[{idx}] 警告: 未找到精灵图片 {filename}")

        # 插入精灵记录
        cursor.execute(
            "INSERT INTO sprite (name, image_path) VALUES (?, ?)",
            (sprite_data["name"], db_image_path)
        )
        sprite_id = cursor.lastrowid

        # 关联属性
        cursor.execute(
            "INSERT INTO sprite_attribute (sprite_id, attribute_id) VALUES (?, ?)",
            (sprite_id, attribute_id)
        )

        imported_count += 1
        print(f"[{idx}] 导入: {sprite_data['name']} ({attribute_name})")

    # 提交事务
    conn.commit()

    # 显示统计
    print(f"\n=== 导入完成 ===")
    print(f"总计: {len(sprite_divs)} 个精灵")
    print(f"成功导入: {imported_count} 个")
    print(f"跳过: {skipped_count} 个")

    # 显示属性统计
    cursor.execute("SELECT COUNT(*) FROM attribute")
    attr_count = cursor.fetchone()[0]
    print(f"属性总数: {attr_count} 个")

    # 显示精灵统计
    cursor.execute("SELECT COUNT(*) FROM sprite")
    sprite_count = cursor.fetchone()[0]
    print(f"精灵总数: {sprite_count} 个")

    conn.close()
    print("\n数据库已更新")


if __name__ == "__main__":
    import_sprites()
