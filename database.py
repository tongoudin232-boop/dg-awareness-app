import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# Urutan 13 kolom baku persis sesuai header A1:M1 di Google Sheets training_records
SHEET_COLUMNS = [
    "training_date", "full_name", "nik", "phone",
    "job_role", "company", "district", "score", "status",
    "cert_no_sj", "cert_no_in", "expiry_date", "id"
]


def get_connection():
    """Mengambil koneksi Google Sheets API via Streamlit GSheetsConnection"""
    return st.connection("gsheets", type=GSheetsConnection)


def init_db():
    """Inisialisasi pasif tanpa menimpa data yang sudah ada"""
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
    """Mengambil riwayat data training dengan 13 kolom baku A-M"""
    conn = get_connection()
    try:
        df = conn.read(worksheet="training_records", ttl=2)
        if df is not None and not df.empty:
            df = df.dropna(how='all')
            if 'id' in df.columns:
                df['id'] = pd.to_numeric(df['id'], errors='coerce').fillna(0).astype(int)
                df = df[(df['id'] > 0) & (df['id'] < 1000000)]

                for col in SHEET_COLUMNS:
                    if col not in df.columns:
                        df[col] = ''
                df = df[SHEET_COLUMNS]

                df['nik'] = df['nik'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
                df['phone'] = df['phone'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
                df['cert_no_sj'] = df['cert_no_sj'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
                df['cert_no_in'] = df['cert_no_in'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()

                df = df.drop_duplicates(subset=['training_date', 'nik', 'cert_no_sj', 'cert_no_in'], keep='first')
                return df.sort_values(by='id', ascending=False).reset_index(drop=True)
    except Exception:
        pass
    return pd.DataFrame(columns=SHEET_COLUMNS)


def get_next_cert_number(airline):
    """
    Penomoran sertifikat urut format YYMMxxxx yang unik di seluruh kolom SJ & IN.
    SJ mendapat urutan tertinggi + 1, dan IN mendapat urutan tertinggi + 2.
    """
    now = datetime.now()
    prefix_yymm = now.strftime("%y%m")

    df_records = get_training_records()
    max_seq = 0

    if not df_records.empty:
        all_certs = []
        if 'cert_no_sj' in df_records.columns:
            all_certs.extend(df_records['cert_no_sj'].dropna().astype(str).tolist())
        if 'cert_no_in' in df_records.columns:
            all_certs.extend(df_records['cert_no_in'].dropna().astype(str).tolist())

        for raw_val in all_certs:
            c_val = raw_val.strip().replace('.0', '')
            if c_val.startswith(prefix_yymm) and len(c_val) == 8 and c_val[4:].isdigit():
                seq_num = int(c_val[4:])
                if seq_num > max_seq:
                    max_seq = seq_num

    offset = 1 if airline == 'SJ' else 2
    next_seq = max_seq + offset
    return f"{prefix_yymm}{next_seq:04d}"


def save_training_record(record_data):
    """Menyimpan record ujian peserta dengan 13 kolom terkunci (A-M)"""
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

    target_dist_code = str(record_data.get('district', '')).strip()
    target_dist_name = str(record_data.get('district_name', '')).strip()

    clean_row = {
        "training_date": str(record_data.get('training_date', '')),
        "full_name": str(record_data.get('full_name', '')),
        "nik": str(record_data.get('nik', '')),
        "phone": str(record_data.get('phone', '')),
        "job_role": str(record_data.get('job_role', '')),
        "company": str(record_data.get('company', '')),
        "district": target_dist_code,
        "score": record_data.get('score', 0),
        "status": str(record_data.get('status', '')),
        "cert_no_sj": str(record_data.get('cert_no_sj', '-')),
        "cert_no_in": str(record_data.get('cert_no_in', '-')),
        "expiry_date": str(record_data.get('expiry_date', '-')),
        "id": next_id
    }

    # Baca ulang data asli sheet agar urutan baris tetap terjaga rapi
    raw_df = conn.read(worksheet="training_records", ttl=0)
    if raw_df is not None and not raw_df.empty:
        raw_df = raw_df.dropna(how='all')
        for col in SHEET_COLUMNS:
            if col not in raw_df.columns:
                raw_df[col] = ''
        raw_df = raw_df[SHEET_COLUMNS]
    else:
        raw_df = pd.DataFrame(columns=SHEET_COLUMNS)

    new_row_df = pd.DataFrame([clean_row])[SHEET_COLUMNS]
    updated_df = pd.concat([raw_df, new_row_df], ignore_index=True).fillna('')
    conn.update(worksheet="training_records", data=updated_df)

    # Perbarui recurrent distrik jika status LULUS
    if clean_row['status'] == 'LULUS':
        t_date = clean_row['training_date']
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
    raw_df = conn.read(worksheet="training_records", ttl=0)
    if raw_df is not None and not raw_df.empty and 'id' in raw_df.columns:
        raw_df = raw_df.dropna(how='all')
        for col in SHEET_COLUMNS:
            if col not in raw_df.columns:
                raw_df[col] = ''
        raw_df['id_num'] = pd.to_numeric(raw_df['id'], errors='coerce').fillna(0).astype(int)
        raw_df = raw_df[raw_df['id_num'] != int(record_id)]
        raw_df = raw_df[SHEET_COLUMNS]
        conn.update(worksheet="training_records", data=raw_df.fillna(''))
        st.cache_data.clear()


def reset_cert_sequence():
    """Membersihkan cache data agar data terbaru langsung terbaca"""
    st.cache_data.clear()


def clear_all_training_records():
    """Mengosongkan seluruh tabel riwayat ujian dengan 13 kolom baku"""
    conn = get_connection()
    empty_records = pd.DataFrame(columns=SHEET_COLUMNS)
    conn.update(worksheet="training_records", data=empty_records)
    st.cache_data.clear()