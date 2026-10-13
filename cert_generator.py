import io
import os
import qrcode
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from pypdf import PdfReader, PdfWriter

def create_qr_file(airline, cert_no, name, date_str):
    # Link URL verifikasi online resmi yang akan dibuka saat scan QR
    verify_url = f"https://ujian-dg-awareness.streamlit.app/?cert={cert_no}"
    
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=1,
    )
    qr.add_data(verify_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    file_path = f"temp_qr_{cert_no}.png"
    img.save(file_path)
    return file_path

def create_overlay(airline, cert_no, name, training_date_str, page_width, page_height, x_offset=0, y_offset=0):
    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=(page_width, page_height))

    COLOR_GOLD = colors.HexColor("#D4A017")
    COLOR_TEXT_DARK = colors.HexColor("#1A1A1A")

    center_x = x_offset + (page_width / 2.0)

    # -----------------------------------------------------------------
    # 1. NOMOR SERTIFIKAT (Diturunkan pas ke tengah ruang kosong)
    # -----------------------------------------------------------------
    can.setFont("Helvetica-Bold", 20)
    can.setFillColor(COLOR_TEXT_DARK)
    y_cert = y_offset + (page_height * 0.630)
    can.drawCentredString(center_x, y_cert, f"No. {cert_no}")

    # -----------------------------------------------------------------
    # 2. NAMA LENGKAP (Diturunkan sedikit ke tengah bidang)
    # -----------------------------------------------------------------
    can.setFont("Helvetica-Bold", 28)
    can.setFillColor(COLOR_GOLD)
    y_name = y_offset + (page_height * 0.468)
    can.drawCentredString(center_x, y_name, name.upper())

    # -----------------------------------------------------------------
    # 3. KOTA DAN TANGGAL (Tetap di posisi yang sudah pas)
    # -----------------------------------------------------------------
    can.setFont("Helvetica", 18)
    can.setFillColor(COLOR_TEXT_DARK)
    y_date = y_offset + (page_height * 0.275)
    can.drawCentredString(center_x, y_date, f"Tangerang, {training_date_str}")

    # -----------------------------------------------------------------
    # 4. QR CODE KADIV CARGO (Scan langsung menuju URL verifikasi)
    # -----------------------------------------------------------------
    qr_path = create_qr_file(airline, cert_no, name, training_date_str)
    qr_size = 80
    qr_x = x_offset + (page_width * 0.785) - (qr_size / 2.0)
    qr_y = y_offset + (page_height * 0.115)

    if os.path.exists(qr_path):
        can.drawImage(qr_path, qr_x, qr_y, width=qr_size, height=qr_size, mask=None)
        # Hapus file temporary QR setelah digambar ke canvas
        try:
            os.remove(qr_path)
        except Exception:
            pass

    can.save()
    packet.seek(0)
    return packet

def generate_certificate(airline, cert_no, name, training_date_str, *args, **kwargs):
    template_filename = "template_sj.pdf" if airline == "SJ" else "template_in.pdf"
    
    if os.path.exists(template_filename):
        existing_pdf = PdfReader(template_filename)
        first_page = existing_pdf.pages[0]
        
        mbox = first_page.mediabox
        x_offset = float(mbox.left)
        y_offset = float(mbox.bottom)
        page_width = float(mbox.width)
        page_height = float(mbox.height)
        
        overlay_stream = create_overlay(airline, cert_no, name, training_date_str, page_width, page_height, x_offset, y_offset)
        overlay_pdf = PdfReader(overlay_stream)
        
        first_page.merge_page(overlay_pdf.pages[0])
        
        output = PdfWriter()
        output.add_page(first_page)
        
        out_stream = io.BytesIO()
        output.write(out_stream)
        out_stream.seek(0)
        return out_stream.getvalue()
    else:
        buffer = io.BytesIO()
        can = canvas.Canvas(buffer, pagesize=(842, 595))
        can.setFont("Helvetica-Bold", 16)
        can.drawCentredString(421, 297, f"Template {template_filename} tidak ditemukan!")
        can.save()
        buffer.seek(0)
        return buffer.getvalue()