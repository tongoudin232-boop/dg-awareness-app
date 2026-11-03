import streamlit as st
import pandas as pd
from datetime import datetime
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

@st.cache_resource
def get_loa_credentials():
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
        st.error(f"Credentials Error di database.py: {e}")
        return None

@st.cache_resource
def get_loa_services():
    creds = get_loa_credentials()
    if not creds: return None, ""
    try:
        s_sht = build("sheets", "v4", credentials=creds, cache_discovery=False)
        sid = ""
        try:
            if "google_drive" in st.secrets:
                sid = str(st.secrets["google_drive"].get("spreadsheet_id", "")).strip()
        except:
            pass
            
        return s_sht, sid
    except Exception as e:
        st.error(f"Service Error di database.py: {e}")
        return None, ""

def get_connection():
    return None

def init_db():
    pass

def get_districts():
    s_sht, sid = get_loa_services()
    if not s_sht or not sid: return pd.DataFrame()
    try:
        r = s_sht.spreadsheets().values().get(spreadsheetId=sid, range="districts!A1:Z").execute()
        v = r.get("values", [])
        if not v or len(v) < 2: return pd.DataFrame()
        headers = v[0]
        rows = [row + [""] * (len(headers) - len(row)) for row in v[1:]]
        df = pd.DataFrame(rows, columns=headers)
        
        df = df.dropna(how='all')
        if 'id' in df.columns:
            df['id'] = pd.to_numeric(df['id'], errors='coerce').fillna(0).astype(int)
            df = df[df['id'] > 0]
            return df.sort_values(by=['code', 'name']).reset_index(drop=True)
        return df
    except Exception as e:
        st.error(f"❌ database.py gagal membaca tab 'districts': {e}")
        return pd.DataFrame()

def add_district(code, name, category):
    df = get_districts()
    next_id = 1 if df.empty else int(df['id'].max()) + 1
    new_row = pd.DataFrame([{
        "id": next_id,
        "code": code.upper().strip(),
        "name": name.strip(),
        "category": category.strip(),
        "last_training_date": "",
        "next_due_date": ""
    }])
    updated_df = pd.concat([df, new_row], ignore_index=True).fillna('')
    
    s_sht, sid = get_loa_services()
    if s_sht and sid:
        body = {"values": [updated_df.columns.values.tolist()] + updated_df.values.tolist()}
        s_sht.spreadsheets().values().update(spreadsheetId=sid, range="districts!A1", valueInputOption="USER_ENTERED", body=body).execute()
        st.cache_data.clear()

def update_district_row(dist_id, code, name, category, last_date, due_date):
    df = get_districts()
    if not df.empty and 'id' in df.columns:
        idx = df[df['id'] == int(dist_id)].index
        if not idx.empty:
            df.loc[idx, 'code'] = code.upper().strip()
            df.loc[idx, 'name'] = name.strip()
            df.loc[idx, 'category'] = category.strip()
            df.loc[idx, 'last_training_date'] = str(last_date).strip()
            df.loc[idx, 'next_due_date'] = str(due_date).strip()
            
            s_sht, sid = get_loa_services()
            if s_sht and sid:
                body = {"values": [df.columns.values.tolist()] + df.fillna('').values.tolist()}
                s_sht.spreadsheets().values().update(spreadsheetId=sid, range="districts!A1", valueInputOption="USER_ENTERED", body=body).execute()
                st.cache_data.clear()

def delete_district_row(dist_id):
    df = get_districts()
    if not df.empty and 'id' in df.columns:
        df = df[df['id'] != int(dist_id)]
        s_sht, sid = get_loa_services()
        if s_sht and sid:
            s_sht.spreadsheets().values().clear(spreadsheetId=sid, range="districts!A1:Z").execute()
            body = {"values": [df.columns.values.tolist()] + df.fillna('').values.tolist()}
            if not df.empty:
                s_sht.spreadsheets().values().update(spreadsheetId=sid, range="districts!A1", valueInputOption="USER_ENTERED", body=body).execute()
            st.cache_data.clear()

def get_training_records():
    s_sht, sid = get_loa_services()
    if not s_sht or not sid: return pd.DataFrame()
    try:
        r = s_sht.spreadsheets().values().get(spreadsheetId=sid, range="training_records!A1:Z").execute()
        v = r.get("values", [])
        if not v or len(v) < 2: return pd.DataFrame()
        headers = v[0]
        rows = [row + [""] * (len(headers) - len(row)) for row in v[1:]]
        df = pd.DataFrame(rows, columns=headers)
        
        df = df.dropna(how='all')
        if 'id' in df.columns:
            df['id'] = pd.to_numeric(df['id'], errors='coerce').fillna(0).astype(int)
            df = df[df['id'] > 0]
            
            if 'nik' in df.columns:
                df['nik'] = df['nik'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
            if 'phone' in df.columns:
                df['phone'] = df['phone'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
            
            df = df.drop_duplicates(subset=['training_date', 'nik', 'cert_no_sj', 'cert_no_in'], keep='first')
            return df.sort_values(by='id', ascending=False).reset_index(drop=True)
        return df
    except Exception as e:
        st.error(f"❌ database.py gagal membaca tab 'training_records': {e}")
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
                if seq_num > max_seq:
                    max_seq = seq_num

    next_seq = max_seq + 1
    return f"{prefix_yymm}{next_seq:04d}"

def save_training_record(record_data):
    df = get_training_records()

    if not df.empty:
        cur_nik = str(record_data.get('nik', '')).strip()
        cur_date = str(record_data.get('training_date', ''))[:10]
        existing = df[
            (df['nik'].astype(str).str.strip() == cur_nik) &
            (df['training_date'].astype(str).str[:10] == cur_date)
        ]
        if not existing.empty:
            return False

    next_id = 1 if df.empty else int(df['id'].max()) + 1
    record_data['id'] = next_id

    target_dist_code = str(record_data.get('district', '')).strip()
    target_dist_name = str(record_data.get('district_name', '')).strip()

    new_row = pd.DataFrame([record_data])
    updated_df = pd.concat([df, new_row], ignore_index=True).fillna('')
    
    s_sht, sid = get_loa_services()
    if s_sht and sid:
        body = {"values": [updated_df.columns.values.tolist()] + updated_df.values.tolist()}
        s_sht.spreadsheets().values().update(spreadsheetId=sid, range="training_records!A1", valueInputOption="USER_ENTERED", body=body).execute()

    if record_data.get('status') == 'LULUS':
        t_date = record_data['training_date']
        try:
            dt_obj = datetime.strptime(str(t_date)[:10], "%Y-%m-%d").date()
            next_due = dt_obj.replace(year=dt_obj.year + 2).strftime("%Y-%m-%d")

            df_dist = get_districts()
            if target_dist_name:
                m_idx = df_dist[(df_dist['code'] == target_dist_code) & (df_dist['name'] == target_dist_name)].index
            else:
                m_idx = df_dist[df_dist['code'] == target_dist_code].index

            if not m_idx.empty:
                df_dist.loc[m_idx, 'last_training_date'] = str(t_date)
                df_dist.loc[m_idx, 'next_due_date'] = next_due
                if s_sht and sid:
                    d_body = {"values": [df_dist.columns.values.tolist()] + df_dist.fillna('').values.tolist()}
                    s_sht.spreadsheets().values().update(spreadsheetId=sid, range="districts!A1", valueInputOption="USER_ENTERED", body=d_body).execute()
        except Exception:
            pass

    st.cache_data.clear()
    return True

def delete_training_record(record_id):
    df = get_training_records()
    if not df.empty and 'id' in df.columns:
        df = df[df['id'] != int(record_id)]
        s_sht, sid = get_loa_services()
        if s_sht and sid:
            s_sht.spreadsheets().values().clear(spreadsheetId=sid, range="training_records!A1:Z").execute()
            body = {"values": [df.columns.values.tolist()] + df.fillna('').values.tolist()}
            if not df.empty:
                s_sht.spreadsheets().values().update(spreadsheetId=sid, range="training_records!A1", valueInputOption="USER_ENTERED", body=body).execute()
            st.cache_data.clear()

def reset_cert_sequence():
    st.cache_data.clear()

def clear_all_training_records():
    s_sht, sid = get_loa_services()
    if s_sht and sid:
        s_sht.spreadsheets().values().clear(spreadsheetId=sid, range="training_records!A1:Z").execute()
        cols = [
            "id", "training_date", "full_name", "nik", "phone",
            "job_role", "company", "district", "district_full", "score", "status",
            "cert_no_sj", "cert_no_in", "expiry_date"
        ]
        body = {"values": [cols]}
        s_sht.spreadsheets().values().update(spreadsheetId=sid, range="training_records!A1", valueInputOption="USER_ENTERED", body=body).execute()
        st.cache_data.clear()