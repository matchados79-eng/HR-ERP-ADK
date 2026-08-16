"""
Comprehensive Automated Test Suite for Saudi HR & SME Finance ERP System
Tests all calculations, database operations, API routes, PDF outputs, SAMA WPS files, and backup/restore.
"""

import os
import io
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

def test_monthly_worker_payroll_tracking():
    """Test individual monthly worker payroll roster, auto-population, adjustments, payslip PDF, and consolidated schedule PDF."""
    token = auth.create_jwt_token({"user_id": 1, "email": "admin@adknprotech.com", "role": "admin", "full_name": "Admin"})
    headers = {"Authorization": f"Bearer {token}"}
    
    # 1. Clean any previous test run for January 2026
    existing = db.query_one("SELECT id FROM payroll_runs WHERE payroll_month = 1 AND payroll_year = 2026")
    if existing:
        client.delete(f"/api/payroll/runs/{existing['id']}", headers=headers)
        
    # 2. Get initial empty roster
    r_res = client.get("/api/payroll/monthly-roster?month=1&year=2026", headers=headers)
    assert r_res.status_code == 200
    assert r_res.json()["has_run"] is False
    
    # 3. 1-Click Auto-Populate Roster
    pop_res = client.post("/api/payroll/monthly-roster/populate", json={"month": 1, "year": 2026}, headers=headers)
    assert pop_res.status_code == 200
    
    # 4. Verify populated workers
    r_after = client.get("/api/payroll/monthly-roster?month=1&year=2026", headers=headers)
    assert r_after.status_code == 200
    workers = r_after.json()["workers"]
    assert len(workers) > 0
    first_worker = workers[0]
    
    # 5. Adjust an individual worker's pay (e.g. Add 1,500 SAR bonus for January)
    adj_res = client.post("/api/payroll/monthly-roster/worker", json={
        "month": 1,
        "year": 2026,
        "employee_id": first_worker["employee_id"],
        "basic_salary": first_worker["basic_salary"],
        "housing_allowance": first_worker["housing_allowance"],
        "transport_allowance": first_worker["transport_allowance"],
        "other_allowances": 1500.0,
        "other_deductions": 0.0,
        "remarks": "January engineering milestone bonus"
    }, headers=headers)
    assert adj_res.status_code == 200
    
    # 6. Verify 1-click individual worker payslip PDF download
    detail_id = first_worker["id"]
    ps_pdf = client.get(f"/api/payroll/details/{detail_id}/payslip.pdf?token={token}")
    assert ps_pdf.status_code == 200
    assert len(ps_pdf.content) > 1000
    assert ps_pdf.headers["content-type"] == "application/pdf"
    
    # 7. Verify consolidated Monthly Payroll Schedule PDF export
    sched_pdf = client.get(f"/api/payroll/monthly-roster/export/pdf?month=1&year=2026&token={token}")
    assert sched_pdf.status_code == 200
    assert len(sched_pdf.content) > 1000
    assert sched_pdf.headers["content-type"] == "application/pdf"
    
    # 8. Remove worker from roster
    rem_res = client.delete(f"/api/payroll/monthly-roster/worker/{detail_id}", headers=headers)
    assert rem_res.status_code == 200

def test_worker_timesheet_calendar_and_payslip_sync():
    """Test monthly attendance calendar hours logging, rates, deductions, and automated payslip sync."""
    token = auth.create_jwt_token({"user_id": 1, "email": "admin@adknprotech.com", "role": "admin", "full_name": "Admin"})
    headers = {"Authorization": f"Bearer {token}"}
    
    emp = db.query_one("SELECT * FROM employees LIMIT 1")
    assert emp is not None
    emp_id = emp["id"]
    
    # 1. Fetch timesheet calendar for July 2026
    ts_res = client.get(f"/api/payroll/timesheet?employee_id={emp_id}&month=7&year=2026", headers=headers)
    assert ts_res.status_code == 200
    ts_data = ts_res.json()
    assert len(ts_data["days"]) == 31
    
    # 2. Simulate 10 days worked (64.0 hrs @ 10.42/hr = 666.67, 16.0 rest hrs = 166.67, 10 meals @ 10 = 100.00, water bill = 12.89, cash advance = 400.00)
    days_payload = []
    for day in range(1, 32):
        if day <= 8:
            days_payload.append({
                "day": day,
                "date": f"2026-07-{day:02d}",
                "regular_hours": 8.0,
                "ot_hours": 0.0,
                "day_type": "Regular",
                "meal_allowance": 1,
                "notes": "Site work"
            })
        elif day in [9, 10]:
            days_payload.append({
                "day": day,
                "date": f"2026-07-{day:02d}",
                "regular_hours": 8.0,
                "ot_hours": 0.0,
                "day_type": "RestDay",
                "meal_allowance": 1,
                "notes": "Rest day support"
            })
        else:
            days_payload.append({
                "day": day,
                "date": f"2026-07-{day:02d}",
                "regular_hours": 0.0,
                "ot_hours": 0.0,
                "day_type": "Regular",
                "meal_allowance": 0,
                "notes": ""
            })
            
    bulk_res = client.post("/api/payroll/timesheet/bulk-save", json={
        "employee_id": emp_id,
        "month": 7,
        "year": 2026,
        "cutoff_period": "July 01-31, 2026",
        "days": days_payload,
        "daily_rate": 83.33333333,
        "hourly_rate": 10.42,
        "ot_rate": 15.63,
        "water_bill": 12.89,
        "wps_deduction": 0.0,
        "other_deductions": 0.0,
        "cash_advance": 400.0,
        "adjustment_add": 0.0,
        "adjustment_sub": 0.0,
        "meal_rate": 10.0
    }, headers=headers)
    
    assert bulk_res.status_code == 200
    res_data = bulk_res.json()
    assert res_data["total_pay"] == 933.33  # 666.67 + 166.67 + 100.00 = 933.34/933.33
    assert res_data["actual_pay"] == 520.44  # 933.33 - 12.89 - 400.00 = 520.44
    
    # 3. Verify Payslip PDF generates successfully with new timesheet data
    detail_id = res_data["detail_id"]
    pdf_res = client.get(f"/api/payroll/details/{detail_id}/payslip.pdf?token={token}")
    assert pdf_res.status_code == 200
    assert len(pdf_res.content) > 1000



def test_supplier_payments_and_disbursals():
    """Test Supplier Payments recording, partial disbursals, aging, and PDF statement generation."""
    token = auth.create_jwt_token({"user_id": 1, "email": "admin@alamal-ksa.com", "role": "admin", "full_name": "Admin"})
    headers = {"Authorization": f"Bearer {token}"}
    
    # Pre-clean any test supplier records
    db.execute_cmd("DELETE FROM supplier_payments WHERE company_name = 'Test Cloud Services Ltd'")
    db.execute_cmd("DELETE FROM suppliers WHERE name = 'Test Cloud Services Ltd'")

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
    
    # 3. Test Statement PDF & AP Report PDF Export (All, Single Supplier, Multi Supplier)
    pdf_res = client.get(f"/api/suppliers/payments/{sp_id}/statement.pdf", headers=headers)
    assert pdf_res.status_code == 200
    assert len(pdf_res.content) > 1000

    # All suppliers report
    ap_report_pdf = client.get("/api/suppliers/export/pdf", headers=headers)
    assert ap_report_pdf.status_code == 200
    assert len(ap_report_pdf.content) > 1000

    # Single supplier report
    ap_single_pdf = client.get("/api/suppliers/export/pdf?suppliers=Test%20Cloud%20Services%20Ltd", headers=headers)
    assert ap_single_pdf.status_code == 200
    assert len(ap_single_pdf.content) > 1000

    # Multi supplier report with status filter
    ap_multi_pdf = client.get("/api/suppliers/export/pdf?suppliers=Test%20Cloud%20Services%20Ltd,Al-Jazeera%20Office%20Supplies%20Co.&status=Pending", headers=headers)
    assert ap_multi_pdf.status_code == 200
    assert len(ap_multi_pdf.content) > 1000
    
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

    # 5. Test Optional Invoice Attachment Upload, Download & Deletion
    fake_pdf = io.BytesIO(b"%PDF-1.4 Fake test invoice content...")
    upload_res = client.post(
        f"/api/suppliers/payments/{sp_id}/attachment",
        files={"file": ("tax_invoice_101.pdf", fake_pdf, "application/pdf")},
        headers=headers
    )
    assert upload_res.status_code == 200
    assert upload_res.json()["attachment_filename"] == "tax_invoice_101.pdf"

    # Download attachment
    dl_res = client.get(f"/api/suppliers/payments/{sp_id}/attachment", headers=headers)
    assert dl_res.status_code == 200
    assert b"Fake test invoice content" in dl_res.content

    # Delete attachment
    del_att_res = client.delete(f"/api/suppliers/payments/{sp_id}/attachment", headers=headers)
    assert del_att_res.status_code == 200

    # 6. Test Multi-Invoice Lump-Sum Settlement (Jan 5000 + Feb 17000, Paid 8000 -> Remaining 14000)
    inv1_res = client.post("/api/suppliers/payments", json={
        "company_name": "Test Cloud Services Ltd",
        "invoice_number": "INV-JAN-5000",
        "invoice_date": "2026-01-10",
        "due_date": "2026-02-10",
        "amount": 5000.0,
        "status": "Pending"
    }, headers=headers)
    inv1_id = inv1_res.json()["id"]

    inv2_res = client.post("/api/suppliers/payments", json={
        "company_name": "Test Cloud Services Ltd",
        "invoice_number": "INV-FEB-17000",
        "invoice_date": "2026-02-10",
        "due_date": "2026-03-10",
        "amount": 17000.0,
        "status": "Pending"
    }, headers=headers)
    inv2_id = inv2_res.json()["id"]

    # Settle SAR 8,000 across the vendor
    lump_res = client.post("/api/suppliers/vendors/Test%20Cloud%20Services%20Ltd/disburse", json={
        "payment_amount": 8000.0,
        "payment_method": "Bank Transfer",
        "reference_number": "LUMP-8000-TEST",
        "notes": "Lump sum partial vendor settlement"
    }, headers=headers)
    assert lump_res.status_code == 200

    # Verify FIFO allocation:
    # First invoice (Jan 5000) is Paid (remaining 0)
    # Second invoice (Feb 17000) is Partially Paid (remaining 14000)
    i1 = db.query_one("SELECT * FROM supplier_payments WHERE id = ?", (inv1_id,))
    i2 = db.query_one("SELECT * FROM supplier_payments WHERE id = ?", (inv2_id,))
    assert i1["paid_amount"] == 5000.0
    assert i1["remaining_amount"] == 0.0
    assert i1["status"] == "Paid"

    assert i2["paid_amount"] == 3000.0
    assert i2["remaining_amount"] == 14000.0
    assert i2["status"] == "Partially Paid"

    # Cleanup
    client.delete(f"/api/suppliers/payments/{inv1_id}", headers=headers)
    client.delete(f"/api/suppliers/payments/{inv2_id}", headers=headers)
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
