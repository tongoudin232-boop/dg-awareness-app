import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

def get_connection():
    """Mengambil koneksi Google Sheets API via Streamlit GSheetsConnection"""
    return st.connection("gsheets", type=GSheetsConnection)

def init_db():
    """
    Inisialisasi pasif.
    Tidak memaksa conn.update() agar tidak memicu error gspread API saat startup.
    """
    pass


def get_districts():
    """Mengambil daftar seluruh distrik dari Google Sheets"""
    conn = get_connection()
    try:
        df = conn.read(worksheet="districts", ttl=2)
        if df is not None and not df.empty:
            df = df.dropna(how='all')
            if 'id' in df.columns:
                df['id'] = pd.to_numeric(df['id'], errors='coerce').fillna(0).astype(int)
                df = df[df['id'] > 0]
                return df.sort_values(by=['code', 'name']).reset_index(drop=True)
    except Exception:
        pass
    return pd.DataFrame()


def add_district(code, name, category):
    """Menambahkan distrik baru ke tabel Google Sheets"""
    conn = get_connection()
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
    updated_df = pd.concat([df, new_row], ignore_index=True)
    conn.update(worksheet="districts", data=updated_df.fillna(''))
    st.cache_data.clear()


def update_district_row(dist_id, code, name, category, last_date, due_date):
    """Memperbarui informasi data distrik tertentu"""
    conn = get_connection()
    df = get_districts()
    if not df.empty and 'id' in df.columns:
        idx = df[df['id'] == int(dist_id)].index
        if not idx.empty:
            df.loc[idx, 'code'] = code.upper().strip()
            df.loc[idx, 'name'] = name.strip()
            df.loc[idx, 'category'] = category.strip()
            df.loc[idx, 'last_training_date'] = str(last_date).strip()
            df.loc[idx, 'next_due_date'] = str(due_date).strip()
            conn.update(worksheet="districts", data=df.fillna(''))
            st.cache_data.clear()


def delete_district_row(dist_id):
    """Menghapus distrik berdasarkan ID"""
    conn = get_connection()
    df = get_districts()
    if not df.empty and 'id' in df.columns:
        df = df[df['id'] != int(dist_id)]
        conn.update(worksheet="districts", data=df.fillna(''))
        st.cache_data.clear()


def get_training_records():
    """Mengambil riwayat data training dan otomatis menyaring baris kembar identik"""
    conn = get_connection()
    try:
        df = conn.read(worksheet="training_records", ttl=2)
        if df is not None and not df.empty:
            df = df.dropna(how='all')
            if 'id' in df.columns:
                df['id'] = pd.to_numeric(df['id'], errors='coerce').fillna(0).astype(int)
                df = df[df['id'] > 0]
                
                # Pembersihan format string NIK dan nomor handphone
                if 'nik' in df.columns:
                    df['nik'] = df['nik'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
                if 'phone' in df.columns:
                    df['phone'] = df['phone'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
                
                # Saring duplikasi baris berdasarkan NIK, tanggal, dan nomor sertifikat
                df = df.drop_duplicates(subset=['training_date', 'nik', 'cert_no_sj', 'cert_no_in'], keep='first')
                return df.sort_values(by='id', ascending=False).reset_index(drop=True)
    except Exception:
        pass
    return pd.DataFrame()


def get_next_cert_number(airline):
    """
    Penomoran sertifikat urut format YYMMxxxx (misal: 26100001).
    Membaca nomor tertinggi langsung dari data riwayat training_records
    sehingga urutan tidak akan pernah ter-reset kembali ke 0001.
    """
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
    """Menyimpan record ujian peserta dengan proteksi anti-submit ganda"""
    conn = get_connection()
    df = get_training_records()

    # Validasi pencegahan submit ganda jika NIK dan tanggal pelatihan identik
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
    conn.update(worksheet="training_records", data=updated_df)

    # Perbarui recurrent distrik jika status LULUS
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
                conn.update(worksheet="districts", data=df_dist.fillna(''))
        except Exception:
            pass

    st.cache_data.clear()
    return True


def delete_training_record(record_id):
    """Menghapus data hasil training berdasarkan ID peserta"""
    conn = get_connection()
    df = get_training_records()
    if not df.empty and 'id' in df.columns:
        df = df[df['id'] != int(record_id)]
        conn.update(worksheet="training_records", data=df.fillna(''))
        st.cache_data.clear()


def reset_cert_sequence():
    """Membersihkan cache data agar data terbaru langsung terbaca"""
    st.cache_data.clear()


def clear_all_training_records():
    """Mengosongkan seluruh tabel riwayat ujian"""
    conn = get_connection()
    empty_records = pd.DataFrame(columns=[
        "id", "training_date", "full_name", "nik", "phone",
        "job_role", "company", "district", "district_full", "score", "status",
        "cert_no_sj", "cert_no_in", "expiry_date"
    ])
    conn.update(worksheet="training_records", data=empty_records)
    st.cache_data.clear()