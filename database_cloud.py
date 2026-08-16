import os
import sqlite3
import shutil
import tempfile
from typing import List, Dict, Any, Optional

DB_WORKSPACE_PATH = os.path.join(os.path.dirname(__file__), "saudi_hr.db")
DB_TMP_PATH = os.path.join(tempfile.gettempdir(), "saudi_hr_runtime.db")

def is_vercel() -> bool:
    return bool(os.environ.get("VERCEL"))

def sync_from_workspace():
    """Restores database from persistent workspace storage to runtime temp directory."""
    if os.path.exists(DB_WORKSPACE_PATH) and os.path.getsize(DB_WORKSPACE_PATH) > 0:
        try:
            shutil.copy2(DB_WORKSPACE_PATH, DB_TMP_PATH)
        except Exception as e:
            print(f"Warning syncing DB from workspace: {e}")

def sync_to_workspace():
    """Flushes runtime database to persistent workspace storage."""
    if is_vercel():
        return
    if os.path.exists(DB_TMP_PATH):
        try:
            shutil.copy2(DB_TMP_PATH, DB_WORKSPACE_PATH)
        except Exception as e:
            print(f"Warning syncing DB to workspace: {e}")

def get_db_connection():
    """Returns a thread-safe SQLite connection with WAL mode and foreign key constraints enabled."""
    if not os.path.exists(DB_TMP_PATH):
        if os.path.exists(DB_WORKSPACE_PATH) and os.path.getsize(DB_WORKSPACE_PATH) > 0:
            sync_from_workspace()
            
    conn = sqlite3.connect(DB_TMP_PATH, timeout=30.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
    except Exception:
        pass
    return conn

def init_db():
    sync_from_workspace()
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("PRAGMA foreign_keys = ON;")
    
    # Departments
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS departments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        code TEXT UNIQUE NOT NULL,
        manager_name TEXT,
        budget REAL DEFAULT 0.0
    );
    """)
    
    # Employees
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS employees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        emp_code TEXT UNIQUE NOT NULL,
        first_name TEXT NOT NULL,
        last_name TEXT NOT NULL,
        arabic_name TEXT,
        email TEXT UNIQUE NOT NULL,
        phone TEXT,
        national_id_iqama TEXT UNIQUE NOT NULL,
        nationality TEXT NOT NULL,
        gender TEXT DEFAULT 'Male',
        is_saudi INTEGER DEFAULT 1,
        dob TEXT,
        department_id INTEGER,
        designation TEXT NOT NULL,
        hire_date TEXT NOT NULL,
        contract_type TEXT DEFAULT 'Fixed',
        contract_end_date TEXT,
        iqama_expiry_date TEXT,
        passport_number TEXT,
        passport_expiry_date TEXT,
        bank_name TEXT,
        iban TEXT,
        basic_salary REAL DEFAULT 0.0,
        housing_allowance REAL DEFAULT 0.0,
        transport_allowance REAL DEFAULT 0.0,
        other_allowances REAL DEFAULT 0.0,
        gosi_number TEXT,
        photo_filename TEXT,
        status TEXT DEFAULT 'Active',
        FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE SET NULL
    );
    """)
    
    # Users for Authentication
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        hashed_password TEXT NOT NULL,
        full_name TEXT NOT NULL,
        role TEXT DEFAULT 'hr_manager',
        employee_id INTEGER,
        created_at TEXT NOT NULL,
        FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE SET NULL
    );
    """)
    
    # Supplier Payment & Aging Invoice Tracking with Auto-Adjusting Balances
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS supplier_payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_name TEXT NOT NULL,
        invoice_number TEXT,
        invoice_date TEXT NOT NULL,
        due_date TEXT NOT NULL,
        invoice_details TEXT,
        supply_date TEXT NOT NULL,
        amount REAL NOT NULL DEFAULT 0.0,
        paid_amount REAL NOT NULL DEFAULT 0.0,
        remaining_amount REAL NOT NULL DEFAULT 0.0,
        status TEXT DEFAULT 'Pending',
        payment_date TEXT,
        remarks TEXT,
        created_at TEXT NOT NULL
    );
    """)
    
    # Supplier Payment History Transaction Logs
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS supplier_payment_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        supplier_payment_id INTEGER NOT NULL,
        payment_amount REAL NOT NULL,
        payment_date TEXT NOT NULL,
        payment_method TEXT DEFAULT 'Bank Transfer',
        reference_number TEXT,
        notes TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (supplier_payment_id) REFERENCES supplier_payments(id) ON DELETE CASCADE
    );
    """)
    
    # Documents
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id INTEGER NOT NULL,
        doc_type TEXT NOT NULL,
        file_name TEXT NOT NULL,
        file_path TEXT NOT NULL,
        upload_date TEXT NOT NULL,
        expiry_date TEXT,
        notes TEXT,
        FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE
    );
    """)
    
    # Leaves
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS leaves (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id INTEGER NOT NULL,
        leave_type TEXT NOT NULL,
        start_date TEXT NOT NULL,
        end_date TEXT NOT NULL,
        days INTEGER NOT NULL,
        reason TEXT,
        status TEXT DEFAULT 'Pending',
        created_at TEXT NOT NULL,
        FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE
    );
    """)
    
    # Payroll Runs
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS payroll_runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        payroll_month INTEGER NOT NULL,
        payroll_year INTEGER NOT NULL,
        total_basic REAL DEFAULT 0.0,
        total_allowances REAL DEFAULT 0.0,
        total_deductions REAL DEFAULT 0.0,
        total_net_pay REAL DEFAULT 0.0,
        status TEXT DEFAULT 'Approved',
        processed_at TEXT NOT NULL
    );
    """)
    
    # Payroll Details
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS payroll_details (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        payroll_run_id INTEGER NOT NULL,
        employee_id INTEGER NOT NULL,
        basic_salary REAL DEFAULT 0.0,
        housing_allowance REAL DEFAULT 0.0,
        transport_allowance REAL DEFAULT 0.0,
        other_allowances REAL DEFAULT 0.0,
        gross_salary REAL DEFAULT 0.0,
        gosi_employee REAL DEFAULT 0.0,
        gosi_employer REAL DEFAULT 0.0,
        other_deductions REAL DEFAULT 0.0,
        net_salary REAL DEFAULT 0.0,
        FOREIGN KEY (payroll_run_id) REFERENCES payroll_runs(id) ON DELETE CASCADE,
        FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE
    );
    """)
    
    # Settings
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    );
    """)
    
    # Create Indexes for High Performance
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_emp_dept ON employees(department_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_emp_status ON employees(status);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_leaves_emp ON leaves(employee_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_docs_emp ON documents(employee_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_payroll_dtl_run ON payroll_details(payroll_run_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_payroll_dtl_emp ON payroll_details(employee_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sp_company ON supplier_payments(company_name);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sp_status ON supplier_payments(status);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sp_logs_sp ON supplier_payment_logs(supplier_payment_id);")
    
    # Default Settings
    default_settings = {
        "company_name": "Al-Amal Enterprise Solutions KSA",
        "company_arabic_name": "شركة الأمل لترشيد الحلول المتكاملة",
        "cr_number": "1010894512",
        "mol_establishment_id": "7-889412",
        "gosi_reg_number": "309481920",
        "wps_bank_code": "RIBL",
        "wps_bank_name": "Riyad Bank",
        "hr_email": "hr@alamal-ksa.com",
        "address": "King Fahd Road, Olaya District, Riyadh, Saudi Arabia"
    }
    
    for k, v in default_settings.items():
        cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?);", (k, v))
        
    # Default Admin User
    from auth import hash_password
    default_admin_hash = hash_password("AdminSecret123!")
    cursor.execute("""
        INSERT OR IGNORE INTO users (email, hashed_password, full_name, role, created_at)
        VALUES ('admin@alamal-ksa.com', ?, 'System Administrator', 'admin', '2026-08-06 12:00:00')
    """, (default_admin_hash,))
    
    conn.commit()
    conn.close()
    sync_to_workspace()

def query_all(sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(sql, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def query_one(sql: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(sql, params)
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def execute_cmd(sql: str, params: tuple = ()) -> int:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(sql, params)
    conn.commit()
    last_id = cursor.lastrowid
    conn.close()
    sync_to_workspace()
    return last_id

def execute_script(sql_script: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.executescript(sql_script)
    conn.commit()
    conn.close()
    sync_to_workspace()
