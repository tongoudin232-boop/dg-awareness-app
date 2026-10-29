import streamlit as st
import pandas as pd
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
import qrcode
import io
import os
import time
import base64
import json

try:
    from PyPDF2 import PdfReader, PdfWriter
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.utils import ImageReader
except ImportError:
    st.error("⚠️ Library 'PyPDF2' dan 'reportlab' belum terinstall. Buka Terminal/CMD dan ketik: `pip install PyPDF2 reportlab qrcode`")
    st.stop()

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

st.set_page_config(
    page_title="Letter of Authorization - Sriwijaya Air & NAM Air",
    page_icon="✈️",
    layout="wide"
)

# ---------------------------------------------------------
# SESSION STATE INISIALISASI MASTER DISTRIK
# ---------------------------------------------------------
DISTRIK_FILE = "distrik_db.json"
def load_distrik():
    if os.path.exists(DISTRIK_FILE):
        with open(DISTRIK_FILE, "r") as f:
            return json.load(f)
    return [
        "CGK - Jakarta", "SUB - Surabaya", "DPS - Denpasar", 
        "KNO - Medan", "UPG - Makassar", "PLM - Palembang"
    ]

def save_distrik(distrik_list):
    with open(DISTRIK_FILE, "w") as f:
        json.dump(distrik_list, f)

if "db_distrik" not in st.session_state:
    st.session_state.db_distrik = load_distrik()

def format_tgl_inggris(dt: date):
    day = dt.day
    if 11 <= day <= 13:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
    return f"{dt.strftime('%B')} {day}{suffix} {dt.year}"

# ---------------------------------------------------------
# GOOGLE API
# ---------------------------------------------------------
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
SHEET_COLUMNS = ["nomor_induk", "nama", "nik_emp", "jabatan", "kategori", "role", "perusahaan", "no_hp", "distrik", "exp_dg_cert", "url_foto", "url_license", "tgl_submit", "status_verifikasi", "catatan_admin", "status_ujian", "nilai", "tgl_ujian", "loa_valid_until", "no_loa_in", "no_loa_sj"]
TAB_NAME = "DataPesertaLoA"

def get_credentials():
    try:
        if "gcp_service_account" in st.secrets:
            creds_info = dict(st.secrets["gcp_service_account"])
        else:
            creds_info = dict(st.secrets)
            
        if not creds_info or "private_key" not in creds_info:
            return None

        if "private_key" in creds_info:
            pk = str(creds_info["private_key"])
            pk = pk.replace("\\n", "\n")
            creds_info["private_key"] = pk.strip()
            
        return Credentials.from_service_account_info(creds_info, scopes=SCOPES)
    except Exception as e:
        st.error(f"Error Credentials: {e}")
        return None

def init_google_resources():
    creds = get_credentials()
    if not creds: 
        st.error("DEBUG: Credentials gagal dimuat dari st.secrets!")
        return None, None, None, None, None
    try:
        s_drv = build("drive", "v3", credentials=creds, cache_discovery=False)
        s_sht = build("sheets", "v4", credentials=creds, cache_discovery=False)
        sid, fid, lid = "", "", ""
        
        try:
            if "google_drive" in st.secrets:
                sid = st.secrets["google_drive"].get("spreadsheet_id", "")
                fid = st.secrets["google_drive"].get("folder_id_photos", "")
                lid = st.secrets["google_drive"].get("folder_id_licenses", "")
        except Exception as e:
            st.error(f"DEBUG: Gagal membaca section google_drive di secrets: {e}")
            
        if not sid or not fid or not lid:
            res = s_drv.files().list(pageSize=100, q="trashed = false", fields="files(id, name, mimeType)").execute()
            for f in res.get("files", []):
                if not sid and f["name"] == "DG_Awareness_Database" and f["mimeType"] == "application/vnd.google-apps.spreadsheet": sid = f["id"]
                elif not fid and f["name"] == "LoA_Foto_Peserta": fid = f["id"]
                elif not lid and f["name"] == "LoA_Sertifikat_DG": lid = f["id"]
                
        return s_sht, s_drv, sid, fid, lid
    except Exception as e:
        st.error(f"DEBUG ERROR init_google_resources: {e}")
        return None, None, None, None, None

service_sheets, service_drive, SPREADSHEET_ID, FOLDER_FOTO_ID, FOLDER_LICENSE_ID = init_google_resources()

def upload_file_handler(uploaded_file, folder_id, filename):
    os.makedirs("uploads", exist_ok=True)
    safe_fn = "".join(c for c in filename if c.isalnum() or c in ("_", "-", ".")).rstrip()
    l_path = f"uploads/{safe_fn}"
    with open(l_path, "wb") as f: f.write(uploaded_file.getbuffer())
    if service_drive and folder_id:
        try:
            m = MediaIoBaseUpload(io.BytesIO(uploaded_file.getvalue()), mimetype=uploaded_file.type or "application/octet-stream", resumable=True)
            f_d = service_drive.files().create(body={"name": safe_fn, "parents": [folder_id]}, media_body=m, fields="id, webViewLink", supportsAllDrives=True).execute()
            service_drive.permissions().create(fileId=f_d.get("id"), body={"role": "reader", "type": "anyone"}, supportsAllDrives=True).execute()
            return f_d.get("webViewLink")
        except: pass
    return l_path

PESERTA_LOCAL_DB = "peserta_loa_db.json"

def load_local_db():
    if os.path.exists(PESERTA_LOCAL_DB):
        try:
            with open(PESERTA_LOCAL_DB, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []
    return []

def save_local_db(data_list):
    try:
        with open(PESERTA_LOCAL_DB, "w", encoding="utf-8") as f:
            json.dump(data_list, f, ensure_ascii=False, indent=4)
    except:
        pass

def load_data_peserta():
    if "local_peserta_loa" not in st.session_state: 
        st.session_state.local_peserta_loa = load_local_db()
        
    if service_sheets and SPREADSHEET_ID:
        try:
            sheet_metadata = service_sheets.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
            sheets = sheet_metadata.get('sheets', '')
            sheet_names = [s['properties']['title'] for s in sheets]
            target_sheet = TAB_NAME if TAB_NAME in sheet_names else (sheet_names[0] if sheet_names else "Sheet1")
            
            r = service_sheets.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID, range=f"{target_sheet}!A1:U").execute()
            v = r.get("values", [])
            if v and len(v) > 1:
                h = v[0]
                c_r = [row + [""] * (len(h) - len(row)) for row in v[1:]]
                df = pd.DataFrame(c_r, columns=h)
                for col in SHEET_COLUMNS:
                    if col not in df.columns: df[col] = ""
                return df
        except Exception:
            pass
            
    if not st.session_state.local_peserta_loa:
        st.session_state.local_peserta_loa = load_local_db()
    
    if st.session_state.local_peserta_loa:
        df = pd.DataFrame(st.session_state.local_peserta_loa)
        for col in SHEET_COLUMNS:
            if col not in df.columns: df[col] = ""
        return df
        
    return pd.DataFrame(columns=SHEET_COLUMNS)

def save_new_peserta(d):
    if "local_peserta_loa" not in st.session_state: 
        st.session_state.local_peserta_loa = load_local_db()
    st.session_state.local_peserta_loa.append(d)
    save_local_db(st.session_state.local_peserta_loa)
    
    if service_sheets and SPREADSHEET_ID:
        try:
            sheet_metadata = service_sheets.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
            sheets = sheet_metadata.get('sheets', '')
            sheet_names = [s['properties']['title'] for s in sheets]
            target_sheet = TAB_NAME if TAB_NAME in sheet_names else (sheet_names[0] if sheet_names else "Sheet1")
            
            rv = [str(d.get(c, ""))[:49000] for c in SHEET_COLUMNS]
            service_sheets.spreadsheets().values().append(
                spreadsheetId=SPREADSHEET_ID,
                range=f"{target_sheet}!A1",
                valueInputOption="USER_ENTERED",
                insertDataOption="INSERT_ROWS",
                body={"values": [rv]}
            ).execute()
        except Exception:
            pass
            
    return True

def update_peserta(no_id, uf):
    if "local_peserta_loa" in st.session_state:
        for p in st.session_state.local_peserta_loa:
            if str(p.get("nomor_induk", "")).strip() == str(no_id).strip(): p.update(uf)
    if not service_sheets or not SPREADSHEET_ID: return True
    try:
        r = service_sheets.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID, range=f"{TAB_NAME}!A1:U").execute()
        v = r.get("values", [])
        if not v: return False
        h = v[0]
        ri = -1
        for i, row in enumerate(v):
            if row and str(row[0]).strip() == str(no_id).strip(): ri = i + 1; break
        if ri != -1:
            for fd, val in uf.items():
                if fd in h:
                    cl = chr(ord('A') + h.index(fd))
                    service_sheets.spreadsheets().values().update(spreadsheetId=SPREADSHEET_ID, range=f"{TAB_NAME}!{cl}{ri}", valueInputOption="USER_ENTERED", body={"values": [[str(val)[:49000]]]}).execute()
            return True
        return False
    except: return False

def delete_peserta_trial(no_id):
    if "local_peserta_loa" in st.session_state:
        st.session_state.local_peserta_loa = [p for p in st.session_state.local_peserta_loa if str(p.get("nomor_induk", "")).strip() != str(no_id).strip()]
    if not service_sheets or not SPREADSHEET_ID: return True
    try:
        r = service_sheets.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID, range=f"{TAB_NAME}!A1:U").execute()
        v = r.get("values", [])
        if not v: return False
        ri = -1
        for i, row in enumerate(v):
            if row and str(row[0]).strip() == str(no_id).strip(): ri = i + 1; break
        if ri != -1:
            sm = service_sheets.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
            sid = next(s["properties"]["sheetId"] for s in sm.get("sheets", []) if s["properties"]["title"] == TAB_NAME)
            service_sheets.spreadsheets().batchUpdate(spreadsheetId=SPREADSHEET_ID, body={"requests": [{"deleteDimension": {"range": {"sheetId": sid, "dimension": "ROWS", "startIndex": ri - 1, "endIndex": ri}}}]}).execute()
            return True
        return False
    except: return False

def generate_nomor_induk(df_all):
    prefix = f"LOA{date.today().strftime('%m%y')}"
    if df_all.empty or "nomor_induk" not in df_all.columns: return f"{prefix}0001"
    ex = df_all[df_all["nomor_induk"].astype(str).str.startswith(prefix, na=False)]["nomor_induk"].tolist()
    if not ex: return f"{prefix}0001"
    nums = [int(str(x).replace(prefix, "")) for x in ex if str(x).replace(prefix, "").isdigit()]
    return f"{prefix}{(max(nums) if nums else 0) + 1:04d}"

def generate_nomor_loa(df_all, carrier):
    today = date.today()
    romawi = {1: "I", 2: "II", 3: "III", 4: "IV", 5: "V", 6: "VI", 7: "VII", 8: "VIII", 9: "IX", 10: "X", 11: "XI", 12: "XII"}.get(today.month, "I")
    cn = "no_loa_in" if carrier == "IN" else "no_loa_sj"
    ct = "IN-CGO" if carrier == "IN" else "SJ-CGO"
    cl = 1
    if not df_all.empty and cn in df_all.columns:
        vl = df_all[df_all[cn].notna() & (df_all[cn].astype(str).str.strip() != "")][cn].tolist()
        cl = len(vl) + 1
    return f"{cl:04d}/LOA/{ct}/{romawi}/{today.year}"

# ---------------------------------------------------------
# GENERATOR LIVE PDF TAMPING OVERLAY (ZERO-OVERLAP FIX)
# ---------------------------------------------------------
def create_pdf_loa(template_path, p, carrier, valid_date_fmt, tgl_terbit_fmt):
    try:
        existing_pdf = PdfReader(open(template_path, "rb"))
        page = existing_pdf.pages[0]
        w = float(page.mediabox.width)
        h = float(page.mediabox.height)
    except Exception as e:
        return None

    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=(w, h))
    
    no_loa = p.get('no_loa_sj', '-') if carrier == "SJ" else p.get('no_loa_in', '-')
    role_str = str(p.get('role', '-')).upper()
    
    can.setFillColorRGB(0, 0, 0)
    
    # 1. Foto Peserta di bawah logo (Kiri)
    import glob
    foto_url = str(p.get("url_foto", "")).strip()
    nomor = str(p.get("nomor_induk", ""))
    foto_local = foto_url if os.path.exists(foto_url) else ""
    if not foto_local:
        matches = glob.glob(f"uploads/FOTO_{nomor}*")
        if matches: foto_local = matches[0]
    
    if foto_local and os.path.exists(foto_local):
        try:
            can.drawImage(ImageReader(foto_local), w * 0.045, h * 0.52, width=65, height=85)
        except Exception:
            pass

    # 2. Nomor LoA (10pt, Bold)
    can.setFont("Helvetica-Bold", 10)
    can.drawCentredString(w * 0.58, h * 0.77, f"{no_loa}")
    
    # 3. Data Karyawan: Dicetak terpisah baris demi baris di X = 42% (sebelah kanan titik dua)
    can.setFont("Helvetica-Bold", 10)
    can.drawString(w * 0.42, h * 0.620, f"{p.get('nama', '-')}")
    can.drawString(w * 0.42, h * 0.582, f"{p.get('nik_emp', '-')}")
    can.drawString(w * 0.42, h * 0.544, f"{p.get('jabatan', '-')}")
    can.drawString(w * 0.42, h * 0.506, f"{p.get('perusahaan', '-')}")
    
    # 4. Role Karyawan (12pt, Bold, Biru/Merah)
    can.setFont("Helvetica-Bold", 12)
    if carrier == "SJ":
        can.setFillColorRGB(0, 0.12, 0.37)
    else:
        can.setFillColorRGB(0.85, 0.01, 0.16)
    can.drawCentredString(w * 0.58, h * 0.40, f"{role_str}")
    
    # 5. Valid Date (10pt, Bold)
    can.setFillColorRGB(0, 0, 0)
    can.setFont("Helvetica-Bold", 10)
    can.drawCentredString(w * 0.115, h * 0.13, f"{valid_date_fmt}")
    
    # 6. Tempat & Tanggal (9.5pt, Semi-Bold Italics / Oblique)
    can.setFont("Helvetica-Oblique", 9.5)
    can.drawCentredString(w * 0.62, h * 0.22, f"Tangerang, {tgl_terbit_fmt}")
    
    # 7. QR Code Verifikasi Keaslian (Kecil & Rapi di Sudut Kanan Bawah)
    verify_text = f"VERIFIKASI RESMI LOA\nNo: {no_loa}\nNama: {p.get('nama', '-')}\nNIK: {p.get('nik_emp', '-')}\nRole: {role_str}\nValid: {valid_date_fmt}\nStatus: VERIFIED"
    qr = qrcode.QRCode(version=1, box_size=2, border=1)
    qr.add_data(verify_text)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")
    qr_bytes = io.BytesIO()
    qr_img.save(qr_bytes, format="PNG")
    qr_bytes.seek(0)
    
    can.drawImage(ImageReader(qr_bytes), w * 0.81, h * 0.10, width=32, height=32)
    
    can.save()
    packet.seek(0)
    new_pdf = PdfReader(packet)
    
    try:
        output = PdfWriter()
        page.merge_page(new_pdf.pages[0])
        output.add_page(page)
        final_pdf = io.BytesIO()
        output.write(final_pdf)
        return final_pdf.getvalue()
    except Exception as e:
        return None

SOAL_UJIAN_RESMI = [
    {"no": 1, "q": "Klasifikasi Dangerous Goods dibagi menjadi?", "options": ["a) 1 class", "b) 7 Class", "c) 9 Class", "d) 8 Class"], "a": "c) 9 Class"},
    {"no": 2, "q": "Manakah zat/artikel di bawah ini yang termasuk dalam kategori DG Class-1 (Explosive)?", "options": ["a) Natrium Klorida", "b) Bomb, Amunisi & Kembang Api", "c) Magnet", "d) Asam Sulfat"], "a": "b) Bomb, Amunisi & Kembang Api"},
    {"no": 3, "q": "Manakah zat/artikel di bawah ini yang termasuk dalam kategori DG Class-2 (Gases)?", "options": ["a) Gas Oksigen", "b) Bensin", "c) Alkohol", "d) Parfum"], "a": "a) Gas Oksigen"},
    {"no": 4, "q": "Manakah zat/artikel di bawah ini yang termasuk dalam kategori DG Class-3 (Flammable Liquid)?", "options": ["a) Gas Oksigen", "b) Bensin", "c) Air Aki", "d) Gas karbondioksida"], "a": "b) Bensin"},
    {"no": 5, "q": "Manakah zat/artikel di bawah ini yang termasuk dalam kategori DG Class-4 (Flammable Solid)?", "options": ["a) Gas Oksigen", "b) Aceton", "c) Sulfur, logam alkali", "d) Gas karbondioksida"], "a": "c) Sulfur, logam alkali"},
    {"no": 6, "q": "Manakah zat/artikel di bawah ini yang termasuk dalam kategori DG Class-5 (Oxidizing Substances & Organic peroxide)?", "options": ["a) Hidrogen peroksida", "b) Oksigen Generator", "c) Jawaban a & b (benar)", "d) Gas karbondioksida"], "a": "c) Jawaban a & b (benar)"},
    {"no": 7, "q": "Manakah zat/artikel di bawah ini yang termasuk dalam kategori DG Class-6 (Toxic & Infectious Substances)?", "options": ["a) Sianida", "b) Bensin", "c) Sampel virus", "d) Jawaban a & c (benar)"], "a": "d) Jawaban a & c (benar)"},
    {"no": 8, "q": "Manakah zat/artikel di bawah ini yang termasuk dalam kategori DG Class-7 (Radioaktive Material)?", "options": ["a) Natrium Benzoat", "b) Uranium", "c) Aluminium", "d) Lithium"], "a": "b) Uranium"},
    {"no": 9, "q": "Manakah zat/artikel di bawah ini yang termasuk dalam kategori DG Class-8 (Corrosive)?", "options": ["a) Kalsium", "b) Plutonium", "c) Asam sulfat", "d) Lithium"], "a": "c) Asam sulfat"},
    {"no": 10, "q": "Manakah zat/artikel di bawah ini yang termasuk dalam kategori DG Class-9 (Miscellaneous Material)?", "options": ["a) Magnet Material", "b) Jawaban a & d (benar)", "c) Air Aki", "d) Lithium Battery"], "a": "b) Jawaban a & d (benar)"},
    {"no": 11, "q": "Dangerous Goods Class 6 (Toxic & Infectious Substances) terbagi menjadi sub divisi?", "options": ["a) 6.1, 6.2", "b) 6.1, 6.2, 6.3", "c) 6.1", "d) 6.1, 6.2, 6.3, 6.4"], "a": "a) 6.1, 6.2"},
    {"no": 12, "q": "Dangerous Goods Class 5 (Oxidizing Substances & Organic Peroxide) terbagi menjadi sub divisi?", "options": ["a) 5.1", "b) 5.1, 5.2, 5.3, 5.4", "c) 5.1, 5.2", "d) 5.1, 5.2, 5.3"], "a": "c) 5.1, 5.2"},
    {"no": 13, "q": "Dangerous Goods Class 4 (Flammable Solid) terbagi menjadi sub divisi?", "options": ["a) 4.1, 4.2, 4.3, 4.4, 4.5", "b) 4.1", "c) 4.1, 4.2, 4.3", "d) 4.1, 4.2"], "a": "c) 4.1, 4.2, 4.3"},
    {"no": 14, "q": "Dangerous Goods Class 2 (Gases) terbagi menjadi sub divisi?", "options": ["a) 2.1, 2.2, 2.3", "b) 2.1, 2.2", "c) 2.1, 2.2, 2.3, 2.4, 2.5", "d) 2.1"], "a": "a) 2.1, 2.2, 2.3"},
    {"no": 15, "q": "Packing Group I dengan kode (X) menandakan tingkat bahaya?", "options": ["a) Medium Danger", "b) High Danger", "c) Low Danger", "d) Small Danger"], "a": "b) High Danger"},
    {"no": 16, "q": "Packing Group II dengan kode (Y) menandakan tingkat bahaya?", "options": ["a) High Danger", "b) Low Danger", "c) Small Danger", "d) Medium Danger"], "a": "d) Medium Danger"},
    {"no": 17, "q": "Packing Group III dengan kode (Z) menandakan tingkat bahaya?", "options": ["a) High Danger", "b) Medium Danger", "c) Low Danger", "d) Small Danger"], "a": "c) Low Danger"},
    {"no": 18, "q": "MSDS adalah lembar petunjuk yang berisikan informasi dari sebuah bahan/produk meliputi sifat kimiawi, jenis bahaya yang ditimbulkan, cara penanganan serta tindakan khusus dalam keadaan darurat. MSDS adalah singkatan dari?", "options": ["a) Material Security Data Safety", "b) Material Safety Data Security", "c) Material Safety Data Sheet", "d) Material Sheet Data Safety"], "a": "c) Material Safety Data Sheet"},
    {"no": 19, "q": "Yang dimaksud dengan Limitasi Dangerous Goods kategori Forbidden/Dilarang adalah:", "options": ["a) Artikel/Zat yang tidak boleh diangkut pada penerbangan dalam keadaan dan kondisi apapun.", "b) Artikel/zat yang diangkut pada penerbangan normal dalam kemasan tertentu.", "c) Artikel/zat yang diangkut pada penerbangan dalam kondisi tertentu.", "d) Artikel/zat yang diangkut pada penerbangan dengan Batasan tertentu."], "a": "a) Artikel/Zat yang tidak boleh diangkut pada penerbangan dalam keadaan dan kondisi apapun."},
    {"no": 20, "q": "Dangerous Goods dikelompokkan pada Group Pengepakan (Packing Group) yang relevan berdasarkan tingkat bahayanya yang terbagi menjadi berapa kelompok packing group?", "options": ["a) 2 Packing Group", "b) 1 Packing Group", "c) 3 Packing Group", "d) 4 Packing Group"], "a": "c) 3 Packing Group"},
    {"no": 21, "q": "Tindakan apa yang harus dilakukan ketika terjadi insiden kebocoran DG Class 3?", "options": ["a) Padamkan api menggunakan air", "b) Taburkan pasir / serbuk kayu pada tampakan TUMPAHAN", "c) Cegah semua sumber api", "d) b dan c benar"], "a": "d) b dan c benar"},
    {"no": 22, "q": "Tindakan apa yang harus dilakukan ketika terjadi insiden paket yang mengandung baterai lithium mengeluarkan asap?", "options": ["a) Berada diposisi menghadap arah angin", "b) Berada diposisi berlawanan arah angin", "c) b dan d benar", "d) Hubungi PKP-PK"], "a": "c) b dan d benar"},
    {"no": 23, "q": "Pilih pernyataan yang benar bagi penumpang yang ingin membawa Smart Baggage (removable batteries)?", "options": ["a) Baterai harus dilepas dan dibawa ke dalam kabin", "b) Hanya boleh dibawa apabila dalam keadaan kosong", "c) Harus masuk bagasi kabin"], "a": "a) Baterai harus dilepas dan dibawa ke dalam kabin"},
    {"no": 24, "q": "Manakah dari kelas barang berbahaya (Dangerous Goods) berikut yang secara tegas dinyatakan tidak diangkut oleh Sriwijaya Air?", "options": ["a) Class 2.1", "b) Class 6.2", "c) Class 7", "d) Class 8"], "a": "c) Class 7"},
    {"no": 25, "q": "Tempat penyimpanan yang benar untuk 'small cigarette lighter' selama penerbangan adalah..", "options": ["a) Saku celana", "b) Saku jaket", "c) Bagasi kabin", "d) a dan b benar"], "a": "d) a dan b benar"}
]

st.sidebar.markdown("---")
st.sidebar.markdown("### **MODUL LOA DG**")

if "is_admin" not in st.session_state: st.session_state.is_admin = False

if not st.session_state.is_admin:
    menu_options = ["1. Submit Data LoA (Publik)", "3. Modul Materi & Ujian LoA (Publik)", "🔑 Akses Admin"]
else:
    menu_options = ["1. Submit Data LoA (Publik)", "2. Verifikasi Data Peserta (Admin)", "3. Modul Materi & Ujian LoA (Publik)", "4. Laporan Evaluasi Assessment", "5. Dashboard Admin & Records (Reminder)", "6. Master Distrik & Jadwal Recurrent", "🚪 Keluar Admin"]

sub_menu = st.sidebar.radio("Alur Proses LoA:", menu_options)

if sub_menu == "🔑 Akses Admin":
    st.title("Akses Khusus Admin")
    st.info("Menu Verifikasi, Laporan, Dashboard, dan Master Distrik hanya untuk Administrator.")
    admin_pin = st.text_input("Masukkan PIN Admin:", type="password")
    if st.button("Login Admin"):
        if admin_pin == "1234":
            st.session_state.is_admin = True
            st.success("Berhasil login sebagai Admin!")
            st.rerun()
        else: st.error("PIN Admin salah!")
    st.stop()

if sub_menu == "🚪 Keluar Admin":
    st.session_state.is_admin = False
    st.success("Berhasil keluar dari mode Admin.")
    st.rerun()

df_all = load_data_peserta()

if sub_menu == "1. Submit Data LoA (Publik)":
    st.title("Tahap 1: Pengajuan Data Diri & Dokumen Persyaratan LoA")
    st.caption("Pendaftaran Personil Shipper, Regulated Agent, Warehouse, dan Ground Handling")
    with st.form("form_registrasi_loa", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            nama = st.text_input("Nama Lengkap (Sesuai KTP / Lisensi):")
            nik_emp = st.text_input("NIK Employee ID / ID Karyawan:")
            jabatan = st.text_input("Job Title / Jabatan:")
            kategori = st.selectbox("Kategori Instansi Personil:", ["--pilih kategori--", "Shipper", "Regulated Agent", "Warehouse", "Ground Handling"], index=0)
            role_dg = st.selectbox("Pilihan Role / Tugas Penanganan DG:", ["--pilih role--", "Packer", "Acceptance", "Cargo Loader", "Load Master"], index=0)
            perusahaan = st.text_input("Nama Perusahaan / Company:")
        with c2:
            no_hp = st.text_input("Nomor Handphone / WA Aktif:")
            distrik = st.selectbox("Distrik / Stasiun Penugasan:", ["--pilih distrik--"] + st.session_state.db_distrik, index=0)
            exp_dg_cert = st.date_input("Masa Berlaku Lisensi/Sertifikat DG Saat Ini:", value=None)
            foto_merah = st.file_uploader("Upload Foto Diri (Wajib Background Merah):", type=["jpg", "png", "jpeg"])
            foto_cert = st.file_uploader("Upload Scan Sertifikat DG / DG Awareness Valid:", type=["jpg", "png", "pdf"])

        btn_submit = st.form_submit_button("Submit Data Permohonan LoA")
        if btn_submit:
            if distrik == "--pilih distrik--" or kategori == "--pilih kategori--" or role_dg == "--pilih role--" or not exp_dg_cert: st.error("Harap pilih Distrik, Kategori, Role, dan Masa Berlaku Lisensi dengan benar!")
            elif not (nama and nik_emp and jabatan and perusahaan and no_hp and foto_merah and foto_cert): st.error("Semua kolom isian formulir wajib diisi!")
            elif not df_all.empty and "nik_emp" in df_all.columns and nik_emp in df_all["nik_emp"].astype(str).values: st.warning("NIK ini sudah terdaftar!")
            else:
                nomor_induk = generate_nomor_induk(df_all)
                with st.spinner("Menyimpan berkas pendaftaran..."):
                    ext_foto = os.path.splitext(foto_merah.name)[1] or ".png"
                    ext_cert = os.path.splitext(foto_cert.name)[1] or ".pdf"
                    url_foto = upload_file_handler(foto_merah, FOLDER_FOTO_ID, f"FOTO_{nomor_induk}_{nama}{ext_foto}")
                    url_license = upload_file_handler(foto_cert, FOLDER_LICENSE_ID, f"CERT_{nomor_induk}_{nama}{ext_cert}")
                    record_baru = {"nomor_induk": nomor_induk, "nama": nama, "nik_emp": nik_emp, "jabatan": jabatan, "kategori": kategori, "role": role_dg, "perusahaan": perusahaan, "no_hp": no_hp, "distrik": distrik, "exp_dg_cert": str(exp_dg_cert), "url_foto": url_foto, "url_license": url_license, "tgl_submit": str(date.today()), "status_verifikasi": "Pending", "catatan_admin": "", "status_ujian": "Belum Ujian", "nilai": 0, "tgl_ujian": "", "loa_valid_until": "", "no_loa_in": "", "no_loa_sj": ""}
                    if save_new_peserta(record_baru):
                        st.success("✅ Berkas berhasil terkirim!")
                        st.info(f"🎫 Nomor Induk Resmi Anda: **{nomor_induk}**. Harap dicatat!")
                        st.cache_data.clear()

elif sub_menu == "2. Verifikasi Data Peserta (Admin)":
    st.title("Tahap 2: Verifikasi Dokumen & Kualifikasi Peserta")
    if st.button("🔄 Sinkronkan Data Lokal ke Google Sheets"):
        success_count = sum(1 for p in st.session_state.get("local_peserta_loa", []) if df_all.empty or str(p["nomor_induk"]) not in df_all["nomor_induk"].astype(str).values and save_new_peserta(p))
        st.success(f"Berhasil menyinkronkan {success_count} data!")
        st.cache_data.clear(); st.rerun()

    df_pending = df_all[df_all["status_verifikasi"].astype(str).str.lower() == "pending"] if not df_all.empty and "status_verifikasi" in df_all.columns else pd.DataFrame()
    if df_pending.empty: st.info("Tidak ada berkas yang menunggu verifikasi saat ini.")
    else:
        for _, p in df_pending.iterrows():
            with st.expander(f"📌 {p['nomor_induk']} - {p['nama']}", expanded=True):
                col_info, col_act = st.columns([2, 1])
                with col_info:
                    st.write(f"**NIK:** {p['nik_emp']} | **Jabatan:** {p['jabatan']} | **Perusahaan:** {p['perusahaan']}")
                    st.write(f"**Role:** `{p['role']}` | **Distrik:** {p['distrik']} | **Sertifikat Expired:** {p['exp_dg_cert']}")
                with col_act:
                    catatan = st.text_input("Catatan Admin:", key=f"cat_{p['nomor_induk']}")
                    btn_a, btn_b = st.columns(2)
                    if btn_a.button("✅ Loloskan", key=f"pass_{p['nomor_induk']}"): update_peserta(p["nomor_induk"], {"status_verifikasi": "Approved", "catatan_admin": catatan}); st.rerun()
                    if btn_b.button("❌ Tolak", key=f"rej_{p['nomor_induk']}"): update_peserta(p["nomor_induk"], {"status_verifikasi": "Rejected", "catatan_admin": catatan}); st.rerun()
                
                import glob
                foto_url = str(p.get("url_foto", "")).strip()
                lic_url = str(p.get("url_license", "")).strip()
                nomor = str(p.get("nomor_induk", ""))
                
                foto_local = foto_url if os.path.exists(foto_url) else ""
                if not foto_local:
                    matches = glob.glob(f"uploads/FOTO_{nomor}*")
                    if matches: foto_local = matches[0]

                if foto_local and os.path.exists(foto_local):
                    st.image(foto_local, caption="Foto Peserta", width=150)
                    with open(foto_local, "rb") as f_foto:
                        st.download_button(label="📥 Download Foto Peserta", data=f_foto.read(), file_name=os.path.basename(foto_local), key=f"dl_foto_{nomor}")
                else:
                    if foto_url.startswith("http"):
                        st.markdown(f"**Foto Peserta:** [Buka di Google Drive]({foto_url})")
                    else:
                        st.caption(f"Path Foto: `{foto_url}` (Tidak ditemukan di lokal)")

                lic_local = lic_url if os.path.exists(lic_url) else ""
                if not lic_local:
                    matches = glob.glob(f"uploads/CERT_{nomor}*")
                    if matches: lic_local = matches[0]

                if lic_local and os.path.exists(lic_local):
                    with open(lic_local, "rb") as f_pdf:
                        st.download_button(label="📥 Download Sertifikat / Lisensi DG", data=f_pdf.read(), file_name=os.path.basename(lic_local), key=f"dl_cert_{nomor}")
                else:
                    if lic_url.startswith("http"):
                        st.markdown(f"**Sertifikat DG:** [Buka di Google Drive]({lic_url})")
                    else:
                        st.caption(f"Path Sertifikat: `{lic_url}` (Tidak ditemukan di lokal)")

elif sub_menu == "3. Modul Materi & Ujian LoA (Publik)":
    st.title("Tahap 3: Modul Materi & Ujian Penilaian Kompetensi LoA")
    login_id = st.text_input("Masukkan Nomor Induk Sistem Anda (Contoh: LOA12345678):").strip().upper()

    if login_id:
        if df_all.empty: st.warning("Belum ada data pendaftar dalam sistem.")
        else:
            p_row = df_all[df_all["nomor_induk"].astype(str).str.strip() == str(login_id)]
            if p_row.empty: st.error("Nomor Induk tidak ditemukan.")
            else:
                p = p_row.iloc[0].to_dict()
                st_verif = str(p.get("status_verifikasi", "")).strip().lower()

                if st_verif == "pending": st.warning("⏳ Pengajuan Anda masih dalam status 'Pending' verifikasi admin.")
                elif st_verif == "rejected": st.error(f"❌ Pengajuan Anda ditolak. Catatan: {p.get('catatan_admin', '-')}")
                elif st_verif == "approved":
                    tab_materi, tab_ujian = st.tabs(["📚 Modul Materi LoA", "📝 Ujian Penilaian LoA"])
                    with tab_materi:
                        st.subheader("Modul Materi Pelatihan DG Awareness & Penanganan Kargo Berbahaya")
                        st.markdown("""
                        ## **MODUL LENGKAP: DANGEROUS GOODS AWARENESS**
                        ---
                        ### **1. PENGERTIAN DANGEROUS GOODS**
                        **Dangerous Goods (Barang Berbahaya)** adalah benda atau zat yang berisiko membahayakan kesehatan, keselamatan, aset properti, maupun lingkungan hidup dan keberadaannya ada di dalam daftar barang berbahaya menurut *IATA Dangerous Goods Regulations (DGR)* atau yang diklasifikasikan berdasarkan regulasi tersebut.

                        ### **2. BATASAN BARANG BERBAHAYA (LIMITATION)**
                        Terdapat 3 jenis batasan pengangkutan barang berbahaya melalui udara:
                        1. **Barang Berbahaya yang DILARANG (Forbidden) diangkut dalam keadaan apapun.** Contoh: Bahan peledak cair yang mudah menguap.
                        2. **Barang Berbahaya yang DILARANG diangkut kecuali mendapat pengecualian khusus (Exemption).** Contoh: Material infeksius tingkat tinggi, atau hewan berpenyakit.
                        3. **Barang Berbahaya yang DAPAT diangkut sebagai kargo.** Syaratnya harus mematuhi semua aturan berat, pengemasan, label, dan dokumen DGD (Dangerous Goods Declaration).

                        > **CATATAN KHUSUS SRIWIJAYA AIR & NAM AIR:**
                        > Maskapai PT Sriwijaya Air dan PT NAM Air secara tegas **DILARANG (TIDAK MENERIMA)** pengangkutan Barang Berbahaya Kelas 7 (*Radioactive Material*).
                        
                        ---
                        ### **3. KLASIFIKASI 9 KELAS DANGEROUS GOODS**
                        PBB (United Nations) mengelompokkan bahaya menjadi 9 kelas utama:
                        * **Class 1 - Explosives (Bahan Peledak):** Amunisi, kembang api, suar.
                        * **Class 2 - Gases (Gas):** Dibagi menjadi 2.1 (Gas mudah terbakar - Butana), 2.2 (Gas tidak mudah terbakar & tidak beracun - Oksigen, Nitrogen), 2.3 (Gas Beracun).
                        * **Class 3 - Flammable Liquids (Cairan Mudah Menyala):** Bensin, avtur, alkohol, aseton, cat, parfum cair.
                        * **Class 4 - Flammable Solids (Padatan Mudah Menyala):** Belerang/sulfur, fosfor, logam alkali (seperti kalium).
                        * **Class 5 - Oxidizing & Organic Peroxides:**
                          * 5.1: Bahan Oksidator (Oksigen generator kimia).
                          * 5.2: Peroksida Organik (Hidrogen peroksida, pemutih keras).
                        * **Class 6 - Toxic & Infectious:** 
                          * 6.1: Zat beracun (Sianida, pestisida). 
                          * 6.2: Zat Infeksius (Sampel darah virus/bakteri berbahaya, limbah medis).
                        * **Class 7 - Radioactive Materials:** Uranium, Plutonium, isotop medis. *(TIDAK DIANGKUT SJ/IN).*
                        * **Class 8 - Corrosives (Zat Korosif):** Asam sulfat, air aki, soda api, raksa/merkuri.
                        * **Class 9 - Miscellaneous (Zat Berbahaya Lainnya):** Baterai Lithium (Ion & Metal), kendaraan bertenaga mesin, magnet kuat, *Dry Ice* (Es Kering).

                        ---
                        ### **4. PACKING GROUP (TINGKAT BAHAYA & PENGEMASAN)**
                        Bahan berbahaya dikelompokkan ke dalam 3 *Packing Group (PG)* berdasarkan tingkat keparahan risikonya untuk menentukan ketebalan dan kekuatan kemasan:
                        * **PG I (Great Danger / Bahaya Sangat Tinggi):** Disimbolkan dengan kode pengujian "X". (Contoh: Sianida sangat beracun).
                        * **PG II (Medium Danger / Bahaya Menengah):** Disimbolkan dengan kode pengujian "Y". (Contoh: Bensin).
                        * **PG III (Minor Danger / Bahaya Rendah):** Disimbolkan dengan kode pengujian "Z". (Contoh: Cairan parfum).

                        ---
                        ### **5. LABELING & MARKING**
                        * **Hazard Labels:** Berbentuk belah ketupat (45 derajat), menampilkan simbol bahaya kelas 1-9 (contoh: simbol api merah untuk kelas 3).
                        * **Handling Labels:** Label instruksi penanganan seperti *Cargo Aircraft Only (CAO)*, arah panah *This Way Up*, atau *Cryogenic Liquid*.
                        * **Marking:** Nomor UN (contoh: UN 1863), Proper Shipping Name (PSN), nama & alamat Shipper dan Consignee, berat isi.

                        ---
                        ### **6. TANGGUNG JAWAB OPERASIONAL LOA (Sesuai Role)**
                        * **SHIPPER / PACKER:** Bertanggung jawab penuh atas keabsahan MSDS (*Material Safety Data Sheet*), pengemasan yang menggunakan *UN Specification Packaging*, pelabelan yang akurat, serta mengisi dokumen *Shipper's Declaration for Dangerous Goods (DGD)*.
                        * **ACCEPTANCE (Regulated Agent / Ground Handling):** Melakukan pemeriksaan dokumen (AWB & DGD) dan fisik kargo menggunakan formulir *Dangerous Goods Acceptance Checklist* yang diterbitkan oleh IATA. Kargo yang cacat/bocor harus langsung ditolak (REJECT).
                        * **CARGO LOADER & LOAD MASTER:** Bertanggung jawab dalam penyusunan (*stowing*) dan pemisahan (*segregation*) di perut pesawat (kompartemen). Barang korosif (Class 8) dilarang diletakkan berdampingan dengan benda yang mudah bereaksi, serta barang beracun (Class 6) dilarang berdekatan dengan bahan makanan/hewan hidup. Load Master wajib menyampaikan dokumen **NOTOC (Notice to Captain)** kepada Pilot sebelum *take-off*.

                        ---
                        ### **7. EMERGENCY RESPONSE (PROSEDUR DARURAT)**
                        Jika terjadi tumpahan (spillage) atau insiden kebocoran DG:
                        1. Jauhi tumpahan dan cari posisi yang **Beralawanan Arah Angin** (*upwind*) agar tidak menghirup uap beracun.
                        2. Identifikasi bahan melalui label atau buku MSDS (jika aman).
                        3. Isolasi area (buat parameter keamanan).
                        4. Hubungi tim tanggap darurat bandara (PKP-PK / ARFF).
                        5. Untuk tumpahan zat mudah terbakar (Class 3), taburkan serbuk kayu/pasir/absorbent, **DILARANG menggunakan air** langsung yang dapat menyebarkan api/reaksi. Untuk baterai Lithium yang berasap, segera amankan dari sumber panas.
                        """)
                    with tab_ujian:
                        if str(p.get("status_ujian", "")).strip().lower() == "lulus":
                            st.info(f"🏆 Anda LULUS dengan skor **{p.get('nilai', 0)}/100**. LoA telah terbit di bawah.")
                        else:
                            st.write("Jawab 25 butir pertanyaan berikut dengan teliti. Passing Grade: **≥ 80 poin**.")
                            with st.form(f"form_exam_{p['nomor_induk']}", clear_on_submit=False):
                                answers = {q_item["no"]: st.radio(f"**{q_item['no']}. {q_item['q']}**", ["--Pilih Jawaban--"] + q_item["options"], index=0, key=f"q_{login_id}_{q_item['no']}") for q_item in SOAL_UJIAN_RESMI}
                                if st.form_submit_button("Submit Jawaban Ujian"):
                                    unanswered = [q["no"] for q in SOAL_UJIAN_RESMI if answers[q["no"]] == "--Pilih Jawaban--"]
                                    if unanswered: st.error("Harap jawab semua soal!")
                                    else:
                                        skor_benar = sum(4 for q in SOAL_UJIAN_RESMI if answers[q["no"]] == q["a"])
                                        tgl_skrg = date.today()
                                        if skor_benar >= 80:
                                            update_peserta(login_id, {"status_ujian": "Lulus", "nilai": skor_benar, "tgl_ujian": str(tgl_skrg), "loa_valid_until": str(tgl_skrg + relativedelta(months=24)), "no_loa_in": generate_nomor_loa(df_all, "IN"), "no_loa_sj": generate_nomor_loa(df_all, "SJ")})
                                            st.success(f"🎉 LULUS! Nilai: {skor_benar}/100."); st.rerun()
                                        else:
                                            update_peserta(login_id, {"status_ujian": "Tidak Lulus", "nilai": skor_benar, "tgl_ujian": str(tgl_skrg)})
                                            st.error(f"Nilai Anda {skor_benar}/100 (Passing Grade: 80). Silakan ulangi ujian."); st.rerun()

                    if str(p.get("status_ujian", "")).strip().lower() == "lulus":
                        st.markdown("---")
                        st.header("📄 Download Dokumen Letter of Authorization (LoA) Resmi")
                        st.info("PENTING: File PDF asli ('Template Letter of Authorization Sriwijaya Air.pdf' dan 'Template Letter of Authorization Nam Air.pdf') wajib berada di dalam folder yang sama dengan app.py!")
                        
                        try: valid_date_fmt = datetime.strptime(str(p["loa_valid_until"]), "%Y-%m-%d").date().strftime("%d/%m/%Y")
                        except: valid_date_fmt = str(p.get("loa_valid_until", "-"))
                        try: tgl_terbit_fmt = format_tgl_inggris(datetime.strptime(str(p["tgl_ujian"]), "%Y-%m-%d").date() if p.get("tgl_ujian") else date.today())
                        except: tgl_terbit_fmt = format_tgl_inggris(date.today())

                        col_sj, col_in = st.columns(2)
                        with col_sj:
                            if os.path.exists("Template Letter of Authorization Sriwijaya Air.pdf"):
                                pdf_sj_bytes = create_pdf_loa("Template Letter of Authorization Sriwijaya Air.pdf", p, "SJ", valid_date_fmt, tgl_terbit_fmt)
                                if pdf_sj_bytes: st.download_button("📥 Download LoA Sriwijaya Air (PDF)", data=pdf_sj_bytes, file_name=f"LoA_Sriwijaya_{p.get('nik_emp')}.pdf", mime="application/pdf")
                                else: st.error("Gagal melakukan stamp ke template PDF Sriwijaya.")
                            else: st.warning("File 'Template Letter of Authorization Sriwijaya Air.pdf' tidak ditemukan di direktori lokal.")

                        with col_in:
                            if os.path.exists("Template Letter of Authorization Nam Air.pdf"):
                                pdf_in_bytes = create_pdf_loa("Template Letter of Authorization Nam Air.pdf", p, "IN", valid_date_fmt, tgl_terbit_fmt)
                                if pdf_in_bytes: st.download_button("📥 Download LoA NAM Air (PDF)", data=pdf_in_bytes, file_name=f"LoA_NAM_{p.get('nik_emp')}.pdf", mime="application/pdf")
                                else: st.error("Gagal melakukan stamp ke template PDF NAM Air.")
                            else: st.warning("File 'Template Letter of Authorization Nam Air.pdf' tidak ditemukan di direktori lokal.")

elif sub_menu == "4. Laporan Evaluasi Assessment":
    st.title("Tahap 4: Laporan Evaluasi Assessment Personil LoA")
    if df_all.empty or "status_verifikasi" not in df_all.columns: st.info("Belum ada data peserta.")
    else:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Personil", len(df_all))
        c2.metric("Lolos Verifikasi", len(df_all[df_all["status_verifikasi"].astype(str).str.lower() == "approved"]))
        c3.metric("Lulus Assessment", len(df_all[df_all["status_ujian"].astype(str).str.lower() == "lulus"]))
        c4.metric("Belum Lulus", len(df_all[df_all["status_ujian"].astype(str).str.lower() == "tidak lulus"]))

        av_cols = [c for c in ["nomor_induk", "nama", "nik_emp", "perusahaan", "kategori", "role", "distrik", "status_verifikasi", "nilai", "status_ujian", "loa_valid_until", "no_loa_in", "no_loa_sj"] if c in df_all.columns]
        st.dataframe(df_all[av_cols])
        
        output_excel = io.BytesIO()
        with pd.ExcelWriter(output_excel, engine="openpyxl") as writer: df_all[av_cols].to_excel(writer, index=False, sheet_name="Laporan_LoA")
        st.download_button("📥 Ekspor Laporan .XLSX", data=output_excel.getvalue(), file_name="Laporan_Evaluasi_LoA.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        
        st.markdown("---")
        st.subheader("🗑️ Hapus Data Trial")
        del_p = st.selectbox("Pilih Nomor Induk:", df_all["nomor_induk"].tolist())
        if st.button("🗑️ Hapus Permanen Data Peserta Ini"):
            if delete_peserta_trial(del_p): st.success("Data terhapus!"); st.cache_data.clear(); st.rerun()
            else: st.error("Gagal menghapus data.")

elif sub_menu == "5. Dashboard Admin & Records (Reminder)":
    st.title("Dashboard Admin & Records Monitoring")
    sel_dist = st.selectbox("🔍 Filter Data Distrik:", ["Semua Distrik"] + st.session_state.db_distrik)
    df_f = df_all[df_all["distrik"] == sel_dist] if sel_dist != "Semua Distrik" else df_all.copy()

    st.subheader("🔔 Peringatan Kedaluwarsa LoA (≤ 30 Hari)")
    rem_list = []
    if not df_f.empty and "loa_valid_until" in df_f.columns:
        for _, p in df_f[(df_f["status_ujian"].str.lower() == "lulus") & df_f["loa_valid_until"].notna()].iterrows():
            try:
                s_hari = (datetime.strptime(str(p["loa_valid_until"]).strip(), "%Y-%m-%d").date() - date.today()).days
                if s_hari <= 30: rem_list.append({"Nomor Induk": p.get("nomor_induk"), "Nama": p.get("nama"), "Distrik": p.get("distrik"), "Sisa Hari": f"{s_hari} hari" if s_hari >= 0 else "EXPIRED"})
            except: pass
    if rem_list: st.error(f"Perhatian: Ada {len(rem_list)} personil segera expired!"); st.dataframe(pd.DataFrame(rem_list))
    else: st.success("✅ Seluruh LoA personil dalam kondisi aman (> 30 hari).")

    st.markdown("---")
    st.subheader("Master Records (Status Valid/Expired)")
    if not df_f.empty:
        df_f["Status_LoA"] = ["Expired / Belum Terbit" if not str(r.get("loa_valid_until", "")).strip() else ("Valid" if datetime.strptime(str(r["loa_valid_until"]).strip(), "%Y-%m-%d").date() >= date.today() else "Expired") for _, r in df_f.iterrows()]
    st.dataframe(df_f)

elif sub_menu == "6. Master Distrik & Jadwal Recurrent":
    st.title("Master Distrik & Jadwal Recurrent")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("➕ Tambah Distrik Baru")
        with st.form("form_tambah"):
            n_dist = st.text_input("Nama Distrik (BPN - Balikpapan):").strip()
            if st.form_submit_button("Simpan Distrik") and n_dist:
                if n_dist not in st.session_state.db_distrik:
                    st.session_state.db_distrik.append(n_dist); save_distrik(st.session_state.db_distrik); st.rerun()
                else: st.warning("Distrik sudah ada.")
        st.subheader("Daftar Distrik:")
        for d in st.session_state.db_distrik: st.markdown(f"- ✈️ `{d}`")
        st.markdown("---")
        with st.form("form_hapus"):
            d_dist = st.selectbox("Hapus Distrik:", st.session_state.db_distrik)
            if st.form_submit_button("Hapus") and len(st.session_state.db_distrik) > 1:
                st.session_state.db_distrik.remove(d_dist); save_distrik(st.session_state.db_distrik); st.rerun()

    with c2:
        st.subheader("📅 Jadwal Recurrent")
        if "db_jadwal_loa" not in st.session_state: st.session_state.db_jadwal_loa = [{"distrik": "CGK - Jakarta", "tanggal": "2026-11-20", "kuota": 30, "lokasi": "Soetta"}]
        st.dataframe(pd.DataFrame(st.session_state.db_jadwal_loa))
        with st.form("form_jadwal"):
            d_in = st.selectbox("Pilih Distrik:", st.session_state.db_distrik)
            t_in = st.date_input("Tanggal Pelaksanaan:", min_value=date.today())
            k_in = st.number_input("Kuota:", min_value=5, value=25)
            l_in = st.text_input("Lokasi:")
            if st.form_submit_button("Simpan Jadwal"):
                st.session_state.db_jadwal_loa.append({"distrik": d_in, "tanggal": str(t_in), "kuota": k_in, "lokasi": l_in}); st.rerun()