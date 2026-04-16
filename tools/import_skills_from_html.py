"""
从技能图鉴HTML提取数据并导入到数据库

HTML结构分析:
- 技能卡片: <div class="detailed-skill-card">
- 技能名称: <div class="detailed-skill-name">
- 技能图标: <img class="detailed-skill-icon">
- 耗能: <div class="stat-label">耗能</div> + star图标 + 数字
- 分类: <div class="stat-label">分类</div> + 图标 (物攻/魔攻/状态/防御)
- 属性: <div class="stat-label">属性</div> + 图标
- 威力: <div class="stat-label">威力</div> + 数字或 "--"
- 描述: <div class="detailed-skill-desc">
"""

import sqlite3
import os
import shutil
from pathlib import Path
from bs4 import BeautifulSoup
from PIL import Image

# 路径配置
PROJECT_ROOT = Path(__file__).parent.parent
HTML_PATH = PROJECT_ROOT / "reference" / "技能" / "技能图鉴.html"
HTML_FILES_DIR = PROJECT_ROOT / "reference" / "技能" / "技能图鉴_files"
DB_PATH = PROJECT_ROOT / "roko_monitor.db"
IMAGES_SKILLS_DIR = PROJECT_ROOT / "data" / "images" / "skills"
IMAGES_ATTRIBUTES_DIR = PROJECT_ROOT / "data" / "images" / "attributes"

# 分类映射 (HTML中的分类 -> 数据库中的分类)
CATEGORY_MAP = {
    "物攻": "物攻",
    "魔攻": "魔攻",
    "状态": "变化",
    "防御": "变化",
}

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
    IMAGES_SKILLS_DIR.mkdir(parents=True, exist_ok=True)
    IMAGES_ATTRIBUTES_DIR.mkdir(parents=True, exist_ok=True)
    print(f"图片目录准备完成:")
    print(f"  - {IMAGES_SKILLS_DIR}")
    print(f"  - {IMAGES_ATTRIBUTES_DIR}")


def get_or_create_attribute(cursor, attribute_name):
    """获取或创建属性记录"""
    # 查询属性是否存在
    cursor.execute("SELECT id FROM attribute WHERE name = ?", (attribute_name,))
    result = cursor.fetchone()

    if result:
        return result[0]

    # 创建新属性
    image_filename = f"{attribute_name}.webp"
    source_path = HTML_FILES_DIR / image_filename

    if source_path.exists():
        # 复制属性图片
        english_name = ATTRIBUTE_NAME_MAP.get(attribute_name, attribute_name)
        dest_path = IMAGES_ATTRIBUTES_DIR / f"{english_name}.png"

        # 转换webp到png
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


def extract_stats(stat_col):
    """从stat-col中提取标签和值"""
    label_elem = stat_col.find("div", class_="stat-label")
    value_elem = stat_col.find("div", class_="stat-value")

    if not label_elem or not value_elem:
        return None, None

    label = label_elem.get_text(strip=True)

    # 处理不同的值类型
    if value_elem.find("img", class_="stat-star"):
        # 耗能: star图标 + 数字
        text = value_elem.get_text(strip=True)
        value = int(text)
    elif value_elem.find("img", class_="stat-icon"):
        # 分类或属性: 图标
        img = value_elem.find("img", class_="stat-icon")
        value = img.get("alt", "")
    else:
        # 威力或其他数字值
        text = value_elem.get_text(strip=True)
        if text == "--":
            value = None
        else:
            try:
                value = int(text)
            except ValueError:
                value = text

    return label, value


def parse_skill_card(card, skill_id):
    """解析单个技能卡片"""
    skill_data = {}

    # 技能名称
    name_elem = card.find("div", class_="detailed-skill-name")
    skill_data["name"] = name_elem.get_text(strip=True) if name_elem else f"未知技能_{skill_id}"

    # 技能图标路径
    icon_elem = card.find("img", class_="detailed-skill-icon")
    skill_data["icon_src"] = icon_elem.get("src", "") if icon_elem else ""

    # 技能描述
    desc_elem = card.find("div", class_="detailed-skill-desc")
    skill_data["description"] = desc_elem.get_text(strip=True) if desc_elem else ""

    # 解析统计信息 (耗能、分类、属性、威力)
    stats = {}
    stat_cols = card.find_all("div", class_="stat-col")
    for col in stat_cols:
        label, value = extract_stats(col)
        if label and value is not None:
            stats[label] = value

    skill_data["energy_consumption"] = stats.get("耗能", 0)
    skill_data["category"] = stats.get("分类", "变化")
    skill_data["attribute"] = stats.get("属性", "")
    skill_data["power"] = stats.get("威力")

    # 映射分类
    skill_data["category"] = CATEGORY_MAP.get(skill_data["category"], "变化")

    return skill_data


def import_skills():
    """从HTML导入技能到数据库"""
    print("=== 开始导入技能数据 ===\n")

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

    # 查找所有技能卡片
    skill_cards = soup.find_all("div", class_="detailed-skill-card")
    print(f"找到 {len(skill_cards)} 个技能\n")

    # 导入技能
    imported_count = 0
    skipped_count = 0

    for idx, card in enumerate(skill_cards, start=1):
        skill_data = parse_skill_card(card, idx)

        # 检查技能是否已存在
        cursor.execute("SELECT id FROM skill WHERE name = ?", (skill_data["name"],))
        if cursor.fetchone():
            print(f"[{idx}] 跳过已存在技能: {skill_data['name']}")
            skipped_count += 1
            continue

        # 获取或创建属性
        attribute_name = skill_data["attribute"]
        if not attribute_name:
            print(f"[{idx}] 警告: 技能 '{skill_data['name']}' 没有属性，跳过")
            skipped_count += 1
            continue

        attribute_id = get_or_create_attribute(cursor, attribute_name)

        # 处理技能图片
        icon_src = skill_data["icon_src"]
        if icon_src:
            # 提取文件名 (如 ./技能图鉴_files/一拳.webp -> 一拳.webp)
            filename = os.path.basename(icon_src)
            source_path = HTML_FILES_DIR / filename

            if source_path.exists():
                dest_path = IMAGES_SKILLS_DIR / f"{idx}.png"

                try:
                    with Image.open(source_path) as img:
                        img.save(dest_path, "PNG")
                    db_image_path = f"data/images/skills/{idx}.png"
                except Exception as e:
                    print(f"[{idx}] 警告: 无法转换技能图片 {filename}: {e}")
                    db_image_path = None
            else:
                db_image_path = None
                print(f"[{idx}] 警告: 未找到技能图片 {filename}")
        else:
            db_image_path = None

        # 插入技能记录
        cursor.execute(
            """INSERT INTO skill (
                name, energy_consumption, category, attribute_id,
                power, description, beizhu, image_path
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                skill_data["name"],
                skill_data["energy_consumption"],
                skill_data["category"],
                attribute_id,
                skill_data["power"],
                skill_data["description"],
                None,  # beizhu暂无
                db_image_path
            )
        )

        imported_count += 1
        print(f"[{idx}] 导入: {skill_data['name']} "
              f"({skill_data['category']} | {skill_data['attribute']} | "
              f"耗能:{skill_data['energy_consumption']} | 威力:{skill_data['power'] or '--'})")

    # 提交事务
    conn.commit()

    # 显示统计
    print(f"\n=== 导入完成 ===")
    print(f"总计: {len(skill_cards)} 个技能")
    print(f"成功导入: {imported_count} 个")
    print(f"跳过: {skipped_count} 个")

    # 显示属性统计
    cursor.execute("SELECT COUNT(*) FROM attribute")
    attr_count = cursor.fetchone()[0]
    print(f"属性总数: {attr_count} 个")

    conn.close()
    print("\n数据库已更新")


if __name__ == "__main__":
    import_skills()
