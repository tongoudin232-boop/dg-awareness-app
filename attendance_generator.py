import io
import os
import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image as RLImage,
    KeepTogether
)
from reportlab.lib.units import cm

def generate_attendance_pdf(airline, date_display, time_str, venue_str, instructor_name, df_session, photo_bytes=None):
    """
    Menghasilkan dokumen PDF Daftar Kehadiran (Absensi) resmi multi-halaman dinamis.
    Foto dokumentasi training diletakkan di atas, diikuti tanda tangan instruktur di bawahnya (sisi kanan).
    """
    buffer = io.BytesIO()
    
    # Margin dokumen standar A4
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm
    )
    
    story = []
    styles = getSampleStyleSheet()

    # Style Definisi Teks
    title_style = ParagraphStyle(
        'AttTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=16,
        alignment=1, # Rata Tengah
        textColor=colors.HexColor('#000000')
    )
    
    meta_label_style = ParagraphStyle(
        'MetaLabel',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#000000')
    )
    
    meta_val_style = ParagraphStyle(
        'MetaVal',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#000000')
    )
    
    cell_style = ParagraphStyle(
        'CellText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=10,
        alignment=0 # Rata Kiri
    )
    
    cell_center_style = ParagraphStyle(
        'CellCenter',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=10,
        alignment=1 # Rata Tengah
    )
    
    cell_header_style = ParagraphStyle(
        'CellHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11,
        alignment=1, # Rata Tengah
        textColor=colors.HexColor('#000000')
    )

    # ==================== 1. HEADER LOGO & JUDUL ====================
    logo_filename = "logo_sriwijaya.png" if airline == "SJ" else "logo_namair.png"
    if os.path.exists(logo_filename):
        try:
            logo_flowable = RLImage(logo_filename, width=4.5 * cm, height=1.6 * cm)
        except Exception:
            logo_flowable = Paragraph(f"<b>{airline}</b>", title_style)
    else:
        logo_flowable = Paragraph(f"<b>{airline}</b>", title_style)

    header_text = """
    <b>DAFTAR KEHADIRAN</b><br/>
    <b>DANGEROUS GOODS AWARENESS</b>
    """
    header_para = Paragraph(header_text, title_style)

    header_table = Table(
        [[logo_flowable, header_para]],
        colWidths=[5.5 * cm, 12.0 * cm]
    )
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('ALIGN', (1, 0), (1, 0), 'CENTER'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 0.6 * cm))

    # ==================== 2. METADATA TRAINING ====================
    meta_data = [
        [Paragraph("Hari / Tanggal", meta_label_style), Paragraph(f": {date_display}", meta_val_style)],
        [Paragraph("Pukul", meta_label_style), Paragraph(f": {time_str}", meta_val_style)],
        [Paragraph("Tempat", meta_label_style), Paragraph(f": {venue_str}", meta_val_style)]
    ]
    meta_table = Table(meta_data, colWidths=[3.2 * cm, 14.3 * cm])
    meta_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 1),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 0.4 * cm))

    # ==================== 3. TABEL DAFTAR PESERTA ====================
    table_content = [
        [
            Paragraph("NO", cell_header_style),
            Paragraph("Nama", cell_header_style),
            Paragraph("No. Handphone", cell_header_style),
            Paragraph("Jabatan", cell_header_style),
            Paragraph("Instansi / Perusahaan", cell_header_style)
        ]
    ]

    df_sorted = df_session.reset_index(drop=True)
    for idx, row in df_sorted.iterrows():
        no_str = str(idx + 1)
        name_str = str(row.get('full_name', '')).strip().upper()
        
        raw_phone = str(row.get('phone', '')).strip()
        if raw_phone.endswith('.0'):
            raw_phone = raw_phone[:-2]
        phone_str = raw_phone if raw_phone not in ['None', 'nan', ''] else '-'
        
        job_str = str(row.get('job_role', '')).strip()
        comp_str = str(row.get('company', '')).strip()

        table_content.append([
            Paragraph(no_str, cell_center_style),
            Paragraph(name_str, cell_style),
            Paragraph(phone_str, cell_center_style),
            Paragraph(job_str, cell_style),
            Paragraph(comp_str, cell_style)
        ])

    # Lebar kolom tabel total 17.5 cm (pas dengan printable area A4)
    col_widths = [1.0 * cm, 5.0 * cm, 3.5 * cm, 4.0 * cm, 4.0 * cm]
    # repeatRows=1 membuat baris judul tabel otomatis muncul kembali di halaman kedua dst.
    participants_table = Table(table_content, colWidths=col_widths, repeatRows=1)
    
    participants_table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#000000')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#000000')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F8F9FA')),
    ]))
    
    story.append(participants_table)
    story.append(Spacer(1, 0.6 * cm))

    # ==================== 4. DOKUMENTASI & TANDA TANGAN (VERTIKAL) ====================
    closing_elements = []

    doc_label_style = ParagraphStyle(
        'DocLabel',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor('#000000')
    )
    
    inst_title_style = ParagraphStyle(
        'InstTitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        alignment=1, # Rata Tengah
        textColor=colors.HexColor('#000000')
    )
    
    inst_name_style = ParagraphStyle(
        'InstName',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9.5,
        leading=13,
        alignment=1, # Rata Tengah
        textColor=colors.HexColor('#000000')
    )

    # 1. Judul & Foto Dokumentasi Training di Bagian Atas
    closing_elements.append(Paragraph("<b>Dokumentasi Training:</b>", doc_label_style))
    closing_elements.append(Spacer(1, 0.25 * cm))

    if photo_bytes:
        try:
            img_io = io.BytesIO(photo_bytes)
            closing_elements.append(RLImage(img_io, width=10.5 * cm, height=5.8 * cm))
        except Exception:
            closing_elements.append(Paragraph("<i>(Gagal memuat gambar)</i>", meta_val_style))
    else:
        closing_elements.append(Paragraph("<i>(Tidak ada lampiran foto kegiatan)</i>", meta_val_style))

    closing_elements.append(Spacer(1, 0.6 * cm))

    # 2. Tanda Tangan Instruktur di Bawah Foto (Sejajar Kanan)
    ttd_flowable = Spacer(1, 1.8 * cm)
    if os.path.exists("ttd_instruktur.png"):
        try:
            ttd_flowable = RLImage("ttd_instruktur.png", width=3.8 * cm, height=1.8 * cm)
        except Exception:
            ttd_flowable = Spacer(1, 1.8 * cm)

    instruktur_box = [
        Paragraph("Instruktur,", inst_title_style),
        Spacer(1, 0.1 * cm),
        ttd_flowable,
        Spacer(1, 0.1 * cm),
        Paragraph(f"<b><u>{instructor_name.upper()}</u></b>", inst_name_style)
    ]

    # Menggunakan tabel 2 kolom: kolom kiri kosong (10.5 cm) agar kotak ttd (7.0 cm) berada rapi di sisi kanan
    ttd_table = Table([["", instruktur_box]], colWidths=[10.5 * cm, 7.0 * cm])
    ttd_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (1, 0), (1, 0), 'CENTER'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    closing_elements.append(ttd_table)

    # KeepTogether menjaga agar foto dan blok ttd tidak terpisah canggung di ujung halaman
    story.append(KeepTogether(closing_elements))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


def generate_attendance_excel(date_display, time_str, venue_str, instructor_name, df_session):
    """
    Menghasilkan file Excel (.xlsx) untuk data absensi seluruh peserta tanpa batasan baris.
    """
    output = io.BytesIO()

    excel_rows = []
    df_sorted = df_session.reset_index(drop=True)

    for idx, row in df_sorted.iterrows():
        raw_phone = str(row.get('phone', '')).strip()
        if raw_phone.endswith('.0'):
            raw_phone = raw_phone[:-2]
        phone_clean = raw_phone if raw_phone not in ['None', 'nan', ''] else '-'

        excel_rows.append({
            'NO': idx + 1,
            'Nama Peserta': str(row.get('full_name', '')).strip().upper(),
            'No. Handphone': phone_clean,
            'Jabatan / Unit Kerja': str(row.get('job_role', '')).strip(),
            'Instansi / Perusahaan': str(row.get('company', '')).strip()
        })

    df_export = pd.DataFrame(excel_rows)

    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_export.to_excel(writer, index=False, sheet_name='Daftar_Hadir')
        ws = writer.sheets['Daftar_Hadir']

        col_widths = {'A': 6, 'B': 30, 'C': 18, 'D': 25, 'E': 25}
        for col_letter, width in col_widths.items():
            ws.column_dimensions[col_letter].width = width

    output.seek(0)
    return output.getvalue()