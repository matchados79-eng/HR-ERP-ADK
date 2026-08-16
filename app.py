import os
import uuid
import json
import zipfile
import shutil
import tempfile
import calendar
from datetime import datetime, date, timedelta
from typing import Optional, List

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Depends, Header, Query
from fastapi.responses import FileResponse, Response, StreamingResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from PIL import Image

import database_cloud as db
import auth
from google_drive_backup import generate_full_backup_archive, restore_from_backup_dict
from models import (
    DepartmentCreate, DepartmentUpdate, EmployeeCreate, EmployeeUpdate,
    LeaveCreate, LeaveStatusUpdate, EOSBRequest, GOSIRequest, PayrollRunRequest,
    WorkerMonthlyPayRequest, SupplierCreate, SupplierUpdate, SupplierPaymentCreate,
    SupplierPaymentStatusUpdate, SupplierDisburseRequest, BackupRestoreRequest,
    DailyTimesheetEntry, BulkTimesheetSaveRequest
)
from saudi_hr_engine import SaudiHREngine
from pdf_generator import (
    generate_payslip_pdf, generate_supplier_statement_pdf,
    generate_supplier_summary_report_pdf, generate_monthly_payroll_schedule_pdf
)

# Initialize DB schema & indexes
db.init_db()

app = FastAPI(
    title="Saudi HR & SME Finance ERP System",
    description="Production-grade Saudi HR, Payroll & Finance ERP System with Accounts Payable, Vendor Ledgers, and SAMA WPS Engine",
    version="3.4.0"
)

# Enable CORS for web portal
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(__file__)

if db.is_vercel():
    UPLOADS_PHOTOS_DIR = os.path.join(tempfile.gettempdir(), "photos")
    UPLOADS_DOCS_DIR = os.path.join(tempfile.gettempdir(), "documents")
    UPLOADS_BACKUPS_DIR = os.path.join(tempfile.gettempdir(), "backups")
    UPLOADS_INVOICES_DIR = os.path.join(tempfile.gettempdir(), "supplier_invoices")
else:
    UPLOADS_PHOTOS_DIR = os.path.join(BASE_DIR, "uploads", "photos")
    UPLOADS_DOCS_DIR = os.path.join(BASE_DIR, "uploads", "documents")
    UPLOADS_BACKUPS_DIR = os.path.join(BASE_DIR, "uploads", "backups")
    UPLOADS_INVOICES_DIR = os.path.join(BASE_DIR, "uploads", "supplier_invoices")

os.makedirs(UPLOADS_PHOTOS_DIR, exist_ok=True)
os.makedirs(UPLOADS_DOCS_DIR, exist_ok=True)
os.makedirs(UPLOADS_BACKUPS_DIR, exist_ok=True)
os.makedirs(UPLOADS_INVOICES_DIR, exist_ok=True)

# Mount static and uploads
static_dir = os.path.join(BASE_DIR, "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

uploads_dir = os.path.join(BASE_DIR, "uploads")
if os.path.exists(uploads_dir):
    app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")

class LoginRequest(BaseModel):
    email: str
    password: str

class UserCreateRequest(BaseModel):
    email: str
    password: str
    full_name: str
    role: str = "viewer"

class UserUpdateRequest(BaseModel):
    email: str
    full_name: str
    role: str
    password: Optional[str] = None

# Dependency for Authenticated Requests (Supports both Bearer Header and Query Token for PDF/File downloads)
def get_current_user(
    authorization: Optional[str] = Header(None),
    token: Optional[str] = Query(None)
):
    raw_token = None
    if authorization and authorization.startswith("Bearer "):
        raw_token = authorization.split(" ")[1]
    elif token and token.strip():
        raw_token = token.strip()
        
    if not raw_token:
        raise HTTPException(status_code=401, detail="Authentication required. Please log in first.")
        
    payload = auth.verify_jwt_token(raw_token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired JWT session. Please log in again.")
    return payload

# Role Checker Dependency
def require_roles(allowed_roles: List[str]):
    def role_checker(user: dict = Depends(get_current_user)):
        if user.get("role") not in allowed_roles:
            raise HTTPException(status_code=403, detail="Permission denied. Your role does not have access to this feature.")
        return user
    return role_checker

# --- UI Root Route ---
@app.get("/", response_class=HTMLResponse)
def read_root():
    index_path = os.path.join(BASE_DIR, "static", "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Saudi HR ERP System Running</h1>"

@app.post("/api/auth/login")
def login(req: LoginRequest):
    input_email = req.email.strip()
    if input_email.lower() in ["admin", "administrator"]:
        user = db.query_one("SELECT * FROM users WHERE role = 'admin' ORDER BY id ASC LIMIT 1")
    else:
        user = db.query_one("SELECT * FROM users WHERE LOWER(email) = LOWER(?)", (input_email,))
        
    if not user or not auth.verify_password(req.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password.")
        
    token = auth.create_jwt_token({
        "user_id": user["id"],
        "email": user["email"],
        "full_name": user["full_name"],
        "role": user["role"]
    })
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "email": user["email"],
            "full_name": user["full_name"],
            "role": user["role"]
        }
    }

@app.get("/api/auth/me")
def get_me(user: dict = Depends(get_current_user)):
    return user

@app.get("/api/users")
def list_users(user: dict = Depends(require_roles(["admin", "hr_manager"]))):
    return db.query_all("SELECT id, email, full_name, role, created_at FROM users ORDER BY id DESC")

@app.post("/api/users")
def create_user_account(req: UserCreateRequest, user: dict = Depends(require_roles(["admin"]))):
    existing = db.query_one("SELECT id FROM users WHERE email = ?", (req.email,))
    if existing:
        raise HTTPException(status_code=400, detail="User account with this email already exists.")
        
    hashed_pwd = auth.hash_password(req.password)
    u_id = db.execute_cmd("""
        INSERT INTO users (email, hashed_password, full_name, role, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (req.email, hashed_pwd, req.full_name, req.role, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    
    return {"message": f"User account for {req.full_name} ({req.role}) created successfully", "id": u_id}

@app.put("/api/users/{user_id}")
def update_user_account(user_id: int, req: UserUpdateRequest, user: dict = Depends(require_roles(["admin"]))):
    existing = db.query_one("SELECT id FROM users WHERE id = ?", (user_id,))
    if not existing:
        raise HTTPException(status_code=404, detail="User account not found.")
        
    # Check duplicate email
    dup = db.query_one("SELECT id FROM users WHERE email = ? AND id != ?", (req.email, user_id))
    if dup:
        raise HTTPException(status_code=400, detail="Email address is already in use by another user.")
        
    if req.password and req.password.strip():
        hashed_pwd = auth.hash_password(req.password.strip())
        db.execute_cmd("""
            UPDATE users SET email = ?, full_name = ?, role = ?, hashed_password = ? WHERE id = ?
        """, (req.email, req.full_name, req.role, hashed_pwd, user_id))
    else:
        db.execute_cmd("""
            UPDATE users SET email = ?, full_name = ?, role = ? WHERE id = ?
        """, (req.email, req.full_name, req.role, user_id))
        
    return {"message": f"User credentials for {req.full_name} updated successfully"}

@app.delete("/api/users/{user_id}")
def delete_user_account(user_id: int, user: dict = Depends(require_roles(["admin"]))):
    if user["user_id"] == user_id:
        raise HTTPException(status_code=400, detail="Cannot delete your own active administrator account.")
        
    db.execute_cmd("DELETE FROM users WHERE id = ?", (user_id,))
    return {"message": "User account deleted successfully"}

# --- Dashboard Overview Endpoint ---
@app.get("/api/dashboard/stats")
def get_dashboard_stats(user: dict = Depends(get_current_user)):
    employees = db.query_all("SELECT * FROM employees WHERE status = 'Active'")
    total_emp = len(employees)
    saudi_emp = sum(1 for e in employees if e["is_saudi"] == 1)
    expat_emp = total_emp - saudi_emp
    
    saudization_info = SaudiHREngine.calculate_saudization(total_emp, saudi_emp)
    total_payroll = sum((e["basic_salary"] + e["housing_allowance"] + e["transport_allowance"] + e["other_allowances"]) for e in employees)
    
    pending_leaves_row = db.query_one("SELECT COUNT(*) as cnt FROM leaves WHERE status = 'Pending'")
    pending_leaves = pending_leaves_row["cnt"] if pending_leaves_row else 0
    
    alerts = SaudiHREngine.check_expiries(employees, threshold_days=60)
    
    depts = db.query_all("""
        SELECT d.name, COUNT(e.id) as emp_count
        FROM departments d
        LEFT JOIN employees e ON d.id = e.department_id AND e.status = 'Active'
        GROUP BY d.id
    """)
    
    pending_sp_row = db.query_one("SELECT SUM(remaining_amount) as tot FROM supplier_payments WHERE status != 'Paid'")
    pending_supplier_pay = float(pending_sp_row["tot"]) if pending_sp_row and pending_sp_row["tot"] is not None else 0.0
    
    return {
        "total_employees": total_emp,
        "saudi_employees": saudi_emp,
        "expat_employees": expat_emp,
        "saudization": saudization_info,
        "total_monthly_payroll": total_payroll if user["role"] in ["admin", "hr_manager"] else 0.0,
        "pending_supplier_payables": pending_supplier_pay if user["role"] in ["admin", "hr_manager"] else 0.0,
        "pending_leaves_count": pending_leaves,
        "expiring_alerts_count": len(alerts),
        "alerts_summary": alerts[:5],
        "department_distribution": depts
    }

# --- Departments Endpoints ---
@app.get("/api/departments")
def get_departments(user: dict = Depends(get_current_user)):
    return db.query_all("""
        SELECT d.*, COUNT(e.id) as employee_count 
        FROM departments d 
        LEFT JOIN employees e ON d.id = e.department_id AND e.status = 'Active'
        GROUP BY d.id
        ORDER BY d.name ASC
    """)

@app.post("/api/departments")
def create_department(dept: DepartmentCreate, user: dict = Depends(require_roles(["admin", "hr_manager"]))):
    existing = db.query_one("SELECT id FROM departments WHERE code = ?", (dept.code,))
    if existing:
        raise HTTPException(status_code=400, detail=f"Department with code '{dept.code}' already exists.")
        
    d_id = db.execute_cmd(
        "INSERT INTO departments (name, code, manager_name, budget) VALUES (?, ?, ?, ?)",
        (dept.name, dept.code, dept.manager_name, dept.budget or 0.0)
    )
    return {"message": "Department created successfully", "id": d_id}

@app.put("/api/departments/{dept_id}")
def update_department(dept_id: int, dept: DepartmentUpdate, user: dict = Depends(require_roles(["admin", "hr_manager"]))):
    existing = db.query_one("SELECT id FROM departments WHERE id = ?", (dept_id,))
    if not existing:
        raise HTTPException(status_code=404, detail="Department not found.")
        
    dup = db.query_one("SELECT id FROM departments WHERE code = ? AND id != ?", (dept.code, dept_id))
    if dup:
        raise HTTPException(status_code=400, detail=f"Department code '{dept.code}' is already used by another department.")
        
    db.execute_cmd("""
        UPDATE departments SET name = ?, code = ?, manager_name = ?, budget = ? WHERE id = ?
    """, (dept.name, dept.code, dept.manager_name, dept.budget or 0.0, dept_id))
    return {"message": "Department updated successfully"}

@app.delete("/api/departments/{dept_id}")
def delete_department(dept_id: int, user: dict = Depends(require_roles(["admin"]))):
    existing = db.query_one("SELECT id FROM departments WHERE id = ?", (dept_id,))
    if not existing:
        raise HTTPException(status_code=404, detail="Department not found.")
        
    db.execute_cmd("UPDATE employees SET department_id = NULL WHERE department_id = ?", (dept_id,))
    db.execute_cmd("DELETE FROM departments WHERE id = ?", (dept_id,))
    return {"message": "Department deleted successfully"}

# --- Employee Endpoints ---
@app.get("/api/employees")
def list_employees(
    search: Optional[str] = None,
    department_id: Optional[int] = None,
    is_saudi: Optional[int] = None,
    status: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    sql = """
        SELECT e.*, d.name as department_name 
        FROM employees e 
        LEFT JOIN departments d ON e.department_id = d.id 
        WHERE 1=1
    """
    params = []
    
    if search:
        sql += " AND (e.first_name LIKE ? OR e.last_name LIKE ? OR e.emp_code LIKE ? OR e.national_id_iqama LIKE ? OR e.email LIKE ?)"
        pattern = f"%{search}%"
        params.extend([pattern, pattern, pattern, pattern, pattern])
        
    if department_id:
        sql += " AND e.department_id = ?"
        params.append(department_id)
        
    if is_saudi is not None:
        sql += " AND e.is_saudi = ?"
        params.append(is_saudi)
        
    if status:
        sql += " AND e.status = ?"
        params.append(status)
        
    sql += " ORDER BY e.id DESC"
    results = db.query_all(sql, tuple(params))
    
    if user["role"] == "viewer":
        for r in results:
            r["basic_salary"] = 0.0
            r["housing_allowance"] = 0.0
            r["transport_allowance"] = 0.0
            r["other_allowances"] = 0.0
            
    return results

@app.post("/api/employees")
def create_employee(emp: EmployeeCreate, user: dict = Depends(require_roles(["admin", "hr_manager"]))):
    existing = db.query_one("SELECT id FROM employees WHERE emp_code = ? OR national_id_iqama = ? OR email = ?", (emp.emp_code, emp.national_id_iqama, emp.email))
    if existing:
        raise HTTPException(status_code=400, detail="Employee Code, Iqama/National ID, or Email already exists in the system.")
        
    data = emp.dict()
    if not data.get("worker_type"):
        data["worker_type"] = "Direct"

    e_id = db.execute_cmd("""
        INSERT INTO employees (
            emp_code, first_name, last_name, arabic_name, email, phone,
            national_id_iqama, nationality, gender, is_saudi, dob,
            department_id, designation, hire_date, contract_type, contract_end_date,
            iqama_expiry_date, passport_number, passport_expiry_date, bank_name,
            iban, basic_salary, housing_allowance, transport_allowance, other_allowances,
            worker_type, gosi_number, status
        ) VALUES (
            :emp_code, :first_name, :last_name, :arabic_name, :email, :phone,
            :national_id_iqama, :nationality, :gender, :is_saudi, :dob,
            :department_id, :designation, :hire_date, :contract_type, :contract_end_date,
            :iqama_expiry_date, :passport_number, :passport_expiry_date, :bank_name,
            :iban, :basic_salary, :housing_allowance, :transport_allowance, :other_allowances,
            :worker_type, :gosi_number, :status
        )
    """, data)
    return {"message": "Employee profile created successfully", "id": e_id}

@app.get("/api/employees/{emp_id}")
def get_employee_detail(emp_id: int, user: dict = Depends(get_current_user)):
    emp = db.query_one("""
        SELECT e.*, d.name as department_name 
        FROM employees e 
        LEFT JOIN departments d ON e.department_id = d.id 
        WHERE e.id = ?
    """, (emp_id,))
    
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found.")
        
    if user["role"] == "viewer":
        emp["basic_salary"] = 0.0
        emp["housing_allowance"] = 0.0
        emp["transport_allowance"] = 0.0
        emp["other_allowances"] = 0.0
        
    documents = db.query_all("SELECT * FROM documents WHERE employee_id = ? ORDER BY id DESC", (emp_id,))
    leaves = db.query_all("SELECT * FROM leaves WHERE employee_id = ? ORDER BY id DESC", (emp_id,))
    payroll_history = db.query_all("""
        SELECT pd.*, pr.payroll_month, pr.payroll_year, pr.processed_at 
        FROM payroll_details pd 
        JOIN payroll_runs pr ON pd.payroll_run_id = pr.id 
        WHERE pd.employee_id = ? 
        ORDER BY pr.id DESC
    """, (emp_id,)) if user["role"] in ["admin", "hr_manager"] else []
    
    gosi_info = SaudiHREngine.calculate_gosi(
        emp["is_saudi"] == 1,
        emp["basic_salary"],
        emp["housing_allowance"]
    )
    
    return {
        "employee": emp,
        "documents": documents,
        "leaves": leaves,
        "payroll_history": payroll_history,
        "gosi_breakdown": gosi_info
    }

@app.put("/api/employees/{emp_id}")
def update_employee(emp_id: int, emp: EmployeeUpdate, user: dict = Depends(require_roles(["admin", "hr_manager"]))):
    existing = db.query_one("SELECT id FROM employees WHERE id = ?", (emp_id,))
    if not existing:
        raise HTTPException(status_code=404, detail="Employee not found.")
        
    # Prevent duplicate code, national ID, or email across OTHER employees
    dup = db.query_one("""
        SELECT id FROM employees 
        WHERE (emp_code = ? OR national_id_iqama = ? OR email = ?) AND id != ?
    """, (emp.emp_code, emp.national_id_iqama, emp.email, emp_id))
    if dup:
        raise HTTPException(status_code=400, detail="Employee Code, Iqama/National ID, or Email is already registered to another employee.")
        
    data = emp.dict()
    data["id"] = emp_id
    if not data.get("worker_type"):
        data["worker_type"] = "Direct"
    
    db.execute_cmd("""
        UPDATE employees SET
            emp_code = :emp_code,
            first_name = :first_name,
            last_name = :last_name,
            arabic_name = :arabic_name,
            email = :email,
            phone = :phone,
            national_id_iqama = :national_id_iqama,
            nationality = :nationality,
            gender = :gender,
            is_saudi = :is_saudi,
            dob = :dob,
            department_id = :department_id,
            designation = :designation,
            hire_date = :hire_date,
            contract_type = :contract_type,
            contract_end_date = :contract_end_date,
            iqama_expiry_date = :iqama_expiry_date,
            passport_number = :passport_number,
            passport_expiry_date = :passport_expiry_date,
            bank_name = :bank_name,
            iban = :iban,
            basic_salary = :basic_salary,
            housing_allowance = :housing_allowance,
            transport_allowance = :transport_allowance,
            other_allowances = :other_allowances,
            worker_type = :worker_type,
            gosi_number = :gosi_number,
            status = :status
        WHERE id = :id
    """, data)
    return {"message": "Employee profile updated successfully"}

@app.delete("/api/employees/{emp_id}")
def delete_employee(emp_id: int, user: dict = Depends(require_roles(["admin"]))):
    existing = db.query_one("SELECT id, first_name, last_name FROM employees WHERE id = ?", (emp_id,))
    if not existing:
        raise HTTPException(status_code=404, detail="Employee not found.")
        
    db.execute_cmd("DELETE FROM employees WHERE id = ?", (emp_id,))
    return {"message": f"Employee {existing['first_name']} {existing['last_name']} removed successfully"}

# --- Image & Document Endpoints ---
@app.post("/api/employees/{emp_id}/photo")
async def upload_employee_photo(emp_id: int, file: UploadFile = File(...), user: dict = Depends(require_roles(["admin", "hr_manager"]))):
    emp = db.query_one("SELECT id FROM employees WHERE id = ?", (emp_id,))
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found.")
        
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".jpg", ".jpeg", ".png", ".webp"]:
        raise HTTPException(status_code=400, detail="Invalid image format. Allowed: JPG, PNG, WEBP")
        
    unique_filename = f"emp_{emp_id}_{uuid.uuid4().hex[:8]}{ext}"
    file_path = os.path.join(UPLOADS_PHOTOS_DIR, unique_filename)
    
    try:
        contents = await file.read()
        with open(file_path, "wb") as f:
            f.write(contents)
            
        try:
            with Image.open(file_path) as im:
                im.thumbnail((400, 400))
                im.save(file_path)
        except Exception:
            pass
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process image upload: {str(e)}")
        
    db.execute_cmd("UPDATE employees SET photo_filename = ? WHERE id = ?", (f"photos/{unique_filename}", emp_id))
    return {"message": "Employee photo uploaded successfully", "photo_url": f"/uploads/photos/{unique_filename}"}

@app.post("/api/employees/{emp_id}/documents")
async def upload_employee_document(
    emp_id: int,
    doc_type: str = Form(...),
    notes: Optional[str] = Form(None),
    expiry_date: Optional[str] = Form(None),
    file: UploadFile = File(...),
    user: dict = Depends(require_roles(["admin", "hr_manager"]))
):
    emp = db.query_one("SELECT id FROM employees WHERE id = ?", (emp_id,))
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found.")
        
    ext = os.path.splitext(file.filename)[1].lower()
    unique_filename = f"doc_emp_{emp_id}_{uuid.uuid4().hex[:8]}{ext}"
    saved_path = os.path.join(UPLOADS_DOCS_DIR, unique_filename)
    rel_path = f"uploads/documents/{unique_filename}"
    
    try:
        contents = await file.read()
        with open(saved_path, "wb") as buffer:
            buffer.write(contents)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file upload: {str(e)}")
        
    doc_id = db.execute_cmd("""
        INSERT INTO documents (employee_id, doc_type, file_name, file_path, upload_date, expiry_date, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (emp_id, doc_type, file.filename, rel_path, date.today().strftime("%Y-%m-%d"), expiry_date, notes))
    
    return {"message": "Document uploaded successfully", "document_id": doc_id, "file_name": file.filename}

@app.delete("/api/documents/{doc_id}")
def delete_document(doc_id: int, user: dict = Depends(require_roles(["admin", "hr_manager"]))):
    doc = db.query_one("SELECT * FROM documents WHERE id = ?", (doc_id,))
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
        
    full_path = os.path.join(BASE_DIR, doc["file_path"])
    if os.path.exists(full_path):
        try:
            os.remove(full_path)
        except Exception:
            pass
            
    db.execute_cmd("DELETE FROM documents WHERE id = ?", (doc_id,))
    return {"message": "Document deleted successfully"}

@app.get("/api/documents/{doc_id}/download")
def download_document(doc_id: int, user: dict = Depends(get_current_user)):
    doc = db.query_one("SELECT * FROM documents WHERE id = ?", (doc_id,))
    if not doc:
        raise HTTPException(status_code=404, detail="Document record not found.")
        
    full_path = os.path.join(BASE_DIR, doc["file_path"])
    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="Document file does not exist on disk.")
        
    return FileResponse(full_path, filename=doc["file_name"])

# --- Robust Supplier Payment & Vendor Ledger Endpoints ---
@app.get("/api/suppliers/payments")
def list_supplier_payments(
    search: Optional[str] = None,
    status: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    sql = "SELECT * FROM supplier_payments WHERE 1=1"
    params = []
    
    if search:
        sql += " AND (company_name LIKE ? OR invoice_number LIKE ? OR invoice_details LIKE ? OR remarks LIKE ?)"
        pattern = f"%{search}%"
        params.extend([pattern, pattern, pattern, pattern])
        
    if status:
        sql += " AND status = ?"
        params.append(status)
        
    sql += " ORDER BY id DESC"
    raw_payments = db.query_all(sql, tuple(params))
    
    aging_res = SaudiHREngine.calculate_accounts_payable_aging(raw_payments)
    return {
        "summary": aging_res["summary"],
        "payments": aging_res["processed_payments"]
    }

@app.get("/api/suppliers/export/pdf")
def export_supplier_report_pdf(
    suppliers: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    user: dict = Depends(get_current_user)
):
    """Generates an executive Accounts Payable & Supplier Invoices PDF Report with custom vendor selection."""
    sql = "SELECT * FROM supplier_payments WHERE 1=1"
    params = []
    
    selected_names = []
    if suppliers and suppliers.strip() and suppliers.strip().lower() != "all":
        selected_names = [s.strip() for s in suppliers.split(",") if s.strip()]
        if selected_names:
            placeholders = ",".join("?" * len(selected_names))
            sql += f" AND company_name IN ({placeholders})"
            params.extend(selected_names)
            
    if status and status.strip() and status.strip() != "All":
        sql += " AND status = ?"
        params.append(status.strip())
        
    if start_date and start_date.strip():
        sql += " AND invoice_date >= ?"
        params.append(start_date.strip())
        
    if end_date and end_date.strip():
        sql += " AND invoice_date <= ?"
        params.append(end_date.strip())
        
    sql += " ORDER BY company_name ASC, id DESC"
    raw_payments = db.query_all(sql, tuple(params))
    aging_res = SaudiHREngine.calculate_accounts_payable_aging(raw_payments)
    
    setting_rows = db.query_all("SELECT * FROM settings")
    settings = {s["key"]: s["value"] for s in setting_rows}
    
    target_scope_str = ", ".join(selected_names) if selected_names else "All Registered Suppliers"
    date_scope_str = f"{start_date or 'Start'} to {end_date or 'Present'}" if (start_date or end_date) else "All Historical Invoices"
    
    filter_info = {
        "selected_suppliers": target_scope_str,
        "status": status or "All Statuses",
        "date_range": date_scope_str
    }
    
    pdf_bytes = generate_supplier_summary_report_pdf(
        aging_res["processed_payments"],
        aging_res["summary"],
        settings,
        filter_info
    )
    
    filename = f"Accounts_Payable_Report_{date.today().strftime('%Y%m%d')}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename={filename}"}
    )

# --- Registered Suppliers / Vendors Directory Endpoints ---
@app.get("/api/suppliers")
def list_suppliers(user: dict = Depends(get_current_user)):
    """Lists all registered suppliers/vendors with aggregated invoice and liability stats."""
    suppliers = db.query_all("SELECT * FROM suppliers ORDER BY name ASC")
    
    # Calculate live invoice summaries per supplier
    for sup in suppliers:
        name = sup["name"]
        inv_stats = db.query_one("""
            SELECT COUNT(id) as inv_count,
                   COALESCE(SUM(amount), 0.0) as total_billed,
                   COALESCE(SUM(paid_amount), 0.0) as total_paid,
                   COALESCE(SUM(remaining_amount), 0.0) as total_balance
            FROM supplier_payments
            WHERE company_name = ?
        """, (name,))
        
        sup["invoices_count"] = inv_stats["inv_count"] if inv_stats else 0
        sup["total_billed"] = round(float(inv_stats["total_billed"]), 2) if inv_stats else 0.0
        sup["total_paid"] = round(float(inv_stats["total_paid"]), 2) if inv_stats else 0.0
        sup["total_balance"] = round(float(inv_stats["total_balance"]), 2) if inv_stats else 0.0
        
    return suppliers

@app.post("/api/suppliers")
def create_supplier(req: SupplierCreate, user: dict = Depends(require_roles(["admin", "hr_manager"]))):
    if not req.name or not req.name.strip():
        raise HTTPException(status_code=400, detail="Supplier / Vendor name is required.")
        
    existing = db.query_one("SELECT id FROM suppliers WHERE LOWER(name) = LOWER(?)", (req.name.strip(),))
    if existing:
        raise HTTPException(status_code=400, detail=f"Supplier '{req.name.strip()}' is already registered.")
        
    sup_id = db.execute_cmd("""
        INSERT INTO suppliers (
            name, contact_person, phone, email, cr_number, vat_number,
            bank_name, iban, payment_terms, address, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        req.name.strip(), req.contact_person, req.phone, req.email,
        req.cr_number, req.vat_number, req.bank_name, req.iban,
        req.payment_terms or "Net 30", req.address, datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))
    
    return {"message": "Supplier profile created successfully", "id": sup_id}

@app.get("/api/suppliers/{sup_id}")
def get_supplier_detail(sup_id: int, user: dict = Depends(get_current_user)):
    sup = db.query_one("SELECT * FROM suppliers WHERE id = ?", (sup_id,))
    if not sup:
        raise HTTPException(status_code=404, detail="Supplier not found.")
        
    invoices = db.query_all("SELECT * FROM supplier_payments WHERE company_name = ? ORDER BY id DESC", (sup["name"],))
    return {
        "supplier": sup,
        "invoices": invoices
    }

@app.put("/api/suppliers/{sup_id}")
def update_supplier(sup_id: int, req: SupplierUpdate, user: dict = Depends(require_roles(["admin", "hr_manager"]))):
    sup = db.query_one("SELECT * FROM suppliers WHERE id = ?", (sup_id,))
    if not sup:
        raise HTTPException(status_code=404, detail="Supplier not found.")
        
    dup = db.query_one("SELECT id FROM suppliers WHERE LOWER(name) = LOWER(?) AND id != ?", (req.name.strip(), sup_id))
    if dup:
        raise HTTPException(status_code=400, detail=f"Another supplier with name '{req.name.strip()}' already exists.")
        
    old_name = sup["name"]
    new_name = req.name.strip()
    
    db.execute_cmd("""
        UPDATE suppliers SET
            name = ?,
            contact_person = ?,
            phone = ?,
            email = ?,
            cr_number = ?,
            vat_number = ?,
            bank_name = ?,
            iban = ?,
            payment_terms = ?,
            address = ?
        WHERE id = ?
    """, (
        new_name, req.contact_person, req.phone, req.email,
        req.cr_number, req.vat_number, req.bank_name, req.iban,
        req.payment_terms or "Net 30", req.address, sup_id
    ))
    
    # If name changed, update linked supplier_payments
    if old_name != new_name:
        db.execute_cmd("UPDATE supplier_payments SET company_name = ? WHERE company_name = ?", (new_name, old_name))
        
    return {"message": "Supplier profile updated successfully"}

@app.delete("/api/suppliers/{sup_id}")
def delete_supplier(sup_id: int, user: dict = Depends(require_roles(["admin"]))):
    sup = db.query_one("SELECT * FROM suppliers WHERE id = ?", (sup_id,))
    if not sup:
        raise HTTPException(status_code=404, detail="Supplier not found.")
        
    db.execute_cmd("DELETE FROM suppliers WHERE id = ?", (sup_id,))
    return {"message": f"Supplier '{sup['name']}' deleted successfully."}

@app.get("/api/suppliers/vendors")
def list_vendor_summaries(user: dict = Depends(get_current_user)):
    sql = """
        SELECT company_name,
               COUNT(id) as total_invoices,
               SUM(amount) as total_billed,
               SUM(paid_amount) as total_paid,
               SUM(remaining_amount) as total_outstanding,
               MAX(due_date) as latest_due_date
        FROM supplier_payments
        GROUP BY company_name
        ORDER BY total_outstanding DESC
    """
    return db.query_all(sql)

@app.get("/api/suppliers/vendors/{company_name}/ledger")
def get_vendor_ledger(company_name: str, user: dict = Depends(get_current_user)):
    invoices = db.query_all("SELECT * FROM supplier_payments WHERE company_name = ? ORDER BY id DESC", (company_name,))
    if not invoices:
        raise HTTPException(status_code=404, detail="Vendor company not found.")
        
    invoice_ids = [inv["id"] for inv in invoices]
    placeholders = ",".join("?" * len(invoice_ids))
    logs = db.query_all(f"SELECT * FROM supplier_payment_logs WHERE supplier_payment_id IN ({placeholders}) ORDER BY id DESC", tuple(invoice_ids)) if invoice_ids else []
    
    total_billed = sum(float(i["amount"]) for i in invoices)
    total_paid = sum(float(i["paid_amount"]) for i in invoices)
    total_balance = sum(float(i["remaining_amount"]) for i in invoices)
    
    return {
        "company_name": company_name,
        "summary": {
            "total_invoices_count": len(invoices),
            "total_billed": round(total_billed, 2),
            "total_paid": round(total_paid, 2),
            "total_balance": round(total_balance, 2)
        },
        "invoices": invoices,
        "payment_logs": logs
    }

@app.post("/api/suppliers/vendors/{company_name}/disburse")
def disburse_vendor_lump_sum(
    company_name: str,
    req: SupplierDisburseRequest,
    user: dict = Depends(require_roles(["admin", "hr_manager"]))
):
    """
    Applies a lump-sum supplier payment across all open/pending invoices 
    using FIFO (First-In, First-Out: oldest invoices settled first).
    """
    if req.payment_amount <= 0:
        raise HTTPException(status_code=400, detail="Disbursal amount must be greater than zero.")
        
    open_invoices = db.query_all("""
        SELECT * FROM supplier_payments 
        WHERE company_name = ? AND remaining_amount > 0 
        ORDER BY invoice_date ASC, id ASC
    """, (company_name,))
    
    if not open_invoices:
        raise HTTPException(status_code=400, detail=f"No outstanding unpaid invoices found for '{company_name}'.")
        
    remaining_to_apply = float(req.payment_amount)
    pay_date = req.payment_date or date.today().strftime("%Y-%m-%d")
    settlements = []
    
    for inv in open_invoices:
        if remaining_to_apply <= 0:
            break
            
        inv_rem = float(inv["remaining_amount"])
        inv_id = inv["id"]
        
        applied_now = min(remaining_to_apply, inv_rem)
        new_paid = float(inv["paid_amount"]) + applied_now
        new_rem = max(0.0, float(inv["amount"]) - new_paid)
        new_status = "Paid" if new_rem == 0 else "Partially Paid"
        
        # Update invoice
        db.execute_cmd("""
            UPDATE supplier_payments 
            SET paid_amount = ?, remaining_amount = ?, status = ?, payment_date = ?
            WHERE id = ?
        """, (new_paid, new_rem, new_status, pay_date, inv_id))
        
        # Log payment transaction
        log_notes = f"{req.notes or 'Vendor settlement'} (Auto-applied SAR {applied_now:,.2f} from lump-sum payment)"
        db.execute_cmd("""
            INSERT INTO supplier_payment_logs (
                supplier_payment_id, payment_amount, payment_date, payment_method, reference_number, notes, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (inv_id, applied_now, pay_date, req.payment_method or "Bank Transfer", req.reference_number or None, log_notes, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        
        settlements.append({
            "invoice_id": inv_id,
            "invoice_number": inv.get("invoice_number"),
            "applied_amount": applied_now,
            "new_remaining": new_rem,
            "status": new_status
        })
        
        remaining_to_apply -= applied_now
        
    return {
        "message": f"Successfully disbursed SAR {req.payment_amount:,.2f} to {company_name} across {len(settlements)} invoice(s).",
        "company_name": company_name,
        "total_disbursed": req.payment_amount,
        "unapplied_credit": max(0.0, remaining_to_apply),
        "settlements": settlements
    }

@app.post("/api/suppliers/payments")
def create_supplier_payment(req: SupplierPaymentCreate, user: dict = Depends(require_roles(["admin", "hr_manager"]))):
    if not req.company_name or not req.company_name.strip():
        raise HTTPException(status_code=400, detail="Vendor / Company name is required.")
        
    inv_amount = float(req.amount or 0.0)
    if inv_amount < 0:
        raise HTTPException(status_code=400, detail="Invoice amount cannot be negative.")
        
    inv_date = req.invoice_date.strip() if req.invoice_date and req.invoice_date.strip() else date.today().strftime("%Y-%m-%d")
    
    # Handle Supply Date From & To
    if req.supply_start_date and req.supply_start_date.strip():
        sup_start = req.supply_start_date.strip()
    elif req.supply_date and req.supply_date.strip():
        sup_start = req.supply_date.strip()
    else:
        sup_start = inv_date
        
    if req.supply_end_date and req.supply_end_date.strip():
        sup_end = req.supply_end_date.strip()
    else:
        sup_end = sup_start
        
    sup_date = sup_start
    
    if req.due_date and req.due_date.strip():
        due_date = req.due_date.strip()
    else:
        try:
            due_date = (datetime.strptime(inv_date, "%Y-%m-%d").date() + timedelta(days=30)).strftime("%Y-%m-%d")
        except Exception:
            due_date = (date.today() + timedelta(days=30)).strftime("%Y-%m-%d")
            
    inv_details = req.invoice_details.strip() if req.invoice_details and req.invoice_details.strip() else "General Supplies & Services"
    inv_status = req.status or "Pending"
    
    paid_amt = inv_amount if inv_status == "Paid" else 0.0
    rem_amt = max(0.0, inv_amount - paid_amt)
    
    sp_id = db.execute_cmd("""
        INSERT INTO supplier_payments (
            company_name, invoice_number, invoice_date, due_date, invoice_details,
            supply_date, supply_start_date, supply_end_date, amount, paid_amount, remaining_amount, status, remarks, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        req.company_name.strip(), req.invoice_number or None, inv_date, due_date, inv_details,
        sup_date, sup_start, sup_end, inv_amount, paid_amt, rem_amt, inv_status, req.remarks or None, datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))
    
    if paid_amt > 0:
        db.execute_cmd("""
            INSERT INTO supplier_payment_logs (
                supplier_payment_id, payment_amount, payment_date, payment_method, reference_number, notes, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (sp_id, paid_amt, inv_date, "Bank Transfer", "Initial Settlement", "Full upfront payment", datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        
    return {"message": "Supplier payment record created successfully", "id": sp_id}

@app.put("/api/suppliers/payments/{sp_id}")
def update_supplier_payment(sp_id: int, req: SupplierPaymentCreate, user: dict = Depends(require_roles(["admin", "hr_manager"]))):
    sp = db.query_one("SELECT * FROM supplier_payments WHERE id = ?", (sp_id,))
    if not sp:
        raise HTTPException(status_code=404, detail="Supplier payment record not found.")
        
    inv_amount = float(req.amount or 0.0)
    inv_date = req.invoice_date.strip() if req.invoice_date and req.invoice_date.strip() else sp["invoice_date"]
    
    sup_start = req.supply_start_date.strip() if req.supply_start_date and req.supply_start_date.strip() else (sp.get("supply_start_date") or sp["supply_date"])
    sup_end = req.supply_end_date.strip() if req.supply_end_date and req.supply_end_date.strip() else (sp.get("supply_end_date") or sup_start)
    sup_date = sup_start
    
    due_date = req.due_date.strip() if req.due_date and req.due_date.strip() else sp["due_date"]
    inv_details = req.invoice_details.strip() if req.invoice_details and req.invoice_details.strip() else sp["invoice_details"]
    
    current_paid = float(sp["paid_amount"])
    new_remaining = max(0.0, inv_amount - current_paid)
    
    if new_remaining <= 0:
        new_status = "Paid"
        new_remaining = 0.0
    elif current_paid > 0:
        new_status = "Partially Paid"
    else:
        new_status = req.status or "Pending"
        
    db.execute_cmd("""
        UPDATE supplier_payments SET
            company_name = ?,
            invoice_number = ?,
            invoice_date = ?,
            due_date = ?,
            invoice_details = ?,
            supply_date = ?,
            supply_start_date = ?,
            supply_end_date = ?,
            amount = ?,
            remaining_amount = ?,
            status = ?,
            remarks = ?
        WHERE id = ?
    """, (
        req.company_name.strip(), req.invoice_number or None, inv_date,
        due_date, inv_details, sup_date, sup_start, sup_end, inv_amount, new_remaining,
        new_status, req.remarks or None, sp_id
    ))
    
def add_one_month(date_str: Optional[str]) -> str:
    """Safely increments a YYYY-MM-DD date string by 1 month, capping at the target month's maximum days."""
    if not date_str or not str(date_str).strip():
        return date.today().strftime("%Y-%m-%d")
    try:
        dt = datetime.strptime(str(date_str).strip(), "%Y-%m-%d")
        year = dt.year + (dt.month // 12)
        month = (dt.month % 12) + 1
        max_days = calendar.monthrange(year, month)[1]
        day = min(dt.day, max_days)
        return date(year, month, day).strftime("%Y-%m-%d")
    except Exception:
        return (date.today() + timedelta(days=30)).strftime("%Y-%m-%d")

@app.post("/api/suppliers/payments/{sp_id}/repeat-next-month")
def repeat_supplier_payment_next_month(
    sp_id: int,
    user: dict = Depends(require_roles(["admin", "hr_manager"]))
):
    """Duplicates an existing invoice for the following month with the same amount and automatically calculated next-month dates."""
    sp = db.query_one("SELECT * FROM supplier_payments WHERE id = ?", (sp_id,))
    if not sp:
        raise HTTPException(status_code=404, detail="Supplier invoice not found.")
        
    next_inv_date = add_one_month(sp["invoice_date"])
    next_due_date = add_one_month(sp["due_date"])
    next_sup_start = add_one_month(sp["supply_start_date"] or sp["supply_date"])
    next_sup_end = add_one_month(sp["supply_end_date"] or sp["supply_date"])
    
    # Generate distinct new invoice number
    old_num = sp.get("invoice_number") or ""
    import random
    new_inv_num = f"{old_num}-REC" if old_num and not old_num.endswith("-REC") else f"INV-{datetime.now().year}-{random.randint(1000, 9999)}"
    
    inv_amount = float(sp["amount"])
    
    new_id = db.execute_cmd("""
        INSERT INTO supplier_payments (
            company_name, invoice_number, invoice_date, due_date, invoice_details,
            supply_date, supply_start_date, supply_end_date, amount, paid_amount,
            remaining_amount, status, remarks, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        sp["company_name"], new_inv_num, next_inv_date, next_due_date, sp["invoice_details"],
        next_sup_start, next_sup_start, next_sup_end, inv_amount, 0.0,
        inv_amount, "Pending", f"Recurring monthly bill (Cloned from #{sp_id})",
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))
    
    return {
        "message": f"Recurring invoice for next month created successfully (Invoice #{new_id})",
        "id": new_id,
        "company_name": sp["company_name"],
        "amount": inv_amount,
        "invoice_number": new_inv_num,
        "invoice_date": next_inv_date,
        "due_date": next_due_date,
        "supply_start_date": next_sup_start,
        "supply_end_date": next_sup_end
    }

@app.post("/api/suppliers/payments/{sp_id}/disburse")
def disburse_supplier_payment(
    sp_id: int,
    req: SupplierDisburseRequest,
    user: dict = Depends(require_roles(["admin", "hr_manager"]))
):
    sp = db.query_one("SELECT * FROM supplier_payments WHERE id = ?", (sp_id,))
    if not sp:
        raise HTTPException(status_code=404, detail="Supplier payment record not found.")
        
    if req.payment_amount <= 0:
        raise HTTPException(status_code=400, detail="Disbursal amount must be greater than zero.")
        
    pay_date = req.payment_date or date.today().strftime("%Y-%m-%d")
    
    db.execute_cmd("""
        INSERT INTO supplier_payment_logs (
            supplier_payment_id, payment_amount, payment_date, payment_method, reference_number, notes, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (sp_id, req.payment_amount, pay_date, req.payment_method or "Bank Transfer", req.reference_number, req.notes, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    
    total_paid_row = db.query_one("SELECT SUM(payment_amount) as tot FROM supplier_payment_logs WHERE supplier_payment_id = ?", (sp_id,))
    total_paid = float(total_paid_row["tot"] or 0.0)
    
    invoice_amount = float(sp["amount"])
    new_remaining = max(0.0, invoice_amount - total_paid)
    
    if new_remaining <= 0:
        new_status = "Paid"
        new_remaining = 0.0
    else:
        new_status = "Partially Paid"
        
    db.execute_cmd("""
        UPDATE supplier_payments SET
            paid_amount = ?,
            remaining_amount = ?,
            status = ?,
            payment_date = ?
        WHERE id = ?
    """, (total_paid, new_remaining, new_status, pay_date, sp_id))
    
    return {
        "message": f"Payment of SAR {req.payment_amount:,.2f} disbursed successfully",
        "paid_amount": total_paid,
        "remaining_amount": new_remaining,
        "status": new_status
    }

@app.get("/api/suppliers/payments/{sp_id}/history")
def get_supplier_payment_history(sp_id: int, user: dict = Depends(get_current_user)):
    sp = db.query_one("SELECT * FROM supplier_payments WHERE id = ?", (sp_id,))
    if not sp:
        raise HTTPException(status_code=404, detail="Supplier payment record not found.")
        
    logs = db.query_all("SELECT * FROM supplier_payment_logs WHERE supplier_payment_id = ? ORDER BY id DESC", (sp_id,))
    
    return {
        "supplier_payment": sp,
        "payment_logs": logs
    }

@app.get("/api/suppliers/payments/{sp_id}/statement.pdf")
def download_supplier_statement_pdf(sp_id: int, user: dict = Depends(get_current_user)):
    sp = db.query_one("SELECT * FROM supplier_payments WHERE id = ?", (sp_id,))
    if not sp:
        raise HTTPException(status_code=404, detail="Supplier payment record not found.")
        
    logs = db.query_all("SELECT * FROM supplier_payment_logs WHERE supplier_payment_id = ? ORDER BY id ASC", (sp_id,))
    
    setting_rows = db.query_all("SELECT * FROM settings")
    settings = {s["key"]: s["value"] for s in setting_rows}
    
    pdf_bytes = generate_supplier_statement_pdf(sp, logs, settings)
    filename = f"Supplier_Statement_{sp.get('company_name', 'Vendor').replace(' ', '_')}_{sp_id}.pdf"
    
    return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": f"inline; filename={filename}"})

@app.post("/api/suppliers/payments/{sp_id}/attachment")
async def upload_supplier_invoice_attachment(
    sp_id: int,
    file: UploadFile = File(...),
    user: dict = Depends(require_roles(["admin", "hr_manager"]))
):
    sp = db.query_one("SELECT * FROM supplier_payments WHERE id = ?", (sp_id,))
    if not sp:
        raise HTTPException(status_code=404, detail="Supplier invoice not found.")
        
    orig_filename = os.path.basename(file.filename) if file.filename else "invoice.pdf"
    safe_name = f"INV_{sp_id}_{uuid.uuid4().hex[:8]}_{orig_filename}"
    file_path = os.path.join(UPLOADS_INVOICES_DIR, safe_name)
    
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)
        
    db.execute_cmd(
        "UPDATE supplier_payments SET attachment_filename = ?, attachment_path = ? WHERE id = ?",
        (orig_filename, safe_name, sp_id)
    )
    
    return {
        "message": "Invoice attachment uploaded successfully",
        "attachment_filename": orig_filename,
        "download_url": f"/api/suppliers/payments/{sp_id}/attachment"
    }

@app.get("/api/suppliers/payments/{sp_id}/attachment")
def download_supplier_invoice_attachment(
    sp_id: int,
    user: dict = Depends(get_current_user)
):
    sp = db.query_one("SELECT * FROM supplier_payments WHERE id = ?", (sp_id,))
    if not sp or not sp.get("attachment_path"):
        raise HTTPException(status_code=404, detail="No attachment found for this invoice.")
        
    safe_name = sp["attachment_path"]
    full_path = os.path.join(UPLOADS_INVOICES_DIR, safe_name)
    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="Attachment file not found on server disk.")
        
    orig_name = sp.get("attachment_filename") or f"Invoice_{sp_id}.pdf"
    media_type = "application/pdf" if orig_name.lower().endswith(".pdf") else "application/octet-stream"
    
    return FileResponse(
        full_path,
        media_type=media_type,
        filename=orig_name,
        headers={"Content-Disposition": f"inline; filename={orig_name}"}
    )

@app.delete("/api/suppliers/payments/{sp_id}/attachment")
def delete_supplier_invoice_attachment(
    sp_id: int,
    user: dict = Depends(require_roles(["admin", "hr_manager"]))
):
    sp = db.query_one("SELECT * FROM supplier_payments WHERE id = ?", (sp_id,))
    if not sp:
        raise HTTPException(status_code=404, detail="Supplier invoice not found.")
        
    if sp.get("attachment_path"):
        full_path = os.path.join(UPLOADS_INVOICES_DIR, sp["attachment_path"])
        if os.path.exists(full_path):
            try:
                os.remove(full_path)
            except Exception:
                pass
                
    db.execute_cmd(
        "UPDATE supplier_payments SET attachment_filename = NULL, attachment_path = NULL WHERE id = ?",
        (sp_id,)
    )
    return {"message": "Invoice attachment removed successfully"}

@app.delete("/api/suppliers/payments/{sp_id}")
def delete_supplier_payment(sp_id: int, user: dict = Depends(require_roles(["admin"]))):
    sp = db.query_one("SELECT * FROM supplier_payments WHERE id = ?", (sp_id,))
    if sp and sp.get("attachment_path"):
        full_path = os.path.join(UPLOADS_INVOICES_DIR, sp["attachment_path"])
        if os.path.exists(full_path):
            try:
                os.remove(full_path)
            except Exception:
                pass
    db.execute_cmd("DELETE FROM supplier_payments WHERE id = ?", (sp_id,))
    return {"message": "Supplier payment record deleted successfully"}

# --- Financial Analytics & Accounts Payable Aging Hub ---
@app.get("/api/finance/analytics")
def get_finance_analytics(user: dict = Depends(require_roles(["admin", "hr_manager"]))):
    supplier_payments = db.query_all("SELECT * FROM supplier_payments ORDER BY id DESC")
    aging_res = SaudiHREngine.calculate_accounts_payable_aging(supplier_payments)
    
    employees = db.query_all("SELECT * FROM employees WHERE status = 'Active'")
    monthly_payroll = sum((e["basic_salary"] + e["housing_allowance"] + e["transport_allowance"] + e["other_allowances"]) for e in employees)
    
    projected_30_day_outflow = monthly_payroll + aging_res["summary"]["total_outstanding_payable"]
    
    return {
        "summary": aging_res["summary"],
        "aging_buckets": aging_res["aging_buckets"],
        "monthly_payroll_commitment": monthly_payroll,
        "projected_30_day_outflow": projected_30_day_outflow,
        "vendor_invoices_count": len(supplier_payments)
    }

# --- Automated Backup & Restoration Endpoints ---
@app.post("/api/backup/google-drive")
def trigger_google_drive_backup(user: dict = Depends(require_roles(["admin"]))):
    try:
        backup_zip_path = generate_full_backup_archive()
        filename = os.path.basename(backup_zip_path)
        download_url = f"/uploads/backups/{filename}"
        
        return {
            "message": "Full system backup archive created successfully!",
            "status": "SUCCESS",
            "backup_filename": filename,
            "backup_download_url": download_url,
            "timestamp": datetime.now().isoformat(),
            "google_drive_status": "Ready for automated sync to user Google Drive"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Backup generation failed: {str(e)}")

@app.post("/api/backup/restore")
async def restore_system_backup(
    file: Optional[UploadFile] = File(None),
    user: dict = Depends(require_roles(["admin"]))
):
    try:
        if not file:
            raise HTTPException(status_code=400, detail="Please provide a backup ZIP or JSON file.")
            
        contents = await file.read()
        filename = file.filename.lower()
        
        if filename.endswith(".json"):
            dump = json.loads(contents.decode("utf-8"))
        elif filename.endswith(".zip"):
            with zipfile.ZipFile(io.BytesIO(contents)) as zf:
                if "database_dump.json" not in zf.namelist():
                    raise HTTPException(status_code=400, detail="Invalid backup ZIP: 'database_dump.json' not found.")
                json_bytes = zf.read("database_dump.json")
                dump = json.loads(json_bytes.decode("utf-8"))
        else:
            raise HTTPException(status_code=400, detail="Unsupported backup format. Please upload a .ZIP or .JSON file.")
            
        result = restore_from_backup_dict(dump)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Restore operation failed: {str(e)}")

# --- Payroll Endpoints ---
@app.get("/api/payroll/runs")
def get_payroll_runs(user: dict = Depends(require_roles(["admin", "hr_manager"]))):
    return db.query_all("SELECT * FROM payroll_runs ORDER BY id DESC")

@app.post("/api/payroll/generate")
def generate_monthly_payroll(req: PayrollRunRequest, user: dict = Depends(require_roles(["admin", "hr_manager"]))):
    existing = db.query_one("SELECT id FROM payroll_runs WHERE payroll_month = ? AND payroll_year = ?", (req.month, req.year))
    if existing:
        raise HTTPException(status_code=400, detail=f"Payroll for {req.month}/{req.year} has already been processed.")
        
    active_emps = db.query_all("SELECT * FROM employees WHERE status = 'Active'")
    if not active_emps:
        raise HTTPException(status_code=400, detail="No active employees found to generate payroll.")
        
    tot_basic = 0.0
    tot_allowances = 0.0
    tot_deductions = 0.0
    tot_net = 0.0
    
    run_id = db.execute_cmd("""
        INSERT INTO payroll_runs (payroll_month, payroll_year, total_basic, total_allowances, total_deductions, total_net_pay, status, processed_at)
        VALUES (?, ?, 0.0, 0.0, 0.0, 0.0, 'Approved', ?)
    """, (req.month, req.year, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    
    for emp in active_emps:
        basic = float(emp["basic_salary"])
        housing = float(emp["housing_allowance"])
        transport = float(emp["transport_allowance"])
        other = float(emp["other_allowances"])
        gross = basic + housing + transport + other
        
        gosi_res = SaudiHREngine.calculate_gosi(emp["is_saudi"] == 1, basic, housing)
        gosi_emp = gosi_res["employee_deduction"]
        gosi_empr = gosi_res["employer_contribution"]
        net = gross - gosi_emp
        
        tot_basic += basic
        tot_allowances += (housing + transport + other)
        tot_deductions += gosi_emp
        tot_net += net
        
        db.execute_cmd("""
            INSERT INTO payroll_details (
                payroll_run_id, employee_id, basic_salary, housing_allowance,
                transport_allowance, other_allowances, gross_salary,
                gosi_employee, gosi_employer, other_deductions, net_salary
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (run_id, emp["id"], basic, housing, transport, other, gross, gosi_emp, gosi_empr, 0.0, net))
        
    db.execute_cmd("""
        UPDATE payroll_runs SET
            total_basic = ?,
            total_allowances = ?,
            total_deductions = ?,
            total_net_pay = ?
        WHERE id = ?
    """, (tot_basic, tot_allowances, tot_deductions, tot_net, run_id))
    
    return {"message": "Payroll generated and approved successfully", "payroll_run_id": run_id}

@app.delete("/api/payroll/runs/{run_id}")
def delete_payroll_run(run_id: int, user: dict = Depends(require_roles(["admin"]))):
    run = db.query_one("SELECT * FROM payroll_runs WHERE id = ?", (run_id,))
    if not run:
        raise HTTPException(status_code=404, detail="Payroll run not found.")
        
    db.execute_cmd("DELETE FROM payroll_runs WHERE id = ?", (run_id,))
    return {"message": f"Payroll run for {run['payroll_month']}/{run['payroll_year']} deleted successfully"}

@app.get("/api/payroll/runs/{run_id}/details")
def get_payroll_run_details(run_id: int, user: dict = Depends(require_roles(["admin", "hr_manager"]))):
    run = db.query_one("SELECT * FROM payroll_runs WHERE id = ?", (run_id,))
    if not run:
        raise HTTPException(status_code=404, detail="Payroll run not found.")
        
    items = db.query_all("""
        SELECT pd.*, e.emp_code, e.first_name, e.last_name, e.national_id_iqama, e.is_saudi, e.bank_name, e.iban, d.name as department_name
        FROM payroll_details pd
        JOIN employees e ON pd.employee_id = e.id
        LEFT JOIN departments d ON e.department_id = d.id
        WHERE pd.payroll_run_id = ?
    """, (run_id,))
    
    return {"run": run, "details": items}

@app.get("/api/payroll/monthly-roster")
def get_monthly_payroll_roster(
    month: int = Query(..., ge=1, le=12),
    year: int = Query(..., ge=2020, le=2050),
    user: dict = Depends(require_roles(["admin", "hr_manager"]))
):
    """
    Returns the monthly worker payroll roster for a specific month and year.
    """
    run = db.query_one("SELECT * FROM payroll_runs WHERE payroll_month = ? AND payroll_year = ?", (month, year))
    
    if not run:
        return {
            "month": month,
            "year": year,
            "has_run": False,
            "run": None,
            "workers": [],
            "summary": {
                "total_workers": 0,
                "total_basic": 0.0,
                "total_allowances": 0.0,
                "total_gross": 0.0,
                "total_gosi": 0.0,
                "total_other_ded": 0.0,
                "total_net": 0.0
            }
        }
        
    workers = db.query_all("""
        SELECT pd.*, e.emp_code, e.first_name, e.last_name, e.national_id_iqama, e.is_saudi, e.designation,
               e.bank_name, e.iban, d.name as department_name
        FROM payroll_details pd
        JOIN employees e ON pd.employee_id = e.id
        LEFT JOIN departments d ON e.department_id = d.id
        WHERE pd.payroll_run_id = ?
        ORDER BY e.emp_code ASC, e.id ASC
    """, (run["id"],))
    
    tot_basic = sum(float(w["basic_salary"]) for w in workers)
    tot_housing = sum(float(w["housing_allowance"]) for w in workers)
    tot_transport = sum(float(w["transport_allowance"]) for w in workers)
    tot_other_allow = sum(float(w["other_allowances"]) for w in workers)
    tot_gross = sum(float(w["gross_salary"]) for w in workers)
    tot_gosi = sum(float(w["gosi_employee"]) for w in workers)
    tot_other_ded = sum(float(w["other_deductions"]) for w in workers)
    tot_net = sum(float(w["net_salary"]) for w in workers)
    
    return {
        "month": month,
        "year": year,
        "has_run": True,
        "run": run,
        "workers": workers,
        "summary": {
            "total_workers": len(workers),
            "total_basic": round(tot_basic, 2),
            "total_housing": round(tot_housing, 2),
            "total_allowances": round(tot_housing + tot_transport + tot_other_allow, 2),
            "total_gross": round(tot_gross, 2),
            "total_gosi": round(tot_gosi, 2),
            "total_other_ded": round(tot_other_ded, 2),
            "total_net": round(tot_net, 2)
        }
    }

@app.post("/api/payroll/monthly-roster/populate")
def populate_monthly_payroll_roster(
    req: PayrollRunRequest,
    user: dict = Depends(require_roles(["admin", "hr_manager"]))
):
    """
    Auto-populates the monthly roster with all active employees and computes their standard contract salary & GOSI.
    """
    active_emps = db.query_all("SELECT * FROM employees WHERE status = 'Active'")
    if not active_emps:
        raise HTTPException(status_code=400, detail="No active employees found to populate payroll.")
        
    run = db.query_one("SELECT * FROM payroll_runs WHERE payroll_month = ? AND payroll_year = ?", (req.month, req.year))
    if not run:
        run_id = db.execute_cmd("""
            INSERT INTO payroll_runs (payroll_month, payroll_year, total_basic, total_allowances, total_deductions, total_net_pay, status, processed_at)
            VALUES (?, ?, 0.0, 0.0, 0.0, 0.0, 'Approved', ?)
        """, (req.month, req.year, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    else:
        run_id = run["id"]
        
    for emp in active_emps:
        existing_detail = db.query_one("SELECT id FROM payroll_details WHERE payroll_run_id = ? AND employee_id = ?", (run_id, emp["id"]))
        if existing_detail:
            continue  # Keep existing adjusted values if already populated
            
        basic = float(emp["basic_salary"])
        housing = float(emp["housing_allowance"])
        transport = float(emp["transport_allowance"])
        other = float(emp["other_allowances"])
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
        """, (run_id, emp["id"], basic, housing, transport, other, gross, gosi_emp, gosi_empr, 0.0, net))
        
    # Recompute parent run totals
    details = db.query_all("SELECT * FROM payroll_details WHERE payroll_run_id = ?", (run_id,))
    tot_basic = sum(float(d["basic_salary"]) for d in details)
    tot_allowances = sum(float(d["housing_allowance"]) + float(d["transport_allowance"]) + float(d["other_allowances"]) for d in details)
    tot_deductions = sum(float(d["gosi_employee"]) + float(d["other_deductions"]) for d in details)
    tot_net = sum(float(d["net_salary"]) for d in details)
    
    db.execute_cmd("""
        UPDATE payroll_runs SET
            total_basic = ?,
            total_allowances = ?,
            total_deductions = ?,
            total_net_pay = ?
        WHERE id = ?
    """, (tot_basic, tot_allowances, tot_deductions, tot_net, run_id))
    
    return {"message": f"Successfully populated payroll for {len(details)} workers for {req.month}/{req.year}", "run_id": run_id}

@app.post("/api/payroll/monthly-roster/worker")
def save_worker_monthly_pay(
    req: WorkerMonthlyPayRequest,
    user: dict = Depends(require_roles(["admin", "hr_manager"]))
):
    """
    Adds or updates an individual worker's full industrial payslip breakdown for a specific month.
    """
    emp = db.query_one("SELECT * FROM employees WHERE id = ?", (req.employee_id,))
    if not emp:
        raise HTTPException(status_code=404, detail="Employee record not found.")
        
    run = db.query_one("SELECT * FROM payroll_runs WHERE payroll_month = ? AND payroll_year = ?", (req.month, req.year))
    if not run:
        run_id = db.execute_cmd("""
            INSERT INTO payroll_runs (payroll_month, payroll_year, total_basic, total_allowances, total_deductions, total_net_pay, status, processed_at)
            VALUES (?, ?, 0.0, 0.0, 0.0, 0.0, 'Approved', ?)
        """, (req.month, req.year, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    else:
        run_id = run["id"]
        
    basic = max(0.0, float(req.basic_salary))
    days_worked = float(req.days_worked or 30.0)
    cutoff_period = req.cutoff_period or f"{datetime(req.year, req.month, 1).strftime('%B 01')}-{calendar.monthrange(req.year, req.month)[1]}, {req.year}"
    
    daily_rate = float(req.daily_rate if req.daily_rate is not None else (basic / 30.0 if basic > 0 else 83.33333333))
    hourly_rate = float(req.hourly_rate if req.hourly_rate is not None else (daily_rate / 8.0 if daily_rate > 0 else 10.42))
    ot_rate = float(req.ot_rate if req.ot_rate is not None else round(hourly_rate * 1.5, 2))
    
    working_hours = float(req.working_hours if req.working_hours is not None else (days_worked * 8.0))
    regular_pay = float(req.regular_pay if req.regular_pay is not None else round(working_hours * hourly_rate, 2))
    
    ot_hours = float(req.ot_hours or 0.0)
    ot_pay = float(req.ot_pay if req.ot_pay is not None else round(ot_hours * ot_rate, 2))
    subtotal_pay = round(regular_pay + ot_pay, 2)
    
    rest_day_hours = float(req.rest_day_hours or 0.0)
    rest_day_rate = float(req.rest_day_rate if req.rest_day_rate is not None else hourly_rate)
    rest_day_pay = float(req.rest_day_pay if req.rest_day_pay is not None else round(rest_day_hours * rest_day_rate, 2))
    
    holiday_hours = float(req.holiday_hours or 0.0)
    holiday_rate = float(req.holiday_rate if req.holiday_rate is not None else hourly_rate)
    holiday_pay = float(req.holiday_pay if req.holiday_pay is not None else round(holiday_hours * holiday_rate, 2))
    
    meal_allowance_qty = float(req.meal_allowance_qty or 0.0)
    meal_allowance_rate = float(req.meal_allowance_rate if req.meal_allowance_rate is not None else (10.0 if meal_allowance_qty > 0 else 0.0))
    meal_allowance_pay = float(req.meal_allowance_pay if req.meal_allowance_pay is not None else (float(req.housing_allowance or 0.0) or round(meal_allowance_qty * meal_allowance_rate, 2)))
    
    adjustment_add = float(req.adjustment_add if req.adjustment_add is not None else float(req.other_allowances or 0.0))
    total_pay = round(subtotal_pay + rest_day_pay + holiday_pay + meal_allowance_pay + adjustment_add, 2)
    
    wps_deduction = float(req.wps_deduction or 0.0)
    water_bill = float(req.water_bill or 0.0)
    other_ded = float(req.other_deductions or 0.0)
    
    gosi_res = SaudiHREngine.calculate_gosi(emp["is_saudi"] == 1, basic, meal_allowance_pay)
    gosi_emp = gosi_res["employee_deduction"]
    gosi_empr = gosi_res["employer_contribution"]
    
    total_deductions = round(wps_deduction + water_bill + gosi_emp + other_ded, 2)
    net_pay = max(0.0, round(total_pay - total_deductions, 2))
    
    cash_advance = float(req.cash_advance or 0.0)
    adjustment_sub = float(req.adjustment_sub or 0.0)
    actual_pay = max(0.0, round(net_pay - cash_advance - adjustment_sub, 2))
    
    housing = meal_allowance_pay
    transport = float(req.transport_allowance or 0.0)
    other_allow = adjustment_add
    gross = total_pay
    
    existing_detail = db.query_one("SELECT id FROM payroll_details WHERE payroll_run_id = ? AND employee_id = ?", (run_id, req.employee_id))
    if existing_detail:
        db.execute_cmd("""
            UPDATE payroll_details SET
                basic_salary = ?,
                housing_allowance = ?,
                transport_allowance = ?,
                other_allowances = ?,
                gross_salary = ?,
                gosi_employee = ?,
                gosi_employer = ?,
                other_deductions = ?,
                net_salary = ?,
                cutoff_period = ?,
                days_worked = ?,
                daily_rate = ?,
                hourly_rate = ?,
                ot_rate = ?,
                working_hours = ?,
                regular_pay = ?,
                ot_hours = ?,
                ot_pay = ?,
                subtotal_pay = ?,
                rest_day_hours = ?,
                rest_day_pay = ?,
                holiday_hours = ?,
                holiday_pay = ?,
                meal_allowance_qty = ?,
                meal_allowance_rate = ?,
                meal_allowance_pay = ?,
                adjustment_add = ?,
                total_pay = ?,
                wps_deduction = ?,
                water_bill = ?,
                total_deductions = ?,
                cash_advance = ?,
                adjustment_sub = ?,
                actual_pay = ?
            WHERE id = ?
        """, (
            basic, housing, transport, other_allow, gross, gosi_emp, gosi_empr, other_ded, net_pay,
            cutoff_period, days_worked, daily_rate, hourly_rate, ot_rate, working_hours, regular_pay,
            ot_hours, ot_pay, subtotal_pay, rest_day_hours, rest_day_pay, holiday_hours, holiday_pay,
            meal_allowance_qty, meal_allowance_rate, meal_allowance_pay, adjustment_add, total_pay,
            wps_deduction, water_bill, total_deductions, cash_advance, adjustment_sub, actual_pay,
            existing_detail["id"]
        ))
        detail_id = existing_detail["id"]
    else:
        detail_id = db.execute_cmd("""
            INSERT INTO payroll_details (
                payroll_run_id, employee_id, basic_salary, housing_allowance,
                transport_allowance, other_allowances, gross_salary,
                gosi_employee, gosi_employer, other_deductions, net_salary,
                cutoff_period, days_worked, daily_rate, hourly_rate, ot_rate,
                working_hours, regular_pay, ot_hours, ot_pay, subtotal_pay,
                rest_day_hours, rest_day_pay, holiday_hours, holiday_pay,
                meal_allowance_qty, meal_allowance_rate, meal_allowance_pay,
                adjustment_add, total_pay, wps_deduction, water_bill,
                total_deductions, cash_advance, adjustment_sub, actual_pay
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            run_id, req.employee_id, basic, housing, transport, other_allow, gross, gosi_emp, gosi_empr, other_ded, net_pay,
            cutoff_period, days_worked, daily_rate, hourly_rate, ot_rate, working_hours, regular_pay,
            ot_hours, ot_pay, subtotal_pay, rest_day_hours, rest_day_pay, holiday_hours, holiday_pay,
            meal_allowance_qty, meal_allowance_rate, meal_allowance_pay, adjustment_add, total_pay,
            wps_deduction, water_bill, total_deductions, cash_advance, adjustment_sub, actual_pay
        ))
        
    # Recompute parent run totals
    details = db.query_all("SELECT * FROM payroll_details WHERE payroll_run_id = ?", (run_id,))
    tot_basic = sum(float(d["basic_salary"]) for d in details)
    tot_allowances = sum(float(d["housing_allowance"] or 0) + float(d["transport_allowance"] or 0) + float(d["other_allowances"] or 0) for d in details)
    tot_deductions = sum(float(d["gosi_employee"] or 0) + float(d["other_deductions"] or 0) for d in details)
    tot_net = sum(float(d["net_salary"] or 0) for d in details)
    
    db.execute_cmd("""
        UPDATE payroll_runs SET
            total_basic = ?,
            total_allowances = ?,
            total_deductions = ?,
            total_net_pay = ?
        WHERE id = ?
    """, (tot_basic, tot_allowances, tot_deductions, tot_net, run_id))
    
    return {
        "message": f"Successfully updated monthly payroll for {emp['first_name']} {emp['last_name']}",
        "detail_id": detail_id,
        "net_salary": net_pay,
        "actual_pay": actual_pay
    }

@app.delete("/api/payroll/monthly-roster/worker/{detail_id}")
def delete_worker_monthly_pay(
    detail_id: int,
    user: dict = Depends(require_roles(["admin", "hr_manager"]))
):
    """
    Removes a worker from the monthly payroll roster.
    """
    detail = db.query_one("SELECT * FROM payroll_details WHERE id = ?", (detail_id,))
    if not detail:
        raise HTTPException(status_code=404, detail="Payroll detail item not found.")
        
    run_id = detail["payroll_run_id"]
    db.execute_cmd("DELETE FROM payroll_details WHERE id = ?", (detail_id,))
    
    # Recompute parent run totals
    details = db.query_all("SELECT * FROM payroll_details WHERE payroll_run_id = ?", (run_id,))
    tot_basic = sum(float(d["basic_salary"] or 0) for d in details)
    tot_allowances = sum(float(d["housing_allowance"] or 0) + float(d["transport_allowance"] or 0) + float(d["other_allowances"] or 0) for d in details)
    tot_deductions = sum(float(d["gosi_employee"] or 0) + float(d["other_deductions"] or 0) for d in details)
    tot_net = sum(float(d["net_salary"] or 0) for d in details)
    
    db.execute_cmd("""
        UPDATE payroll_runs SET
            total_basic = ?,
            total_allowances = ?,
            total_deductions = ?,
            total_net_pay = ?
        WHERE id = ?
    """, (tot_basic, tot_allowances, tot_deductions, tot_net, run_id))
    
    return {"message": "Worker removed from this month's payroll roster."}

# =========================================================================
# WORKER DAILY TIMESHEET ATTENDANCE CALENDAR & PAYROLL ENGINE
# =========================================================================
@app.get("/api/payroll/timesheet")
def get_worker_timesheet(
    employee_id: int = Query(...),
    month: int = Query(..., ge=1, le=12),
    year: int = Query(..., ge=2020, le=2050),
    user: dict = Depends(require_roles(["admin", "hr_manager", "viewer"]))
):
    """
    Retrieves the daily attendance & working hours calendar for an employee in a given month.
    Combines existing logged records with default dates for full calendar display.
    """
    emp = db.query_one("""
        SELECT e.*, d.name as department_name 
        FROM employees e 
        LEFT JOIN departments d ON e.department_id = d.id 
        WHERE e.id = ?
    """, (employee_id,))
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found.")
        
    num_days = calendar.monthrange(year, month)[1]
    
    # Query logged daily timesheets
    logged_rows = db.query_all("""
        SELECT * FROM worker_timesheets 
        WHERE employee_id = ? AND year = ? AND month = ?
        ORDER BY day ASC
    """, (employee_id, year, month))
    logged_map = {row["day"]: row for row in logged_rows}
    
    # Check if a payroll detail record already exists for this worker & month
    run = db.query_one("SELECT * FROM payroll_runs WHERE payroll_month = ? AND payroll_year = ?", (month, year))
    detail = None
    if run:
        detail = db.query_one("SELECT * FROM payroll_details WHERE payroll_run_id = ? AND employee_id = ?", (run["id"], employee_id))
        
    # Build complete calendar days
    calendar_days = []
    for day in range(1, num_days + 1):
        dt = date(year, month, day)
        weekday_name = dt.strftime("%a")  # Mon, Tue, etc.
        is_friday = dt.weekday() == 4     # In Saudi Arabia, Friday is rest day (weekday 4 in Python)
        
        if day in logged_map:
            rec = logged_map[day]
            calendar_days.append({
                "day": day,
                "date": rec["timesheet_date"],
                "weekday": weekday_name,
                "regular_hours": rec["regular_hours"],
                "ot_hours": rec["ot_hours"],
                "day_type": rec["day_type"],
                "meal_allowance": rec["meal_allowance"],
                "notes": rec.get("notes") or ""
            })
        else:
            # Default suggestion: Fridays are RestDay, other days are Regular 8.0h
            def_type = "RestDay" if is_friday else "Regular"
            def_hours = 0.0 if is_friday else 8.0
            calendar_days.append({
                "day": day,
                "date": dt.isoformat(),
                "weekday": weekday_name,
                "regular_hours": def_hours,
                "ot_hours": 0.0,
                "day_type": def_type,
                "meal_allowance": 0 if is_friday else 1,
                "notes": ""
            })
            
    base_sal = float(emp["basic_salary"] or 0)
    worker_type = emp.get("worker_type") or "Direct"
    
    if worker_type == "Direct":
        # Direct: Rate depends on Monthly Basic / 30, then / 8
        daily_rate = float(detail.get("daily_rate") or (base_sal / 30.0 if base_sal > 0 else 83.33333333)) if detail else (base_sal / 30.0 if base_sal > 0 else 83.33333333)
        hourly_rate = float(detail.get("hourly_rate") or (daily_rate / 8.0 if daily_rate > 0 else 10.42)) if detail else (daily_rate / 8.0 if daily_rate > 0 else 10.42)
        ot_rate = float(detail.get("ot_rate") or round(hourly_rate * 1.5, 2)) if detail else round(hourly_rate * 1.5, 2)
    else:
        # Indirect: Regular only and hourly
        daily_rate = float(detail.get("daily_rate") or (base_sal / 30.0 if base_sal > 0 else 0.0)) if detail else (base_sal / 30.0 if base_sal > 0 else 0.0)
        hourly_rate = float(detail.get("hourly_rate") or (base_sal / 240.0 if base_sal > 0 else 25.0)) if detail else (base_sal / 240.0 if base_sal > 0 else 25.0)
        ot_rate = 0.0  # Indirect workers are regular only
    
    return {
        "employee": {
            "id": emp["id"],
            "emp_code": emp["emp_code"],
            "first_name": emp["first_name"],
            "last_name": emp["last_name"],
            "designation": emp["designation"] or "Electrician Foreman",
            "department_name": emp.get("department_name") or "Operations",
            "is_saudi": emp["is_saudi"],
            "worker_type": worker_type,
            "basic_salary": base_sal,
            "daily_rate": daily_rate,
            "hourly_rate": hourly_rate,
            "ot_rate": ot_rate
        },
        "month": month,
        "year": year,
        "days": calendar_days,
        "detail": detail
    }

@app.post("/api/payroll/timesheet/bulk-save")
def save_worker_timesheet_and_payroll(
    req: BulkTimesheetSaveRequest,
    user: dict = Depends(require_roles(["admin", "hr_manager"]))
):
    """
    Saves daily attendance & hours timesheet for an employee and automatically calculates
    the monthly payslip breakdown and updates the monthly payroll run.
    """
    emp = db.query_one("SELECT * FROM employees WHERE id = ?", (req.employee_id,))
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found.")
        
    # 1. Upsert daily timesheet records
    for d in req.days:
        db.execute_cmd("""
            INSERT INTO worker_timesheets (
                employee_id, timesheet_date, year, month, day,
                regular_hours, ot_hours, day_type, meal_allowance, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(employee_id, timesheet_date) DO UPDATE SET
                regular_hours = excluded.regular_hours,
                ot_hours = excluded.ot_hours,
                day_type = excluded.day_type,
                meal_allowance = excluded.meal_allowance,
                notes = excluded.notes;
        """, (
            req.employee_id, d.date, req.year, req.month, d.day,
            float(d.regular_hours or 0), float(d.ot_hours or 0),
            d.day_type or "Regular", int(d.meal_allowance or 0), d.notes or ""
        ))
        
    # 2. Aggregate timesheet totals & Saudi Friday Paid Rest Day Rule
    days_by_num = {d.day: d for d in req.days}
    tot_regular_hours = 0.0
    tot_ot_hours = sum(float(d.ot_hours or 0) for d in req.days)
    tot_rest_day_hours = 0.0
    tot_holiday_hours = 0.0

    for d in req.days:
        reg_h = float(d.regular_hours or 0)
        dt = date(req.year, req.month, d.day)
        is_friday = (dt.weekday() == 4)  # 4 is Friday in Python datetime

        if d.day_type == 'Holiday':
            tot_holiday_hours += (reg_h if reg_h > 0 else 8.0)
        elif d.day_type == 'RestDay' or is_friday:
            if reg_h > 0:
                # Explicit hours entered
                tot_rest_day_hours += reg_h
            else:
                # Friday Paid Rest Day Policy:
                # Paid if employee was NOT absent on Thursday (day - 1) AND Saturday (day + 1)
                thu = days_by_num.get(d.day - 1)
                sat = days_by_num.get(d.day + 1)
                
                thu_absent = (thu is not None and (thu.day_type == 'Absent' or (float(thu.regular_hours or 0) == 0 and thu.day_type not in ['Holiday', 'Leave', 'RestDay'])))
                sat_absent = (sat is not None and (sat.day_type == 'Absent' or (float(sat.regular_hours or 0) == 0 and sat.day_type not in ['Holiday', 'Leave', 'RestDay'])))
                
                if not thu_absent and not sat_absent:
                    tot_rest_day_hours += 8.0  # Paid Friday Rest Day
                else:
                    tot_rest_day_hours += 0.0  # Unpaid due to absence on Thu or Sat
        else:
            tot_regular_hours += reg_h

    # Days worked: any day where regular hours > 0 or marked Regular
    days_worked = sum(1 for d in req.days if float(d.regular_hours or 0) > 0 or d.day_type == 'Regular')
    
    # Meal allowances count
    tot_meal_qty = sum(1 for d in req.days if int(d.meal_allowance or 0) == 1)
    
    # 3. Rates & Financial Calculations
    base_sal = float(emp["basic_salary"] or 0)
    daily_rate = float(req.daily_rate if req.daily_rate is not None else (base_sal / 30.0 if base_sal > 0 else 83.33333333))
    hourly_rate = float(req.hourly_rate if req.hourly_rate is not None else (daily_rate / 8.0 if daily_rate > 0 else 10.42))
    ot_rate = float(req.ot_rate if req.ot_rate is not None else round(hourly_rate * 1.5, 2))
    
    regular_pay = round(tot_regular_hours * hourly_rate, 2)
    ot_pay = round(tot_ot_hours * ot_rate, 2)
    subtotal_pay = round(regular_pay + ot_pay, 2)
    
    rest_day_pay = round(tot_rest_day_hours * hourly_rate, 2)
    holiday_pay = round(tot_holiday_hours * hourly_rate, 2)
    
    meal_rate = float(req.meal_rate or 10.0)
    meal_allowance_pay = round(tot_meal_qty * meal_rate, 2)
    
    adjustment_add = float(req.adjustment_add or 0.0)
    total_pay = round(subtotal_pay + rest_day_pay + holiday_pay + meal_allowance_pay + adjustment_add, 2)
    
    # Deductions
    wps_deduction = float(req.wps_deduction or 0.0)
    water_bill = float(req.water_bill or 0.0)
    other_ded = float(req.other_deductions or 0.0)
    
    gosi_res = SaudiHREngine.calculate_gosi(emp["is_saudi"] == 1, total_pay, 0.0)
    gosi_emp = gosi_res["employee_deduction"]
    gosi_empr = gosi_res["employer_contribution"]
    
    total_deductions = round(wps_deduction + water_bill + other_ded + gosi_emp, 2)
    net_pay = max(0.0, round(total_pay - total_deductions, 2))
    
    cash_advance = float(req.cash_advance or 0.0)
    adjustment_sub = float(req.adjustment_sub or 0.0)
    actual_pay = max(0.0, round(net_pay - cash_advance - adjustment_sub, 2))
    
    # 4. Sync with Payroll Run & Payroll Details
    run = db.query_one("SELECT * FROM payroll_runs WHERE payroll_month = ? AND payroll_year = ?", (req.month, req.year))
    if not run:
        run_id = db.execute_cmd("""
            INSERT INTO payroll_runs (payroll_month, payroll_year, total_basic, total_allowances, total_deductions, total_net_pay, status, processed_at)
            VALUES (?, ?, 0.0, 0.0, 0.0, 0.0, 'Approved', ?)
        """, (req.month, req.year, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    else:
        run_id = run["id"]
        
    cutoff_period = req.cutoff_period or f"{datetime(req.year, req.month, 1).strftime('%B 01')}-{calendar.monthrange(req.year, req.month)[1]}, {req.year}"
    
    existing_detail = db.query_one("SELECT id FROM payroll_details WHERE payroll_run_id = ? AND employee_id = ?", (run_id, req.employee_id))
    if existing_detail:
        db.execute_cmd("""
            UPDATE payroll_details SET
                basic_salary = ?,
                housing_allowance = ?,
                transport_allowance = ?,
                other_allowances = ?,
                gross_salary = ?,
                gosi_employee = ?,
                gosi_employer = ?,
                other_deductions = ?,
                net_salary = ?,
                cutoff_period = ?,
                days_worked = ?,
                daily_rate = ?,
                hourly_rate = ?,
                ot_rate = ?,
                working_hours = ?,
                regular_pay = ?,
                ot_hours = ?,
                ot_pay = ?,
                subtotal_pay = ?,
                rest_day_hours = ?,
                rest_day_pay = ?,
                holiday_hours = ?,
                holiday_pay = ?,
                meal_allowance_qty = ?,
                meal_allowance_rate = ?,
                meal_allowance_pay = ?,
                adjustment_add = ?,
                total_pay = ?,
                wps_deduction = ?,
                water_bill = ?,
                total_deductions = ?,
                cash_advance = ?,
                adjustment_sub = ?,
                actual_pay = ?
            WHERE id = ?
        """, (
            regular_pay, meal_allowance_pay, 0.0, adjustment_add, total_pay, gosi_emp, gosi_empr, other_ded, net_pay,
            cutoff_period, days_worked, daily_rate, hourly_rate, ot_rate, tot_regular_hours, regular_pay,
            tot_ot_hours, ot_pay, subtotal_pay, tot_rest_day_hours, rest_day_pay, tot_holiday_hours, holiday_pay,
            tot_meal_qty, meal_rate, meal_allowance_pay, adjustment_add, total_pay,
            wps_deduction, water_bill, total_deductions, cash_advance, adjustment_sub, actual_pay,
            existing_detail["id"]
        ))
        detail_id = existing_detail["id"]
    else:
        detail_id = db.execute_cmd("""
            INSERT INTO payroll_details (
                payroll_run_id, employee_id, basic_salary, housing_allowance,
                transport_allowance, other_allowances, gross_salary,
                gosi_employee, gosi_employer, other_deductions, net_salary,
                cutoff_period, days_worked, daily_rate, hourly_rate, ot_rate,
                working_hours, regular_pay, ot_hours, ot_pay, subtotal_pay,
                rest_day_hours, rest_day_pay, holiday_hours, holiday_pay,
                meal_allowance_qty, meal_allowance_rate, meal_allowance_pay,
                adjustment_add, total_pay, wps_deduction, water_bill,
                total_deductions, cash_advance, adjustment_sub, actual_pay
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            run_id, req.employee_id, regular_pay, meal_allowance_pay, 0.0, adjustment_add, total_pay, gosi_emp, gosi_empr, other_ded, net_pay,
            cutoff_period, days_worked, daily_rate, hourly_rate, ot_rate, tot_regular_hours, regular_pay,
            tot_ot_hours, ot_pay, subtotal_pay, tot_rest_day_hours, rest_day_pay, tot_holiday_hours, holiday_pay,
            tot_meal_qty, meal_rate, meal_allowance_pay, adjustment_add, total_pay,
            wps_deduction, water_bill, total_deductions, cash_advance, adjustment_sub, actual_pay
        ))
        
    # Recompute parent run totals
    details = db.query_all("SELECT * FROM payroll_details WHERE payroll_run_id = ?", (run_id,))
    tot_basic = sum(float(d["basic_salary"] or 0) for d in details)
    tot_allowances = sum(float(d["housing_allowance"] or 0) + float(d["transport_allowance"] or 0) + float(d["other_allowances"] or 0) for d in details)
    tot_deductions = sum(float(d["gosi_employee"] or 0) + float(d["other_deductions"] or 0) for d in details)
    tot_net = sum(float(d["net_salary"] or 0) for d in details)
    
    db.execute_cmd("""
        UPDATE payroll_runs SET
            total_basic = ?,
            total_allowances = ?,
            total_deductions = ?,
            total_net_pay = ?
        WHERE id = ?
    """, (tot_basic, tot_allowances, tot_deductions, tot_net, run_id))
    
    return {
        "message": f"Timesheet calendar and payslip saved for {emp['first_name']} {emp['last_name']}",
        "detail_id": detail_id,
        "total_pay": total_pay,
        "net_pay": net_pay,
        "actual_pay": actual_pay,
        "working_hours": tot_regular_hours,
        "ot_hours": tot_ot_hours,
        "days_worked": days_worked
    }

@app.get("/api/payroll/monthly-roster/export/pdf")
def export_monthly_payroll_schedule_pdf(
    month: int = Query(..., ge=1, le=12),
    year: int = Query(..., ge=2020, le=2050),
    user: dict = Depends(get_current_user)
):
    """
    Generates an executive consolidated Monthly Payroll Schedule PDF using Playwright.
    """
    run = db.query_one("SELECT * FROM payroll_runs WHERE payroll_month = ? AND payroll_year = ?", (month, year))
    if not run:
        workers = []
    else:
        workers = db.query_all("""
            SELECT pd.*, e.emp_code, e.first_name, e.last_name, e.national_id_iqama, e.is_saudi, e.designation,
                   e.bank_name, e.iban, d.name as department_name
            FROM payroll_details pd
            JOIN employees e ON pd.employee_id = e.id
            LEFT JOIN departments d ON e.department_id = d.id
            WHERE pd.payroll_run_id = ?
            ORDER BY e.emp_code ASC, e.id ASC
        """, (run["id"],))
        
    setting_rows = db.query_all("SELECT * FROM settings")
    settings = {s["key"]: s["value"] for s in setting_rows}
    
    pdf_bytes = generate_monthly_payroll_schedule_pdf(month, year, workers, settings)
    filename = f"ADK_Payroll_Schedule_{month:02d}_{year}.pdf"
    
    return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": f"inline; filename={filename}"})

@app.get("/api/payroll/details/{detail_id}/payslip.pdf")
def download_payslip_pdf(
    detail_id: int,
    user: dict = Depends(get_current_user)
):
    detail = db.query_one("SELECT pd.*, pr.payroll_month, pr.payroll_year FROM payroll_details pd JOIN payroll_runs pr ON pd.payroll_run_id = pr.id WHERE pd.id = ?", (detail_id,))
    if not detail:
        raise HTTPException(status_code=404, detail="Payroll detail item not found.")
        
    emp = db.query_one("SELECT e.*, d.name as department_name FROM employees e LEFT JOIN departments d ON e.department_id = d.id WHERE e.id = ?", (detail["employee_id"],))
    
    setting_rows = db.query_all("SELECT * FROM settings")
    settings = {s["key"]: s["value"] for s in setting_rows}
    
    pay_data = {
        "month": detail["payroll_month"],
        "year": detail["payroll_year"],
        "cutoff_period": detail.get("cutoff_period"),
        "days_worked": detail.get("days_worked"),
        "daily_rate": detail.get("daily_rate"),
        "hourly_rate": detail.get("hourly_rate"),
        "ot_rate": detail.get("ot_rate"),
        "working_hours": detail.get("working_hours"),
        "regular_pay": detail.get("regular_pay"),
        "ot_hours": detail.get("ot_hours"),
        "ot_pay": detail.get("ot_pay"),
        "subtotal_pay": detail.get("subtotal_pay"),
        "rest_day_hours": detail.get("rest_day_hours"),
        "rest_day_rate": detail.get("rest_day_rate"),
        "rest_day_pay": detail.get("rest_day_pay"),
        "holiday_hours": detail.get("holiday_hours"),
        "holiday_rate": detail.get("holiday_rate"),
        "holiday_pay": detail.get("holiday_pay"),
        "meal_allowance_qty": detail.get("meal_allowance_qty"),
        "meal_allowance_rate": detail.get("meal_allowance_rate"),
        "meal_allowance_pay": detail.get("meal_allowance_pay") or detail.get("housing_allowance"),
        "adjustment_add": detail.get("adjustment_add") or detail.get("other_allowances"),
        "total_pay": detail.get("total_pay") or detail.get("gross_salary"),
        "wps_deduction": detail.get("wps_deduction"),
        "water_bill": detail.get("water_bill"),
        "gosi_employee": detail.get("gosi_employee"),
        "other_deductions": detail.get("other_deductions"),
        "total_deductions": detail.get("total_deductions"),
        "net_salary": detail.get("net_salary"),
        "cash_advance": detail.get("cash_advance"),
        "adjustment_sub": detail.get("adjustment_sub"),
        "actual_pay": detail.get("actual_pay")
    }
    
    pdf_bytes = generate_payslip_pdf(emp, pay_data, settings)
    filename = f"ADK_Payslip_{emp['emp_code']}_{detail['payroll_month']}_{detail['payroll_year']}.pdf"
    
    return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": f"inline; filename={filename}"})

@app.get("/api/payroll/runs/{run_id}/wps.csv")
def download_wps_file(run_id: int, user: dict = Depends(require_roles(["admin", "hr_manager"]))):
    run = db.query_one("SELECT * FROM payroll_runs WHERE id = ?", (run_id,))
    if not run:
        raise HTTPException(status_code=404, detail="Payroll run not found.")
        
    items = db.query_all("""
        SELECT pd.*, e.emp_code, e.first_name, e.last_name, e.national_id_iqama, e.bank_name, e.iban
        FROM payroll_details pd
        JOIN employees e ON pd.employee_id = e.id
        WHERE pd.payroll_run_id = ?
    """, (run_id,))
    
    records = []
    for item in items:
        records.append({
            "national_id_iqama": item["national_id_iqama"],
            "emp_name": f"{item['first_name']} {item['last_name']}",
            "bank_name": item["bank_name"],
            "iban": item["iban"],
            "basic_salary": item["basic_salary"],
            "housing_allowance": item["housing_allowance"],
            "transport_allowance": item["transport_allowance"],
            "other_allowances": item["other_allowances"],
            "gosi_employee": item["gosi_employee"],
            "other_deductions": item["other_deductions"],
            "net_salary": item["net_salary"]
        })
        
    setting_rows = db.query_all("SELECT * FROM settings")
    settings = {s["key"]: s["value"] for s in setting_rows}
    
    cr = settings.get("cr_number", "1010894512")
    mol = settings.get("mol_establishment_id", "7-889412")
    bank = settings.get("wps_bank_code", "RIBL")
    pay_date = date.today().strftime("%Y-%m-%d")
    
    csv_content = SaudiHREngine.generate_wps_csv(records, cr, mol, bank, pay_date)
    filename = f"WPS_Salary_File_{run['payroll_year']}_{run['payroll_month']:02d}.csv"
    
    return Response(content=csv_content, media_type="text/csv", headers={"Content-Disposition": f"attachment; filename={filename}"})

# --- Leave Management Endpoints ---
@app.get("/api/leaves")
def get_leaves(user: dict = Depends(get_current_user)):
    return db.query_all("""
        SELECT l.*, e.emp_code, e.first_name, e.last_name, d.name as department_name
        FROM leaves l
        JOIN employees e ON l.employee_id = e.id
        LEFT JOIN departments d ON e.department_id = d.id
        ORDER BY l.id DESC
    """)

@app.post("/api/leaves")
def apply_leave(req: LeaveCreate, user: dict = Depends(get_current_user)):
    emp = db.query_one("SELECT id FROM employees WHERE id = ?", (req.employee_id,))
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found.")
        
    if req.days <= 0:
        raise HTTPException(status_code=400, detail="Leave duration must be at least 1 day.")
        
    l_id = db.execute_cmd("""
        INSERT INTO leaves (employee_id, leave_type, start_date, end_date, days, reason, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, 'Pending', ?)
    """, (req.employee_id, req.leave_type, req.start_date, req.end_date, req.days, req.reason, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    
    return {"message": "Leave application submitted successfully", "id": l_id}

@app.put("/api/leaves/{leave_id}/status")
def update_leave_status(leave_id: int, body: LeaveStatusUpdate, user: dict = Depends(require_roles(["admin", "hr_manager"]))):
    existing = db.query_one("SELECT id FROM leaves WHERE id = ?", (leave_id,))
    if not existing:
        raise HTTPException(status_code=404, detail="Leave application not found.")
        
    db.execute_cmd("UPDATE leaves SET status = ? WHERE id = ?", (body.status, leave_id))
    return {"message": f"Leave status updated to {body.status}"}

@app.delete("/api/leaves/{leave_id}")
def delete_leave(leave_id: int, user: dict = Depends(require_roles(["admin", "hr_manager"]))):
    existing = db.query_one("SELECT id FROM leaves WHERE id = ?", (leave_id,))
    if not existing:
        raise HTTPException(status_code=404, detail="Leave record not found.")
        
    db.execute_cmd("DELETE FROM leaves WHERE id = ?", (leave_id,))
    return {"message": "Leave application record removed successfully"}

# --- Saudi Compliance Calculators ---
@app.post("/api/calculators/eosb")
def calculate_eosb_api(req: EOSBRequest, user: dict = Depends(get_current_user)):
    return SaudiHREngine.calculate_eosb(
        req.basic_salary,
        req.gross_salary,
        req.start_date,
        req.end_date,
        req.reason
    )

@app.post("/api/calculators/gosi")
def calculate_gosi_api(req: GOSIRequest, user: dict = Depends(get_current_user)):
    return SaudiHREngine.calculate_gosi(
        req.is_saudi,
        req.basic_salary,
        req.housing_allowance
    )

@app.get("/api/alerts/expiries")
def get_document_expiry_alerts(user: dict = Depends(get_current_user)):
    employees = db.query_all("SELECT * FROM employees WHERE status = 'Active'")
    return SaudiHREngine.check_expiries(employees, threshold_days=90)

# --- Settings ---
@app.get("/api/settings")
def get_settings(user: dict = Depends(get_current_user)):
    rows = db.query_all("SELECT * FROM settings")
    return {r["key"]: r["value"] for r in rows}

@app.post("/api/settings")
def update_settings(settings_dict: dict, user: dict = Depends(require_roles(["admin"]))):
    for k, v in settings_dict.items():
        db.execute_cmd("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (k, str(v)))
    return {"message": "Settings updated successfully"}
