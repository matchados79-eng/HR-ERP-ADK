import os
import io
from datetime import datetime, date
from typing import List, Dict, Any, Optional
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

# =========================================================================
# MODERN FINTECH COLOR SYSTEM (Stripe / Linear / Saudi Luxury Green Theme)
# =========================================================================
COLOR_BRAND_DARK      = colors.HexColor('#064E3B')   # Deep Emerald Slate
COLOR_BRAND_PRIMARY   = colors.HexColor('#047857')   # Modern Forest Green
COLOR_BRAND_LIGHT     = colors.HexColor('#F0FDF4')   # Ultra-soft Mint
COLOR_BRAND_BORDER    = colors.HexColor('#BBF7D0')   # Soft Mint Border

COLOR_GOLD_ACCENT     = colors.HexColor('#B45309')   # Warm Amber / Gold
COLOR_GOLD_BG         = colors.HexColor('#FFFBEB')   # Warm Sand
COLOR_GOLD_BORDER     = colors.HexColor('#FDE68A')   # Soft Gold Border

COLOR_CRIMSON         = colors.HexColor('#B91C1C')   # Clean Crimson Red
COLOR_CRIMSON_BG      = colors.HexColor('#FEF2F2')   # Soft Red Tint
COLOR_CRIMSON_BORDER  = colors.HexColor('#FECACA')   # Light Red Border

COLOR_BLUE            = colors.HexColor('#1D4ED8')   # Modern Corporate Blue
COLOR_BLUE_BG         = colors.HexColor('#EFF6FF')   # Soft Blue Tint
COLOR_BLUE_BORDER     = colors.HexColor('#BFDBFE')   # Light Blue Border

COLOR_CARD_BG         = colors.HexColor('#F8FAFC')   # Clean Slate 50
COLOR_CARD_BORDER     = colors.HexColor('#E2E8F0')   # Subtle Slate 200 Border
COLOR_ROW_ALT         = colors.HexColor('#FAFAFA')   # Subtle Off-White Zebra
COLOR_DIVIDER         = colors.HexColor('#F1F5F9')   # Ultra-light Line

COLOR_TEXT_TITLE      = colors.HexColor('#0F172A')   # Slate 900
COLOR_TEXT_BODY       = colors.HexColor('#334155')   # Slate 700
COLOR_TEXT_MUTED      = colors.HexColor('#64748B')   # Slate 500
COLOR_TEXT_FAINT      = colors.HexColor('#94A3B8')   # Slate 400

MONTH_NAMES = ["", "January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]

def format_long_date(date_val: Optional[str]) -> str:
    """Formats 'YYYY-MM-DD' into clean calendar format e.g. '16 Aug 2026'."""
    if not date_val or not str(date_val).strip() or str(date_val).strip() in ("-", "N/A", "None", ""):
        return "-"
    raw = str(date_val).strip()
    try:
        if len(raw) >= 10:
            dt = datetime.strptime(raw[:10], "%Y-%m-%d")
            return dt.strftime("%d %b %Y")
    except Exception:
        pass
    return raw

def format_date_range(start_val: Optional[str], end_val: Optional[str]) -> str:
    """Formats start and end dates into clean range '01 Jul 2026 – 31 Jul 2026'."""
    d1 = format_long_date(start_val)
    d2 = format_long_date(end_val)
    if d1 == "-" and d2 == "-":
        return "N/A"
    if d1 != "-" and d2 != "-" and d1 != d2:
        return f"{d1} – {d2}"
    return d1 if d1 != "-" else d2

def format_long_datetime(dt_val: Optional[Any] = None) -> str:
    """Formats current or provided datetime into clean timestamp '16 Aug 2026, 09:00 PM'."""
    if dt_val is None:
        dt = datetime.now()
    elif isinstance(dt_val, datetime):
        dt = dt_val
    else:
        try:
            dt = datetime.strptime(str(dt_val)[:19], "%Y-%m-%d %H:%M:%S")
        except Exception:
            dt = datetime.now()
    return dt.strftime("%d %b %Y, %I:%M %p")

def format_pay_period(month_val: Any, year_val: Any) -> str:
    """Formats month and year into 'August 2026'."""
    try:
        m = int(month_val)
        y = int(year_val)
        if 1 <= m <= 12:
            return f"{MONTH_NAMES[m]} {y}"
    except Exception:
        pass
    return f"{month_val}/{year_val}"

def get_modern_styles():
    """Builds a refined, modern typography hierarchy."""
    styles = getSampleStyleSheet()
    
    return {
        'brand_title': ParagraphStyle(
            'BrandTitle',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=13,
            leading=16,
            textColor=COLOR_BRAND_DARK
        ),
        'brand_subtitle': ParagraphStyle(
            'BrandSubTitle',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=8,
            leading=11,
            textColor=COLOR_TEXT_MUTED
        ),
        'doc_header_title': ParagraphStyle(
            'DocHeaderTitle',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=14,
            leading=17,
            textColor=COLOR_BRAND_DARK,
            alignment=2
        ),
        'doc_header_subtitle': ParagraphStyle(
            'DocHeaderSub',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=7.5,
            leading=10,
            textColor=COLOR_GOLD_ACCENT,
            alignment=2
        ),
        'section_title': ParagraphStyle(
            'SectionTitle',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=9.5,
            leading=12,
            textColor=COLOR_BRAND_DARK
        ),
        'kpi_label': ParagraphStyle(
            'KpiLabel',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=6.5,
            leading=8,
            textColor=COLOR_TEXT_MUTED,
            alignment=1
        ),
        'kpi_val': ParagraphStyle(
            'KpiVal',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=10.5,
            leading=13,
            textColor=COLOR_TEXT_TITLE,
            alignment=1
        ),
        'kpi_val_green': ParagraphStyle(
            'KpiValGreen',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=10.5,
            leading=13,
            textColor=COLOR_BRAND_PRIMARY,
            alignment=1
        ),
        'kpi_val_red': ParagraphStyle(
            'KpiValRed',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=10.5,
            leading=13,
            textColor=COLOR_CRIMSON,
            alignment=1
        ),
        'th_label': ParagraphStyle(
            'THLabel',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=7,
            leading=9,
            textColor=COLOR_TEXT_MUTED
        ),
        'th_label_right': ParagraphStyle(
            'THLabelRight',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=7,
            leading=9,
            textColor=COLOR_TEXT_MUTED,
            alignment=2
        ),
        'cell_body': ParagraphStyle(
            'CellBody',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=7.5,
            leading=10,
            textColor=COLOR_TEXT_BODY
        ),
        'cell_bold': ParagraphStyle(
            'CellBold',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=7.5,
            leading=10,
            textColor=COLOR_TEXT_TITLE
        ),
        'cell_right': ParagraphStyle(
            'CellRight',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=7.5,
            leading=10,
            textColor=COLOR_TEXT_BODY,
            alignment=2
        ),
        'cell_right_bold': ParagraphStyle(
            'CellRightBold',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=7.5,
            leading=10,
            textColor=COLOR_TEXT_TITLE,
            alignment=2
        ),
        'cell_red_bold': ParagraphStyle(
            'CellRedBold',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=7.5,
            leading=10,
            textColor=COLOR_CRIMSON,
            alignment=2
        ),
        'sig_name': ParagraphStyle(
            'SigName',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=7.5,
            leading=9.5,
            textColor=COLOR_TEXT_TITLE,
            alignment=1
        ),
        'sig_dept': ParagraphStyle(
            'SigDept',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=7,
            leading=9,
            textColor=COLOR_TEXT_MUTED,
            alignment=1
        ),
        'footer_legal': ParagraphStyle(
            'FooterLegal',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=6.5,
            leading=8.5,
            textColor=COLOR_TEXT_FAINT,
            alignment=1
        )
    }

def format_status_badge(status: str) -> str:
    """Renders modern, sleek status pill badges."""
    st = (status or "Pending").strip()
    if st == "Paid":
        return "<font color='#047857'><b>● PAID</b></font>"
    elif st in ("Partially Paid", "Partial"):
        return "<font color='#B45309'><b>● PARTIAL</b></font>"
    elif st == "Approved":
        return "<font color='#1D4ED8'><b>● APPROVED</b></font>"
    else:
        return "<font color='#B91C1C'><b>● PENDING</b></font>"


# =========================================================================
# 1. MODERN BILINGUAL SALARY PAYSLIP VOUCHER
# =========================================================================
def generate_payslip_pdf(employee_data: dict, payroll_detail: dict, company_info: dict) -> bytes:
    """Generates a modern, clean Bilingual Saudi Salary Voucher PDF."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=32,
        leftMargin=32,
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
    
    pay_period_str = format_pay_period(payroll_detail.get('month', ''), payroll_detail.get('year', ''))
    
    # Header
    header_data = [
        [
            Paragraph(f"<b>{company_name}</b><br/><font size=7.5 color='#047857'>{ar_name}</font><br/><font size=7 color='#64748B'>CR: {cr_num} • GOSI: {gosi_reg} • {address}</font>", st['brand_title']),
            Paragraph(f"<b>SALARY PAYSLIP</b><br/><font size=7.5 color='#B45309'><b>قسيمة صرف الراتب</b></font><br/><font size=7 color='#64748B'>Pay Period: <b>{pay_period_str}</b></font>", st['doc_header_title'])
        ]
    ]
    header_table = Table(header_data, colWidths=[4.3*inch, 3.3*inch])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN', (1,0), (1,0), 'RIGHT'),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 4))
    elements.append(HRFlowable(width="100%", thickness=1, color=COLOR_CARD_BORDER, spaceAfter=8))
    
    # Employee Info Card
    emp_name = f"{employee_data.get('first_name', '')} {employee_data.get('last_name', '')}".strip()
    is_saudi = employee_data.get("is_saudi") == 1
    nat_type = "Saudi National (مواطن)" if is_saudi else "Expat (مقيم)"
    
    emp_meta = [
        [
            Paragraph("<b>EMPLOYEE NAME:</b>", st['th_label']), Paragraph(emp_name, st['cell_bold']),
            Paragraph("<b>EMPLOYEE CODE:</b>", st['th_label']), Paragraph(str(employee_data.get("emp_code", "N/A")), st['cell_bold'])
        ],
        [
            Paragraph("<b>NATIONAL ID / IQAMA:</b>", st['th_label']), Paragraph(str(employee_data.get("national_id_iqama", "N/A")), st['cell_body']),
            Paragraph("<b>DEPARTMENT:</b>", st['th_label']), Paragraph(str(employee_data.get("department_name", "General Operations")), st['cell_body'])
        ],
        [
            Paragraph("<b>DESIGNATION:</b>", st['th_label']), Paragraph(str(employee_data.get("designation", "N/A")), st['cell_body']),
            Paragraph("<b>NATIONALITY:</b>", st['th_label']), Paragraph(nat_type, st['cell_body'])
        ],
        [
            Paragraph("<b>BANK & IBAN:</b>", st['th_label']), Paragraph(f"{employee_data.get('bank_name', 'Bank')} • {employee_data.get('iban', 'N/A')}", st['cell_body']),
            Paragraph("<b>GOSI NUMBER:</b>", st['th_label']), Paragraph(str(employee_data.get("gosi_number", "N/A")), st['cell_body'])
        ]
    ]
    emp_table = Table(emp_meta, colWidths=[1.5*inch, 2.3*inch, 1.4*inch, 2.4*inch])
    emp_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), COLOR_CARD_BG),
        ('BOX', (0,0), (-1,-1), 0.5, COLOR_CARD_BORDER),
        ('INNERGRID', (0,0), (-1,-1), 0.5, COLOR_DIVIDER),
        ('TOPPADDING', (0,0), (-1,-1), 4.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4.5),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    elements.append(emp_table)
    elements.append(Spacer(1, 8))
    
    # 4-Card Hero Metric Strip
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
    
    kpi_cards = [
        [
            Paragraph("BASIC SALARY", st['kpi_label']),
            Paragraph("GROSS EARNINGS", st['kpi_label']),
            Paragraph("TOTAL DEDUCTIONS", st['kpi_label']),
            Paragraph("NET SALARY PAYABLE", st['kpi_label'])
        ],
        [
            Paragraph(f"SAR {basic:,.2f}", st['kpi_val']),
            Paragraph(f"SAR {gross:,.2f}", st['kpi_val']),
            Paragraph(f"SAR {total_ded:,.2f}", st['kpi_val_red']),
            Paragraph(f"<b>SAR {net_pay:,.2f}</b>", ParagraphStyle('NetMain', parent=st['kpi_val_green'], fontSize=11.5))
        ]
    ]
    kpi_table = Table(kpi_cards, colWidths=[1.9*inch, 1.9*inch, 1.9*inch, 1.9*inch])
    kpi_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (0,-1), COLOR_CARD_BG),
        ('BACKGROUND', (1,0), (1,-1), COLOR_CARD_BG),
        ('BACKGROUND', (2,0), (2,-1), COLOR_CRIMSON_BG),
        ('BACKGROUND', (3,0), (3,-1), COLOR_BRAND_LIGHT),
        ('BOX', (0,0), (-1,-1), 0.8, COLOR_CARD_BORDER),
        ('INNERGRID', (0,0), (-1,-1), 0.5, COLOR_CARD_BORDER),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    elements.append(kpi_table)
    elements.append(Spacer(1, 10))
    
    # Modern Clean Financial Table
    elements.append(Paragraph("<b>Itemized Compensation & Deductions Breakdown</b>", st['section_title']))
    elements.append(Spacer(1, 3))
    
    fin_rows = [
        [
            Paragraph("EARNINGS CATEGORY", st['th_label']),
            Paragraph("AMOUNT (SAR)", st['th_label_right']),
            Paragraph("DEDUCTIONS & GOSI", st['th_label']),
            Paragraph("AMOUNT (SAR)", st['th_label_right'])
        ],
        [
            Paragraph("Basic Salary (الراتب الأساسي)", st['cell_body']), Paragraph(f"{basic:,.2f}", st['cell_right']),
            Paragraph(f"GOSI Employee Share ({'9.75%' if is_saudi else '0%'})", st['cell_body']), Paragraph(f"{gosi_emp:,.2f}", st['cell_right'])
        ],
        [
            Paragraph("Housing Allowance (بدل سكن)", st['cell_body']), Paragraph(f"{housing:,.2f}", st['cell_right']),
            Paragraph("Other Disciplinary / Loan Deductions", st['cell_body']), Paragraph(f"{other_ded:,.2f}", st['cell_right'])
        ],
        [
            Paragraph("Transportation Allowance (بدل نقل)", st['cell_body']), Paragraph(f"{transport:,.2f}", st['cell_right']),
            Paragraph("-", st['cell_body']), Paragraph("-", st['cell_right'])
        ],
        [
            Paragraph("Other Allowances & Benefits", st['cell_body']), Paragraph(f"{other_allow:,.2f}", st['cell_right']),
            Paragraph("-", st['cell_body']), Paragraph("-", st['cell_right'])
        ],
        [
            Paragraph("<b>Total Gross Earnings:</b>", st['cell_bold']), Paragraph(f"<b>SAR {gross:,.2f}</b>", st['cell_right_bold']),
            Paragraph("<b>Total Deductions:</b>", st['cell_bold']), Paragraph(f"<b>SAR {total_ded:,.2f}</b>", st['cell_right_bold'])
        ]
    ]
    fin_table = Table(fin_rows, colWidths=[2.4*inch, 1.4*inch, 2.4*inch, 1.4*inch])
    fin_table.setStyle(TableStyle([
        ('LINEBELOW', (0,0), (-1,0), 1, COLOR_TEXT_TITLE),
        ('LINEBELOW', (0,1), (-1,-2), 0.5, COLOR_DIVIDER),
        ('LINEABOVE', (0,-1), (-1,-1), 1, COLOR_TEXT_TITLE),
        ('BACKGROUND', (0,-1), (-1,-1), COLOR_CARD_BG),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
    ]))
    elements.append(fin_table)
    elements.append(Spacer(1, 6))
    
    # Employer Contribution Note
    gosi_note = Paragraph(f"<font size=7 color='#64748B'>* Employer Statutory GOSI Contribution for this period: <b>SAR {gosi_empr:,.2f}</b> ({'11.75%' if is_saudi else '2.0%'} per Saudi Social Insurance Law).</font>", st['cell_body'])
    elements.append(gosi_note)
    elements.append(Spacer(1, 14))
    
    # Signatures
    sig_data = [
        [
            Paragraph("<b>AUTHORIZED COMPANY SIGNATURE</b>", st['sig_name']),
            Paragraph("<b>EMPLOYEE ACKNOWLEDGMENT</b>", st['sig_name'])
        ],
        [
            Paragraph("HR & Payroll Operations Department<br/><br/>________________________________________<br/>Authorized Signatory & Corporate Seal", st['sig_dept']),
            Paragraph("I confirm receipt of salary payment in full.<br/><br/>________________________________________<br/>Employee Signature & Date", st['sig_dept'])
        ]
    ]
    sig_table = Table(sig_data, colWidths=[3.8*inch, 3.8*inch])
    sig_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), COLOR_CARD_BG),
        ('BOX', (0,0), (-1,-1), 0.5, COLOR_CARD_BORDER),
        ('INNERGRID', (0,0), (-1,-1), 0.5, COLOR_CARD_BORDER),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    elements.append(sig_table)
    elements.append(Spacer(1, 8))
    
    elements.append(Paragraph("This payroll voucher is electronically certified and fully compliant with Saudi Labor Law & SAMA WPS regulations.", st['footer_legal']))
    
    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


# =========================================================================
# 2. MODERN VENDOR STATEMENT OF ACCOUNT & PAYMENT VOUCHER
# =========================================================================
def generate_supplier_statement_pdf(sp: dict, payment_logs: list, company_info: dict) -> bytes:
    """Generates a modern, fintech-grade Supplier Statement & Payment Voucher PDF."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=32,
        leftMargin=32,
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
    
    inv_date_formatted = format_long_date(sp.get("invoice_date"))
    due_date_formatted = format_long_date(sp.get("due_date"))
    supply_period_formatted = format_date_range(
        sp.get("supply_start_date") or sp.get("supply_date"),
        sp.get("supply_end_date") or sp.get("supply_date")
    )
    gen_time_formatted = format_long_datetime()
    
    # Top Header
    header_data = [
        [
            Paragraph(f"<b>{company_name}</b><br/><font size=7.5 color='#047857'>{ar_name}</font><br/><font size=7 color='#64748B'>CR: {cr_num} • {address}</font>", st['brand_title']),
            Paragraph(f"<b>VENDOR STATEMENT OF ACCOUNT</b><br/><font size=7.5 color='#B45309'><b>كشف حساب المورد وسند الصرف</b></font><br/><font size=7 color='#64748B'>Generated: {gen_time_formatted}</font>", st['doc_header_title'])
        ]
    ]
    header_table = Table(header_data, colWidths=[4.3*inch, 3.3*inch])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN', (1,0), (1,0), 'RIGHT'),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 4))
    elements.append(HRFlowable(width="100%", thickness=1, color=COLOR_CARD_BORDER, spaceAfter=8))
    
    # 4-Card Hero Metric Strip
    kpi_cards = [
        [
            Paragraph("TOTAL BILLED", st['kpi_label']),
            Paragraph("TOTAL DISBURSED", st['kpi_label']),
            Paragraph("OUTSTANDING BALANCE", st['kpi_label']),
            Paragraph("INVOICE STATUS", st['kpi_label'])
        ],
        [
            Paragraph(f"SAR {total_amt:,.2f}", st['kpi_val']),
            Paragraph(f"SAR {paid_amt:,.2f}", st['kpi_val_green']),
            Paragraph(f"<b>SAR {rem_amt:,.2f}</b>", st['kpi_val_red']),
            Paragraph(format_status_badge(sp.get("status", "Pending")), st['cell_bold'])
        ]
    ]
    kpi_table = Table(kpi_cards, colWidths=[1.9*inch, 1.9*inch, 1.9*inch, 1.9*inch])
    kpi_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (0,-1), COLOR_CARD_BG),
        ('BACKGROUND', (1,0), (1,-1), COLOR_BRAND_LIGHT),
        ('BACKGROUND', (2,0), (2,-1), COLOR_CRIMSON_BG),
        ('BACKGROUND', (3,0), (3,-1), COLOR_CARD_BG),
        ('BOX', (0,0), (-1,-1), 0.8, COLOR_CARD_BORDER),
        ('INNERGRID', (0,0), (-1,-1), 0.5, COLOR_CARD_BORDER),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    elements.append(kpi_table)
    elements.append(Spacer(1, 10))
    
    # Metadata Card
    inv_meta = [
        [
            Paragraph("<b>VENDOR COMPANY:</b>", st['th_label']), Paragraph(str(sp.get("company_name", "")), st['cell_bold']),
            Paragraph("<b>INVOICE NUMBER:</b>", st['th_label']), Paragraph(str(sp.get("invoice_number", "N/A")), st['cell_bold'])
        ],
        [
            Paragraph("<b>INVOICE DATE:</b>", st['th_label']), Paragraph(inv_date_formatted, st['cell_body']),
            Paragraph("<b>PAYMENT DUE DATE:</b>", st['th_label']), Paragraph(due_date_formatted, st['cell_body'])
        ],
        [
            Paragraph("<b>SUPPLY PERIOD:</b>", st['th_label']), Paragraph(supply_period_formatted, st['cell_body']),
            Paragraph("<b>SYSTEM RECORD ID:</b>", st['th_label']), Paragraph(f"#INV-{sp.get('id', '')}", st['cell_body'])
        ],
        [
            Paragraph("<b>ITEM / SERVICE DETAILS:</b>", st['th_label']), Paragraph(str(sp.get("invoice_details", "N/A")), st['cell_body']),
            Paragraph("<b>INTERNAL REMARKS:</b>", st['th_label']), Paragraph(str(sp.get("remarks", "N/A")), st['cell_body'])
        ]
    ]
    meta_table = Table(inv_meta, colWidths=[1.5*inch, 2.3*inch, 1.4*inch, 2.4*inch])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), COLOR_CARD_BG),
        ('BOX', (0,0), (-1,-1), 0.5, COLOR_CARD_BORDER),
        ('INNERGRID', (0,0), (-1,-1), 0.5, COLOR_DIVIDER),
        ('TOPPADDING', (0,0), (-1,-1), 4.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4.5),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    elements.append(meta_table)
    elements.append(Spacer(1, 10))
    
    # Disbursal Logs Table
    elements.append(Paragraph("<b>Disbursal Settlement & Outflow History</b>", st['section_title']))
    elements.append(Spacer(1, 3))
    
    log_rows = [
        [
            Paragraph("SETTLEMENT DATE", st['th_label']),
            Paragraph("PAYMENT METHOD", st['th_label']),
            Paragraph("TRANSACTION REF #", st['th_label']),
            Paragraph("NOTES / DESCRIPTION", st['th_label']),
            Paragraph("AMOUNT (SAR)", st['th_label_right'])
        ]
    ]
    
    if not payment_logs:
        log_rows.append([Paragraph("No payment disbursals recorded yet. Full balance remains open.", st['cell_body']), Paragraph("-", st['cell_body']), Paragraph("-", st['cell_body']), Paragraph("-", st['cell_body']), Paragraph("SAR 0.00", st['cell_right'])])
    else:
        for lg in payment_logs:
            amt_lg = float(lg.get("payment_amount", 0.0))
            pay_date_formatted = format_long_date(lg.get("payment_date"))
            log_rows.append([
                Paragraph(pay_date_formatted, st['cell_body']),
                Paragraph(str(lg.get("payment_method", "Bank Transfer")), st['cell_body']),
                Paragraph(str(lg.get("reference_number", "N/A")), st['cell_body']),
                Paragraph(str(lg.get("notes", "N/A")), st['cell_body']),
                Paragraph(f"<b>SAR {amt_lg:,.2f}</b>", st['cell_right_bold'])
            ])
            
    history_table = Table(log_rows, colWidths=[1.3*inch, 1.2*inch, 1.4*inch, 2.2*inch, 1.5*inch])
    history_table.setStyle(TableStyle([
        ('LINEBELOW', (0,0), (-1,0), 1, COLOR_TEXT_TITLE),
        ('LINEBELOW', (0,1), (-1,-1), 0.5, COLOR_DIVIDER),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
    ]))
    elements.append(history_table)
    elements.append(Spacer(1, 14))
    
    # Signatures
    sig_data = [
        [
            Paragraph("<b>ACCOUNTS PAYABLE CONTROLLER</b>", st['sig_name']),
            Paragraph("<b>VENDOR RECEIVER ACKNOWLEDGMENT</b>", st['sig_name'])
        ],
        [
            Paragraph("Finance & Treasury Department<br/><br/>________________________________________<br/>Signature & Company Stamp", st['sig_dept']),
            Paragraph("Authorized Vendor Representative<br/><br/>________________________________________<br/>Signature & Official Stamp", st['sig_dept'])
        ]
    ]
    sig_table = Table(sig_data, colWidths=[3.8*inch, 3.8*inch])
    sig_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), COLOR_CARD_BG),
        ('BOX', (0,0), (-1,-1), 0.5, COLOR_CARD_BORDER),
        ('INNERGRID', (0,0), (-1,-1), 0.5, COLOR_CARD_BORDER),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    elements.append(sig_table)
    elements.append(Spacer(1, 8))
    
    elements.append(Paragraph("This official statement of account is issued under Saudi Commercial Regulations as verified financial proof of AP settlement.", st['footer_legal']))
    
    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


# =========================================================================
# 3. MODERN EXECUTIVE ACCOUNTS PAYABLE REPORT
# =========================================================================
def generate_supplier_summary_report_pdf(
    invoices: List[Dict[str, Any]],
    summary_stats: Dict[str, Any],
    company_info: Dict[str, Any],
    filter_info: Optional[Dict[str, Any]] = None
) -> bytes:
    """Generates an executive, modern Accounts Payable Schedule PDF with clean typography and subtotals."""
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
    
    gen_time_formatted = format_long_datetime()
    
    # Header
    header_data = [
        [
            Paragraph(f"<b>{company_name}</b><br/><font size=7.5 color='#047857'>{ar_name}</font><br/><font size=7 color='#64748B'>CR: {cr_num} • {address}</font>", st['brand_title']),
            Paragraph(f"<b>ACCOUNTS PAYABLE REPORT</b><br/><font size=7.5 color='#B45309'><b>جدول التزامات ومستحقات الموردين</b></font><br/><font size=7 color='#64748B'>Generated: {gen_time_formatted}</font>", st['doc_header_title'])
        ]
    ]
    header_table = Table(header_data, colWidths=[4.3*inch, 3.4*inch])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN', (1,0), (1,0), 'RIGHT'),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 3))
    elements.append(HRFlowable(width="100%", thickness=1, color=COLOR_CARD_BORDER, spaceAfter=6))
    
    # Scope Box
    f_info = filter_info or {}
    sel_sups = f_info.get("selected_suppliers", "All Registered Suppliers")
    st_filter = f_info.get("status", "All Statuses")
    raw_date_scope = f_info.get("date_range", "All Historical Invoices")
    
    meta_data = [
        [
            Paragraph("<b>TARGET SUPPLIERS:</b>", st['th_label']), Paragraph(str(sel_sups), st['cell_body']),
            Paragraph("<b>GENERATED ON:</b>", st['th_label']), Paragraph(gen_time_formatted, st['cell_body'])
        ],
        [
            Paragraph("<b>PAYMENT STATUS:</b>", st['th_label']), Paragraph(str(st_filter), st['cell_body']),
            Paragraph("<b>DATE FILTER:</b>", st['th_label']), Paragraph(str(raw_date_scope), st['cell_body'])
        ]
    ]
    meta_table = Table(meta_data, colWidths=[1.3*inch, 3.1*inch, 1.1*inch, 2.2*inch])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), COLOR_CARD_BG),
        ('BOX', (0,0), (-1,-1), 0.5, COLOR_CARD_BORDER),
        ('INNERGRID', (0,0), (-1,-1), 0.5, COLOR_DIVIDER),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
    ]))
    elements.append(meta_table)
    elements.append(Spacer(1, 6))
    
    # 4-Card Hero Metric Strip
    tot_billed = float(summary_stats.get("total_billed", sum(float(i.get("amount", 0)) for i in invoices)))
    tot_paid = float(summary_stats.get("total_paid", sum(float(i.get("paid_amount", 0)) for i in invoices)))
    tot_rem = float(summary_stats.get("total_outstanding_payable", sum(float(i.get("remaining_amount", 0)) for i in invoices)))
    
    kpi_cards = [
        [
            Paragraph("TOTAL INVOICES", st['kpi_label']),
            Paragraph("TOTAL BILLED", st['kpi_label']),
            Paragraph("TOTAL DISBURSED", st['kpi_label']),
            Paragraph("NET LIABILITY DUE", st['kpi_label'])
        ],
        [
            Paragraph(f"{len(invoices)} Invoices", st['kpi_val']),
            Paragraph(f"SAR {tot_billed:,.2f}", st['kpi_val']),
            Paragraph(f"SAR {tot_paid:,.2f}", st['kpi_val_green']),
            Paragraph(f"<b>SAR {tot_rem:,.2f}</b>", ParagraphStyle('NetMainRed', parent=st['kpi_val_red'], fontSize=11))
        ]
    ]
    kpi_table = Table(kpi_cards, colWidths=[1.92*inch, 1.92*inch, 1.92*inch, 1.92*inch])
    kpi_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (0,-1), COLOR_CARD_BG),
        ('BACKGROUND', (1,0), (1,-1), COLOR_CARD_BG),
        ('BACKGROUND', (2,0), (2,-1), COLOR_BRAND_LIGHT),
        ('BACKGROUND', (3,0), (3,-1), COLOR_CRIMSON_BG),
        ('BOX', (0,0), (-1,-1), 0.8, COLOR_CARD_BORDER),
        ('INNERGRID', (0,0), (-1,-1), 0.5, COLOR_CARD_BORDER),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    elements.append(kpi_table)
    elements.append(Spacer(1, 8))
    
    # Grouped Supplier Invoices
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
                Paragraph(f"🏢 <b>{vendor_name}</b> <font size=6.5 color='#64748B'>({len(v_invoices)} Invoices)</font>", ParagraphStyle('VTitle', parent=st['cell_bold'], textColor=COLOR_BRAND_DARK, fontSize=8.5)),
                Paragraph(f"Billed: <b>SAR {v_billed:,.2f}</b> • Paid: <font color='#047857'><b>SAR {v_paid:,.2f}</b></font> • Due: <font color='#B91C1C'><b>SAR {v_rem:,.2f}</b></font>", ParagraphStyle('VRight', parent=st['cell_body'], alignment=2, fontSize=7.5))
            ]
        ]
        v_header_table = Table(v_header_data, colWidths=[4.3*inch, 3.4*inch])
        v_header_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), COLOR_CARD_BG),
            ('BOX', (0,0), (-1,-1), 0.5, COLOR_CARD_BORDER),
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
                Paragraph("INVOICE #", st['th_label']),
                Paragraph("INVOICE DATE", st['th_label']),
                Paragraph("SUPPLY PERIOD", st['th_label']),
                Paragraph("DUE DATE", st['th_label']),
                Paragraph("BILLED (SAR)", st['th_label_right']),
                Paragraph("PAID (SAR)", st['th_label_right']),
                Paragraph("BALANCE (SAR)", st['th_label_right']),
                Paragraph("STATUS", st['th_label'])
            ]
        ]
        
        for inv in v_invoices:
            period_formatted = format_date_range(
                inv.get("supply_start_date") or inv.get("supply_date"),
                inv.get("supply_end_date") or inv.get("supply_date")
            )
            inv_d_formatted = format_long_date(inv.get("invoice_date"))
            due_d_formatted = format_long_date(inv.get("due_date"))
            
            amt = float(inv.get("amount", 0.0))
            pd = float(inv.get("paid_amount", 0.0))
            rem = float(inv.get("remaining_amount", max(0.0, amt - pd)))
            st_text = str(inv.get("status", "Pending"))
            
            rows.append([
                Paragraph(str(inv.get('invoice_number', 'N/A')), st['cell_bold']),
                Paragraph(inv_d_formatted, st['cell_body']),
                Paragraph(period_formatted, st['cell_body']),
                Paragraph(due_d_formatted, st['cell_body']),
                Paragraph(f"{amt:,.2f}", st['cell_right']),
                Paragraph(f"{pd:,.2f}", st['cell_right']),
                Paragraph(f"<b>{rem:,.2f}</b>", st['cell_red_bold'] if rem > 0 else st['cell_right_bold']),
                Paragraph(format_status_badge(st_text), st['cell_body'])
            ])
            
        t = Table(rows, colWidths=[1.1*inch, 0.9*inch, 1.5*inch, 0.9*inch, 0.85*inch, 0.85*inch, 0.85*inch, 0.75*inch])
        t.setStyle(TableStyle([
            ('LINEBELOW', (0,0), (-1,0), 1, COLOR_TEXT_TITLE),
            ('LINEBELOW', (0,1), (-1,-1), 0.5, COLOR_DIVIDER),
            ('TOPPADDING', (0,0), (-1,-1), 3),
            ('BOTTOMPADDING', (0,0), (-1,-1), 3),
            ('LEFTPADDING', (0,0), (-1,-1), 4),
            ('RIGHTPADDING', (0,0), (-1,-1), 4),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 6))
        
    # Grand Total Bar
    grand_data = [
        [
            Paragraph("<b>CONSOLIDATED GRAND TOTALS:</b>", ParagraphStyle('GTL', parent=st['cell_bold'], fontSize=7.5)),
            Paragraph(f"<b>Billed: SAR {tot_billed:,.2f}</b>", st['cell_bold']),
            Paragraph(f"<b>Disbursed: SAR {tot_paid:,.2f}</b>", ParagraphStyle('GP', parent=st['cell_bold'], textColor=COLOR_BRAND_PRIMARY)),
            Paragraph(f"<b>Total Due: <font color='#B91C1C'>SAR {tot_rem:,.2f}</font></b>", st['cell_bold'])
        ]
    ]
    gt_table = Table(grand_data, colWidths=[2.8*inch, 1.6*inch, 1.6*inch, 1.7*inch])
    gt_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), COLOR_CARD_BG),
        ('BOX', (0,0), (-1,-1), 0.8, COLOR_GOLD_BORDER),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    elements.append(gt_table)
    elements.append(Spacer(1, 10))
    
    # Signatures
    sig_data = [
        [
            Paragraph("<b>PREPARED BY: ACCOUNTS PAYABLE CONTROLLER</b>", st['sig_name']),
            Paragraph("<b>APPROVED BY: CHIEF FINANCIAL OFFICER (CFO)</b>", st['sig_name'])
        ],
        [
            Paragraph("Treasury & AP Operations Department<br/><br/>________________________________________<br/>Signature & Review Stamp", st['sig_dept']),
            Paragraph("Executive Financial Management<br/><br/>________________________________________<br/>Authorized Signature & Corporate Seal", st['sig_dept'])
        ]
    ]
    sig_table = Table(sig_data, colWidths=[3.85*inch, 3.85*inch])
    sig_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), COLOR_CARD_BG),
        ('BOX', (0,0), (-1,-1), 0.5, COLOR_CARD_BORDER),
        ('INNERGRID', (0,0), (-1,-1), 0.5, COLOR_CARD_BORDER),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    elements.append(sig_table)
    elements.append(Spacer(1, 4))
    
    elements.append(Paragraph("This accounts payable report is generated by the Cloud ERP System in compliance with Saudi Financial & Commercial Standards.", st['footer_legal']))
    
    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
