from flask import Flask, request, render_template_string, redirect, jsonify
import sqlite3
import os
from datetime import datetime, timedelta
import hashlib
import secrets

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

# ==================== نظام العلامة المائية والترخيص ====================

def is_licensed():
    """التحقق من وجود ترخيص صالح"""
    try:
        with open('license.key', 'r') as f:
            key = f.read().strip()
        # تحقق بسيط - يمكن تطويره لاحقاً
        return key == "GENIX_LICENSED_2025"
    except:
        return False

def get_trial_days_left():
    """حساب الأيام المتبقية في النسخة التجريبية"""
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

# ==================== هيكل الرتب حسب الجريدة الرسمية ====================

GRADES_DATA = [
    # ===== السلك الطبي (الأطباء) =====
    {'name_ar': 'ممارس متخصص خارج الصنف (SUB 6)', 'name_fr': 'Praticien spécialiste hors classe', 'sector': 'صحة', 'category': 'طبيب مختص', 'base_salary': 204000, 'order': 1, 'icon': '🩺'},
    {'name_ar': 'طبيب عام رئيس (SUB 2)', 'name_fr': 'Médecin généraliste principal', 'sector': 'صحة', 'category': 'طبيب عام', 'base_salary': 145000, 'order': 2, 'icon': '👨‍⚕️'},
    {'name_ar': 'ممارس طبي مختص', 'name_fr': 'Praticien médical spécialiste', 'sector': 'صحة', 'category': 'طبيب مختص', 'base_salary': 180000, 'order': 3, 'icon': '🩺'},
    {'name_ar': 'ممارس طبي عام', 'name_fr': 'Praticien médical généraliste', 'sector': 'صحة', 'category': 'طبيب عام', 'base_salary': 120000, 'order': 4, 'icon': '👨‍⚕️'},
    {'name_ar': 'طبيب أسنان عام', 'name_fr': 'Chirurgien-dentiste généraliste', 'sector': 'صحة', 'category': 'طبيب أسنان', 'base_salary': 110000, 'order': 5, 'icon': '🦷'},
    {'name_ar': 'صيدلي عام', 'name_fr': 'Pharmacien généraliste', 'sector': 'صحة', 'category': 'صيدلي', 'base_salary': 110000, 'order': 6, 'icon': '💊'},
    
    # ===== السلك شبه الطبي =====
    {'name_ar': 'ممرض ممتاز في الصحة العمومية', 'name_fr': 'Infirmier senior en santé publique', 'sector': 'صحة', 'category': 'شبه طبي', 'base_salary': 85000, 'order': 7, 'icon': '💉'},
    {'name_ar': 'قابلة رئيسة في الصحة العمومية', 'name_fr': 'Sage-femme principale en santé publique', 'sector': 'صحة', 'category': 'قابلة', 'base_salary': 102000, 'order': 8, 'icon': '👶'},
    {'name_ar': 'ممرض رئيسي', 'name_fr': 'Infirmier principal', 'sector': 'صحة', 'category': 'شبه طبي', 'base_salary': 75000, 'order': 9, 'icon': '💉'},
    {'name_ar': 'قابلة رئيسية', 'name_fr': 'Sage-femme principale', 'sector': 'صحة', 'category': 'قابلة', 'base_salary': 90000, 'order': 10, 'icon': '👶'},
    {'name_ar': 'ممرض', 'name_fr': 'Infirmier', 'sector': 'صحة', 'category': 'شبه طبي', 'base_salary': 60000, 'order': 11, 'icon': '💉'},
    {'name_ar': 'مساعد ممرض', 'name_fr': 'Aide-soignant', 'sector': 'صحة', 'category': 'شبه طبي', 'base_salary': 50000, 'order': 12, 'icon': '🩹'},
    
    # ===== السلك التقني =====
    {'name_ar': 'بيولوجي رئيس في الصحة العمومية', 'name_fr': 'Biologiste principal en santé publique', 'sector': 'صحة', 'category': 'تقني', 'base_salary': 93000, 'order': 13, 'icon': '🔬'},
    {'name_ar': 'فيزيائي طبي', 'name_fr': 'Physicien médical', 'sector': 'صحة', 'category': 'تقني', 'base_salary': 80000, 'order': 14, 'icon': '⚛️'},
    {'name_ar': 'مستخدم تخدير', 'name_fr': "Utilisateur d'anesthésie", 'sector': 'صحة', 'category': 'تقني', 'base_salary': 78000, 'order': 15, 'icon': '😷'},
    {'name_ar': 'نفساني عيادي', 'name_fr': 'Psychologue clinicien', 'sector': 'صحة', 'category': 'تقني', 'base_salary': 70000, 'order': 16, 'icon': '🧠'},
    
    # ===== السلك الإداري =====
    {'name_ar': 'مدير إدارة مركزية', 'name_fr': "Directeur d'administration centrale", 'sector': 'إدارة', 'category': 'إداري', 'base_salary': 150000, 'order': 17, 'icon': '👔'},
    {'name_ar': 'رئيس مصلحة', 'name_fr': 'Chef de service', 'sector': 'إدارة', 'category': 'إداري', 'base_salary': 120000, 'order': 18, 'icon': '📋'},
    {'name_ar': 'محاسب رئيسي', 'name_fr': 'Comptable principal', 'sector': 'مالية', 'category': 'إداري', 'base_salary': 110000, 'order': 19, 'icon': '💰'},
    {'name_ar': 'متصرف', 'name_fr': 'Attaché', 'sector': 'إدارة', 'category': 'إداري', 'base_salary': 90000, 'order': 20, 'icon': '📁'},
    {'name_ar': 'كاتب إداري', 'name_fr': 'Rédacteur administratif', 'sector': 'إدارة', 'category': 'إداري', 'base_salary': 80000, 'order': 21, 'icon': '✍️'},
    {'name_ar': 'عون إداري', 'name_fr': 'Agent administratif', 'sector': 'إدارة', 'category': 'إداري', 'base_salary': 60000, 'order': 22, 'icon': '🖥️'},
    
    # ===== السلك المهني =====
    {'name_ar': 'تقني سامي', 'name_fr': 'Technicien supérieur', 'sector': 'تقني', 'category': 'مهني', 'base_salary': 70000, 'order': 23, 'icon': '🔧'},
    {'name_ar': 'عون مهني', 'name_fr': 'Agent professionnel', 'sector': 'مهني', 'category': 'مهني', 'base_salary': 50000, 'order': 24, 'icon': '🛠️'},
    {'name_ar': 'عامل مهني', 'name_fr': 'Travailleur professionnel', 'sector': 'مهني', 'category': 'عامل', 'base_salary': 45000, 'order': 25, 'icon': '🏗️'},
    {'name_ar': 'عون خدمة', 'name_fr': 'Agent de service', 'sector': 'خدمات', 'category': 'خدمة', 'base_salary': 40000, 'order': 26, 'icon': '🧹'},
]

ALLOWANCES_DATA = [
    {'code': '101', 'name_ar': 'منحة الخبرة المهنية', 'name_fr': "Prime d'expérience", 'amount': 0.15, 'is_percentage': True},
    {'code': '102', 'name_ar': 'منحة السكن', 'name_fr': 'Prime de logement', 'amount': 5000, 'is_percentage': False},
    {'code': '103', 'name_ar': 'منحة النقل', 'name_fr': 'Prime de transport', 'amount': 3000, 'is_percentage': False},
    {'code': '104', 'name_ar': 'منحة خطر العدوى', 'name_fr': "Prime d'infection", 'amount': 8000, 'is_percentage': False},
    {'code': '105', 'name_ar': 'منحة المناوبة', 'name_fr': 'Prime de garde', 'amount': 5000, 'is_percentage': False},
    {'code': '106', 'name_ar': 'منحة التوثيق', 'name_fr': "Indemnité de documentation", 'amount': 12000, 'is_percentage': False},
]

# ==================== دوال قاعدة البيانات ====================

def init_database():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS grades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name_ar TEXT, name_fr TEXT, sector TEXT, category TEXT,
            base_salary REAL, "order" INTEGER, icon TEXT
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS allowances (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT, name_ar TEXT, name_fr TEXT, amount REAL, is_percentage BOOLEAN
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT, position TEXT, grade_id INTEGER,
            base_salary REAL, hire_date DATE, status TEXT DEFAULT 'actif'
        )
    ''')
    
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

# ==================== قالب HTML مع العلامة المائية ====================

TEMPLATE = '''
<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>نظام Genix | إدارة أجور قطاع الصحة</title>
    <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.7.2/css/all.min.css">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Cairo', sans-serif;
        }

        /* خلفية متحركة */
        body {
            min-height: 100vh;
            background: linear-gradient(135deg, #0f2027, #203a43, #2c5364);
            background-size: 400% 400%;
            animation: gradientBG 15s ease infinite;
            padding: 20px;
            position: relative;
        }

        @keyframes gradientBG {
            0% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
            100% { background-position: 0% 50%; }
        }

        /* العلامة المائية للنسخة التجريبية */
        {% if is_trial %}
        body::before {
            content: "⚠️ نسخة تجريبية - للبيع ⚠️";
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%) rotate(-25deg);
            font-size: 3.5rem;
            font-weight: bold;
            color: rgba(255, 255, 255, 0.08);
            white-space: nowrap;
            pointer-events: none;
            z-index: 999;
            letter-spacing: 5px;
            font-family: 'Cairo', sans-serif;
            text-shadow: 0 0 10px rgba(0,0,0,0.3);
        }
        {% endif %}

        /* شريط التحذير للتجريبي */
        .trial-banner {
            background: linear-gradient(95deg, #dc2626, #b91c1c);
            color: white;
            padding: 12px 20px;
            text-align: center;
            border-radius: 50px;
            margin-bottom: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 10px;
        }

        .licensed-banner {
            background: linear-gradient(95deg, #059669, #047857);
            color: white;
            padding: 12px 20px;
            text-align: center;
            border-radius: 50px;
            margin-bottom: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 10px;
        }

        .buy-btn {
            background: white;
            color: #b91c1c;
            padding: 6px 18px;
            border-radius: 40px;
            text-decoration: none;
            font-weight: bold;
            transition: all 0.2s;
        }

        .buy-btn:hover {
            transform: scale(1.05);
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        }

        /* بقية التنسيقات (نفس السابق) */
        .glass-card {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 28px;
            box-shadow: 0 25px 45px rgba(0, 0, 0, 0.2);
            transition: all 0.3s ease;
        }

        .stat-card {
            background: linear-gradient(145deg, #ffffff, #f8fafc);
            border-radius: 28px;
            padding: 1.5rem;
            text-align: center;
            transition: all 0.2s ease;
            box-shadow: 0 8px 20px rgba(0,0,0,0.05);
        }

        .stat-card i {
            font-size: 2.8rem;
            background: linear-gradient(145deg, #1e3c72, #2a5298);
            -webkit-background-clip: text;
            background-clip: text;
            color: transparent;
        }

        .stat-number {
            font-size: 2.5rem;
            font-weight: 800;
            color: #0b2b44;
        }

        .custom-table {
            width: 100%;
            border-collapse: separate;
            border-spacing: 0 12px;
        }

        .custom-table thead th {
            background: #1e2f47;
            color: white;
            padding: 16px 12px;
            font-weight: 600;
        }

        .custom-table tbody tr {
            background: white;
            border-radius: 20px;
            transition: all 0.2s;
        }

        .custom-table tbody tr:hover {
            transform: scale(1.01);
            background: #fefef7;
            box-shadow: 0 10px 25px -5px rgba(0,0,0,0.1);
        }

        .btn-primary-custom {
            background: linear-gradient(95deg, #1e3c72, #2b4b7a);
            border: none;
            padding: 0.7rem 1.5rem;
            border-radius: 40px;
            font-weight: 600;
            color: white;
        }

        .delete-btn {
            background: #fee2e2;
            color: #b91c1c;
            padding: 8px 14px;
            border-radius: 40px;
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }

        .badge-sector {
            background: #eef2ff;
            padding: 4px 12px;
            border-radius: 100px;
            font-size: 0.75rem;
        }

        @media (max-width: 768px) {
            .stat-number { font-size: 1.6rem; }
            .custom-table thead { display: none; }
            .custom-table tbody tr { display: block; margin-bottom: 20px; }
            .custom-table td { display: flex; justify-content: space-between; padding: 10px; }
            .custom-table td::before { content: attr(data-label); font-weight: bold; }
        }
    </style>
</head>
<body>

<div class="container" style="max-width: 1400px; margin: auto;">
    
    {% if is_trial %}
    <div class="trial-banner">
        <span><i class="fas fa-hourglass-half"></i> ⚠️ نسخة تجريبية - متبقي {{ trial_days }} يوماً</span>
        <a href="#" class="buy-btn" onclick="alert('للشراء: اتصل بالمطور على 05XX XX XX XX')"><i class="fas fa-shopping-cart"></i> شراء الترخيص</a>
    </div>
    {% else %}
    <div class="licensed-banner">
        <span><i class="fas fa-check-circle"></i> ✅ نسخة مرخصة - نظام رسمي</span>
        <span><i class="fas fa-shield-alt"></i> الدعم الفني متوفر</span>
    </div>
    {% endif %}

    <!-- رأس الصفحة -->
    <div class="glass-card p-4 mb-5" style="background: rgba(255,255,255,0.97);">
        <div class="d-flex flex-wrap justify-content-between align-items-center">
            <div>
                <h1 style="font-weight: 800; background: linear-gradient(145deg, #1e3c72, #0f2b48); -webkit-background-clip: text; background-clip: text; color: transparent;">
                    <i class="fas fa-microscope"></i> نظام Genix
                </h1>
                <p class="text-muted mt-2"><i class="fas fa-calendar-check"></i> متوافق مع الجريدة الرسمية (مرسوم 24-416) – قطاع الصحة</p>
            </div>
            <div><span class="badge bg-dark rounded-pill px-3 py-2">{{ now }}</span></div>
        </div>
    </div>

    <!-- بطاقات إحصائية -->
    <div class="row g-4 mb-5">
        <div class="col-md-4">
            <div class="stat-card">
                <i class="fas fa-users"></i>
                <h5 class="mt-2 text-muted">عدد المنتسبين</h5>
                <p class="stat-number">{{ stats.count }}</p>
            </div>
        </div>
        <div class="col-md-4">
            <div class="stat-card">
                <i class="fas fa-money-bill-wave"></i>
                <h5 class="mt-2 text-muted">كتلة الأجور الإجمالية</h5>
                <p class="stat-number">{{ stats.total_payroll }} <small>دج</small></p>
            </div>
        </div>
        <div class="col-md-4">
            <div class="stat-card">
                <i class="fas fa-chart-line"></i>
                <h5 class="mt-2 text-muted">متوسط الدخل الصافي</h5>
                <p class="stat-number">{{ stats.avg_salary }} <small>دج</small></p>
            </div>
        </div>
    </div>

    <!-- إضافة موظف -->
    <div class="glass-card p-4 mb-5">
        <h4 class="mb-3 fw-bold"><i class="fas fa-user-plus"></i> إضافة موظف جديد</h4>
        <form action="/add" method="post" class="row g-3">
            <div class="col-md-3">
                <input type="text" name="name" class="form-control" placeholder="الاسم الرباعي" required>
            </div>
            <div class="col-md-3">
                <input type="text" name="position" class="form-control" placeholder="المنصب">
            </div>
            <div class="col-md-4">
                <select name="grade_id" class="form-control" required>
                    <option value="">-- اختر الرتبة --</option>
                    {% for grade in grades %}
                    <option value="{{ grade.id }}">{{ grade.icon }} {{ grade.name_ar }} ({{ "%.0f"|format(grade.base_salary) }} دج)</option>
                    {% endfor %}
                </select>
            </div>
            <div class="col-md-2">
                <button type="submit" class="btn btn-primary-custom w-100"><i class="fas fa-save"></i> تسجيل</button>
            </div>
        </form>
    </div>

    <!-- جدول الموظفين -->
    <div class="glass-card p-4">
        <h4 class="mb-3 fw-bold"><i class="fas fa-list-ul"></i> قائمة الكوادر الصحية والإدارية</h4>
        <div style="overflow-x: auto;">
            <table class="custom-table">
                <thead>
                    <tr><th>#</th><th>الاسم</th><th>الرتبة</th><th>القطاع</th><th>الأجر القاعدي</th><th>الأجر الصافي</th><th></th></tr>
                </thead>
                <tbody>
                    {% for emp in employees %}
                    <tr>
                        <td data-label="#">{{ loop.index }}</td>
                        <td data-label="الاسم">{{ emp.name }}</td>
                        <td data-label="الرتبة">{{ emp.grade_name }}</td>
                        <td data-label="القطاع"><span class="badge-sector">{{ emp.icon }} {{ emp.sector }}</span></td>
                        <td data-label="الأجر القاعدي">{{ "%.0f"|format(emp.base_salary) }} دج</td>
                        <td data-label="الأجر الصافي" style="color:#15803d; font-weight:800;">{{ "%.0f"|format(emp.net) }} دج</td>
                        <td data-label=""><a href="/delete/{{ emp.id }}" class="delete-btn" onclick="return confirm('حذف الموظف؟')"><i class="fas fa-trash-alt"></i> حذف</a></td>
                    </tr>
                    {% else %}
                    <tr><td colspan="7" class="text-center text-muted">لا يوجد موظفون بعد</td></tr>
               
