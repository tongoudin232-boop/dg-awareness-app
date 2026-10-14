import sqlite3
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta

DB_FILE = 'dg_training.db'

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # 1. Tabel Master Distrik (tanpa batasan UNIQUE pada code)
    c.execute('''
        CREATE TABLE IF NOT EXISTS districts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT,
            name TEXT,
            category TEXT,
            last_training_date TEXT,
            next_due_date TEXT
        )
    ''')

    # 2. Cek apakah tabel districts sudah pernah memiliki data
    c.execute("SELECT COUNT(*) FROM districts")
    count = c.fetchone()[0]

    # Hanya isi data awal jika database benar-benar baru dibuat (masih kosong)
    if count == 0:
        default_districts = [
            ('CGK', 'Cengkareng', 'Sriwijaya Air'),
            ('SUB', 'Surabaya', 'Sriwijaya Air'),
            ('DPS', 'Denpasar', 'Sriwijaya Air'),
            ('UPG', 'Makassar', 'Sriwijaya Air'),
            ('KNO', 'Medan', 'Sriwijaya Air'),
            ('PNK', 'Pontianak', 'Sriwijaya Air'),
            ('BTH', 'Batam', 'NAM Air'),
            ('SRG', 'Semarang', 'NAM Air')
        ]
        c.executemany('''
            INSERT INTO districts (code, name, category)
            VALUES (?, ?, ?)
        ''', default_districts)

    # 3. Tabel Riwayat Training Peserta
    c.execute('''
        CREATE TABLE IF NOT EXISTS training_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            training_date TEXT,
            full_name TEXT,
            nik TEXT,
            phone TEXT,
            job_role TEXT,
            company TEXT,
            district TEXT,
            score INTEGER,
            status TEXT,
            cert_no_sj TEXT,
            cert_no_in TEXT,
            expiry_date TEXT
        )
    ''')

    # 4. Tabel Penomoran Sertifikat 24 Bulan
    c.execute('''
        CREATE TABLE IF NOT EXISTS cert_sequence (
            airline TEXT PRIMARY KEY,
            current_seq INTEGER,
            batch_start_date TEXT
        )
    ''')

    conn.commit()
    conn.close()

def get_districts():
    """Mengambil seluruh data distrik terdaftar urut alfabet A-Z berdasarkan kode"""
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM districts ORDER BY code ASC", conn)
    conn.close()
    return df

def add_district(code, name, category):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        INSERT INTO districts (code, name, category)
        VALUES (?, ?, ?)
    ''', (code, name, category))
    conn.commit()
    conn.close()

def save_training_record(record_data):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        INSERT INTO training_records (
            training_date, full_name, nik, phone, job_role, company,
            district, score, status, cert_no_sj, cert_no_in, expiry_date
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        record_data['training_date'],
        record_data['full_name'],
        record_data['nik'],
        record_data['phone'],
        record_data['job_role'],
        record_data['company'],
        record_data['district'],
        record_data['score'],
        record_data['status'],
        record_data['cert_no_sj'],
        record_data['cert_no_in'],
        record_data['expiry_date']
    ))

    # Jika peserta lulus, perbarui tanggal training distrik
    if record_data['status'] == 'LULUS':
        t_date = record_data['training_date']
        dt_obj = datetime.strptime(t_date[:10], "%Y-%m-%d").date()
        next_due = dt_obj.replace(year=dt_obj.year + 2).strftime("%Y-%m-%d")
        
        c.execute('''
            UPDATE districts 
            SET last_training_date = ?, next_due_date = ?
            WHERE code = ?
        ''', (t_date, next_due, record_data['district']))

    conn.commit()
    conn.close()

def get_training_records():
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM training_records ORDER BY id DESC", conn)
    conn.close()
    return df

def get_next_cert_number(airline):
    """
    Format nomor sertifikat: YYMMxxxx (contoh: 26100001)
    Sequence otomatis reset setiap siklus 24 bulan dari batch pertama.
    """
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    prefix_yymm = now.strftime("%y%m")

    c.execute("SELECT current_seq, batch_start_date FROM cert_sequence WHERE airline = ?", (airline,))
    row = c.fetchone()

    if row is None:
        next_seq = 1
        c.execute('''
            INSERT INTO cert_sequence (airline, current_seq, batch_start_date)
            VALUES (?, ?, ?)
        ''', (airline, next_seq, today_str))
    else:
        current_seq, start_date_str = row
        start_date = datetime.strptime(start_date_str[:10], "%Y-%m-%d")
        diff_months = (now.year - start_date.year) * 12 + (now.month - start_date.month)

        if diff_months >= 24:
            next_seq = 1
            c.execute('''
                UPDATE cert_sequence
                SET current_seq = ?, batch_start_date = ?
                WHERE airline = ?
            ''', (next_seq, today_str, airline))
        else:
            next_seq = current_seq + 1
            c.execute('''
                UPDATE cert_sequence
                SET current_seq = ?
                WHERE airline = ?
            ''', (next_seq, airline))

    conn.commit()
    conn.close()

    return f"{prefix_yymm}{next_seq:04d}"

def reset_cert_sequence():
    """Mereset penomoran sertifikat kembali ke urutan awal (0001)"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM cert_sequence")
    conn.commit()
    conn.close()

def clear_all_training_records():
    """Menghapus seluruh rekaman riwayat ujian/training percobaan"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM training_records")
    conn.commit()
    conn.close()