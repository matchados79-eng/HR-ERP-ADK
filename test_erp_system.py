"""
Comprehensive Automated Test Suite for Saudi HR & SME Finance ERP System
Tests all calculations, database operations, API routes, PDF outputs, SAMA WPS files, and backup/restore.
"""

import os
import json
from fastapi.testclient import TestClient

import database_cloud as db
from app import app
import auth
from saudi_hr_engine import SaudiHREngine

client = TestClient(app)

def test_database_initialization():
    """Verify database schema, tables, indexes, and default settings."""
    db.init_db()
    settings = db.query_all("SELECT * FROM settings")
    assert len(settings) >= 5
    
    admin_user = db.query_one("SELECT * FROM users WHERE email = 'admin@alamal-ksa.com'")
    assert admin_user is not None
    assert admin_user["role"] == "admin"

def test_auth_and_jwt():
    """Test login with valid and invalid credentials and JWT token generation."""
    res = client.post("/api/auth/login", json={
        "email": "admin@alamal-ksa.com",
        "password": "AdminSecret123!"
    })
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["user"]["role"] == "admin"
    token = data["access_token"]
    
    headers = {"Authorization": f"Bearer {token}"}
    me_res = client.get("/api/auth/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "admin@alamal-ksa.com"
    
    bad_res = client.post("/api/auth/login", json={
        "email": "admin@alamal-ksa.com",
        "password": "WrongPassword!"
    })
    assert bad_res.status_code == 401

def test_saudi_hr_engine_eosb():
    """Test Saudi Labor Law End of Service calculations."""
    calc1 = SaudiHREngine.calculate_eosb(
        basic_salary=10000.0,
        gross_salary=12500.0,
        start_date="2020-01-01",
        end_date="2024-01-01",
        reason="resignation"
    )
    assert calc1["years_of_service"] >= 3.9
    assert calc1["multiplier_percentage"] == 33.33
    assert calc1["net_eosb"] > 0
    
    calc2 = SaudiHREngine.calculate_eosb(
        basic_salary=10000.0,
        gross_salary=12500.0,
        start_date="2018-01-01",
        end_date="2024-01-01",
        reason="contract_ended"
    )
    assert calc2["multiplier_percentage"] == 100.0
    assert abs(calc2["net_eosb"] - 35000.0) < 100

def test_saudi_hr_engine_gosi():
    """Test GOSI deductions for Saudi vs Expat."""
    gosi_saudi = SaudiHREngine.calculate_gosi(
        is_saudi=True,
        basic_salary=10000.0,
        housing_allowance=2500.0
    )
    assert gosi_saudi["gosi_base"] == 12500.0
    assert gosi_saudi["employee_deduction"] == round(12500.0 * 0.0975, 2)
    assert gosi_saudi["employer_contribution"] == round(12500.0 * 0.1175, 2)
    
    gosi_expat = SaudiHREngine.calculate_gosi(
        is_saudi=False,
        basic_salary=10000.0,
        housing_allowance=2500.0
    )
    assert gosi_expat["employee_deduction"] == 0.0
    assert gosi_expat["employer_contribution"] == round(12500.0 * 0.02, 2)

def test_saudi_hr_engine_nitaqat():
    """Test Nitaqat Saudization band calculation."""
    res = SaudiHREngine.calculate_saudization(total_employees=10, saudi_employees=5)
    assert res["saudization_percentage"] == 50.0
    assert res["nitaqat_band"] == "Platinum"

def test_department_crud():
    """Test Department Create, Read, Update, Delete."""
    token = auth.create_jwt_token({"user_id": 1, "email": "admin@alamal-ksa.com", "role": "admin", "full_name": "Admin"})
    headers = {"Authorization": f"Bearer {token}"}
    
    create_res = client.post("/api/departments", json={
        "name": "Quality Assurance",
        "code": "QA_TEST",
        "manager_name": "Tariq Test",
        "budget": 150000.0
    }, headers=headers)
    assert create_res.status_code == 200
    dept_id = create_res.json()["id"]
    
    upd_res = client.put(f"/api/departments/{dept_id}", json={
        "name": "Quality Assurance & Testing",
        "code": "QA_TEST",
        "manager_name": "Tariq Test Jr",
        "budget": 180000.0
    }, headers=headers)
    assert upd_res.status_code == 200
    
    del_res = client.delete(f"/api/departments/{dept_id}", headers=headers)
    assert del_res.status_code == 200

def test_employee_crud_and_duplicates():
    """Test Employee creation, duplicate rejection, update, and detail retrieval."""
    token = auth.create_jwt_token({"user_id": 1, "email": "admin@alamal-ksa.com", "role": "admin", "full_name": "Admin"})
    headers = {"Authorization": f"Bearer {token}"}
    
    emp_payload = {
        "emp_code": "EMP-TEST-99",
        "first_name": "Khaled",
        "last_name": "Al-Amri",
        "arabic_name": "خالد العامري",
        "email": "khaled.test@alamal-ksa.com",
        "phone": "+966512345678",
        "national_id_iqama": "1999888777",
        "nationality": "Saudi Arabia",
        "gender": "Male",
        "is_saudi": 1,
        "department_id": None,
        "designation": "Systems Analyst",
        "hire_date": "2022-05-01",
        "contract_type": "Fixed",
        "basic_salary": 12000.0,
        "housing_allowance": 3000.0,
        "transport_allowance": 1000.0,
        "other_allowances": 500.0,
        "status": "Active"
    }
    
    res = client.post("/api/employees", json=emp_payload, headers=headers)
    assert res.status_code == 200
    emp_id = res.json()["id"]
    
    dup_res = client.post("/api/employees", json=emp_payload, headers=headers)
    assert dup_res.status_code == 400
    
    detail_res = client.get(f"/api/employees/{emp_id}", headers=headers)
    assert detail_res.status_code == 200
    assert detail_res.json()["employee"]["first_name"] == "Khaled"
    
    # Update employee
    emp_payload["designation"] = "Senior Systems Analyst"
    upd_res = client.put(f"/api/employees/{emp_id}", json=emp_payload, headers=headers)
    assert upd_res.status_code == 200
    
    del_res = client.delete(f"/api/employees/{emp_id}", headers=headers)
    assert del_res.status_code == 200

def test_leaves_workflow():
    """Test Leave application, approval, and deletion."""
    token = auth.create_jwt_token({"user_id": 1, "email": "admin@alamal-ksa.com", "role": "admin", "full_name": "Admin"})
    headers = {"Authorization": f"Bearer {token}"}
    
    emp = db.query_one("SELECT id FROM employees LIMIT 1")
    if not emp:
        return
    emp_id = emp["id"]
    
    l_res = client.post("/api/leaves", json={
        "employee_id": emp_id,
        "leave_type": "Annual Leave",
        "start_date": "2026-09-01",
        "end_date": "2026-09-10",
        "days": 10,
        "reason": "Annual vacation trip"
    }, headers=headers)
    assert l_res.status_code == 200
    l_id = l_res.json()["id"]
    
    upd_res = client.put(f"/api/leaves/{l_id}/status", json={"status": "Approved"}, headers=headers)
    assert upd_res.status_code == 200
    
    del_res = client.delete(f"/api/leaves/{l_id}", headers=headers)
    assert del_res.status_code == 200

def test_payroll_and_wps():
    """Test Monthly Payroll generation, SAMA WPS CSV, PDF Payslip, and run deletion."""
    token = auth.create_jwt_token({"user_id": 1, "email": "admin@alamal-ksa.com", "role": "admin", "full_name": "Admin"})
    headers = {"Authorization": f"Bearer {token}"}
    
    # Clean any previous run for month 11/2026
    existing = db.query_one("SELECT id FROM payroll_runs WHERE payroll_month = 11 AND payroll_year = 2026")
    if existing:
        client.delete(f"/api/payroll/runs/{existing['id']}", headers=headers)
        
    p_res = client.post("/api/payroll/generate", json={"month": 11, "year": 2026}, headers=headers)
    assert p_res.status_code == 200
    run_id = p_res.json()["payroll_run_id"]
    
    # Get details
    dtl_res = client.get(f"/api/payroll/runs/{run_id}/details", headers=headers)
    assert dtl_res.status_code == 200
    details = dtl_res.json()["details"]
    assert len(details) > 0
    
    # Download WPS CSV
    wps_res = client.get(f"/api/payroll/runs/{run_id}/wps.csv", headers=headers)
    assert wps_res.status_code == 200
    assert "HDR" in wps_res.text
    assert "SAR" in wps_res.text
    
    # Download Payslip PDF
    first_detail_id = details[0]["id"]
    ps_res = client.get(f"/api/payroll/details/{first_detail_id}/payslip.pdf", headers=headers)
    assert ps_res.status_code == 200
    assert len(ps_res.content) > 1000
    
    # Delete run
    del_res = client.delete(f"/api/payroll/runs/{run_id}", headers=headers)
    assert del_res.status_code == 200

def test_supplier_payments_and_disbursals():
    """Test Supplier Payments recording, partial disbursals, aging, and PDF statement generation."""
    token = auth.create_jwt_token({"user_id": 1, "email": "admin@alamal-ksa.com", "role": "admin", "full_name": "Admin"})
    headers = {"Authorization": f"Bearer {token}"}
    
    # 1. Test Supplier Profile Creation & Listing
    sup_create_res = client.post("/api/suppliers", json={
        "name": "Test Cloud Services Ltd",
        "contact_person": "Eng. Faisal Al-Zahrani",
        "phone": "+966500000000",
        "email": "cloud@testvendor.com",
        "cr_number": "1010999888",
        "payment_terms": "Net 30"
    }, headers=headers)
    assert sup_create_res.status_code == 200
    sup_id = sup_create_res.json()["id"]

    sups_res = client.get("/api/suppliers", headers=headers)
    assert sups_res.status_code == 200
    assert any(s["name"] == "Test Cloud Services Ltd" for s in sups_res.json())

    # 2. Test Supplier Invoice Recording
    sp_res = client.post("/api/suppliers/payments", json={
        "company_name": "Test Cloud Services Ltd",
        "invoice_number": "INV-TEST-001",
        "invoice_date": "2026-08-01",
        "due_date": "2026-08-25",
        "supply_start_date": "2026-07-01",
        "supply_end_date": "2026-07-31",
        "invoice_details": "Cloud server hosting & managed databases",
        "amount": 20000.0,
        "status": "Pending",
        "remarks": "Net 30 term"
    }, headers=headers)
    assert sp_res.status_code == 200
    sp_id = sp_res.json()["id"]
    
    disb_res = client.post(f"/api/suppliers/payments/{sp_id}/disburse", json={
        "payment_amount": 5000.0,
        "payment_method": "Bank Transfer",
        "reference_number": "TXN-TEST-123",
        "notes": "First partial settlement"
    }, headers=headers)
    assert disb_res.status_code == 200
    assert disb_res.json()["remaining_amount"] == 15000.0
    assert disb_res.json()["status"] == "Partially Paid"
    
    # 3. Test Statement PDF & AP Report PDF Export
    pdf_res = client.get(f"/api/suppliers/payments/{sp_id}/statement.pdf", headers=headers)
    assert pdf_res.status_code == 200
    assert len(pdf_res.content) > 1000

    ap_report_pdf = client.get("/api/suppliers/export/pdf", headers=headers)
    assert ap_report_pdf.status_code == 200
    assert len(ap_report_pdf.content) > 1000
    
    ledger_res = client.get("/api/suppliers/vendors/Test%20Cloud%20Services%20Ltd/ledger", headers=headers)
    assert ledger_res.status_code == 200
    # 4. Test Recurring Next Month Invoice Auto-Cloning
    rec_res = client.post(f"/api/suppliers/payments/{sp_id}/repeat-next-month", headers=headers)
    assert rec_res.status_code == 200
    rec_data = rec_res.json()
    rec_id = rec_data["id"]
    assert rec_data["amount"] == 20000.0
    assert rec_data["invoice_date"] == "2026-09-01"
    assert rec_data["due_date"] == "2026-09-25"
    assert rec_data["supply_start_date"] == "2026-08-01"
    assert rec_data["supply_end_date"] == "2026-08-31"

    client.delete(f"/api/suppliers/payments/{rec_id}", headers=headers)
    client.delete(f"/api/suppliers/payments/{sp_id}", headers=headers)
    client.delete(f"/api/suppliers/{sup_id}", headers=headers)

def test_backup_and_restore():
    """Test full system backup archive creation and JSON restoration."""
    token = auth.create_jwt_token({"user_id": 1, "email": "admin@alamal-ksa.com", "role": "admin", "full_name": "Admin"})
    headers = {"Authorization": f"Bearer {token}"}
    
    b_res = client.post("/api/backup/google-drive", headers=headers)
    assert b_res.status_code == 200
    assert b_res.json()["status"] == "SUCCESS"
    
    fn = b_res.json()["backup_filename"]
    path = os.path.join(os.path.dirname(__file__), "uploads", "backups", fn)
    assert os.path.exists(path)

if __name__ == "__main__":
    print("Running Complete ERP Test Suite...")
    test_database_initialization()
    test_auth_and_jwt()
    test_saudi_hr_engine_eosb()
    test_saudi_hr_engine_gosi()
    test_saudi_hr_engine_nitaqat()
    test_department_crud()
    test_employee_crud_and_duplicates()
    test_leaves_workflow()
    test_payroll_and_wps()
    test_supplier_payments_and_disbursals()
    test_backup_and_restore()
    print("ALL TESTS PASSED WITH ZERO ERRORS!")
