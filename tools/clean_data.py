import sqlite3

conn = sqlite3.connect('data/roko_monitor.db')
cursor = conn.cursor()

print('=== Current data ===')
for table in ['attribute', 'skill', 'sprite', 'sprite_attribute', 'sprite_skill']:
    cursor.execute(f'SELECT COUNT(*) FROM {table}')
    count = cursor.fetchone()[0]
    print(f'{table}: {count} rows')

print('\n=== Clearing data ===')
# 按依赖关系倒序删除：先删除关联表，再删除主表
for table in ['sprite_skill', 'sprite_attribute', 'sprite', 'skill', 'attribute']:
    cursor.execute(f'DELETE FROM {table}')
    affected = cursor.rowcount
    print(f'{table}: {affected} rows deleted')

conn.commit()

print('\n=== Data after cleanup ===')
for table in ['attribute', 'skill', 'sprite', 'sprite_attribute', 'sprite_skill']:
    cursor.execute(f'SELECT COUNT(*) FROM {table}')
    count = cursor.fetchone()[0]
    print(f'{table}: {count} rows')

conn.close()
print('\nCleanup complete!')
