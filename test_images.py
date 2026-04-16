"""测试图片显示功能"""
from src.database.connection import init_db, get_session
from src.database.queries import get_all_sprites, get_sprite_detail
from src.ui.image_utils import load_icon

init_db()
session = get_session()

# 查看所有精灵
sprites = get_all_sprites(session)
print(f"数据库中有 {len(sprites)} 只精灵:")
for s in sprites:
    print(f"  {s.id}: {s.name} - {s.image_path}")

# 获取第一个精灵来测试
if sprites:
    info = get_sprite_detail(session, sprites[0].id)
    print(f"\n测试精灵: {info.name}, icon_path: {info.image_path}")
    print(f"Skills with icons:")
    for s in info.skills:
        print(f"  {s.name}: {s.image_path}")

    # 测试图片加载
    if info.image_path:
        icon = load_icon(info.image_path)
        print(f"\nSprite icon loaded: {icon is not None}")

    for s in info.skills:
        if s.image_path:
            icon = load_icon(s.image_path)
            print(f"  Skill '{s.name}' icon loaded: {icon is not None}")

session.close()
print("\n图片显示功能测试完成!")
