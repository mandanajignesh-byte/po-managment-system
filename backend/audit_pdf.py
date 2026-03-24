"""
Audit Log — tracks every state-changing action on POs
PDF Export — generates a proper purchase order PDF
"""

# ══════════════════════════════════════════════════════════════════
# AUDIT LOG
# ══════════════════════════════════════════════════════════════════

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import Session
from datetime import datetime
from models import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id            = Column(Integer, primary_key=True, index=True)
    entity_type   = Column(String(50), nullable=False)   # "PurchaseOrder", "Vendor", etc.
    entity_id     = Column(Integer, nullable=False)
    action        = Column(String(50), nullable=False)   # "CREATED", "STATUS_CHANGED", "DELETED"
    old_value     = Column(Text)                         # JSON snapshot before change
    new_value     = Column(Text)                         # JSON snapshot after change
    performed_by  = Column(String(255), default="system")
    ip_address    = Column(String(45))
    created_at    = Column(DateTime, default=datetime.utcnow)


def write_audit(
    db: Session,
    entity_type: str,
    entity_id: int,
    action: str,
    old_value: str = None,
    new_value: str = None,
    performed_by: str = "system",
    ip_address: str = None,
):
    log = AuditLog(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        old_value=old_value,
        new_value=new_value,
        performed_by=performed_by,
        ip_address=ip_address,
    )
    db.add(log)
    db.commit()
    return log


def get_audit_logs(db: Session, entity_type: str = None, entity_id: int = None, limit: int = 100):
    q = db.query(AuditLog)
    if entity_type:
        q = q.filter(AuditLog.entity_type == entity_type)
    if entity_id:
        q = q.filter(AuditLog.entity_id == entity_id)
    return q.order_by(AuditLog.created_at.desc()).limit(limit).all()


# ══════════════════════════════════════════════════════════════════
# PDF EXPORT
# ══════════════════════════════════════════════════════════════════

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph,
    Spacer, HRFlowable
)
from reportlab.lib.enums import TA_RIGHT, TA_CENTER, TA_LEFT
from io import BytesIO
from datetime import datetime


BRAND_DARK   = colors.HexColor("#0f172a")
BRAND_INDIGO = colors.HexColor("#6366f1")
BRAND_LIGHT  = colors.HexColor("#f1f5f9")
BRAND_MUTED  = colors.HexColor("#64748b")
BRAND_AMBER  = colors.HexColor("#f59e0b")
BRAND_GREEN  = colors.HexColor("#10b981")

STATUS_COLORS = {
    "DRAFT":     colors.HexColor("#94a3b8"),
    "PENDING":   colors.HexColor("#f59e0b"),
    "APPROVED":  colors.HexColor("#10b981"),
    "REJECTED":  colors.HexColor("#ef4444"),
    "DELIVERED": colors.HexColor("#6366f1"),
}


def fmt_inr(amount: float) -> str:
    return f"₹{amount:,.2f}"


def generate_po_pdf(po: dict) -> bytes:
    """
    Generates a professional A4 PDF for a Purchase Order.
    po dict keys: reference_no, status, created_at, vendor (dict),
                  line_items (list), subtotal, tax_amount, total_amount, notes
    Returns raw bytes of the PDF.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=20*mm, rightMargin=20*mm,
        topMargin=15*mm, bottomMargin=20*mm,
    )

    styles = getSampleStyleSheet()
    story = []

    # ── Header band ───────────────────────────────────────────────
    header_data = [[
        Paragraph(
            '<font size="22" color="#ffffff"><b>📦 IV Innovations Pvt Ltd</b></font><br/>'
            '<font size="9" color="#a5b4fc">Kundli, Sonipat, Haryana — erp@ivinnovations.in</font>',
            ParagraphStyle("hdr", fontName="Helvetica", leading=16)
        ),
        Paragraph(
            f'<font size="11" color="#ffffff"><b>PURCHASE ORDER</b></font><br/>'
            f'<font size="9" color="#a5b4fc">{po["reference_no"]}</font>',
            ParagraphStyle("ref", fontName="Helvetica", alignment=TA_RIGHT, leading=16)
        ),
    ]]
    header_table = Table(header_data, colWidths=[120*mm, 50*mm])
    header_table.setStyle(TableStyle([
        ("BACKGROUND",   (0,0), (-1,-1), BRAND_DARK),
        ("TOPPADDING",   (0,0), (-1,-1), 12),
        ("BOTTOMPADDING",(0,0), (-1,-1), 12),
        ("LEFTPADDING",  (0,0), (0,-1),  10),
        ("RIGHTPADDING", (-1,0),(-1,-1), 10),
        ("ROUNDEDCORNERS", [6]),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 6*mm))

    # ── Meta row (status + date) ──────────────────────────────────
    status = po.get("status", "DRAFT")
    status_color = STATUS_COLORS.get(status, BRAND_MUTED)
    created = po.get("created_at", "")
    if hasattr(created, "strftime"):
        created_str = created.strftime("%d %b %Y")
    else:
        try:
            created_str = datetime.fromisoformat(str(created)).strftime("%d %b %Y")
        except Exception:
            created_str = str(created)[:10]

    meta_data = [[
        Paragraph(f'<font size="9" color="#64748b">Status</font><br/>'
                  f'<font size="11" color="{status_color.hexval() if hasattr(status_color,"hexval") else "#6366f1"}"><b>{status}</b></font>',
                  ParagraphStyle("meta", fontName="Helvetica", leading=14)),
        Paragraph(f'<font size="9" color="#64748b">Date Issued</font><br/>'
                  f'<font size="11"><b>{created_str}</b></font>',
                  ParagraphStyle("meta2", fontName="Helvetica", leading=14)),
        Paragraph(f'<font size="9" color="#64748b">Reference</font><br/>'
                  f'<font size="10" color="#6366f1"><b>{po["reference_no"]}</b></font>',
                  ParagraphStyle("meta3", fontName="Helvetica", leading=14)),
    ]]
    meta_table = Table(meta_data, colWidths=[57*mm, 57*mm, 56*mm])
    meta_table.setStyle(TableStyle([
        ("BOX",          (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
        ("INNERGRID",    (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
        ("TOPPADDING",   (0,0), (-1,-1), 8),
        ("BOTTOMPADDING",(0,0), (-1,-1), 8),
        ("LEFTPADDING",  (0,0), (-1,-1), 10),
        ("BACKGROUND",   (0,0), (-1,-1), colors.HexColor("#f8fafc")),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 6*mm))

    # ── Vendor block ──────────────────────────────────────────────
    vendor = po.get("vendor", {})
    story.append(Paragraph(
        '<font size="9" color="#64748b"><b>BILL TO / VENDOR</b></font>',
        ParagraphStyle("section_label", fontName="Helvetica-Bold")
    ))
    story.append(Spacer(1, 2*mm))
    vendor_data = [[
        Paragraph(
            f'<font size="12"><b>{vendor.get("name", "—")}</b></font><br/>'
            f'<font size="9" color="#64748b">{vendor.get("contact", "")}</font><br/>'
            f'<font size="9" color="#64748b">{vendor.get("email", "")}</font>',
            ParagraphStyle("vendor", fontName="Helvetica", leading=16)
        ),
        Paragraph(
            f'<font size="9" color="#64748b">Vendor Rating</font><br/>'
            f'<font size="14" color="#f59e0b"><b>{"★" * int(vendor.get("rating", 3))}</b></font>'
            f'<font size="10" color="#94a3b8"> {vendor.get("rating", "—")}/5</font>',
            ParagraphStyle("vendor_r", fontName="Helvetica", alignment=TA_RIGHT, leading=18)
        ),
    ]]
    vendor_table = Table(vendor_data, colWidths=[120*mm, 50*mm])
    vendor_table.setStyle(TableStyle([
        ("BOX",          (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
        ("TOPPADDING",   (0,0), (-1,-1), 10),
        ("BOTTOMPADDING",(0,0), (-1,-1), 10),
        ("LEFTPADDING",  (0,0), (0,-1),  10),
        ("RIGHTPADDING", (-1,0),(-1,-1), 10),
        ("BACKGROUND",   (0,0), (-1,-1), colors.HexColor("#f8fafc")),
    ]))
    story.append(vendor_table)
    story.append(Spacer(1, 6*mm))

    # ── Line items table ──────────────────────────────────────────
    story.append(Paragraph(
        '<font size="9" color="#64748b"><b>ORDER ITEMS</b></font>',
        ParagraphStyle("section_label2", fontName="Helvetica-Bold")
    ))
    story.append(Spacer(1, 2*mm))

    table_data = [["#", "Product", "SKU", "Qty", "Unit Price", "Line Total"]]
    for i, item in enumerate(po.get("line_items", []), 1):
        product = item.get("product", {})
        table_data.append([
            str(i),
            product.get("name", "—"),
            product.get("sku", "—"),
            str(item.get("quantity", 0)),
            fmt_inr(item.get("unit_price", 0)),
            fmt_inr(item.get("line_total", 0)),
        ])

    items_table = Table(
        table_data,
        colWidths=[10*mm, 60*mm, 30*mm, 15*mm, 27*mm, 28*mm]
    )
    items_table.setStyle(TableStyle([
        # Header row
        ("BACKGROUND",   (0,0), (-1,0),  BRAND_DARK),
        ("TEXTCOLOR",    (0,0), (-1,0),  BRAND_LIGHT),
        ("FONTNAME",     (0,0), (-1,0),  "Helvetica-Bold"),
        ("FONTSIZE",     (0,0), (-1,0),  8),
        ("TOPPADDING",   (0,0), (-1,0),  8),
        ("BOTTOMPADDING",(0,0), (-1,0),  8),
        # Data rows
        ("FONTSIZE",     (0,1), (-1,-1), 9),
        ("ROWBACKGROUNDS",(0,1),(-1,-1), [colors.white, colors.HexColor("#f8fafc")]),
        ("TOPPADDING",   (0,1), (-1,-1), 7),
        ("BOTTOMPADDING",(0,1), (-1,-1), 7),
        # Alignment
        ("ALIGN",        (0,0), (0,-1),  "CENTER"),
        ("ALIGN",        (3,0), (-1,-1), "RIGHT"),
        # Grid
        ("GRID",         (0,0), (-1,-1), 0.4, colors.HexColor("#e2e8f0")),
        # Last col bold
        ("FONTNAME",     (-1,1),(-1,-1), "Helvetica-Bold"),
        ("TEXTCOLOR",    (-1,1),(-1,-1), BRAND_DARK),
        ("LEFTPADDING",  (0,0), (-1,-1), 6),
        ("RIGHTPADDING", (0,0), (-1,-1), 6),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 6*mm))

    # ── Totals block ──────────────────────────────────────────────
    totals_data = [
        ["", "Subtotal", fmt_inr(po.get("subtotal", 0))],
        ["", "GST / Tax (5%)", fmt_inr(po.get("tax_amount", 0))],
        ["", "TOTAL AMOUNT", fmt_inr(po.get("total_amount", 0))],
    ]
    totals_table = Table(totals_data, colWidths=[90*mm, 45*mm, 35*mm])
    totals_table.setStyle(TableStyle([
        ("ALIGN",        (1,0), (-1,-1), "RIGHT"),
        ("FONTSIZE",     (0,0), (-1,-2), 9),
        ("FONTSIZE",     (0,2), (-1,2),  11),
        ("FONTNAME",     (0,2), (-1,2),  "Helvetica-Bold"),
        ("BACKGROUND",   (1,2), (-1,2),  BRAND_DARK),
        ("TEXTCOLOR",    (1,2), (-1,2),  colors.white),
        ("TOPPADDING",   (0,0), (-1,-1), 6),
        ("BOTTOMPADDING",(0,0), (-1,-1), 6),
        ("LEFTPADDING",  (1,0), (-1,-1), 8),
        ("RIGHTPADDING", (-1,0),(-1,-1), 8),
        ("LINEABOVE",    (1,2), (-1,2),  1, BRAND_INDIGO),
        ("TEXTCOLOR",    (1,1), (-1,1),  BRAND_AMBER),
    ]))
    story.append(totals_table)

    # ── Notes ─────────────────────────────────────────────────────
    if po.get("notes"):
        story.append(Spacer(1, 6*mm))
        story.append(Paragraph(
            f'<font size="9" color="#64748b"><b>NOTES:</b></font> '
            f'<font size="9" color="#475569">{po["notes"]}</font>',
            ParagraphStyle("notes", fontName="Helvetica", leading=13)
        ))

    # ── Signature line ────────────────────────────────────────────
    story.append(Spacer(1, 12*mm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#e2e8f0")))
    story.append(Spacer(1, 4*mm))
    sig_data = [[
        Paragraph('<font size="8" color="#94a3b8">Authorised Signatory</font><br/><br/>'
                  '<font size="8" color="#64748b">_________________________</font>',
                  ParagraphStyle("sig", fontName="Helvetica", leading=14)),
        Paragraph('<font size="8" color="#94a3b8">Date</font><br/><br/>'
                  '<font size="8" color="#64748b">_________________________</font>',
                  ParagraphStyle("sig2", fontName="Helvetica", leading=14)),
        Paragraph('<font size="7" color="#94a3b8" align="right">Generated by PO Management System<br/>'
                  'IV Innovations Pvt Ltd · Kundli, Sonipat</font>',
                  ParagraphStyle("footer", fontName="Helvetica", alignment=TA_RIGHT, leading=12)),
    ]]
    sig_table = Table(sig_data, colWidths=[57*mm, 57*mm, 56*mm])
    sig_table.setStyle(TableStyle([
        ("TOPPADDING", (0,0), (-1,-1), 0),
        ("VALIGN",     (0,0), (-1,-1), "TOP"),
    ]))
    story.append(sig_table)

    doc.build(story)
    return buffer.getvalue()
