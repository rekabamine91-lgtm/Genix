from flask import Flask, request, render_template_string, redirect, jsonify
import sqlite3
import os
from datetime import datetime
import secrets

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

# ---------- قاعدة البيانات ونفس دوال الحساب السابقة ----------
# (رجاءً احتفظ بكل دوال init_database, calculate_irg, calculate_salary_with_allowances
#  كما كانت سليمة في مشروعك، لأن الخطأ كان فقط في قالب HTML الطويل)
# ... ضع هنا كل الدوال السابقة التي كانت تعمل بكفاءة ...

# ---------- المسار الرئيسي بعد الفصل ----------
@app.route('/')
def index():
    # نفس الكود لجلب data من قاعدة البيانات...
    # ...
    # ثم قم بتمريرها إلى القالب المنفصل
    return render_template_string(TEMPLATE) # سنقوم بتحميل القالب من ملف خارجي

# السطر السحري: تحميل القالب من ملف خارجي مباشرة
with open('template.html', 'r', encoding='utf-8') as f:
    TEMPLATE = f.read()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
