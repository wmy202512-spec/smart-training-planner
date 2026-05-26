"""
从 Excel 导入训练计划数据到 SQLite
"""
import sqlite3
import os
import re
import openpyxl

EXCEL_PATH = '/Users/wumengying/Desktop/私人项目/运动训练系统/2026年5月7日 -- v1.0 -- 跳绳训练app/跳绳训练计划.xlsx'
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'training.db')

def parse_type(type_str):
    """解析类型字段，如 'A（耐力+开合跳）' -> ('A', '耐力+开合跳')"""
    match = re.match(r'([A-D])（(.+?)）', type_str)
    if match:
        return match.group(1), match.group(2)
    return type_str[0], type_str

def extract_jump_target(outdoor_content):
    """从楼下部分提取连续跳目标数"""
    match = re.search(r'目标[>＞](\d+)', outdoor_content)
    if match:
        return int(match.group(1))
    return None

def import_data():
    wb = openpyxl.load_workbook(EXCEL_PATH)
    ws = wb.active
    
    db = sqlite3.connect(DB_PATH)
    db.execute('DELETE FROM training_plan')  # 清空重导
    
    for row in ws.iter_rows(min_row=2, max_row=17, values_only=True):
        day_number, type_raw, outdoor, indoor = row
        day_number = int(day_number)
        type_code, type_name = parse_type(type_raw)
        jump_target = extract_jump_target(outdoor or '')
        
        db.execute('''
            INSERT INTO training_plan (day_number, type, type_name, outdoor_content, indoor_content, jump_target)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (day_number, type_code, type_name, outdoor, indoor, jump_target))
    
    db.commit()
    count = db.execute('SELECT COUNT(*) FROM training_plan').fetchone()[0]
    db.close()
    print(f'✅ 成功导入 {count} 天训练计划')

if __name__ == '__main__':
    # 先确保表存在
    db = sqlite3.connect(DB_PATH)
    db.executescript('''
        CREATE TABLE IF NOT EXISTS training_plan (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            day_number INTEGER UNIQUE NOT NULL,
            type TEXT NOT NULL,
            type_name TEXT NOT NULL,
            outdoor_content TEXT NOT NULL,
            indoor_content TEXT NOT NULL,
            jump_target INTEGER
        );
        CREATE TABLE IF NOT EXISTS check_in (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plan_id INTEGER NOT NULL,
            day_number INTEGER NOT NULL,
            completed_date TEXT NOT NULL,
            actual_jump_count INTEGER,
            created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
            FOREIGN KEY (plan_id) REFERENCES training_plan(id)
        );
        CREATE TABLE IF NOT EXISTS auth_token (
            token TEXT PRIMARY KEY,
            created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
        );
    ''')
    db.commit()
    db.close()
    import_data()