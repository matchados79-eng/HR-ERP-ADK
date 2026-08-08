import os
import uuid
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
from google_drive_backup import generate_full_backup_archive
from models import (
    DepartmentCreate, EmployeeCreate, LeaveCreate, LeaveStatusUpdate,
    EOSBRequest, GOSIRequest, PayrollRunRequest
)
from saudi_hr_engine import SaudiHREngine
from pdf_generator import generate_payslip_pdf

# Initialize DB
db.init_db()

app = FastAPI(
    title="Saudi HR ERP System - Production Cloud Edition",
    description="Production-grade Saudi HR & Payroll ERP System deployed on Vercel + Supabase with Auth & Google Drive Backups",
    version="3.0.0"
)

# Enable CORS for local & Vercel access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(__file__)

if os.environ.get("VERCEL"):
    UPLOADS_PHOTOS_DIR = os.path.join(tempfile.gettempdir(), "photos")
    UPLOADS_DOCS_DIR = os.path.join(tempfile.gettempdir(), "documents")
else:
    UPLOADS_PHOTOS_DIR = os.path.join(BASE_DIR, "uploads", "photos")
    UPLOADS_DOCS_DIR = os.path.join(BASE_DIR, "uploads", "documents")

os.makedirs(UPLOADS_PHOTOS_DIR, exist_ok=True)
os.makedirs(UPLOADS_DOCS_DIR, exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")

if os.path.exists(os.path.join(BASE_DIR, "uploads")):
    app.mount("/uploads", StaticFiles(directory=os.path.join(BASE_DIR, "uploads")), name="uploads")

class LoginRequest(BaseModel):
    email: str
    password: str

class UserCreateRequest(BaseModel):
    email: str
    password: str
    full_name: str
    role: str = "viewer" # 'admin', 'hr_manager', 'viewer'

# Strict Dependency for Authenticated Requests
def get_current_user(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authentication required. Please log in first.")
    token = authorization.split(" ")[1]
    payload = auth.verify_jwt_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired JWT session. Please log in again.")
    return payload

# Role Checker Helper
def require_roles(allowed_roles: List[str]):
    def role_checker(user: dict = Depends(get_current_user)):
        if user.get("role") not in allowed_roles:
            raise HTTPException(status_code=403, detail="Permission denied. Your role does not have access to this feature.")
        return user
    return role_checker

# --- UI Route ---
@app.get("/", response_class=HTMLResponse)
def read_root():
    index_path = os.path.join(BASE_DIR, "static", "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Saudi HR ERP System Production Running</h1>"

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

# --- Automated Google Drive Backup Endpoint ---
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

# --- Dashboard Overview Endpoint ---
@app.get("/api/dashboard/stats")
def get_dashboard_stats(user: dict = Depends(get_current_user)):
    employees = db.query_all("SELECT * FROM employees WHERE status = 'Active'")
    total_emp = len(employees)
    saudi_emp = sum(1 for e in employees if e["is_saudi"] == 1)
    expat_emp = total_emp - saudi_emp
    
    saudization_info = SaudiHREngine.calculate_saudization(total_emp, saudi_emp)
    total_payroll = sum((e["basic_salary"] + e["housing_allowance"] + e["transport_allowance"] + e["other_allowances"]) for e in employees)
    pending_leaves = db.query_all("SELECT COUNT(*) as cnt FROM leaves WHERE status = 'Pending'")[0]["cnt"]
    alerts = SaudiHREngine.check_expiries(employees, threshold_days=60)
    
    depts = db.query_all("""
        SELECT d.name, COUNT(e.id) as emp_count
        FROM departments d
        LEFT JOIN employees e ON d.id = e.department_id AND e.status = 'Active'
        GROUP BY d.id
    """)
    
    return {
        "total_employees": total_emp,
        "saudi_employees": saudi_emp,
        "expat_employees": expat_emp,
        "saudization": saudization_info,
        "total_monthly_payroll": total_payroll if user["role"] in ["admin", "hr_manager"] else 0.0,
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
    """)

@app.post("/api/departments")
def create_department(dept: DepartmentCreate, user: dict = Depends(require_roles(["admin", "hr_manager"]))):
    d_id = db.execute_cmd(
        "INSERT INTO departments (name, code, manager_name, budget) VALUES (?, ?, ?, ?)",
        (dept.name, dept.code, dept.manager_name, dept.budget)
    )
    return {"message": "Department created successfully", "id": d_id}

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
        sql += " AND (e.first_name LIKE ? OR e.last_name LIKE ? OR e.emp_code LIKE ? OR e.national_id_iqama LIKE ?)"
        pattern = f"%{search}%"
        params.extend([pattern, pattern, pattern, pattern])
        
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
    
    # Hide salary details if user is 'viewer'
    if user["role"] == "viewer":
        for r in results:
            r["basic_salary"] = 0.0
            r["housing_allowance"] = 0.0
            r["transport_allowance"] = 0.0
            r["other_allowances"] = 0.0
            
    return results

@app.post("/api/employees")
def create_employee(emp: EmployeeCreate, user: dict = Depends(require_roles(["admin", "hr_manager"]))):
    existing = db.query_one("SELECT id FROM employees WHERE emp_code = ? OR national_id_iqama = ?", (emp.emp_code, emp.national_id_iqama))
    if existing:
        raise HTTPException(status_code=400, detail="Employee Code or Iqama/National ID already exists.")
        
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
    return {"message": "Employee created successfully", "id": e_id}

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
        
    # Redact salary for viewer
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
def update_employee(emp_id: int, emp: EmployeeCreate, user: dict = Depends(require_roles(["admin", "hr_manager"]))):
    existing = db.query_one("SELECT id FROM employees WHERE id = ?", (emp_id,))
    if not existing:
        raise HTTPException(status_code=404, detail="Employee not found.")
        
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

# --- Image Upload Endpoint ---
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

# --- Document Upload Endpoint ---
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

@app.get("/api/documents/{doc_id}/download")
def download_document(doc_id: int, user: dict = Depends(get_current_user)):
    doc = db.query_one("SELECT * FROM documents WHERE id = ?", (doc_id,))
    if not doc:
        raise HTTPException(status_code=404, detail="Document record not found.")
        
    full_path = os.path.join(BASE_DIR, doc["file_path"])
    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="Document file does not exist on disk.")
        
    return FileResponse(full_path, filename=doc["file_name"])

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
        basic = emp["basic_salary"]
        housing = emp["housing_allowance"]
        transport = emp["transport_allowance"]
        other = emp["other_allowances"]
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
        
    l_id = db.execute_cmd("""
        INSERT INTO leaves (employee_id, leave_type, start_date, end_date, days, reason, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, 'Pending', ?)
    """, (req.employee_id, req.leave_type, req.start_date, req.end_date, req.days, req.reason, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    
    return {"message": "Leave application submitted successfully", "id": l_id}

@app.put("/api/leaves/{leave_id}/status")
def update_leave_status(leave_id: int, body: LeaveStatusUpdate, user: dict = Depends(require_roles(["admin", "hr_manager"]))):
    db.execute_cmd("UPDATE leaves SET status = ? WHERE id = ?", (body.status, leave_id))
    return {"message": f"Leave status updated to {body.status}"}

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
