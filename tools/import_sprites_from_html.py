#!/usr/bin/env python3
"""
精灵图鉴 HTML 数据提取脚本
从 rkteambuilder.com 保存的 HTML 文件中提取精灵数据
"""

import re
import sqlite3
import os
import shutil
from pathlib import Path
from bs4 import BeautifulSoup
from typing import List, Dict, Tuple


# 属性图标文件名到中文名称的映射
ATTRIBUTE_MAP = {
    'normal.png': '普通',
    'grass.png': '草',
    'fire.png': '火',
    'water.png': '水',
    'light.png': '光',
    'ground.png': '地',
    'ice.png': '冰',
    'dragon.png': '龙',
    'electric.png': '电',
    'poison.png': '毒',
    'bug.png': '虫',
    'fighting.png': '武',
    'flying.png': '翼',
    'cute.png': '萌',
    'ghost.png': '幽',
    'dark.png': '恶',
    'mechanical.png': '机械',
    'illusion.png': '幻',
}


def extract_sprites_from_html(html_path: str, files_dir: str) -> List[Dict]:
    """
    从 HTML 文件中提取精灵数据

    Args:
        html_path: HTML 文件路径
        files_dir: 附件文件目录路径

    Returns:
        精灵数据列表，每个元素包含 id, name, attributes, image_file
    """
    with open(html_path, 'r', encoding='utf-8') as f:
        html = f.read()

    soup = BeautifulSoup(html, 'html.parser')

    sprites = []

    # 查找所有精灵链接
    for link in soup.find_all('a', href=re.compile(r'dex/monsters/\d+')):
        # 提取 ID
        href = link.get('href', '')
        id_match = re.search(r'dex/monsters/(\d+)', href)
        if not id_match:
            continue
        sprite_id = int(id_match.group(1))

        # 提取名称
        name_div = link.find('div', class_='text-sm')
        if not name_div:
            continue
        name = name_div.get('title', '').strip()

        # 提取图片文件名
        img = link.find('img', src=re.compile(r'\.png$'))
        image_file = None
        if img:
            src = img.get('src', '')
            # 提取文件名（去掉路径前缀）
            image_file = os.path.basename(src)

        # 提取属性
        attributes = []
        attr_spans = link.find_all('span', class_=re.compile(r'inline-flex'))
        for attr_span in attr_spans:
            attr_img = attr_span.find('img')
            if attr_img:
                src = attr_img.get('src', '')
                icon_file = os.path.basename(src)
                if icon_file in ATTRIBUTE_MAP:
                    attributes.append(ATTRIBUTE_MAP[icon_file])

        if name and attributes:
            sprites.append({
                'id': sprite_id,
                'name': name,
                'attributes': attributes,
                'image_file': image_file,
            })

    return sprites


def init_database(db_path: str) -> None:
    """
    初始化数据库，创建必要的表
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 创建属性表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS attribute (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            image_path TEXT
        )
    ''')

    # 创建技能表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS skill (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            energy_consumption INTEGER NOT NULL,
            category TEXT NOT NULL CHECK (category IN ('魔攻', '物攻', '变化')),
            attribute_id INTEGER NOT NULL,
            power INTEGER,
            description TEXT,
            beizhu TEXT,
            image_path TEXT,
            FOREIGN KEY (attribute_id) REFERENCES attribute(id)
        )
    ''')

    # 创建精灵表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sprite (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            image_path TEXT
        )
    ''')

    # 创建精灵-属性关联表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sprite_attribute (
            sprite_id INTEGER NOT NULL,
            attribute_id INTEGER NOT NULL,
            PRIMARY KEY (sprite_id, attribute_id),
            FOREIGN KEY (sprite_id) REFERENCES sprite(id) ON DELETE CASCADE,
            FOREIGN KEY (attribute_id) REFERENCES attribute(id) ON DELETE CASCADE
        )
    ''')

    # 创建精灵-技能关联表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sprite_skill (
            sprite_id INTEGER NOT NULL,
            skill_id INTEGER NOT NULL,
            PRIMARY KEY (sprite_id, skill_id),
            FOREIGN KEY (sprite_id) REFERENCES sprite(id) ON DELETE CASCADE,
            FOREIGN KEY (skill_id) REFERENCES skill(id) ON DELETE CASCADE
        )
    ''')

    # 创建索引
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_sprite_name ON sprite(name)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_skill_name ON skill(name)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_sprite_skill_sprite ON sprite_skill(sprite_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_sprite_skill_skill ON sprite_skill(skill_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_sprite_attribute_sprite ON sprite_attribute(sprite_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_attribute_name ON attribute(name)')

    conn.commit()
    conn.close()


def insert_attributes(db_path: str, attributes: List[str]) -> Dict[str, int]:
    """
    插入属性数据并返回属性名称到 ID 的映射

    Args:
        db_path: 数据库路径
        attributes: 属性名称列表

    Returns:
        属性名称到 ID 的映射字典
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    attr_map = {}
    for attr_name in attributes:
        # 检查是否已存在
        cursor.execute('SELECT id FROM attribute WHERE name = ?', (attr_name,))
        row = cursor.fetchone()
        if row:
            attr_map[attr_name] = row[0]
        else:
            # 插入新属性
            cursor.execute('INSERT INTO attribute (name) VALUES (?)', (attr_name,))
            attr_id = cursor.lastrowid
            attr_map[attr_name] = attr_id

    conn.commit()
    conn.close()
    return attr_map


def insert_sprites(db_path: str, sprites: List[Dict], attr_map: Dict[str, int], source_img_dir: str, target_img_dir: str) -> None:
    """
    插入精灵数据并复制图片

    Args:
        db_path: 数据库路径
        sprites: 精灵数据列表
        attr_map: 属性名称到 ID 的映射
        source_img_dir: 源图片目录
        target_img_dir: 目标图片目录
    """
    # 确保目标目录存在
    os.makedirs(target_img_dir, exist_ok=True)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    for sprite in sprites:
        sprite_id = sprite['id']
        name = sprite['name']
        attributes = sprite['attributes']
        image_file = sprite['image_file']

        # 确定图片路径
        image_path = None
        if image_file:
            # 复制图片
            source_path = os.path.join(source_img_dir, image_file)
            if os.path.exists(source_path):
                # 使用精灵 ID 作为目标文件名
                target_file = f"{sprite_id}.png"
                target_path = os.path.join(target_img_dir, target_file)

                # 只有当文件不存在时才复制
                if not os.path.exists(target_path):
                    shutil.copy2(source_path, target_path)

                image_path = f"data/images/sprites/{target_file}"

        # 插入精灵（如果不存在）
        cursor.execute('''
            INSERT OR IGNORE INTO sprite (id, name, image_path)
            VALUES (?, ?, ?)
        ''', (sprite_id, name, image_path))

        # 插入属性关联
        for attr_name in attributes:
            if attr_name in attr_map:
                cursor.execute('''
                    INSERT OR IGNORE INTO sprite_attribute (sprite_id, attribute_id)
                    VALUES (?, ?)
                ''', (sprite_id, attr_map[attr_name]))

    conn.commit()
    conn.close()


def main():
    # 配置路径
    project_root = Path(__file__).parent.parent
    html_path = project_root / 'reference' / '精灵' / '精灵图鉴 _ 洛克王国_ 世界.html'
    files_dir = project_root / 'reference' / '精灵' / '精灵图鉴 _ 洛克王国_ 世界_files'
    db_path = project_root / 'roko_monitor.db'
    target_img_dir = project_root / 'data' / 'images' / 'sprites'

    print(f"项目根目录: {project_root}")
    print(f"HTML 文件: {html_path}")
    print(f"附件目录: {files_dir}")
    print(f"数据库: {db_path}")
    print(f"目标图片目录: {target_img_dir}")
    print()

    # 检查文件是否存在
    if not html_path.exists():
        print(f"错误: HTML 文件不存在: {html_path}")
        return

    if not files_dir.exists():
        print(f"错误: 附件目录不存在: {files_dir}")
        return

    # 初始化数据库
    print("初始化数据库...")
    init_database(str(db_path))

    # 提取精灵数据
    print("提取精灵数据...")
    sprites = extract_sprites_from_html(str(html_path), str(files_dir))
    print(f"找到 {len(sprites)} 个精灵")

    # 收集所有属性
    all_attributes = set()
    for sprite in sprites:
        all_attributes.update(sprite['attributes'])

    print(f"找到 {len(all_attributes)} 个属性: {sorted(all_attributes)}")

    # 插入属性
    print("插入属性数据...")
    attr_map = insert_attributes(str(db_path), sorted(all_attributes))

    # 插入精灵数据
    print("插入精灵数据...")
    insert_sprites(str(db_path), sprites, attr_map, str(files_dir), str(target_img_dir))

    print("完成!")


if __name__ == '__main__':
    main()
