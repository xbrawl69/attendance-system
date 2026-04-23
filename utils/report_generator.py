import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from datetime import datetime


def export_csv(records, output_path):
    df = pd.DataFrame(records)
    df.to_csv(output_path, index=False)
    print(f"[EXPORT] CSV saved: {output_path}")
    return output_path


def export_pdf(records, output_path, title="Attendance Report"):
    doc    = SimpleDocTemplate(output_path, pagesize=A4)
    styles = getSampleStyleSheet()
    story  = []

    story.append(Paragraph(title, styles["Title"]))
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles["Normal"]))
    story.append(Spacer(1, 16))

    if not records:
        story.append(Paragraph("No records found.", styles["Normal"]))
        doc.build(story)
        return output_path

    df      = pd.DataFrame(records)
    headers = list(df.columns)
    rows    = [headers] + df.values.tolist()

    table = Table(rows, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, 0),  colors.HexColor("#2C3E50")),
        ("TEXTCOLOR",    (0, 0), (-1, 0),  colors.white),
        ("FONTNAME",     (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",     (0, 0), (-1, 0),  10),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#F2F3F4"), colors.white]),
        ("FONTSIZE",     (0, 1), (-1, -1), 9),
        ("GRID",         (0, 0), (-1, -1), 0.4, colors.HexColor("#BDC3C7")),
        ("ALIGN",        (0, 0), (-1, -1), "LEFT"),
        ("PADDING",      (0, 0), (-1, -1), 6),
    ]))

    story.append(table)
    doc.build(story)
    print(f"[EXPORT] PDF saved: {output_path}")
    return output_path
