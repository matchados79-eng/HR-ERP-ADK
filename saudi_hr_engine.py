"""
Saudi Labor Law & SME Finance Analytics Engine
Handles EOSB, GOSI, Nitaqat, WPS CSV Generation, and Accounts Payable Aging Schedule & Finance Analytics.
"""

from datetime import datetime, date
import csv
import io
from typing import List, Dict, Any

class SaudiHREngine:
    
    @staticmethod
    def calculate_eosb(basic_salary: float, gross_salary: float, start_date: str, end_date: str, reason: str = "contract_ended") -> Dict[str, Any]:
        d1 = datetime.strptime(start_date, "%Y-%m-%d").date()
        d2 = datetime.strptime(end_date, "%Y-%m-%d").date()
        
        days_worked = (d2 - d1).days
        if days_worked <= 0:
            return {
                "years_of_service": 0.0,
                "days_worked": 0,
                "raw_benefit": 0.0,
                "multiplier": 0.0,
                "net_eosb": 0.0,
                "article": "Article 84/85",
                "notes": "Service duration is zero or invalid."
            }
            
        years_of_service = days_worked / 365.25
        salary_base = basic_salary
        
        if years_of_service <= 5.0:
            raw_benefit = (years_of_service * 0.5) * salary_base
        else:
            first_5_years = (5.0 * 0.5) * salary_base
            additional_years = ((years_of_service - 5.0) * 1.0) * salary_base
            raw_benefit = first_5_years + additional_years
            
        multiplier = 1.0
        article_applied = "Article 84 (Full Payout)"
        notes = "Full benefit entitlement."
        
        if reason == "resignation":
            article_applied = "Article 85 (Resignation)"
            if years_of_service < 2.0:
                multiplier = 0.0
                notes = "Less than 2 years of service: 0% payout under Article 85."
            elif 2.0 <= years_of_service < 5.0:
                multiplier = 1.0 / 3.0
                notes = "Between 2 and 5 years of service: 1/3 (33.33%) payout under Article 85."
            elif 5.0 <= years_of_service < 10.0:
                multiplier = 2.0 / 3.0
                notes = "Between 5 and 10 years of service: 2/3 (66.67%) payout under Article 85."
            else:
                multiplier = 1.0
                notes = "10 or more years of service: 100% payout under Article 85."
        elif reason in ["force_majeure", "female_marriage", "contract_ended", "termination"]:
            multiplier = 1.0
            if reason == "female_marriage":
                notes = "Female employee resigned within 6 months of marriage: 100% benefit per Article 87."
            elif reason == "force_majeure":
                notes = "Termination due to Force Majeure: 100% benefit per Article 87."
            elif reason == "termination":
                notes = "Employer termination (without Article 80 cause): 100% benefit."
            else:
                notes = "Fixed-term contract completion: 100% benefit."
                
        net_eosb = round(raw_benefit * multiplier, 2)
        
        return {
            "years_of_service": round(years_of_service, 2),
            "days_worked": days_worked,
            "monthly_base_salary": basic_salary,
            "raw_benefit": round(raw_benefit, 2),
            "multiplier_percentage": round(multiplier * 100, 2),
            "net_eosb": net_eosb,
            "article": article_applied,
            "notes": notes
        }

    @staticmethod
    def calculate_gosi(is_saudi: bool, basic_salary: float, housing_allowance: float) -> Dict[str, Any]:
        gosi_base = min(basic_salary + housing_allowance, 45000.0)
        
        if is_saudi:
            emp_rate = 0.0975
            empr_rate = 0.1175
            emp_deduction = round(gosi_base * emp_rate, 2)
            empr_contribution = round(gosi_base * empr_rate, 2)
            breakdown = {
                "saudi_annuity_emp": round(gosi_base * 0.09, 2),
                "saned_emp": round(gosi_base * 0.0075, 2),
                "saudi_annuity_empr": round(gosi_base * 0.09, 2),
                "saned_empr": round(gosi_base * 0.0075, 2),
                "hazard_empr": round(gosi_base * 0.02, 2),
            }
        else:
            emp_deduction = 0.0
            empr_contribution = round(gosi_base * 0.02, 2)
            breakdown = {
                "hazard_empr": round(gosi_base * 0.02, 2)
            }
            
        return {
            "is_saudi": is_saudi,
            "gosi_base": gosi_base,
            "employee_deduction": emp_deduction,
            "employer_contribution": empr_contribution,
            "total_gosi": round(emp_deduction + empr_contribution, 2),
            "breakdown": breakdown
        }

    @staticmethod
    def calculate_saudization(total_employees: int, saudi_employees: int) -> Dict[str, Any]:
        rate = round((saudi_employees / total_employees) * 100, 2) if total_employees > 0 else 0.0
            
        if rate >= 40.0:
            band = "Platinum"
            color = "#10B981"
            status = "Compliant - Top Tier Access to Visas & Services"
        elif rate >= 26.0:
            band = "High Green"
            color = "#059669"
            status = "Compliant - Standard Visa & HR Privileges"
        elif rate >= 16.0:
            band = "Medium Green"
            color = "#34D399"
            status = "Compliant - Basic Services Active"
        elif rate >= 10.0:
            band = "Low Green"
            color = "#F59E0B"
            status = "Warning - Near Minimum Saudization Threshold"
        else:
            band = "Red"
            color = "#EF4444"
            status = "Non-Compliant - Blocked Work Visas & Services"
            
        return {
            "total_employees": total_employees,
            "saudi_employees": saudi_employees,
            "expat_employees": total_employees - saudi_employees,
            "saudization_percentage": rate,
            "nitaqat_band": band,
            "nitaqat_color": color,
            "status_description": status
        }

    @staticmethod
    def generate_wps_csv(payroll_records: List[Dict[str, Any]], company_cr: str, company_mol_id: str, bank_code: str, payment_date: str) -> str:
        output = io.StringIO()
        writer = csv.writer(output)
        
        total_amount = sum(r.get("net_salary", 0.0) for r in payroll_records)
        writer.writerow(["HDR", company_cr, company_mol_id, payment_date, f"{total_amount:.2f}", bank_code, "SAR"])
        writer.writerow(["EmpID_NationalID_Iqama", "EmployeeName", "BankName", "IBAN", "BasicSalary", "HousingAllowance", "TransportAllowance", "OtherAllowances", "GOSIDeduction", "OtherDeductions", "NetSalary", "Currency"])
        
        for r in payroll_records:
            writer.writerow([
                r.get("national_id_iqama", ""),
                r.get("emp_name", ""),
                r.get("bank_name", ""),
                r.get("iban", ""),
                f"{r.get('basic_salary', 0.0):.2f}",
                f"{r.get('housing_allowance', 0.0):.2f}",
                f"{r.get('transport_allowance', 0.0):.2f}",
                f"{r.get('other_allowances', 0.0):.2f}",
                f"{r.get('gosi_employee', 0.0):.2f}",
                f"{r.get('other_deductions', 0.0):.2f}",
                f"{r.get('net_salary', 0.0):.2f}",
                "SAR"
            ])
            
        return output.getvalue()

    @staticmethod
    def calculate_accounts_payable_aging(supplier_payments: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Computes Accounts Payable Aging Schedule & SME Financial Metrics.
        Buckets: Current, 1-30 Days Overdue, 31-60 Days Overdue, 61-90 Days Overdue, 90+ Days Overdue.
        """
        today = date.today()
        
        aging_buckets = {
            "current": {"label": "Current (Not Overdue)", "count": 0, "amount": 0.0, "color": "#10B981"},
            "days_1_30": {"label": "1 - 30 Days Overdue", "count": 0, "amount": 0.0, "color": "#F59E0B"},
            "days_31_60": {"label": "31 - 60 Days Overdue", "count": 0, "amount": 0.0, "color": "#F97316"},
            "days_61_90": {"label": "61 - 90 Days Overdue", "count": 0, "amount": 0.0, "color": "#EF4444"},
            "days_90_plus": {"label": "90+ Days Overdue", "count": 0, "amount": 0.0, "color": "#991B1B"}
        }
        
        total_payable = 0.0
        total_overdue = 0.0
        total_paid = 0.0
        
        processed_payments = []
        
        for sp in supplier_payments:
            amt = float(sp.get("amount", 0.0))
            due_str = sp.get("due_date")
            status = sp.get("status", "Pending")
            
            days_overdue = 0
            aging_category = "Current"
            badge_class = "badge-active"
            
            if status == "Paid":
                total_paid += amt
                aging_category = "Paid & Settled"
                badge_class = "badge-saudi"
            else:
                total_payable += amt
                if due_str:
                    try:
                        due_d = datetime.strptime(due_str, "%Y-%m-%d").date()
                        days_overdue = (today - due_d).days
                    except ValueError:
                        days_overdue = 0
                        
                if days_overdue <= 0:
                    aging_buckets["current"]["count"] += 1
                    aging_buckets["current"]["amount"] += amt
                    aging_category = "Current"
                    badge_class = "badge-saudi"
                else:
                    total_overdue += amt
                    if days_overdue <= 30:
                        aging_buckets["days_1_30"]["count"] += 1
                        aging_buckets["days_1_30"]["amount"] += amt
                        aging_category = f"Overdue {days_overdue}d (1-30)"
                        badge_class = "badge-pending"
                    elif days_overdue <= 60:
                        aging_buckets["days_31_60"]["count"] += 1
                        aging_buckets["days_31_60"]["amount"] += amt
                        aging_category = f"Overdue {days_overdue}d (31-60)"
                        badge_class = "badge-pending"
                    elif days_overdue <= 90:
                        aging_buckets["days_61_90"]["count"] += 1
                        aging_buckets["days_61_90"]["amount"] += amt
                        aging_category = f"Overdue {days_overdue}d (61-90)"
                        badge_class = "badge-critical"
                    else:
                        aging_buckets["days_90_plus"]["count"] += 1
                        aging_buckets["days_90_plus"]["amount"] += amt
                        aging_category = f"Critical Overdue {days_overdue}d (90+)"
                        badge_class = "badge-critical"
                        
            sp_copy = dict(sp)
            sp_copy["days_overdue"] = max(0, days_overdue)
            sp_copy["aging_category"] = aging_category
            sp_copy["badge_class"] = badge_class
            processed_payments.append(sp_copy)
            
        overdue_ratio = round((total_overdue / total_payable * 100), 2) if total_payable > 0 else 0.0
        
        return {
            "summary": {
                "total_outstanding_payable": round(total_payable, 2),
                "total_overdue_payable": round(total_overdue, 2),
                "overdue_ratio_percentage": overdue_ratio,
                "total_settled_paid": round(total_paid, 2)
            },
            "aging_buckets": aging_buckets,
            "processed_payments": processed_payments
        }

    @staticmethod
    def check_expiries(employees: List[Dict[str, Any]], threshold_days: int = 60) -> List[Dict[str, Any]]:
        alerts = []
        today = date.today()
        
        for emp in employees:
            emp_id = emp.get("id")
            emp_name = f"{emp.get('first_name', '')} {emp.get('last_name', '')}".strip()
            
            iqama_exp = emp.get("iqama_expiry_date")
            if iqama_exp:
                try:
                    exp_date = datetime.strptime(iqama_exp, "%Y-%m-%d").date()
                    days_left = (exp_date - today).days
                    if days_left <= threshold_days:
                        alerts.append({
                            "employee_id": emp_id,
                            "employee_name": emp_name,
                            "doc_type": "Iqama / ID",
                            "document_number": emp.get("national_id_iqama", ""),
                            "expiry_date": iqama_exp,
                            "days_remaining": days_left,
                            "severity": "CRITICAL" if days_left <= 15 else ("HIGH" if days_left <= 30 else "MEDIUM")
                        })
                except ValueError:
                    pass
                    
            pass_exp = emp.get("passport_expiry_date")
            if pass_exp:
                try:
                    exp_date = datetime.strptime(pass_exp, "%Y-%m-%d").date()
                    days_left = (exp_date - today).days
                    if days_left <= threshold_days:
                        alerts.append({
                            "employee_id": emp_id,
                            "employee_name": emp_name,
                            "doc_type": "Passport",
                            "document_number": emp.get("passport_number", ""),
                            "expiry_date": pass_exp,
                            "days_remaining": days_left,
                            "severity": "CRITICAL" if days_left <= 15 else ("HIGH" if days_left <= 30 else "MEDIUM")
                        })
                except ValueError:
                    pass
                    
        return sorted(alerts, key=lambda x: x["days_remaining"])
