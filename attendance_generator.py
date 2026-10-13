import io
import os
import pandas as pd
from PIL import Image as PILImage
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm

def generate_attendance_pdf(airline, date_display, time_str, venue_str, instructor_name, df_session, photo_bytes=None):
    """
    Menghasilkan dokumen PDF Daftar Kehadiran resmi Sriwijaya Air / NAM Air
    lengkap dengan tanda tangan instruktur dan gambar dokumentasi.
    """
    # 1. Pastikan peserta unik (tidak ada duplikat berdasarkan NIK)
    df_clean = df_session.drop_duplicates(subset=['nik']).reset_index(drop=True)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=1.5*cm,
        rightMargin=1.5*cm,
        topMargin=1.5*cm,
        bottomMargin=1.5*cm
    )
    
    story = []
    styles = getSampleStyleSheet()
    
    style_title = ParagraphStyle(
        'TitleStyle',
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=15,
        alignment=1
    )
    style_info = ParagraphStyle(
        'InfoStyle',
        fontName='Helvetica',
        fontSize=9,
        leading=12
    )
    style_cell = ParagraphStyle(
        'CellText',
        fontName='Helvetica',
        fontSize=8,
        leading=10
    )
    style_cell_header = ParagraphStyle(
        'CellHeader',
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        alignment=1
    )
    style_sign_name = ParagraphStyle(
        'SignName',
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=12,
        alignment=1
    )
    style_sign_title = ParagraphStyle(
        'SignTitle',
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        alignment=1
    )

    # 1. Header Logo & Judul
    logo_filename = "logo_sriwijaya.png" if airline == "SJ" else "logo_namair.png"
    logo_flowable = ""
    if os.path.exists(logo_filename):
        logo_flowable = RLImage(logo_filename, width=3.5*cm, height=1.5*cm)

    title_text = "<b>DAFTAR KEHADIRAN<br/>DANGEROUS GOODS AWARENESS</b>"
    header_table_data = [[logo_flowable, Paragraph(title_text, style_title)]]
    
    header_table = Table(header_table_data, colWidths=[4*cm, 14*cm])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN', (1,0), (1,0), 'CENTER'),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 0.4*cm))

    # 2. Metadata Training
    info_data = [
        [Paragraph("<b>Hari / Tanggal</b>", style_info), Paragraph(f": {date_display}", style_info)],
        [Paragraph("<b>Pukul</b>", style_info), Paragraph(f": {time_str}", style_info)],
        [Paragraph("<b>Tempat</b>", style_info), Paragraph(f": {venue_str}", style_info)],
    ]
    info_table = Table(info_data, colWidths=[3.2*cm, 14.8*cm])
    info_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 1),
        ('BOTTOMPADDING', (0,0), (-1,-1), 1),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 0.4*cm))

    # 3. Tabel Peserta
    table_rows = [
        [
            Paragraph("<b>NO</b>", style_cell_header),
            Paragraph("<b>Nama</b>", style_cell_header),
            Paragraph("<b>No. Handphone</b>", style_cell_header),
            Paragraph("<b>Jabatan</b>", style_cell_header),
            Paragraph("<b>Instansi / Perusahaan</b>", style_cell_header)
        ]
    ]

    for idx, row in df_clean.iterrows():
        table_rows.append([
            Paragraph(str(idx + 1), style_cell_header),
            Paragraph(str(row.get('full_name', '')).upper(), style_cell),
            Paragraph(str(row.get('phone', '-')), style_cell),
            Paragraph(str(row.get('job_role', '')), style_cell),
            Paragraph(str(row.get('company', '')).upper(), style_cell)
        ])

    col_widths = [1.2*cm, 5.2*cm, 3.2*cm, 4.2*cm, 4.2*cm]
    table_peserta = Table(table_rows, colWidths=col_widths, repeatRows=1)
    table_peserta.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 0.8, colors.black),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.black),
        ('BACKGROUND', (0,0), (-1,0), colors.whitesmoke),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    story.append(table_peserta)
    story.append(Spacer(1, 0.5*cm))

    # 4. Dokumentasi & Tanda Tangan Instruktur
    closing_elements = []
    
    if photo_bytes is not None:
        try:
            temp_img = io.BytesIO(photo_bytes)
            pil_i = PILImage.open(temp_img)
            w, h = pil_i.size
            aspect = h / w
            rl_img = RLImage(temp_img, width=8.5*cm, height=(8.5*cm * aspect))
            closing_elements.append(Paragraph("<b>Dokumentasi Training:</b>", style_info))
            closing_elements.append(Spacer(1, 0.2*cm))
            closing_elements.append(rl_img)
            closing_elements.append(Spacer(1, 0.3*cm))
        except Exception:
            pass

    # Ambil gambar tanda tangan jika ada file ttd_instruktur.png
    ttd_image = ""
    if os.path.exists("ttd_instruktur.png"):
        ttd_image = RLImage("ttd_instruktur.png", width=3.5*cm, height=2.0*cm)
    else:
        ttd_image = Spacer(1, 1.8*cm)

    # Format tanda tangan instruktur
    clean_inst_name = str(instructor_name).replace("<b>", "").replace("</b>", "").upper().strip()
    sign_data = [
        ["", Paragraph("Instruktur,", style_sign_title)],
        ["", ttd_image],
        ["", Paragraph(f"<u><b>{clean_inst_name}</b></u>", style_sign_name)]
    ]
    sign_table = Table(sign_data, colWidths=[11*cm, 7*cm])
    sign_table.setStyle(TableStyle([
        ('ALIGN', (1,0), (1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (1,0), (1,-1), 2),
        ('TOPPADDING', (1,0), (1,-1), 2),
    ]))
    closing_elements.append(sign_table)

    story.append(KeepTogether(closing_elements))
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


def generate_attendance_excel(date_display, time_str, venue_str, instructor_name, df_session):
    """
    Menghasilkan file Excel (.xlsx) Daftar Kehadiran tanpa duplikat.
    """
    df_clean = df_session.drop_duplicates(subset=['nik']).reset_index(drop=True)
    clean_inst_name = str(instructor_name).replace("<b>", "").replace("</b>", "").upper().strip()
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        meta_df = pd.DataFrame([
            ["DAFTAR KEHADIRAN TRAINING DANGEROUS GOODS AWARENESS", ""],
            [f"Hari / Tanggal: {date_display}", ""],
            [f"Pukul: {time_str}", ""],
            [f"Tempat: {venue_str}", ""],
            [f"Instruktur: {clean_inst_name}", ""],
            ["", ""]
        ])
        meta_df.to_excel(writer, index=False, header=False, sheet_name='Absensi', startrow=0)

        rows = []
        for idx, r in df_clean.iterrows():
            rows.append({
                "NO": idx + 1,
                "Nama": str(r.get('full_name', '')).upper(),
                "No. Handphone": str(r.get('phone', '-')),
                "Jabatan": str(r.get('job_role', '')),
                "Instansi / Perusahaan": str(r.get('company', '')).upper()
            })
        df_out = pd.DataFrame(rows)
        df_out.to_excel(writer, index=False, sheet_name='Absensi', startrow=6)
        
    output.seek(0)
    return output.getvalue()