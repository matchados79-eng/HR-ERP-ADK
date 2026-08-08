"""
Saudi Labor Law & Compliance Engine
Handles End of Service Benefit (EOSB) calculation per Articles 84 & 85,
GOSI contributions breakdown, Nitaqat Saudization color band mapping,
SAMA Wage Protection System (WPS) CSV file generation, and Expiry Alert tracking.
"""

from datetime import datetime, date
import csv
import io
from typing import List, Dict, Any

class SaudiHREngine:
    
    @staticmethod
    def calculate_eosb(basic_salary: float, gross_salary: float, start_date: str, end_date: str, reason: str = "contract_ended") -> Dict[str, Any]:
        """
        Calculates End of Service Benefit (EOSB / مكافأة نهاية الخدمة) per Saudi Labor Law (Articles 84 & 85).
        
        Args:
            basic_salary: Monthly basic salary (or gross if agreed by contract, defaulted to basic per standard practice)
            gross_salary: Total monthly gross salary
            start_date: Hire date (YYYY-MM-DD)
            end_date: Termination/Resignation date (YYYY-MM-DD)
            reason: Reason for leaving ('contract_ended', 'termination', 'resignation', 'force_majeure', 'female_marriage')
            
        Returns:
            Dict containing years of service, total gross benefit, resignation multiplier, net payable EOSB, and breakdown explanation.
        """
        # Parse dates
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
        
        # Base benefit calculation (Article 84)
        # First 5 years: 0.5 month salary per year
        # Beyond 5 years: 1.0 month salary per year for each additional year
        salary_base = basic_salary  # Saudi Labor Law standard is basic salary unless gross specified
        
        if years_of_service <= 5.0:
            raw_benefit = (years_of_service * 0.5) * salary_base
        else:
            first_5_years = (5.0 * 0.5) * salary_base
            additional_years = ((years_of_service - 5.0) * 1.0) * salary_base
            raw_benefit = first_5_years + additional_years
            
        # Resignation Multiplier (Article 85)
        multiplier = 1.0
        article_applied = "Article 84 (Full Payout)"
        notes = "Full benefit entitlement."
        
        if reason == "resignation":
            article_applied = "Article 85 (Resignation)"
            if years_of_service < 2.0:
                multiplier = 0.0
                notes = "Less than 2 years of service: 0% payout under Article 85."
            elif 2.0 <= years_of_service < 5.0:
                multiplier = 1.0 / 3.0  # 33.33%
                notes = "Between 2 and 5 years of service: 1/3 (33.33%) payout under Article 85."
            elif 5.0 <= years_of_service < 10.0:
                multiplier = 2.0 / 3.0  # 66.67%
                notes = "Between 5 and 10 years of service: 2/3 (66.67%) payout under Article 85."
            else:
                multiplier = 1.0  # 100%
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
        raw_benefit = round(raw_benefit, 2)
        years_of_service = round(years_of_service, 2)
        
        return {
            "years_of_service": years_of_service,
            "days_worked": days_worked,
            "monthly_base_salary": basic_salary,
            "raw_benefit": raw_benefit,
            "multiplier_percentage": round(multiplier * 100, 2),
            "net_eosb": net_eosb,
            "article": article_applied,
            "notes": notes
        }

    @staticmethod
    def calculate_gosi(is_saudi: bool, basic_salary: float, housing_allowance: float) -> Dict[str, Any]:
        """
        Calculates GOSI (General Organization for Social Insurance) contribution.
        
        Wage Cap: SAR 45,000 max eligible monthly base (Basic + Housing).
        Saudi Employees:
          - Employee Deduction: 9% Annuity + 0.75% SANED = 9.75%
          - Employer Contribution: 9% Annuity + 0.75% SANED + 2.0% Occupational Hazard = 11.75%
        Non-Saudi Employees:
          - Employee Deduction: 0%
          - Employer Contribution: 2.0% Occupational Hazard
        """
        gosi_base = min(basic_salary + housing_allowance, 45000.0)
        
        if is_saudi:
            emp_rate = 0.0975  # 9.75%
            empr_rate = 0.1175 # 11.75%
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
        """
        Calculates Saudization percentage and maps to Nitaqat Color Band.
        """
        if total_employees <= 0:
            rate = 0.0
        else:
            rate = round((saudi_employees / total_employees) * 100, 2)
            
        if rate >= 40.0:
            band = "Platinum"
            color = "#10B981"  # Emerald
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
            color = "#F59E0B"  # Yellow/Amber
            status = "Warning - Near Minimum Saudization Threshold"
        else:
            band = "Red"
            color = "#EF4444"  # Red
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
        """
        Generates SAMA (Saudi Central Bank) / MHRSD Wage Protection System (WPS) compliant CSV output.
        Format: Header record followed by employee salary lines.
        """
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header Row (WPS Standard Header)
        # Record Type, Company CR/MOL ID, Payment Date, Total Employees, Total Amount, Payer Bank Code
        total_amount = sum(r.get("net_salary", 0.0) for r in payroll_records)
        total_count = len(payroll_records)
        
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
    def check_expiries(employees: List[Dict[str, Any]], threshold_days: int = 60) -> List[Dict[str, Any]]:
        """
        Scans employees for expiring documents (Iqama, Passport, Contract).
        """
        alerts = []
        today = date.today()
        
        for emp in employees:
            emp_id = emp.get("id")
            emp_name = f"{emp.get('first_name', '')} {emp.get('last_name', '')}".strip()
            
            # Iqama Expiry
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
                    
            # Passport Expiry
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
                    
            # Contract Expiry
            contract_exp = emp.get("contract_end_date")
            if contract_exp:
                try:
                    exp_date = datetime.strptime(contract_exp, "%Y-%m-%d").date()
                    days_left = (exp_date - today).days
                    if days_left <= threshold_days:
                        alerts.append({
                            "employee_id": emp_id,
                            "employee_name": emp_name,
                            "doc_type": "Employment Contract",
                            "document_number": f"Contract-{emp.get('emp_code', '')}",
                            "expiry_date": contract_exp,
                            "days_remaining": days_left,
                            "severity": "CRITICAL" if days_left <= 15 else ("HIGH" if days_left <= 30 else "MEDIUM")
                        })
                except ValueError:
                    pass
                    
        return sorted(alerts, key=lambda x: x["days_remaining"])
