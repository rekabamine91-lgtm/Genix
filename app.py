from flask import Flask, request, render_template_string, redirect, jsonify
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)

# ==================== هيكل الرتب حسب الجريدة الرسمية ====================

# تعريف جميع الرتب والأسلاك حسب التصنيف الرسمي
GRADES_DATA = [
    # ===== السلك الطبي (الأطباء) - الترتيب حسب الأهمية =====
    {'name_ar': 'ممارس متخصص خارج الصنف (SUB 6)', 'name_fr': 'Praticien spécialiste hors classe', 'sector': 'صحة', 'category': 'طبيب مختص', 'base_salary': 204000, 'order': 1},
    {'name_ar': 'طبيب عام رئيس (SUB 2)', 'name_fr': 'Médecin généraliste principal', 'sector': 'صحة', 'category': 'طبيب عام', 'base_salary': 145000, 'order': 2},
    {'name_ar': 'ممارس طبي مختص', 'name_fr': 'Praticien médical spécialiste', 'sector': 'صحة', 'category': 'طبيب مختص', 'base_salary': 180000, 'order': 3},
    {'name_ar': 'ممارس طبي عام', 'name_fr': 'Praticien médical généraliste', 'sector': 'صحة', 'category': 'طبيب عام', 'base_salary': 120000, 'order': 4},
    {'name_ar': 'ممارس طبي مفتش', 'name_fr': 'Praticien médical inspecteur', 'sector': 'صحة', 'category': 'طبيب مفتش', 'base_salary': 160000, 'order': 5},
    {'name_ar': 'طبيب أسنان عام', 'name_fr': 'Chirurgien-dentiste généraliste', 'sector': 'صحة', 'category': 'طبيب أسنان', 'base_salary': 110000, 'order': 6},
    {'name_ar': 'صيدلي عام', 'name_fr': 'Pharmacien généraliste', 'sector': 'صحة', 'category': 'صيدلي', 'base_salary': 110000, 'order': 7},
    
    # ===== السلك شبه الطبي (الممرضون والقابلات) =====
    {'name_ar': 'ممرض ممتاز في الصحة العمومية (الدرجة 14)', 'name_fr': 'Infirmier senior en santé publique', 'sector': 'صحة', 'category': 'شبه طبي', 'base_salary': 85000, 'order': 8},
    {'name_ar': 'قابلة رئيسة في الصحة العمومية (الدرجة 15)', 'name_fr': 'Sage-femme principale en santé publique', 'sector': 'صحة', 'category': 'قابلة', 'base_salary': 102000, 'order': 9},
    {'name_ar': 'ممرض رئيسي', 'name_fr': 'Infirmier principal', 'sector': 'صحة', 'category': 'شبه طبي', 'base_salary': 75000, 'order': 10},
    {'name_ar': 'قابلة رئيسية', 'name_fr': 'Sage-femme principale', 'sector': 'صحة', 'category': 'قابلة', 'base_salary': 90000, 'order': 11},
    {'name_ar': 'ممرض', 'name_fr': 'Infirmier', 'sector': 'صحة', 'category': 'شبه طبي', 'base_salary': 60000, 'order': 12},
    {'name_ar': 'قابلة', 'name_fr': 'Sage-femme', 'sector': 'صحة', 'category': 'قابلة', 'base_salary': 70000, 'order': 13},
    {'name_ar': 'مساعد ممرض', 'name_fr': 'Aide-soignant', 'sector': 'صحة', 'category': 'شبه طبي', 'base_salary': 50000, 'order': 14},
    
    # ===== السلك التقني (البيولوجيون، الفيزيائيون، التخدير) =====
    {'name_ar': 'بيولوجي رئيس في الصحة العمومية (الدرجة 16)', 'name_fr': 'Biologiste principal en santé publique', 'sector': 'صحة', 'category': 'تقني', 'base_salary': 93000, 'order': 15},
    {'name_ar': 'فيزيائي طبي', 'name_fr': 'Physicien médical', 'sector': 'صحة', 'category': 'تقني', 'base_salary': 80000, 'order': 16},
    {'name_ar': 'مستخدم تخدير', 'name_fr': 'Utilisateur d\'anesthésie', 'sector': 'صحة', 'category': 'تقني', 'base_salary': 78000, 'order': 17},
    {'name_ar': 'نفساني عيادي', 'name_fr': 'Psychologue clinicien', 'sector': 'صحة', 'category': 'تقني', 'base_salary': 70000, 'order': 18},
    {'name_ar': 'أرطوفوني', 'name_fr': 'Orthophoniste', 'sector': 'صحة', 'category': 'تقني', 'base_salary': 68000, 'order': 19},
    {'name_ar': 'أستاذ تعليم للصحة العمومية', 'name_fr': 'Professeur d\'enseignement en santé publique', 'sector': 'صحة', 'category': 'تعليمي', 'base_salary': 85000, 'order': 20},
    
    # ===== السلك الإداري =====
    {'name_ar': 'مدير إدارة مركزية', 'name_fr': 'Directeur d\'administration centrale', 'sector': 'إدارة', 'category': 'إداري', 'base_salary': 150000, 'order': 21},
    {'name_ar': 'مدير دراسة', 'name_fr': 'Directeur d\'études', 'sector': 'إدارة', 'category': 'إداري', 'base_salary': 140000, 'order': 22},
    {'name_ar': 'رئيس مصلحة', 'name_fr': 'Chef de service', 'sector': 'إدارة', 'category': 'إداري', 'base_salary': 120000, 'order': 23},
    {'name_ar': 'محاسب رئيسي', 'name_fr': 'Comptable principal', 'sector': 'مالية', 'category': 'إداري', 'base_salary': 110000, 'order': 24},
    {'name_ar': 'متصرف', 'name_fr': 'Attaché', 'sector': 'إدارة', 'category': 'إداري', 'base_salary': 90000, 'order': 25},
    {'name_ar': 'كاتب إداري', 'name_fr': 'Rédacteur administratif', 'sector': 'إدارة', 'category': 'إداري', 'base_salary': 80000, 'order': 26},
    {'name_ar': 'عون إداري', 'name_fr': 'Agent administratif', 'sector': 'إدارة', 'category': 'إداري', 'base_salary': 60000, 'order': 27},
    
    # ===== السلك المهني والعمال =====
    {'name_ar': 'تقني سامي', 'name_fr': 'Technicien supérieur', 'sector': 'تقني', 'category': 'مهني', 'base_salary': 70000, 'order': 28},
    {'name_ar': 'عون مهني', 'name_fr': 'Agent professionnel', 'sector': 'مهني', 'category': 'مهني', 'base_salary': 50000, 'order': 29},
    {'name_ar': 'عامل مهني', 'name_fr': 'Travailleur professionnel', 'sector': 'مهني', 'category': 'عامل', 'base_salary': 45000, 'order': 30},
    {'name_ar': 'عون خدمة', 'name_fr': 'Agent de service', 'sector': 'خدمات', 'category': 'خدمة', 'base_salary': 40000, 'order': 31},
]

# ==================== المنح حسب الجريدة الرسمية ====================

ALLOWANCES_DATA = [
    {'code': '101', 'name_ar': 'منحة الخبرة المهنية', 'name_fr': "Prime d'expérience professionnelle", 'amount': 0.15, 'is_percentage': True},
    {'code': '102', 'name_ar': 'منحة السكن', 'name_fr': 'Prime de logement', 'amount': 5000, 'is_percentage': False},
    {'code': '103', 'name_ar': 'منحة النقل', 'name_fr': 'Prime de transport', 'amount': 3000, 'is_percentage': False},
    {'code': '104', 'name_ar': 'منحة خطر العدوى', 'name_fr': "Prime d'infection", 'amount': 8000, 'is_percentage': False},
    {'code': '105', 'name_ar': 'منحة المناوبة', 'name_fr': 'Prime de garde', 'amount': 5000, 'is_percentage': False},
    {'code': '106', 'name_ar': 'منحة التعويض عن الإقليم', 'name_fr': "Prime d'éloignement", 'amount': 0.10, 'is_percentage': True},
    {'code': '107', 'name_ar': 'منحة المردود', 'name_fr': 'Prime de rendement', 'amount': 0.08, 'is_percentage': True},
    {'code': '108', 'name_ar': 'تعويض التوثيق', 'name_fr': "Indemnité de documentation", 'amount': 12000, 'is_percentage': False},
    {'code': '109', 'name_ar': 'منحة تحسين الأداء (ثلاثية)', 'name_fr': "Prime d'amélioration de performance", 'amount': 30000, 'is_percentage': False},
]

# ==================== دوال قاعدة البيانات ====================

def init_advanced_database():
    """إنشاء قاعدة البيانات مع جميع الجداول والبيانات"""
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    
    # 1. جدول الرتب والأسلاك
    c.execute('''
        CREATE TABLE IF NOT EXISTS grades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name_ar TEXT NOT NULL,
            name_fr TEXT NOT NULL,
            sector TEXT,
            category TEXT,
            base_salary REAL,
            "order" INTEGER
        )
    ''')
    
    # 2. جدول المنح
    c.execute('''
        CREATE TABLE IF NOT EXISTS allowances (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE,
            name_ar TEXT,
            name_fr TEXT,
            amount REAL,
            is_percentage BOOLEAN DEFAULT 0
        )
    ''')
    
    # 3. جدول الموظفين
    c.execute('''
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            position TEXT,
            grade_id INTEGER,
            base_salary REAL,
            hire_date DATE,
            status TEXT DEFAULT 'actif',
            FOREIGN KEY (grade_id) REFERENCES grades(id)
        )
    ''')
    
    # 4. جدول الرواتب المحسوبة
    c.execute('''
        CREATE TABLE IF NOT EXISTS salaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER,
            month INTEGER,
            year INTEGER,
            grade_id INTEGER,
            base_salary REAL,
            total_allowances REAL,
            gross_salary REAL,
            irg REAL,
            cnap REAL,
            net_salary REAL,
            FOREIGN KEY (employee_id) REFERENCES employees(id)
        )
    ''')
    
    # إضافة الرتب حسب الجريدة الرسمية (مرتبة حسب order)
    for grade in GRADES_DATA:
        c.execute('''
            INSERT OR IGNORE INTO grades (name_ar, name_fr, sector, category, base_salary, "order")
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (grade['name_ar'], grade['name_fr'], grade['sector'], grade['category'], grade['base_salary'], grade['order']))
    
    # إضافة المنح حسب الجريدة الرسمية
    for allowance in ALLOWANCES_DATA:
        c.execute('''
            INSERT OR IGNORE INTO allowances (code, name_ar, name_fr, amount, is_percentage)
            VALUES (?, ?, ?, ?, ?)
        ''', (allowance['code'], allowance['name_ar'], allowance['name_fr'], allowance['amount'], allowance['is_percentage']))
    
    conn.commit()
    conn.close()

def get_db():
    """الاتصال بقاعدة البيانات"""
    try:
        init_advanced_database()
    except:
        pass
    
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

# ==================== دوال الحساب ====================

def calculate_irg(salary):
    """حساب IRG حسب الجدول الضريبي الجزائري"""
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
    """حساب الراتب الصافي مع جميع المنح"""
    conn = get_db()
    c = conn.cursor()
    
    # جلب جميع المنح
    c.execute("SELECT amount, is_percentage FROM allowances")
    allowances = c.fetchall()
    conn.close()
    
    # حساب مجموع المنح
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

# ==================== قالب HTML الرئيسي (محدث) ====================

TEMPLATE = '''
<!DOCTYPE html>
<html dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>نظام Genix - إدارة أجور قطاع الصحة</title>
    <style>
        * { font-family: 'Tahoma', 'Segoe UI', sans-serif; margin: 0; padding: 0; box-sizing: border-box; }
        body { background: #f0f2f5; padding: 20px; }
        .container { max-width: 1400px; margin: auto; }
        .header { background: linear-gradient(135deg, #1e3c72, #2a5298); color: white; padding: 20px; border-radius: 15px; margin-bottom: 20px; }
        .header h1 { margin: 0; font-size: 1.8em; }
        .badge { background: #ff9800; display: inline-block; padding: 5px 15px; border-radius: 20px; font-size: 12px; margin-top: 10px; }
        .stats { display: flex; gap: 15px; margin-bottom: 20px; flex-wrap: wrap; }
        .stat-card { background: white; border-radius: 15px; padding: 20px; flex: 1; min-width: 150px; text-align: center; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .stat-card h3 { margin: 0; color: #1e3c72; font-size: 14px; }
        .stat-card p { font-size: 2em; margin: 10px 0 0; font-weight: bold; color: #1e3c72; }
        .card { background: white; border-radius: 15px; padding: 20px; margin-bottom: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .card h3 { margin: 0 0 15px; color: #1e3c72; border-right: 4px solid #1e3c72; padding-right: 10px; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 12px; text-align: right; border-bottom: 1px solid #ddd; }
        th { background: #1e3c72; color: white; border-radius: 8px; }
        input, select { padding: 10px; margin: 5px; border-radius: 8px; border: 1px solid #ddd; width: 200px; }
        button { background: #1e3c72; color: white; border: none; padding: 10px 20px; border-radius: 8px; cursor: pointer; }
        button:hover { background: #2a5298; }
        .delete { color: red; text-decoration: none; }
        .form-row { display: flex; gap: 10px; flex-wrap: wrap; align-items: end; margin-bottom: 20px; }
        .sector-tag { display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 11px; margin-right: 5px; }
        .sector-sante { background: #e8f5e9; color: #2e7d32; }
        .sector-admin { background: #e3f2fd; color: #1565c0; }
        .sector-technique { background: #fff3e0; color: #e65100; }
        @media (max-width: 768px) {
            .stats { flex-direction: column; }
            input, select { width: 100%; }
            .form-row { flex-direction: column; }
            table { font-size: 12px; }
            th, td { padding: 8px; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>💰 نظام Genix لإدارة أجور قطاع الصحة</h1>
            <div class="badge">🇩🇿 متوافق مع الجريدة الرسمية (مرسوم 24-416)</div>
        </div>
        
        <div class="stats">
            <div class="stat-card">
                <h3>👥 عدد الموظفين</h3>
                <p>{{ stats.count }}</p>
            </div>
            <div class="stat-card">
                <h3>💰 كتلة الأجور</h3>
                <p>{{ stats.total_payroll }} دج</p>
            </div>
            <div class="stat-card">
                <h3>📊 متوسط الراتب</h3>
                <p>{{ stats.avg_salary }} دج</p>
            </div>
        </div>
        
        <div class="card">
            <h3>➕ إضافة موظف جديد</h3>
            <form action="/add" method="post" class="form-row">
                <input type="text" name="name" placeholder="الاسم الكامل" required>
                <input type="text" name="position" placeholder="المنصب">
                <select name="grade_id" required>
                    <option value="">اختر الرتبة</option>
                    <optgroup label="🏥 السلك الطبي (الأطباء)">
                        {% for grade in grades if grade.sector == 'صحة' and grade.category in ['طبيب مختص', 'طبيب عام', 'طبيب مفتش', 'طبيب أسنان', 'صيدلي'] %}
                        <option value="{{ grade.id }}">{{ grade.name_ar }} - {{ "%.0f"|format(grade.base_salary) }} دج</option>
                        {% endfor %}
                    </optgroup>
                    <optgroup label="🩺 السلك شبه الطبي (ممرضون وقابلات)">
                        {% for grade in grades if grade.sector == 'صحة' and grade.category in ['شبه طبي', 'قابلة'] %}
                        <option value="{{ grade.id }}">{{ grade.name_ar }} - {{ "%.0f"|format(grade.base_salary) }} دج</option>
                        {% endfor %}
                    </optgroup>
                    <optgroup label="🔬 السلك التقني (بيولوجيون، فيزيائيون)">
                        {% for grade in grades if grade.sector == 'صحة' and grade.category in ['تقني', 'تعليمي'] %}
                        <option value="{{ grade.id }}">{{ grade.name_ar }} - {{ "%.0f"|format(grade.base_salary) }} دج</option>
                        {% endfor %}
                    </optgroup>
                    <optgroup label="📋 السلك الإداري">
                        {% for grade in grades if grade.sector == 'إدارة' or grade.sector == 'مالية' %}
                        <option value="{{ grade.id }}">{{ grade.name_ar }} - {{ "%.0f"|format(grade.base_salary) }} دج</option>
                        {% endfor %}
                    </optgroup>
                    <optgroup label="🔧 السلك المهني والعمال">
                        {% for grade in grades if grade.sector in ['تقني', 'مهني', 'خدمات'] and grade.category not in ['تقني', 'تعليمي'] %}
                        <option value="{{ grade.id }}">{{ grade.name_ar }} - {{ "%.0f"|format(grade.base_salary) }} دج</option>
                        {% endfor %}
                    </optgroup>
                </select>
                <button type="submit">إضافة</button>
            </form>
        </div>
        
        <div class="card">
            <h3>📋 قائمة الموظفين</h3>
            <div style="overflow-x: auto;">
                <table class="table">
                    <thead>
                        <tr>
                            <th>#</th>
                            <th>الاسم الكامل</th>
                            <th>المنصب</th>
                            <th>الرتبة</th>
                            <th>القطاع</th>
                            <th>الراتب الأساسي</th>
                            <th>الراتب الصافي</th>
                            <th>الإجراءات</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for emp in employees %}
                        <tr>
                            <td>{{ loop.index }}</td>
                            <td>{{ emp.name }}</td>
                            <td>{{ emp.position or '-' }}</td>
                            <td>{{ emp.grade_name }}</td>
                            <td>
                                {% if emp.sector == 'صحة' %}
                                <span class="sector-tag sector-sante">🏥 صحة</span>
                                {% elif emp.sector == 'إدارة' %}
                                <span class="sector-tag sector-admin">📋 إدارة</span>
                                {% else %}
                                <span class="sector-tag sector-technique">🔧 تقني</span>
                                {% endif %}
                            </td>
                            <td>{{ "%.0f"|format(emp.base_salary) }} دج</td>
                            <td style="color: green; font-weight: bold;">{{ "%.0f"|format(emp.net) }} دج</td>
                            <td><a href="/delete/{{ emp.id }}" class="delete" onclick="return confirm('هل أنت متأكد؟')">🗑️ حذف</a></td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
        
        <div class="info-text" style="margin-top: 20px; padding: 15px; background: #e3f2fd; border-radius: 10px;">
            <p>📌 <strong>معلومات النظام:</strong></p>
            <p>✓ متوافق مع آخر تحديثات الجريدة الرسمية (مرسوم رقم 24-416 المؤرخ في 28 ديسمبر 2024)</p>
            <p>✓ يشمل جميع أسلاك قطاع الصحة: الأطباء، شبه الطبيين، التقنيين، الإداريين، والعمال المهنيين</p>
            <p>✓ المنح المطبقة: خبرة 15%، سكن 5000 دج، نقل 3000 دج، خطر العدوى 8000 دج، مناوبة 5000 دج، توثيق 12000 دج</p>
            <p>✓ ضريبة IRG حسب الشرائح الرسمية + CNAS 9%</p>
        </div>
    </div>
</body>
</html>
'''

# ==================== المسارات (Routes) ====================

@app.route('/')
def index():
    conn = get_db()
    c = conn.cursor()
    
    # جلب الموظفين مع الرتبة والقطاع
    c.execute('''
        SELECT e.id, e.name, e.position, e.base_salary, g.name_ar, g.sector, g.base_salary as grade_salary
        FROM employees e
        JOIN grades g ON e.grade_id = g.id
        ORDER BY g."order"
    ''')
    rows = c.fetchall()
    
    employees = []
    total_net = 0
    
    for row in rows:
        # استخدام راتب الرتبة إذا لم يكن محدداً
        salary = row['base_salary'] if row['base_salary'] and row['base_salary'] > 0 else row['grade_salary']
        salary_result = calculate_salary_with_allowances(salary)
        net = salary_result['net_salary']
        total_net += net
        
        employees.append({
            'id': row['id'],
            'name': row['name'],
            'position': row['position'],
            'grade_name': row['name_ar'],
            'sector': row['sector'],
            'base_salary': salary,
            'net': net
        })
    
    # جلب جميع الرتب للقائمة المنسدلة
    c.execute("SELECT id, name_ar, sector, category, base_salary FROM grades ORDER BY \"order\"")
    grades = [{'id': row['id'], 'name_ar': row['name_ar'], 'sector': row['sector'], 'category': row['category'], 'base_salary': row['base_salary']} for row in c.fetchall()]
    
    # إحصائيات
    stats = {
        'count': len(employees),
        'total_payroll': f"{total_net:,.0f}",
        'avg_salary': f"{total_net/len(employees):,.0f}" if employees else "0"
    }
    
    conn.close()
    
    return render_template_string(TEMPLATE, employees=employees, stats=stats, grades=grades)

@app.route('/add', methods=['POST'])
def add_employee():
    name = request.form['name']
    position = request.form.get('position', '')
    grade_id = int(request.form['grade_id']) if request.form['grade_id'] else None
    
    conn = get_db()
    c = conn.cursor()
    
    # جلب الراتب الأساسي من الرتبة
    if grade_id:
        c.execute("SELECT base_salary FROM grades WHERE id = ?", (grade_id,))
        grade = c.fetchone()
        base_salary = grade['base_salary'] if grade else 0
    else:
        base_salary = 0
    
    c.execute('''
        INSERT INTO employees (name, position, grade_id, base_salary, hire_date)
        VALUES (?, ?, ?, ?, ?)
    ''', (name, position, grade_id, base_salary, datetime.now().strftime('%Y-%m-%d')))
    
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
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

# ==================== التشغيل ====================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
