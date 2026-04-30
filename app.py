from flask import Flask, request, render_template_string, redirect, jsonify, session, send_file
import sqlite3
import os
import hashlib
import secrets
import json
from datetime import datetime
from functools import wraps
from io import BytesIO

# تفادي خطأ pandas
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    print("⚠️ Pandas not installed. Excel import/export disabled.")

# تفادي خطأ arabic_reshaper
try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    ARABIC_AVAILABLE = True
except ImportError:
    ARABIC_AVAILABLE = False
    print("⚠️ Arabic reshaping not installed.")

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# ==================== دوال الأمان ====================

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def init_users():
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
    c.execute("SELECT * FROM users WHERE username = 'admin'")
    if not c.fetchone():
        admin_pass = hash_password('admin123')
        c.execute("INSERT INTO users (username, password, role, created_at) VALUES (?, ?, ?, ?)",
                  ('admin', admin_pass, 'admin', datetime.now().strftime('%Y-%m-%d')))
    c.execute("SELECT * FROM users WHERE username = 'viewer'")
    if not c.fetchone():
        viewer_pass = hash_password('viewer123')
        c.execute("INSERT INTO users (username, password, role, created_at) VALUES (?, ?, ?, ?)",
                  ('viewer', viewer_pass, 'viewer', datetime.now().strftime('%Y-%m-%d')))
    conn.commit()
    conn.close()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect('/login')
        if session.get('role') != 'admin':
            return "⛔ غير مصرح لك", 403
        return f(*args, **kwargs)
    return decorated_function

def get_current_user():
    if 'user_id' in session:
        return {'id': session['user_id'], 'username': session['username'], 'role': session['role']}
    return None

# ==================== قاعدة البيانات المتطورة ====================

def init_database():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    
    # جدول الرتب
    c.execute('''
        CREATE TABLE IF NOT EXISTS grades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name_ar TEXT,
            name_fr TEXT,
            category TEXT,
            base_salary REAL,
            "order" INTEGER,
            icon TEXT
        )
    ''')
    
    # جدول المنح
    c.execute('''
        CREATE TABLE IF NOT EXISTS allowances (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE,
            name_ar TEXT,
            name_fr TEXT,
            amount REAL,
            is_percentage BOOLEAN DEFAULT 0,
            is_active BOOLEAN DEFAULT 1
        )
    ''')
    
    # جدول الموظفين
    c.execute('''
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE,
            name TEXT NOT NULL,
            position TEXT,
            grade_id INTEGER,
            base_salary REAL,
            family_allowance REAL DEFAULT 0,
            regional_allowance REAL DEFAULT 0,
            contract_type TEXT DEFAULT 'cadre',
            hire_date DATE,
            status TEXT DEFAULT 'actif',
            FOREIGN KEY (grade_id) REFERENCES grades(id)
        )
    ''')
    
    # جدول الرواتب المؤرشفة
    c.execute('''
        CREATE TABLE IF NOT EXISTS payroll_archive (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            month INTEGER,
            year INTEGER,
            employee_id INTEGER,
            employee_code TEXT,
            employee_name TEXT,
            grade_name TEXT,
            base_salary REAL,
            total_allowances REAL,
            gross_salary REAL,
            irg REAL,
            cnap REAL,
            net_salary REAL,
            created_at DATE,
            FOREIGN KEY (employee_id) REFERENCES employees(id)
        )
    ''')
    
    # إضافة الرتب الأساسية
    default_grades = [
        ('طبيب مختص', 'Médecin spécialiste', 'طبي', 180000, 1, '🩺'),
        ('طبيب عام', 'Médecin généraliste', 'طبي', 120000, 2, '👨‍⚕️'),
        ('ممرض رئيسي', 'Infirmier principal', 'طبي', 75000, 3, '💉'),
        ('ممرض', 'Infirmier', 'طبي', 60000, 4, '💉'),
        ('مدير', 'Directeur', 'إداري', 150000, 5, '👔'),
        ('كاتب', 'Rédacteur', 'إداري', 80000, 6, '✍️'),
        ('عون', 'Agent', 'خدمات', 50000, 7, '🔧'),
    ]
    for grade in default_grades:
        c.execute('''INSERT OR IGNORE INTO grades (name_ar, name_fr, category, base_salary, "order", icon) 
                    VALUES (?, ?, ?, ?, ?, ?)''', grade)
    
    # إضافة منح افتراضية
    default_allowances = [
        ('101', 'منحة الخبرة', "Prime d'expérience", 0.15, 1, 1),
        ('102', 'منحة السكن', 'Prime logement', 5000, 0, 1),
        ('103', 'منحة النقل', 'Prime transport', 3000, 0, 1),
        ('104', 'منحة المنطقة', "Prime d'éloignement", 0.10, 1, 1),
        ('105', 'منحة المردودية', 'Prime de rendement', 0.08, 1, 1),
    ]
    for allowance in default_allowances:
        c.execute('''INSERT OR IGNORE INTO allowances (code, name_ar, name_fr, amount, is_percentage, is_active) 
                    VALUES (?, ?, ?, ?, ?, ?)''', allowance)
    
    conn.commit()
    conn.close()

def get_db():
    try:
        init_database()
        init_users()
    except Exception as e:
        print(f"Database init error: {e}")
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

def calculate_total_allowances(base_salary, family=0, regional=0):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT amount, is_percentage FROM allowances WHERE is_active = 1")
    allowances = c.fetchall()
    conn.close()
    total = family + regional
    for allowance in allowances:
        if allowance['is_percentage']:
            total += base_salary * allowance['amount']
        else:
            total += allowance['amount']
    return total

def calculate_net_salary(base_salary, family=0, regional=0):
    total_allowances = calculate_total_allowances(base_salary, family, regional)
    gross = base_salary + total_allowances
    irg = calculate_irg(gross)
    cnap = gross * 0.09
    net = gross - irg - cnap
    return {
        'base': base_salary,
        'allowances': total_allowances,
        'gross': gross,
        'irg': irg,
        'cnap': cnap,
        'net': net
    }

# ==================== API الاستيراد والتصدير ====================

@app.route('/api/export_etat_matrice')
@admin_required
def export_etat_matrice():
    if not PANDAS_AVAILABLE:
        return "Pandas not available", 500
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        SELECT e.id, e.code, e.name, e.position, g.name_ar as grade, 
               e.base_salary, e.family_allowance, e.regional_allowance, e.contract_type
        FROM employees e
        JOIN grades g ON e.grade_id = g.id
        WHERE e.status = 'actif'
        ORDER BY g."order", e.name
    ''')
    employees = c.fetchall()
    conn.close()
    data = []
    for emp in employees:
        salary_data = calculate_net_salary(emp['base_salary'], emp['family_allowance'], emp['regional_allowance'])
        data.append({
            'الرقم التسلسلي': emp['code'],
            'الاسم الكامل': emp['name'],
            'الرتبة / المنصب': emp['grade'],
            'نوع العقد': 'مرسم' if emp['contract_type'] == 'cadre' else 'متعاقد',
            'الراتب القاعدي': emp['base_salary'],
            'منحة عائلية': emp['family_allowance'],
            'منحة المنطقة': emp['regional_allowance'],
            'مجموع المنح': salary_data['allowances'],
            'الراتب الإجمالي': salary_data['gross'],
            'IRG': salary_data['irg'],
            'CNAS': salary_data['cnap'],
            'صافي الراتب': salary_data['net']
        })
    df = pd.DataFrame(data)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Etat Matrice', index=False)
    output.seek(0)
    return send_file(output, as_attachment=True, download_name=f'etat_matrice_{datetime.now().strftime("%Y%m%d")}.xlsx')

@app.route('/api/stats')
@login_required
def api_stats():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM employees WHERE status = 'actif'")
    total_employees = c.fetchone()[0] or 0
    c.execute("SELECT SUM(base_salary) FROM employees WHERE status = 'actif'")
    total_payroll = c.fetchone()[0] or 0
    c.execute("SELECT COUNT(*) FROM employees WHERE contract_type = 'cadre'")
    cadres = c.fetchone()[0] or 0
    c.execute("SELECT COUNT(*) FROM employees WHERE contract_type = 'contract'")
    contracts = c.fetchone()[0] or 0
    workers = total_employees - cadres - contracts
    conn.close()
    return jsonify({
        'total_employees': total_employees,
        'total_payroll': total_payroll,
        'cadres': cadres,
        'workers': workers,
        'contracts': contracts,
        'total_cnas': total_payroll * 0.09,
        'total_irg': total_payroll * 0.15
    })

@app.route('/api/search')
@login_required
def api_search():
    q = request.args.get('q', '')
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT code, name FROM employees WHERE code LIKE ? OR name LIKE ? LIMIT 20", (f'%{q}%', f'%{q}%'))
    results = [{'code': row[0], 'name': row[1]} for row in c.fetchall()]
    conn.close()
    return jsonify(results)

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

# ==================== المسارات الرئيسية ====================

@app.route('/')
@login_required
def index():
    user = get_current_user()
    is_admin = user['role'] == 'admin'
    
    conn = get_db()
    c = conn.cursor()
    
    c.execute('''
        SELECT e.id, e.code, e.name, e.position, e.base_salary, e.family_allowance, e.regional_allowance,
               g.name_ar as grade_name, g.icon, g.base_salary as grade_salary, e.contract_type
        FROM employees e
        JOIN grades g ON e.grade_id = g.id
        WHERE e.status = 'actif'
        ORDER BY g."order", e.name
    ''')
    rows = c.fetchall()
    
    employees_list = []
    total_net = 0
    for row in rows:
        salary = row['base_salary'] if row['base_salary'] and row['base_salary'] > 0 else row['grade_salary']
        res = calculate_net_salary(salary or 0, row['family_allowance'] or 0, row['regional_allowance'] or 0)
        net = res['net']
        total_net += net
        employees_list.append({
            'id': row['id'],
            'code': row['code'],
            'name': row['name'],
            'position': row['position'] or '',
            'grade_name': row['grade_name'] or '',
            'icon': row['icon'] or '👤',
            'base_salary': salary or 0,
            'net': net,
            'contract_type': row['contract_type'] or 'cadre'
        })
    
    c.execute("SELECT id, name_ar, icon, base_salary FROM grades ORDER BY \"order\"")
    grades = [{'id': row['id'], 'name_ar': row['name_ar'], 'icon': row['icon'], 'base_salary': row['base_salary']} for row in c.fetchall()]
    
    c.execute("SELECT COUNT(*) FROM employees WHERE status = 'actif'")
    total_emp = c.fetchone()[0] or 0
    
    c.execute("SELECT COUNT(*) FROM employees WHERE contract_type = 'cadre'")
    cadres = c.fetchone()[0] or 0
    
    c.execute("SELECT COUNT(*) FROM employees WHERE contract_type = 'contract'")
    contracts = c.fetchone()[0] or 0
    
    workers = total_emp - cadres - contracts
    
    conn.close()
    
    stats = {
        'count': total_emp,
        'total_payroll': f"{total_net:,.0f}" if total_net else "0",
        'avg_salary': f"{total_net/total_emp:,.0f}" if total_emp else "0",
        'cadres': cadres,
        'workers': workers,
        'contracts': contracts
    }
    
    return render_template_string(TEMPLATE, employees=employees_list, stats=stats, grades=grades, user=user, is_admin=is_admin)

@app.route('/add', methods=['POST'])
@admin_required
def add_employee():
    name = request.form['name']
    position = request.form.get('position', '')
    grade_id = int(request.form['grade_id'])
    contract_type = request.form.get('contract_type', 'cadre')
    
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT base_salary FROM grades WHERE id = ?", (grade_id,))
    grade_row = c.fetchone()
    base_salary = grade_row['base_salary'] if grade_row else 50000
    
    code = f"EMP{datetime.now().strftime('%Y%m%d%H%M%S')}"
    c.execute('''INSERT INTO employees (code, name, position, grade_id, base_salary, contract_type, hire_date) 
                 VALUES (?, ?, ?, ?, ?, ?, ?)''',
              (code, name, position, grade_id, base_salary, contract_type, datetime.now().strftime('%Y-%m-%d')))
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
    return jsonify({'status': 'running', 'pandas': PANDAS_AVAILABLE})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
