import os
import uuid
import json
import zipfile
import shutil
import tempfile
from datetime import datetime, date
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
    SupplierPaymentCreate, SupplierPaymentStatusUpdate, SupplierDisburseRequest,
    BackupRestoreRequest
)
from saudi_hr_engine import SaudiHREngine
from pdf_generator import generate_payslip_pdf, generate_supplier_statement_pdf

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
else:
    UPLOADS_PHOTOS_DIR = os.path.join(BASE_DIR, "uploads", "photos")
    UPLOADS_DOCS_DIR = os.path.join(BASE_DIR, "uploads", "documents")
    UPLOADS_BACKUPS_DIR = os.path.join(BASE_DIR, "uploads", "backups")

os.makedirs(UPLOADS_PHOTOS_DIR, exist_ok=True)
os.makedirs(UPLOADS_DOCS_DIR, exist_ok=True)
os.makedirs(UPLOADS_BACKUPS_DIR, exist_ok=True)

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

# --- Authentication & User Management Endpoints ---
@app.post("/api/auth/login")
def login(req: LoginRequest):
    user = db.query_one("SELECT * FROM users WHERE email = ?", (req.email,))
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
    """, emp.dict())
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
    
    return {"message": "Supplier payment record updated successfully"}

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

@app.delete("/api/suppliers/payments/{sp_id}")
def delete_supplier_payment(sp_id: int, user: dict = Depends(require_roles(["admin"]))):
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

@app.get("/api/payroll/details/{detail_id}/payslip.pdf")
def download_payslip_pdf(detail_id: int, user: dict = Depends(require_roles(["admin", "hr_manager"]))):
    detail = db.query_one("SELECT pd.*, pr.payroll_month, pr.payroll_year FROM payroll_details pd JOIN payroll_runs pr ON pd.payroll_run_id = pr.id WHERE pd.id = ?", (detail_id,))
    if not detail:
        raise HTTPException(status_code=404, detail="Payroll detail item not found.")
        
    emp = db.query_one("SELECT e.*, d.name as department_name FROM employees e LEFT JOIN departments d ON e.department_id = d.id WHERE e.id = ?", (detail["employee_id"],))
    
    setting_rows = db.query_all("SELECT * FROM settings")
    settings = {s["key"]: s["value"] for s in setting_rows}
    
    pay_data = {
        "month": detail["payroll_month"],
        "year": detail["payroll_year"],
        "basic_salary": detail["basic_salary"],
        "housing_allowance": detail["housing_allowance"],
        "transport_allowance": detail["transport_allowance"],
        "other_allowances": detail["other_allowances"],
        "gross_salary": detail["gross_salary"],
        "gosi_employee": detail["gosi_employee"],
        "gosi_employer": detail["gosi_employer"],
        "other_deductions": detail["other_deductions"],
        "net_salary": detail["net_salary"]
    }
    
    pdf_bytes = generate_payslip_pdf(emp, pay_data, settings)
    filename = f"Payslip_{emp['emp_code']}_{detail['payroll_month']}_{detail['payroll_year']}.pdf"
    
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
