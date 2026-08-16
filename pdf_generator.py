import os
import io
from datetime import datetime, date
from typing import List, Dict, Any, Optional
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

# --- Modern Color Palette Tokens ---
COLOR_PRIMARY_DARK = colors.HexColor('#064E3B')   # Deep Saudi Forest Green
COLOR_PRIMARY_MED = colors.HexColor('#006C35')    # Classic Saudi Green
COLOR_PRIMARY_LIGHT = colors.HexColor('#ECFDF5')  # Soft Emerald Background
COLOR_PRIMARY_BORDER = colors.HexColor('#A7F3D0') # Light Green Border

COLOR_GOLD = colors.HexColor('#D97706')           # Executive Gold/Amber
COLOR_GOLD_BG = colors.HexColor('#FEF3C7')        # Soft Gold Background
COLOR_GOLD_BORDER = colors.HexColor('#FCD34D')    # Gold Border

COLOR_DANGER = colors.HexColor('#DC2626')         # Crimson Red (Due / Liability)
COLOR_DANGER_BG = colors.HexColor('#FEF2F2')      # Soft Red Background
COLOR_DANGER_BORDER = colors.HexColor('#FECACA')  # Red Border

COLOR_INFO = colors.HexColor('#2563EB')           # Royal Blue
COLOR_INFO_BG = colors.HexColor('#EFF6FF')        # Soft Blue Background
COLOR_INFO_BORDER = colors.HexColor('#BFDBFE')    # Blue Border

COLOR_NEUTRAL_BG = colors.HexColor('#F8FAFC')     # Slate 50 Neutral
COLOR_NEUTRAL_BORDER = colors.HexColor('#E2E8F0') # Slate 200 Border
COLOR_TEXT_MAIN = colors.HexColor('#0F172A')      # Slate 900
COLOR_TEXT_MUTED = colors.HexColor('#64748B')     # Slate 500

def get_modern_styles():
    """Builds a comprehensive typography hierarchy for executive PDF exports."""
    styles = getSampleStyleSheet()
    
    return {
        'doc_title': ParagraphStyle(
            'DocTitle',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=15,
            leading=18,
            textColor=COLOR_PRIMARY_DARK,
            alignment=2
        ),
        'doc_badge': ParagraphStyle(
            'DocBadge',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=8,
            leading=10,
            textColor=COLOR_GOLD,
            alignment=2
        ),
        'company_brand': ParagraphStyle(
            'CompanyBrand',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=12,
            leading=15,
            textColor=COLOR_PRIMARY_DARK
        ),
        'company_ar': ParagraphStyle(
            'CompanyArabic',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=9,
            leading=12,
            textColor=COLOR_TEXT_MUTED
        ),
        'company_meta': ParagraphStyle(
            'CompanyMeta',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=7.5,
            leading=10,
            textColor=COLOR_TEXT_MUTED
        ),
        'section_heading': ParagraphStyle(
            'SectionHeading',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=10,
            leading=13,
            textColor=COLOR_PRIMARY_DARK
        ),
        'kpi_label': ParagraphStyle(
            'KpiLabel',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=6.5,
            leading=8,
            textColor=COLOR_TEXT_MUTED
        ),
        'kpi_val_green': ParagraphStyle(
            'KpiValGreen',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=11,
            leading=13,
            textColor=COLOR_PRIMARY_DARK
        ),
        'kpi_val_red': ParagraphStyle(
            'KpiValRed',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=11,
            leading=13,
            textColor=COLOR_DANGER
        ),
        'kpi_val_blue': ParagraphStyle(
            'KpiValBlue',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=11,
            leading=13,
            textColor=COLOR_INFO
        ),
        'cell_text': ParagraphStyle(
            'CellText',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=7.5,
            leading=10,
            textColor=COLOR_TEXT_MAIN
        ),
        'cell_bold': ParagraphStyle(
            'CellBold',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=7.5,
            leading=10,
            textColor=COLOR_TEXT_MAIN
        ),
        'cell_white': ParagraphStyle(
            'CellWhite',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=7.5,
            leading=10,
            textColor=colors.white
        ),
        'cell_right': ParagraphStyle(
            'CellRight',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=7.5,
            leading=10,
            textColor=COLOR_TEXT_MAIN,
            alignment=2
        ),
        'cell_right_bold': ParagraphStyle(
            'CellRightBold',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=7.5,
            leading=10,
            textColor=COLOR_TEXT_MAIN,
            alignment=2
        ),
        'footer_note': ParagraphStyle(
            'FooterNote',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=6.5,
            leading=8.5,
            textColor=COLOR_TEXT_MUTED,
            alignment=1
        ),
        'sig_title': ParagraphStyle(
            'SigTitle',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=8,
            leading=10,
            textColor=COLOR_TEXT_MAIN,
            alignment=1
        ),
        'sig_sub': ParagraphStyle(
            'SigSub',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=7,
            leading=9,
            textColor=COLOR_TEXT_MUTED,
            alignment=1
        )
    }

def format_status_pill(status: str) -> str:
    """Renders a modern colored status badge in HTML Paragraph format."""
    st = (status or "Pending").strip()
    if st == "Paid":
        return "<font color='#059669'><b>● PAID</b></font>"
    elif st in ("Partially Paid", "Partial"):
        return "<font color='#D97706'><b>● PARTIAL</b></font>"
    elif st == "Approved":
        return "<font color='#2563EB'><b>● APPROVED</b></font>"
    else:
        return "<font color='#DC2626'><b>● PENDING</b></font>"


# =========================================================================
# 1. BILINGUAL SAUDI SALARY PAYSLIP PDF
# =========================================================================
def generate_payslip_pdf(employee_data: dict, payroll_detail: dict, company_info: dict) -> bytes:
    """
    Generates an official Bilingual Saudi Standard Payslip PDF with executive design.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=30,
        leftMargin=30,
        topMargin=28,
        bottomMargin=28
    )
    
    st = get_modern_styles()
    elements = []
    
    company_name = company_info.get("company_name", "Al-Amal Enterprise Solutions KSA")
    ar_name = company_info.get("company_arabic_name", "شركة الأمل لترشيد الحلول المتكاملة")
    cr_num = company_info.get("cr_number", "1010894512")
    gosi_reg = company_info.get("gosi_reg_number", "309481920")
    address = company_info.get("address", "King Fahd Road, Riyadh, Saudi Arabia")
    
    # 1. Executive Top Header
    header_data = [
        [
            Paragraph(f"<b>{company_name}</b><br/><font size=8 color='#064E3B'>{ar_name}</font><br/><font size=7 color='#64748B'>CR: {cr_num} • GOSI: {gosi_reg} • {address}</font>", st['company_meta']),
            Paragraph("<b>SALARY PAYSLIP VOUCHER</b><br/><font size=7.5 color='#D97706'><b>قسيمة الراتب الرسمية</b></font><br/><font size=7 color='#64748B'>Period: " + f"{payroll_detail.get('month', '')}/{payroll_detail.get('year', '')}</font>", st['doc_title'])
        ]
    ]
    header_table = Table(header_data, colWidths=[4.2*inch, 3.4*inch])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN', (1,0), (1,0), 'RIGHT'),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 4))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=COLOR_PRIMARY_DARK, spaceAfter=8))
    
    # 2. Employee Profile Metadata Grid
    emp_name = f"{employee_data.get('first_name', '')} {employee_data.get('last_name', '')}".strip()
    is_saudi = employee_data.get("is_saudi") == 1
    nat_type = "Saudi National (مواطن)" if is_saudi else "Expat / Non-Saudi (مقيم)"
    
    emp_info = [
        [
            Paragraph("<b>Employee Name:</b>", st['cell_bold']), Paragraph(emp_name, st['cell_text']),
            Paragraph("<b>Employee ID:</b>", st['cell_bold']), Paragraph(str(employee_data.get("emp_code", "N/A")), st['cell_text'])
        ],
        [
            Paragraph("<b>National ID / Iqama:</b>", st['cell_bold']), Paragraph(str(employee_data.get("national_id_iqama", "N/A")), st['cell_text']),
            Paragraph("<b>Department:</b>", st['cell_bold']), Paragraph(str(employee_data.get("department_name", "General")), st['cell_text'])
        ],
        [
            Paragraph("<b>Job Designation:</b>", st['cell_bold']), Paragraph(str(employee_data.get("designation", "N/A")), st['cell_text']),
            Paragraph("<b>Nationality Type:</b>", st['cell_bold']), Paragraph(nat_type, st['cell_text'])
        ],
        [
            Paragraph("<b>Bank / IBAN:</b>", st['cell_bold']), Paragraph(f"{employee_data.get('bank_name', 'Bank')} • {employee_data.get('iban', 'N/A')}", st['cell_text']),
            Paragraph("<b>GOSI Reg #:</b>", st['cell_bold']), Paragraph(str(employee_data.get("gosi_number", "N/A")), st['cell_text'])
        ]
    ]
    emp_table = Table(emp_info, colWidths=[1.4*inch, 2.4*inch, 1.3*inch, 2.5*inch])
    emp_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), COLOR_NEUTRAL_BG),
        ('BOX', (0,0), (-1,-1), 0.5, COLOR_NEUTRAL_BORDER),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#F1F5F9')),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    elements.append(emp_table)
    elements.append(Spacer(1, 8))
    
    # 3. KPI Quick Metrics Bar
    basic = float(payroll_detail.get("basic_salary", 0.0))
    housing = float(payroll_detail.get("housing_allowance", 0.0))
    transport = float(payroll_detail.get("transport_allowance", 0.0))
    other_allow = float(payroll_detail.get("other_allowances", 0.0))
    gross = float(payroll_detail.get("gross_salary", basic + housing + transport + other_allow))
    
    gosi_emp = float(payroll_detail.get("gosi_employee", 0.0))
    other_ded = float(payroll_detail.get("other_deductions", 0.0))
    total_ded = gosi_emp + other_ded
    net_pay = float(payroll_detail.get("net_salary", gross - total_ded))
    gosi_empr = float(payroll_detail.get("gosi_employer", 0.0))
    
    kpi_data = [
        [
            Paragraph("<b>BASIC SALARY</b>", st['kpi_label']),
            Paragraph("<b>GROSS EARNINGS</b>", st['kpi_label']),
            Paragraph("<b>TOTAL DEDUCTIONS</b>", st['kpi_label']),
            Paragraph("<b>NET TAKE-HOME PAY</b>", st['kpi_label'])
        ],
        [
            Paragraph(f"SAR {basic:,.2f}", st['kpi_val_green']),
            Paragraph(f"SAR {gross:,.2f}", st['kpi_val_blue']),
            Paragraph(f"SAR {total_ded:,.2f}", st['kpi_val_red']),
            Paragraph(f"<b>SAR {net_pay:,.2f}</b>", ParagraphStyle('NetHuge', parent=st['kpi_val_green'], fontSize=13, textColor=COLOR_PRIMARY_DARK))
        ]
    ]
    kpi_table = Table(kpi_data, colWidths=[1.9*inch, 1.9*inch, 1.9*inch, 1.9*inch])
    kpi_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (0,-1), COLOR_NEUTRAL_BG),
        ('BACKGROUND', (1,0), (1,-1), COLOR_INFO_BG),
        ('BACKGROUND', (2,0), (2,-1), COLOR_DANGER_BG),
        ('BACKGROUND', (3,0), (3,-1), COLOR_PRIMARY_LIGHT),
        ('BOX', (0,0), (-1,-1), 0.8, COLOR_PRIMARY_MED),
        ('INNERGRID', (0,0), (-1,-1), 0.5, COLOR_NEUTRAL_BORDER),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
    ]))
    elements.append(kpi_table)
    elements.append(Spacer(1, 10))
    
    # 4. Detailed Earnings & Deductions Breakdown
    elements.append(Paragraph("<b>Itemized Salary & Statutory Deductions Breakdown</b>", st['section_heading']))
    elements.append(Spacer(1, 4))
    
    fin_breakdown = [
        [
            Paragraph("Earnings Component", st['cell_white']), Paragraph("Amount (SAR)", st['cell_white']),
            Paragraph("Deductions & GOSI", st['cell_white']), Paragraph("Amount (SAR)", st['cell_white'])
        ],
        [
            Paragraph("Basic Salary (الراتب الأساسي)", st['cell_text']), Paragraph(f"{basic:,.2f}", st['cell_right']),
            Paragraph(f"GOSI Employee Share ({'9.75%' if is_saudi else '0%'})", st['cell_text']), Paragraph(f"{gosi_emp:,.2f}", st['cell_right'])
        ],
        [
            Paragraph("Housing Allowance (بدل سكن)", st['cell_text']), Paragraph(f"{housing:,.2f}", st['cell_right']),
            Paragraph("Other Disciplinary / Loan Deductions", st['cell_text']), Paragraph(f"{other_ded:,.2f}", st['cell_right'])
        ],
        [
            Paragraph("Transportation Allowance (بدل نقل)", st['cell_text']), Paragraph(f"{transport:,.2f}", st['cell_right']),
            Paragraph("-", st['cell_text']), Paragraph("-", st['cell_right'])
        ],
        [
            Paragraph("Other Allowances & Benefits (بدلات أخرى)", st['cell_text']), Paragraph(f"{other_allow:,.2f}", st['cell_right']),
            Paragraph("-", st['cell_text']), Paragraph("-", st['cell_right'])
        ],
        [
            Paragraph("<b>Total Gross Earnings:</b>", st['cell_bold']), Paragraph(f"<b>SAR {gross:,.2f}</b>", st['cell_right_bold']),
            Paragraph("<b>Total Deductions:</b>", st['cell_bold']), Paragraph(f"<b>SAR {total_ded:,.2f}</b>", st['cell_right_bold'])
        ]
    ]
    fin_table = Table(fin_breakdown, colWidths=[2.3*inch, 1.5*inch, 2.3*inch, 1.5*inch])
    fin_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), COLOR_PRIMARY_DARK),
        ('BOX', (0,0), (-1,-1), 0.5, COLOR_NEUTRAL_BORDER),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E5E7EB')),
        ('BACKGROUND', (0,-1), (-1,-1), COLOR_NEUTRAL_BG),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    elements.append(fin_table)
    elements.append(Spacer(1, 8))
    
    # Statutory Employer Contribution Note
    gosi_note = Paragraph(f"<font size=7 color='#64748B'>* Employer Statutory GOSI Contribution for this period: <b>SAR {gosi_empr:,.2f}</b> ({'11.75%' if is_saudi else '2.0%'} per Saudi Social Insurance Law).</font>", st['cell_text'])
    elements.append(gosi_note)
    elements.append(Spacer(1, 14))
    
    # 5. Dual Verification & Corporate Stamp Block
    sig_data = [
        [
            Paragraph("<b>AUTHORIZED COMPANY REPRESENTATIVE</b>", st['sig_title']),
            Paragraph("<b>EMPLOYEE ACKNOWLEDGMENT</b>", st['sig_title'])
        ],
        [
            Paragraph("HR & Payroll Operations Department<br/><br/>________________________________________<br/>Signature & Corporate Stamp", st['sig_sub']),
            Paragraph("I acknowledge receipt of full salary payment.<br/><br/>________________________________________<br/>Employee Signature & Date", st['sig_sub'])
        ]
    ]
    sig_table = Table(sig_data, colWidths=[3.8*inch, 3.8*inch])
    sig_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), COLOR_NEUTRAL_BG),
        ('BOX', (0,0), (-1,-1), 0.5, COLOR_NEUTRAL_BORDER),
        ('INNERGRID', (0,0), (-1,-1), 0.5, COLOR_NEUTRAL_BORDER),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    elements.append(sig_table)
    elements.append(Spacer(1, 8))
    
    elements.append(Paragraph("This payroll voucher is electronically certified and fully compliant with the Saudi Ministry of Human Resources (MHRSD) & SAMA WPS regulations.", st['footer_note']))
    
    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


# =========================================================================
# 2. VENDOR STATEMENT OF ACCOUNT & PAYMENT VOUCHER PDF
# =========================================================================
def generate_supplier_statement_pdf(sp: dict, payment_logs: list, company_info: dict) -> bytes:
    """
    Generates an executive-grade Supplier Statement & Payment Voucher PDF.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=30,
        leftMargin=30,
        topMargin=28,
        bottomMargin=28
    )
    
    st = get_modern_styles()
    elements = []
    
    company_name = company_info.get("company_name", "Al-Amal Enterprise Solutions KSA")
    ar_name = company_info.get("company_arabic_name", "شركة الأمل لترشيد الحلول المتكاملة")
    cr_num = company_info.get("cr_number", "1010894512")
    address = company_info.get("address", "King Fahd Road, Riyadh, Saudi Arabia")
    
    total_amt = float(sp.get("amount", 0.0))
    paid_amt = float(sp.get("paid_amount", 0.0))
    rem_amt = float(sp.get("remaining_amount", max(0.0, total_amt - paid_amt)))
    
    start_d = sp.get("supply_start_date") or sp.get("supply_date", "")
    end_d = sp.get("supply_end_date") or sp.get("supply_date", "")
    supply_period = f"{start_d} to {end_d}" if start_d and end_d and start_d != end_d else (start_d or "N/A")
    
    # 1. Executive Top Header
    header_data = [
        [
            Paragraph(f"<b>{company_name}</b><br/><font size=8 color='#064E3B'>{ar_name}</font><br/><font size=7 color='#64748B'>CR: {cr_num} • {address}</font>", st['company_meta']),
            Paragraph("<b>VENDOR STATEMENT OF ACCOUNT</b><br/><font size=7.5 color='#D97706'><b>كشف حساب المورد وسند الصرف</b></font><br/><font size=7 color='#64748B'>Generated: " + datetime.now().strftime("%Y-%m-%d %H:%M") + "</font>", st['doc_title'])
        ]
    ]
    header_table = Table(header_data, colWidths=[4.2*inch, 3.4*inch])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN', (1,0), (1,0), 'RIGHT'),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 4))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=COLOR_PRIMARY_DARK, spaceAfter=8))
    
    # 2. Executive KPI Cards
    kpi_data = [
        [
            Paragraph("<b>TOTAL BILLED</b>", st['kpi_label']),
            Paragraph("<b>TOTAL DISBURSED</b>", st['kpi_label']),
            Paragraph("<b>OUTSTANDING BALANCE</b>", st['kpi_label']),
            Paragraph("<b>INVOICE STATUS</b>", st['kpi_label'])
        ],
        [
            Paragraph(f"SAR {total_amt:,.2f}", st['kpi_val_blue']),
            Paragraph(f"SAR {paid_amt:,.2f}", st['kpi_val_green']),
            Paragraph(f"<b>SAR {rem_amt:,.2f}</b>", st['kpi_val_red']),
            Paragraph(format_status_pill(sp.get("status", "Pending")), st['cell_bold'])
        ]
    ]
    kpi_table = Table(kpi_data, colWidths=[1.9*inch, 1.9*inch, 1.9*inch, 1.9*inch])
    kpi_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (0,-1), COLOR_INFO_BG),
        ('BACKGROUND', (1,0), (1,-1), COLOR_PRIMARY_LIGHT),
        ('BACKGROUND', (2,0), (2,-1), COLOR_DANGER_BG),
        ('BACKGROUND', (3,0), (3,-1), COLOR_NEUTRAL_BG),
        ('BOX', (0,0), (-1,-1), 0.8, COLOR_PRIMARY_MED),
        ('INNERGRID', (0,0), (-1,-1), 0.5, COLOR_NEUTRAL_BORDER),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
    ]))
    elements.append(kpi_table)
    elements.append(Spacer(1, 10))
    
    # 3. Invoice & Vendor Metadata Card
    inv_info = [
        [
            Paragraph("<b>Vendor Company:</b>", st['cell_bold']), Paragraph(str(sp.get("company_name", "")), st['cell_text']),
            Paragraph("<b>Invoice Number:</b>", st['cell_bold']), Paragraph(str(sp.get("invoice_number", "N/A")), st['cell_text'])
        ],
        [
            Paragraph("<b>Invoice Date:</b>", st['cell_bold']), Paragraph(str(sp.get("invoice_date", "")), st['cell_text']),
            Paragraph("<b>Payment Due Date:</b>", st['cell_bold']), Paragraph(str(sp.get("due_date", "")), st['cell_text'])
        ],
        [
            Paragraph("<b>Supply Period:</b>", st['cell_bold']), Paragraph(supply_period, st['cell_text']),
            Paragraph("<b>System Record ID:</b>", st['cell_bold']), Paragraph(f"#INV-{sp.get('id', '')}", st['cell_text'])
        ],
        [
            Paragraph("<b>Service / Item Details:</b>", st['cell_bold']), Paragraph(str(sp.get("invoice_details", "N/A")), st['cell_text']),
            Paragraph("<b>Internal Notes:</b>", st['cell_bold']), Paragraph(str(sp.get("remarks", "N/A")), st['cell_text'])
        ]
    ]
    inv_table = Table(inv_info, colWidths=[1.4*inch, 2.4*inch, 1.3*inch, 2.5*inch])
    inv_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), COLOR_NEUTRAL_BG),
        ('BOX', (0,0), (-1,-1), 0.5, COLOR_NEUTRAL_BORDER),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#F1F5F9')),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    elements.append(inv_table)
    elements.append(Spacer(1, 10))
    
    # 4. Disbursal Transaction History Table
    elements.append(Paragraph("<b>Disbursal Settlements & Transaction Logs</b>", st['section_heading']))
    elements.append(Spacer(1, 4))
    
    log_rows = [
        [
            Paragraph("Settlement Date", st['cell_white']),
            Paragraph("Payment Method", st['cell_white']),
            Paragraph("Reference / Transaction #", st['cell_white']),
            Paragraph("Notes & Settlement Details", st['cell_white']),
            Paragraph("Amount Disbursed (SAR)", st['cell_white'])
        ]
    ]
    
    if not payment_logs:
        log_rows.append([Paragraph("No payments disbursed yet. Full amount remains outstanding.", st['cell_text']), Paragraph("-", st['cell_text']), Paragraph("-", st['cell_text']), Paragraph("-", st['cell_text']), Paragraph("SAR 0.00", st['cell_right'])])
    else:
        for idx, lg in enumerate(payment_logs):
            bg_color = COLOR_NEUTRAL_BG if idx % 2 == 1 else colors.white
            amt_lg = float(lg.get("payment_amount", 0.0))
            log_rows.append([
                Paragraph(str(lg.get("payment_date", "")), st['cell_text']),
                Paragraph(str(lg.get("payment_method", "Bank Transfer")), st['cell_text']),
                Paragraph(str(lg.get("reference_number", "N/A")), st['cell_text']),
                Paragraph(str(lg.get("notes", "N/A")), st['cell_text']),
                Paragraph(f"<b>SAR {amt_lg:,.2f}</b>", st['cell_right_bold'])
            ])
            
    history_table = Table(log_rows, colWidths=[1.1*inch, 1.3*inch, 1.4*inch, 2.2*inch, 1.6*inch])
    history_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), COLOR_PRIMARY_DARK),
        ('BOX', (0,0), (-1,-1), 0.5, COLOR_NEUTRAL_BORDER),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E5E7EB')),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    elements.append(history_table)
    elements.append(Spacer(1, 14))
    
    # 5. Signatures Block
    sig_data = [
        [
            Paragraph("<b>ACCOUNTS PAYABLE CONTROLLER</b>", st['sig_title']),
            Paragraph("<b>VENDOR RECEIVER ACKNOWLEDGMENT</b>", st['sig_title'])
        ],
        [
            Paragraph("Finance & Treasury Department<br/><br/>________________________________________<br/>Signature & Company Stamp", st['sig_sub']),
            Paragraph("Authorized Commercial Representative<br/><br/>________________________________________<br/>Signature & Official Stamp", st['sig_sub'])
        ]
    ]
    sig_table = Table(sig_data, colWidths=[3.8*inch, 3.8*inch])
    sig_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), COLOR_NEUTRAL_BG),
        ('BOX', (0,0), (-1,-1), 0.5, COLOR_NEUTRAL_BORDER),
        ('INNERGRID', (0,0), (-1,-1), 0.5, COLOR_NEUTRAL_BORDER),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    elements.append(sig_table)
    elements.append(Spacer(1, 8))
    
    elements.append(Paragraph("This official statement of account is issued under Saudi Commercial Law and serves as verified proof of AP settlement.", st['footer_note']))
    
    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


# =========================================================================
# 3. EXECUTIVE ACCOUNTS PAYABLE & MULTI-SUPPLIER SCHEDULE REPORT PDF
# =========================================================================
def generate_supplier_summary_report_pdf(
    invoices: List[Dict[str, Any]],
    summary_stats: Dict[str, Any],
    company_info: Dict[str, Any],
    filter_info: Optional[Dict[str, Any]] = None
) -> bytes:
    """
    Generates a modern, executive-grade Accounts Payable & Supplier Invoices Report PDF
    with multi-supplier selection support, vendor subtotals, and luxury Saudi corporate styling.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=26,
        leftMargin=26,
        topMargin=26,
        bottomMargin=26
    )
    
    st = get_modern_styles()
    elements = []
    
    company_name = company_info.get("company_name", "Al-Amal Enterprise Solutions KSA")
    ar_name = company_info.get("company_arabic_name", "شركة الأمل لترشيد الحلول المتكاملة")
    cr_num = company_info.get("cr_number", "1010894512")
    address = company_info.get("address", "King Fahd Road, Riyadh, Saudi Arabia")
    
    # 1. Executive Top Header
    header_data = [
        [
            Paragraph(f"<b>{company_name}</b><br/><font size=8 color='#064E3B'>{ar_name}</font><br/><font size=7 color='#64748B'>CR: {cr_num} • {address}</font>", st['company_meta']),
            Paragraph("<b>ACCOUNTS PAYABLE REPORT</b><br/><font size=7.5 color='#D97706'><b>جدول التزامات الموردين والمستحقات</b></font><br/><font size=7 color='#64748B'>Generated: " + datetime.now().strftime("%Y-%m-%d %H:%M") + "</font>", st['doc_title'])
        ]
    ]
    header_table = Table(header_data, colWidths=[4.3*inch, 3.4*inch])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN', (1,0), (1,0), 'RIGHT'),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 3))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=COLOR_PRIMARY_DARK, spaceAfter=6))
    
    # 2. Scope & Filter Parameters Box
    f_info = filter_info or {}
    sel_sups = f_info.get("selected_suppliers", "All Registered Suppliers")
    st_filter = f_info.get("status", "All Statuses")
    date_scope = f_info.get("date_range", "All Historical Invoices")
    
    meta_data = [
        [
            Paragraph("<b>Target Suppliers:</b>", st['cell_bold']), Paragraph(str(sel_sups), st['cell_text']),
            Paragraph("<b>Generated On:</b>", st['cell_bold']), Paragraph(datetime.now().strftime("%Y-%m-%d %H:%M"), st['cell_text'])
        ],
        [
            Paragraph("<b>Payment Status Scope:</b>", st['cell_bold']), Paragraph(str(st_filter), st['cell_text']),
            Paragraph("<b>Invoice Date Filter:</b>", st['cell_bold']), Paragraph(str(date_scope), st['cell_text'])
        ]
    ]
    meta_table = Table(meta_data, colWidths=[1.3*inch, 3.1*inch, 1.1*inch, 2.2*inch])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), COLOR_NEUTRAL_BG),
        ('BOX', (0,0), (-1,-1), 0.5, COLOR_NEUTRAL_BORDER),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#F1F5F9')),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
    ]))
    elements.append(meta_table)
    elements.append(Spacer(1, 6))
    
    # 3. KPI Executive Summary Cards
    tot_billed = float(summary_stats.get("total_billed", sum(float(i.get("amount", 0)) for i in invoices)))
    tot_paid = float(summary_stats.get("total_paid", sum(float(i.get("paid_amount", 0)) for i in invoices)))
    tot_rem = float(summary_stats.get("total_outstanding_payable", sum(float(i.get("remaining_amount", 0)) for i in invoices)))
    tot_over = float(summary_stats.get("total_overdue_payable", 0.0))
    
    kpi_data = [
        [
            Paragraph("<b>TOTAL INVOICES</b>", st['kpi_label']),
            Paragraph("<b>TOTAL BILLED</b>", st['kpi_label']),
            Paragraph("<b>TOTAL DISBURSED</b>", st['kpi_label']),
            Paragraph("<b>NET LIABILITY DUE</b>", st['kpi_label'])
        ],
        [
            Paragraph(f"{len(invoices)} Records", st['kpi_val_blue']),
            Paragraph(f"SAR {tot_billed:,.2f}", st['kpi_val_blue']),
            Paragraph(f"SAR {tot_paid:,.2f}", st['kpi_val_green']),
            Paragraph(f"<b>SAR {tot_rem:,.2f}</b>", ParagraphStyle('NetHugeRed', parent=st['kpi_val_red'], fontSize=11.5, textColor=COLOR_DANGER))
        ]
    ]
    kpi_table = Table(kpi_data, colWidths=[1.92*inch, 1.92*inch, 1.92*inch, 1.92*inch])
    kpi_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (0,-1), COLOR_NEUTRAL_BG),
        ('BACKGROUND', (1,0), (1,-1), COLOR_INFO_BG),
        ('BACKGROUND', (2,0), (2,-1), COLOR_PRIMARY_LIGHT),
        ('BACKGROUND', (3,0), (3,-1), COLOR_DANGER_BG),
        ('BOX', (0,0), (-1,-1), 0.8, COLOR_PRIMARY_MED),
        ('INNERGRID', (0,0), (-1,-1), 0.5, COLOR_NEUTRAL_BORDER),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
    ]))
    elements.append(kpi_table)
    elements.append(Spacer(1, 8))
    
    # 4. Grouped Supplier Tables
    grouped = {}
    for inv in invoices:
        c_name = inv.get("company_name", "Other Vendors")
        if c_name not in grouped:
            grouped[c_name] = []
        grouped[c_name].append(inv)
        
    for vendor_name, v_invoices in grouped.items():
        v_billed = sum(float(i.get("amount", 0.0)) for i in v_invoices)
        v_paid = sum(float(i.get("paid_amount", 0.0)) for i in v_invoices)
        v_rem = sum(float(i.get("remaining_amount", max(0.0, float(i.get("amount", 0.0)) - float(i.get("paid_amount", 0.0))))) for i in v_invoices)
        
        # Vendor Section Banner
        v_header_data = [
            [
                Paragraph(f"🏢 <b>Supplier: {vendor_name}</b> <font size=6.5 color='#64748B'>({len(v_invoices)} Invoices)</font>", ParagraphStyle('VTitle', parent=st['cell_bold'], textColor=COLOR_PRIMARY_DARK, fontSize=8.5)),
                Paragraph(f"Billed: <b>SAR {v_billed:,.2f}</b> | Paid: <font color='#059669'><b>SAR {v_paid:,.2f}</b></font> | Balance Due: <font color='#DC2626'><b>SAR {v_rem:,.2f}</b></font>", ParagraphStyle('VRight', parent=st['cell_text'], alignment=2, fontSize=7.5))
            ]
        ]
        v_header_table = Table(v_header_data, colWidths=[4.3*inch, 3.4*inch])
        v_header_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F1F5F9')),
            ('BOX', (0,0), (-1,-1), 0.5, COLOR_NEUTRAL_BORDER),
            ('TOPPADDING', (0,0), (-1,-1), 3),
            ('BOTTOMPADDING', (0,0), (-1,-1), 3),
            ('LEFTPADDING', (0,0), (-1,-1), 5),
            ('RIGHTPADDING', (0,0), (-1,-1), 5),
        ]))
        elements.append(v_header_table)
        elements.append(Spacer(1, 1))
        
        # Invoice Rows
        rows = [
            [
                Paragraph("Invoice #", st['cell_white']),
                Paragraph("Invoice Date", st['cell_white']),
                Paragraph("Supply Period", st['cell_white']),
                Paragraph("Due Date", st['cell_white']),
                Paragraph("Billed (SAR)", st['cell_white']),
                Paragraph("Paid (SAR)", st['cell_white']),
                Paragraph("Balance (SAR)", st['cell_white']),
                Paragraph("Status", st['cell_white'])
            ]
        ]
        
        for idx, inv in enumerate(v_invoices):
            start_d = inv.get("supply_start_date") or inv.get("supply_date", "")
            end_d = inv.get("supply_end_date") or inv.get("supply_date", "")
            period = f"{start_d} to {end_d}" if start_d and end_d and start_d != end_d else (start_d or "N/A")
            
            amt = float(inv.get("amount", 0.0))
            pd = float(inv.get("paid_amount", 0.0))
            rem = float(inv.get("remaining_amount", max(0.0, amt - pd)))
            st_text = str(inv.get("status", "Pending"))
            
            rows.append([
                Paragraph(str(inv.get('invoice_number', 'N/A')), st['cell_text']),
                Paragraph(str(inv.get('invoice_date', '')), st['cell_text']),
                Paragraph(period, st['cell_text']),
                Paragraph(str(inv.get('due_date', '')), st['cell_text']),
                Paragraph(f"{amt:,.2f}", st['cell_right']),
                Paragraph(f"{pd:,.2f}", st['cell_right']),
                Paragraph(f"<b>{rem:,.2f}</b>", ParagraphStyle('RedCell', parent=st['cell_right_bold'], textColor=COLOR_DANGER if rem > 0 else COLOR_TEXT_MAIN)),
                Paragraph(format_status_pill(st_text), st['cell_text'])
            ])
            
        t = Table(rows, colWidths=[1.1*inch, 0.8*inch, 1.6*inch, 0.8*inch, 0.85*inch, 0.85*inch, 0.9*inch, 0.85*inch])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), COLOR_PRIMARY_DARK),
            ('BOX', (0,0), (-1,-1), 0.5, COLOR_NEUTRAL_BORDER),
            ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#F1F5F9')),
            ('TOPPADDING', (0,0), (-1,-1), 3),
            ('BOTTOMPADDING', (0,0), (-1,-1), 3),
            ('LEFTPADDING', (0,0), (-1,-1), 4),
            ('RIGHTPADDING', (0,0), (-1,-1), 4),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 6))
        
    # 5. Grand Totals Summary Bar
    grand_data = [
        [
            Paragraph("<b>GRAND TOTALS (CONSOLIDATED SCOPE):</b>", ParagraphStyle('GTL', parent=st['cell_bold'], fontSize=7.5)),
            Paragraph(f"<b>Billed: SAR {tot_billed:,.2f}</b>", st['cell_bold']),
            Paragraph(f"<b>Disbursed: SAR {tot_paid:,.2f}</b>", ParagraphStyle('GP', parent=st['cell_bold'], textColor=COLOR_PRIMARY_DARK)),
            Paragraph(f"<b>Total Net Due: <font color='#DC2626'>SAR {tot_rem:,.2f}</font></b>", st['cell_bold'])
        ]
    ]
    gt_table = Table(grand_data, colWidths=[2.8*inch, 1.6*inch, 1.6*inch, 1.7*inch])
    gt_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), COLOR_GOLD_BG),
        ('BOX', (0,0), (-1,-1), 1, COLOR_GOLD),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    elements.append(gt_table)
    elements.append(Spacer(1, 10))
    
    # 6. Corporate Signatures Block
    sig_data = [
        [
            Paragraph("<b>PREPARED BY: ACCOUNTS PAYABLE OFFICER</b>", st['sig_title']),
            Paragraph("<b>APPROVED BY: CHIEF FINANCIAL OFFICER (CFO)</b>", st['sig_title'])
        ],
        [
            Paragraph("Treasury & Accounts Payable Division<br/><br/>________________________________________<br/>Signature & Review Stamp", st['sig_sub']),
            Paragraph("Executive Financial Management<br/><br/>________________________________________<br/>Authorized Signature & Corporate Seal", st['sig_sub'])
        ]
    ]
    sig_table = Table(sig_data, colWidths=[3.85*inch, 3.85*inch])
    sig_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), COLOR_NEUTRAL_BG),
        ('BOX', (0,0), (-1,-1), 0.5, COLOR_NEUTRAL_BORDER),
        ('INNERGRID', (0,0), (-1,-1), 0.5, COLOR_NEUTRAL_BORDER),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    elements.append(sig_table)
    elements.append(Spacer(1, 4))
    
    elements.append(Paragraph("This accounts payable report is generated by the Cloud ERP System in compliance with Saudi Corporate & Financial Standards.", st['footer_note']))
    
    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
