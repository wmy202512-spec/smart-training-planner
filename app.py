from flask import Flask, jsonify, request, send_from_directory
import sqlite3
import hashlib
import secrets
import os
import json
import urllib.request
import uuid
from datetime import datetime, timedelta
from functools import wraps
import threading
import re
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(32))

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'training.db')

# ===== LLM =====
LLM_BASE = os.getenv('LLM_BASE', 'http://113.45.39.247:3001/v1/chat/completions')
LLM_KEY = os.getenv('LLM_KEY', '')
LLM_MODEL = os.getenv('LLM_MODEL', 'deepseek/deepseek-v4-flash')

ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'admin123')

# ============ DB ============

def get_db():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA foreign_keys=ON")
    return db

def init_db():
    db = get_db()
    db.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        nickname TEXT DEFAULT '',
        is_admin INTEGER DEFAULT 0,
        created_at TEXT DEFAULT (datetime('now','localtime'))
    )''')
    db.execute('''CREATE TABLE IF NOT EXISTS plans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        sport_type TEXT NOT NULL,
        total_days INTEGER NOT NULL,
        description TEXT DEFAULT '',
        created_at TEXT DEFAULT (datetime('now','localtime')),
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')
    db.execute('''CREATE TABLE IF NOT EXISTS plan_days (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        plan_id INTEGER NOT NULL,
        day_number INTEGER NOT NULL,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        day_type TEXT DEFAULT '',
        FOREIGN KEY (plan_id) REFERENCES plans(id) ON DELETE CASCADE
    )''')
    db.execute('''CREATE TABLE IF NOT EXISTS checkins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        plan_id INTEGER NOT NULL,
        day_number INTEGER NOT NULL,
        completed_date TEXT NOT NULL,
        note TEXT DEFAULT '',
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (plan_id) REFERENCES plans(id) ON DELETE CASCADE
    )''')
    db.execute('''CREATE TABLE IF NOT EXISTS conversations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        session_id TEXT NOT NULL,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at TEXT DEFAULT (datetime('now','localtime')),
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')
    db.execute('''CREATE TABLE IF NOT EXISTS templates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        sport_type TEXT NOT NULL,
        total_days INTEGER NOT NULL,
        description TEXT DEFAULT '',
        days_json TEXT NOT NULL
    )''')
    db.execute('''CREATE TABLE IF NOT EXISTS pending_plans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        session_id TEXT NOT NULL,
        message_id INTEGER NOT NULL,
        full_text TEXT NOT NULL,
        plan_json TEXT DEFAULT NULL,
        status TEXT DEFAULT 'processing',
        created_at TEXT DEFAULT (datetime('now','localtime')),
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')
    admin_hash = hashlib.sha256("admin123".encode()).hexdigest()
    db.execute('INSERT OR IGNORE INTO users (username, password_hash, nickname, is_admin) VALUES (?, ?, ?, 1)',
               (ADMIN_USERNAME, admin_hash, '管理员'))
    db.commit()
    _init_templates(db)
    db.close()

def _init_templates(db):
    existing = db.execute("SELECT COUNT(*) as c FROM templates").fetchone()['c']
    if existing > 0:
        return
    templates = [
        {
            "title": "16天跳绳燃脂计划",
            "sport_type": "跳绳",
            "total_days": 16,
            "description": "适合初学者的渐进式跳绳训练，从基础跳到花式组合",
            "days": [
                {"day": 1, "type": "A", "title": "基础入门", "content": "【热身】开合跳30个+手腕脚踝活动2分钟\n【跳绳】基础跳 30秒x6组（组间休息30秒）\n【核心】平板支撑30秒x2\n【拉伸】小腿+大腿拉伸各30秒"},
                {"day": 2, "type": "B", "title": "节奏训练", "content": "【热身】高抬腿20个+动态拉伸2分钟\n【跳绳】交替跳 30秒x6组（组间休息30秒）\n【核心】卷腹15个x2组\n【拉伸】全身拉伸3分钟"},
                {"day": 3, "type": "C", "title": "耐力提升", "content": "【热身】开合跳30个+弓步走8个\n【跳绳】基础跳 45秒x5组（组间休息30秒）\n【核心】俄罗斯转体20个x2\n【拉伸】小腿+髋部拉伸"},
                {"day": 4, "type": "D", "title": "综合训练", "content": "【热身】动态拉伸3分钟\n【跳绳】混合跳（基础+交替）40秒x6组\n【核心】平板支撑40秒+侧平板20秒x2\n【拉伸】全身放松5分钟"},
                {"day": 5, "type": "A", "title": "速度初探", "content": "【热身】开合跳40个+手腕活动\n【跳绳】快速跳 20秒x8组（组间休息40秒）\n【核心】卷腹20个x2\n【拉伸】小腿重点拉伸"},
                {"day": 6, "type": "B", "title": "间歇挑战", "content": "【热身】高抬腿30个+动态拉伸\n【跳绳】30秒快+30秒慢 x5轮\n【核心】平板支撑45秒x2\n【拉伸】全身拉伸3分钟"},
                {"day": 7, "type": "C", "title": "耐力突破", "content": "【热身】弓步走10个+开合跳30个\n【跳绳】基础跳 60秒x4组（组间休息30秒）\n【核心】俄罗斯转体25个x2\n【拉伸】深度拉伸5分钟"},
                {"day": 8, "type": "D", "title": "花式入门", "content": "【热身】动态拉伸3分钟\n【跳绳】交叉跳练习 30秒x6组\n【核心】登山者20个x2\n【拉伸】肩部+小腿拉伸"},
                {"day": 9, "type": "A", "title": "强度提升", "content": "【热身】开合跳50个+手腕活动\n【跳绳】快速跳 30秒x8组（组间休息30秒）\n【核心】平板支撑50秒x2\n【拉伸】全身拉伸"},
                {"day": 10, "type": "B", "title": "组合训练", "content": "【热身】高抬腿40个+动态拉伸\n【跳绳】基础30秒+交替30秒+快速20秒 x4轮\n【核心】卷腹25个+俄罗斯转体20个\n【拉伸】重点拉伸5分钟"},
                {"day": 11, "type": "C", "title": "长时挑战", "content": "【热身】弓步走12个+开合跳40个\n【跳绳】基础跳 90秒x3组（组间休息45秒）\n【核心】平板支撑60秒\n【拉伸】深度拉伸5分钟"},
                {"day": 12, "type": "D", "title": "花式进阶", "content": "【热身】动态拉伸3分钟\n【跳绳】交叉跳+双摇尝试 30秒x8组\n【核心】登山者25个x2+侧平板30秒x2\n【拉伸】全身放松"},
                {"day": 13, "type": "A", "title": "速度突破", "content": "【热身】开合跳50个+快速踏步\n【跳绳】最快速度 20秒x10组（组间休息40秒）\n【核心】卷腹30个x2\n【拉伸】小腿+跟腱重点"},
                {"day": 14, "type": "B", "title": "HIIT跳绳", "content": "【热身】高抬腿50个+动态拉伸\n【跳绳】40秒全力+20秒休息 x8轮\n【核心】平板支撑60秒+俄罗斯转体30个\n【拉伸】全身拉伸5分钟"},
                {"day": 15, "type": "C", "title": "耐力巅峰", "content": "【热身】弓步走+开合跳各40个\n【跳绳】基础跳 2分钟x3组（组间休息60秒）\n【核心】综合核心训练5分钟\n【拉伸】深度放松"},
                {"day": 16, "type": "D", "title": "毕业挑战", "content": "【热身】全面动态热身5分钟\n【跳绳】自由组合 3分钟x3组（展示所有技巧）\n【核心】平板支撑90秒\n【拉伸】庆祝拉伸10分钟 \U0001f389"}
            ]
        },
        {
            "title": "14天居家力量训练",
            "sport_type": "力量训练",
            "total_days": 14,
            "description": "无器械居家力量训练，覆盖全身各肌群，适合零基础",
            "days": [
                {"day": 1, "type": "上肢", "title": "俯卧撑入门", "content": "【热身】手臂画圈30秒+开合跳20个\n【训练】跪姿俯卧撑 8个x3组\n钻石俯卧撑（跪姿）6个x2组\n【放松】胸部+肩部拉伸"},
                {"day": 2, "type": "下肢", "title": "深蹲基础", "content": "【热身】高抬腿20个+踝关节活动\n【训练】标准深蹲 12个x3组\n弓步蹲 8个x2组（每侧）\n【放松】大腿+臀部拉伸"},
                {"day": 3, "type": "核心", "title": "核心激活", "content": "【热身】猫牛式8个+骨盆前后倾\n【训练】平板支撑 30秒x3\n卷腹 15个x3组\n侧平板 20秒x2（每侧）\n【放松】婴儿式放松"},
                {"day": 4, "type": "休息", "title": "主动恢复", "content": "【活动】散步20分钟或轻度瑜伽\n【拉伸】全身各部位拉伸，每个动作保持30秒\n【提示】充分休息，补充蛋白质"},
                {"day": 5, "type": "上肢", "title": "推拉结合", "content": "【热身】手臂动态拉伸2分钟\n【训练】标准俯卧撑 10个x3组\n反向划船（桌边）8个x3组\n肩部推举（水瓶）12个x3组\n【放松】上肢拉伸"},
                {"day": 6, "type": "下肢", "title": "单腿力量", "content": "【热身】动态弓步8个+踝关节活动\n【训练】保加利亚分腿蹲 8个x3组（每侧）\n单腿臀桥 10个x3组（每侧）\n小腿提踵 15个x3组\n【放松】下肢深度拉伸"},
                {"day": 7, "type": "核心", "title": "核心进阶", "content": "【热身】猫牛式+鸟狗式各8个\n【训练】平板支撑 45秒x3\n俄罗斯转体 20个x3组\n登山者 15个x3组\n死虫 10个x2组\n【放松】脊柱放松"},
                {"day": 8, "type": "全身", "title": "全身循环", "content": "【热身】开合跳30个+动态拉伸\n【训练】循环x3轮：\n俯卧撑10个-深蹲12个-平板30秒-弓步蹲8个（每侧）\n轮间休息60秒\n【放松】全身拉伸5分钟"},
                {"day": 9, "type": "上肢", "title": "上肢耐力", "content": "【热身】手臂画圈+俯卧撑热身5个\n【训练】宽距俯卧撑 10个x3组\n窄距俯卧撑 8个x3组\n俯卧撑保持（底部）15秒x3\n【放松】胸肩三头拉伸"},
                {"day": 10, "type": "下肢", "title": "爆发力", "content": "【热身】高抬腿30个+动态弓步\n【训练】跳跃深蹲 8个x3组\n交替跳弓步 6个x3组（每侧）\n臀桥 15个x3组\n【放松】下肢+髋部拉伸"},
                {"day": 11, "type": "核心", "title": "核心挑战", "content": "【热身】猫牛式+骨盆活动\n【训练】平板支撑 60秒x2\nV字卷腹 12个x3组\n侧平板提髋 10个x2（每侧）\n超人式 12个x3组\n【放松】脊柱扭转放松"},
                {"day": 12, "type": "休息", "title": "恢复日", "content": "【活动】轻度有氧20分钟（散步/骑车）\n【拉伸】泡沫轴放松或深度拉伸15分钟\n【营养】注意补充水分和蛋白质"},
                {"day": 13, "type": "全身", "title": "全身HIIT", "content": "【热身】开合跳40个+动态拉伸3分钟\n【训练】40秒训练+20秒休息 x8轮：\n波比跳-深蹲-俯卧撑-登山者-弓步跳-平板-高抬腿-卷腹\n【放松】全身拉伸5分钟"},
                {"day": 14, "type": "全身", "title": "毕业测试", "content": "【热身】全面热身5分钟\n【测试】计时完成：\n俯卧撑x最多-深蹲x20-平板支撑x最久-弓步蹲x10每侧-卷腹x20\n记录成绩，对比第1天！\n【庆祝】全身放松拉伸10分钟 \U0001f389"}
            ]
        },
        {
            "title": "7天晨跑入门计划",
            "sport_type": "跑步",
            "total_days": 7,
            "description": "零基础跑步入门，从走跑结合到连续慢跑",
            "days": [
                {"day": 1, "type": "基础", "title": "走跑结合", "content": "【热身】快走5分钟\n【训练】慢跑2分钟+快走3分钟 x4组（共20分钟）\n【放松】慢走3分钟+小腿拉伸"},
                {"day": 2, "type": "基础", "title": "延长跑段", "content": "【热身】快走5分钟+动态拉伸\n【训练】慢跑3分钟+快走2分钟 x4组（共20分钟）\n【放松】慢走3分钟+腿部拉伸"},
                {"day": 3, "type": "休息", "title": "主动恢复", "content": "【活动】散步30分钟或轻度拉伸\n【重点】关注膝盖和脚踝感受\n【提示】补充水分，早睡"},
                {"day": 4, "type": "进阶", "title": "连续慢跑", "content": "【热身】快走5分钟\n【训练】连续慢跑10分钟+快走5分钟+慢跑5分钟\n【放松】慢走+全腿拉伸5分钟"},
                {"day": 5, "type": "进阶", "title": "节奏感知", "content": "【热身】快走5分钟+动态拉伸\n【训练】慢跑12分钟（保持能说话的配速）+快走3分钟+慢跑5分钟\n【放松】慢走+髋部拉伸"},
                {"day": 6, "type": "休息", "title": "恢复调整", "content": "【活动】轻度瑜伽或散步20分钟\n【拉伸】重点放松小腿、髋屈肌\n【准备】明天是毕业跑，早点休息"},
                {"day": 7, "type": "挑战", "title": "毕业跑", "content": "【热身】快走5分钟+动态热身\n【挑战】连续慢跑20分钟（相信自己！）\n【放松】慢走5分钟+全身拉伸10分钟\n\U0001f389 恭喜完成！你已经是一个跑者了！"}
            ]
        }
    ]
    for t in templates:
        db.execute('INSERT INTO templates (title, sport_type, total_days, description, days_json) VALUES (?, ?, ?, ?, ?)',
                   (t['title'], t['sport_type'], t['total_days'], t['description'], json.dumps(t['days'], ensure_ascii=False)))
    db.commit()

# ============ Auth ============

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '').strip()
        if not token:
            return jsonify({'error': '未登录'}), 401
        
        db = get_db()
        try:
            # 【修复】查询 session 并验证是否过期
            session = db.execute('''
                SELECT s.user_id, u.username, u.nickname, u.is_admin 
                FROM sessions s
                JOIN users u ON s.user_id = u.id
                WHERE s.token = ? AND s.expires_at > datetime('now', 'localtime')
            ''', (token,)).fetchone()
            
            if not session:
                return jsonify({'error': 'Token无效或已过期'}), 401
            
            kwargs['user_id'] = session['user_id']
            kwargs['username'] = session['username']
            kwargs['is_admin'] = session['is_admin']
            kwargs['nickname'] = session['nickname']
            return f(*args, **kwargs)
        finally:
            db.close()
    
    return decorated

# ============ User API ============

@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    nickname = data.get('nickname', '').strip() or username
    if not username or not password:
        return jsonify({'error': '用户名和密码不能为空'}), 400
    if len(password) < 4:
        return jsonify({'error': '密码至少4位'}), 400
    db = get_db()
    try:
        existing = db.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone()
        if existing:
            return jsonify({'error': '用户名已存在'}), 400
        db.execute('INSERT INTO users (username, password_hash, nickname) VALUES (?, ?, ?)',
                   (username, hash_password(password), nickname))
        db.commit()
        user = db.execute('SELECT id, nickname, is_admin FROM users WHERE username = ?', (username,)).fetchone()
        
        # 【修复】生成UUID token并存入sessions表
        token = str(uuid.uuid4())
        expires_at = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S')
        db.execute('INSERT INTO sessions (token, user_id, expires_at) VALUES (?, ?, ?)',
                   (token, user['id'], expires_at))
        db.commit()
        
        return jsonify({'token': token, 'nickname': user['nickname'], 'is_admin': user['is_admin']})
    finally:
        db.close()

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    db = get_db()
    try:
        user = db.execute('SELECT id, password_hash, nickname, is_admin FROM users WHERE username = ?', (username,)).fetchone()
        if not user or user['password_hash'] != hash_password(password):
            return jsonify({'error': '用户名或密码错误'}), 401
        
        # 【修复】生成UUID token并存入sessions表
        token = str(uuid.uuid4())
        expires_at = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S')
        db.execute('INSERT INTO sessions (token, user_id, expires_at) VALUES (?, ?, ?)',
                   (token, user['id'], expires_at))
        db.commit()
        
        return jsonify({'token': token, 'nickname': user['nickname'], 'is_admin': user['is_admin']})
    finally:
        db.close()

@app.route('/api/change-password', methods=['POST'])
@require_auth
def change_password(**kwargs):
    user_id = kwargs['user_id']
    data = request.get_json()
    old_password = data.get('old_password', '')
    new_password = data.get('new_password', '')
    if len(new_password) < 4:
        return jsonify({'error': '新密码至少4位'}), 400
    db = get_db()
    user = db.execute('SELECT password_hash FROM users WHERE id = ?', (user_id,)).fetchone()
    if user['password_hash'] != hash_password(old_password):
        db.close()
        return jsonify({'error': '原密码错误'}), 400
    db.execute('UPDATE users SET password_hash = ? WHERE id = ?', (hash_password(new_password), user_id))
    db.commit()
    db.close()
    return jsonify({'success': True})

@app.route('/api/admin/reset-password', methods=['POST'])
@require_auth
def admin_reset_password(**kwargs):
    if not kwargs['is_admin']:
        return jsonify({'error': '无权限'}), 403
    data = request.get_json()
    target_username = data.get('username', '').strip()
    new_password = data.get('new_password', '123456')
    db = get_db()
    user = db.execute('SELECT id FROM users WHERE username = ?', (target_username,)).fetchone()
    if not user:
        db.close()
        return jsonify({'error': '用户不存在'}), 404
    db.execute('UPDATE users SET password_hash = ? WHERE id = ?', (hash_password(new_password), user['id']))
    db.commit()
    db.close()
    return jsonify({'success': True, 'message': f'已重置 {target_username} 的密码为 {new_password}'})

@app.route('/api/admin/users', methods=['GET'])
@require_auth
def admin_list_users(**kwargs):
    if not kwargs['is_admin']:
        return jsonify({'error': '无权限'}), 403
    db = get_db()
    users = db.execute('SELECT id, username, nickname, is_admin, created_at FROM users ORDER BY id').fetchall()
    db.close()
    return jsonify([dict(u) for u in users])

@app.route('/api/user/info', methods=['GET'])
@require_auth
def get_user_info(**kwargs):
    return jsonify({
        'user_id': kwargs['user_id'],
        'username': kwargs['username'],
        'nickname': kwargs['nickname'],
        'is_admin': kwargs['is_admin']
    })

@app.route('/api/logout', methods=['POST'])
@require_auth
def logout(**kwargs):
    token = request.headers.get('Authorization', '').replace('Bearer ', '').strip()
    db = get_db()
    try:
        db.execute('DELETE FROM sessions WHERE token = ?', (token,))
        db.commit()
        return jsonify({'success': True})
    finally:
        db.close()

# ============ Plan API ============

@app.route('/api/plans', methods=['GET'])
@require_auth
def get_plans(**kwargs):
    user_id = kwargs['user_id']
    db = get_db()
    plans = db.execute('''SELECT p.*,
        (SELECT COUNT(*) FROM checkins WHERE plan_id = p.id AND user_id = ?) as completed_days
        FROM plans p WHERE p.user_id = ? ORDER BY p.created_at DESC''', (user_id, user_id)).fetchall()
    db.close()
    return jsonify({'plans': [dict(p) for p in plans]})

@app.route('/api/plans/<int:plan_id>', methods=['GET'])
@require_auth
def get_plan_detail(plan_id, **kwargs):
    user_id = kwargs['user_id']
    db = get_db()
    plan = db.execute('SELECT * FROM plans WHERE id = ? AND user_id = ?', (plan_id, user_id)).fetchone()
    if not plan:
        db.close()
        return jsonify({'error': '计划不存在'}), 404
    days = db.execute('SELECT * FROM plan_days WHERE plan_id = ? ORDER BY day_number', (plan_id,)).fetchall()
    checkins = db.execute('SELECT day_number, completed_date, note FROM checkins WHERE plan_id = ? AND user_id = ? ORDER BY day_number',
                          (plan_id, user_id)).fetchall()
    db.close()
    return jsonify({
        'plan': dict(plan),
        'days': [dict(d) for d in days],
        'checkins': [dict(c) for c in checkins]
    })

@app.route('/api/plans/<int:plan_id>', methods=['DELETE'])
@require_auth
def delete_plan(plan_id, **kwargs):
    user_id = kwargs['user_id']
    db = get_db()
    plan = db.execute('SELECT id FROM plans WHERE id = ? AND user_id = ?', (plan_id, user_id)).fetchone()
    if not plan:
        db.close()
        return jsonify({'error': '计划不存在'}), 404
    db.execute('DELETE FROM checkins WHERE plan_id = ? AND user_id = ?', (plan_id, user_id))
    db.execute('DELETE FROM plan_days WHERE plan_id = ?', (plan_id,))
    db.execute('DELETE FROM plans WHERE id = ?', (plan_id,))
    db.commit()
    db.close()
    return jsonify({'success': True})

@app.route('/api/templates', methods=['GET'])
def get_templates():
    db = get_db()
    templates = db.execute('SELECT id, title, sport_type, total_days, description, days_json FROM templates').fetchall()
    db.close()
    return jsonify({'templates': [dict(t) for t in templates]})

@app.route('/api/plans/from-template', methods=['POST'])
@require_auth
def create_plan_from_template(**kwargs):
    user_id = kwargs['user_id']
    data = request.get_json()
    template_id = data.get('template_id')
    db = get_db()
    count = db.execute('SELECT COUNT(*) as c FROM plans WHERE user_id = ?', (user_id,)).fetchone()['c']
    if count >= 3:
        db.close()
        return jsonify({'error': '最多只能有3个运动计划，请先删除现有计划'}), 400
    template = db.execute('SELECT * FROM templates WHERE id = ?', (template_id,)).fetchone()
    if not template:
        db.close()
        return jsonify({'error': '模板不存在'}), 404
    cursor = db.execute('INSERT INTO plans (user_id, title, sport_type, total_days, description) VALUES (?, ?, ?, ?, ?)',
               (user_id, template['title'], template['sport_type'], template['total_days'], template['description']))
    plan_id = cursor.lastrowid
    days = json.loads(template['days_json'])
    for d in days:
        db.execute('INSERT INTO plan_days (plan_id, day_number, title, content, day_type) VALUES (?, ?, ?, ?, ?)',
                   (plan_id, d['day'], d['title'], d['content'], d.get('type', '')))
    db.commit()
    db.close()
    return jsonify({'success': True, 'plan_id': plan_id})

@app.route('/api/plans/from_chat', methods=['POST'])
@require_auth
def create_plan_from_chat(**kwargs):
    user_id = kwargs['user_id']
    data = request.get_json()
    plan_data = data.get('plan')
    
    if not plan_data:
        return jsonify({'error': '计划数据不能为空'}), 400
    
    # 验证必需字段
    required_fields = ['title', 'sport_type', 'total_days', 'days']
    for field in required_fields:
        if field not in plan_data:
            return jsonify({'error': f'缺少必需字段: {field}'}), 400
    
    db = get_db()
    
    # 检查计划数量限制
    count = db.execute('SELECT COUNT(*) as c FROM plans WHERE user_id = ?', (user_id,)).fetchone()['c']
    if count >= 3:
        db.close()
        return jsonify({'error': '最多只能有3个运动计划，请先删除现有计划'}), 400
    
    # 创建计划
    try:
        cursor = db.execute(
            'INSERT INTO plans (user_id, title, sport_type, total_days, description, full_description) VALUES (?, ?, ?, ?, ?, ?)',
            (user_id, plan_data['title'], plan_data['sport_type'], 
             plan_data['total_days'], plan_data.get('description', ''),
             plan_data.get('full_description', ''))
        )
        plan_id = cursor.lastrowid
        
        # 添加每日训练内容
        for day_data in plan_data['days']:
            db.execute(
                'INSERT INTO plan_days (plan_id, day_number, title, content, day_type, full_content) VALUES (?, ?, ?, ?, ?, ?)',
                (plan_id, day_data.get('day', day_data.get('day_number', 0)), 
                 day_data.get('title', ''), day_data.get('content', ''), 
                 day_data.get('type', day_data.get('day_type', '')),
                 day_data.get('full_content', ''))
            )
        
        db.commit()
        db.close()
        return jsonify({'success': True, 'plan_id': plan_id})
    except Exception as e:
        db.close()
        return jsonify({'error': f'保存计划失败: {str(e)}'}), 500

# ============ Checkin API ============

@app.route('/api/checkin', methods=['POST'])
@require_auth
def checkin(**kwargs):
    user_id = kwargs['user_id']
    data = request.get_json()
    plan_id = data.get('plan_id')
    day_number = data.get('day_number')
    note = data.get('note', '')
    completed_date = data.get('completed_date', datetime.now().strftime('%Y-%m-%d'))
    db = get_db()
    plan = db.execute('SELECT id, total_days FROM plans WHERE id = ? AND user_id = ?', (plan_id, user_id)).fetchone()
    if not plan:
        db.close()
        return jsonify({'error': '计划不存在'}), 404
    existing = db.execute('SELECT id FROM checkins WHERE plan_id = ? AND user_id = ? AND day_number = ?',
                          (plan_id, user_id, day_number)).fetchone()
    if existing:
        db.close()
        return jsonify({'error': '该天已打卡'}), 400
    db.execute('INSERT INTO checkins (user_id, plan_id, day_number, completed_date, note) VALUES (?, ?, ?, ?, ?)',
               (user_id, plan_id, day_number, completed_date, note))
    db.commit()
    db.close()
    return jsonify({'success': True})

@app.route('/api/checkin/undo', methods=['POST'])
@require_auth
def undo_checkin(**kwargs):
    user_id = kwargs['user_id']
    data = request.get_json()
    plan_id = data.get('plan_id')
    db = get_db()
    latest = db.execute('SELECT id, day_number FROM checkins WHERE plan_id = ? AND user_id = ? ORDER BY day_number DESC LIMIT 1',
                        (plan_id, user_id)).fetchone()
    if not latest:
        db.close()
        return jsonify({'error': '没有打卡记录'}), 400
    db.execute('DELETE FROM checkins WHERE id = ?', (latest['id'],))
    db.commit()
    db.close()
    return jsonify({'success': True, 'undone_day': latest['day_number']})

# ============ 异步生成计划JSON ============

def generate_plan_json_async(user_id, session_id, message_id, full_text):
    """后台异步生成计划的JSON数据"""
    try:
        # 构建第二次AI调用的prompt
        extract_prompt = f"""请从以下训练计划文本中提取关键信息，生成JSON格式的数据。

训练计划文本：
{full_text}

请严格按照以下JSON格式输出（只输出JSON，不要其他内容）：
{{
  "title": "计划标题",
  "sport_type": "运动类型（如：跑步、跳绳、健身、瑜伽等）",
  "total_days": 天数,
  "description": "计划简介（一句话）",
  "days": [
    {{"day": 1, "type": "训练类型", "title": "当天标题", "content": "简化的训练内容（一句话概括）", "full_content": "完整的训练内容描述"}},
    {{"day": 2, "type": "训练类型", "title": "当天标题", "content": "简化的训练内容（一句话概括）", "full_content": "完整的训练内容描述"}}
  ]
}}

**重要要求**：
1. **content字段**：简化的训练内容，一句话概括（如："热身5分钟 + 跑走结合18分钟 + 拉伸5分钟"）
2. **full_content字段**：完整提取原文中每一天的训练内容，包括：
   - 热身部分（如：快走3分钟 + 原地高抬腿30秒 + 开合跳30次）
   - 主训练部分（如：跑1分钟 + 走2分钟 × 重复6组，总时长18分钟）
   - 放松部分（如：慢走2分钟 + 站立小腿拉伸每侧30秒）
3. **不要简化或省略full_content中的任何细节**，保持原文的完整性
4. **保留所有emoji和格式符号**（如：🔥、💪、🧘、\n换行符）
5. 必须包含所有天数的数据
6. 只输出JSON，不要任何其他文字

**示例**：
如果原文是：
"**第1天（周一）**
🔥 热身：快走3分钟 + 原地高抬腿30秒 + 开合跳30次 + 踝关节绕环左右各10次
💪 主训练：跑1分钟 + 走2分钟 × 重复6组，总时长18分钟
🧘 放松：慢走2分钟 + 站立小腿拉伸每侧30秒 + 大腿前侧拉伸每侧30秒"

则：
- content: "热身5分钟 + 跑走结合18分钟 + 拉伸5分钟"
- full_content: "🔥 热身：快走3分钟 + 原地高抬腿30秒 + 开合跳30次 + 踝关节绕环左右各10次\n💪 主训练：跑1分钟 + 走2分钟 × 重复6组，总时长18分钟\n🧘 放松：慢走2分钟 + 站立小腿拉伸每侧30秒 + 大腿前侧拉伸每侧30秒"
"""

        # 调用AI生成JSON
        req_data = json.dumps({
            "model": LLM_MODEL,
            "messages": [
                {"role": "system", "content": "你是一个数据提取助手，只输出JSON格式的数据，不要其他内容。"},
                {"role": "user", "content": extract_prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 4096
        }).encode('utf-8')

        req = urllib.request.Request(LLM_BASE, data=req_data, headers={
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {LLM_KEY}'
        })
        
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read().decode('utf-8'))
        
        json_reply = result['choices'][0]['message']['content'].strip()
        
        # 尝试解析JSON
        # 提取JSON（可能包含在```json...```中）
        json_match = re.search(r'```json\s*([\s\S]*?)```', json_reply)
        if json_match:
            json_str = json_match.group(1).strip()
        else:
            json_str = json_reply
        
        plan_json = json.loads(json_str)
        
        # 验证必需字段
        if all(k in plan_json for k in ['title', 'sport_type', 'total_days', 'days']):
            # 将完整文本添加到 plan_json 中
            plan_json['full_description'] = full_text
            
            # 保存到数据库
            db = get_db()
            db.execute('''UPDATE pending_plans SET plan_json = ?, status = 'completed' 
                          WHERE user_id = ? AND session_id = ? AND message_id = ?''',
                       (json.dumps(plan_json, ensure_ascii=False), user_id, session_id, message_id))
            db.commit()
            db.close()
            print(f"[INFO] 成功生成计划JSON: session_id={session_id}, message_id={message_id}")
        else:
            raise ValueError("JSON缺少必需字段")
            
    except Exception as e:
        print(f"[ERROR] 生成计划JSON失败: {str(e)}")
        print(f"[ERROR] 错误类型: {type(e).__name__}")
        print(f"[ERROR] 详细信息: {repr(e)}")
        import traceback
        print(f"[ERROR] 堆栈跟踪:\n{traceback.format_exc()}")
        # 标记为失败
        try:
            db = get_db()
            db.execute('''UPDATE pending_plans SET status = 'failed' 
                          WHERE user_id = ? AND session_id = ? AND message_id = ?''',
                       (user_id, session_id, message_id))
            db.commit()
            db.close()
        except:
            pass

# ============ AI Chat API ============

@app.route('/api/chat', methods=['POST'])
@require_auth
def chat(**kwargs):
    user_id = kwargs['user_id']
    data = request.get_json()
    
    # 前端发送的是 messages 数组，提取最新的用户消息
    messages = data.get('messages', [])
    if not messages:
        return jsonify({'error': '消息不能为空'}), 400
    
    # 获取最新的用户消息
    last_message = messages[-1] if messages else None
    if not last_message or last_message.get('role') != 'user':
        return jsonify({'error': '消息格式错误'}), 400
    
    message = last_message.get('content', '').strip()
    if not message:
        return jsonify({'error': '消息不能为空'}), 400
    
    # 获取或生成 session_id
    session_id = data.get('session_id', '')
    if not session_id:
        # 如果前端没有传递 session_id，生成一个新的
        import uuid
        session_id = str(uuid.uuid4())
        print(f"[DEBUG] 生成新的 session_id: {session_id}")
    else:
        print(f"[DEBUG] 使用现有 session_id: {session_id}")

    db = get_db()
    # Save user message
    db.execute('INSERT INTO conversations (user_id, session_id, role, content) VALUES (?, ?, ?, ?)',
               (user_id, session_id, 'user', message))
    db.commit()

    # Get conversation history (使用前端传来的messages，因为它已经包含了完整历史)
    # 但为了保持数据库记录，我们仍然查询数据库
    history = db.execute('SELECT role, content FROM conversations WHERE user_id = ? AND session_id = ? ORDER BY id',
                         (user_id, session_id)).fetchall()

    system_prompt = """你是一个专业的运动教练AI助手。你的任务是帮助用户制定个性化的运动训练计划。

**重要限制**：
- 每次只生成一个阶段的计划（最多28天）
- 如果用户需要更长期的计划（如3个月），请分阶段生成，先生成第一阶段（如前4周）

**当用户确认要生成计划时，请按以下格式回复**：

---
好的！我为你制定了【计划标题】（共X天）

**📋 计划信息**
运动类型：[跑步/跳绳/健身/瑜伽等] | 目标：[用户目标] | 周期：X天 | 强度：[低/中/高]

**📅 训练计划**

**第1天 - 标题**
🔥 热身：具体动作
💪 主训练：具体内容
🧘 放松：拉伸动作

**第2天 - 标题**
🔥 热身：具体动作
💪 主训练：具体内容
🧘 放松：拉伸动作

...(列出所有天数)

💡 **温馨提示**
- 注意事项
- 休息建议
---

**格式要求**：
- 直接展示计划内容，不要过多寒暄和说明
- 每天的训练描述要清晰具体，但不要过于冗长
- 合理安排休息日（每周1-2天）
- 天数限制：最多28天
- 不要在回复中包含JSON或代码块
- 如果用户还没确定具体需求，先通过对话了解情况再生成计划"""

    messages = [{"role": "system", "content": system_prompt}]
    for h in history:
        messages.append({"role": h['role'], "content": h['content']})

    # Call LLM
    try:
        req_data = json.dumps({
            "model": LLM_MODEL,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 4096
        }).encode('utf-8')

        req = urllib.request.Request(LLM_BASE, data=req_data, headers={
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {LLM_KEY}'
        })
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read().decode('utf-8'))

        reply = result['choices'][0]['message']['content']
    except Exception as e:
        reply = f"抱歉，AI服务暂时不可用：{str(e)}"

    # Save assistant reply
    db.execute('INSERT INTO conversations (user_id, session_id, role, content) VALUES (?, ?, ?, ?)',
               (user_id, session_id, 'assistant', reply))
    db.commit()
    
    # 获取刚插入的message_id
    message_id = db.execute('SELECT last_insert_rowid() as id').fetchone()['id']
    
    # 检测是否包含训练计划（启发式检测）
    is_plan = any(keyword in reply for keyword in ['📋 计划概述', '📅 第一周', '第1天', '🔥 热身', '💪 主训练', '🧘 放松', '**第1天'])
    
    if is_plan:
        # 保存到 pending_plans 表，状态为 processing
        db.execute('''INSERT INTO pending_plans (user_id, session_id, message_id, full_text, status) 
                      VALUES (?, ?, ?, ?, 'processing')''',
                   (user_id, session_id, message_id, reply))
        db.commit()
        
        # 启动后台线程生成 JSON
        thread = threading.Thread(target=generate_plan_json_async, 
                                   args=(user_id, session_id, message_id, reply))
        thread.daemon = True
        thread.start()
    
    db.close()

    return jsonify({
        'reply': reply, 
        'has_plan_detected': is_plan,
        'session_id': session_id
    })

@app.route('/api/chat/sessions', methods=['GET'])
@require_auth
def get_sessions(**kwargs):
    user_id = kwargs['user_id']
    db = get_db()
    sessions = db.execute('''SELECT session_id, MIN(created_at) as started_at, COUNT(*) as msg_count
        FROM conversations WHERE user_id = ? GROUP BY session_id ORDER BY started_at DESC''',
        (user_id,)).fetchall()
    db.close()
    return jsonify([dict(s) for s in sessions])

@app.route('/api/chat/history/<session_id>', methods=['GET'])
@require_auth
def get_chat_history(session_id, **kwargs):
    user_id = kwargs['user_id']
    db = get_db()
    messages = db.execute('SELECT role, content, created_at FROM conversations WHERE user_id = ? AND session_id = ? ORDER BY id',
                          (user_id, session_id)).fetchall()
    db.close()
    return jsonify([dict(m) for m in messages])

@app.route('/api/chat/plan_status/<session_id>', methods=['GET'])
@require_auth
def get_plan_status(session_id, **kwargs):
    user_id = kwargs['user_id']
    db = get_db()
    pending = db.execute('''SELECT status, plan_json FROM pending_plans 
                            WHERE user_id = ? AND session_id = ? 
                            ORDER BY id DESC LIMIT 1''',
                         (user_id, session_id)).fetchone()
    db.close()
    
    if not pending:
        return jsonify({'status': 'not_found'})
    
    if pending['status'] == 'completed' and pending['plan_json']:
        return jsonify({
            'status': 'completed',
            'plan': json.loads(pending['plan_json'])
        })
    elif pending['status'] == 'failed':
        return jsonify({'status': 'failed'})
    else:
        return jsonify({'status': 'processing'})

@app.route('/api/chat/session/<session_id>', methods=['DELETE'])
@require_auth
def delete_session(session_id, **kwargs):
    user_id = kwargs['user_id']
    db = get_db()
    db.execute('DELETE FROM conversations WHERE user_id = ? AND session_id = ?', (user_id, session_id))
    db.commit()
    db.close()
    return jsonify({'success': True})

@app.route('/api/plans/from-ai', methods=['POST'])
@require_auth
def create_plan_from_ai(**kwargs):
    user_id = kwargs['user_id']
    data = request.get_json()
    plan_data = data.get('plan')
    if not plan_data:
        return jsonify({'error': '计划数据为空'}), 400
    db = get_db()
    count = db.execute('SELECT COUNT(*) as c FROM plans WHERE user_id = ?', (user_id,)).fetchone()['c']
    if count >= 3:
        db.close()
        return jsonify({'error': '最多只能有3个运动计划，请先删除现有计划'}), 400
    cursor = db.execute('INSERT INTO plans (user_id, title, sport_type, total_days, description) VALUES (?, ?, ?, ?, ?)',
               (user_id, plan_data['title'], plan_data['sport_type'], plan_data['total_days'], plan_data.get('description', '')))
    plan_id = cursor.lastrowid
    for d in plan_data['days']:
        db.execute('INSERT INTO plan_days (plan_id, day_number, title, content, day_type) VALUES (?, ?, ?, ?, ?)',
                   (plan_id, d['day'], d['title'], d['content'], d.get('type', '')))
    db.commit()
    db.close()
    return jsonify({'success': True, 'plan_id': plan_id})

# ============ Static ============

@app.route('/')
def index():
    return send_from_directory('templates', 'index.html')

@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)

# ============ Main ============

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5051, debug=False)
