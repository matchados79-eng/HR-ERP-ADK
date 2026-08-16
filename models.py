from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List

class DepartmentCreate(BaseModel):
    name: str
    code: str
    manager_name: Optional[str] = None
    budget: Optional[float] = 0.0

class DepartmentUpdate(BaseModel):
    name: str
    code: str
    manager_name: Optional[str] = None
    budget: Optional[float] = 0.0

class EmployeeCreate(BaseModel):
    emp_code: str
    first_name: str
    last_name: str
    arabic_name: Optional[str] = None
    email: str
    phone: Optional[str] = None
    national_id_iqama: str
    nationality: str
    gender: Optional[str] = "Male"
    is_saudi: int = 1
    dob: Optional[str] = None
    department_id: Optional[int] = None
    designation: str
    hire_date: str
    contract_type: Optional[str] = "Fixed"
    contract_end_date: Optional[str] = None
    iqama_expiry_date: Optional[str] = None
    passport_number: Optional[str] = None
    passport_expiry_date: Optional[str] = None
    bank_name: Optional[str] = None
    iban: Optional[str] = None
    basic_salary: float = 0.0
    housing_allowance: float = 0.0
    transport_allowance: float = 0.0
    other_allowances: float = 0.0
    worker_type: Optional[str] = "Direct"  # 'Direct' (Site / Monthly / 30) or 'Indirect' (Regular Hourly)
    gosi_number: Optional[str] = None
    status: Optional[str] = "Active"

class EmployeeUpdate(BaseModel):
    emp_code: str
    first_name: str
    last_name: str
    arabic_name: Optional[str] = None
    email: str
    phone: Optional[str] = None
    national_id_iqama: str
    nationality: str
    gender: Optional[str] = "Male"
    is_saudi: int = 1
    dob: Optional[str] = None
    department_id: Optional[int] = None
    designation: str
    hire_date: str
    contract_type: Optional[str] = "Fixed"
    contract_end_date: Optional[str] = None
    iqama_expiry_date: Optional[str] = None
    passport_number: Optional[str] = None
    passport_expiry_date: Optional[str] = None
    bank_name: Optional[str] = None
    iban: Optional[str] = None
    basic_salary: float = 0.0
    housing_allowance: float = 0.0
    transport_allowance: float = 0.0
    other_allowances: float = 0.0
    gosi_number: Optional[str] = None
    status: Optional[str] = "Active"

class LeaveCreate(BaseModel):
    employee_id: int
    leave_type: str
    start_date: str
    end_date: str
    days: int
    reason: Optional[str] = None

class LeaveStatusUpdate(BaseModel):
    status: str

class SupplierCreate(BaseModel):
    name: str
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    cr_number: Optional[str] = None
    vat_number: Optional[str] = None
    bank_name: Optional[str] = None
    iban: Optional[str] = None
    payment_terms: Optional[str] = "Net 30"
    address: Optional[str] = None

class SupplierUpdate(BaseModel):
    name: str
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    cr_number: Optional[str] = None
    vat_number: Optional[str] = None
    bank_name: Optional[str] = None
    iban: Optional[str] = None
    payment_terms: Optional[str] = "Net 30"
    address: Optional[str] = None

class SupplierPaymentCreate(BaseModel):
    company_name: str
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    due_date: Optional[str] = None
    invoice_details: Optional[str] = None
    supply_date: Optional[str] = None
    supply_start_date: Optional[str] = None
    supply_end_date: Optional[str] = None
    amount: float = 0.0
    remarks: Optional[str] = None
    status: Optional[str] = "Pending"

class SupplierPaymentStatusUpdate(BaseModel):
    status: str
    payment_date: Optional[str] = None

class SupplierDisburseRequest(BaseModel):
    payment_amount: float
    payment_date: Optional[str] = None
    payment_method: Optional[str] = "Bank Transfer"
    reference_number: Optional[str] = None
    notes: Optional[str] = None

class EOSBRequest(BaseModel):
    basic_salary: float
    gross_salary: float
    start_date: str
    end_date: str
    reason: Optional[str] = "contract_ended"

class GOSIRequest(BaseModel):
    is_saudi: bool
    basic_salary: float
    housing_allowance: float

class PayrollRunRequest(BaseModel):
    month: int
    year: int

class WorkerMonthlyPayRequest(BaseModel):
    month: int
    year: int
    employee_id: int
    worker_type: Optional[str] = "Direct"
    basic_salary: float
    housing_allowance: Optional[float] = 0.0
    transport_allowance: Optional[float] = 0.0
    other_allowances: Optional[float] = 0.0
    other_deductions: Optional[float] = 0.0
    remarks: Optional[str] = None

    # Industrial Payslip Breakdown Fields
    cutoff_period: Optional[str] = None
    days_worked: Optional[float] = 30.0
    daily_rate: Optional[float] = None
    hourly_rate: Optional[float] = None
    ot_rate: Optional[float] = None
    working_hours: Optional[float] = None
    regular_pay: Optional[float] = None
    ot_hours: Optional[float] = 0.0
    ot_pay: Optional[float] = 0.0
    subtotal_pay: Optional[float] = None
    rest_day_hours: Optional[float] = 0.0
    rest_day_rate: Optional[float] = None
    rest_day_pay: Optional[float] = 0.0
    holiday_hours: Optional[float] = 0.0
    holiday_rate: Optional[float] = None
    holiday_pay: Optional[float] = 0.0
    meal_allowance_qty: Optional[float] = 0.0
    meal_allowance_rate: Optional[float] = 0.0
    meal_allowance_pay: Optional[float] = 0.0
    adjustment_add: Optional[float] = 0.0
    total_pay: Optional[float] = None
    wps_deduction: Optional[float] = 0.0
    water_bill: Optional[float] = 0.0
    total_deductions: Optional[float] = None
    cash_advance: Optional[float] = 0.0
    adjustment_sub: Optional[float] = 0.0
    actual_pay: Optional[float] = None

class BackupRestoreRequest(BaseModel):
    backup_json: Optional[str] = None

class DailyTimesheetEntry(BaseModel):
    day: int
    date: str
    regular_hours: float = 0.0
    ot_hours: float = 0.0
    day_type: str = "Regular"  # Regular, RestDay, Holiday, Leave, Absent
    meal_allowance: int = 0
    notes: Optional[str] = None

class BulkTimesheetSaveRequest(BaseModel):
    employee_id: int
    month: int
    year: int
    worker_type: Optional[str] = "Direct"
    cutoff_period: Optional[str] = None
    days: List[DailyTimesheetEntry]
    
    # Financial Deductions & Overrides
    water_bill: Optional[float] = 0.0
    wps_deduction: Optional[float] = 0.0
    other_deductions: Optional[float] = 0.0
    cash_advance: Optional[float] = 0.0
    adjustment_add: Optional[float] = 0.0
    adjustment_sub: Optional[float] = 0.0
    meal_rate: Optional[float] = 10.0
    daily_rate: Optional[float] = None
    hourly_rate: Optional[float] = None
    ot_rate: Optional[float] = None
    remarks: Optional[str] = None

