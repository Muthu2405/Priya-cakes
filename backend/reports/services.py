"""Builds the costing PDF for a saved product."""
from decimal import Decimal
from functools import lru_cache
from io import BytesIO
from pathlib import Path

from django.conf import settings
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

FONT_DIR = Path(__file__).parent / "fonts"
INK = colors.HexColor("#1b2620")
MUTED = colors.HexColor("#5b6861")
LINE = colors.HexColor("#c9d1c6")
GREEN = colors.HexColor("#234634")
TURMERIC = colors.HexColor("#f2b705")


@lru_cache(maxsize=1)
def fonts():
    """(regular, bold, currency prefix). Helvetica has no rupee sign, so fall back to 'Rs. '."""
    try:
        pdfmetrics.registerFont(TTFont("Body", str(FONT_DIR / "DejaVuSans.ttf")))
        pdfmetrics.registerFont(TTFont("Body-Bold", str(FONT_DIR / "DejaVuSans-Bold.ttf")))
        pdfmetrics.registerFontFamily("Body", normal="Body", bold="Body-Bold")
        return "Body", "Body-Bold", "\u20b9"
    except Exception:
        return "Helvetica", "Helvetica-Bold", "Rs. "


def indian(value) -> str:
    """12345.5 -> '12,345.50' using lakh/crore grouping."""
    text = f"{Decimal(value):.2f}"
    whole, frac = text.split(".")
    sign = "-" if whole.startswith("-") else ""
    whole = whole.lstrip("-")
    if len(whole) > 3:
        head, tail = whole[:-3], whole[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        whole = ",".join(groups + [tail])
    return f"{sign}{whole}.{frac}"


def plain_qty(value) -> str:
    return format(Decimal(value).normalize(), "f")


def build_product_pdf(product) -> bytes:
    regular, bold, rupee = fonts()
    money = lambda v: f"{rupee}{indian(v)}"

    def style(name, **kw):
        return ParagraphStyle(name, fontName=kw.pop("fontName", regular), textColor=kw.pop("textColor", INK), **kw)

    business = style("business", fontName=bold, fontSize=11, textColor=GREEN)
    title = style("title", fontName=bold, fontSize=22, leading=26, spaceBefore=4)
    meta = style("meta", fontSize=10, textColor=MUTED, spaceBefore=2)
    h2 = style("h2", fontName=bold, fontSize=12, spaceBefore=18, spaceAfter=6)
    note = style("note", fontSize=8.5, textColor=MUTED, leading=12)

    saved_on = timezone.localtime(product.created_at).strftime("%d %b %Y")
    story = [
        Paragraph(settings.BUSINESS_NAME, business),
        Paragraph(product.name, title),
        Paragraph(f"Costing date: {saved_on}", meta),
        Paragraph("Ingredients", h2),
    ]

    rows = [["Ingredient", "Used qty", "Unit", "Cost"]]
    for line in product.ingredients.all():
        rows.append([line.ingredient.name, plain_qty(line.used_quantity), line.used_unit, money(line.calculated_cost)])
    table = Table(rows, colWidths=[78 * mm, 30 * mm, 22 * mm, 40 * mm], repeatRows=1)
    table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), regular),
        ("FONTNAME", (0, 0), (-1, 0), bold),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("TEXTCOLOR", (0, 0), (-1, -1), INK),
        ("TEXTCOLOR", (0, 0), (-1, 0), MUTED),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("ALIGN", (3, 0), (3, -1), "RIGHT"),
        ("LINEBELOW", (0, 0), (-1, 0), 0.8, INK),
        ("LINEBELOW", (0, 1), (-1, -1), 0.4, LINE),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(table)

    story.append(Paragraph("Cost summary", h2))
    summary = [
        ["Ingredient total", money(product.total_ingredient_cost)],
        ["Packaging", money(product.packaging_cost)],
        ["EB / electricity", money(product.eb_cost)],
        ["Labour", money(product.labour_cost)],
        ["Final cost", money(product.total_cost)],
        ["Profit", money(product.profit)],
        ["Selling price", money(product.selling_price)],
    ]
    st = Table(summary, colWidths=[110 * mm, 60 * mm])
    st.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), regular),
        ("FONTSIZE", (0, 0), (-1, -1), 10.5),
        ("TEXTCOLOR", (0, 0), (-1, -1), INK),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LINEABOVE", (0, 4), (-1, 4), 0.6, INK),
        ("FONTNAME", (0, 4), (-1, 4), bold),
        ("LINEABOVE", (0, -1), (-1, -1), 1, INK),
        ("BACKGROUND", (0, -1), (-1, -1), TURMERIC),
        ("FONTNAME", (0, -1), (-1, -1), bold),
        ("FONTSIZE", (0, -1), (-1, -1), 13),
        ("TOPPADDING", (0, -1), (-1, -1), 8),
        ("BOTTOMPADDING", (0, -1), (-1, -1), 8),
    ]))
    story.append(st)

    story.append(Spacer(1, 14))
    story.append(Paragraph(
        f"Ingredient costs are fixed at the prices on {saved_on}; later price changes do not affect this report.", note))

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm, topMargin=20 * mm, bottomMargin=18 * mm,
        title=f"{product.name} costing", author=settings.BUSINESS_NAME,
    )
    doc.build(story)
    return buffer.getvalue()
