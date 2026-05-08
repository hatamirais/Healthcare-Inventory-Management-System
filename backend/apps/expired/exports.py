import csv
from html import escape
from io import BytesIO

from django.http import HttpResponse

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import LongTable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def export_expired_audit_csv(report, filters):
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = (
        'attachment; filename="expired_audit_report_'
        f'{filters["start_date"]}_{filters["end_date"]}.csv"'
    )
    response.write("\ufeff")
    writer = csv.writer(response)

    writer.writerow(
        [
            "row_type",
            "outcome_type",
            "document_type",
            "document_number",
            "document_url",
            "item_code",
            "item_name",
            "batch_lot",
            "expiry_date",
            "quantity",
            "unit",
            "location",
            "facility",
            "funding_source",
            "responsible_user",
            "event_timestamp",
            "notes",
            "reference_identifier",
        ]
    )

    for row in report["rows"]:
        writer.writerow(
            [
                row["row_type"],
                row["outcome_type"],
                row["document_type"],
                row["document_number"],
                row["document_url"],
                row["item_code"],
                row["item_name"],
                row["batch_lot"],
                row["expiry_date"].isoformat() if row["expiry_date"] else "",
                str(row["quantity"]),
                row["unit_name"],
                row["location_name"],
                row["facility_name"],
                row["funding_source_name"],
                row["responsible_user"],
                row["event_timestamp"].isoformat() if row["event_timestamp"] else "",
                row["notes"],
                row["reference_identifier"],
            ]
        )

    writer.writerow([])
    writer.writerow(["row_type", "label", "quantity"])
    for row in report["summary_by_outcome"]:
        writer.writerow(["SUMMARY_OUTCOME", row["label"], str(row["quantity"])])

    writer.writerow([])
    writer.writerow(
        ["row_type", "item_code", "item_name", "out_quantity", "destroy_quantity", "total_quantity"]
    )
    for row in report["summary_by_item"]:
        writer.writerow(
            [
                "SUMMARY_ITEM",
                row["item_code"],
                row["item_name"],
                str(row["out_quantity"]),
                str(row["destroy_quantity"]),
                str(row["total_quantity"]),
            ]
        )

    writer.writerow([])
    writer.writerow(
        ["row_type", "item_code", "item_name", "out_quantity", "destroy_quantity", "difference", "status"]
    )
    for row in report["reconciliation_rows"]:
        writer.writerow(
            [
                "RECONCILIATION",
                row["item_code"],
                row["item_name"],
                str(row["out_quantity"]),
                str(row["destroy_quantity"]),
                str(row["difference"]),
                row["status"],
            ]
        )

    return response


def export_expired_audit_pdf(report, filters):
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=18,
        rightMargin=18,
        topMargin=18,
        bottomMargin=18,
    )

    styles = getSampleStyleSheet()
    title_style = styles["Title"]
    title_style.fontSize = 16
    title_style.leading = 20
    small_style = ParagraphStyle(
        "SmallBody",
        parent=styles["BodyText"],
        fontSize=8,
        leading=10,
    )

    story = [
        Paragraph("Laporan Audit Barang Kedaluwarsa", title_style),
        Spacer(1, 8),
        Paragraph(
            escape(
                "Periode: "
                f'{filters["start_date"]} s/d {filters["end_date"]} | '
                f'Tipe hasil: {filters["outcome_type"]}'
            ),
            small_style,
        ),
        Spacer(1, 10),
    ]

    summary_table = Table(
        [
            ["Ringkasan per Tipe Hasil", "Jumlah"],
            *[
                [row["label"], str(row["quantity"])]
                for row in report["summary_by_outcome"]
            ],
        ],
        colWidths=[250, 120],
    )
    summary_table.setStyle(_table_style())
    story.extend([summary_table, Spacer(1, 10)])

    if report["summary_by_item"]:
        item_summary_table = LongTable(
            [
                ["Kode Barang", "Nama Barang", "OUT", "Destroy", "Total"],
                *[
                    [
                        row["item_code"],
                        row["item_name"],
                        str(row["out_quantity"]),
                        str(row["destroy_quantity"]),
                        str(row["total_quantity"]),
                    ]
                    for row in report["summary_by_item"]
                ],
            ],
            colWidths=[90, 220, 70, 70, 70],
            repeatRows=1,
        )
        item_summary_table.setStyle(_table_style())
        story.extend([item_summary_table, Spacer(1, 10)])

    if report["reconciliation_rows"]:
        mismatch_lines = []
        for row in report["reconciliation_rows"]:
            if row["difference"] == 0:
                continue
            mismatch_lines.append(
                f'- {escape(row["item_code"] or "-")} / {escape(row["item_name"] or "-")}: '
                f'OUT {row["out_quantity"]} vs Destroy {row["destroy_quantity"]} '
                f'(selisih {row["difference"]})'
            )
        reconciliation_text = (
            "<br/>".join(mismatch_lines)
            if mismatch_lines
            else "Tidak ada selisih antara total OUT dan Destroy pada scope filter ini."
        )
        story.extend(
            [
                Paragraph("<b>Catatan Rekonsiliasi</b>", styles["Heading4"]),
                Paragraph(reconciliation_text, small_style),
                Spacer(1, 10),
            ]
        )

    detail_rows = [
        [
            "Hasil",
            "Dokumen",
            "Barang",
            "Batch",
            "ED",
            "Qty",
            "Satuan",
            "Lokasi",
            "Fasilitas",
            "Pengguna",
            "Waktu",
            "Ref",
            "Catatan",
        ]
    ]
    for row in report["rows"]:
        detail_rows.append(
            [
                row["outcome_label"],
                row["document_number"],
                row["item_display"],
                row["batch_lot"],
                row["expiry_date"].isoformat() if row["expiry_date"] else "-",
                str(row["quantity"]),
                row["unit_name"],
                row["location_name"],
                row["facility_name"],
                row["responsible_user"],
                row["event_timestamp"].strftime("%Y-%m-%d %H:%M")
                if row["event_timestamp"]
                else "-",
                row["reference_label"],
                row["notes"],
            ]
        )

    detail_table = LongTable(
        detail_rows,
        colWidths=[65, 85, 135, 60, 62, 45, 45, 70, 80, 70, 82, 60, 95],
        repeatRows=1,
    )
    detail_table.setStyle(_table_style(font_size=6.5, leading=8))
    story.append(detail_table)

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()

    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = (
        'attachment; filename="expired_audit_report_'
        f'{filters["start_date"]}_{filters["end_date"]}.pdf"'
    )
    return response


def _table_style(font_size=8, leading=10):
    return TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e9ecef")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#adb5bd")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), font_size),
            ("LEADING", (0, 0), (-1, -1), leading),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8f9fa")]),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]
    )
