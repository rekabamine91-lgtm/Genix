from flask import Flask, request, render_template_string, redirect, jsonify, session
import sqlite3
import os
import hashlib
import secrets
from datetime import datetime
from functools import wraps

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

# ==================== دوال الأمان ====================

def hash_password(password):
    """تشفير كلمة المرور باستخدام SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def init_users():
    """إنشاء جدول المستخدمين ومستخدم افتراضي"""
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            role TEXT DEFAULT 'viewer',
            created_at DATE
        )
    ''')
    
    # التحقق من وجود مستخدم admin، إذا لم يكن موجوداً يتم إنشاؤه
    c.execute("SELECT * FROM users WHERE username = 'admin'")
    if not c.fetchone():
        admin_pass = hash_password('admin123')
        c.execute("INSERT INTO users (username, password, role, created_at) VALUES (?, ?, ?, ?)",
                  ('admin', admin_pass, 'admin', datetime.now().strftime('%Y-%m-%d')))
    
    # إضافة مستخدم مشاهد (viewer) للاختبار
    c.execute("SELECT * FROM users WHERE username = 'viewer'")
    if not c.fetchone():
        viewer_pass = hash_password('viewer123')
        c.execute("INSERT INTO users (username, password, role, created_at) VALUES (?, ?, ?, ?)",
                  ('viewer', viewer_pass, 'viewer', datetime.now().strftime('%Y-%m-%d')))
    
    conn.commit()
    conn.close()

def login_required(f):
    """ديكوراتور لحماية المسارات التي تتطلب تسجيل دخول"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """ديكوراتور لحماية المسارات التي تتطلب صلاحيات مدير"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect('/login')
        if session.get('role') != 'admin':
            return "⛔ غير مصرح لك بالوصول إلى هذه الصفحة", 403
        return f(*args, **kwargs)
    return decorated_function

def get_current_user():
    """جلب معلومات المستخدم الحالي"""
    if 'user_id' in session:
        return {'id': session['user_id'], 'username': session['username'], 'role': session['role']}
    return None

# ==================== هيكل الرتب والمنح ====================

GRADES_DATA = [
    {'name_ar': 'ممارس متخصص خارج الصنف', 'name_fr': 'Praticien spécialiste hors classe', 'sector': 'صحة', 'category': 'طبيب مختص', 'base_salary': 204000, 'order': 1, 'icon': '🩺'},
    {'name_ar': 'طبيب عام رئيس', 'name_fr': 'Médecin généraliste principal', 'sector': 'صحة', 'category': 'طبيب عام', 'base_salary': 145000, 'order': 2, 'icon': '👨‍⚕️'},
    {'name_ar': 'ممارس طبي عام', 'name_fr': 'Praticien médical généraliste', 'sector': 'صحة', 'category': 'طبيب عام', 'base_salary': 120000, 'order': 3, 'icon': '👨‍⚕️'},
    {'name_ar': 'ممرض ممتاز', 'name_fr': 'Infirmier senior', 'sector': 'صحة', 'category': 'شبه طبي', 'base_salary': 85000, 'order': 4, 'icon': '💉'},
    {'name_ar': 'ممرض رئيسي', 'name_fr': 'Infirmier principal', 'sector': 'صحة', 'category': 'شبه طبي', 'base_salary': 75000, 'order': 5, 'icon': '💉'},
    {'name_ar': 'قابلة رئيسة', 'name_fr': 'Sage-femme principale', 'sector': 'صحة', 'category': 'قابلة', 'base_salary': 90000, 'order': 6, 'icon': '👶'},
    {'name_ar': 'مدير إدارة مركزية', 'name_fr': "Directeur d'administration", 'sector': 'إدارة', 'category': 'إداري', 'base_salary': 150000, 'order': 7, 'icon': '👔'},
    {'name_ar': 'رئيس مصلحة', 'name_fr': 'Chef de service', 'sector': 'إدارة', 'category': 'إداري', 'base_salary': 120000, 'order': 8, 'icon': '📋'},
    {'name_ar': 'كاتب إداري', 'name_fr': 'Rédacteur', 'sector': 'إدارة', 'category': 'إداري', 'base_salary': 80000, 'order': 9, 'icon': '✍️'},
    {'name_ar': 'عون إداري', 'name_fr': 'Agent admin', 'sector': 'إدارة', 'category': 'إداري', 'base_salary': 60000, 'order': 10, 'icon': '🖥️'},
    {'name_ar': 'تقني سامي', 'name_fr': 'Technicien supérieur', 'sector': 'تقني', 'category': 'مهني', 'base_salary': 70000, 'order': 11, 'icon': '🔧'},
    {'name_ar': 'عون خدمة', 'name_fr': 'Agent de service', 'sector': 'خدمات', 'category': 'خدمة', 'base_salary': 40000, 'order': 12, 'icon': '🧹'},
]

ALLOWANCES_DATA = [
    {'code': '101', 'name_ar': 'منحة الخبرة', 'name_fr': "Prime d'expérience", 'amount': 0.15, 'is_percentage': True},
    {'code': '102', 'name_ar': 'منحة السكن', 'name_fr': 'Prime logement', 'amount': 5000, 'is_percentage': False},
    {'code': '103', 'name_ar': 'منحة النقل', 'name_fr': 'Prime transport', 'amount': 3000, 'is_percentage': False},
    {'code': '104', 'name_ar': 'منحة خطر العدوى', 'name_fr': "Prime d'infection", 'amount': 8000, 'is_percentage': False},
]

# ==================== دوال قاعدة البيانات ====================

def init_database():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS grades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name_ar TEXT, name_fr TEXT, sector TEXT, category TEXT,
        base_salary REAL, "order" INTEGER, icon TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS allowances (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT, name_ar TEXT, name_fr TEXT, amount REAL, is_percentage BOOLEAN)''')
    c.execute('''CREATE TABLE IF NOT EXISTS employees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT, position TEXT, grade_id INTEGER,
        base_salary REAL, hire_date DATE, status TEXT DEFAULT 'actif')''')
    
    for grade in GRADES_DATA:
        c.execute('''INSERT OR IGNORE INTO grades 
                    (name_ar, name_fr, sector, category, base_salary, "order", icon) 
                    VALUES (?, ?, ?, ?, ?, ?, ?)''',
                  (grade['name_ar'], grade['name_fr'], grade['sector'], 
                   grade['category'], grade['base_salary'], grade['order'], grade['icon']))
    
    for allowance in ALLOWANCES_DATA:
        c.execute('''INSERT OR IGNORE INTO allowances 
                    (code, name_ar, name_fr, amount, is_percentage) VALUES (?, ?, ?, ?, ?)''',
                  (allowance['code'], allowance['name_ar'], allowance['name_fr'], 
                   allowance['amount'], allowance['is_percentage']))
    conn.commit()
    conn.close()

def get_db():
    try:
        init_database()
        init_users()
    except:
        pass
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

# ==================== دوال الحساب ====================

def calculate_irg(salary):
    if salary <= 30000:
        return 0
    elif salary <= 80000:
        return (salary - 30000) * 0.15
    elif salary <= 160000:
        return 7500 + (salary - 80000) * 0.25
    elif salary <= 320000:
        return 27500 + (salary - 160000) * 0.35
    else:
        return 83500 + (salary - 320000) * 0.40

def calculate_salary_with_allowances(base_salary):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT amount, is_percentage FROM allowances")
    allowances = c.fetchall()
    conn.close()
    
    total_allowances = 0
    for allowance in allowances:
        if allowance['is_percentage']:
            total_allowances += base_salary * allowance['amount']
        else:
            total_allowances += allowance['amount']
    
    gross_salary = base_salary + total_allowances
    irg = calculate_irg(gross_salary)
    cnap = gross_salary * 0.09
    net_salary = gross_salary - irg - cnap
    
    return {
        'gross_salary': round(gross_salary, 2),
        'total_allowances': round(total_allowances, 2),
        'irg': round(irg, 2),
        'cnap': round(cnap, 2),
        'net_salary': round(net_salary, 2)
    }

# ==================== صفحات تسجيل الدخول ====================

LOGIN_TEMPLATE = '''
<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>تسجيل الدخول - Genix Pro</title>
    <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Cairo', sans-serif; }
        body {
            min-height: 100vh;
            background: linear-gradient(135deg, #0f2027, #203a43, #2c5364);
            display: flex;
            justify-content: center;
            align-items: center;
        }
        .login-card {
            background: rgba(255,255,255,0.95);
            backdrop-filter: blur(10px);
            border-radius: 32px;
            padding: 40px;
            width: 400px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.2);
            text-align: center;
        }
        .login-card h2 { color: #1e3c72; margin-bottom: 10px; }
        .login-card input {
            width: 100%;
            padding: 14px;
            margin: 12px 0;
            border: 1px solid #ddd;
            border-radius: 28px;
            font-size: 16px;
        }
        .login-card button {
            width: 100%;
            padding: 14px;
            background: linear-gradient(135deg, #1e3c72, #2a5298);
            color: white;
            border: none;
            border-radius: 28px;
            font-size: 18px;
            cursor: pointer;
            margin-top: 10px;
        }
        .error { color: #dc2626; margin-top: 15px; font-size: 14px; }
        .flag { width: 60px; margin-bottom: 20px; }
    </style>
</head>
<body>
    <div class="login-card">
        <img class="flag" src="https://upload.wikimedia.org/wikipedia/commons/7/77/Flag_of_Algeria.svg" alt="علم الجزائر">
        <h2>🔐 Genix Pro</h2>
        <p style="color: #666; margin-bottom: 20px;">نظام إدارة أجور الصحة</p>
        <form method="post">
            <input type="text" name="username" placeholder="اسم المستخدم" required>
            <input type="password" name="password" placeholder="كلمة المرور" required>
            <button type="submit">دخول</button>
        </form>
        {% if error %}
        <div class="error">{{ error }}</div>
        {% endif %}
        <hr style="margin: 20px 0;">
        <p style="font-size: 12px; color: #666;">Demo: admin / admin123 | viewer / viewer123</p>
        <p style="font-size: 12px; margin-top: 10px;">© 2025 Rekab Amine</p>
    </div>
</body>
</html>
'''

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed = hash_password(password)
        
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT id, username, role FROM users WHERE username = ? AND password = ?", (username, hashed))
        user = c.fetchone()
        conn.close()
        
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            return redirect('/')
        else:
            error = 'اسم المستخدم أو كلمة المرور غير صحيحة'
    
    return render_template_string(LOGIN_TEMPLATE, error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

# ==================== تحميل القالب ====================

with open('template.html', 'r', encoding='utf-8') as f:
    TEMPLATE = f.read()

# ==================== المسارات الرئيسية المحمية ====================

@app.route('/')
@login_required
def index():
    user = get_current_user()
    is_admin = user['role'] == 'admin'
    
    conn = get_db()
    c = conn.cursor()
    
    c.execute('''
        SELECT e.id, e.name, e.position, e.base_salary, g.name_ar, g.sector, g.icon, g.base_salary as grade_salary
        FROM employees e
        JOIN grades g ON e.grade_id = g.id
        ORDER BY g."order"
    ''')
    rows = c.fetchall()
    
    employees_list = []
    total_net = 0
    for row in rows:
        salary = row['base_salary'] if row['base_salary'] > 0 else row['grade_salary']
        res = calculate_salary_with_allowances(salary)
        net = res['net_salary']
        total_net += net
        employees_list.append({
            'id': row['id'],
            'name': row['name'],
            'position': row['position'],
            'grade_name': row['name_ar'],
            'sector': row['sector'],
            'icon': row['icon'],
            'base_salary': salary,
            'net': net
        })
    
    c.execute("SELECT id, name_ar, icon, base_salary FROM grades ORDER BY \"order\"")
    grades = [{'id': row['id'], 'name_ar': row['name_ar'], 'icon': row['icon'], 'base_salary': row['base_salary']} for row in c.fetchall()]
    conn.close()
    
    stats = {
        'count': len(employees_list),
        'total_payroll': f"{total_net:,.0f}",
        'avg_salary': f"{total_net/len(employees_list):,.0f}" if employees_list else "0"
    }
    
    return render_template_string(TEMPLATE, 
                                  employees=employees_list, 
                                  stats=stats, 
                                  grades=grades,
                                  user=user,
                                  is_admin=is_admin)

@app.route('/add', methods=['POST'])
@admin_required
def add_employee():
    name = request.form['name']
    position = request.form.get('position', '')
    grade_id = int(request.form['grade_id'])
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT base_salary FROM grades WHERE id = ?", (grade_id,))
    grade_row = c.fetchone()
    base_salary = grade_row['base_salary'] if grade_row else 0
    c.execute('INSERT INTO employees (name, position, grade_id, base_salary, hire_date) VALUES (?,?,?,?,?)',
              (name, position, grade_id, base_salary, datetime.now().strftime('%Y-%m-%d')))
    conn.commit()
    conn.close()
    return redirect('/')

@app.route('/delete/<int:emp_id>')
@admin_required
def delete_employee(emp_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM employees WHERE id = ?", (emp_id,))
    conn.commit()
    conn.close()
    return redirect('/')

@app.route('/health')
def health():
    return jsonify({'status': 'running'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
