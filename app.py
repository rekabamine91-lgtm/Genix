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

# ==================== قاعدة البيانات ====================

def init_database():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            position TEXT,
            salary REAL
        )
    ''')
    c.execute("SELECT COUNT(*) FROM employees")
    if c.fetchone()[0] == 0:
        sample_data = [
            ('أمين ركاب', 'مدير', 50000),
            ('محمد أحمد', 'محاسب', 40000),
            ('سارة علي', 'ممرضة', 35000),
        ]
        c.executemany("INSERT INTO employees (name, position, salary) VALUES (?, ?, ?)", sample_data)
    conn.commit()
    conn.close()

def get_db():
    try:
        init_database()
        init_users()
    except Exception as e:
        print(f"Error: {e}")
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

# ==================== صفحة تسجيل الدخول ====================

LOGIN_TEMPLATE = '''
<!DOCTYPE html>
<html dir="rtl">
<head>
    <meta charset="UTF-8">
    <title>تسجيل الدخول - Genix</title>
    <style>
        * { font-family: 'Tahoma', sans-serif; }
        body { background: linear-gradient(135deg, #1e3c72, #2a5298); display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; }
        .login-box { background: white; padding: 40px; border-radius: 20px; width: 350px; text-align: center; }
        input { width: 100%; padding: 12px; margin: 10px 0; border: 1px solid #ddd; border-radius: 8px; }
        button { width: 100%; padding: 12px; background: #1e3c72; color: white; border: none; border-radius: 8px; cursor: pointer; }
        .error { color: red; margin-top: 10px; }
    </style>
</head>
<body>
    <div class="login-box">
        <h2>🔐 Genix Pro</h2>
        <form method="post">
            <input type="text" name="username" placeholder="اسم المستخدم" required>
            <input type="password" name="password" placeholder="كلمة المرور" required>
            <button type="submit">دخول</button>
        </form>
        {% if error %}<p class="error">{{ error }}</p>{% endif %}
        <p style="font-size:12px; margin-top:20px;">admin / admin123 | viewer / viewer123</p>
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
            error = 'خطأ في اسم المستخدم أو كلمة المرور'
    return render_template_string(LOGIN_TEMPLATE, error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

# ==================== الصفحة الرئيسية (القالب مدمج هنا) ====================

MAIN_TEMPLATE = '''
<!DOCTYPE html>
<html dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Genix Pro | نظام إدارة الأجور</title>
    <style>
        * { font-family: 'Tahoma', sans-serif; margin: 0; padding: 0; box-sizing: border-box; }
        body { background: #f0f2f5; padding: 20px; }
        .header { background: linear-gradient(135deg, #1e3c72, #2a5298); color: white; padding: 20px; border-radius: 15px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; }
        .stats { display: flex; gap: 15px; margin-bottom: 20px; flex-wrap: wrap; }
        .stat-card { background: white; border-radius: 15px; padding: 20px; flex: 1; text-align: center; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .stat-number { font-size: 2em; font-weight: bold; color: #1e3c72; }
        .card { background: white; border-radius: 15px; padding: 20px; margin-bottom: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 12px; text-align: right; border-bottom: 1px solid #ddd; }
        th { background: #1e3c72; color: white; }
        input, select { padding: 10px; margin: 5px; border-radius: 8px; border: 1px solid #ddd; }
        button { background: #1e3c72; color: white; border: none; padding: 10px 20px; border-radius: 8px; cursor: pointer; }
        .delete { color: red; text-decoration: none; }
        .form-row { display: flex; gap: 10px; flex-wrap: wrap; align-items: end; }
        @media (max-width: 600px) {
            .header { flex-direction: column; gap: 10px; text-align: center; }
            .stats { flex-direction: column; }
            .form-row { flex-direction: column; }
            table { font-size: 12px; }
            th, td { padding: 8px; }
        }
    </style>
</head>
<body>
    <div class="container" style="max-width: 1200px; margin: auto;">
        <div class="header">
            <div>
                <h1>💰 Genix Pro</h1>
                <p>نظام إدارة أجور الصحة</p>
            </div>
            <div>
                <span style="background: rgba(255,255,255,0.2); padding: 8px 15px; border-radius: 20px;">
                    👤 {{ user.username }} ({% if is_admin %}مدير{% else %}مشاهد{% endif %})
                </span>
                <a href="/logout" style="background: #dc2626; color: white; padding: 8px 15px; border-radius: 20px; text-decoration: none; margin-right: 10px;">🚪 خروج</a>
            </div>
        </div>
        
        <div class="stats">
            <div class="stat-card"><div class="stat-number">{{ stats.count }}</div><div>عدد الموظفين</div></div>
            <div class="stat-card"><div class="stat-number">{{ stats.total_payroll }} دج</div><div>كتلة الأجور</div></div>
            <div class="stat-card"><div class="stat-number">{{ stats.avg_salary }} دج</div><div>متوسط الراتب</div></div>
        </div>
        
        {% if is_admin %}
        <div class="card">
            <h3>➕ إضافة موظف جديد</h3>
            <form action="/add" method="post" class="form-row">
                <input type="text" name="name" placeholder="الاسم الكامل" required>
                <input type="text" name="position" placeholder="المنصب">
                <input type="number" name="salary" placeholder="الراتب" step="1000" required>
                <button type="submit">إضافة</button>
            </form>
        </div>
        {% endif %}
        
        <div class="card">
            <h3>📋 قائمة الموظفين</h3>
            <div style="overflow-x: auto;">
                <table>
                    <thead>
                        <tr>
                            <th>#</th>
                            <th>الاسم</th>
                            <th>المنصب</th>
                            <th>الراتب الأساسي</th>
                            <th>الراتب الصافي</th>
                            {% if is_admin %}<th></th>{% endif %}
                        </tr>
                    </thead>
                    <tbody>
                        {% for emp in employees %}
                        <tr>
                            <td>{{ loop.index }}</td>
                            <td>{{ emp.name }}</td>
                            <td>{{ emp.position or '-' }}</td>
                            <td>{{ "%.0f"|format(emp.salary) }} دج</td>
                            <td style="color: green; font-weight: bold;">{{ "%.0f"|format(emp.net) }} دج</td>
                            {% if is_admin %}
                            <td><a href="/delete/{{ emp.id }}" class="delete" onclick="return confirm('حذف؟')">🗑️ حذف</a></td>
                            {% endif %}
                        </tr>
                        {% else %}
                        <tr><td colspan="5" style="text-align: center;">لا يوجد موظفون بعد</td></tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
        
        <div style="text-align: center; margin-top: 20px; color: #666; font-size: 12px;">
            <p>© 2025 Rekab Amine | Genix Healthcare Payroll System</p>
        </div>
    </div>
</body>
</html>
'''

def calculate_net(salary):
    irg = salary * 0.15 if salary > 30000 else 0
    cnap = salary * 0.09
    return salary - irg - cnap

@app.route('/')
@login_required
def index():
    user = get_current_user()
    is_admin = user['role'] == 'admin'
    
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, name, position, salary FROM employees")
    rows = c.fetchall()
    conn.close()
    
    employees = []
    total_net = 0
    for row in rows:
        net = calculate_net(row['salary'])
        total_net += net
        employees.append({
            'id': row['id'],
            'name': row['name'],
            'position': row['position'],
            'salary': row['salary'],
            'net': net
        })
    
    stats = {
        'count': len(employees),
        'total_payroll': f"{total_net:,.0f}",
        'avg_salary': f"{total_net/len(employees):,.0f}" if employees else "0"
    }
    
    return render_template_string(MAIN_TEMPLATE, employees=employees, stats=stats, user=user, is_admin=is_admin)

@app.route('/add', methods=['POST'])
@admin_required
def add_employee():
    name = request.form['name']
    position = request.form.get('position', '')
    salary = float(request.form['salary'])
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO employees (name, position, salary) VALUES (?, ?, ?)", (name, position, salary))
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
