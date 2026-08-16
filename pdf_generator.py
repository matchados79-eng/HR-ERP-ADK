import os
import io
from datetime import datetime, date
from typing import List, Dict, Any, Optional
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

# =========================================================================
# EXECUTIVE CFO / FINANCIAL ADVISOR PALETTE (Deep Royal Navy, Emerald & Gold)
# =========================================================================
NAVY_PRIMARY       = colors.HexColor('#0F172A')   # Slate 900 Executive Navy
NAVY_SECONDARY     = colors.HexColor('#1E293B')   # Slate 800
EMERALD_BRAND      = colors.HexColor('#065F46')   # Deep Corporate Emerald
EMERALD_LIGHT      = colors.HexColor('#ECFDF5')   # Soft Emerald Tint
EMERALD_BORDER     = colors.HexColor('#10B981')   # Emerald Border Line

GOLD_ACCENT        = colors.HexColor('#B45309')   # Luxury Corporate Amber / Gold
GOLD_BG            = colors.HexColor('#FEF3C7')   # Soft Gold Fill
GOLD_BORDER        = colors.HexColor('#F59E0B')   # Gold Divider

RED_ALERT          = colors.HexColor('#991B1B')   # Deep Crimson Alert
RED_ALERT_BG       = colors.HexColor('#FEF2F2')   # Soft Crimson Fill
RED_ALERT_BORDER   = colors.HexColor('#EF4444')   # Crimson Border

BLUE_INFO          = colors.HexColor('#1E40AF')   # Corporate Royal Blue
BLUE_INFO_BG       = colors.HexColor('#EFF6FF')   # Soft Blue Fill
BLUE_INFO_BORDER   = colors.HexColor('#3B82F6')   # Blue Border

NEUTRAL_DARK       = colors.HexColor('#0F172A')   # Heading Slate 900
NEUTRAL_BODY       = colors.HexColor('#334155')   # Body Slate 700
NEUTRAL_MUTED      = colors.HexColor('#64748B')   # Muted Slate 500
NEUTRAL_LIGHT      = colors.HexColor('#F8FAFC')   # Section Slate 50
NEUTRAL_BORDER     = colors.HexColor('#CBD5E1')   # Clean Slate 300 Grid
NEUTRAL_ZEBRA      = colors.HexColor('#F1F5F9')   # Zebra Alternate Fill

MONTH_NAMES = ["", "January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]

def format_long_date(date_val: Optional[str]) -> str:
    """Formats 'YYYY-MM-DD' into clean calendar format e.g. '05 Oct 2026'."""
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
    """Formats start and end dates into '01 Jul 2026 – 31 Jul 2026'."""
    d1 = format_long_date(start_val)
    d2 = format_long_date(end_val)
    if d1 == "-" and d2 == "-":
        return "N/A"
    if d1 != "-" and d2 != "-" and d1 != d2:
        return f"{d1} – {d2}"
    return d1 if d1 != "-" else d2

def format_long_datetime(dt_val: Optional[Any] = None) -> str:
    """Formats current or provided datetime into '16 Aug 2026, 09:00 PM'."""
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

def get_executive_styles():
    """Builds an executive typography hierarchy for C-suite / Board financial advisory reports."""
    styles = getSampleStyleSheet()
    
    return {
        'company_header_en': ParagraphStyle(
            'CompHeadEn',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=13,
            leading=16,
            textColor=colors.white
        ),
        'company_header_meta': ParagraphStyle(
            'CompHeadMeta',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=7.5,
            leading=10.5,
            textColor=colors.HexColor('#94A3B8')
        ),
        'doc_type_badge': ParagraphStyle(
            'DocTypeBadge',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=13,
            leading=16,
            textColor=GOLD_BG,
            alignment=2
        ),
        'doc_type_sub': ParagraphStyle(
            'DocTypeSub',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=7.5,
            leading=10.5,
            textColor=colors.HexColor('#CBD5E1'),
            alignment=2
        ),
        'section_title': ParagraphStyle(
            'SecTitle',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=9.5,
            leading=12,
            textColor=NAVY_PRIMARY
        ),
        'vendor_banner_title': ParagraphStyle(
            'VendorBannerTitle',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=9,
            leading=11.5,
            textColor=colors.white
        ),
        'vendor_banner_meta': ParagraphStyle(
            'VendorBannerMeta',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=8,
            leading=10.5,
            textColor=colors.HexColor('#FEF08A'),
            alignment=2
        ),
        'kpi_title': ParagraphStyle(
            'KpiTitle',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=6.5,
            leading=8,
            textColor=NEUTRAL_MUTED,
            alignment=1
        ),
        'kpi_val_large': ParagraphStyle(
            'KpiValLarge',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=11.5,
            leading=14,
            textColor=NEUTRAL_DARK,
            alignment=1
        ),
        'kpi_sub_tag': ParagraphStyle(
            'KpiSubTag',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=6.5,
            leading=8,
            alignment=1
        ),
        'kpi_subTag': ParagraphStyle(
            'KpiSubTag2',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=6.5,
            leading=8,
            alignment=1
        ),
        'th_white': ParagraphStyle(
            'THWhite',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=7,
            leading=9,
            textColor=colors.white
        ),
        'th_white_right': ParagraphStyle(
            'THWhiteRight',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=7,
            leading=9,
            textColor=colors.white,
            alignment=2
        ),
        'th_white_center': ParagraphStyle(
            'THWhiteCenter',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=7,
            leading=9,
            textColor=colors.white,
            alignment=1
        ),
        'cell_text': ParagraphStyle(
            'CellText',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=7,
            leading=9.5,
            textColor=NEUTRAL_BODY
        ),
        'cell_bold': ParagraphStyle(
            'CellBold',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=7,
            leading=9.5,
            textColor=NEUTRAL_DARK
        ),
        'cell_right': ParagraphStyle(
            'CellRight',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=7,
            leading=9.5,
            textColor=NEUTRAL_BODY,
            alignment=2
        ),
        'cell_right_bold': ParagraphStyle(
            'CellRightBold',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=7,
            leading=9.5,
            textColor=NEUTRAL_DARK,
            alignment=2
        ),
        'advisory_body': ParagraphStyle(
            'AdvBody',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=7.5,
            leading=10.5,
            textColor=NEUTRAL_DARK
        ),
        'sig_title': ParagraphStyle(
            'SigTitle',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=7.5,
            leading=9.5,
            textColor=NEUTRAL_DARK,
            alignment=1
        ),
        'sig_sub': ParagraphStyle(
            'SigSub',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=7,
            leading=9,
            textColor=NEUTRAL_MUTED,
            alignment=1
        ),
        'footer_note': ParagraphStyle(
            'FooterNote',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=6.5,
            leading=8.5,
            textColor=NEUTRAL_MUTED,
            alignment=1
        )
    }

def format_status_badge(status: str) -> str:
    """Renders high-contrast, clean status pills."""
    st = (status or "Pending").strip()
    if st == "Paid":
        return "<font color='#15803D'><b>● PAID (خالص)</b></font>"
    elif st in ("Partially Paid", "Partial"):
        return "<font color='#B45309'><b>● PARTIAL (سداد جزئي)</b></font>"
    elif st == "Approved":
        return "<font color='#1D4ED8'><b>● APPROVED (معتمد)</b></font>"
    else:
        return "<font color='#B91C1C'><b>● PENDING (مستحق)</b></font>"


# =========================================================================
# 1. EXECUTIVE ACCOUNTS PAYABLE & SUPPLIER SCHEDULE REPORT (FOR CFO / BOSS)
# =========================================================================
def generate_supplier_summary_report_pdf(
    invoices: List[Dict[str, Any]],
    summary_stats: Dict[str, Any],
    company_info: Dict[str, Any],
    filter_info: Optional[Dict[str, Any]] = None
) -> bytes:
    """
    Generates an executive, boardroom-ready Accounts Payable Financial Advisory Report PDF.
    Organized strictly by supplier with rich corporate headers, subtotal ribbons,
    cash-flow liquidity risk advisory, and certified signature blocks.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=26,
        leftMargin=26,
        topMargin=24,
        bottomMargin=24
    )
    
    st = get_executive_styles()
    elements = []
    
    company_name = company_info.get("company_name", "Al-Amal Enterprise Solutions KSA")
    ar_name = company_info.get("company_arabic_name", "شركة الأمل لترشيد الحلول المتكاملة")
    cr_num = company_info.get("cr_number", "1010894512")
    address = company_info.get("address", "King Fahd Road, Riyadh, Saudi Arabia")
    
    gen_time = format_long_datetime()
    f_info = filter_info or {}
    sel_sups = f_info.get("selected_suppliers", "All Registered Suppliers")
    st_filter = f_info.get("status", "All Statuses")
    date_scope = f_info.get("date_range", "All Historical Invoices")
    
    # 1. High-Contrast Deep Navy Executive Header Banner
    header_data = [
        [
            Paragraph(f"<b>{company_name}</b><br/><font size=7.5 color='#CBD5E1'>{ar_name}</font><br/><font size=7 color='#94A3B8'>Commercial Reg: {cr_num} • VAT: 300492819200003 • {address}</font>", st['company_header_en']),
            Paragraph("<b>ACCOUNTS PAYABLE & SUPPLIER AUDIT</b><br/><font size=7.5 color='#FDE68A'>تقرير التزامات الموردين والتدفقات النقدية</font><br/><font size=7 color='#94A3B8'>Generated: " + gen_time + " • Confidential</font>", st['doc_type_badge'])
        ]
    ]
    header_table = Table(header_data, colWidths=[4.3*inch, 3.4*inch])
    header_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), NAVY_PRIMARY),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 4))
    
    # Gold Accent Separator Line
    elements.append(HRFlowable(width="100%", thickness=2, color=GOLD_ACCENT, spaceAfter=8))
    
    # 2. Executive Scope & Parameters Strip
    scope_data = [
        [
            Paragraph("<b>REPORTING SCOPE:</b>", st['cell_bold']), Paragraph(str(sel_sups), st['cell_text']),
            Paragraph("<b>AUDIT DATE:</b>", st['cell_bold']), Paragraph(gen_time, st['cell_text'])
        ],
        [
            Paragraph("<b>PAYMENT STATUS:</b>", st['cell_bold']), Paragraph(str(st_filter), st['cell_text']),
            Paragraph("<b>DATE RANGE:</b>", st['cell_bold']), Paragraph(str(date_scope), st['cell_text'])
        ]
    ]
    scope_table = Table(scope_data, colWidths=[1.4*inch, 3.1*inch, 1.1*inch, 2.1*inch])
    scope_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), NEUTRAL_LIGHT),
        ('BOX', (0,0), (-1,-1), 0.5, NEUTRAL_BORDER),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    elements.append(scope_table)
    elements.append(Spacer(1, 8))
    
    # 3. 4 Executive KPI Financial Summary Cards
    tot_billed = float(summary_stats.get("total_billed", sum(float(i.get("amount", 0)) for i in invoices)))
    tot_paid = float(summary_stats.get("total_paid", sum(float(i.get("paid_amount", 0)) for i in invoices)))
    tot_rem = float(summary_stats.get("total_outstanding_payable", sum(float(i.get("remaining_amount", 0)) for i in invoices)))
    
    overdue_invoices = [i for i in invoices if float(i.get("remaining_amount", 0)) > 0]
    settled_pct = round((tot_paid / tot_billed * 100), 1) if tot_billed > 0 else 100.0
    
    c1 = [Paragraph("TOTAL BILLED LIABILITY", st['kpi_title']), Paragraph(f"SAR {tot_billed:,.2f}", st['kpi_val_large']), Paragraph(f"<font color='#1E40AF'><b>{len(invoices)} Invoices In Scope</b></font>", st['kpi_subTag'])]
    c2 = [Paragraph("SETTLED DISBURSEMENTS", st['kpi_title']), Paragraph(f"SAR {tot_paid:,.2f}", ParagraphStyle('PVal', parent=st['kpi_val_large'], textColor=EMERALD_BRAND)), Paragraph(f"<font color='#065F46'><b>● {settled_pct}% Disbursed</b></font>", st['kpi_subTag'])]
    c3 = [Paragraph("OUTSTANDING PAYABLE (NET DUE)", st['kpi_title']), Paragraph(f"SAR {tot_rem:,.2f}", ParagraphStyle('RVal', parent=st['kpi_val_large'], textColor=RED_ALERT if tot_rem > 0 else EMERALD_BRAND)), Paragraph(f"<font color='#991B1B'><b>● {len(overdue_invoices)} Open Invoices</b></font>" if tot_rem > 0 else "<font color='#065F46'><b>● Fully Settled</b></font>", st['kpi_subTag'])]
    c4 = [Paragraph("WORKING CAPITAL IMPACT", st['kpi_title']), Paragraph(f"SAR {tot_rem:,.2f}", ParagraphStyle('WVal', parent=st['kpi_val_large'], textColor=NAVY_PRIMARY)), Paragraph("<font color='#B45309'><b>Cash Flow Advisory Active</b></font>", st['kpi_subTag'])]
    
    kpi_table = Table([[c1, c2, c3, c4]], colWidths=[1.92*inch, 1.92*inch, 1.92*inch, 1.92*inch])
    kpi_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (0,-1), BLUE_INFO_BG),
        ('BACKGROUND', (1,0), (1,-1), EMERALD_LIGHT),
        ('BACKGROUND', (2,0), (2,-1), RED_ALERT_BG if tot_rem > 0 else EMERALD_LIGHT),
        ('BACKGROUND', (3,0), (3,-1), GOLD_BG),
        ('BOX', (0,0), (-1,-1), 0.8, NEUTRAL_BORDER),
        ('INNERGRID', (0,0), (-1,-1), 0.5, NEUTRAL_BORDER),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
    ]))
    elements.append(kpi_table)
    elements.append(Spacer(1, 10))
    
    # 4. Grouped & Sorted By Supplier
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for inv in invoices:
        c_name = str(inv.get("company_name", "Other Registered Vendors")).strip()
        if c_name not in grouped:
            grouped[c_name] = []
        grouped[c_name].append(inv)
        
    # Sort suppliers alphabetically or by highest balance due
    sorted_suppliers = sorted(grouped.items(), key=lambda x: sum(float(i.get("remaining_amount", max(0.0, float(i.get("amount", 0)) - float(i.get("paid_amount", 0))))) for i in x[1]), reverse=True)
    
    for v_idx, (vendor_name, v_invoices) in enumerate(sorted_suppliers, 1):
        v_billed = sum(float(i.get("amount", 0.0)) for i in v_invoices)
        v_paid = sum(float(i.get("paid_amount", 0.0)) for i in v_invoices)
        v_rem = sum(float(i.get("remaining_amount", max(0.0, float(i.get("amount", 0.0)) - float(i.get("paid_amount", 0.0))))) for i in v_invoices)
        
        vendor_flowables = []
        
        # Vendor Section Banner (High-Contrast Slate Navy)
        v_header_data = [
            [
                Paragraph(f"🏢 <b>VENDOR #{v_idx}: {vendor_name.upper()}</b> &nbsp;<font size=7 color='#CBD5E1'>({len(v_invoices)} Invoices)</font>", st['vendor_banner_title']),
                Paragraph(f"Billed: <b>SAR {v_billed:,.2f}</b> &nbsp;|&nbsp; Paid: <b>SAR {v_paid:,.2f}</b> &nbsp;|&nbsp; <font color='#FCA5A5'><b>Net Due: SAR {v_rem:,.2f}</b></font>", st['vendor_banner_meta'])
            ]
        ]
        v_header_table = Table(v_header_data, colWidths=[4.2*inch, 3.5*inch])
        v_header_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), NAVY_SECONDARY),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
            ('LEFTPADDING', (0,0), (-1,-1), 6),
            ('RIGHTPADDING', (0,0), (-1,-1), 6),
        ]))
        vendor_flowables.append(v_header_table)
        
        # Invoice Rows for this Vendor
        rows = [
            [
                Paragraph("INVOICE #", st['th_white']),
                Paragraph("INVOICE DATE", st['th_white']),
                Paragraph("SUPPLY PERIOD", st['th_white']),
                Paragraph("DUE DATE", st['th_white']),
                Paragraph("BILLED (SAR)", st['th_white_right']),
                Paragraph("PAID (SAR)", st['th_white_right']),
                Paragraph("BALANCE DUE", st['th_white_right']),
                Paragraph("PAYMENT STATUS", st['th_white_center'])
            ]
        ]
        
        # Sort invoices for this vendor by invoice_date
        sorted_v_invoices = sorted(v_invoices, key=lambda x: str(x.get("invoice_date", "")))
        
        for r_idx, inv in enumerate(sorted_v_invoices):
            period_str = format_date_range(
                inv.get("supply_start_date") or inv.get("supply_date"),
                inv.get("supply_end_date") or inv.get("supply_date")
            )
            inv_d_str = format_long_date(inv.get("invoice_date"))
            due_d_str = format_long_date(inv.get("due_date"))
            
            amt = float(inv.get("amount", 0.0))
            pd = float(inv.get("paid_amount", 0.0))
            rem = float(inv.get("remaining_amount", max(0.0, amt - pd)))
            st_text = str(inv.get("status", "Pending"))
            inv_num = str(inv.get('invoice_number') or f"#INV-{inv.get('id', '001')}")
            
            rows.append([
                Paragraph(f"<b>{inv_num}</b>", st['cell_bold']),
                Paragraph(inv_d_str, st['cell_text']),
                Paragraph(period_str, st['cell_text']),
                Paragraph(due_d_str, st['cell_text']),
                Paragraph(f"{amt:,.2f}", st['cell_right']),
                Paragraph(f"{pd:,.2f}", st['cell_right']),
                Paragraph(f"<b>{rem:,.2f}</b>", ParagraphStyle('BalDueCell', parent=st['cell_right_bold'], textColor=RED_ALERT if rem > 0 else EMERALD_BRAND)),
                Paragraph(format_status_badge(st_text), ParagraphStyle('StatCent', parent=st['cell_text'], alignment=1))
            ])
            
        # Vendor Subtotal Row
        rows.append([
            Paragraph(f"<b>SUBTOTAL ({vendor_name}):</b>", ParagraphStyle('SubLbl', parent=st['cell_bold'], fontSize=7.5)),
            Paragraph("", st['cell_text']),
            Paragraph("", st['cell_text']),
            Paragraph("", st['cell_text']),
            Paragraph(f"<b>SAR {v_billed:,.2f}</b>", st['cell_right_bold']),
            Paragraph(f"<b>SAR {v_paid:,.2f}</b>", ParagraphStyle('SubPaid', parent=st['cell_right_bold'], textColor=EMERALD_BRAND)),
            Paragraph(f"<b>SAR {v_rem:,.2f}</b>", ParagraphStyle('SubRem', parent=st['cell_right_bold'], textColor=RED_ALERT if v_rem > 0 else EMERALD_BRAND)),
            Paragraph(f"<b>{'● ' + str(len(v_invoices)) + ' Bills'}</b>", ParagraphStyle('SubCnt', parent=st['cell_text'], alignment=1, fontName='Helvetica-Bold'))
        ])
        
        t = Table(rows, colWidths=[1.1*inch, 0.9*inch, 1.5*inch, 0.9*inch, 0.85*inch, 0.85*inch, 0.85*inch, 0.75*inch])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), EMERALD_BRAND),
            ('BOX', (0,0), (-1,-1), 0.5, NEUTRAL_BORDER),
            ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
            ('ROWBACKGROUNDS', (0,1), (-1,-2), [colors.white, NEUTRAL_ZEBRA]),
            ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#E2E8F0')),  # Distinct subtotal row
            ('TOPPADDING', (0,0), (-1,-1), 3.5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 3.5),
            ('LEFTPADDING', (0,0), (-1,-1), 4),
            ('RIGHTPADDING', (0,0), (-1,-1), 4),
        ]))
        vendor_flowables.append(t)
        vendor_flowables.append(Spacer(1, 8))
        
        elements.append(KeepTogether(vendor_flowables))
        
    # 5. Executive Consolidated Grand Totals Bar (Gold / Navy Luxury Finish)
    gt_data = [
        [
            Paragraph("<b>CONSOLIDATED ACCOUNTS PAYABLE GRAND TOTALS:</b>", ParagraphStyle('GTL', parent=st['cell_bold'], textColor=NAVY_PRIMARY, fontSize=8)),
            Paragraph(f"<b>Billed: SAR {tot_billed:,.2f}</b>", st['cell_bold']),
            Paragraph(f"<b>Disbursed: SAR {tot_paid:,.2f}</b>", ParagraphStyle('GP', parent=st['cell_bold'], textColor=EMERALD_BRAND)),
            Paragraph(f"<b>Total Net Liability: <font color='#991B1B'>SAR {tot_rem:,.2f}</font></b>", st['cell_bold'])
        ]
    ]
    gt_table = Table(gt_data, colWidths=[2.8*inch, 1.6*inch, 1.6*inch, 1.7*inch])
    gt_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), GOLD_BG),
        ('BOX', (0,0), (-1,-1), 1.2, GOLD_ACCENT),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    elements.append(gt_table)
    elements.append(Spacer(1, 10))
    
    # 6. CFO / Financial Advisor Strategic Advisory Note
    advice_text = (
        f"<b>CFO & Financial Advisory Commentary:</b> Out of <b>SAR {tot_billed:,.2f}</b> total liabilities, "
        f"<b>SAR {tot_paid:,.2f} ({settled_pct}%)</b> has been successfully disbursed via bank transfer. "
        f"The net remaining liability of <b>SAR {tot_rem:,.2f}</b> is distributed across {len(overdue_invoices)} open invoice(s). "
        f"<b>Recommendation:</b> Schedule priority settlement for due vendor invoices to ensure seamless supply chain continuity and preserve credit terms."
    )
    advice_table = Table([[Paragraph(advice_text, st['advisory_body'])]], colWidths=[7.7*inch])
    advice_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), BLUE_INFO_BG),
        ('BOX', (0,0), (-1,-1), 0.8, BLUE_INFO_BORDER),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    elements.append(advice_table)
    elements.append(Spacer(1, 12))
    
    # 7. Boardroom Authorization & Dual Verification Block
    sig_data = [
        [
            Paragraph("<b>PREPARED BY: SENIOR FINANCIAL CONTROLLER / ADVISOR</b>", st['sig_title']),
            Paragraph("<b>APPROVED BY: CHIEF EXECUTIVE OFFICER (CEO) / MANAGING DIRECTOR</b>", st['sig_title'])
        ],
        [
            Paragraph("Treasury & Accounts Payable Division<br/><br/>________________________________________<br/>Signature & Audit Verification Stamp", st['sig_sub']),
            Paragraph("Executive Leadership & Board of Directors<br/><br/>________________________________________<br/>Authorized Signature & Official Corporate Seal", st['sig_sub'])
        ]
    ]
    sig_table = Table(sig_data, colWidths=[3.85*inch, 3.85*inch])
    sig_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), NEUTRAL_LIGHT),
        ('BOX', (0,0), (-1,-1), 0.8, NEUTRAL_BORDER),
        ('INNERGRID', (0,0), (-1,-1), 0.5, NEUTRAL_BORDER),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
    ]))
    elements.append(sig_table)
    elements.append(Spacer(1, 6))
    
    elements.append(Paragraph("This accounts payable financial report is strictly confidential, generated for executive decision making, and certified under Saudi Corporate Law.", st['footer_note']))
    
    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


# =========================================================================
# 2. EXECUTIVE VENDOR STATEMENT OF ACCOUNT & SETTLEMENT VOUCHER
# =========================================================================
def generate_supplier_statement_pdf(sp: dict, payment_logs: list, company_info: dict) -> bytes:
    """Generates an executive-grade Vendor Statement of Account & Payment Voucher PDF."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=26,
        leftMargin=26,
        topMargin=24,
        bottomMargin=24
    )
    
    st = get_executive_styles()
    elements = []
    
    company_name = company_info.get("company_name", "Al-Amal Enterprise Solutions KSA")
    ar_name = company_info.get("company_arabic_name", "شركة الأمل لترشيد الحلول المتكاملة")
    cr_num = company_info.get("cr_number", "1010894512")
    address = company_info.get("address", "King Fahd Road, Riyadh, Saudi Arabia")
    
    total_amt = float(sp.get("amount", 0.0))
    paid_amt = float(sp.get("paid_amount", 0.0))
    rem_amt = float(sp.get("remaining_amount", max(0.0, total_amt - paid_amt)))
    
    inv_date_str = format_long_date(sp.get("invoice_date"))
    due_date_str = format_long_date(sp.get("due_date"))
    supply_period_str = format_date_range(
        sp.get("supply_start_date") or sp.get("supply_date"),
        sp.get("supply_end_date") or sp.get("supply_date")
    )
    gen_time = format_long_datetime()
    
    # 1. Executive Navy Top Header
    header_data = [
        [
            Paragraph(f"<b>{company_name}</b><br/><font size=7.5 color='#CBD5E1'>{ar_name}</font><br/><font size=7 color='#94A3B8'>CR: {cr_num} • VAT: 300492819200003 • {address}</font>", st['company_header_en']),
            Paragraph("<b>VENDOR STATEMENT OF ACCOUNT</b><br/><font size=7.5 color='#FDE68A'>كشف حساب المورد وسند الصرف الرسمي</font><br/><font size=7 color='#94A3B8'>Generated: " + gen_time + "</font>", st['doc_type_badge'])
        ]
    ]
    header_table = Table(header_data, colWidths=[4.3*inch, 3.4*inch])
    header_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), NAVY_PRIMARY),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 4))
    elements.append(HRFlowable(width="100%", thickness=2, color=GOLD_ACCENT, spaceAfter=8))
    
    # 2. 4 Metric Cards
    c1 = [Paragraph("TOTAL BILLED INVOICE", st['kpi_title']), Paragraph(f"SAR {total_amt:,.2f}", st['kpi_val_large']), Paragraph("<font color='#1E40AF'><b>Verified Liability</b></font>", st['kpi_subTag'])]
    c2 = [Paragraph("TOTAL DISBURSED (PAID)", st['kpi_title']), Paragraph(f"SAR {paid_amt:,.2f}", ParagraphStyle('PVal2', parent=st['kpi_val_large'], textColor=EMERALD_BRAND)), Paragraph(f"<font color='#065F46'><b>● {round(paid_amt/total_amt*100, 1) if total_amt>0 else 100}% Settled</b></font>", st['kpi_subTag'])]
    c3 = [Paragraph("NET BALANCE OUTSTANDING", st['kpi_title']), Paragraph(f"SAR {rem_amt:,.2f}", ParagraphStyle('RVal2', parent=st['kpi_val_large'], textColor=RED_ALERT if rem_amt > 0 else EMERALD_BRAND)), Paragraph(f"<font color='#991B1B'><b>● Net Due Now</b></font>" if rem_amt > 0 else "<font color='#065F46'><b>● Fully Disbursed</b></font>", st['kpi_subTag'])]
    c4 = [Paragraph("INVOICE STATUS", st['kpi_title']), Paragraph(format_status_badge(sp.get("status", "Pending")), ParagraphStyle('StatBig', parent=st['kpi_val_large'], fontSize=9.5)), Paragraph("<font color='#475569'>Official Record</font>", st['kpi_subTag'])]
    
    kpi_table = Table([[c1, c2, c3, c4]], colWidths=[1.92*inch, 1.92*inch, 1.92*inch, 1.92*inch])
    kpi_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (0,-1), BLUE_INFO_BG),
        ('BACKGROUND', (1,0), (1,-1), EMERALD_LIGHT),
        ('BACKGROUND', (2,0), (2,-1), RED_ALERT_BG if rem_amt > 0 else EMERALD_LIGHT),
        ('BACKGROUND', (3,0), (3,-1), GOLD_BG),
        ('BOX', (0,0), (-1,-1), 0.8, NEUTRAL_BORDER),
        ('INNERGRID', (0,0), (-1,-1), 0.5, NEUTRAL_BORDER),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
    ]))
    elements.append(kpi_table)
    elements.append(Spacer(1, 10))
    
    # 3. Vendor & Invoice Details Metadata Card
    inv_info = [
        [
            Paragraph("<b>Vendor Company:</b>", st['cell_bold']), Paragraph(str(sp.get("company_name", "")), st['cell_text']),
            Paragraph("<b>Invoice Number:</b>", st['cell_bold']), Paragraph(str(sp.get("invoice_number", "N/A")), st['cell_text'])
        ],
        [
            Paragraph("<b>Invoice Issue Date:</b>", st['cell_bold']), Paragraph(inv_date_str, st['cell_text']),
            Paragraph("<b>Payment Due Date:</b>", st['cell_bold']), Paragraph(due_date_str, st['cell_text'])
        ],
        [
            Paragraph("<b>Supply Period:</b>", st['cell_bold']), Paragraph(supply_period_str, st['cell_text']),
            Paragraph("<b>ERP Record Ref:</b>", st['cell_bold']), Paragraph(f"#INV-{sp.get('id', '')}", st['cell_text'])
        ],
        [
            Paragraph("<b>Service / Supply Scope:</b>", st['cell_bold']), Paragraph(str(sp.get("invoice_details", "N/A")), st['cell_text']),
            Paragraph("<b>Financial Remarks:</b>", st['cell_bold']), Paragraph(str(sp.get("remarks", "N/A")), st['cell_text'])
        ]
    ]
    inv_table = Table(inv_info, colWidths=[1.4*inch, 2.5*inch, 1.4*inch, 2.4*inch])
    inv_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), NEUTRAL_LIGHT),
        ('BOX', (0,0), (-1,-1), 0.5, NEUTRAL_BORDER),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    elements.append(inv_table)
    elements.append(Spacer(1, 10))
    
    # 4. Disbursal Settlement Log Table
    elements.append(Paragraph("<b>DISBURSAL TRANSACTION & SETTLEMENT LOGS</b>", st['section_title']))
    elements.append(Spacer(1, 4))
    
    log_rows = [
        [
            Paragraph("SETTLEMENT DATE", st['th_white']),
            Paragraph("PAYMENT METHOD", st['th_white']),
            Paragraph("TRANSACTION REF #", st['th_white']),
            Paragraph("SETTLEMENT DETAILS / NOTES", st['th_white']),
            Paragraph("AMOUNT DISBURSED", st['th_white_right'])
        ]
    ]
    
    if not payment_logs:
        log_rows.append([Paragraph("No payments disbursed yet. Full amount remains outstanding.", st['cell_text']), Paragraph("-", st['cell_text']), Paragraph("-", st['cell_text']), Paragraph("-", st['cell_text']), Paragraph("SAR 0.00", st['cell_right'])])
    else:
        for idx, lg in enumerate(payment_logs):
            amt_lg = float(lg.get("payment_amount", 0.0))
            pay_d_str = format_long_date(lg.get("payment_date"))
            log_rows.append([
                Paragraph(pay_d_str, st['cell_text']),
                Paragraph(str(lg.get("payment_method", "Bank Transfer")), st['cell_text']),
                Paragraph(str(lg.get("reference_number", "N/A")), st['cell_text']),
                Paragraph(str(lg.get("notes", "N/A")), st['cell_text']),
                Paragraph(f"<b>SAR {amt_lg:,.2f}</b>", st['cell_right_bold'])
            ])
            
    history_table = Table(log_rows, colWidths=[1.3*inch, 1.3*inch, 1.4*inch, 2.2*inch, 1.5*inch])
    history_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), NAVY_PRIMARY),
        ('BOX', (0,0), (-1,-1), 0.5, NEUTRAL_BORDER),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, NEUTRAL_ZEBRA]),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
    ]))
    elements.append(history_table)
    elements.append(Spacer(1, 14))
    
    # 5. Dual Signatures
    sig_data = [
        [
            Paragraph("<b>ACCOUNTS PAYABLE CONTROLLER</b>", st['sig_title']),
            Paragraph("<b>VENDOR AUTHORIZED REPRESENTATIVE</b>", st['sig_title'])
        ],
        [
            Paragraph("Finance & Treasury Department<br/><br/>________________________________________<br/>Authorized Signature & Company Stamp", st['sig_sub']),
            Paragraph("Vendor Commercial Receiver<br/><br/>________________________________________<br/>Signature & Official Stamp", st['sig_sub'])
        ]
    ]
    sig_table = Table(sig_data, colWidths=[3.85*inch, 3.85*inch])
    sig_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), NEUTRAL_LIGHT),
        ('BOX', (0,0), (-1,-1), 0.8, NEUTRAL_BORDER),
        ('INNERGRID', (0,0), (-1,-1), 0.5, NEUTRAL_BORDER),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
    ]))
    elements.append(sig_table)
    elements.append(Spacer(1, 6))
    
    elements.append(Paragraph("This official statement of account is issued under Saudi Commercial Law as certified proof of accounts payable settlement.", st['footer_note']))
    
    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


# =========================================================================
# 3. EXECUTIVE BILINGUAL SALARY PAYSLIP VOUCHER
# =========================================================================
def generate_payslip_pdf(employee_data: dict, payroll_detail: dict, company_info: dict) -> bytes:
    """Generates an executive Bilingual Saudi Standard Salary Voucher PDF."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=26,
        leftMargin=26,
        topMargin=24,
        bottomMargin=24
    )
    
    st = get_executive_styles()
    elements = []
    
    company_name = company_info.get("company_name", "Al-Amal Enterprise Solutions KSA")
    ar_name = company_info.get("company_arabic_name", "شركة الأمل لترشيد الحلول المتكاملة")
    cr_num = company_info.get("cr_number", "1010894512")
    gosi_reg = company_info.get("gosi_reg_number", "309481920")
    address = company_info.get("address", "King Fahd Road, Riyadh, Saudi Arabia")
    
    pay_period_str = format_pay_period(payroll_detail.get('month', ''), payroll_detail.get('year', ''))
    
    # 1. Executive Navy Header
    header_data = [
        [
            Paragraph(f"<b>{company_name}</b><br/><font size=7.5 color='#CBD5E1'>{ar_name}</font><br/><font size=7 color='#94A3B8'>CR: {cr_num} • GOSI: {gosi_reg} • {address}</font>", st['company_header_en']),
            Paragraph(f"<b>SALARY PAYSLIP VOUCHER</b><br/><font size=7.5 color='#FDE68A'>قسيمة الراتب الرسمية</font><br/><font size=7 color='#94A3B8'>Period: {pay_period_str}</font>", st['doc_type_badge'])
        ]
    ]
    header_table = Table(header_data, colWidths=[4.3*inch, 3.4*inch])
    header_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), NAVY_PRIMARY),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 4))
    elements.append(HRFlowable(width="100%", thickness=2, color=GOLD_ACCENT, spaceAfter=8))
    
    # 2. Employee Profile Metadata Card
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
            Paragraph("<b>Department:</b>", st['cell_bold']), Paragraph(str(employee_data.get("department_name", "General Operations")), st['cell_text'])
        ],
        [
            Paragraph("<b>Job Designation:</b>", st['cell_bold']), Paragraph(str(employee_data.get("designation", "N/A")), st['cell_text']),
            Paragraph("<b>Nationality Type:</b>", st['cell_bold']), Paragraph(nat_type, st['cell_text'])
        ],
        [
            Paragraph("<b>Bank / IBAN:</b>", st['cell_bold']), Paragraph(f"{employee_data.get('bank_name', 'Bank')} • {employee_data.get('iban', 'N/A')}", st['cell_text']),
            Paragraph("<b>Pay Period:</b>", st['cell_bold']), Paragraph(pay_period_str, st['cell_text'])
        ]
    ]
    emp_table = Table(emp_info, colWidths=[1.4*inch, 2.5*inch, 1.4*inch, 2.4*inch])
    emp_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), NEUTRAL_LIGHT),
        ('BOX', (0,0), (-1,-1), 0.5, NEUTRAL_BORDER),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    elements.append(emp_table)
    elements.append(Spacer(1, 8))
    
    # 3. KPI Metrics
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
    
    c1 = [Paragraph("BASIC CONTRACT SALARY", st['kpi_title']), Paragraph(f"SAR {basic:,.2f}", st['kpi_val_large']), Paragraph("<font color='#1E40AF'><b>Base Pay</b></font>", st['kpi_subTag'])]
    c2 = [Paragraph("TOTAL GROSS EARNINGS", st['kpi_title']), Paragraph(f"SAR {gross:,.2f}", ParagraphStyle('GrVal', parent=st['kpi_val_large'], textColor=BLUE_INFO)), Paragraph("<font color='#1E40AF'><b>Salary + Allowances</b></font>", st['kpi_subTag'])]
    c3 = [Paragraph("TOTAL DEDUCTIONS & GOSI", st['kpi_title']), Paragraph(f"SAR {total_ded:,.2f}", ParagraphStyle('DedVal', parent=st['kpi_val_large'], textColor=RED_ALERT)), Paragraph("<font color='#991B1B'><b>Statutory Withholding</b></font>", st['kpi_subTag'])]
    c4 = [Paragraph("NET SALARY PAYABLE", st['kpi_title']), Paragraph(f"SAR {net_pay:,.2f}", ParagraphStyle('NetMainVal', parent=st['kpi_val_large'], textColor=EMERALD_BRAND, fontSize=12)), Paragraph("<font color='#065F46'><b>● SAMA WPS Certified</b></font>", st['kpi_subTag'])]
    
    kpi_table = Table([[c1, c2, c3, c4]], colWidths=[1.92*inch, 1.92*inch, 1.92*inch, 1.92*inch])
    kpi_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (0,-1), NEUTRAL_LIGHT),
        ('BACKGROUND', (1,0), (1,-1), BLUE_INFO_BG),
        ('BACKGROUND', (2,0), (2,-1), RED_ALERT_BG),
        ('BACKGROUND', (3,0), (3,-1), EMERALD_LIGHT),
        ('BOX', (0,0), (-1,-1), 0.8, NEUTRAL_BORDER),
        ('INNERGRID', (0,0), (-1,-1), 0.5, NEUTRAL_BORDER),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
    ]))
    elements.append(kpi_table)
    elements.append(Spacer(1, 10))
    
    # 4. Detailed Earnings & Deductions Breakdown
    elements.append(Paragraph("<b>ITEMIZED SALARY & STATUTORY DEDUCTIONS BREAKDOWN</b>", st['section_title']))
    elements.append(Spacer(1, 4))
    
    fin_breakdown = [
        [
            Paragraph("EARNINGS CATEGORY", st['th_white']), Paragraph("AMOUNT (SAR)", st['th_white_right']),
            Paragraph("DEDUCTIONS & STATUTORY GOSI", st['th_white']), Paragraph("AMOUNT (SAR)", st['th_white_right'])
        ],
        [
            Paragraph("Basic Salary (الراتب الأساسي)", st['cell_text']), Paragraph(f"{basic:,.2f}", st['cell_right']),
            Paragraph(f"GOSI Employee Share ({'9.75%' if is_saudi else '0%'})", st['cell_text']), Paragraph(f"{gosi_emp:,.2f}", st['cell_right'])
        ],
        [
            Paragraph("Housing Allowance (بدل سكن)", st['cell_text']), Paragraph(f"{housing:,.2f}", st['cell_right']),
            Paragraph("Loan / Other Disciplinary Deductions", st['cell_text']), Paragraph(f"{other_ded:,.2f}", st['cell_right'])
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
    fin_table = Table(fin_breakdown, colWidths=[2.4*inch, 1.45*inch, 2.4*inch, 1.45*inch])
    fin_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), NAVY_PRIMARY),
        ('BOX', (0,0), (-1,-1), 0.5, NEUTRAL_BORDER),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('ROWBACKGROUNDS', (0,1), (-1,-2), [colors.white, NEUTRAL_ZEBRA]),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
    ]))
    elements.append(fin_table)
    elements.append(Spacer(1, 6))
    
    # Statutory Employer Contribution Note
    gosi_note = Paragraph(f"<font size=7 color='#475569'>* Employer Statutory GOSI Contribution for this period: <b>SAR {gosi_empr:,.2f}</b> ({'11.75%' if is_saudi else '2.0%'} per Saudi Social Insurance Law).</font>", st['cell_text'])
    elements.append(gosi_note)
    elements.append(Spacer(1, 14))
    
    # 5. Dual Verification & Corporate Stamp Block
    sig_data = [
        [
            Paragraph("<b>AUTHORIZED HR & PAYROLL CONTROLLER</b>", st['sig_title']),
            Paragraph("<b>EMPLOYEE ACKNOWLEDGMENT & RECEIPT</b>", st['sig_title'])
        ],
        [
            Paragraph("HR & Payroll Operations Department<br/><br/>________________________________________<br/>Signature & Corporate Stamp", st['sig_sub']),
            Paragraph("I acknowledge receipt of full salary settlement.<br/><br/>________________________________________<br/>Employee Signature & Date", st['sig_sub'])
        ]
    ]
    sig_table = Table(sig_data, colWidths=[3.85*inch, 3.85*inch])
    sig_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), NEUTRAL_LIGHT),
        ('BOX', (0,0), (-1,-1), 0.8, NEUTRAL_BORDER),
        ('INNERGRID', (0,0), (-1,-1), 0.5, NEUTRAL_BORDER),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
    ]))
    elements.append(sig_table)
    elements.append(Spacer(1, 6))
    
    elements.append(Paragraph("This payroll voucher is electronically certified and fully compliant with Saudi Labor Law & SAMA WPS regulations.", st['footer_note']))
    
    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
