import os
import io
from datetime import datetime, date
from typing import List, Dict, Any, Optional
from playwright.sync_api import sync_playwright

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

def html_to_pdf_playwright(html_content: str, landscape: bool = False) -> bytes:
    """Renders pixel-perfect, modern vector PDFs using Playwright Chromium."""
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage']
        )
        page = browser.new_page()
        page.set_content(html_content, wait_until='networkidle')
        pdf_bytes = page.pdf(
            format='Letter',
            landscape=landscape,
            print_background=True,
            margin={'top': '20px', 'bottom': '20px', 'left': '22px', 'right': '22px'}
        )
        browser.close()
        return pdf_bytes


# =========================================================================
# 1. EXECUTIVE ACCOUNTS PAYABLE & SUPPLIER AUDIT REPORT (FOR BOSS / CFO)
# =========================================================================
def generate_supplier_summary_report_pdf(
    invoices: List[Dict[str, Any]],
    summary_stats: Dict[str, Any],
    company_info: Dict[str, Any],
    filter_info: Optional[Dict[str, Any]] = None
) -> bytes:
    """
    Generates a high-stakes, executive-grade Accounts Payable Financial Advisory Report PDF
    using Playwright with rich corporate styling, supplier grouping, subtotal ribbons,
    cash-flow advisory, and boardroom verification.
    """
    company_name = company_info.get("company_name", "ADK Co., LTD.")
    ar_name = company_info.get("company_arabic_name", "شركة إيه دي كيه للخدمات الصناعية المحدودة")
    cr_num = company_info.get("cr_number", "2055001234")
    address = company_info.get("address", "2837, B13, Tebah District, Al Jubail, Kingdom of Saudi Arabia")
    
    gen_time = format_long_datetime()
    f_info = filter_info or {}
    sel_sups = f_info.get("selected_suppliers", "All Registered Suppliers")
    st_filter = f_info.get("status", "All Statuses")
    date_scope = f_info.get("date_range", "All Historical Invoices")
    
    tot_billed = float(summary_stats.get("total_billed", sum(float(i.get("amount", 0)) for i in invoices)))
    tot_paid = float(summary_stats.get("total_paid", sum(float(i.get("paid_amount", 0)) for i in invoices)))
    tot_rem = float(summary_stats.get("total_outstanding_payable", sum(float(i.get("remaining_amount", 0)) for i in invoices)))
    
    settled_pct = round((tot_paid / tot_billed * 100), 1) if tot_billed > 0 else 100.0
    open_invoices_count = sum(1 for i in invoices if float(i.get("remaining_amount", 0)) > 0)
    
    # Group and sort by supplier
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for inv in invoices:
        c_name = str(inv.get("company_name", "Other Registered Vendors")).strip()
        if c_name not in grouped:
            grouped[c_name] = []
        grouped[c_name].append(inv)
        
    sorted_suppliers = sorted(
        grouped.items(),
        key=lambda x: sum(float(i.get("remaining_amount", max(0.0, float(i.get("amount", 0)) - float(i.get("paid_amount", 0))))) for i in x[1]),
        reverse=True
    )
    
    vendor_sections_html = ""
    for v_idx, (vendor_name, v_invoices) in enumerate(sorted_suppliers, 1):
        v_billed = sum(float(i.get("amount", 0.0)) for i in v_invoices)
        v_paid = sum(float(i.get("paid_amount", 0.0)) for i in v_invoices)
        v_rem = sum(float(i.get("remaining_amount", max(0.0, float(i.get("amount", 0.0)) - float(i.get("paid_amount", 0.0))))) for i in v_invoices)
        
        sorted_v_invoices = sorted(v_invoices, key=lambda x: str(x.get("invoice_date", "")))
        
        inv_rows_html = ""
        for inv in sorted_v_invoices:
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
            
            badge_class = "badge-paid" if st_text == "Paid" else ("badge-partial" if st_text in ("Partially Paid", "Partial") else "badge-pending")
            
            inv_rows_html += f"""
            <tr>
              <td><strong>{inv_num}</strong></td>
              <td>{inv_d_str}</td>
              <td>{period_str}</td>
              <td>{due_d_str}</td>
              <td class="num">{amt:,.2f}</td>
              <td class="num font-green">{pd:,.2f}</td>
              <td class="num {'font-red bold' if rem > 0 else 'font-green bold'}">{rem:,.2f}</td>
              <td class="text-center"><span class="badge {badge_class}">{st_text.upper()}</span></td>
            </tr>
            """
            
        vendor_sections_html += f"""
        <div class="vendor-block">
          <div class="vendor-banner">
            <div class="vendor-title">🏢 VENDOR #{v_idx}: <strong>{vendor_name.upper()}</strong> <span class="vendor-count">({len(v_invoices)} Invoices)</span></div>
            <div class="vendor-meta">
              Billed: <strong>SAR {v_billed:,.2f}</strong> &nbsp;|&nbsp;
              Paid: <strong style="color: #6EE7B7;">SAR {v_paid:,.2f}</strong> &nbsp;|&nbsp;
              Net Due: <strong style="color: #FCA5A5;">SAR {v_rem:,.2f}</strong>
            </div>
          </div>
          
          <table class="data-table">
            <thead>
              <tr>
                <th>INVOICE #</th>
                <th>INVOICE DATE</th>
                <th>SUPPLY PERIOD</th>
                <th>DUE DATE</th>
                <th class="text-right">BILLED (SAR)</th>
                <th class="text-right">PAID (SAR)</th>
                <th class="text-right">BALANCE DUE (SAR)</th>
                <th class="text-center">PAYMENT STATUS</th>
              </tr>
            </thead>
            <tbody>
              {inv_rows_html}
            </tbody>
            <tfoot>
              <tr class="subtotal-row">
                <td colspan="4"><strong>SUBTOTAL ({vendor_name}):</strong></td>
                <td class="num"><strong>SAR {v_billed:,.2f}</strong></td>
                <td class="num font-green"><strong>SAR {v_paid:,.2f}</strong></td>
                <td class="num {'font-red bold' if v_rem > 0 else 'font-green bold'}"><strong>SAR {v_rem:,.2f}</strong></td>
                <td class="text-center"><strong>● {len(v_invoices)} Bills</strong></td>
              </tr>
            </tfoot>
          </table>
        </div>
        """
        
    html = f"""<!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <title>Accounts Payable Financial Audit Report</title>
      <style>
        @page {{
          size: letter;
          margin: 0;
        }}
        * {{
          box-sizing: border-box;
          margin: 0;
          padding: 0;
          font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
        }}
        body {{
          background-color: #FFFFFF;
          color: #0F172A;
          padding: 16px 20px;
          font-size: 8pt;
          line-height: 1.35;
        }}
        .header-banner {{
          background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%);
          color: #FFFFFF;
          padding: 12px 16px;
          border-radius: 6px;
          display: flex;
          justify-content: space-between;
          align-items: center;
          border-bottom: 3px solid #B45309;
        }}
        .header-left .comp-title {{
          font-size: 13pt;
          font-weight: 800;
          letter-spacing: -0.2px;
        }}
        .header-left .comp-ar {{
          font-size: 8.5pt;
          color: #94A3B8;
          margin-top: 1px;
        }}
        .header-left .comp-meta {{
          font-size: 7pt;
          color: #64748B;
          margin-top: 2px;
        }}
        .header-right {{
          text-align: right;
        }}
        .header-right .doc-badge {{
          font-size: 12pt;
          font-weight: 800;
          color: #FEF3C7;
          letter-spacing: 0.5px;
        }}
        .header-right .doc-ar {{
          font-size: 8pt;
          color: #FDE68A;
        }}
        .header-right .doc-meta {{
          font-size: 7pt;
          color: #94A3B8;
          margin-top: 2px;
        }}
        
        .scope-strip {{
          background: #F8FAFC;
          border: 1px solid #E2E8F0;
          border-radius: 6px;
          padding: 6px 12px;
          margin: 8px 0;
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 4px 16px;
          font-size: 7.5pt;
        }}
        .scope-item strong {{
          color: #0F172A;
        }}
        
        .kpi-grid {{
          display: grid;
          grid-template-columns: repeat(4, 1fr);
          gap: 8px;
          margin-bottom: 10px;
        }}
        .kpi-card {{
          padding: 8px 10px;
          border-radius: 6px;
          border: 1px solid #CBD5E1;
          text-align: center;
        }}
        .kpi-card.blue {{ background: #EFF6FF; border-color: #BFDBFE; }}
        .kpi-card.green {{ background: #ECFDF5; border-color: #A7F3D0; }}
        .kpi-card.red {{ background: #FEF2F2; border-color: #FECACA; }}
        .kpi-card.gold {{ background: #FEF3C7; border-color: #FDE68A; }}
        
        .kpi-label {{
          font-size: 6.5pt;
          font-weight: 700;
          color: #64748B;
          text-transform: uppercase;
          letter-spacing: 0.5px;
        }}
        .kpi-val {{
          font-size: 11.5pt;
          font-weight: 800;
          color: #0F172A;
          margin: 2px 0;
        }}
        .kpi-sub {{
          font-size: 6.5pt;
          font-weight: 700;
        }}
        
        .vendor-block {{
          margin-bottom: 10px;
          page-break-inside: avoid;
        }}
        .vendor-banner {{
          background: #1E293B;
          color: #FFFFFF;
          padding: 5px 10px;
          border-radius: 5px 5px 0 0;
          display: flex;
          justify-content: space-between;
          align-items: center;
          font-size: 8pt;
        }}
        .vendor-banner .vendor-title {{
          font-weight: 700;
        }}
        .vendor-banner .vendor-count {{
          font-size: 7pt;
          color: #CBD5E1;
          font-weight: normal;
        }}
        
        .data-table {{
          width: 100%;
          border-collapse: collapse;
          font-size: 7.2pt;
          border: 1px solid #CBD5E1;
          border-top: none;
        }}
        .data-table th {{
          background: #065F46;
          color: #FFFFFF;
          font-weight: 700;
          padding: 4px 6px;
          text-align: left;
          font-size: 6.8pt;
        }}
        .data-table td {{
          padding: 3.5px 6px;
          border-bottom: 1px solid #E2E8F0;
          color: #334155;
        }}
        .data-table tbody tr:nth-child(even) {{
          background-color: #F8FAFC;
        }}
        .subtotal-row td {{
          background-color: #E2E8F0;
          border-top: 1.5px solid #94A3B8;
          color: #0F172A;
          font-size: 7.5pt;
        }}
        
        .badge {{
          display: inline-block;
          padding: 1px 5px;
          border-radius: 3px;
          font-size: 6.2pt;
          font-weight: 700;
        }}
        .badge-paid {{ background: #DCFCE7; color: #15803D; border: 1px solid #86EFAC; }}
        .badge-partial {{ background: #FEF3C7; color: #B45309; border: 1px solid #FDE68A; }}
        .badge-pending {{ background: #FEE2E2; color: #B91C1C; border: 1px solid #FECACA; }}
        
        .num {{ text-align: right; font-variant-numeric: tabular-nums; }}
        .text-right {{ text-align: right; }}
        .text-center {{ text-align: center; }}
        .font-green {{ color: #065F46; }}
        .font-red {{ color: #991B1B; }}
        .bold {{ font-weight: 700; }}
        
        .grand-total-bar {{
          background: #FEF3C7;
          border: 1.5px solid #B45309;
          border-radius: 6px;
          padding: 6px 12px;
          display: flex;
          justify-content: space-between;
          align-items: center;
          font-size: 8pt;
          margin-bottom: 8px;
        }}
        
        .advisory-box {{
          background: #EFF6FF;
          border: 1px solid #3B82F6;
          border-radius: 6px;
          padding: 6px 10px;
          font-size: 7.2pt;
          color: #0F172A;
          margin-bottom: 10px;
        }}
        
        .sig-grid {{
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 12px;
          margin-top: 8px;
        }}
        .sig-card {{
          background: #F8FAFC;
          border: 1px solid #CBD5E1;
          border-radius: 6px;
          padding: 6px 10px;
          text-align: center;
        }}
        .sig-card .sig-title {{
          font-size: 7.2pt;
          font-weight: 700;
          color: #0F172A;
          margin-bottom: 2px;
        }}
        .sig-card .sig-dept {{
          font-size: 6.8pt;
          color: #64748B;
          margin-bottom: 14px;
        }}
        .sig-line {{
          border-top: 1px solid #94A3B8;
          padding-top: 3px;
          font-size: 6.5pt;
          color: #64748B;
        }}
        
        .footer-note {{
          text-align: center;
          font-size: 6.5pt;
          color: #94A3B8;
          margin-top: 6px;
        }}
      </style>
    </head>
    <body>
      <div class="header-banner">
        <div class="header-left">
          <div class="comp-title">🏢 {company_name}</div>
          <div class="comp-ar">{ar_name}</div>
          <div class="comp-meta">Commercial Reg: {cr_num} • VAT: 300492819200003 • {address}</div>
        </div>
        <div class="header-right">
          <div class="doc-badge">ACCOUNTS PAYABLE & SUPPLIER AUDIT</div>
          <div class="doc-ar">تقرير التزامات الموردين والتدفقات النقدية</div>
          <div class="doc-meta">Generated: {gen_time} • Strictly Confidential</div>
        </div>
      </div>
      
      <div class="scope-strip">
        <div class="scope-item"><strong>REPORTING SCOPE:</strong> {sel_sups}</div>
        <div class="scope-item"><strong>AUDIT TIMESTAMP:</strong> {gen_time}</div>
        <div class="scope-item"><strong>PAYMENT STATUS SCOPE:</strong> {st_filter}</div>
        <div class="scope-item"><strong>DATE RANGE:</strong> {date_scope}</div>
      </div>
      
      <div class="kpi-grid">
        <div class="kpi-card blue">
          <div class="kpi-label">TOTAL BILLED LIABILITY</div>
          <div class="kpi-val">SAR {tot_billed:,.2f}</div>
          <div class="kpi-sub" style="color: #1E40AF;">{len(invoices)} Invoices In Scope</div>
        </div>
        <div class="kpi-card green">
          <div class="kpi-label">SETTLED DISBURSEMENTS</div>
          <div class="kpi-val" style="color: #065F46;">SAR {tot_paid:,.2f}</div>
          <div class="kpi-sub" style="color: #065F46;">● {settled_pct}% Disbursed</div>
        </div>
        <div class="kpi-card {'red' if tot_rem > 0 else 'green'}">
          <div class="kpi-label">OUTSTANDING PAYABLE (NET DUE)</div>
          <div class="kpi-val" style="color: {'#991B1B' if tot_rem > 0 else '#065F46'};">SAR {tot_rem:,.2f}</div>
          <div class="kpi-sub" style="color: {'#991B1B' if tot_rem > 0 else '#065F46'};">{'● ' + str(open_invoices_count) + ' Open Invoices' if tot_rem > 0 else '● Fully Settled'}</div>
        </div>
        <div class="kpi-card gold">
          <div class="kpi-label">WORKING CAPITAL IMPACT</div>
          <div class="kpi-val">SAR {tot_rem:,.2f}</div>
          <div class="kpi-sub" style="color: #B45309;">Cash Flow Advisory Active</div>
        </div>
      </div>
      
      {vendor_sections_html}
      
      <div class="grand-total-bar">
        <div><strong>CONSOLIDATED ACCOUNTS PAYABLE GRAND TOTALS:</strong></div>
        <div>Billed: <strong>SAR {tot_billed:,.2f}</strong></div>
        <div style="color: #065F46;">Disbursed: <strong>SAR {tot_paid:,.2f}</strong></div>
        <div style="color: #991B1B;">Total Net Liability: <strong>SAR {tot_rem:,.2f}</strong></div>
      </div>
      
      <div class="advisory-box">
        <strong>CFO & Financial Advisory Commentary:</strong> Out of <strong>SAR {tot_billed:,.2f}</strong> total liabilities, 
        <strong>SAR {tot_paid:,.2f} ({settled_pct}%)</strong> has been successfully settled via corporate bank transfer. 
        The net remaining liability of <strong>SAR {tot_rem:,.2f}</strong> is distributed across {open_invoices_count} open invoice(s). 
        <strong>Strategic Recommendation:</strong> Prioritize settlement for due vendor invoices to ensure supply continuity and preserve vendor credit terms.
      </div>
      
      <div class="sig-grid">
        <div class="sig-card">
          <div class="sig-title">PREPARED BY: SENIOR FINANCIAL CONTROLLER / ADVISOR</div>
          <div class="sig-dept">Treasury & Accounts Payable Division</div>
          <div class="sig-line">Signature & Audit Verification Stamp</div>
        </div>
        <div class="sig-card">
          <div class="sig-title">APPROVED BY: CHIEF EXECUTIVE OFFICER (CEO) / MANAGING DIRECTOR</div>
          <div class="sig-dept">Executive Leadership & Board of Directors</div>
          <div class="sig-line">Authorized Signature & Official Corporate Seal</div>
        </div>
      </div>
      
      <div class="footer-note">
        Page 1 of 1 | Strictly Confidential • Certified Accounts Payable Audit Report under Saudi Corporate Law
      </div>
    </body>
    </html>
    """
    return html_to_pdf_playwright(html)


# =========================================================================
# 2. EXECUTIVE VENDOR STATEMENT & SETTLEMENT VOUCHER
# =========================================================================
def generate_supplier_statement_pdf(sp: dict, payment_logs: list, company_info: dict) -> bytes:
    """Generates an executive Vendor Statement of Account & Payment Voucher PDF using Playwright."""
    company_name = company_info.get("company_name", "ADK Co., LTD.")
    ar_name = company_info.get("company_arabic_name", "شركة إيه دي كيه للخدمات الصناعية المحدودة")
    cr_num = company_info.get("cr_number", "2055001234")
    address = company_info.get("address", "2837, B13, Tebah District, Al Jubail, Kingdom of Saudi Arabia")
    
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
    
    settled_pct = round((paid_amt / total_amt * 100), 1) if total_amt > 0 else 100.0
    st_text = str(sp.get("status", "Pending"))
    badge_class = "badge-paid" if st_text == "Paid" else ("badge-partial" if st_text in ("Partially Paid", "Partial") else "badge-pending")
    
    logs_rows_html = ""
    if not payment_logs:
        logs_rows_html = '<tr><td colspan="5" class="text-center" style="padding: 10px;">No payment disbursals recorded yet. Full balance remains open.</td></tr>'
    else:
        for lg in payment_logs:
            amt_lg = float(lg.get("payment_amount", 0.0))
            pay_d_str = format_long_date(lg.get("payment_date"))
            logs_rows_html += f"""
            <tr>
              <td>{pay_d_str}</td>
              <td>{lg.get("payment_method", "Bank Transfer")}</td>
              <td><code>{lg.get("reference_number", "N/A")}</code></td>
              <td>{lg.get("notes", "N/A")}</td>
              <td class="num font-green bold">SAR {amt_lg:,.2f}</td>
            </tr>
            """
            
    html = f"""<!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <title>Vendor Statement of Account</title>
      <style>
        @page {{ size: letter; margin: 0; }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif; }}
        body {{ background-color: #FFFFFF; color: #0F172A; padding: 16px 20px; font-size: 8pt; line-height: 1.35; }}
        .header-banner {{
          background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%);
          color: #FFFFFF; padding: 12px 16px; border-radius: 6px; display: flex; justify-content: space-between; align-items: center; border-bottom: 3px solid #B45309;
        }}
        .header-left .comp-title {{ font-size: 13pt; font-weight: 800; }}
        .header-left .comp-ar {{ font-size: 8.5pt; color: #94A3B8; margin-top: 1px; }}
        .header-left .comp-meta {{ font-size: 7pt; color: #64748B; margin-top: 2px; }}
        .header-right {{ text-align: right; }}
        .header-right .doc-badge {{ font-size: 12pt; font-weight: 800; color: #FEF3C7; }}
        .header-right .doc-ar {{ font-size: 8pt; color: #FDE68A; }}
        .header-right .doc-meta {{ font-size: 7pt; color: #94A3B8; margin-top: 2px; }}
        
        .kpi-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; margin: 10px 0; }}
        .kpi-card {{ padding: 8px 10px; border-radius: 6px; border: 1px solid #CBD5E1; text-align: center; }}
        .kpi-card.blue {{ background: #EFF6FF; border-color: #BFDBFE; }}
        .kpi-card.green {{ background: #ECFDF5; border-color: #A7F3D0; }}
        .kpi-card.red {{ background: #FEF2F2; border-color: #FECACA; }}
        .kpi-card.gold {{ background: #FEF3C7; border-color: #FDE68A; }}
        .kpi-label {{ font-size: 6.5pt; font-weight: 700; color: #64748B; text-transform: uppercase; }}
        .kpi-val {{ font-size: 11.5pt; font-weight: 800; color: #0F172A; margin: 2px 0; }}
        .kpi-sub {{ font-size: 6.5pt; font-weight: 700; }}
        
        .meta-card {{
          background: #F8FAFC; border: 1px solid #CBD5E1; border-radius: 6px; padding: 8px 12px; margin-bottom: 10px;
          display: grid; grid-template-columns: 1fr 1fr; gap: 6px 20px; font-size: 7.5pt;
        }}
        .meta-item strong {{ color: #0F172A; }}
        
        .section-title {{ font-size: 9pt; font-weight: 800; color: #0F172A; margin-bottom: 5px; }}
        .data-table {{ width: 100%; border-collapse: collapse; font-size: 7.2pt; border: 1px solid #CBD5E1; margin-bottom: 12px; }}
        .data-table th {{ background: #0F172A; color: #FFFFFF; font-weight: 700; padding: 5px 8px; text-align: left; }}
        .data-table td {{ padding: 4px 8px; border-bottom: 1px solid #E2E8F0; }}
        .data-table tbody tr:nth-child(even) {{ background-color: #F8FAFC; }}
        
        .badge {{ display: inline-block; padding: 2px 6px; border-radius: 3px; font-size: 6.5pt; font-weight: 700; }}
        .badge-paid {{ background: #DCFCE7; color: #15803D; border: 1px solid #86EFAC; }}
        .badge-partial {{ background: #FEF3C7; color: #B45309; border: 1px solid #FDE68A; }}
        .badge-pending {{ background: #FEE2E2; color: #B91C1C; border: 1px solid #FECACA; }}
        
        .num {{ text-align: right; font-variant-numeric: tabular-nums; }}
        .font-green {{ color: #065F46; }}
        .font-red {{ color: #991B1B; }}
        .bold {{ font-weight: 700; }}
        .text-center {{ text-align: center; }}
        
        .sig-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-top: 10px; }}
        .sig-card {{ background: #F8FAFC; border: 1px solid #CBD5E1; border-radius: 6px; padding: 8px 12px; text-align: center; }}
        .sig-title {{ font-size: 7.2pt; font-weight: 700; color: #0F172A; margin-bottom: 2px; }}
        .sig-dept {{ font-size: 6.8pt; color: #64748B; margin-bottom: 16px; }}
        .sig-line {{ border-top: 1px solid #94A3B8; padding-top: 3px; font-size: 6.5pt; color: #64748B; }}
        .footer-note {{ text-align: center; font-size: 6.5pt; color: #94A3B8; margin-top: 8px; }}
      </style>
    </head>
    <body>
      <div class="header-banner">
        <div class="header-left">
          <div class="comp-title">🏢 {company_name}</div>
          <div class="comp-ar">{ar_name}</div>
          <div class="comp-meta">Commercial Reg: {cr_num} • VAT: 300492819200003 • {address}</div>
        </div>
        <div class="header-right">
          <div class="doc-badge">VENDOR STATEMENT OF ACCOUNT</div>
          <div class="doc-ar">كشف حساب المورد وسند الصرف الرسمي</div>
          <div class="doc-meta">Generated: {gen_time}</div>
        </div>
      </div>
      
      <div class="kpi-grid">
        <div class="kpi-card blue">
          <div class="kpi-label">TOTAL BILLED INVOICE</div>
          <div class="kpi-val">SAR {total_amt:,.2f}</div>
          <div class="kpi-sub" style="color: #1E40AF;">Verified Liability</div>
        </div>
        <div class="kpi-card green">
          <div class="kpi-label">TOTAL DISBURSED (PAID)</div>
          <div class="kpi-val" style="color: #065F46;">SAR {paid_amt:,.2f}</div>
          <div class="kpi-sub" style="color: #065F46;">● {settled_pct}% Settled</div>
        </div>
        <div class="kpi-card {'red' if rem_amt > 0 else 'green'}">
          <div class="kpi-label">NET BALANCE OUTSTANDING</div>
          <div class="kpi-val" style="color: {'#991B1B' if rem_amt > 0 else '#065F46'};">SAR {rem_amt:,.2f}</div>
          <div class="kpi-sub" style="color: {'#991B1B' if rem_amt > 0 else '#065F46'};">{'● Net Due Now' if rem_amt > 0 else '● Fully Disbursed'}</div>
        </div>
        <div class="kpi-card gold">
          <div class="kpi-label">INVOICE STATUS</div>
          <div style="margin: 4px 0;"><span class="badge {badge_class}">{st_text.upper()}</span></div>
          <div class="kpi-sub" style="color: #475569;">Official Record</div>
        </div>
      </div>
      
      <div class="meta-card">
        <div class="meta-item"><strong>Vendor Company:</strong> {sp.get("company_name", "")}</div>
        <div class="meta-item"><strong>Invoice Number:</strong> {sp.get("invoice_number", "N/A")}</div>
        <div class="meta-item"><strong>Invoice Issue Date:</strong> {inv_date_str}</div>
        <div class="meta-item"><strong>Payment Due Date:</strong> {due_date_str}</div>
        <div class="meta-item"><strong>Supply Period:</strong> {supply_period_str}</div>
        <div class="meta-item"><strong>ERP Record Ref:</strong> #INV-{sp.get('id', '')}</div>
        <div class="meta-item"><strong>Service / Scope:</strong> {sp.get("invoice_details", "N/A")}</div>
        <div class="meta-item"><strong>Financial Remarks:</strong> {sp.get("remarks", "N/A")}</div>
      </div>
      
      <div class="section-title">DISBURSAL TRANSACTIONS & SETTLEMENT LOGS</div>
      <table class="data-table">
        <thead>
          <tr>
            <th>SETTLEMENT DATE</th>
            <th>PAYMENT METHOD</th>
            <th>TRANSACTION REF #</th>
            <th>SETTLEMENT DETAILS / NOTES</th>
            <th class="num">AMOUNT DISBURSED</th>
          </tr>
        </thead>
        <tbody>
          {logs_rows_html}
        </tbody>
      </table>
      
      <div class="sig-grid">
        <div class="sig-card">
          <div class="sig-title">ACCOUNTS PAYABLE CONTROLLER</div>
          <div class="sig-dept">Finance & Treasury Department</div>
          <div class="sig-line">Authorized Signature & Company Stamp</div>
        </div>
        <div class="sig-card">
          <div class="sig-title">VENDOR AUTHORIZED REPRESENTATIVE</div>
          <div class="sig-dept">Vendor Commercial Receiver</div>
          <div class="sig-line">Signature & Official Stamp</div>
        </div>
      </div>
      
      <div class="footer-note">
        Page 1 of 1 | Strictly Confidential • Official Accounts Payable Statement under Saudi Commercial Law
      </div>
    </body>
    </html>
    """
    return html_to_pdf_playwright(html)


# =========================================================================
# 3. EXECUTIVE INDUSTRIAL WORKER PAYSLIP VOUCHER (ADK EXACT TEMPLATE)
# =========================================================================
def generate_payslip_pdf(employee_data: dict, payroll_detail: dict, company_info: dict) -> bytes:
    """
    Generates the exact ADK Industrial Worker Payslip Voucher PDF matching the company's
    standard rate breakdown, regular/OT hours, rest day/holiday pay, meal allowances,
    WPS/utility deductions, cash advances, and Actual Pay highlights.
    """
    company_name = company_info.get("company_name", "ADK Co., LTD.")
    ar_name = company_info.get("company_arabic_name", "شركة إيه دي كيه للخدمات الصناعية المحدودة")
    cr_num = company_info.get("cr_number", "2055001234")
    address = company_info.get("address", "2837, B13, Tebah District, Al Jubail, Kingdom of Saudi Arabia")
    
    pay_period_str = format_pay_period(payroll_detail.get('month', ''), payroll_detail.get('year', ''))
    cutoff_str = payroll_detail.get("cutoff_period") or f"{pay_period_str}"
    
    emp_name = f"{employee_data.get('first_name', '')} {employee_data.get('last_name', '')}".strip().upper()
    designation = str(employee_data.get("designation") or "TECHNICIAN / OPERATOR").upper()
    
    # Days & Rates calculation
    days_worked = float(payroll_detail.get("days_worked") or 30.0)
    basic = float(payroll_detail.get("basic_salary") or 0.0)
    
    daily_rate = float(payroll_detail.get("daily_rate") or (basic / 30.0 if basic > 0 else 83.33333333))
    hourly_rate = float(payroll_detail.get("hourly_rate") or (daily_rate / 8.0 if daily_rate > 0 else 10.42))
    ot_rate = float(payroll_detail.get("ot_rate") or round(hourly_rate * 1.5, 2))
    
    # Hours & Base Earnings
    working_hours = float(payroll_detail.get("working_hours") if payroll_detail.get("working_hours") is not None else (days_worked * 8.0 if days_worked > 0 else 64.0))
    regular_pay = float(payroll_detail.get("regular_pay") if payroll_detail.get("regular_pay") is not None else round(working_hours * hourly_rate, 2))
    
    ot_hours = float(payroll_detail.get("ot_hours") or 0.0)
    ot_pay = float(payroll_detail.get("ot_pay") or round(ot_hours * ot_rate, 2))
    
    subtotal_hours = working_hours + ot_hours
    subtotal_pay = float(payroll_detail.get("subtotal_pay") or round(regular_pay + ot_pay, 2))
    
    # Rest Day, Holiday, Meal Allowance, Adjustments
    rest_day_hours = float(payroll_detail.get("rest_day_hours") or 0.0)
    rest_day_rate = float(payroll_detail.get("rest_day_rate") or hourly_rate)
    rest_day_pay = float(payroll_detail.get("rest_day_pay") or round(rest_day_hours * rest_day_rate, 2))
    
    holiday_hours = float(payroll_detail.get("holiday_hours") or 0.0)
    holiday_rate = float(payroll_detail.get("holiday_rate") or hourly_rate)
    holiday_pay = float(payroll_detail.get("holiday_pay") or round(holiday_hours * holiday_rate, 2))
    
    meal_allowance_qty = float(payroll_detail.get("meal_allowance_qty") or 0.0)
    meal_allowance_rate = float(payroll_detail.get("meal_allowance_rate") or (10.0 if meal_allowance_qty > 0 else 0.0))
    meal_allowance_pay = float(payroll_detail.get("meal_allowance_pay") or float(payroll_detail.get("housing_allowance") or 0.0) or round(meal_allowance_qty * meal_allowance_rate, 2))
    
    adjustment_add = float(payroll_detail.get("adjustment_add") or float(payroll_detail.get("other_allowances") or 0.0))
    
    total_pay = float(payroll_detail.get("total_pay") or float(payroll_detail.get("gross_salary") or 0.0) or round(subtotal_pay + rest_day_pay + holiday_pay + meal_allowance_pay + adjustment_add, 2))
    
    # Deductions
    wps_deduction = float(payroll_detail.get("wps_deduction") or 0.0)
    water_bill = float(payroll_detail.get("water_bill") or 0.0)
    gosi_emp = float(payroll_detail.get("gosi_employee") or 0.0)
    other_ded = float(payroll_detail.get("other_deductions") or 0.0)
    
    total_deductions = float(payroll_detail.get("total_deductions") or round(wps_deduction + water_bill + gosi_emp + other_ded, 2))
    net_pay = float(payroll_detail.get("net_salary") or float(payroll_detail.get("net_pay") or 0.0) or round(total_pay - total_deductions, 2))
    
    # Cash Advance & Actual Pay
    cash_advance = float(payroll_detail.get("cash_advance") or 0.0)
    adjustment_sub = float(payroll_detail.get("adjustment_sub") or 0.0)
    actual_pay = float(payroll_detail.get("actual_pay") or round(net_pay - cash_advance - adjustment_sub, 2))
    
    gen_time = format_long_datetime()
    
    def fmt_num(val, show_zero_as_dash=False, decimals=2):
        if val is None:
            return "-"
        try:
            v = float(val)
            if v == 0.0 and show_zero_as_dash:
                return "-"
            if decimals == 8:
                return f"{v:.8f}".rstrip('0').rstrip('.') if '.' in f"{v:.8f}" else f"{v:.2f}"
            return f"{v:,.2f}"
        except Exception:
            return str(val)

    html = f"""<!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <title>Payslip Voucher - {emp_name}</title>
      <style>
        @page {{ size: letter portrait; margin: 0; }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif; }}
        body {{ background-color: #FFFFFF; color: #000000; padding: 24px 28px; font-size: 8.5pt; line-height: 1.3; }}
        
        .company-header {{
          display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; border-bottom: 2px solid #0A1128; padding-bottom: 6px;
        }}
        .company-title {{ font-size: 13pt; font-weight: 900; color: #0A1128; }}
        .company-sub {{ font-size: 7.5pt; color: #475569; }}
        .doc-title-badge {{ font-size: 11pt; font-weight: 800; color: #0047AB; text-align: right; }}
        .doc-title-sub {{ font-size: 7.5pt; color: #64748B; text-align: right; }}
        
        /* Master Payslip Grid matching template image */
        .payslip-table {{
          width: 100%; border-collapse: collapse; border: 2.5px solid #000000; font-size: 8.5pt;
        }}
        .payslip-table th, .payslip-table td {{
          border: 1.5px solid #000000; padding: 5px 8px; vertical-align: middle;
        }}
        
        .worker-name-box {{
          font-size: 11.5pt; font-weight: 900; text-align: center; color: #000000; letter-spacing: 0.5px;
        }}
        .hdr-label {{
          font-weight: 900; font-size: 8.5pt; width: 140px; text-align: right; padding-right: 10px;
        }}
        .hdr-val {{
          font-weight: 800; font-size: 8.5pt; text-align: center;
        }}
        .col-head-title {{
          font-weight: 900; text-align: center; font-size: 8pt; line-height: 1.15;
        }}
        
        .bold {{ font-weight: 800; }}
        .bolder {{ font-weight: 900; }}
        .num {{ text-align: right; font-variant-numeric: tabular-nums; font-weight: 700; }}
        .text-center {{ text-align: center; }}
        
        /* Highlights matching user template */
        .row-subtotal td {{ background-color: #FFFFFF; font-weight: 900; }}
        .row-total-pay td {{ background-color: #FFFFFF; font-weight: 900; font-size: 9pt; }}
        
        .row-net-pay td {{
          background-color: #DDE5F4 !important; font-weight: 900; font-size: 9.5pt;
        }}
        .row-actual-pay td {{
          background-color: #FFF066 !important; font-weight: 900; font-size: 10.5pt; border-top: 2px solid #000000;
        }}
        
        .sig-block {{
          display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 14px;
        }}
        .sig-box {{
          border: 1px solid #000000; padding: 8px 12px; text-align: center; border-radius: 3px;
        }}
        .sig-title {{ font-size: 7.5pt; font-weight: 800; margin-bottom: 2px; }}
        .sig-line {{ border-top: 1px solid #000000; margin-top: 22px; padding-top: 2px; font-size: 6.8pt; color: #475569; }}
        .footer-stamp {{ text-align: center; font-size: 6.5pt; color: #64748B; margin-top: 10px; }}
      </style>
    </head>
    <body>
      
      <div class="company-header">
        <div>
          <div class="company-title">{company_name}</div>
          <div class="company-sub">{ar_name} • CR: {cr_num} • Al Jubail, KSA</div>
        </div>
        <div>
          <div class="doc-title-badge">INDIVIDUAL SALARY PAYSLIP</div>
          <div class="doc-title-sub">Official SAMA WPS Labor Voucher • {pay_period_str}</div>
        </div>
      </div>

      <table class="payslip-table">
        <!-- TOP HEADER METADATA -->
        <tr>
          <td colspan="2" rowspan="3" style="width: 50%; vertical-align: middle; text-align: center; padding: 10px;">
            <div class="worker-name-box">{emp_name}</div>
          </td>
          <td class="hdr-label">DESIGNATION:</td>
          <td class="hdr-val">{designation}</td>
        </tr>
        <tr>
          <td class="hdr-label">CUTOFF:</td>
          <td class="hdr-val">{cutoff_str}</td>
        </tr>
        <tr>
          <td class="hdr-label">DAYS:</td>
          <td class="hdr-val">{days_worked:,.2f}</td>
        </tr>

        <!-- COLUMN HEADERS -->
        <tr>
          <td class="bold" style="width: 32%;">DAILY RATE</td>
          <td class="num" style="width: 20%;">{fmt_num(daily_rate, decimals=8)}</td>
          <td class="col-head-title" style="width: 24%;">TOTAL<br>WORKING<br>HOURS</td>
          <td class="col-head-title" style="width: 24%;">HALF<br>MONTH<br>PAY</td>
        </tr>

        <!-- HOURLY RATE -->
        <tr>
          <td class="bold">HOURLY RATE</td>
          <td class="num">{fmt_num(hourly_rate)}</td>
          <td class="num">{fmt_num(working_hours)}</td>
          <td class="num bold">{fmt_num(regular_pay)}</td>
        </tr>

        <!-- O.T -->
        <tr>
          <td class="bold">O.T</td>
          <td class="num">{fmt_num(ot_rate)}</td>
          <td class="num">{fmt_num(ot_hours, show_zero_as_dash=True)}</td>
          <td class="num bold">{fmt_num(ot_pay, show_zero_as_dash=True)}</td>
        </tr>

        <!-- SUB TOTAL -->
        <tr class="row-subtotal">
          <td colspan="2" class="text-center bolder">SUB TOTAL</td>
          <td class="num bolder">{fmt_num(subtotal_hours)}</td>
          <td class="num bolder">{fmt_num(subtotal_pay)}</td>
        </tr>

        <!-- FRIDAY/REST DAY -->
        <tr>
          <td class="bold">FRIDAY/REST DAY</td>
          <td class="num">{fmt_num(rest_day_rate)}</td>
          <td class="num">{fmt_num(rest_day_hours, show_zero_as_dash=True)}</td>
          <td class="num bold">{fmt_num(rest_day_pay, show_zero_as_dash=True)}</td>
        </tr>

        <!-- HOLIDAY -->
        <tr>
          <td class="bold">HOLIDAY</td>
          <td class="num">{fmt_num(holiday_rate)}</td>
          <td class="num">{fmt_num(holiday_hours, show_zero_as_dash=True)}</td>
          <td class="num bold">{fmt_num(holiday_pay, show_zero_as_dash=True)}</td>
        </tr>

        <!-- MEAL ALLOWANCE -->
        <tr>
          <td class="bold">MEAL ALLOWANCE</td>
          <td class="num">{fmt_num(meal_allowance_rate, show_zero_as_dash=True)}</td>
          <td class="num">{fmt_num(meal_allowance_qty, show_zero_as_dash=True)}</td>
          <td class="num bold">{fmt_num(meal_allowance_pay, show_zero_as_dash=True)}</td>
        </tr>

        <!-- ADJUSTMENT (ADDITION) -->
        <tr>
          <td class="bold">ADJUSTMENT</td>
          <td class="num"></td>
          <td class="num"></td>
          <td class="num bold">{fmt_num(adjustment_add, show_zero_as_dash=True)}</td>
        </tr>

        <!-- TOTAL PAY (GROSS) -->
        <tr class="row-total-pay">
          <td colspan="3" class="text-center bolder">TOTAL PAY</td>
          <td class="num bolder">{fmt_num(total_pay)}</td>
        </tr>

        <!-- DEDUCTIONS -->
        <tr>
          <td rowspan="2" class="bold text-center" style="vertical-align: middle;">DEDUCTION</td>
          <td colspan="2" class="bold">WPS</td>
          <td class="num bold">{fmt_num(wps_deduction, show_zero_as_dash=True)}</td>
        </tr>
        <tr>
          <td colspan="2" class="bold">WATER BILL</td>
          <td class="num bold">{fmt_num(water_bill, show_zero_as_dash=True)}</td>
        </tr>

        <!-- TOTAL DEDUCTION -->
        <tr class="row-subtotal">
          <td colspan="3" class="text-center bolder">TOTAL DEDUCTION</td>
          <td class="num bolder">{fmt_num(total_deductions)}</td>
        </tr>

        <!-- NET PAY -->
        <tr class="row-net-pay">
          <td colspan="3" class="text-center bolder">NET PAY</td>
          <td class="num bolder">{fmt_num(net_pay)}</td>
        </tr>

        <!-- CASH ADVANCE -->
        <tr>
          <td colspan="3" class="bold text-center">CASH ADVANCE</td>
          <td class="num bold">{fmt_num(cash_advance, show_zero_as_dash=True)}</td>
        </tr>

        <!-- ADJUSTMENT (SUBTRACTION) -->
        <tr>
          <td colspan="3" class="bold text-center">ADJUSTMENT</td>
          <td class="num bold">{fmt_num(adjustment_sub, show_zero_as_dash=True)}</td>
        </tr>

        <!-- ACTUAL PAY -->
        <tr class="row-actual-pay">
          <td colspan="3" class="text-center bolder">ACTUAL PAY</td>
          <td class="num bolder">SAR {fmt_num(actual_pay)}</td>
        </tr>
      </table>

      <!-- SIGNATURES BLOCK -->
      <div class="sig-block">
        <div class="sig-box">
          <div class="sig-title">EMPLOYEE ACKNOWLEDGEMENT & RECEIPT</div>
          <div class="sig-line">Employee Signature & Date</div>
        </div>
        <div class="sig-box">
          <div class="sig-title">AUTHORIZED BY: PAYROLL & HR CONTROLLER</div>
          <div class="sig-line">ADK Finance & HR Operations Stamp</div>
        </div>
      </div>

      <div class="footer-stamp">
        Certified Official Payslip Voucher under Saudi Labor Law & SAMA WPS • Generated on {gen_time}
      </div>

    </body>
    </html>
    """
    return html_to_pdf_playwright(html)


# =========================================================================
# 4. EXECUTIVE MONTHLY PAYROLL & WORKER SALARY SCHEDULE PDF
# =========================================================================
def generate_monthly_payroll_schedule_pdf(
    month: int,
    year: int,
    workers: List[Dict[str, Any]],
    company_info: Dict[str, Any]
) -> bytes:
    """
    Generates an executive-grade Monthly Payroll & Worker Salary Schedule PDF
    using Playwright with ADK Co., LTD. corporate branding, summary KPI cards,
    individual worker salary breakdowns, GOSI contributions, net payouts, and authorization blocks.
    """
    company_name = company_info.get("company_name", "ADK Co., LTD.")
    ar_name = company_info.get("company_arabic_name", "شركة إيه دي كيه للخدمات الصناعية المحدودة")
    cr_num = company_info.get("cr_number", "2055001234")
    address = company_info.get("address", "2837, B13, Tebah District, Al Jubail, Kingdom of Saudi Arabia")
    
    pay_period_str = format_pay_period(month, year)
    gen_time = format_long_datetime()
    
    tot_basic = sum(float(w.get("basic_salary", 0)) for w in workers)
    tot_housing = sum(float(w.get("housing_allowance", 0)) for w in workers)
    tot_transport = sum(float(w.get("transport_allowance", 0)) for w in workers)
    tot_other_allow = sum(float(w.get("other_allowances", 0)) for w in workers)
    tot_gross = sum(float(w.get("gross_salary", 0)) for w in workers)
    tot_gosi = sum(float(w.get("gosi_employee", 0)) for w in workers)
    tot_other_ded = sum(float(w.get("other_deductions", 0)) for w in workers)
    tot_net = sum(float(w.get("net_salary", 0)) for w in workers)
    
    worker_rows_html = ""
    if not workers:
        worker_rows_html = '<tr><td colspan="10" class="text-center" style="padding: 14px;">No workers registered on payroll for this month.</td></tr>'
    else:
        for idx, w in enumerate(workers, 1):
            emp_code = w.get("emp_code", f"EMP-{w.get('id', idx)}")
            emp_name = f"{w.get('first_name', '')} {w.get('last_name', '')}".strip()
            is_saudi = w.get("is_saudi") == 1
            nat_badge = '<span class="badge badge-saudi">SAUDI</span>' if is_saudi else '<span class="badge badge-expat">EXPAT</span>'
            dept_name = w.get("department_name", "Operations")
            
            b = float(w.get("basic_salary", 0))
            h = float(w.get("housing_allowance", 0))
            t_o = float(w.get("transport_allowance", 0)) + float(w.get("other_allowances", 0))
            gr = float(w.get("gross_salary", b + h + t_o))
            gosi = float(w.get("gosi_employee", 0))
            o_ded = float(w.get("other_deductions", 0))
            net = float(w.get("net_salary", gr - gosi - o_ded))
            
            worker_rows_html += f"""
            <tr>
              <td><strong>{emp_code}</strong></td>
              <td><strong>{emp_name}</strong> {nat_badge}</td>
              <td>{dept_name}</td>
              <td class="num">{b:,.2f}</td>
              <td class="num">{h:,.2f}</td>
              <td class="num">{t_o:,.2f}</td>
              <td class="num font-blue bold">{gr:,.2f}</td>
              <td class="num font-red">{gosi:,.2f}</td>
              <td class="num">{o_ded:,.2f}</td>
              <td class="num font-green bold">SAR {net:,.2f}</td>
            </tr>
            """
            
    html = f"""<!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <title>Monthly Payroll Schedule - {pay_period_str}</title>
      <style>
        @page {{ size: letter landscape; margin: 0; }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif; }}
        body {{ background-color: #FFFFFF; color: #0F172A; padding: 14px 18px; font-size: 7.5pt; line-height: 1.3; }}
        .header-banner {{
          background: linear-gradient(135deg, #0A1128 0%, #0047AB 100%);
          color: #FFFFFF; padding: 10px 14px; border-radius: 6px; display: flex; justify-content: space-between; align-items: center; border-bottom: 3px solid #D97706;
        }}
        .header-left .comp-title {{ font-size: 12pt; font-weight: 800; }}
        .header-left .comp-ar {{ font-size: 8pt; color: #BFDBFE; margin-top: 1px; }}
        .header-left .comp-meta {{ font-size: 6.8pt; color: #94A3B8; margin-top: 2px; }}
        .header-right {{ text-align: right; }}
        .header-right .doc-badge {{ font-size: 11pt; font-weight: 800; color: #FEF3C7; }}
        .header-right .doc-ar {{ font-size: 7.5pt; color: #FDE68A; }}
        .header-right .doc-meta {{ font-size: 6.8pt; color: #BFDBFE; margin-top: 2px; }}
        
        .kpi-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; margin: 8px 0; }}
        .kpi-card {{ padding: 6px 10px; border-radius: 5px; border: 1px solid #CBD5E1; text-align: center; }}
        .kpi-card.blue {{ background: #EFF6FF; border-color: #BFDBFE; }}
        .kpi-card.green {{ background: #ECFDF5; border-color: #A7F3D0; }}
        .kpi-card.red {{ background: #FEF2F2; border-color: #FECACA; }}
        .kpi-card.gold {{ background: #FEF3C7; border-color: #FDE68A; }}
        .kpi-label {{ font-size: 6pt; font-weight: 700; color: #64748B; text-transform: uppercase; }}
        .kpi-val {{ font-size: 11pt; font-weight: 800; color: #0F172A; margin: 1px 0; }}
        .kpi-sub {{ font-size: 6pt; font-weight: 700; }}
        
        .data-table {{ width: 100%; border-collapse: collapse; font-size: 7pt; border: 1px solid #CBD5E1; margin-bottom: 8px; }}
        .data-table th {{ background: #0A1128; color: #FFFFFF; font-weight: 700; padding: 4px 6px; text-align: left; font-size: 6.5pt; }}
        .data-table td {{ padding: 3px 6px; border-bottom: 1px solid #E2E8F0; }}
        .data-table tbody tr:nth-child(even) {{ background-color: #F8FAFC; }}
        .data-table tfoot td {{ background-color: #E2E8F0; font-weight: 700; color: #0F172A; border-top: 1.5px solid #64748B; }}
        
        .badge {{ display: inline-block; padding: 1px 4px; border-radius: 2px; font-size: 5.5pt; font-weight: 700; }}
        .badge-saudi {{ background: #DCFCE7; color: #15803D; border: 1px solid #86EFAC; }}
        .badge-expat {{ background: #E0F2FE; color: #0369A1; border: 1px solid #BAE6FD; }}
        
        .num {{ text-align: right; font-variant-numeric: tabular-nums; }}
        .font-blue {{ color: #0047AB; }}
        .font-green {{ color: #065F46; }}
        .font-red {{ color: #991B1B; }}
        .bold {{ font-weight: 700; }}
        .text-center {{ text-align: center; }}
        
        .sig-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-top: 6px; }}
        .sig-card {{ background: #F8FAFC; border: 1px solid #CBD5E1; border-radius: 5px; padding: 6px 10px; text-align: center; }}
        .sig-title {{ font-size: 6.8pt; font-weight: 700; color: #0F172A; margin-bottom: 1px; }}
        .sig-dept {{ font-size: 6.2pt; color: #64748B; margin-bottom: 12px; }}
        .sig-line {{ border-top: 1px solid #94A3B8; padding-top: 2px; font-size: 6pt; color: #64748B; }}
        .footer-note {{ text-align: center; font-size: 6pt; color: #94A3B8; margin-top: 4px; }}
      </style>
    </head>
    <body>
      <div class="header-banner">
        <div class="header-left">
          <div class="comp-title">🏢 {company_name}</div>
          <div class="comp-ar">{ar_name}</div>
          <div class="comp-meta">Commercial Reg: {cr_num} • Al Jubail, Saudi Arabia • www.adknprotech.com</div>
        </div>
        <div class="header-right">
          <div class="doc-badge">MONTHLY PAYROLL ROSTER | {pay_period_str.upper()}</div>
          <div class="doc-ar">جدول مسير الرواتب الشهري المعتمد</div>
          <div class="doc-meta">Generated: {gen_time} • Confidential</div>
        </div>
      </div>
      
      <div class="kpi-grid">
        <div class="kpi-card blue">
          <div class="kpi-label">TOTAL WORKERS ON PAYROLL</div>
          <div class="kpi-val">{len(workers)} Active Staff</div>
          <div class="kpi-sub" style="color: #0047AB;">● SAMA WPS Standard</div>
        </div>
        <div class="kpi-card blue">
          <div class="kpi-label">TOTAL GROSS PAYABLE</div>
          <div class="kpi-val" style="color: #0047AB;">SAR {tot_gross:,.2f}</div>
          <div class="kpi-sub" style="color: #0047AB;">Basic + All Allowances</div>
        </div>
        <div class="kpi-card red">
          <div class="kpi-label">STATUTORY GOSI DEDUCTIONS</div>
          <div class="kpi-val" style="color: #991B1B;">SAR {tot_gosi:,.2f}</div>
          <div class="kpi-sub" style="color: #991B1B;">Social Insurance Share</div>
        </div>
        <div class="kpi-card green">
          <div class="kpi-label">NET SALARY OUTFLOW</div>
          <div class="kpi-val" style="color: #065F46;">SAR {tot_net:,.2f}</div>
          <div class="kpi-sub" style="color: #065F46;">● Disbursable Net Pay</div>
        </div>
      </div>
      
      <table class="data-table">
        <thead>
          <tr>
            <th>EMP CODE</th>
            <th>WORKER / EMPLOYEE NAME</th>
            <th>DEPARTMENT</th>
            <th class="num">BASIC (SAR)</th>
            <th class="num">HOUSING (SAR)</th>
            <th class="num">OTHER ALLOW.</th>
            <th class="num">GROSS (SAR)</th>
            <th class="num">GOSI (SAR)</th>
            <th class="num">OTHER DED.</th>
            <th class="num">NET SALARY (SAR)</th>
          </tr>
        </thead>
        <tbody>
          {worker_rows_html}
        </tbody>
        <tfoot>
          <tr>
            <td colspan="3"><strong>CONSOLIDATED ROSTER TOTALS ({len(workers)} WORKERS):</strong></td>
            <td class="num"><strong>SAR {tot_basic:,.2f}</strong></td>
            <td class="num"><strong>SAR {tot_housing:,.2f}</strong></td>
            <td class="num"><strong>SAR {tot_transport + tot_other_allow:,.2f}</strong></td>
            <td class="num font-blue bold"><strong>SAR {tot_gross:,.2f}</strong></td>
            <td class="num font-red bold"><strong>SAR {tot_gosi:,.2f}</strong></td>
            <td class="num"><strong>SAR {tot_other_ded:,.2f}</strong></td>
            <td class="num font-green bold"><strong>SAR {tot_net:,.2f}</strong></td>
          </tr>
        </tfoot>
      </table>
      
      <div class="sig-grid">
        <div class="sig-card">
          <div class="sig-title">PREPARED BY: PAYROLL & HR OPERATIONS MANAGER</div>
          <div class="sig-dept">ADK Human Resources & Payroll Division</div>
          <div class="sig-line">Signature & Audit Verification</div>
        </div>
        <div class="sig-card">
          <div class="sig-title">APPROVED BY: CHIEF FINANCIAL OFFICER (CFO) / MANAGING DIRECTOR</div>
          <div class="sig-dept">ADK Executive Financial Leadership</div>
          <div class="sig-line">Authorized Signature & Corporate Stamp</div>
        </div>
      </div>
      
      <div class="footer-note">
        Page 1 of 1 | Strictly Confidential • ADK Co., LTD. Official Payroll Document under Saudi Labor Law & SAMA WPS
      </div>
    </body>
    </html>
    """
    return html_to_pdf_playwright(html, landscape=True)

