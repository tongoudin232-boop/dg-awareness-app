import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta

def get_connection():
    return st.connection("gsheets", type=GSheetsConnection)

def init_db():
    conn = get_connection()
    try:
        df_dist = conn.read(worksheet="districts", ttl=0)
        if df_dist is not None and not df_dist.empty:
            return
    except Exception:
        pass

    try:
        default_districts = [
            # Sriwijaya Air
            {'id': 1, 'code': 'BEJ', 'name': 'Berau', 'category': 'Sriwijaya Air', 'last_training_date': '', 'next_due_date': ''},
            {'id': 2, 'code': 'BPN', 'name': 'Balikpapan', 'category': 'Sriwijaya Air', 'last_training_date': '', 'next_due_date': ''},
            {'id': 3, 'code': 'CGK', 'name': 'Cengkareng', 'category': 'Sriwijaya Air', 'last_training_date': '2025-12-05', 'next_due_date': '2027-12-05'},
            {'id': 4, 'code': 'DPS', 'name': 'Denpasar', 'category': 'Sriwijaya Air', 'last_training_date': '', 'next_due_date': ''},
            {'id': 5, 'code': 'KNO', 'name': 'Medan', 'category': 'Sriwijaya Air', 'last_training_date': '', 'next_due_date': ''},
            {'id': 6, 'code': 'PNK', 'name': 'Pontianak', 'category': 'Sriwijaya Air', 'last_training_date': '', 'next_due_date': ''},
            {'id': 7, 'code': 'SUB', 'name': 'Surabaya', 'category': 'Sriwijaya Air', 'last_training_date': '', 'next_due_date': ''},
            {'id': 8, 'code': 'UPG', 'name': 'Makassar', 'category': 'Sriwijaya Air', 'last_training_date': '', 'next_due_date': ''},
            
            # NAM Air
            {'id': 9, 'code': 'BTH', 'name': 'Batam', 'category': 'NAM Air', 'last_training_date': '', 'next_due_date': ''},
            {'id': 10, 'code': 'SRG', 'name': 'Semarang', 'category': 'NAM Air', 'last_training_date': '', 'next_due_date': ''},
            {'id': 11, 'code': 'TMC', 'name': 'Tambolaka', 'category': 'NAM Air', 'last_training_date': '', 'next_due_date': ''},
            
            # Regulated Agent
            {'id': 12, 'code': 'CGK', 'name': 'RA AAP', 'category': 'Regulated Agent', 'last_training_date': '2022-01-11', 'next_due_date': '2024-01-11'},
            {'id': 13, 'code': 'CGK', 'name': 'RA PERSADA', 'category': 'Regulated Agent', 'last_training_date': '', 'next_due_date': ''},
            {'id': 14, 'code': 'CGK', 'name': 'RA BST', 'category': 'Regulated Agent', 'last_training_date': '', 'next_due_date': ''},
            {'id': 15, 'code': 'CGK', 'name': 'RA CMU I', 'category': 'Regulated Agent', 'last_training_date': '', 'next_due_date': ''},
            {'id': 16, 'code': 'CGK', 'name': 'RA CMU III', 'category': 'Regulated Agent', 'last_training_date': '', 'next_due_date': ''},
            {'id': 17, 'code': 'CGK', 'name': 'RA DAPK', 'category': 'Regulated Agent', 'last_training_date': '', 'next_due_date': ''},
            {'id': 18, 'code': 'CGK-APK', 'name': 'CGK (APK)', 'category': 'Regulated Agent', 'last_training_date': '', 'next_due_date': ''},
            {'id': 19, 'code': 'CGK-DAP', 'name': 'CGK (DAPK)', 'category': 'Regulated Agent', 'last_training_date': '', 'next_due_date': ''},
            {'id': 20, 'code': 'CGK-DBM', 'name': 'CGK (DBM)', 'category': 'Regulated Agent', 'last_training_date': '', 'next_due_date': ''},
            {'id': 21, 'code': 'CGK-GAT', 'name': 'CGK (GATRANS)', 'category': 'Regulated Agent', 'last_training_date': '', 'next_due_date': ''}
        ]
        df_init = pd.DataFrame(default_districts).fillna('')
        conn.update(worksheet="districts", data=df_init)
    except Exception:
        pass

def get_districts():
    conn = get_connection()
    try:
        df = conn.read(worksheet="districts", ttl=0)
        if df is not None and not df.empty:
            df['id'] = pd.to_numeric(df['id'], errors='coerce').fillna(0).astype(int)
            return df.sort_values(by=['code', 'name'], ascending=True).reset_index(drop=True)
    except Exception:
        pass
    return pd.DataFrame()

def add_district(code, name, category):
    conn = get_connection()
    df = get_districts()
    next_id = 1 if df.empty else int(df['id'].max()) + 1
    new_row = pd.DataFrame([{
        'id': next_id,
        'code': code.strip().upper(),
        'name': name.strip(),
        'category': category.strip(),
        'last_training_date': '',
        'next_due_date': ''
    }])
    updated_df = pd.concat([df, new_row], ignore_index=True).fillna('')
    conn.update(worksheet="districts", data=updated_df)

def update_district_row(dist_id, code, name, category, last_date, due_date):
    conn = get_connection()
    df = get_districts()
    idx = df[df['id'] == int(dist_id)].index
    if not idx.empty:
        df.loc[idx, 'code'] = code.strip().upper()
        df.loc[idx, 'name'] = name.strip()
        df.loc[idx, 'category'] = category.strip()
        df.loc[idx, 'last_training_date'] = last_date if last_date else ''
        df.loc[idx, 'next_due_date'] = due_date if due_date else ''
        conn.update(worksheet="districts", data=df.fillna(''))

def delete_district_row(dist_id):
    conn = get_connection()
    df = get_districts()
    updated_df = df[df['id'] != int(dist_id)].reset_index(drop=True).fillna('')
    conn.update(worksheet="districts", data=updated_df)

def get_training_records():
    conn = get_connection()
    try:
        df = conn.read(worksheet="training_records", ttl=0)
        if df is not None and not df.empty:
            df['id'] = pd.to_numeric(df['id'], errors='coerce').fillna(0).astype(int)
            return df.sort_values(by='id', ascending=False).reset_index(drop=True)
    except Exception:
        pass
    return pd.DataFrame()

def save_training_record(record_data):
    conn = get_connection()
    df = get_training_records()
    next_id = 1 if df.empty else int(df['id'].max()) + 1
    record_data['id'] = next_id
    new_row = pd.DataFrame([record_data])
    updated_df = pd.concat([df, new_row], ignore_index=True).fillna('')
    conn.update(worksheet="training_records", data=updated_df)

    if record_data.get('status') == 'LULUS':
        t_date = record_data['training_date']
        try:
            dt_obj = datetime.strptime(str(t_date)[:10], "%Y-%m-%d").date()
            next_due = dt_obj.replace(year=dt_obj.year + 2).strftime("%Y-%m-%d")
            
            df_dist = get_districts()
            m_idx = df_dist[df_dist['code'] == record_data['district']].index
            if not m_idx.empty:
                df_dist.loc[m_idx, 'last_training_date'] = str(t_date)
                df_dist.loc[m_idx, 'next_due_date'] = next_due
                conn.update(worksheet="districts", data=df_dist.fillna(''))
        except Exception:
            pass

def delete_training_record(record_id):
    conn = get_connection()
    df = get_training_records()
    updated_df = df[df['id'] != int(record_id)].reset_index(drop=True).fillna('')
    conn.update(worksheet="training_records", data=updated_df)

def clear_all_training_records():
    conn = get_connection()
    cols = ['id', 'training_date', 'full_name', 'nik', 'phone', 'job_role', 'company', 
            'district', 'score', 'status', 'cert_no_sj', 'cert_no_in', 'expiry_date']
    conn.update(worksheet="training_records", data=pd.DataFrame(columns=cols))

def get_next_cert_number(airline):
    conn = get_connection()
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    prefix_yymm = now.strftime("%y%m")

    try:
        df_seq = conn.read(worksheet="cert_sequence", ttl=0)
    except Exception:
        df_seq = pd.DataFrame()

    if df_seq is None or df_seq.empty:
        df_seq = pd.DataFrame(columns=['airline', 'current_seq', 'batch_start_date'])

    idx = df_seq[df_seq['airline'] == airline].index

    if idx.empty:
        next_seq = 1
        new_row = pd.DataFrame([{'airline': airline, 'current_seq': next_seq, 'batch_start_date': today_str}])
        df_seq = pd.concat([df_seq, new_row], ignore_index=True)
    else:
        current_seq = int(df_seq.loc[idx[0], 'current_seq'])
        start_date_str = str(df_seq.loc[idx[0], 'batch_start_date'])
        try:
            start_date = datetime.strptime(start_date_str[:10], "%Y-%m-%d")
            diff_months = (now.year - start_date.year) * 12 + (now.month - start_date.month)
        except Exception:
            diff_months = 0

        if diff_months >= 24:
            next_seq = 1
            df_seq.loc[idx[0], 'current_seq'] = next_seq
            df_seq.loc[idx[0], 'batch_start_date'] = today_str
        else:
            next_seq = current_seq + 1
            df_seq.loc[idx[0], 'current_seq'] = next_seq

    conn.update(worksheet="cert_sequence", data=df_seq.fillna(''))
    return f"{prefix_yymm}{next_seq:04d}"

def reset_cert_sequence():
    conn = get_connection()
    cols = ['airline', 'current_seq', 'batch_start_date']
    conn.update(worksheet="cert_sequence", data=pd.DataFrame(columns=cols))