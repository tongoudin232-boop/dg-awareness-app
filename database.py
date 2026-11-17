import re
import streamlit as st
import pandas as pd
from datetime import datetime
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# ID Asli Spreadsheet DG_Awareness_Database (huruf I besar ganda)
DEFAULT_SPREADSHEET_ID = "1wr7cAII_gMDTjyK6yeScysAkOLcgoGfyXYXFtx7cFrs".strip()

TAB_RECORDS = "training_records"
TAB_DISTRICTS = "districts"

# Urutan 13 kolom baku persis sesuai header A1:M1 di Google Sheets training_records
SHEET_COLUMNS = [
    "training_date", "full_name", "nik", "phone",
    "job_role", "company", "district", "score", "status",
    "cert_no_sj", "cert_no_in", "expiry_date", "id"
]

DISTRICT_COLUMNS = [
    "id", "code", "name", "category", "last_training_date", "next_due_date"
]


def get_sheets_config():
    """Mengambil kredensial dan Spreadsheet ID milik DG Awareness dari st.secrets"""
    creds_info = None
    sheet_id = DEFAULT_SPREADSHEET_ID

    try:
        # 1. Prioritaskan [connections.gsheets] yang dipakai DG Awareness sebelumnya
        if "connections" in st.secrets and "gsheets" in st.secrets["connections"]:
            gs_sec = dict(st.secrets["connections"]["gsheets"])
            if "private_key" in gs_sec:
                creds_info = gs_sec
            raw_ss = str(gs_sec.get("spreadsheet", "")).strip()
            if raw_ss:
                match = re.search(r"/d/([a-zA-Z0-9-_]+)", raw_ss)
                if match:
                    sheet_id = match.group(1)
                elif len(raw_ss) > 20 and "/" not in raw_ss:
                    sheet_id = raw_ss

        # 2. Fallback ke [gcp_service_account] jika [connections.gsheets] tidak ada
        if not creds_info and "gcp_service_account" in st.secrets:
            creds_info = dict(st.secrets["gcp_service_account"])

        if not creds_info and "private_key" in st.secrets:
            creds_info = dict(st.secrets)

        if not creds_info or "private_key" not in creds_info:
            return None, sheet_id, ""

        creds_info["private_key"] = str(creds_info["private_key"]).replace("\\n", "\n").strip()
        client_email = str(creds_info.get("client_email", "")).strip()
        creds = Credentials.from_service_account_info(creds_info, scopes=SCOPES)
        service = build("sheets", "v4", credentials=creds, cache_discovery=False)
        return service, sheet_id, client_email
    except Exception:
        return None, sheet_id, ""


def init_db():
    """Inisialisasi pasif tanpa menimpa data yang sudah ada"""
    pass


def get_districts():
    """Mengambil daftar seluruh distrik dari tab 'districts' Google Sheets"""
    service, sheet_id, client_email = get_sheets_config()
    if not service:
        st.error("⚠️ Kredensial Google Sheets tidak ditemukan di Secrets.")
        return pd.DataFrame()

    try:
        res = service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range=f"{TAB_DISTRICTS}!A1:F"
        ).execute()
        values = res.get("values", [])
        if values and len(values) > 1:
            headers = [str(h).strip() for h in values[0]]
            rows = [r + [""] * (len(headers) - len(r)) for r in values[1:]]
            df = pd.DataFrame(rows, columns=headers)
            for col in DISTRICT_COLUMNS:
                if col not in df.columns:
                    df[col] = ""
            df['id'] = pd.to_numeric(df['id'], errors='coerce').fillna(0).astype(int)
            df = df[df['id'] > 0]
            return df.sort_values(by=['code', 'name']).reset_index(drop=True)
    except Exception as e:
        st.error(f"⚠️ Gagal membaca tabel districts (pastikan email `{client_email}` sudah menjadi Editor di Google Sheets): {e}")

    return pd.DataFrame()


def add_district(code, name, category):
    """Menambahkan distrik baru ke tab 'districts' Google Sheets"""
    service, sheet_id, _ = get_sheets_config()
    if not service:
        return

    df = get_districts()
    next_id = 1 if df.empty else int(df['id'].max()) + 1
    row_values = [
        str(next_id),
        code.upper().strip(),
        name.strip(),
        category.strip(),
        "",
        ""
    ]
    try:
        service.spreadsheets().values().append(
            spreadsheetId=sheet_id,
            range=f"{TAB_DISTRICTS}!A1:F1",
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body={"values": [row_values]}
        ).execute()
        st.cache_data.clear()
    except Exception as e:
        st.error(f"Gagal menambah distrik: {e}")


def update_district_row(dist_id, code, name, category, last_date, due_date):
    """Memperbarui informasi data distrik tertentu"""
    service, sheet_id, _ = get_sheets_config()
    if not service:
        return

    try:
        res = service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range=f"{TAB_DISTRICTS}!A1:F"
        ).execute()
        values = res.get("values", [])
        target_row = -1
        for i, row in enumerate(values):
            if i == 0:
                continue
            if row and str(row[0]).strip() == str(dist_id).strip():
                target_row = i + 1
                break

        if target_row != -1:
            service.spreadsheets().values().update(
                spreadsheetId=sheet_id,
                range=f"{TAB_DISTRICTS}!B{target_row}:F{target_row}",
                valueInputOption="USER_ENTERED",
                body={"values": [[
                    code.upper().strip(),
                    name.strip(),
                    category.strip(),
                    str(last_date).strip(),
                    str(due_date).strip()
                ]]}
            ).execute()
            st.cache_data.clear()
    except Exception as e:
        st.error(f"Gagal mengubah distrik: {e}")


def delete_district_row(dist_id):
    """Menghapus distrik berdasarkan ID"""
    service, sheet_id, _ = get_sheets_config()
    if not service:
        return

    try:
        res = service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range=f"{TAB_DISTRICTS}!A1:A"
        ).execute()
        values = res.get("values", [])
        row_idx = -1
        for i, row in enumerate(values):
            if i == 0:
                continue
            if row and str(row[0]).strip() == str(dist_id).strip():
                row_idx = i
                break

        if row_idx != -1:
            meta = service.spreadsheets().get(spreadsheetId=sheet_id).execute()
            gid = next(
                (s["properties"]["sheetId"] for s in meta.get("sheets", []) if s["properties"]["title"] == TAB_DISTRICTS),
                None
            )
            if gid is not None:
                service.spreadsheets().batchUpdate(
                    spreadsheetId=sheet_id,
                    body={"requests": [{
                        "deleteDimension": {
                            "range": {
                                "sheetId": gid,
                                "dimension": "ROWS",
                                "startIndex": row_idx,
                                "endIndex": row_idx + 1
                            }
                        }
                    }]}
                ).execute()
                st.cache_data.clear()
    except Exception as e:
        st.error(f"Gagal menghapus distrik: {e}")


def get_training_records():
    """Mengambil riwayat data training dengan 13 kolom baku A-M"""
    service, sheet_id, client_email = get_sheets_config()
    if not service:
        st.error("⚠️ Kredensial Google Sheets tidak ditemukan di Secrets.")
        return pd.DataFrame(columns=SHEET_COLUMNS)

    try:
        res = service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range=f"{TAB_RECORDS}!A1:M"
        ).execute()
        values = res.get("values", [])
        if values and len(values) > 1:
            headers = [str(h).strip() for h in values[0]]
            rows = [r + [""] * (len(headers) - len(r)) for r in values[1:]]
            df = pd.DataFrame(rows, columns=headers)

            for col in SHEET_COLUMNS:
                if col not in df.columns:
                    df[col] = ""
            df = df[SHEET_COLUMNS]

            df['id'] = pd.to_numeric(df['id'], errors='coerce').fillna(0).astype(int)
            df = df[(df['id'] > 0) & (df['id'] < 1000000)]

            df['nik'] = df['nik'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
            df['phone'] = df['phone'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
            df['cert_no_sj'] = df['cert_no_sj'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
            df['cert_no_in'] = df['cert_no_in'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()

            df = df.drop_duplicates(subset=['training_date', 'nik', 'cert_no_sj', 'cert_no_in'], keep='first')
            return df.sort_values(by='id', ascending=False).reset_index(drop=True)
    except Exception as e:
        st.error(f"⚠️ Gagal membaca data training_records (pastikan email `{client_email}` sudah menjadi Editor di Google Sheets): {e}")

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
    """Menyimpan record ujian peserta baru dengan 13 kolom terkunci (A-M)"""
    service, sheet_id, _ = get_sheets_config()
    if not service:
        st.error("⚠️ Koneksi Google Sheets gagal saat menyimpan data.")
        return False

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
        "score": str(record_data.get('score', 0)),
        "status": str(record_data.get('status', '')),
        "cert_no_sj": str(record_data.get('cert_no_sj', '-')),
        "cert_no_in": str(record_data.get('cert_no_in', '-')),
        "expiry_date": str(record_data.get('expiry_date', '-')),
        "id": str(next_id)
    }

    row_values = [clean_row[col] for col in SHEET_COLUMNS]

    try:
        service.spreadsheets().values().append(
            spreadsheetId=sheet_id,
            range=f"{TAB_RECORDS}!A1:M1",
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body={"values": [row_values]}
        ).execute()
    except Exception as e:
        st.error(f"❌ Gagal menyimpan ke Google Sheets: {e}")
        return False

    # Perbarui jadwal recurrent distrik jika status LULUS
    if clean_row['status'] == 'LULUS':
        t_date = clean_row['training_date']
        try:
            dt_obj = datetime.strptime(str(t_date)[:10], "%Y-%m-%d").date()
            next_due = dt_obj.replace(year=dt_obj.year + 2).strftime("%Y-%m-%d")

            df_dist = get_districts()
            if not df_dist.empty:
                if target_dist_name:
                    matched_dist = df_dist[(df_dist['code'] == target_dist_code) & (df_dist['name'] == target_dist_name)]
                else:
                    matched_dist = df_dist[df_dist['code'] == target_dist_code]

                for _, d_row in matched_dist.iterrows():
                    update_district_row(
                        d_row['id'],
                        d_row['code'],
                        d_row['name'],
                        d_row['category'],
                        str(t_date),
                        next_due
                    )
        except Exception:
            pass

    st.cache_data.clear()
    return True


def delete_training_record(record_id):
    """Menghapus data hasil training berdasarkan ID peserta"""
    service, sheet_id, _ = get_sheets_config()
    if not service:
        return

    try:
        res = service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range=f"{TAB_RECORDS}!A1:M"
        ).execute()
        values = res.get("values", [])
        row_idx = -1
        for i, row in enumerate(values):
            if i == 0:
                continue
            if len(row) >= 13 and str(row[12]).strip() == str(record_id).strip():
                row_idx = i
                break

        if row_idx != -1:
            meta = service.spreadsheets().get(spreadsheetId=sheet_id).execute()
            gid = next(
                (s["properties"]["sheetId"] for s in meta.get("sheets", []) if s["properties"]["title"] == TAB_RECORDS),
                None
            )
            if gid is not None:
                service.spreadsheets().batchUpdate(
                    spreadsheetId=sheet_id,
                    body={"requests": [{
                        "deleteDimension": {
                            "range": {
                                "sheetId": gid,
                                "dimension": "ROWS",
                                "startIndex": row_idx,
                                "endIndex": row_idx + 1
                            }
                        }
                    }]}
                ).execute()
                st.cache_data.clear()
    except Exception as e:
        st.error(f"Gagal menghapus data: {e}")


def reset_cert_sequence():
    """Membersihkan cache data agar data terbaru langsung terbaca"""
    st.cache_data.clear()
    st.cache_resource.clear()


def clear_all_training_records():
    """Mengosongkan seluruh baris data riwayat ujian (header baris 1 tetap aman)"""
    service, sheet_id, _ = get_sheets_config()
    if not service:
        return

    try:
        meta = service.spreadsheets().get(spreadsheetId=sheet_id).execute()
        gid = next(
            (s["properties"]["sheetId"] for s in meta.get("sheets", []) if s["properties"]["title"] == TAB_RECORDS),
            None
        )
        if gid is not None:
            service.spreadsheets().batchUpdate(
                spreadsheetId=sheet_id,
                body={"requests": [{
                    "deleteDimension": {
                        "range": {
                            "sheetId": gid,
                            "dimension": "ROWS",
                            "startIndex": 1
                        }
                    }
                }]}
            ).execute()
            st.cache_data.clear()
    except Exception as e:
        st.error(f"Gagal mengosongkan tabel: {e}")
