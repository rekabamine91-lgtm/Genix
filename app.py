from flask import Flask, render_template
import csv
import os

app = Flask(__name__)

@app.route('/')
def dashboard():
    employees = []
    total_payroll = 0
    try:
        base_dir = os.path.abspath(os.path.dirname(__file__))
        file_path = os.path.join(base_dir, 'employees_sample.csv')
        with open(file_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                val = float(row.get('indice', 0))
                salary = val * 45
                total_payroll += salary
                row['net_salary'] = "{:,.2f}".format(salary)
                employees.append(row)
        stats = {
            'total_employees': len(employees),
            'total_payroll': "{:,.2f}".format(total_payroll),
            'avg_salary': "{:,.2f}".format(total_payroll/len(employees)) if employees else 0
        }
        return render_template('index.html', employees=employees, stats=stats)
    except Exception as e:
        return f"Error: {str(e)}"

if __name__ == "__main__":
    app.run()
  
