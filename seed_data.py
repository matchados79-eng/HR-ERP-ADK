import sys
import os
from datetime import datetime, date, timedelta

sys.path.append(os.path.dirname(__file__))

import database as db
from saudi_hr_engine import SaudiHREngine

def seed_database():
    print("Initializing Database Schema...")
    db.init_db()
    
    # Check if already seeded
    existing_emps = db.query_all("SELECT COUNT(*) as cnt FROM employees")
    if existing_emps and existing_emps[0]["cnt"] > 0:
        print("Database already contains employees. Skipping seeder.")
        return
        
    print("Seeding Departments...")
    depts = [
        ("Engineering & Technology", "ENG", "Eng. Tariq Al-Mansoor", 450000.0),
        ("Human Resources & Admin", "HR", "Sara Al-Dosari", 200000.0),
        ("Finance & Accounting", "FIN", "Fahad Al-Qahtani", 300000.0),
        ("Operations & Supply Chain", "OPS", "John Smith", 500000.0),
        ("Executive Office", "EXEC", "Dr. Khalid Al-Ghamdi", 750000.0)
    ]
    dept_ids = {}
    for name, code, mgr, budget in depts:
        d_id = db.execute_cmd(
            "INSERT INTO departments (name, code, manager_name, budget) VALUES (?, ?, ?, ?)",
            (name, code, mgr, budget)
        )
        dept_ids[code] = d_id

    print("Seeding Employee Directory (Saudi & Expat profiles)...")
    employees = [
        {
            "emp_code": "EMP-001",
            "first_name": "Mohammed",
            "last_name": "Al-Otaibi",
            "arabic_name": "محمد العتيبي",
            "email": "m.otaibi@alamal-ksa.com",
            "phone": "+966501234567",
            "national_id_iqama": "1098765432", # Saudi National ID starts with 1
            "nationality": "Saudi Arabia",
            "gender": "Male",
            "is_saudi": 1,
            "dob": "1988-04-12",
            "department_id": dept_ids["ENG"],
            "designation": "Lead Software Architect",
            "hire_date": "2019-03-01",
            "contract_type": "Indefinite",
            "contract_end_date": None,
            "iqama_expiry_date": "2028-12-31",
            "passport_number": "A9841029",
            "passport_expiry_date": "2029-05-15",
            "bank_name": "Al Rajhi Bank",
            "iban": "SA0380000000608010167519",
            "basic_salary": 18000.0,
            "housing_allowance": 4500.0,
            "transport_allowance": 1500.0,
            "other_allowances": 1000.0,
            "gosi_number": "304918201",
            "status": "Active"
        },
        {
            "emp_code": "EMP-002",
            "first_name": "Sara",
            "last_name": "Al-Dosari",
            "arabic_name": "سارة الدوسري",
            "email": "sara.dosari@alamal-ksa.com",
            "phone": "+966559876543",
            "national_id_iqama": "1087654321",
            "nationality": "Saudi Arabia",
            "gender": "Female",
            "is_saudi": 1,
            "dob": "1992-09-25",
            "department_id": dept_ids["HR"],
            "designation": "HR Operations Director",
            "hire_date": "2020-06-15",
            "contract_type": "Indefinite",
            "contract_end_date": None,
            "iqama_expiry_date": "2027-10-10",
            "passport_number": "B7651092",
            "passport_expiry_date": "2028-08-20",
            "bank_name": "Riyad Bank",
            "iban": "SA2020000000100020003000",
            "basic_salary": 22000.0,
            "housing_allowance": 5500.0,
            "transport_allowance": 2000.0,
            "other_allowances": 1500.0,
            "gosi_number": "409182736",
            "status": "Active"
        },
        {
            "emp_code": "EMP-003",
            "first_name": "Rahul",
            "last_name": "Sharma",
            "arabic_name": "راهول شارما",
            "email": "rahul.sharma@alamal-ksa.com",
            "phone": "+966541122334",
            "national_id_iqama": "2391029384", # Expat Iqama starts with 2
            "nationality": "India",
            "gender": "Male",
            "is_saudi": 0,
            "dob": "1985-11-03",
            "department_id": dept_ids["ENG"],
            "designation": "Senior DevOps Engineer",
            "hire_date": "2021-01-10",
            "contract_type": "Fixed",
            "contract_end_date": (date.today() + timedelta(days=45)).strftime("%Y-%m-%d"), # Expiring soon!
            "iqama_expiry_date": (date.today() + timedelta(days=25)).strftime("%Y-%m-%d"), # Expiring critical!
            "passport_number": "Z8910293",
            "passport_expiry_date": "2027-03-30",
            "bank_name": "Saudi National Bank (SNB)",
            "iban": "SA4410000000123456789012",
            "basic_salary": 14000.0,
            "housing_allowance": 3500.0,
            "transport_allowance": 1000.0,
            "other_allowances": 500.0,
            "gosi_number": "908127364",
            "status": "Active"
        },
        {
            "emp_code": "EMP-004",
            "first_name": "Fahad",
            "last_name": "Al-Qahtani",
            "arabic_name": "فهد القحطاني",
            "email": "fahad.qahtani@alamal-ksa.com",
            "phone": "+966503344556",
            "national_id_iqama": "1076543210",
            "nationality": "Saudi Arabia",
            "gender": "Male",
            "is_saudi": 1,
            "dob": "1990-01-18",
            "department_id": dept_ids["FIN"],
            "designation": "Finance Manager",
            "hire_date": "2018-08-01",
            "contract_type": "Indefinite",
            "contract_end_date": None,
            "iqama_expiry_date": "2030-01-01",
            "passport_number": "K1092837",
            "passport_expiry_date": "2028-11-11",
            "bank_name": "Alinma Bank",
            "iban": "SA0505000000112233445566",
            "basic_salary": 20000.0,
            "housing_allowance": 5000.0,
            "transport_allowance": 1500.0,
            "other_allowances": 1000.0,
            "gosi_number": "209182736",
            "status": "Active"
        },
        {
            "emp_code": "EMP-005",
            "first_name": "Ahmed",
            "last_name": "El-Sayed",
            "arabic_name": "أحمد السيد",
            "email": "ahmed.sayed@alamal-ksa.com",
            "phone": "+966567788990",
            "national_id_iqama": "2481029381",
            "nationality": "Egypt",
            "gender": "Male",
            "is_saudi": 0,
            "dob": "1987-07-14",
            "department_id": dept_ids["OPS"],
            "designation": "Supply Chain Specialist",
            "hire_date": "2022-04-01",
            "contract_type": "Fixed",
            "contract_end_date": "2027-04-01",
            "iqama_expiry_date": (date.today() + timedelta(days=50)).strftime("%Y-%m-%d"), # Expiring soon!
            "passport_number": "F9081273",
            "passport_expiry_date": (date.today() + timedelta(days=40)).strftime("%Y-%m-%d"), # Passport expiring soon!
            "bank_name": "Bank AlJazira",
            "iban": "SA6060000000998877665544",
            "basic_salary": 11000.0,
            "housing_allowance": 2750.0,
            "transport_allowance": 1000.0,
            "other_allowances": 500.0,
            "gosi_number": "709182736",
            "status": "Active"
        },
        {
            "emp_code": "EMP-006",
            "first_name": "Noura",
            "last_name": "Al-Zahrani",
            "arabic_name": "نورة الزهراني",
            "email": "noura.zahrani@alamal-ksa.com",
            "phone": "+966509988776",
            "national_id_iqama": "1065432109",
            "nationality": "Saudi Arabia",
            "gender": "Female",
            "is_saudi": 1,
            "dob": "1995-02-28",
            "department_id": dept_ids["HR"],
            "designation": "Talent Acquisition Specialist",
            "hire_date": "2023-02-15",
            "contract_type": "Indefinite",
            "contract_end_date": None,
            "iqama_expiry_date": "2030-05-05",
            "passport_number": "P8091283",
            "passport_expiry_date": "2029-01-20",
            "bank_name": "Saudi British Bank (SABB)",
            "iban": "SA1818000000443322110099",
            "basic_salary": 12000.0,
            "housing_allowance": 3000.0,
            "transport_allowance": 1000.0,
            "other_allowances": 500.0,
            "gosi_number": "509182736",
            "status": "Active"
        }
    ]

    emp_db_ids = []
    for emp in employees:
        e_id = db.execute_cmd("""
            INSERT INTO employees (
                emp_code, first_name, last_name, arabic_name, email, phone,
                national_id_iqama, nationality, gender, is_saudi, dob,
                department_id, designation, hire_date, contract_type, contract_end_date,
                iqama_expiry_date, passport_number, passport_expiry_date, bank_name,
                iban, basic_salary, housing_allowance, transport_allowance, other_allowances,
                gosi_number, status
            ) VALUES (
                :emp_code, :first_name, :last_name, :arabic_name, :email, :phone,
                :national_id_iqama, :nationality, :gender, :is_saudi, :dob,
                :department_id, :designation, :hire_date, :contract_type, :contract_end_date,
                :iqama_expiry_date, :passport_number, :passport_expiry_date, :bank_name,
                :iban, :basic_salary, :housing_allowance, :transport_allowance, :other_allowances,
                :gosi_number, :status
            )
        """, emp)
        emp_db_ids.append(e_id)

    print("Seeding Sample Documents...")
    db.execute_cmd("""
        INSERT INTO documents (employee_id, doc_type, file_name, file_path, upload_date, expiry_date, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (emp_db_ids[0], "National ID", "Mohammed_ID_Copy.pdf", "uploads/documents/sample_id.pdf", "2023-01-01", "2028-12-31", "Verified National ID"))

    db.execute_cmd("""
        INSERT INTO documents (employee_id, doc_type, file_name, file_path, upload_date, expiry_date, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (emp_db_ids[2], "Iqama", "Rahul_Iqama_Copy.pdf", "uploads/documents/rahul_iqama.pdf", "2023-02-10", (date.today() + timedelta(days=25)).strftime("%Y-%m-%d"), "Expiring Iqama Renewal Requested"))

    print("Seeding Leave Requests...")
    db.execute_cmd("""
        INSERT INTO leaves (employee_id, leave_type, start_date, end_date, days, reason, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (emp_db_ids[0], "Annual", "2026-09-01", "2026-09-14", 14, "Annual Family Vacation in Abha", "Approved", "2026-08-01"))

    db.execute_cmd("""
        INSERT INTO leaves (employee_id, leave_type, start_date, end_date, days, reason, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (emp_db_ids[2], "Sick", "2026-08-10", "2026-08-12", 3, "Medical Checkup & Treatment", "Pending", "2026-08-05"))

    print("Seeding Initial Monthly Payroll Run...")
    payroll_run_id = db.execute_cmd("""
        INSERT INTO payroll_runs (payroll_month, payroll_year, total_basic, total_allowances, total_deductions, total_net_pay, status, processed_at)
        VALUES (8, 2026, 97000.0, 34750.0, 7156.25, 124593.75, 'Approved', ?)
    """, (datetime.now().strftime("%Y-%m-%d %H:%M:%S"),))

    # Calculate details for employees
    all_emps = db.query_all("SELECT * FROM employees")
    for emp in all_emps:
        basic = emp["basic_salary"]
        housing = emp["housing_allowance"]
        transport = emp["transport_allowance"]
        other = emp["other_allowances"]
        gross = basic + housing + transport + other
        
        gosi_res = SaudiHREngine.calculate_gosi(emp["is_saudi"] == 1, basic, housing)
        gosi_emp = gosi_res["employee_deduction"]
        gosi_empr = gosi_res["employer_contribution"]
        net = gross - gosi_emp
        
        db.execute_cmd("""
            INSERT INTO payroll_details (
                payroll_run_id, employee_id, basic_salary, housing_allowance,
                transport_allowance, other_allowances, gross_salary,
                gosi_employee, gosi_employer, other_deductions, net_salary
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (payroll_run_id, emp["id"], basic, housing, transport, other, gross, gosi_emp, gosi_empr, 0.0, net))

    print("Database seeding completed successfully!")

if __name__ == "__main__":
    seed_database()
