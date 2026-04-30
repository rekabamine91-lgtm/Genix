from flask import Flask, request, render_template_string, redirect, jsonify
import sqlite3
import os
from datetime import datetime
import hashlib
import secrets

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

# ==================== نظام الترخيص والعلامة المائية ====================

def is_licensed():
    try:
        with open('license.key', 'r') as f:
            key = f.read().strip()
        return key == "GENIX_LICENSED_2025"
    except:
        return False

def get_trial_days_left():
    trial_file = '.trial_info'
    if os.path.exists(trial_file):
        with open(trial_file, 'r') as f:
            first_run = datetime.fromisoformat(f.read())
            days_left = 30 - (datetime.now() - first_run).days
            return max(0, days_left)
    else:
        with open(trial_file, 'w') as f:
            f.write(datetime.now().isoformat())
        return 30

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
    except:
        pass
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

# ==================== دوال الحساب ====================

def calculate_irg(salary):
    if salary <= 30000: return 0
    elif salary <= 80000: return (salary - 30000) * 0.15
    elif salary <= 160000: return 7500 + (salary - 80000) * 0.25
    elif salary <= 320000: return 27500 + (salary - 160000) * 0.35
    else: return 83500 + (salary - 320000) * 0.40

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

# ==================== تحميل القالب ====================

with open('template.html', 'r', encoding='utf-8') as f:
    TEMPLATE = f.read()

# ==================== المسارات ====================

@app.route('/')
def index():
    licensed = is_licensed()
    is_trial = not licensed
    trial_days = get_trial_days_left() if is_trial else None
    
    if is_trial and trial_days <= 0:
        return "⛔ انتهت النسخة التجريبية للتواصل مع المطور", 403
    
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
                                  now=datetime.now().strftime('%Y-%m-%d %H:%M'),
                                  is_trial=is_trial,
                                  trial_days=trial_days)

@app.route('/add', methods=['POST'])
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
