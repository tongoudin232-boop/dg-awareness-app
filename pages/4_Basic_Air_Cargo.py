import streamlit as st
import pandas as pd
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
import io
import os
import zipfile
import json
import time
import textwrap

# Impor library PDF (Eksklusif untuk cetak sertifikat Basic Cargo di sini)
try:
    from PyPDF2 import PdfReader, PdfWriter, Transformation
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
except ImportError:
    st.error("⚠️ Library 'PyPDF2' dan 'reportlab' belum terinstall.")
    st.stop()

# Impor Google Sheets API
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# Impor fungsi absensi dari file pendukung Anda 
try:
    from attendance_generator import generate_attendance_pdf, generate_attendance_excel
except ImportError:
    st.error("Gagal mengimpor fungsi dari 'attendance_generator.py'. Pastikan file tersebut ada.")

# ==================== KONFIGURASI HALAMAN ====================
st.set_page_config(
    page_title="Basic Air Cargo - SJ & IN",
    layout="wide",
    page_icon="✈️",
    initial_sidebar_state="expanded"
)

# ==================== KONTROL TAMPILAN HEADER & MOBILE ====================
st.markdown(
    """
    <style>
    [data-testid="stHeader"] { min-height: 4.5rem !important; background: transparent !important; }
    [data-testid="stToolbarActions"], .stAppDeployButton, #MainMenu { opacity: 0 !important; pointer-events: none !important; }
    [data-testid="collapsedControl"] {
        display: flex !important; visibility: visible !important; opacity: 1 !important;
        background-color: #0b1d3a !important; border-radius: 8px !important;
        padding: 5px !important; margin-top: 5px !important; margin-left: 5px !important; z-index: 999999 !important;
    }
    [data-testid="collapsedControl"] svg { fill: #ffffff !important; color: #ffffff !important; }
    [class*="viewerBadge"] { display: none !important; }
    [data-testid="stSidebarNav"] ul li:first-child { display: none !important; }
    [data-testid="stDecoration"], footer { display: none !important; }
    </style>
    """,
    unsafe_allow_html=True
)

# ==================== SISTEM DATABASE EKSKLUSIF BASIC CARGO ====================
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

TAB_NAME_BASIC = "Training_Records_Basic"
LOCAL_DB_BASIC = "basic_records.json"
SHEET_COLUMNS_BASIC = ["id", "training_date", "full_name", "nik", "phone", "job_role", "company", "district", "district_name", "district_full", "score", "status", "cert_no_sj", "cert_no_in", "expiry_date", "jawaban_ujian"]

LOCAL_DISTRICTS_BASIC = "districts_basic.json"
SHEET_COLUMNS_DISTRICTS = ["id", "code", "name", "category", "last_training_date", "next_due_date"]

SPREADSHEET_ID_FIXED = "1wr7CAll_gMDTjyK6yeScysAkOLcgogFyXYFXt7cFrs"

def get_credentials():
    try:
        creds_info = dict(st.secrets["gcp_service_account"]) if "gcp_service_account" in st.secrets else dict(st.secrets)
        if not creds_info or "private_key" not in creds_info: return None
        creds_info["private_key"] = str(creds_info["private_key"]).replace("\\n", "\n").replace("\n", "\n").strip()
        return Credentials.from_service_account_info(creds_info, scopes=SCOPES)
    except: return None

def init_google_sheets():
    creds = get_credentials()
    if not creds: return None, None
    try:
        s_sht = build("sheets", "v4", credentials=creds, cache_discovery=False)
        return s_sht, SPREADSHEET_ID_FIXED
    except: return None, None

service_sheets, SPREADSHEET_ID = init_google_sheets()

# FUNGSI PINTAR: DETEKSI NAMA TAB DISTRIK OTOMATIS DARI GOOGLE SHEETS
def get_actual_district_tab_name():
    if service_sheets and SPREADSHEET_ID:
        try:
            meta = service_sheets.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
            sheets = meta.get('sheets', [])
            for s in sheets:
                title = s.get('properties', {}).get('title', '')
                if 'district' in title.lower() and 'basic' in title.lower():
                    return title
        except: pass
    return "districts_basic"

TAB_DISTRICTS_BASIC = get_actual_district_tab_name()

# ---------------- FUNGSI DISTRIK BASIC CARGO ----------------
def get_districts_basic():
    tab_target = get_actual_district_tab_name()
    if service_sheets and SPREADSHEET_ID:
        try:
            r = service_sheets.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID, range=f"{tab_target}!A1:F").execute()
            v = r.get("values", [])
            if v and len(v) > 1:
                df = pd.DataFrame(v[1:], columns=v[0])
                for col in SHEET_COLUMNS_DISTRICTS:
                    if col not in df.columns: df[col] = ""
                try: df.to_json(LOCAL_DISTRICTS_BASIC, orient="records", force_ascii=False)
                except: pass
                return df
        except Exception as e:
            st.warning(f"⚠️ Gagal sinkron Google Sheets: {e}")
            
    if os.path.exists(LOCAL_DISTRICTS_BASIC):
        try:
            df = pd.read_json(LOCAL_DISTRICTS_BASIC, orient="records")
            if not df.empty: return df
        except: pass
        
    return pd.DataFrame(columns=SHEET_COLUMNS_DISTRICTS)

def add_district_basic(code, name, category):
    tab_target = get_actual_district_tab_name()
    df = get_districts_basic()
    new_id = 1
    if not df.empty and 'id' in df.columns:
        ids = pd.to_numeric(df['id'], errors='coerce').dropna()
        if not ids.empty: new_id = int(ids.max()) + 1
        
    if service_sheets and SPREADSHEET_ID:
        try:
            rv = [str(new_id), code, name, category, "", ""]
            service_sheets.spreadsheets().values().append(
                spreadsheetId=SPREADSHEET_ID, range=f"{tab_target}!A1",
                valueInputOption="USER_ENTERED", insertDataOption="INSERT_ROWS", body={"values": [rv]}
            ).execute()
        except: pass
        
    new_row = {"id": new_id, "code": code, "name": name, "category": category, "last_training_date": "", "next_due_date": ""}
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    try: df.to_json(LOCAL_DISTRICTS_BASIC, orient="records", force_ascii=False)
    except: pass
    return True

def update_district_row_basic(dist_id, code, name, category, last_date, next_date):
    tab_target = get_actual_district_tab_name()
    if service_sheets and SPREADSHEET_ID:
        try:
            r = service_sheets.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID, range=f"{tab_target}!A1:F").execute()
            v = r.get("values", [])
            ri = -1
            for i, row in enumerate(v):
                if row and str(row[0]).strip() == str(dist_id).strip(): ri = i + 1; break
            if ri != -1:
                service_sheets.spreadsheets().values().update(
                    spreadsheetId=SPREADSHEET_ID, range=f"{tab_target}!B{ri}:F{ri}",
                    valueInputOption="USER_ENTERED", body={"values": [[code, name, category, last_date, next_date]]}
                ).execute()
        except: pass
    return True

def delete_district_row_basic(dist_id):
    tab_target = get_actual_district_tab_name()
    if service_sheets and SPREADSHEET_ID:
        try:
            r = service_sheets.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID, range=f"{tab_target}!A1:A").execute()
            v = r.get("values", [])
            ri = -1
            for i, row in enumerate(v):
                if row and str(row[0]).strip() == str(dist_id).strip(): ri = i; break
            if ri != -1:
                sm = service_sheets.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
                sid = next((s["properties"]["sheetId"] for s in sm.get("sheets", []) if s["properties"]["title"] == tab_target), None)
                if sid is not None:
                    service_sheets.spreadsheets().batchUpdate(
                        spreadsheetId=SPREADSHEET_ID, 
                        body={"requests": [{"deleteDimension": {"range": {"sheetId": sid, "dimension": "ROWS", "startIndex": ri, "endIndex": ri + 1}}}]}
                    ).execute()
        except: pass
    return True

# ---------------- FUNGSI RECORD TRAINING (BASIC CARGO) ----------------
def load_basic_records():
    if service_sheets and SPREADSHEET_ID:
        try:
            r = service_sheets.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID, range=f"{TAB_NAME_BASIC}!A1:Z").execute()
            v = r.get("values", [])
            df = pd.DataFrame(columns=SHEET_COLUMNS_BASIC)
            if v and len(v) > 1:
                h = v[0]
                c_r = [row + [""] * (len(h) - len(row)) for row in v[1:]]
                df = pd.DataFrame(c_r, columns=h)
                for col in SHEET_COLUMNS_BASIC:
                    if col not in df.columns: df[col] = ""
            return df
        except: pass 
    if os.path.exists(LOCAL_DB_BASIC):
        try:
            with open(LOCAL_DB_BASIC, "r", encoding="utf-8") as f: 
                data = json.load(f)
                return pd.DataFrame(data) if data else pd.DataFrame(columns=SHEET_COLUMNS_BASIC)
        except: pass
    return pd.DataFrame(columns=SHEET_COLUMNS_BASIC)

def save_basic_record(payload):
    if service_sheets and SPREADSHEET_ID:
        try:
            rv = [str(payload.get(c, ""))[:49000] for c in SHEET_COLUMNS_BASIC]
            service_sheets.spreadsheets().values().append(spreadsheetId=SPREADSHEET_ID, range=f"{TAB_NAME_BASIC}!A1", valueInputOption="USER_ENTERED", insertDataOption="INSERT_ROWS", body={"values": [rv]}).execute()
        except: pass
    local_data = []
    if os.path.exists(LOCAL_DB_BASIC):
        try:
            with open(LOCAL_DB_BASIC, "r", encoding="utf-8") as f: local_data = json.load(f)
        except: pass
    local_data.append(payload)
    try:
        with open(LOCAL_DB_BASIC, "w", encoding="utf-8") as f: json.dump(local_data, f, ensure_ascii=False, indent=4)
    except: pass
    return True

def get_next_cert_number_basic(airline, df_records):
    today = date.today()
    romawi = {1: "I", 2: "II", 3: "III", 4: "IV", 5: "V", 6: "VI", 7: "VII", 8: "VIII", 9: "IX", 10: "X", 11: "XI", 12: "XII"}.get(today.month, "I")
    cn = "cert_no_in" if airline == "IN" else "cert_no_sj"
    limit_date = today - relativedelta(months=24)
    valid_count = 0
    if not df_records.empty and cn in df_records.columns and 'training_date' in df_records.columns:
        for _, row in df_records.iterrows():
            if pd.notna(row[cn]) and str(row[cn]).strip() not in ["", "-"]:
                try:
                    tgl_str = str(row['training_date']).strip()
                    if tgl_str:
                        t_date = datetime.strptime(tgl_str[:10], "%Y-%m-%d").date()
                        if t_date >= limit_date: valid_count += 1
                except: pass
    return f"{(valid_count + 1):04d}/BC/{airline}-CGO/{romawi}/{today.year}"

# ==================== GENERATOR SERTIFIKAT KHUSUS BASIC CARGO ====================
def generate_cert_basic(airline, cert_no, name, training_date_str):
    template_name = "Template_Basic_SJ.pdf" if airline == "SJ" else "Template_Basic_IN.pdf"
    if not os.path.exists(template_name): return None
    
    try:
        existing_pdf = PdfReader(open(template_name, "rb"))
        page = existing_pdf.pages[0]
        orig_w, orig_h = float(page.mediabox.width), float(page.mediabox.height)
    except: return None

    a4_w, a4_h = landscape(A4)
    scale_x, scale_y = a4_w / orig_w, a4_h / orig_h
    try: page.add_transformation(Transformation().scale(sx=scale_x, sy=scale_y)); page.mediabox.upper_right = (a4_w, a4_h)
    except: pass 

    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=(a4_w, a4_h))
    can.setFillColorRGB(0, 0, 0)
    
    font_utama = "Times-Bold"
    try:
        if os.path.exists("Alice-Bold.ttf"): pdfmetrics.registerFont(TTFont('Alice', 'Alice-Bold.ttf')); font_utama = "Alice"
    except: pass

    try: 
        tgl_obj = datetime.strptime(str(training_date_str)[:10], "%Y-%m-%d").date()
        valid_dt = (tgl_obj + relativedelta(months=24)).strftime("%d/%m/%Y")
        day = tgl_obj.day
        if 11 <= day <= 13: suffix = "th"
        else: suffix = {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
        bulan_en = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"][tgl_obj.month - 1]
        tgl_terbit_fmt = f"Tangerang, {bulan_en} {day}{suffix} {tgl_obj.year}"
    except: 
        valid_dt = str(training_date_str)
        tgl_terbit_fmt = f"Tangerang, {str(training_date_str)}"

    can.setFont(font_utama, 14) 
    can.drawCentredString(a4_w * 0.5, a4_h * 0.85, f"No: {cert_no}")
    can.setFont(font_utama, 24)
    can.drawCentredString(a4_w * 0.5, a4_h * 0.55, f"{str(name).upper()}")
    
    can.setFont("Helvetica-Bold", 12)
    can.drawCentredString(a4_w * 0.15, a4_h * 0.15, f"VALID UNTIL: {valid_dt}")
    can.drawCentredString(a4_w * 0.85, a4_h * 0.30, f"{tgl_terbit_fmt}")
    
    verify_url = f"https://sjnam-cargo.streamlit.app/Basic_Air_Cargo?basic_cert={cert_no}"
    try:
        import qrcode
        qr = qrcode.QRCode(version=1, box_size=4, border=2) 
        qr.add_data(verify_url)
        qr.make(fit=True)
        qr_bytes = io.BytesIO()
        qr.make_image(fill_color="black", back_color="white").convert('RGB').save(qr_bytes, format="PNG")
        qr_bytes.seek(0)
        
        qr_size = a4_w * 0.11 
        qr_x = (a4_w * 0.85) - (qr_size / 2) 
        qr_y = a4_h * 0.12 
        can.drawImage(ImageReader(qr_bytes), qr_x, qr_y, width=qr_size, height=qr_size, mask=[250, 255, 250, 255, 250, 255])
    except: pass
        
    can.save()
    packet.seek(0)
    page.merge_page(PdfReader(packet).pages[0])

    try:
        output = PdfWriter()
        output.add_page(page)
        final_pdf = io.BytesIO()
        output.write(final_pdf)
        return final_pdf.getvalue()
    except: return None

# ==================== DAFTAR SOAL BASIC CARGO ====================
SOAL_UJIAN_BASIC_CARGO = [
    {"no": 1, "q": "Apa yang dimaksud dengan Kargo (Cargo) udara?", "options": ["a) Penumpang yang membawa barang banyak", "b) Semua barang kiriman via udara, laut/darat yang dilengkapi dokumen pengangkutan", "c) Bagasi bawaan penumpang di kabin", "d) Barang ilegal yang disita bandara"], "a": "b) Semua barang kiriman via udara, laut/darat yang dilengkapi dokumen pengangkutan"},
    {"no": 2, "q": "Secara umum, kargo dibagi menjadi dua kategori utama, yaitu:", "options": ["a) Normal Cargo & Abnormal Cargo", "b) Domestic Cargo & International Cargo", "c) General Cargo & Special Cargo", "d) Safe Cargo & Dangerous Cargo"], "a": "c) General Cargo & Special Cargo"},
    {"no": 3, "q": "Barang-barang umum yang tidak membutuhkan penanganan secara khusus (special handling) disebut?", "options": ["a) Special Cargo", "b) Dangerous Goods", "c) General Cargo", "d) Valuable Cargo"], "a": "c) General Cargo"},
    {"no": 4, "q": "Kiriman yang membutuhkan penanganan khusus dari sisi penerimaan, penyimpanan, maupun pengangkutan disebut?", "options": ["a) Special Cargo", "b) General Cargo", "c) Regular Cargo", "d) Normal Goods"], "a": "a) Special Cargo"},
    {"no": 5, "q": "Barang yang mudah rusak, hancur, atau busuk seperti daging, sayuran, dan vaksin masuk ke dalam kategori?", "options": ["a) Wet Cargo", "b) Perishable Cargo", "c) Heavy Cargo", "d) Fragile Cargo"], "a": "b) Perishable Cargo"},
    {"no": 6, "q": "Barang yang mengandung cairan atau memiliki sifat dapat mengeluarkan air (contoh: ikan hidup dalam air) diklasifikasikan sebagai?", "options": ["a) Perishable Cargo", "b) Liquid Cargo", "c) Wet Cargo", "d) Damp Cargo"], "a": "c) Wet Cargo"},
    {"no": 7, "q": "Syarat utama pengiriman Electronic Goods (seperti Handphone dan Laptop) melalui kargo udara adalah?", "options": ["a) Harus baterai kosong", "b) Wajib dalam kondisi baru", "c) Boleh kondisi bekas pakai", "d) Harus dibungkus plastik hitam"], "a": "b) Wajib dalam kondisi baru"},
    {"no": 8, "q": "Pengiriman hewan hidup seperti mamalia, burung, dan reptil melalui pesawat udara disebut?", "options": ["a) Wildlife Cargo", "b) Live Animal Cargo", "c) Zoo Cargo", "d) Pet Cargo"], "a": "b) Live Animal Cargo"},
    {"no": 9, "q": "Surat resmi antar pemerintah atau dokumen rahasia kedutaan yang ditandai dan disegel resmi termasuk kategori?", "options": ["a) Diplomatic Pouch", "b) Top Secret Cargo", "c) Government Mail", "d) Valuable Cargo"], "a": "a) Diplomatic Pouch"},
    {"no": 10, "q": "Valuable Cargo adalah barang yang memiliki nilai sesungguhnya (value) lebih dari ... per kilogram.", "options": ["a) $ 100", "b) $ 500", "c) $ 1.000", "d) $ 10.000"], "a": "c) $ 1.000"},
    {"no": 11, "q": "Batas berat minimum untuk sebuah barang agar dikategorikan sebagai Heavy Cargo adalah?", "options": ["a) > 25 Kg per Koli", "b) > 50 Kg per Koli", "c) > 75 Kg per Koli", "d) > 100 Kg per Koli"], "a": "c) > 75 Kg per Koli"},
    {"no": 12, "q": "Pengiriman jenazah, kerangka manusia, maupun abu kremasi masuk ke dalam penanganan khusus kategori?", "options": ["a) Human Remains", "b) Medical Cargo", "c) Biological Cargo", "d) Perishable Cargo"], "a": "a) Human Remains"},
    {"no": 13, "q": "Berapa jumlah total kelas (Class) Dangerous Goods menurut standar internasional IATA?", "options": ["a) 7 Kelas", "b) 8 Kelas", "c) 9 Kelas", "d) 10 Kelas"], "a": "c) 9 Kelas"},
    {"no": 14, "q": "Bahan yang memiliki bahaya ledakan besar (Mass explosion hazards) seperti amunisi, termasuk dalam DG Kelas?", "options": ["a) Class 1", "b) Class 2", "c) Class 3", "d) Class 4"], "a": "a) Class 1"},
    {"no": 15, "q": "Gas oksigen, aerosol, dan gas karbondioksida diklasifikasikan ke dalam Dangerous Goods kelas?", "options": ["a) Class 1 (Explosive)", "b) Class 2 (Gases)", "c) Class 3 (Flammable Liquid)", "d) Class 8 (Corrosive)"], "a": "b) Class 2 (Gases)"},
    {"no": 16, "q": "Cairan yang mudah terbakar (Flammable Liquid) seperti bensin dan parfum adalah DG kelas?", "options": ["a) Class 2", "b) Class 3", "c) Class 4", "d) Class 5"], "a": "b) Class 3"},
    {"no": 17, "q": "Zat beracun dan menular (Toxic & Infectious Substances) seperti sampel virus dan sianida termasuk dalam kelas?", "options": ["a) Class 4", "b) Class 5", "c) Class 6", "d) Class 7"], "a": "c) Class 6"},
    {"no": 18, "q": "Bahan yang memancarkan radiasi berbahaya (Radioactive Material) seperti Uranium termasuk ke dalam kelas?", "options": ["a) Class 5", "b) Class 6", "c) Class 7", "d) Class 9"], "a": "c) Class 7"},
    {"no": 19, "q": "Asam sulfat dan air aki yang dapat menyebabkan kerusakan atau korosif pada benda lain termasuk ke dalam DG Kelas?", "options": ["a) Class 6", "b) Class 7", "c) Class 8", "d) Class 9"], "a": "c) Class 8"},
    {"no": 20, "q": "Baterai Lithium dan kendaraan bermotor bermagnet masuk ke dalam kategori Miscellaneous Material yaitu kelas?", "options": ["a) Class 6", "b) Class 7", "c) Class 8", "d) Class 9"], "a": "d) Class 9"},
    {"no": 21, "q": "Berdasarkan urutan Prioritas Muatan di pesawat (Cargo Priority Onboard), kargo apa yang menempati urutan PERTAMA (Paling Prioritas)?", "options": ["a) Live Animal", "b) Human Remains", "c) Aircraft on Ground (AOG) Sparepart", "d) Valuable Goods"], "a": "c) Aircraft on Ground (AOG) Sparepart"},
    {"no": 22, "q": "Kargo manakah yang menempati prioritas KEDUA setelah AOG Sparepart untuk dimuat ke dalam pesawat?", "options": ["a) Live Animal", "b) Human Remains", "c) Perishable Goods", "d) General Cargo"], "a": "b) Human Remains"},
    {"no": 23, "q": "Dalam urutan prioritas muatan, kargo jenis apakah yang menempati urutan paling akhir (Urutan ke-8)?", "options": ["a) Premium Product", "b) Valuable Goods", "c) Cargo Ex Offload", "d) General Cargo"], "a": "d) General Cargo"},
    {"no": 24, "q": "Manakah di bawah ini yang BUKAN merupakan dokumen persyaratan pengiriman Cargo?", "options": ["a) Surat Izin Mengemudi (SIM)", "b) SMU / Air Waybill", "c) Pemberitahuan Tentang Isi (PTI)", "d) Consignment Security Declaration (CSD)"], "a": "a) Surat Izin Mengemudi (SIM)"},
    {"no": 25, "q": "Dokumen NOTOC biasanya digunakan dalam pengiriman kargo tertentu. NOTOC merupakan singkatan dari?", "options": ["a) Notice To Captain", "b) Notice Of Transfer Or Cargo", "c) Notice To Operation Control", "d) Note Of Cargo"], "a": "a) Notice To Captain"}
]

# State & Inisialisasi
if "is_instructor_bc" not in st.session_state: st.session_state["is_instructor_bc"] = False
if "current_page_bc" not in st.session_state: st.session_state["current_page_bc"] = "Modul Materi Basic Cargo"

CATEGORY_OPTIONS = ["Sriwijaya Air", "NAM Air", "Regulated Agent", "Mitra Cargo", "Warehouse", "Jaster"]
JOB_ROLES = ["Staf Kargo / Cargo Officer", "Porter / Cargo Loader", "Loadmaster / Load Control", "Supervisor / Duty Manager", "Frontliner", "Pasasi / Passenger Service", "Security Avsec", "Lainnya"]

# ==================== VERIFIKASI QR CODE BASIC CARGO ====================
query_params = st.query_params
if "basic_cert" in query_params:
    cert_query = str(query_params["basic_cert"]).strip()
    records_df = load_basic_records()
    matched = pd.DataFrame()

    if not records_df.empty:
        def clean_cert_val(val):
            if pd.isna(val) or val is None: return ""
            s = str(val).strip()
            if s.endswith(".0"): s = s[:-2]
            return s
        df_check = records_df.copy()
        df_check['clean_sj'] = df_check['cert_no_sj'].apply(clean_cert_val)
        df_check['clean_in'] = df_check['cert_no_in'].apply(clean_cert_val)
        matched = df_check[(df_check['clean_sj'] == cert_query) | (df_check['clean_in'] == cert_query)]

    col_vlogo1, col_vtitle, col_vlogo2 = st.columns([1.5, 5, 1.5])
    with col_vlogo1:
        if os.path.exists("logo_sriwijaya.png"): st.image("logo_sriwijaya.png", use_container_width=True)
    with col_vtitle:
        st.markdown(
            """
            <div style="text-align: center; padding: 10px 0;">
                <h1 style="color: #0E3B68; margin-bottom: 0px;">✈️ Portal Verifikasi Sertifikat</h1>
                <h4 style="color: #6C757D; margin-top: 5px;">Basic Air Cargo Training - SJ & NAM</h4>
            </div>
            """, unsafe_allow_html=True
        )
    with col_vlogo2:
        if os.path.exists("logo_namair.png"): st.image("logo_namair.png", use_container_width=True)

    st.markdown("<hr style='border: 1px solid #E0E0E0;'>", unsafe_allow_html=True)

    if not matched.empty:
        rec = matched.iloc[0]
        st.success("✅ **SERTIFIKAT RESMI TERVERIFIKASI & TERCATAT DI DATABASE (VALID)**")
        col_v1, col_v2 = st.columns(2)
        with col_v1:
            st.markdown(f"**Nama Peserta:** {rec['full_name']}")
            st.markdown(f"**NIK / Employee ID:** {rec['nik']}")
            st.markdown(f"**Perusahaan:** {rec['company']}")
            st.markdown(f"**Jabatan / Posisi:** {rec['job_role']}")
        with col_v2:
            st.markdown(f"**Distrik Pelaksanaan:** {rec['district']}")
            st.markdown(f"**Tanggal Training:** {rec['training_date']}")
            st.markdown(f"**No. Sertifikat Sriwijaya Air:** `{rec['cert_no_sj']}`")
            st.markdown(f"**No. Sertifikat NAM Air:** `{rec['cert_no_in']}`")

        st.markdown("---")
        st.subheader("Salinan Resmi Dokumen")
        clean_sj_val = clean_cert_val(rec['cert_no_sj'])
        airline_target = "SJ" if clean_sj_val == cert_query else "IN"
        airline_name = "Sriwijaya Air" if airline_target == "SJ" else "NAM Air"
        try:
            cert_pdf = generate_cert_basic(airline_target, str(cert_query), str(rec['full_name']), str(rec['training_date']))
            if cert_pdf:
                st.download_button(
                    label=f"📥 Unduh Salinan Sertifikat {airline_name} ({airline_target})",
                    data=cert_pdf,
                    file_name=f"Salinan_Basic_Cargo_{rec['full_name']}_{airline_target}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
            else: st.warning(f"File Template_Basic_{airline_target}.pdf tidak ditemukan di server.")
        except Exception as e: st.error(f"Gagal memuat salinan sertifikat: {e}")
    else:
        st.error("❌ **DATA SERTIFIKAT TIDAK DITEMUKAN!**")
        st.warning(f"Nomor sertifikat '{cert_query}' tidak terdaftar pada sistem database Basic Cargo.")
    st.stop()


# ==================== SISTEM AKSES INSTRUKTUR (SIDEBAR) ====================
if os.path.exists("logo_sriwijaya.png"): st.sidebar.image("logo_sriwijaya.png", use_container_width=True)
st.sidebar.title("Navigasi Utama")

if st.session_state["is_instructor_bc"]:
    menu_options = ["Modul Materi Basic Cargo", "Ujian Basic Cargo", "Dashboard Instruktur & Records", "Master Distrik & Jadwal Recurrent"]
    cur_idx = menu_options.index(st.session_state["current_page_bc"]) if st.session_state["current_page_bc"] in menu_options else 0
    selected_menu = st.sidebar.radio("Navigasi Menu", menu_options, index=cur_idx)
    st.session_state["current_page_bc"] = selected_menu
    st.sidebar.markdown("---")
    if st.sidebar.button("🔒 Logout Instruktur"):
        st.session_state["is_instructor_bc"] = False
        st.session_state["current_page_bc"] = "Modul Materi Basic Cargo"
        st.rerun()
else:
    participant_options = ["Modul Materi Basic Cargo", "Ujian Basic Cargo"]
    p_idx = participant_options.index(st.session_state["current_page_bc"]) if st.session_state["current_page_bc"] in participant_options else 0
    selected_p = st.sidebar.radio("Pilih Menu:", participant_options, index=p_idx)
    st.session_state["current_page_bc"] = selected_p

    with st.sidebar.expander("🔐 Akses Khusus Instruktur", expanded=False):
        instructor_pin = st.text_input("Masukkan PIN Instruktur:", type="password")
        if st.button("Masuk"):
            if instructor_pin == "Indomiesoto1":
                st.session_state["is_instructor_bc"] = True; st.success("Login berhasil!"); st.rerun()
            else: st.error("PIN salah!")

if not st.session_state["is_instructor_bc"]:
    nav_c1, nav_c2 = st.columns(2)
    with nav_c1:
        if st.button("📘 Baca Modul Materi", use_container_width=True, type="primary" if st.session_state["current_page_bc"] == "Modul Materi Basic Cargo" else "secondary"):
            st.session_state["current_page_bc"] = "Modul Materi Basic Cargo"; st.rerun()
    with nav_c2:
        if st.button("✍️ Kerjakan Ujian Basic Air Cargo", use_container_width=True, type="primary" if st.session_state["current_page_bc"] == "Ujian Basic Cargo" else "secondary"):
            st.session_state["current_page_bc"] = "Ujian Basic Cargo"; st.rerun()
    st.markdown("<hr style='margin-top: 5px; margin-bottom: 20px;'>", unsafe_allow_html=True)

menu = st.session_state["current_page_bc"]

# ==================== MENU 1: MODUL MATERI BASIC CARGO ====================
if menu == "Modul Materi Basic Cargo":
    st.markdown(
        """
        <div style="background-color: #1A406B; padding: 25px; border-radius: 10px; color: white; margin-bottom: 20px;">
            <h2 style="margin-top: 0; color: white;">Modul Pelatihan Basic Air Cargo</h2>
            <p style="margin-bottom: 5px;">Panduan Komprehensif Dasar-Dasar Kargo Udara — Sriwijaya Air & NAM Air Cargo</p>
            <p style="font-size: 0.9em; opacity: 0.8; margin-bottom: 0;">Instruktur: Hadi Nurhuda | Edisi: 2026</p>
        </div>
        <div style="background-color: #e6f2ff; padding: 15px; border-radius: 8px; border-left: 5px solid #0066cc; margin-bottom: 20px;">
            💡 <strong>Petunjuk Belajar Peserta:</strong> Pelajari seluruh materi pada tab di bawah ini sebelum memulai Ujian Basic Cargo. Passing grade kelulusan adalah <strong>≥ 80 poin</strong>.
        </div>
        """, unsafe_allow_html=True
    )
    
    t1, t2, t3, t4 = st.tabs(["1. Definisi & Jenis Kargo", "2. Rincian Special Cargo", "3. 9 Kelas Dangerous Goods", "4. Prioritas & Dokumen"])
    
    with t1:
        st.subheader("1. Definisi Cargo")
        st.write("Kargo adalah semua barang (goods) yang dikirim melalui udara, laut, atau darat baik antar wilayah/kota di dalam negeri maupun antar negara dilengkapi dengan dokumen pengangkutan.")
        st.subheader("2. Jenis-jenis Cargo (Type of Cargo)")
        st.markdown("**A. General Cargo**\nBerupa barang-barang umum yang tidak membutuhkan penanganan secara khusus, namun wajib memenuhi persyaratan dalam aspek safety dan security.")
        st.markdown("**B. Special Cargo**\nKiriman yang membutuhkan penanganan khusus (special handling) baik dari sisi penerimaan, penyimpanan, dan pengangkutan.")

    with t2:
        st.subheader("Rincian Kategori Special Cargo")
        st.markdown("""
        * **1. Perishable Cargo:** Barang yang mudah rusak, hancur, atau busuk. (Contoh: Daging, Buah, Sayur, Seafood, Vaksin).
        * **2. Wet Cargo:** Barang yang mengandung cairan atau mengeluarkan air. (Contoh: Sampel air, ikan dalam air).
        * **3. Electronic Goods:** Seluruh barang elektronik (Handphone dan laptop wajib baru).
        * **4. Live Animal Cargo:** Hewan hidup yang dikirim via pesawat. (Contoh: Mamalia, Burung, Reptil).
        * **5. Diplomatic Pouch:** Surat/dokumen resmi kedutaan atau pemerintah (disegel resmi).
        * **6. Valuable Cargo:** Barang berharga tinggi > $1.000 per Kg. (Contoh: Emas, perhiasan, uang).
        * **7. Heavy Cargo:** Barang dengan berat di luar standar (>75Kg per koli).
        * **8. Human Remains:** Pengiriman jenazah (peti, kerangka, atau abu kremasi).
        * **9. Dangerous Goods:** Bahan berbahaya yang mengancam keselamatan penerbangan.
        """)

    with t3:
        st.subheader("Klasifikasi Dangerous Goods (9 Kelas)")
        st.markdown("""
        * **Class 1 (Explosive):** Bahaya ledakan besar (Bom, amunisi, kembang api).
        * **Class 2 (Gases):** Gas mudah terbakar/beracun (Oksigen, Aerosol, Karbondioksida).
        * **Class 3 (Flammable Liquid):** Cairan mudah terbakar (Bensin, cat, aseton, parfum).
        * **Class 4 (Flammable Solid):** Padatan mudah terbakar (Sulfur, logam alkali).
        * **Class 5 (Oxidizing Substances):** Zat pengoksidasi (Hidrogen peroksida).
        * **Class 6 (Toxic & Infectious):** Zat beracun & menular (Sianida, sampel virus, limbah medis).
        * **Class 7 (Radioactive Material):** Memancarkan radiasi berbahaya (Uranium).
        * **Class 8 (Corrosive):** Merusak jaringan kulit/benda (Asam sulfat, air aki).
        * **Class 9 (Miscellaneous):** Berbahaya lainnya (Baterai Lithium, kendaraan bermotor).
        """)

    with t4:
        st.subheader("Prioritas Muatan (Cargo Priority Onboard)")
        st.write("Urutan prioritas muatan kargo di dalam kompartemen pesawat:")
        st.markdown("1. Aircraft on Ground (AOG) Sparepart\n2. Human Remains\n3. Live Animal\n4. Perishable Goods\n5. Valuable Goods\n6. Premium Product\n7. Cargo Ex Offload\n8. General Cargo")
        st.subheader("Dokumen Persyaratan Pengiriman")
        st.markdown("1. SMU / Air Waybill\n2. Pemberitahuan Tentang Isi (PTI)\n3. Surat Pernyataan Pembebasan Tanggung Jawab\n4. Consignment Security Declaration (CSD)\n5. NOTOC (Apabila Perlu)")

    if os.path.exists("Modul_Materi_Basic_Air_Cargo.pdf"):
        st.markdown("<br>", unsafe_allow_html=True)
        with open("Modul_Materi_Basic_Air_Cargo.pdf", "rb") as pdf_file:
            st.download_button("📥 Download Modul Materi Lengkap (PDF)", data=pdf_file, file_name="Modul_Basic_Cargo.pdf", mime="application/pdf")

    st.markdown("---")
    st.markdown("<div style='text-align: center;'>", unsafe_allow_html=True)
    if st.button("🚀 Sudah Memahami Materi? Mulai Ujian Basic Cargo Sekarang", type="primary", use_container_width=True):
        st.session_state["current_page_bc"] = "Ujian Basic Cargo"
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


# ==================== MENU 2: UJIAN BASIC CARGO ====================
elif menu == "Ujian Basic Cargo":
    col_logo1, col_title, col_logo2 = st.columns([1.5, 5, 1.5])
    with col_logo1:
        if os.path.exists("logo_sriwijaya.png"): st.image("logo_sriwijaya.png", use_container_width=True)
    with col_title:
        st.markdown(
            """
            <div style="text-align: center; padding: 10px 0;">
                <h1 style="color: #0E3B68; margin-bottom: 0px; font-size: 2.2rem; font-weight: 800;">
                    ✈️ Examination Basic Air Cargo
                </h1>
                <h4 style="color: #6C757D; margin-top: 5px; font-weight: 400; letter-spacing: 1px;">
                    Sriwijaya Air & NAM Air Cargo Training System
                </h4>
            </div>
            """, unsafe_allow_html=True
        )
    with col_logo2:
        if os.path.exists("logo_namair.png"): st.image("logo_namair.png", use_container_width=True)

    st.markdown("<hr style='margin-top: -5px; margin-bottom: 25px; border: 1px solid #E0E0E0;'>", unsafe_allow_html=True)

    with st.expander("📋 Syarat & Ketentuan Kelulusan", expanded=True):
        st.write("""
        - **Jumlah Soal:** 25 Pilihan Ganda (Bobot 4 Poin/Soal)
        - **Passing Grade Kelulusan:** ≥ 80 Poin (Minimal 20 Jawaban Benar)
        - Peserta yang lulus langsung memperoleh **2 Sertifikat Resmi** (Sriwijaya Air & NAM Air).
        """)

    if 'exam_result_bc' in st.session_state:
        res = st.session_state['exam_result_bc']
        if res['passed']:
            st.balloons()
            st.success(f"🎉 SELAMAT! Anda dinyatakan **LULUS** dengan Nilai: **{res['score']} / 100** (Benar: {res['correct_count']}/25).")
            st.subheader("Unduh Sertifikat Kelulusan")
            col_d1, col_d2 = st.columns(2)
            with col_d1:
                if res['pdf_sj']:
                    st.download_button("📥 Unduh Sertifikat Sriwijaya Air (SJ)", data=res['pdf_sj'], file_name=f"Sertifikat_SJ_Basic_{res['full_name'].replace(' ', '_')}.pdf", mime="application/pdf", use_container_width=True)
                else: st.warning("File Template_Basic_SJ.pdf belum tersedia di server.")
            with col_d2:
                if res['pdf_in']:
                    st.download_button("📥 Unduh Sertifikat NAM Air (IN)", data=res['pdf_in'], file_name=f"Sertifikat_IN_Basic_{res['full_name'].replace(' ', '_')}.pdf", mime="application/pdf", use_container_width=True)
                else: st.warning("File Template_Basic_IN.pdf belum tersedia di server.")
            st.info("ℹ️ Data ujian Anda telah resmi tersimpan. Silakan simpan dan unduh dokumen sertifikat di atas.")
        else:
            st.error(f"MOHON MAAF, Anda dinyatakan **BELUM LULUS** dengan Nilai: **{res['score']} / 100** (Benar: {res['correct_count']}/25). Passing grade: 80.")
            if st.button("🔄 Ulangi Ujian", type="primary"):
                del st.session_state['exam_result_bc']; st.rerun()
    else:
        st.subheader("1. Data Diri Peserta")
        col1, col2 = st.columns(2)
        with col1:
            full_name = st.text_input("Nama Lengkap*")
            nik = st.text_input("NIK / Employee ID*")
            phone = st.text_input("No. Handphone / WhatsApp*")
            job_role_selected = st.selectbox("Jabatan / Unit Kerja*", options=JOB_ROLES, index=None, placeholder="-- Pilih Jabatan / Unit Kerja --")
            if job_role_selected == "Lainnya": job_role = st.text_input("Sebutkan Jabatan / Unit Kerja Anda*").strip()
            else: job_role = job_role_selected if job_role_selected else ""
        with col2:
            company = st.text_input("Perusahaan*")
            dist_df = get_districts_basic()
            dist_options = (dist_df['code'] + " - " + dist_df['name']).tolist() if not dist_df.empty and 'code' in dist_df.columns and 'name' in dist_df.columns else []
            selected_dist = st.selectbox("Distrik Penugasan*", options=dist_options, index=None, placeholder="-- Pilih Distrik Penugasan --")
            training_date = st.date_input("Tanggal Pelaksanaan Training", date.today(), format="DD/MM/YYYY")

        st.subheader("2. Lembar Soal Ujian (25 Soal)")
        with st.form("exam_form_bc"):
            user_answers = {}
            for i, q in enumerate(SOAL_UJIAN_BASIC_CARGO):
                st.markdown(f"**Soal {q['no']}:** {q['q']}")
                user_answers[i] = st.radio(f"Pilih jawaban untuk nomor {q['no']}:", options=q['options'], key=f"q_{i}", index=None, label_visibility="collapsed")
                st.write("")

            submit_btn = st.form_submit_button("Submit Jawaban & Evaluasi Nilai", type="primary")

        if submit_btn:
            if not full_name or not nik or not phone or not company or not selected_dist or not job_role:
                st.error("Mohon lengkapi seluruh kolom Data Diri Peserta (termasuk Distrik dan Jabatan) sebelum submit!")
            elif any(user_answers[i] is None for i in range(len(SOAL_UJIAN_BASIC_CARGO))):
                st.warning("Pastikan seluruh 25 soal telah dijawab!")
            else:
                with st.spinner("Sedang memproses evaluasi nilai dan menyimpan sertifikat..."):
                    correct_count = sum(1 for i, q in enumerate(SOAL_UJIAN_BASIC_CARGO) if str(user_answers[i]).strip() == str(q['a']).strip())
                    score = correct_count * 4
                    ans_json = json.dumps({str(q['no']): str(user_answers[i]) for i, q in enumerate(SOAL_UJIAN_BASIC_CARGO)})

                    dist_parts = selected_dist.split(" - ", 1)
                    dist_code = dist_parts[0].strip()
                    dist_name = dist_parts[1].strip() if len(dist_parts) > 1 else ""

                    passed = score >= 80
                    records_df = load_basic_records()
                    
                    if passed:
                        cert_no_sj = get_next_cert_number_basic("SJ", records_df)
                        cert_no_in = get_next_cert_number_basic("IN", records_df)
                        exp_date = (training_date + relativedelta(months=24)).strftime("%Y-%m-%d")
                    else:
                        cert_no_sj, cert_no_in, exp_date = "-", "-", "-"

                    rec_id = f"BC{datetime.now().strftime('%Y%m%d%H%M%S')}"
                    record_payload = {
                        'id': rec_id,
                        'training_date': str(training_date),
                        'full_name': full_name.strip(),
                        'nik': nik.strip(),
                        'phone': str(phone).strip(),
                        'job_role': job_role.strip(),
                        'company': company.strip(),
                        'district': dist_code,
                        'district_name': dist_name,
                        'district_full': selected_dist,
                        'score': score,
                        'status': 'LULUS' if passed else 'TIDAK LULUS',
                        'cert_no_sj': cert_no_sj,
                        'cert_no_in': cert_no_in,
                        'expiry_date': exp_date,
                        'jawaban_ujian': ans_json
                    }
                    
                    save_basic_record(record_payload)
                    
                    pdf_sj_out, pdf_in_out = None, None
                    if passed:
                        pdf_sj_out = generate_cert_basic("SJ", cert_no_sj, full_name.strip(), str(training_date))
                        pdf_in_out = generate_cert_basic("IN", cert_no_in, full_name.strip(), str(training_date))

                    st.session_state['exam_result_bc'] = {
                        'passed': passed,
                        'score': score,
                        'correct_count': correct_count,
                        'full_name': full_name.strip(),
                        'pdf_sj': pdf_sj_out,
                        'pdf_in': pdf_in_out
                    }
                st.rerun()

# ==================== MENU 3: DASHBOARD INSTRUKTUR & RECORDS ====================
elif menu == "Dashboard Instruktur & Records":
    st.title("📊 Training Records & Audit Report (Basic Cargo)")
    st.subheader("(Google Sheets Cloud)")
    
    with st.expander("⚙️ **Pengaturan Khusus & Refresh Data Cache**", expanded=False):
        c_tool1, c_tool2 = st.columns(2)
        with c_tool1:
            st.markdown("**1. Sinkronisasi & Refresh Cache Database**")
            st.caption("Membersihkan cache internal agar data Google Sheets termutakhir langsung terbaca.")
            if st.button("🔄 Refresh Data Cache", type="primary"):
                st.cache_data.clear(); st.cache_resource.clear(); st.success("✅ Cache berhasil dibersihkan!"); time.sleep(1); st.rerun()
        with c_tool2:
            st.markdown("**2. Kosongkan Seluruh Data Percobaan (Trial)**")
            st.caption("Menghapus seluruh riwayat ujian yang ada di tabel Google Sheets.")
            if st.button("⚠️ Hapus Seluruh Data Basic Cargo", type="secondary"):
                if service_sheets and SPREADSHEET_ID:
                    try:
                        sm = service_sheets.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
                        sid = next((s["properties"]["sheetId"] for s in sm.get("sheets", []) if s["properties"]["title"] == TAB_NAME_BASIC), None)
                        if sid is not None:
                            service_sheets.spreadsheets().batchUpdate(spreadsheetId=SPREADSHEET_ID, body={"requests": [{"deleteDimension": {"range": {"sheetId": sid, "dimension": "ROWS", "startIndex": 1}}}]}).execute()
                    except: pass
                st.toast("Seluruh record Basic Cargo berhasil dibersihkan dari cloud!", icon="🗑️"); st.rerun()

    st.markdown("---")
    records_df = load_basic_records()

    if records_df.empty: st.info("Belum ada data riwayat training. (Tabel Google Sheets Basic Cargo masih kosong)")
    else:
        with st.expander("🗑️ **Hapus Record Spesifik (Berdasarkan ID / Nama)**", expanded=False):
            rec_options = {f"ID {r['id']} | {r['full_name']} ({r['district']}) - Tgl: {r['training_date']}": r['id'] for _, r in records_df.iterrows()}
            selected_to_delete = st.selectbox("Pilih data yang ingin dihapus permanen:", list(rec_options.keys()))
            if st.button("Hapus Data Terpilih Ini", type="primary"):
                del_id = rec_options[selected_to_delete]
                if service_sheets and SPREADSHEET_ID:
                    try:
                        r = service_sheets.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID, range=f"{TAB_NAME_BASIC}!A1:A").execute()
                        v = r.get("values", [])
                        ri = next((i for i, row in enumerate(v) if row and row[0] == del_id), -1)
                        if ri != -1:
                            sm = service_sheets.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
                            sid = next((s["properties"]["sheetId"] for s in sm.get("sheets", []) if s["properties"]["title"] == TAB_NAME_BASIC), None)
                            service_sheets.spreadsheets().batchUpdate(spreadsheetId=SPREADSHEET_ID, body={"requests": [{"deleteDimension": {"range": {"sheetId": sid, "dimension": "ROWS", "startIndex": ri, "endIndex": ri + 1}}}]}).execute()
                    except: pass
                st.success("✅ Data berhasil dihapus permanen dari Google Sheets!"); time.sleep(1); st.rerun()

        col1, col2 = st.columns(2)
        with col1: filter_dist = st.multiselect("Filter Distrik", options=records_df['district'].unique() if 'district' in records_df.columns else [])
        with col2: filter_role = st.multiselect("Filter Jabatan", options=records_df['job_role'].unique() if 'job_role' in records_df.columns else [])

        filtered_df = records_df.copy()
        if filter_dist and 'district' in filtered_df.columns: filtered_df = filtered_df[filtered_df['district'].isin(filter_dist)]
        if filter_role and 'job_role' in filtered_df.columns: filtered_df = filtered_df[filtered_df['job_role'].isin(filter_role)]

        st.dataframe(filtered_df, use_container_width=True, hide_index=True)

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer: filtered_df.to_excel(writer, index=False, sheet_name='Training_Records_Basic')
        excel_data = output.getvalue()
        
        col_exp1, col_exp2 = st.columns(2)
        with col_exp1: st.download_button("📥 Ekspor Data ke Excel (.xlsx)", data=excel_data, file_name=f"Basic_Cargo_Records_{date.today().strftime('%Y%m%d')}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
        with col_exp2: st.download_button("📥 Ekspor Data ke CSV (.csv)", data=filtered_df.to_csv(index=False).encode('utf-8'), file_name=f"Basic_Cargo_Records_{date.today().strftime('%Y%m%d')}.csv", mime="text/csv", use_container_width=True)

        # ==================== ABSENSI BASIC CARGO ====================
        st.markdown("---")
        st.subheader("📝 Penerbitan Daftar Kehadiran (Absensi) Training")
        st.caption("Gunakan bagian ini untuk menerbitkan absensi resmi per distrik dan per tanggal kegiatan.")
        col_ab1, col_ab2 = st.columns(2)
        with col_ab1:
            all_districts = sorted(records_df['district'].dropna().unique().tolist()) if 'district' in records_df.columns else []
            selected_absensi_dist = st.selectbox("1. Pilih Distrik Penugasan:", options=all_districts) if all_districts else None
        with col_ab2:
            if selected_absensi_dist and 'district' in records_df.columns:
                dist_records = records_df[records_df['district'] == selected_absensi_dist]
                avail_dates = sorted(dist_records['training_date'].dropna().unique().tolist(), reverse=True) if 'training_date' in dist_records.columns else []
                selected_absensi_date = st.selectbox("2. Pilih Tanggal Training:", options=avail_dates) if avail_dates else None
            else: selected_absensi_date = None

        if selected_absensi_date:
            candidates_att = dist_records[dist_records['training_date'] == selected_absensi_date].copy()
            st.info(f"Ditemukan **{len(candidates_att)} orang peserta** untuk Distrik **{selected_absensi_dist}** pada tanggal **{selected_absensi_date}**.")
            
            c_meta1, c_meta2, c_meta3 = st.columns(3)
            with c_meta1: mode_training = st.radio("Metode Pelaksanaan:", ["Online", "Offline"], horizontal=True)
            with c_meta2: jam_training = st.text_input("Pukul / Waktu Training:", value="13.00 - 17.00")
            with c_meta3: nama_instruktur = st.text_input("Nama Instruktur:", value="HADI NURHUDA")
            c_meta4, c_meta5 = st.columns([2, 2])
            with c_meta4: tempat_training = st.text_input("Tempat Training:", value=f"Station {selected_absensi_dist} ({mode_training.lower()})")
            with c_meta5: foto_uploaded = st.file_uploader("Upload Foto Bukti Pelatihan (JPG / PNG):", type=["jpg", "jpeg", "png"])
            
            if mode_training == "Offline":
                sessions = [candidates_att.iloc[i:i+25] for i in range(0, len(candidates_att), 25)]
                st.write(f"📌 *Mode Offline: Dipecah menjadi **{len(sessions)} Sesi** (Maksimal 25 peserta/sesi).*")
            else:
                sessions = [candidates_att]
                st.write("📌 *Mode Online: Seluruh peserta digabung ke dalam 1 lembar absensi.*")
                
            try:
                dt_obj = datetime.strptime(str(selected_absensi_date)[:10], "%Y-%m-%d")
                hari_id = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"][dt_obj.weekday()]
                bulan_id = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"][dt_obj.month - 1]
                tgl_display = f"{hari_id}, {dt_obj.day} {bulan_id} {dt_obj.year}"
            except: tgl_display = str(selected_absensi_date)

            for s_idx, session_df in enumerate(sessions):
                sesi_label = f"Sesi {s_idx + 1}" if len(sessions) > 1 else "Dokumen Absensi"
                st.markdown(f"#### 📄 Unduh {sesi_label} ({len(session_df)} Peserta)")
                c_btn1, c_btn2, c_btn3 = st.columns(3)
                foto_bytes = foto_uploaded.getvalue() if foto_uploaded else None
                with c_btn1:
                    try: st.download_button(label=f"📥 PDF Sriwijaya Air ({sesi_label})", data=generate_attendance_pdf("SJ", tgl_display, jam_training, tempat_training, nama_instruktur, session_df, foto_bytes), file_name=f"Absensi_SJ_BC_{selected_absensi_dist}.pdf", mime="application/pdf", use_container_width=True)
                    except Exception as e: st.error(f"Gagal generate PDF SJ: {e}")
                with c_btn2:
                    try: st.download_button(label=f"📥 PDF NAM Air ({sesi_label})", data=generate_attendance_pdf("IN", tgl_display, jam_training, tempat_training, nama_instruktur, session_df, foto_bytes), file_name=f"Absensi_IN_BC_{selected_absensi_dist}.pdf", mime="application/pdf", use_container_width=True)
                    except Exception as e: st.error(f"Gagal generate PDF IN: {e}")
                with c_btn3:
                    try: st.download_button(label=f"📊 Excel (.xlsx) ({sesi_label})", data=generate_attendance_excel(tgl_display, jam_training, tempat_training, nama_instruktur, session_df), file_name=f"Absensi_BC_{selected_absensi_dist}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
                    except Exception as e: st.error(f"Gagal generate Excel: {e}")

        # ==================== UNDUH ULANG SERTIFIKAT ====================
        st.markdown("---")
        st.subheader("🎓 Cetak / Unduh Ulang Sertifikat Peserta")
        passed_records = records_df[(records_df['status'] == 'LULUS') & (records_df['cert_no_sj'] != '-') & (records_df['cert_no_sj'].notna())].copy() if 'status' in records_df.columns and 'cert_no_sj' in records_df.columns else pd.DataFrame()

        if passed_records.empty: st.info("Belum ada data peserta yang dinyatakan lulus untuk diunduh sertifikatnya.")
        else:
            tab_cert1, tab_cert2 = st.tabs(["📦 Unduh Sekaligus Berdasarkan Pilihan Distrik (.ZIP)", "👤 Unduh Perorangan"])
            with tab_cert1:
                st.markdown("##### 📁 Download Sertifikat Sesuai Distrik Penugasan")
                dist_codes = sorted(passed_records['district'].dropna().unique().tolist()) if 'district' in passed_records.columns else []
                all_choices = [f"{d} - (Semua Unit / Perusahaan)" for d in dist_codes]
                
                sel_group_col1, sel_group_col2 = st.columns(2)
                with sel_group_col1:
                    selected_group = st.selectbox("Pilih Distrik Penugasan Target:", options=all_choices, key="bc_batch_dist") if all_choices else None
                with sel_group_col2:
                    target_dist = selected_group.split(" - ", 1)[0].strip() if selected_group else ""
                    df_dist_only = passed_records[passed_records['district'] == target_dist].copy() if target_dist and 'district' in passed_records.columns else pd.DataFrame()
                    dist_dates = sorted(df_dist_only['training_date'].dropna().unique().tolist(), reverse=True) if not df_dist_only.empty and 'training_date' in df_dist_only.columns else []
                    batch_date = st.selectbox("Pilih Tanggal Pelaksanaan (Opsional):", options=["Semua Tanggal"] + dist_dates, key="bc_batch_date") if dist_dates else "Semua Tanggal"

                if batch_date != "Semua Tanggal" and not df_dist_only.empty: batch_candidates = df_dist_only[df_dist_only['training_date'] == batch_date].copy()
                else: batch_candidates = df_dist_only.copy()

                st.info(f"Ditemukan **{len(batch_candidates)} orang peserta** untuk target: **{selected_group if selected_group else '-'}**.")
                
                if not batch_candidates.empty:
                    c_zip1, c_zip2, c_zip3 = st.columns(3)
                    with c_zip1:
                        if st.button("📦 Siapkan ZIP Sertifikat SJ", use_container_width=True):
                            zip_buf_sj = io.BytesIO()
                            with zipfile.ZipFile(zip_buf_sj, "w", zipfile.ZIP_DEFLATED) as zf:
                                for _, row in batch_candidates.iterrows():
                                    pdf_bytes = generate_cert_basic("SJ", str(row['cert_no_sj']).replace('.0', ''), str(row['full_name']), str(row['training_date']))
                                    if pdf_bytes: zf.writestr(f"Sertifikat_SJ_{row['cert_no_sj']}_{str(row['full_name']).strip().replace(' ', '_')}.pdf", pdf_bytes)
                            st.download_button("📥 Unduh ZIP Sriwijaya Air (SJ)", data=zip_buf_sj.getvalue(), file_name=f"Sertifikat_Basic_SJ_{target_dist}.zip", mime="application/zip", use_container_width=True)
                    with c_zip2:
                        if st.button("📦 Siapkan ZIP Sertifikat IN", use_container_width=True):
                            zip_buf_in = io.BytesIO()
                            with zipfile.ZipFile(zip_buf_in, "w", zipfile.ZIP_DEFLATED) as zf:
                                for _, row in batch_candidates.iterrows():
                                    pdf_bytes = generate_cert_basic("IN", str(row['cert_no_in']).replace('.0', ''), str(row['full_name']), str(row['training_date']))
                                    if pdf_bytes: zf.writestr(f"Sertifikat_IN_{row['cert_no_in']}_{str(row['full_name']).strip().replace(' ', '_')}.pdf", pdf_bytes)
                            st.download_button("📥 Unduh ZIP NAM Air (IN)", data=zip_buf_in.getvalue(), file_name=f"Sertifikat_Basic_IN_{target_dist}.zip", mime="application/zip", use_container_width=True)
                    with c_zip3:
                        if st.button("📦 Siapkan ZIP Lengkap (SJ + IN)", use_container_width=True):
                            zip_buf_all = io.BytesIO()
                            with zipfile.ZipFile(zip_buf_all, "w", zipfile.ZIP_DEFLATED) as zf:
                                for _, row in batch_candidates.iterrows():
                                    c_name = str(row['full_name']).strip().replace(' ', '_')
                                    p_sj = generate_cert_basic("SJ", str(row['cert_no_sj']).replace('.0', ''), str(row['full_name']), str(row['training_date']))
                                    p_in = generate_cert_basic("IN", str(row['cert_no_in']).replace('.0', ''), str(row['full_name']), str(row['training_date']))
                                    if p_sj: zf.writestr(f"Sriwijaya_Air/Sertifikat_SJ_{row['cert_no_sj']}_{c_name}.pdf", p_sj)
                                    if p_in: zf.writestr(f"NAM_Air/Sertifikat_IN_{row['cert_no_in']}_{c_name}.pdf", p_in)
                            st.download_button("📥 Unduh ZIP Lengkap", data=zip_buf_all.getvalue(), file_name=f"Sertifikat_Lengkap_Basic_{target_dist}.zip", mime="application/zip", use_container_width=True)

            with tab_cert2:
                st.markdown("##### 👤 Download Sertifikat Spesifik Per Peserta")
                options_dict = {f"{r['nik']} - {r['full_name']} ({r['district']} - {r['company']}) | Tgl: {r['training_date']}": r for _, r in passed_records.iterrows()}
                selected_candidate_label = st.selectbox("Pilih Peserta untuk Dicetak Ulang Sertifikatnya:", options=list(options_dict.keys()), key="bc_single_cert") if options_dict else None
                if selected_candidate_label:
                    selected_candidate = options_dict[selected_candidate_label]
                    st.write(f"**Peserta:** {selected_candidate['full_name']} | **Perusahaan:** {selected_candidate['company']} | **No Sertifikat SJ:** `{selected_candidate['cert_no_sj']}` | **No Sertifikat IN:** `{selected_candidate['cert_no_in']}`")
                    re_col1, re_col2 = st.columns(2)
                    with re_col1:
                        re_pdf_sj = generate_cert_basic("SJ", str(selected_candidate['cert_no_sj']).replace('.0', ''), str(selected_candidate['full_name']), str(selected_candidate['training_date']))
                        if re_pdf_sj: st.download_button(label=f"📄 Unduh Ulang Sertifikat SJ", data=re_pdf_sj, file_name=f"Sertifikat_Basic_SJ_{str(selected_candidate['full_name']).replace(' ', '_')}.pdf", mime="application/pdf", use_container_width=True)
                    with re_col2:
                        re_pdf_in = generate_cert_basic("IN", str(selected_candidate['cert_no_in']).replace('.0', ''), str(selected_candidate['full_name']), str(selected_candidate['training_date']))
                        if re_pdf_in: st.download_button(label=f"📄 Unduh Ulang Sertifikat IN", data=re_pdf_in, file_name=f"Sertifikat_Basic_IN_{str(selected_candidate['full_name']).replace(' ', '_')}.pdf", mime="application/pdf", use_container_width=True)

# ==================== MENU 4: MASTER DISTRIK & RECURRENT ====================
elif menu == "Master Distrik & Jadwal Recurrent":
    st.title("📍 Master Distrik & Monitoring Recurrent Basic Cargo (24 Bulan)")
    dist_df = get_districts_basic()

    def calculate_status(due_str):
        if pd.isna(due_str) or not due_str or str(due_str).strip() in ['None', '', 'nan', 'NaT']: return "Belum Ada Riwayat Training"
        try:
            diff_days = (datetime.strptime(str(due_str)[:10], "%Y-%m-%d").date() - date.today()).days
            if diff_days < 0: return "⚠️ Kedaluwarsa (Wajib Recurrent)"
            elif diff_days <= 30: return f"🔔 Segera Recurrent ({diff_days} Hari Tersisa)"
            else: return "✅ Aktif"
        except: return "Format Tanggal Salah"

    with st.expander("✏️ **Pusat Edit Manual Data Distrik & Jadwal Recurrent (Basic Cargo)**", expanded=True):
        if not dist_df.empty and 'code' in dist_df.columns:
            dist_map = {f"ID {d_row.get('id', '')} | {d_row.get('code', '')} - {d_row.get('name', '')} ({d_row.get('category', '')})": d_row for _, d_row in dist_df.iterrows()}
            sel_dist_lbl = st.selectbox("Pilih Distrik yang Ingin Diubah:", list(dist_map.keys())) if dist_map else None
            if sel_dist_lbl:
                cur_data = dist_map[sel_dist_lbl]
                raw_last, raw_due = str(cur_data.get('last_training_date', '')).strip(), str(cur_data.get('next_due_date', '')).strip()
                default_last, default_due, has_valid_history = date.today(), date.today() + relativedelta(months=24), False
                if raw_last and raw_last not in ['None', '', 'nan', 'NaT']:
                    try: default_last = datetime.strptime(raw_last[:10], "%Y-%m-%d").date(); has_valid_history = True
                    except: pass
                if raw_due and raw_due not in ['None', '', 'nan', 'NaT']:
                    try: default_due = datetime.strptime(raw_due[:10], "%Y-%m-%d").date()
                    except: default_due = default_last + relativedelta(months=24)

                with st.form("form_edit_manual_distrik_bc"):
                    e_c1, e_c2, e_c3 = st.columns(3)
                    with e_c1: edit_code = st.text_input("Kode Distrik (Code)", value=str(cur_data.get('code', '')))
                    with e_c2: edit_name = st.text_input("Nama Distrik / Stasiun", value=str(cur_data.get('name', '')))
                    with e_c3: 
                        cat_val = str(cur_data.get('category', 'Sriwijaya Air'))
                        cat_idx = CATEGORY_OPTIONS.index(cat_val) if cat_val in CATEGORY_OPTIONS else 0
                        edit_cat = st.selectbox("Kategori", CATEGORY_OPTIONS, index=cat_idx)

                    st.markdown("---")
                    status_history = st.radio("Status Riwayat Pelatihan:", options=["Ada Riwayat Training", "Belum Ada Riwayat (Kosongkan Tanggal)"], index=0 if has_valid_history else 1, horizontal=True)
                    e_c4, e_c5 = st.columns(2)
                    with e_c4: edit_last_date = st.date_input("Last Training Date:", value=default_last, format="DD/MM/YYYY")
                    with e_c5: edit_due_date = st.date_input("Next Due Date (Reminder):", value=default_due, format="DD/MM/YYYY")

                    st.markdown("---")
                    b_col1, b_col2 = st.columns([1, 1])
                    with b_col1: btn_save_manual = st.form_submit_button("💾 Simpan Perubahan ke Google Sheets", type="primary")
                    with b_col2: btn_del_single = st.form_submit_button("🗑️ Hapus Distrik Ini Permanen", type="secondary")

                    if btn_save_manual:
                        update_district_row_basic(cur_data.get('id'), edit_code, edit_name, edit_cat, edit_last_date.strftime("%Y-%m-%d") if status_history == "Ada Riwayat Training" else "", edit_due_date.strftime("%Y-%m-%d") if status_history == "Ada Riwayat Training" else "")
                        st.success(f"✅ Data ID {cur_data.get('id')} berhasil diperbarui!"); time.sleep(1); st.rerun()
                    if btn_del_single:
                        delete_district_row_basic(cur_data.get('id'))
                        st.toast(f"Distrik dihapus!", icon="🗑️"); time.sleep(1); st.rerun()

    st.markdown("---")
    st.subheader("📋 Tabel Monitoring Distrik & Recurrent Basic Cargo")
    
    if dist_df.empty or 'code' not in dist_df.columns:
        st.info("Tabel distrik masih kosong. Pastikan tab 'districts_basic' sudah terisi data di Google Sheets.")
    else:
        df_display = dist_df.copy()
        def format_date_display(d_str):
            if pd.isna(d_str) or not d_str or str(d_str).strip() in ['None', '', 'nan', 'NaT']: return "-"
            try: return datetime.strptime(str(d_str)[:10], "%Y-%m-%d").strftime("%d-%b-%Y")
            except: return str(d_str)
            
        df_display['Status Recurrent'] = df_display['next_due_date'].apply(calculate_status) if 'next_due_date' in df_display.columns else "Belum Ada Riwayat Training"
        df_display['Last Training Date'] = df_display['last_training_date'].apply(format_date_display) if 'last_training_date' in df_display.columns else "-"
        df_display['Next Due Date (Reminder)'] = df_display['next_due_date'].apply(format_date_display) if 'next_due_date' in df_display.columns else "-"
        
        show_cols = [c for c in ['id', 'code', 'name', 'category', 'Last Training Date', 'Next Due Date (Reminder)', 'Status Recurrent'] if c in df_display.columns]
        st.dataframe(df_display[show_cols], hide_index=True, use_container_width=True)

    st.markdown("---")
    st.subheader("➕ Tambah Rute / Distrik Baru (Basic Cargo)")
    with st.form("add_dist_form_bc"):
        c1, c2, c3 = st.columns(3)
        with c1: new_code = st.text_input("Kode Distrik / IATA (misal: BDJ)")
        with c2: new_name = st.text_input("Nama Kota / Bandara (misal: Banjarmasin)")
        with c3: new_cat = st.selectbox("Kategori", CATEGORY_OPTIONS)
        
        if st.form_submit_button("Simpan Distrik Baru ke Google Sheets"):
            if new_code and new_name:
                add_district_basic(new_code.upper().strip(), new_name.strip(), new_cat)
                st.success(f"Distrik {new_code.upper()} berhasil ditambahkan!")
                time.sleep(1); st.rerun()
            else:
                st.error("Mohon isi kode dan nama distrik terlebih dahulu.")