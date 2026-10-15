import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta

# Inisialisasi koneksi Google Sheets resmi dari Streamlit
def get_connection():
    return st.connection("gsheets", type=GSheetsConnection)

def init_db():
    """Memeriksa dan membuat struktur tabel awal di Google Sheets jika masih kosong"""
    conn = get_connection()
    
    # 1. Pastikan Sheet 'districts' ada & terisi
    try:
        df_dist = conn.read(worksheet="districts", ttl=0)
    except Exception:
        df_dist = pd.DataFrame()
        
    if df_dist is None or df_dist.empty:
        default_districts = [
            # Sriwijaya Air
            {'id': 1, 'code': 'BEJ', 'name': 'Berau', 'category': 'Sriwijaya Air', 'last_training_date': None, 'next_due_date': None},
            {'id': 2, 'code': 'BPN', 'name': 'Balikpapan', 'category': 'Sriwijaya Air', 'last_training_date': None, 'next_due_date': None},
            {'id': 3, 'code': 'CGK', 'name': 'Cengkareng', 'category': 'Sriwijaya Air', 'last_training_date': '2025-12-05', 'next_due_date': '2027-12-05'},
            {'id': 4, 'code': 'DPS', 'name': 'Denpasar', 'category': 'Sriwijaya Air', 'last_training_date': None, 'next_due_date': None},
            {'id': 5, 'code': 'KNO', 'name': 'Medan', 'category': 'Sriwijaya Air', 'last_training_date': None, 'next_due_date': None},
            {'id': 6, 'code': 'PNK', 'name': 'Pontianak', 'category': 'Sriwijaya Air', 'last_training_date': None, 'next_due_date': None},
            {'id': 7, 'code': 'SUB', 'name': 'Surabaya', 'category': 'Sriwijaya Air', 'last_training_date': None, 'next_due_date': None},
            {'id': 8, 'code': 'UPG', 'name': 'Makassar', 'category': 'Sriwijaya Air', 'last_training_date': None, 'next_due_date': None},
            
            # NAM Air
            {'id': 9, 'code': 'BTH', 'name': 'Batam', 'category': 'NAM Air', 'last_training_date': None, 'next_due_date': None},
            {'id': 10, 'code': 'SRG', 'name': 'Semarang', 'category': 'NAM Air', 'last_training_date': None, 'next_due_date': None},
            {'id': 11, 'code': 'TMC', 'name': 'Tambolaka', 'category': 'NAM Air', 'last_training_date': None, 'next_due_date': None},
            
            # Regulated Agent
            {'id': 12, 'code': 'CGK', 'name': 'RA AAP', 'category': 'Regulated Agent', 'last_training_date': '2022-01-11', 'next_due_date': '2024-01-11'},
            {'id': 13, 'code': 'CGK', 'name': 'RA PERSADA', 'category': 'Regulated Agent', 'last_training_date': None, 'next_due_date': None},
            {'id': 14, 'code': 'CGK', 'name': 'RA BST', 'category': 'Regulated Agent', 'last_training_date': None, 'next_due_date': None},
            {'id': 15, 'code': 'CGK', 'name': 'RA CMU I', 'category': 'Regulated Agent', 'last_training_date': None, 'next_due_date': None},
            {'id': 16, 'code': 'CGK', 'name': 'RA CMU III', 'category': 'Regulated Agent', 'last_training_date': None, 'next_due_date': None},
            {'id': 17, 'code': 'CGK', 'name': 'RA DAPK', 'category': 'Regulated Agent', 'last_training_date': None, 'next_due_date': None},
            {'id': 18, 'code': 'CGK-APK', 'name': 'CGK (APK)', 'category': 'Regulated Agent', 'last_training_date': None, 'next_due_date': None},
            {'id': 19, 'code': 'CGK-DAP', 'name': 'CGK (DAPK)', 'category': 'Regulated Agent', 'last_training_date': None, 'next_due_date': None},
            {'id': 20, 'code': 'CGK-DBM', 'name': 'CGK (DBM)', 'category': 'Regulated Agent', 'last_training_date': None, 'next_due_date': None},
            {'id': 21, 'code': 'CGK-GAT', 'name': 'CGK (GATRANS)', 'category': 'Regulated Agent', 'last_training_date': None, 'next_due_date': None}
        ]
        df_init = pd.DataFrame(default_districts)
        conn.update(worksheet="districts", data=df_init)

    # 2. Inisialisasi sheet 'training_records'
    try:
        df_rec = conn.read(worksheet="training_records", ttl=0)
    except Exception:
        df_rec = pd.DataFrame()
    if df_rec is None or df_rec.empty:
        cols = ['id', 'training_date', 'full_name', 'nik', 'phone', 'job_role', 'company', 
                'district', 'score', 'status', 'cert_no_sj', 'cert_no_in', 'expiry_date']
        conn.update(worksheet="training_records", data=pd.DataFrame(columns=cols))

    # 3. Inisialisasi sheet 'cert_sequence'
    try:
        df_seq = conn.read(worksheet="cert_sequence", ttl=0)
    except Exception:
        df_seq = pd.DataFrame()
    if df_seq is None or df_seq.empty:
        cols = ['airline', 'current_seq', 'batch_start_date']
        conn.update(worksheet="cert_sequence", data=pd.DataFrame(columns=cols))

def get_districts():
    """Mengambil seluruh data distrik dari Google Sheets urut alfabet"""
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
    """Menambah distrik baru langsung ke Google Sheets"""
    conn = get_connection()
    df = get_districts()
    next_id = 1 if df.empty else int(df['id'].max()) + 1
    new_row = pd.DataFrame([{
        'id': next_id,
        'code': code.strip().upper(),
        'name': name.strip(),
        'category': category.strip(),
        'last_training_date': None,
        'next_due_date': None
    }])
    updated_df = pd.concat([df, new_row], ignore_index=True)
    conn.update(worksheet="districts", data=updated_df)

def update_district_row(dist_id, code, name, category, last_date, due_date):
    """Memperbarui baris data distrik di Google Sheets"""
    conn = get_connection()
    df = get_districts()
    idx = df[df['id'] == int(dist_id)].index
    if not idx.empty:
        df.loc[idx, 'code'] = code.strip().upper()
        df.loc[idx, 'name'] = name.strip()
        df.loc[idx, 'category'] = category.strip()
        df.loc[idx, 'last_training_date'] = last_date if last_date else None
        df.loc[idx, 'next_due_date'] = due_date if due_date else None
        conn.update(worksheet="districts", data=df)

def delete_district_row(dist_id):
    """Menghapus baris distrik di Google Sheets berdasarkan ID"""
    conn = get_connection()
    df = get_districts()
    updated_df = df[df['id'] != int(dist_id)].reset_index(drop=True)
    conn.update(worksheet="districts", data=updated_df)

def get_training_records():
    """Mengambil riwayat data training dari Google Sheets"""
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
    """Menyimpan record training peserta dan update tanggal reminder distrik di Google Sheets"""
    conn = get_connection()
    df = get_training_records()
    next_id = 1 if df.empty else int(df['id'].max()) + 1
    record_data['id'] = next_id
    new_row = pd.DataFrame([record_data])
    updated_df = pd.concat([df, new_row], ignore_index=True)
    conn.update(worksheet="training_records", data=updated_df)

    # Perbarui jadwal recurrent di master distrik jika peserta lulus
    if record_data.get('status') == 'LULUS':
        t_date = record_data['training_date']
        dt_obj = datetime.strptime(str(t_date)[:10], "%Y-%m-%d").date()
        next_due = dt_obj.replace(year=dt_obj.year + 2).strftime("%Y-%m-%d")
        
        df_dist = get_districts()
        m_idx = df_dist[df_dist['code'] == record_data['district']].index
        if not m_idx.empty:
            df_dist.loc[m_idx, 'last_training_date'] = t_date
            df_dist.loc[m_idx, 'next_due_date'] = next_due
            conn.update(worksheet="districts", data=df_dist)

def delete_training_record(record_id):
    """Menghapus record spesifik di Google Sheets"""
    conn = get_connection()
    df = get_training_records()
    updated_df = df[df['id'] != int(record_id)].reset_index(drop=True)
    conn.update(worksheet="training_records", data=updated_df)

def clear_all_training_records():
    """Mengosongkan seluruh riwayat ujian di Google Sheets"""
    conn = get_connection()
    cols = ['id', 'training_date', 'full_name', 'nik', 'phone', 'job_role', 'company', 
            'district', 'score', 'status', 'cert_no_sj', 'cert_no_in', 'expiry_date']
    conn.update(worksheet="training_records", data=pd.DataFrame(columns=cols))

def get_next_cert_number(airline):
    """
    Format nomor sertifikat: YYMMxxxx (contoh: 26100001)
    Sequence otomatis reset setiap siklus 24 bulan dari batch pertama di Google Sheets.
    """
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

    conn.update(worksheet="cert_sequence", data=df_seq)
    return f"{prefix_yymm}{next_seq:04d}"

def reset_cert_sequence():
    """Mereset sequence nomor urut sertifikat ke awal di Google Sheets"""
    conn = get_connection()
    cols = ['airline', 'current_seq', 'batch_start_date']
    conn.update(worksheet="cert_sequence", data=pd.DataFrame(columns=cols))