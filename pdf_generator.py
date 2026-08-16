import os
import io
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

def generate_payslip_pdf(employee_data: dict, payroll_detail: dict, company_info: dict) -> bytes:
    """
    Generates official Bilingual Saudi Standard Payslip PDF with GOSI deductions.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )
    
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#006C35'),
        alignment=2
    )
    
    subtitle_style = ParagraphStyle(
        'SubTitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#4B5563')
    )
    
    section_heading = ParagraphStyle(
        'SectionHeading',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=15,
        textColor=colors.HexColor('#0B5D34')
    )
    
    cell_style = ParagraphStyle(
        'CellText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#1F2937')
    )
    
    cell_bold = ParagraphStyle(
        'CellBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#1F2937')
    )
    
    elements = []
    
    company_name = company_info.get("company_name", "Al-Amal Enterprise Solutions KSA")
    cr_num = company_info.get("cr_number", "1010894512")
    gosi_reg = company_info.get("gosi_reg_number", "309481920")
    
    header_data = [
        [
            Paragraph(f"<b>{company_name}</b><br/><font size=8 color='#6B7280'>Commercial Reg: {cr_num} | GOSI: {gosi_reg}</font>", subtitle_style),
            Paragraph("<b>SALARY PAYSLIP</b><br/><font size=9 color='#006C35'>Official Payroll Voucher</font>", title_style)
        ]
    ]
    
    header_table = Table(header_data, colWidths=[4.2*inch, 3.0*inch])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN', (1,0), (1,0), 'RIGHT'),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 10))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#006C35'), spaceAfter=15))
    
    emp_name = f"{employee_data.get('first_name', '')} {employee_data.get('last_name', '')}".strip()
    is_saudi_str = "Saudi National" if employee_data.get("is_saudi") == 1 else "Expat / Non-Saudi"
    
    emp_info_data = [
        [
            Paragraph("<b>Employee Name:</b>", cell_bold), Paragraph(emp_name, cell_style),
            Paragraph("<b>Employee Code:</b>", cell_bold), Paragraph(str(employee_data.get("emp_code", "N/A")), cell_style)
        ],
        [
            Paragraph("<b>National ID / Iqama:</b>", cell_bold), Paragraph(str(employee_data.get("national_id_iqama", "N/A")), cell_style),
            Paragraph("<b>Department:</b>", cell_bold), Paragraph(str(employee_data.get("department_name", "General")), cell_style)
        ],
        [
            Paragraph("<b>Designation:</b>", cell_bold), Paragraph(str(employee_data.get("designation", "N/A")), cell_style),
            Paragraph("<b>Nationality Type:</b>", cell_bold), Paragraph(is_saudi_str, cell_style)
        ],
        [
            Paragraph("<b>Bank Name:</b>", cell_bold), Paragraph(str(employee_data.get("bank_name", "N/A")), cell_style),
            Paragraph("<b>IBAN Number:</b>", cell_bold), Paragraph(str(employee_data.get("iban", "N/A")), cell_style)
        ],
        [
            Paragraph("<b>Pay Period:</b>", cell_bold), Paragraph(f"{payroll_detail.get('month', '')}/{payroll_detail.get('year', '')}", cell_style),
            Paragraph("<b>GOSI Reg Number:</b>", cell_bold), Paragraph(str(employee_data.get("gosi_number", "N/A")), cell_style)
        ]
    ]
    
    emp_table = Table(emp_info_data, colWidths=[1.5*inch, 2.1*inch, 1.5*inch, 2.1*inch])
    emp_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F9FAFB')),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#E5E7EB')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#F3F4F6')),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    elements.append(emp_table)
    elements.append(Spacer(1, 15))
    
    elements.append(Paragraph("Salary & Allowance Breakdown", section_heading))
    elements.append(Spacer(1, 6))
    
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
    
    financial_data = [
        [
            Paragraph("<font color='white'><b>Earnings Category</b></font>", cell_bold), Paragraph("<font color='white'><b>Amount (SAR)</b></font>", cell_bold),
            Paragraph("<font color='white'><b>Deductions & GOSI</b></font>", cell_bold), Paragraph("<font color='white'><b>Amount (SAR)</b></font>", cell_bold)
        ],
        [
            Paragraph("Basic Salary", cell_style), Paragraph(f"{basic:,.2f}", cell_style),
            Paragraph("GOSI Employee Share (9.75% / 0%)", cell_style), Paragraph(f"{gosi_emp:,.2f}", cell_style)
        ],
        [
            Paragraph("Housing Allowance", cell_style), Paragraph(f"{housing:,.2f}", cell_style),
            Paragraph("Other Deductions", cell_style), Paragraph(f"{other_ded:,.2f}", cell_style)
        ],
        [
            Paragraph("Transportation Allowance", cell_style), Paragraph(f"{transport:,.2f}", cell_style),
            Paragraph("-", cell_style), Paragraph("-", cell_style)
        ],
        [
            Paragraph("Other Allowances", cell_style), Paragraph(f"{other_allow:,.2f}", cell_style),
            Paragraph("-", cell_style), Paragraph("-", cell_style)
        ],
        [
            Paragraph("<b>Total Gross Earnings:</b>", cell_bold), Paragraph(f"<b>SAR {gross:,.2f}</b>", cell_bold),
            Paragraph("<b>Total Deductions:</b>", cell_bold), Paragraph(f"<b>SAR {total_ded:,.2f}</b>", cell_bold)
        ]
    ]
    
    fin_table = Table(financial_data, colWidths=[2.2*inch, 1.4*inch, 2.2*inch, 1.4*inch])
    fin_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#006C35')),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#D1D5DB')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E5E7EB')),
        ('BACKGROUND', (0,5), (-1,5), colors.HexColor('#F3F4F6')),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    elements.append(fin_table)
    elements.append(Spacer(1, 15))
    
    net_box_data = [
        [
            Paragraph("<b>NET SALARY PAYABLE:</b>", ParagraphStyle('NetLbl', parent=cell_bold, fontSize=12, textColor=colors.HexColor('#0B5D34'))),
            Paragraph(f"<b>SAR {net_pay:,.2f}</b>", ParagraphStyle('NetVal', parent=cell_bold, fontSize=14, textColor=colors.HexColor('#006C35'), alignment=2))
        ]
    ]
    net_table = Table(net_box_data, colWidths=[4.5*inch, 2.7*inch])
    net_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#ECFDF5')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#10B981')),
        ('TOPPADDING', (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
        ('LEFTPADDING', (0,0), (-1,-1), 12),
        ('RIGHTPADDING', (0,0), (-1,-1), 12),
    ]))
    elements.append(net_table)
    elements.append(Spacer(1, 12))
    
    gosi_info_p = Paragraph(f"<font size=8 color='#6B7280'>* Employer GOSI Contribution for this period: SAR {gosi_empr:,.2f} (Computed per Saudi GOSI Regulations).</font>", cell_style)
    elements.append(gosi_info_p)
    elements.append(Spacer(1, 25))
    
    sig_data = [
        [
            Paragraph("<b>Employer Authorized Stamp & Signature</b>", cell_style),
            Paragraph("<b>Employee Acknowledgment</b>", cell_style)
        ],
        [
            Paragraph("<br/><br/>____________________________________<br/>HR & Payroll Department", subtitle_style),
            Paragraph("<br/><br/>____________________________________<br/>Signature & Date", subtitle_style)
        ]
    ]
    sig_table = Table(sig_data, colWidths=[3.6*inch, 3.6*inch])
    sig_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    elements.append(sig_table)
    
    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes

def generate_supplier_statement_pdf(sp: dict, payment_logs: list, company_info: dict) -> bytes:
    """
    Generates official Supplier Statement & Payment Voucher PDF.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )
    
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#006C35'),
        alignment=2
    )
    
    subtitle_style = ParagraphStyle(
        'SubTitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#4B5563')
    )
    
    section_heading = ParagraphStyle(
        'SectionHeading',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=15,
        textColor=colors.HexColor('#0B5D34')
    )
    
    cell_style = ParagraphStyle(
        'CellText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#1F2937')
    )
    
    cell_bold = ParagraphStyle(
        'CellBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#1F2937')
    )
    
    elements = []
    
    company_name = company_info.get("company_name", "Al-Amal Enterprise Solutions KSA")
    cr_num = company_info.get("cr_number", "1010894512")
    
    header_data = [
        [
            Paragraph(f"<b>{company_name}</b><br/><font size=8 color='#6B7280'>Commercial Reg: {cr_num} | Riyadh, Saudi Arabia</font>", subtitle_style),
            Paragraph("<b>SUPPLIER STATEMENT</b><br/><font size=9 color='#006C35'>Accounts Payable Voucher</font>", title_style)
        ]
    ]
    
    header_table = Table(header_data, colWidths=[4.2*inch, 3.0*inch])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN', (1,0), (1,0), 'RIGHT'),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 10))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#006C35'), spaceAfter=15))
    
    total_amt = float(sp.get("amount", 0.0))
    paid_amt = float(sp.get("paid_amount", 0.0))
    rem_amt = float(sp.get("remaining_amount", max(0.0, total_amt - paid_amt)))
    
    start_d = sp.get("supply_start_date") or sp.get("supply_date", "")
    end_d = sp.get("supply_end_date") or sp.get("supply_date", "")
    supply_period = f"{start_d} to {end_d}" if start_d and end_d and start_d != end_d else (start_d or "N/A")
    
    inv_info_data = [
        [
            Paragraph("<b>Vendor Company:</b>", cell_bold), Paragraph(str(sp.get("company_name", "")), cell_style),
            Paragraph("<b>Invoice Number:</b>", cell_bold), Paragraph(str(sp.get("invoice_number", "N/A")), cell_style)
        ],
        [
            Paragraph("<b>Invoice Date:</b>", cell_bold), Paragraph(str(sp.get("invoice_date", "")), cell_style),
            Paragraph("<b>Due Date:</b>", cell_bold), Paragraph(str(sp.get("due_date", "")), cell_style)
        ],
        [
            Paragraph("<b>Supply Period:</b>", cell_bold), Paragraph(supply_period, cell_style),
            Paragraph("<b>Payment Status:</b>", cell_bold), Paragraph(str(sp.get("status", "Pending")), cell_style)
        ],
        [
            Paragraph("<b>Invoice Description:</b>", cell_bold), Paragraph(str(sp.get("invoice_details", "N/A")), cell_style),
            Paragraph("<b>Remarks / Notes:</b>", cell_bold), Paragraph(str(sp.get("remarks", "N/A")), cell_style)
        ]
    ]
    
    inv_table = Table(inv_info_data, colWidths=[1.5*inch, 2.1*inch, 1.5*inch, 2.1*inch])
    inv_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F9FAFB')),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#E5E7EB')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#F3F4F6')),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    elements.append(inv_table)
    elements.append(Spacer(1, 15))
    
    # Financial Balance Box
    bal_data = [
        [
            Paragraph("<b>Total Billed:</b>", cell_bold), Paragraph(f"SAR {total_amt:,.2f}", cell_style),
            Paragraph("<b>Total Paid:</b>", cell_bold), Paragraph(f"SAR {paid_amt:,.2f}", cell_style),
            Paragraph("<b>Balance Due:</b>", ParagraphStyle('BalL', parent=cell_bold, textColor=colors.HexColor('#991B1B'))),
            Paragraph(f"<b>SAR {rem_amt:,.2f}</b>", ParagraphStyle('BalV', parent=cell_bold, textColor=colors.HexColor('#EF4444'), fontSize=10))
        ]
    ]
    bal_table = Table(bal_data, colWidths=[1.3*inch, 1.1*inch, 1.3*inch, 1.1*inch, 1.3*inch, 1.1*inch])
    bal_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#FEF2F2')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#FCA5A5')),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    elements.append(bal_table)
    elements.append(Spacer(1, 15))
    
    # Payment History Table
    elements.append(Paragraph("Payment Disbursal History & Transactions", section_heading))
    elements.append(Spacer(1, 6))
    
    log_rows = [
        [
            Paragraph("<font color='white'><b>Date</b></font>", cell_bold),
            Paragraph("<font color='white'><b>Payment Method</b></font>", cell_bold),
            Paragraph("<font color='white'><b>Reference #</b></font>", cell_bold),
            Paragraph("<font color='white'><b>Notes / Details</b></font>", cell_bold),
            Paragraph("<font color='white'><b>Amount Paid (SAR)</b></font>", cell_bold)
        ]
    ]
    
    if not payment_logs:
        log_rows.append([Paragraph("No payment transactions recorded yet.", cell_style), Paragraph("-", cell_style), Paragraph("-", cell_style), Paragraph("-", cell_style), Paragraph("SAR 0.00", cell_style)])
    else:
        for lg in payment_logs:
            log_rows.append([
                Paragraph(str(lg.get("payment_date", "")), cell_style),
                Paragraph(str(lg.get("payment_method", "Bank Transfer")), cell_style),
                Paragraph(str(lg.get("reference_number", "N/A")), cell_style),
                Paragraph(str(lg.get("notes", "N/A")), cell_style),
                Paragraph(f"<b>SAR {float(lg.get('payment_amount', 0.0)):,.2f}</b>", cell_style)
            ])
            
    history_table = Table(log_rows, colWidths=[1.1*inch, 1.4*inch, 1.3*inch, 2.0*inch, 1.4*inch])
    history_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#006C35')),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#D1D5DB')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E5E7EB')),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    elements.append(history_table)
    elements.append(Spacer(1, 25))
    
    sig_data = [
        [
            Paragraph("<b>Finance Manager Signature</b>", cell_style),
            Paragraph("<b>Vendor Acknowledgment</b>", cell_style)
        ],
        [
            Paragraph("<br/><br/>____________________________________<br/>Finance Department", subtitle_style),
            Paragraph("<br/><br/>____________________________________<br/>Authorized Representative", subtitle_style)
        ]
    ]
    sig_table = Table(sig_data, colWidths=[3.6*inch, 3.6*inch])
    sig_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    elements.append(sig_table)
    
    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
