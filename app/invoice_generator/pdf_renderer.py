from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import (Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)

FONT_NAME = "HeiseiKakuGo-W5"
pdfmetrics.registerFont(UnicodeCIDFont(FONT_NAME))

DARK = colors.HexColor("#1a1a2e")
ACCENT = colors.HexColor("#4a9eff")
HEADER_BG = colors.HexColor("#f5f5f0")
BANK_BG = colors.HexColor("#f9f9f7")
BORDER = colors.HexColor("#e0e0e0")
ROW_LINE = colors.HexColor("#eeeeee")
SUBTEXT = colors.HexColor("#666666")
MUTED = colors.HexColor("#888888")


def yen(n: int) -> str:
    return f"¥{n:,}"


def _qty_str(q: float, unit: str) -> str:
    n = int(q) if float(q).is_integer() else q
    return f"{n} {unit}"


def render_invoice(out_path, *, issuer, client, items_calc,
                   invoice_no, issue_date, due_date, contact_person):
    doc = SimpleDocTemplate(
        str(out_path), pagesize=A4,
        leftMargin=15 * mm, rightMargin=15 * mm,
        topMargin=15 * mm, bottomMargin=15 * mm,
        title=f"請求書 {invoice_no}", author=issuer["company_name"],
    )
    styles = _styles()
    content_width = A4[0] - 30 * mm

    story = []
    story.append(_header(issuer, invoice_no, styles, content_width))
    story.append(Spacer(1, 4 * mm))
    story.append(_divider(content_width))
    story.append(Spacer(1, 4 * mm))
    story.append(_meta(client, issue_date, due_date, contact_person, styles, content_width))
    story.append(Spacer(1, 6 * mm))
    story.append(_total_box(items_calc["grand_total"], styles, content_width))
    story.append(Spacer(1, 6 * mm))
    story.append(_items_table(items_calc["rows"], content_width))
    story.append(Spacer(1, 4 * mm))
    story.append(_summary_table(items_calc))
    story.append(Spacer(1, 6 * mm))
    story.append(_bank_section(client, styles, content_width))
    story.append(Spacer(1, 4 * mm))
    notes = issuer.get("notes") or []
    if notes:
        story.append(_notes(notes, styles, content_width))

    doc.build(story)


def _styles():
    base = dict(fontName=FONT_NAME)
    return {
        "header_left": ParagraphStyle("hl", **base, leading=14),
        "header_right": ParagraphStyle("hr", **base, alignment=2, leading=13),
        "recipient": ParagraphStyle("rc", **base, leading=18),
        "meta": ParagraphStyle("mt", **base, alignment=2, leading=15),
        "total_label": ParagraphStyle("tl", **base, leading=12),
        "total_amount": ParagraphStyle("ta", **base, alignment=2, leading=24),
        "bank": ParagraphStyle("bk", **base, leading=14),
        "notes": ParagraphStyle("nt", **base, leading=12),
    }


def _header(issuer, invoice_no, styles, width):
    left = Paragraph(
        f'<font size="22"><b>請 求 書</b></font><br/>'
        f'<font size="8" color="#888888">No. {invoice_no}</font>',
        styles["header_left"],
    )
    right = Paragraph(
        f'<font size="11"><b>{issuer["company_name"]}</b></font><br/>'
        f'<font size="8" color="#666666">〒{issuer["postal_code"]}　{issuer["address"]}<br/>'
        f'TEL: {issuer.get("tel","")}'
        + (f'　FAX: {issuer["fax"]}' if issuer.get("fax") else "") + "<br/>"
        f'登録番号：{issuer.get("registration_number","")}</font>',
        styles["header_right"],
    )
    tbl = Table([[left, right]], colWidths=[width * 0.5, width * 0.5])
    tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("LINEABOVE", (0, 0), (-1, 0), 2, DARK),
        ("TOPPADDING", (0, 0), (-1, 0), 8),
    ]))
    return tbl


def _divider(width):
    line = Table([[""]], colWidths=[width], rowHeights=[0.1])
    line.setStyle(TableStyle([("LINEABOVE", (0, 0), (-1, 0), 0.5, BORDER)]))
    return line


def _meta(client, issue_date, due_date, contact_person, styles, width):
    recip = Paragraph(
        f'<font size="14"><b>{client["client_name"]}　御中</b></font><br/>'
        f'<font size="8" color="#666666">〒{client["postal_code"]}　{client["address"]}</font>',
        styles["recipient"],
    )
    meta = Paragraph(
        f'<font size="9"><b>発行日：</b>{issue_date}<br/>'
        f'<b>支払期限：</b>{due_date}<br/>'
        f'<b>担当者：</b>{contact_person}</font>',
        styles["meta"],
    )
    tbl = Table([[recip, meta]], colWidths=[width * 0.6, width * 0.4])
    tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("LINEBELOW", (0, 0), (0, 0), 1.5, DARK),
        ("BOTTOMPADDING", (0, 0), (0, 0), 4),
    ]))
    return tbl


def _total_box(grand_total, styles, width):
    label = Paragraph(
        '<font size="10" color="#8892b0">今回ご請求金額（税込）</font>',
        styles["total_label"],
    )
    amount = Paragraph(
        f'<font size="20" color="#ccd6f6"><b>{yen(grand_total)}</b></font>',
        styles["total_amount"],
    )
    tbl = Table([[label, amount]], colWidths=[width * 0.5, width * 0.5], rowHeights=[18 * mm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), DARK),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (0, 0), 16),
        ("RIGHTPADDING", (1, 0), (1, 0), 16),
    ]))
    return tbl


def _items_table(rows, width):
    header = ["品目・サービス", "数量", "単価", "金額"]
    data = [header]
    for r in rows:
        data.append([
            r["item_name"],
            _qty_str(r["quantity"], r["unit"]),
            f'{r["unit_price"]:,}',
            f'{r["amount"]:,}',
        ])
    col_w = [width * 0.46, width * 0.14, width * 0.18, width * 0.22]
    tbl = Table(data, colWidths=col_w, repeatRows=1)
    style = [
        ("FONTNAME", (0, 0), (-1, -1), FONT_NAME),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("FONTSIZE", (0, 1), (-1, -1), 10),
        ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
        ("TEXTCOLOR", (0, 0), (-1, 0), DARK),
        ("LINEBELOW", (0, 0), (-1, 0), 1.5, DARK),
        ("ALIGN", (0, 0), (0, -1), "LEFT"),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]
    for i in range(1, len(data)):
        style.append(("LINEBELOW", (0, i), (-1, i), 0.3, ROW_LINE))
    tbl.setStyle(TableStyle(style))
    return tbl


def _summary_table(calc):
    rows = []
    for rate in sorted(calc["by_rate"].keys(), reverse=True):
        v = calc["by_rate"][rate]
        pct = f"{rate * 100:g}"
        rows.append([f"小計（{pct}%対象）", yen(v["subtotal"])])
        rows.append([f"消費税（{pct}%）", yen(v["tax"])])
    rows.append(["合計（税込）", yen(calc["grand_total"])])
    last = len(rows) - 1

    tbl = Table(rows, colWidths=[55 * mm, 35 * mm])
    style = [
        ("FONTNAME", (0, 0), (-1, -1), FONT_NAME),
        ("FONTSIZE", (0, 0), (-1, last - 1), 9),
        ("FONTSIZE", (0, last), (-1, last), 12),
        ("TEXTCOLOR", (0, last), (-1, last), DARK),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LINEABOVE", (0, last), (-1, last), 1, DARK),
    ]
    for i in range(last):
        style.append(("LINEBELOW", (0, i), (-1, i), 0.3, ROW_LINE))
    tbl.setStyle(TableStyle(style))
    tbl.hAlign = "RIGHT"
    return tbl


def _bank_section(client, styles, width):
    bank_html = (
        '<font size="9" color="#4a9eff"><b>▍ お振込先</b></font><br/>'
        f'<font size="10">{client["bank_name"]}　{client["bank_branch"]}　'
        f'（{client["account_type"]}）　{client["account_number"]}<br/>'
        f'{client["account_holder"]}</font><br/>'
        '<font size="8" color="#888888">※振込手数料はご負担をお願いいたします。</font>'
    )
    p = Paragraph(bank_html, styles["bank"])
    tbl = Table([[p]], colWidths=[width])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BANK_BG),
        ("LINEBEFORE", (0, 0), (0, 0), 3, ACCENT),
        ("LEFTPADDING", (0, 0), (-1, -1), 14),
        ("RIGHTPADDING", (0, 0), (-1, -1), 14),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    return tbl


def _notes(notes, styles, width):
    body = "<br/>".join(f"※ {n}" for n in notes)
    p = Paragraph(f'<font size="8" color="#888888">{body}</font>', styles["notes"])
    tbl = Table([[p]], colWidths=[width])
    tbl.setStyle(TableStyle([
        ("LINEABOVE", (0, 0), (-1, 0), 0.5, BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    return tbl
