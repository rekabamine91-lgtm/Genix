from flask import Flask, request, render_template_string, redirect, jsonify
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)

def init_db():
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
            ('أمين ركاب', 'مدير إداري', 30000),
            ('محمد أحمد', 'محاسب أجور', 24000),
            ('سارة علي', 'مساعد إداري', 21000),
        ]
        c.executemany("INSERT INTO employees (name, position, salary) VALUES (?, ?, ?)", sample_data)
    
    conn.commit()
    conn.close()

def calculate_net_salary(salary):
    irg = salary * 0.15 if salary > 30000 else 0
    cnap = salary * 0.09
    return salary - irg - cnap

TEMPLATE = '''
<!DOCTYPE html>
<html dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>نظام Genix لإدارة الأجور</title>
    <style>
        * { font-family: 'Tahoma', sans-serif; }
        body { background: #f0f2f5; padding: 20px; }
        .container { max-width: 1000px; margin: auto; }
        .header { background: linear-gradient(135deg, #1e3c72, #2a5298); color: white; padding: 20px; border-radius: 15px; margin-bottom: 20px; }
        h1 { margin: 0; }
        .stats { display: flex; gap: 15px; margin-bottom: 20px; }
        .stat-card { background: white; border-radius: 15px; padding: 15px; flex: 1; text-align: center; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .stat-card p { font-size: 1.8em; margin: 10px 0 0; font-weight: bold; color: #1e3c72; }
        .card { background: white; border-radius: 15px; padding: 20px; margin-bottom: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 12px; text-align: right; border-bottom: 1px solid #ddd; }
        th { background: #1e3c72; color: white; }
        input, button { padding: 10px; margin: 5px; border-radius: 8px; border: 1px solid #ddd; }
        button { background: #1e3c72; color: white; border: none; cursor: pointer; }
        button:hover { background: #2a5298; }
        .delete { color: red; text-decoration: none; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>💰 نظام Genix لإدارة الأجور</h1>
        </div>
        
        <div class="stats">
            <div class="stat-card">
                <h3>عدد الموظفين</h3>
                <p>{{ stats.count }}</p>
            </div>
            <div class="stat-card">
                <h3>كتلة الأجور</h3>
                <p>{{ stats.total_payroll }} دج</p>
            </div>
            <div class="stat-card">
                <h3>متوسط الراتب</h3>
                <p>{{ stats.avg_salary }} دج</p>
            </div>
        </div>
        
        <div class="card">
            <h3>➕ إضافة موظف</h3>
            <form action="/add" method="post">
                <input type="text" name="name" placeholder="الاسم" required>
                <input type="text" name="position" placeholder="المنصب">
                <input type="number" name="salary" placeholder="الراتب" step="1000" required>
                <button type="submit">إضافة</button>
            </form>
        </div>
        
        <div class="card">
            <h3>📋 قائمة الموظفين</h3>
            <table>
                <thead>
                    <tr>
                        <th>الاسم</th>
                        <th>المنصب</th>
                        <th>الراتب الأساسي</th>
                        <th>الراتب الصافي</th>
                        <th></th>
                    </tr>
                </thead>
                <tbody>
                    {% for emp in employees %}
                    <tr>
                        <td>{{ emp.name }}</td>
                        <td>{{ emp.position or '-' }}</td>
                        <td>{{ "%.2f"|format(emp.salary) }} دج</td>
                        <td style="color: green;">{{ "%.2f"|format(emp.net) }} دج</td>
                        <td><a href="/delete/{{ emp.id }}" class="delete" onclick="return confirm('حذف؟')">🗑️</a></td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>
'''

@app.route('/')
def index():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT id, name, position, salary FROM employees")
    rows = c.fetchall()
    conn.close()
    
    employees = []
    total = 0
    for row in rows:
        net = calculate_net_salary(row[3])
        total += net
        employees.append({'id': row[0], 'name': row[1], 'position': row[2], 'salary': row[3], 'net': net})
    
    stats = {
        'count': len(employees),
        'total_payroll': f"{total:,.0f}",
        'avg_salary': f"{total/len(employees):,.0f}" if employees else "0"
    }
    
    return render_template_string(TEMPLATE, employees=employees, stats=stats)

@app.route('/add', methods=['POST'])
def add_employee():
    name = request.form['name']
    position = request.form.get('position', '')
    salary = float(request.form['salary'])
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("INSERT INTO employees (name, position, salary) VALUES (?, ?, ?)", (name, position, salary))
    conn.commit()
    conn.close()
    return redirect('/')

@app.route('/delete/<int:emp_id>')
def delete_employee(emp_id):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("DELETE FROM employees WHERE id = ?", (emp_id,))
    conn.commit()
    conn.close()
    return redirect('/')

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
