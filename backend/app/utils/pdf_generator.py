import io
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

def generate_boe_pdf(slip_data: dict) -> io.BytesIO:
    """Generates a Bill of Entry PDF mimicking the dot-matrix style."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=20, leftMargin=20, topMargin=20, bottomMargin=20)
    
    styles = getSampleStyleSheet()
    
    # Custom Courier Style for the entire document
    mono_style = ParagraphStyle(
        name='Mono',
        fontName='Courier',
        fontSize=8,
        leading=10,
        alignment=0
    )
    
    mono_center = ParagraphStyle(
        name='MonoCenter',
        fontName='Courier-Bold',
        fontSize=10,
        leading=12,
        alignment=1
    )
    
    elements = []
    
    # Header
    elements.append(Paragraph("KARGO LEAGUE LOGISTICS PVT LTD", mono_center))
    elements.append(Paragraph("Printed through Focus Server Edition Version 8.0.0.26 on 18/06/2026 11:49:50", mono_center))
    elements.append(Paragraph("SAHAR AIR CARGO (Air Cargo)", mono_center))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph("BILL OF ENTRY FOR HOME CONSUMPTION - CHECKLIST", mono_center))
    elements.append(Paragraph(f"[Custom Stn :INBOM4]         CHA :AAECK8850HCH002 [KARGO LEAGUE LOGISTICS PVT LTD]", mono_style))
    elements.append(Paragraph(f"BE No./Dt./CC/Type/DktRefNo/Dt./JobNo ://N/H///Job No:{slip_data.get('processing_id', '489')[:4]} Date:{slip_data.get('clearance_date', '18-06-2026')}", mono_style))
    elements.append(Spacer(1, 10))
    
    ext_data = slip_data.get("extracted_data", {})
    pol = ext_data.get("port_of_loading", "N/A")
    gross_wt = ext_data.get("gross_weight", "N/A")
    supplier = ext_data.get("supplier", "N/A")
    
    # Body
    text_lines = [
        "-------------------------------------------------------------------------------------------------------------------",
        f"Importer Details :0388070412(AAACM8029J)       Formatted Job:I/A/000489/26-27",
        "MAZAGON DOCK SHIPBUILDERS LIMITED",
        "0          :DOCKYARD ROAD, MUMBAI",
        "MUMBAI-400010",
        "AD Code :0006070",
        "",
        f"IGM No           :                           Port of Loading  :   {pol}",
        f"Inward date      :                           Port of Origin   :   {pol}",
        "Cntry of Orgn.   :       GERMANY             Cntry of Consign :   GERMANY",
        f"BL/AWB No        :       02023590512         H.BL/AWB No      :   MEN60149666",
        f"Date             :       17-06-2026          Date             :   17-06-2026",
        f"No. of Pkgs.     :       1.000PKG            Gross Wt.        :   {gross_wt}",
        f"Status           :       {slip_data.get('status', 'APPROVED')}",
        "-------------------------------------------------------------------------------------------------------------------",
        "Kachcha BE       :       N                   Green channel    :   Y",
        "High Sea Sale    :       N                   Section 48       :   N",
        "Prior BE         :       Y                   First Check      :   N",
        "UCR No           :                           UCR Type         :",
        "Payment Method   :       T - Transaction",
        "",
        f"Invoice Sl. No   :       1                   Supplier Details :",
        f"Inv No & Dt      :       67308    17-06-2026                 {supplier}",
        "Inv Val          :       18.9 EUR  TOI:CIF",
        "Freight          :       0      0.000%                       WERFTSTRASSE 112-114",
        "Insurance        :       0      0.00000%                     24143 KIEL",
        "Commission       :       0      0.000%                       GERMANY",
        "",
        "SlNo RITC        Description                            RSP              Load PROV",
        "Qty  End Use     Unit Price       CTH        C.Notn C.NSNO           Cus Duty",
        "Unit Country     Ass Val          CETH       E.Notn E.NSNO           Exc Duty",
        "-------------------------------------------------------------------------------------------------------------------",
        "1    74072910    ROUND BARS 65 140P 2.1504 CUNI14AL3",
        "0.14 GNX200      135.000000       74072910   045/2025/I351@ 0        0%",
        "MTR  DE          2135.700",
        "-------------------------------------------------------------------------------------------------------------------",
        "Duty Payable :                                                                                 Rs.106.80",
        "Rupees one hundred six and paise eighty Only",
        "",
        "DECLARATION",
        "1. I/We Certify that the above entries are correct.",
        "2. I/We further declare that wherever the RSP is applicable same has been truthfully declared.",
        "-------------------------------------------------------------------------------------------------------------------",
        "                                                                                    Signature of CHA"
    ]
    
    for line in text_lines:
        elements.append(Paragraph(line.replace(" ", "&nbsp;"), mono_style))
        
    doc.build(elements)
    buffer.seek(0)
    return buffer

def generate_checklist_pdf(slip_data: dict) -> io.BytesIO:
    """Generates a Vessel Customs Clearance Checklist PDF."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        name='TitleStyle',
        fontName='Helvetica-Bold',
        fontSize=16,
        textColor=colors.HexColor('#1b3a5b'),
        spaceAfter=5
    )
    subtitle_style = ParagraphStyle(
        name='SubTitleStyle',
        fontName='Helvetica',
        fontSize=10,
        textColor=colors.dimgrey,
        spaceAfter=20
    )
    
    elements = []
    
    # Header
    elements.append(Paragraph("CUSTOMS BOARDING & CLEARANCE CHECKLIST", title_style))
    elements.append(Paragraph("Standard Operating Procedure for Vessel Inspection & Entry Inward Facilitation", subtitle_style))
    
    ext_data = slip_data.get("extracted_data", {})
    vessel = ext_data.get("vessel_name", "N/A")
    pol = ext_data.get("port_of_loading", "N/A")
    
    # Top Info Table
    info_data = [
        ["Vessel Name", vessel, "IMO / Registry No.", "9811000"],
        ["Nationality / Flag", "PANAMA", "Voyage Number", "048E"],
        ["Port of Berth / Anchor", pol, "Last Port of Call", "COLOMBO"],
        ["Date & Time of Arrival", slip_data.get("clearance_date", "18/06/2026"), "Boarding Officer Name", "AI AGENT SYSTEM"]
    ]
    
    t_info = Table(info_data, colWidths=[120, 150, 120, 140])
    t_info.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (0,-1), colors.HexColor('#f0f5fa')),
        ('BACKGROUND', (2,0), (2,-1), colors.HexColor('#f0f5fa')),
        ('TEXTCOLOR', (0,0), (-1,-1), colors.HexColor('#1b3a5b')),
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
        ('FONTNAME', (2,0), (2,-1), 'Helvetica-Bold'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#d3dce6')),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('TOPPADDING', (0,0), (-1,-1), 8),
    ]))
    elements.append(t_info)
    elements.append(Spacer(1, 20))
    
    # Phase 1 Table (Validation)
    elements.append(create_phase_table("PHASE 1: DOCUMENT VALIDATION", [
        ["Manifest Verification", "Verify Sea Arrival Manifest (SAM) or Import\nGeneral Manifest (IGM) data filed.", "PASS" if slip_data.get('validation_status') in ['PASS', 'OVERRIDDEN_PASS'] else "FAIL"],
        ["AI Remarks", slip_data.get('validation_reason', 'Verified'), ""]
    ]))
    elements.append(Spacer(1, 10))
    
    # Phase 2 Table (Compliance)
    elements.append(create_phase_table("PHASE 2: COMPLIANCE & REGULATIONS", [
        ["Statutory Declarations", "Check against local ChromaDB rules engine.", "PASS" if slip_data.get('compliance_status') in ['PASS', 'OVERRIDDEN_PASS'] else "FAIL"],
        ["AI Remarks", slip_data.get('compliance_reason', 'Compliant'), ""]
    ]))
    elements.append(Spacer(1, 10))
    
    # Phase 3 Table (Final)
    final_pass = slip_data.get('status') in ['APPROVED', 'RESUMED']
    elements.append(create_phase_table("PHASE 3: CLEARANCE AUTHORIZATION", [
        ["Discrepancy Evaluation", "Identify and formalize any shortfalls or undeclared\nassets.", "COMPLETED"],
        ["Grant Inward Entry", "Sign off on the physical boarding document to\nofficially authorize the start of shore cargo unloading.", "GRANTED" if final_pass else "DENIED"]
    ]))
    
    # Signatures
    elements.append(Spacer(1, 40))
    sig_data = [
        ["_______________________________", "_______________________________"],
        ["Signature of Ship's Master (Captain)", "Signature of Customs Boarding Officer"],
        ["Name & Official Vessel Stamp", "Name, Designation & Service Badge ID (AI)"]
    ]
    t_sig = Table(sig_data, colWidths=[260, 260])
    t_sig.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('TEXTCOLOR', (0,0), (-1,-1), colors.dimgrey),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('BOTTOMPADDING', (0,0), (-1,0), 5),
    ]))
    elements.append(t_sig)
    
    doc.build(elements)
    buffer.seek(0)
    return buffer

def create_phase_table(title: str, rows: list) -> Table:
    """Helper to build a phase block like in the Checklist PDF."""
    styles = getSampleStyleSheet()
    cell_style = ParagraphStyle('CellStyle', parent=styles['Normal'], fontSize=9, fontName='Helvetica', leading=11)
    
    data = [[title, "", ""]]
    data.append(["INSPECTION PARAMETER", "VERIFICATION & COMPLIANCE NOTES", "STATUS"])
    for row in rows:
        wrapped_notes = Paragraph(str(row[1]).replace('\n', '<br/>'), cell_style)
        data.append([row[0], wrapped_notes, row[2]])
        
    t = Table(data, colWidths=[130, 300, 100])
    t.setStyle(TableStyle([
        # Phase Title row
        ('SPAN', (0,0), (-1,0)),
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1b3a5b')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('ALIGN', (0,0), (-1,0), 'LEFT'),
        ('BOTTOMPADDING', (0,0), (-1,0), 8),
        
        # Headers row
        ('BACKGROUND', (0,1), (-1,1), colors.HexColor('#2c5c8f')),
        ('TEXTCOLOR', (0,1), (-1,1), colors.whitesmoke),
        ('FONTNAME', (0,1), (-1,1), 'Helvetica-Bold'),
        ('FONTSIZE', (0,1), (-1,1), 9),
        ('BOTTOMPADDING', (0,1), (-1,1), 6),
        
        # Content rows
        ('FONTNAME', (0,2), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,2), (-1,-1), 9),
        ('FONTNAME', (0,2), (0,-1), 'Helvetica-Bold'), # Bold parameter names
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('GRID', (0,1), (-1,-1), 0.5, colors.lightgrey),
        ('BOTTOMPADDING', (0,2), (-1,-1), 10),
        ('TOPPADDING', (0,2), (-1,-1), 10),
    ]))
    return t
