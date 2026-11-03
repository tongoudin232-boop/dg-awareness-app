import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

@st.cache_resource
def get_gspread_client():
    try:
        if "gcp_service_account" in st.secrets:
            creds_dict = dict(st.secrets["gcp_service_account"])
        else:
            creds_dict = dict(st.secrets)
            
        if "private_key" in creds_dict:
            creds_dict["private_key"] = str(creds_dict["private_key"]).replace("\n", "
")
            
        credentials = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        client = gspread.authorize(credentials)
        return client
    except Exception as e:
        st.error(f"Gagal otentikasi Google Sheets: {e}")
        return None

def get_spreadsheet():
    client = get_gspread_client()
    if not client: return None
    
    # KITA PAKSA MENGGUNAKAN SPREADSHEET MILIK SERVICE ACCOUNT SENDIRI
    # UNTUK MENGHINDARI ERROR 404 PERMISSIONS
    try:
        sh = client.open("DG_Awareness_Database")
        
        # Share spreadsheet ini ke email Gmail user agar mereka bisa buka
        try:
            sh.share('tongoudin232@gmail.com', perm_type='user', role='writer')
        except:
            pass # abaikan jika sudah di-share
            
        st.success(f"✅ Terhubung ke Database Cloud Internal: [Buka Google Sheets]({sh.url})")
        st.info("💡 Karena Google memblokir akses ke file lama Anda, sistem otomatis membuatkan file database baru. Silakan klik link di atas, buka file-nya, lalu **COPY-PASTE** isi tabel lama Anda ke file yang baru ini.")
        
        # Buat tab jika belum ada
        try:
            sh.worksheet("districts")
        except:
            sh.add_worksheet("districts", 1000, 26)
            sh.worksheet("districts").append_row(["id", "code", "name", "category", "last_training_date", "next_due_date"])
            
        try:
            sh.worksheet("training_records")
        except:
            sh.add_worksheet("training_records", 1000, 26)
            sh.worksheet("training_records").append_row([
                "id", "training_date", "full_name", "nik", "phone",
                "job_role", "company", "district", "district_full", "score", "status",
                "cert_no_sj", "cert_no_in", "expiry_date"
            ])
            
        return sh
    except gspread.exceptions.SpreadsheetNotFound:
        # Jika belum ada sama sekali, buat baru
        sh = client.create("DG_Awareness_Database")
        sh.share('tongoudin232@gmail.com', perm_type='user', role='writer')
        
        sh.add_worksheet("districts", 1000, 26)
        sh.worksheet("districts").append_row(["id", "code", "name", "category", "last_training_date", "next_due_date"])
        
        sh.add_worksheet("training_records", 1000, 26)
        sh.worksheet("training_records").append_row([
            "id", "training_date", "full_name", "nik", "phone",
            "job_role", "company", "district", "district_full", "score", "status",
            "cert_no_sj", "cert_no_in", "expiry_date"
        ])
        
        try:
            sh.del_worksheet(sh.worksheet("Sheet1"))
        except: pass
        
        st.success(f"✅ Database Cloud Internal Berhasil Dibuat: [Buka Google Sheets]({sh.url})")
        return sh
    except Exception as e:
        st.error(f"❌ Terjadi kesalahan saat menyiapkan database internal: {e}")
        return None

def get_connection(): return None
def init_db(): pass

def get_districts():
    sh = get_spreadsheet()
    if not sh: return pd.DataFrame()
    try:
        ws = sh.worksheet("districts")
        data = ws.get_all_records()
        df = pd.DataFrame(data)
        if not df.empty and 'id' in df.columns:
            df['id'] = pd.to_numeric(df['id'], errors='coerce').fillna(0).astype(int)
            df = df[df['id'] > 0]
            return df.sort_values(by=['code', 'name']).reset_index(drop=True)
        return df
    except Exception as e:
        st.error(f"Gagal membaca tab districts: {e}")
        return pd.DataFrame()


def add_district(code, name, category):
    df = get_districts()
    next_id = 1 if df.empty else int(df['id'].max()) + 1
    new_row = [next_id, code.upper().strip(), name.strip(), category.strip(), "", ""]
    
    sh = get_spreadsheet()
    if sh:
        try:
            ws = sh.worksheet("districts")
            ws.append_row(new_row)
            st.cache_data.clear()
            st.cache_resource.clear()
        except: pass


def update_district_row(dist_id, code, name, category, last_date, due_date):
    sh = get_spreadsheet()
    if sh:
        try:
            ws = sh.worksheet("districts")
            records = ws.get_all_records()
            for i, row in enumerate(records):
                if str(row.get('id', '')) == str(dist_id):
                    row_idx = i + 2
                    ws.update(f"B{row_idx}:F{row_idx}", [[code.upper().strip(), name.strip(), category.strip(), str(last_date).strip(), str(due_date).strip()]])
                    st.cache_data.clear()
                    st.cache_resource.clear()
                    break
        except: pass


def delete_district_row(dist_id):
    sh = get_spreadsheet()
    if sh:
        try:
            ws = sh.worksheet("districts")
            records = ws.get_all_records()
            for i, row in enumerate(records):
                if str(row.get('id', '')) == str(dist_id):
                    ws.delete_rows(i + 2)
                    st.cache_data.clear()
                    st.cache_resource.clear()
                    break
        except: pass


def get_training_records():
    sh = get_spreadsheet()
    if not sh: return pd.DataFrame()
    try:
        ws = sh.worksheet("training_records")
        data = ws.get_all_records()
        df = pd.DataFrame(data)
        
        if not df.empty and 'id' in df.columns:
            df['id'] = pd.to_numeric(df['id'], errors='coerce').fillna(0).astype(int)
            df = df[df['id'] > 0]
            if 'nik' in df.columns: df['nik'] = df['nik'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
            if 'phone' in df.columns: df['phone'] = df['phone'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
            df = df.drop_duplicates(subset=['training_date', 'nik', 'cert_no_sj', 'cert_no_in'], keep='first')
            return df.sort_values(by='id', ascending=False).reset_index(drop=True)
        return df
    except Exception as e:
        st.error(f"Gagal membaca tab training_records: {e}")
        return pd.DataFrame()


def get_next_cert_number(airline):
    now = datetime.now()
    prefix_yymm = now.strftime("%y%m")
    target_col = 'cert_no_sj' if airline == 'SJ' else 'cert_no_in'

    df_records = get_training_records()
    max_seq = 0

    if not df_records.empty and target_col in df_records.columns:
        valid_certs = df_records[target_col].dropna().astype(str).str.strip()
        valid_certs = valid_certs.str.replace(r'\.0$', '', regex=True)

        for c_val in valid_certs:
            if c_val.startswith(prefix_yymm) and len(c_val) == 8 and c_val[4:].isdigit():
                seq_num = int(c_val[4:])
                if seq_num > max_seq: max_seq = seq_num

    next_seq = max_seq + 1
    return f"{prefix_yymm}{next_seq:04d}"


def save_training_record(record_data):
    df = get_training_records()

    if not df.empty:
        cur_nik = str(record_data.get('nik', '')).strip()
        cur_date = str(record_data.get('training_date', ''))[:10]
        existing = df[(df['nik'].astype(str).str.strip() == cur_nik) & (df['training_date'].astype(str).str[:10] == cur_date)]
        if not existing.empty: return False

    next_id = 1 if df.empty else int(df['id'].max()) + 1
    record_data['id'] = next_id

    # Pastikan urutan list sesuai header
    headers = [
        "id", "training_date", "full_name", "nik", "phone",
        "job_role", "company", "district", "district_full", "score", "status",
        "cert_no_sj", "cert_no_in", "expiry_date"
    ]
    new_row = [record_data.get(h, "") for h in headers]
    
    sh = get_spreadsheet()
    if sh:
        try:
            ws = sh.worksheet("training_records")
            ws.append_row(new_row)
        except: pass

        if record_data.get('status') == 'LULUS':
            t_date = record_data['training_date']
            target_dist_code = str(record_data.get('district', '')).strip()
            try:
                dt_obj = datetime.strptime(str(t_date)[:10], "%Y-%m-%d").date()
                next_due = dt_obj.replace(year=dt_obj.year + 2).strftime("%Y-%m-%d")
                
                ws_dist = sh.worksheet("districts")
                d_records = ws_dist.get_all_records()
                for i, row in enumerate(d_records):
                    if str(row.get('code', '')).strip().upper() == target_dist_code.upper():
                        row_idx = i + 2
                        ws_dist.update(f"E{row_idx}:F{row_idx}", [[str(t_date), str(next_due)]])
                        break
            except: pass

    st.cache_data.clear()
    st.cache_resource.clear()
    return True


def delete_training_record(record_id):
    sh = get_spreadsheet()
    if sh:
        try:
            ws = sh.worksheet("training_records")
            records = ws.get_all_records()
            for i, row in enumerate(records):
                if str(row.get('id', '')) == str(record_id):
                    ws.delete_rows(i + 2)
                    st.cache_data.clear()
                    st.cache_resource.clear()
                    break
        except: pass


def reset_cert_sequence():
    st.cache_data.clear()
    st.cache_resource.clear()


def clear_all_training_records():
    sh = get_spreadsheet()
    if sh:
        try:
            ws = sh.worksheet("training_records")
            ws.clear()
            headers = [
                "id", "training_date", "full_name", "nik", "phone",
                "job_role", "company", "district", "district_full", "score", "status",
                "cert_no_sj", "cert_no_in", "expiry_date"
            ]
            ws.append_row(headers)
            st.cache_data.clear()
            st.cache_resource.clear()
        except: pass
