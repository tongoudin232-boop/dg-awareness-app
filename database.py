import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta

def get_connection():
    return st.connection("gsheets", type=GSheetsConnection)

def init_db():
    """
    Hanya memastikan sheet dapat diakses tanpa menimpa data yang sudah ada.
    Tidak akan pernah menyuntikkan ulang data distrik default agar distrik yang dihapus tidak muncul lagi.
    """
    pass

def get_districts():
    """Mengambil seluruh data distrik dari Google Sheets urut alfabet"""
    conn = get_connection()
    try:
        # Cache pendek 2 detik agar UI sangat cepat dan tidak kena rate limit Google
        df = conn.read(worksheet="districts", ttl=2)
        if df is not None and not df.empty:
            df = df.dropna(how='all')
            if 'id' in df.columns:
                df['id'] = pd.to_numeric(df['id'], errors='coerce').fillna(0).astype(int)
                # Bersihkan baris kosong / id 0
                df = df[df['id'] > 0]
                return df.sort_values(by=['code', 'name'], ascending=True).reset_index(drop=True)
    except Exception as e:
        st.warning(f"Menghubungkan ke Google Sheets: {e}")
    return pd.DataFrame()

def add_district(code, name, category):
    """Menambah distrik baru langsung ke Google Sheets"""
    conn = get_connection()
    df = get_districts()
    next_id = 1 if df.empty else int(df['id'].max()) + 1
    new_row = pd.DataFrame([{
        'id': next_id,
        'code': str(code).strip().upper(),
        'name': str(name).strip(),
        'category': str(category).strip(),
        'last_training_date': '',
        'next_due_date': ''
    }])
    updated_df = pd.concat([df, new_row], ignore_index=True).fillna('')
    conn.update(worksheet="districts", data=updated_df)
    st.cache_data.clear()

def update_district_row(dist_id, code, name, category, last_date, due_date):
    """Memperbarui baris data distrik di Google Sheets"""
    conn = get_connection()
    df = get_districts()
    idx = df[df['id'] == int(dist_id)].index
    if not idx.empty:
        df.loc[idx, 'code'] = str(code).strip().upper()
        df.loc[idx, 'name'] = str(name).strip()
        df.loc[idx, 'category'] = str(category).strip()
        df.loc[idx, 'last_training_date'] = str(last_date) if last_date else ''
        df.loc[idx, 'next_due_date'] = str(due_date) if due_date else ''
        conn.update(worksheet="districts", data=df.fillna(''))
        st.cache_data.clear()

def delete_district_row(dist_id):
    """Menghapus baris distrik di Google Sheets secara permanen"""
    conn = get_connection()
    df = get_districts()
    # Filter buang ID yang dipilih
    updated_df = df[df['id'] != int(dist_id)].reset_index(drop=True).fillna('')
    conn.update(worksheet="districts", data=updated_df)
    st.cache_data.clear()

def get_training_records():
    """Mengambil riwayat data training dari Google Sheets"""
    conn = get_connection()
    try:
        df = conn.read(worksheet="training_records", ttl=2)
        if df is not None and not df.empty:
            df = df.dropna(how='all')
            if 'id' in df.columns:
                df['id'] = pd.to_numeric(df['id'], errors='coerce').fillna(0).astype(int)
                df = df[df['id'] > 0]
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
    st.cache_data.clear()

def delete_training_record(record_id):
    """Menghapus record spesifik di Google Sheets"""
    conn = get_connection()
    df = get_training_records()
    updated_df = df[df['id'] != int(record_id)].reset_index(drop=True).fillna('')
    conn.update(worksheet="training_records", data=updated_df)
    st.cache_data.clear()

def clear_all_training_records():
    """Mengosongkan seluruh riwayat ujian di Google Sheets"""
    conn = get_connection()
    cols = ['id', 'training_date', 'full_name', 'nik', 'phone', 'job_role', 'company', 
            'district', 'score', 'status', 'cert_no_sj', 'cert_no_in', 'expiry_date']
    conn.update(worksheet="training_records", data=pd.DataFrame(columns=cols))
    st.cache_data.clear()

def get_next_cert_number(airline):
    """Penomoran sertifikat resmi YYMMxxxx"""
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
    """Mereset urutan nomor sertifikat"""
    conn = get_connection()
    cols = ['airline', 'current_seq', 'batch_start_date']
    conn.update(worksheet="cert_sequence", data=pd.DataFrame(columns=cols))
    st.cache_data.clear()