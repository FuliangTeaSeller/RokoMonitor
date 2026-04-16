"""
从JSON文件批量导入精灵-技能绑定数据

JSON格式说明:
{
    "version": "1.0",
    "description": "精灵-技能绑定数据导入文件（可选）",
    "bindings": [
        {
            "sprite_name": "火花",
            "skill_names": ["火花喷射", "火焰冲撞", "灼烧"]
        },
        {
            "sprite_name": "水蓝蓝",
            "skill_names": ["水枪", "水之波动"]
        }
    ]
}

特性:
- 使用精灵名称和技能名称，便于用户编辑
- 自动查找对应ID并建立绑定关系
- 支持增量导入，不删除已有技能
- 幂等性：已存在的绑定自动跳过
"""

import json
import sys
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.database.connection import get_session
from src.database.models import Sprite, Skill, SpriteSkill


def load_json_file(json_path: Path) -> dict:
    """加载并验证JSON文件

    参数:
        json_path: JSON文件路径

    返回:
        解析后的字典

    异常:
        FileNotFoundError: 文件不存在
        json.JSONDecodeError: JSON格式错误
        ValueError: 数据格式不符合要求
    """
    if not json_path.exists():
        raise FileNotFoundError(f"JSON文件不存在: {json_path}")

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 验证数据结构
    if "bindings" not in data:
        raise ValueError("JSON缺少必需的 'bindings' 字段")

    if not isinstance(data["bindings"], list):
        raise ValueError("'bindings' 必须是数组")

    for i, binding in enumerate(data["bindings"]):
        if "sprite_name" not in binding:
            raise ValueError(f"绑定项 {i} 缺少 'sprite_name' 字段")
        if "skill_names" not in binding:
            raise ValueError(f"绑定项 {i} 缺少 'skill_names' 字段")
        if not isinstance(binding["skill_names"], list):
            raise ValueError(f"绑定项 {i} 的 'skill_names' 必须是数组")

    return data


def get_sprite_by_name(session: Session, name: str) -> Sprite | None:
    """按名称查询精灵"""
    stmt = select(Sprite).where(Sprite.name == name)
    return session.execute(stmt).scalar_one_or_none()


def get_skill_by_name(session: Session, name: str) -> Skill | None:
    """按名称查询技能"""
    stmt = select(Skill).where(Skill.name == name)
    return session.execute(stmt).scalar_one_or_none()


def get_existing_skill_ids(session: Session, sprite_id: int) -> set[int]:
    """获取精灵已绑定的技能ID集合"""
    stmt = select(SpriteSkill.skill_id).where(SpriteSkill.sprite_id == sprite_id)
    return set(session.execute(stmt).scalars().all())


def import_bindings(session: Session, data: dict, verbose: bool = True) -> dict:
    """导入精灵-技能绑定数据

    参数:
        session: 数据库会话
        data: 解析后的JSON数据
        verbose: 是否输出详细信息

    返回:
        导入统计信息字典:
        {
            "total_bindings": 总绑定数,
            "success_count": 成功数,
            "skipped_count": 跳过数（已存在）,
            "sprite_not_found": 未找到的精灵列表,
            "skill_not_found": 未找到的技能列表（按精灵分组）,
            "errors": 错误列表
        }
    """
    stats = {
        "total_bindings": 0,
        "success_count": 0,
        "skipped_count": 0,
        "sprite_not_found": [],
        "skill_not_found": {},
        "errors": []
    }

    bindings = data.get("bindings", [])

    for binding in bindings:
        sprite_name = binding["sprite_name"]
        skill_names = binding["skill_names"]

        # 查找精灵
        sprite = get_sprite_by_name(session, sprite_name)
        if sprite is None:
            stats["sprite_not_found"].append(sprite_name)
            if verbose:
                print(f"  [警告] 精灵不存在: {sprite_name}")
            continue

        # 获取已有技能
        existing_ids = get_existing_skill_ids(session, sprite.id)

        # 处理每个技能
        for skill_name in skill_names:
            stats["total_bindings"] += 1

            skill = get_skill_by_name(session, skill_name)
            if skill is None:
                if sprite_name not in stats["skill_not_found"]:
                    stats["skill_not_found"][sprite_name] = []
                stats["skill_not_found"][sprite_name].append(skill_name)
                if verbose:
                    print(f"  [警告] 技能不存在: {skill_name} (精灵: {sprite_name})")
                continue

            # 检查是否已存在
            if skill.id in existing_ids:
                stats["skipped_count"] += 1
                if verbose:
                    print(f"  [跳过] {sprite_name} 已绑定技能: {skill_name}")
                continue

            # 添加绑定
            try:
                session.add(SpriteSkill(sprite_id=sprite.id, skill_id=skill.id))
                stats["success_count"] += 1
                if verbose:
                    print(f"  [成功] {sprite_name} + {skill_name}")
            except Exception as e:
                stats["errors"].append(f"{sprite_name} + {skill_name}: {str(e)}")
                if verbose:
                    print(f"  [错误] {sprite_name} + {skill_name}: {e}")

    # 提交事务
    if stats["success_count"] > 0:
        try:
            session.commit()
        except Exception as e:
            session.rollback()
            stats["errors"].append(f"提交失败: {e}")
            stats["success_count"] = 0

    return stats


def print_summary(stats: dict):
    """打印导入统计摘要"""
    print("\n" + "=" * 50)
    print("导入统计摘要")
    print("=" * 50)
    print(f"总绑定数: {stats['total_bindings']}")
    print(f"成功添加: {stats['success_count']}")
    print(f"跳过(已存在): {stats['skipped_count']}")

    if stats["sprite_not_found"]:
        print(f"\n未找到的精灵 ({len(stats['sprite_not_found'])}个):")
        for name in stats["sprite_not_found"]:
            print(f"  - {name}")

    if stats["skill_not_found"]:
        total = sum(len(v) for v in stats["skill_not_found"].values())
        print(f"\n未找到的技能 ({total}个):")
        for sprite_name, skills in stats["skill_not_found"].items():
            print(f"  {sprite_name}:")
            for skill in skills:
                print(f"    - {skill}")

    if stats["errors"]:
        print(f"\n错误 ({len(stats['errors'])}个):")
        for error in stats["errors"]:
            print(f"  - {error}")


def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(
        description="从JSON文件批量导入精灵-技能绑定数据",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
JSON格式示例:
{
    "version": "1.0",
    "bindings": [
        {
            "sprite_name": "火花",
            "skill_names": ["火花喷射", "火焰冲撞"]
        }
    ]
}
        """
    )
    parser.add_argument(
        "json_file",
        type=str,
        help="JSON文件路径"
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="静默模式，只输出摘要"
    )

    args = parser.parse_args()
    json_path = Path(args.json_file)

    print(f"正在加载JSON文件: {json_path}")

    try:
        # 加载JSON
        data = load_json_file(json_path)
        print(f"发现 {len(data['bindings'])} 个精灵绑定数据")

        # 导入数据
        print("\n开始导入...")
        session = get_session()
        stats = import_bindings(session, data, verbose=not args.quiet)

        # 打印摘要
        print_summary(stats)

    except FileNotFoundError as e:
        print(f"错误: {e}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"JSON解析错误: {e}")
        sys.exit(1)
    except ValueError as e:
        print(f"数据格式错误: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"未知错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
