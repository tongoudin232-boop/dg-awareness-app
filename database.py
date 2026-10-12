import sqlite3
from datetime import datetime
from dateutil.relativedelta import relativedelta
import pandas as pd

DB_FILE = "dg_training.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    # Tabel Distrik
    c.execute('''
        CREATE TABLE IF NOT EXISTS districts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE,
            name TEXT,
            category TEXT,
            last_training_date TEXT,
            next_due_date TEXT
        )
    ''')

    # Tabel Rekam Training
    c.execute('''
        CREATE TABLE IF NOT EXISTS training_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            training_date TEXT,
            full_name TEXT,
            nik TEXT,
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

    # Tabel Counter Siklus 24 Bulan untuk Penomoran
    c.execute('''
        CREATE TABLE IF NOT EXISTS cert_sequence (
            airline TEXT PRIMARY KEY,
            cycle_start_date TEXT,
            last_seq INTEGER
        )
    ''')
    conn.commit()

    # Inisialisasi awal distrik jika kosong
    c.execute("SELECT COUNT(*) FROM districts")
    if c.fetchone()[0] == 0:
        default_districts = [
            ("DJJ", "Jayapura", "Sriwijaya Air"),
            ("TIM", "Timika", "Sriwijaya Air"),
            ("BIK", "Biak", "Sriwijaya Air"),
            ("SOQ", "Sorong", "Sriwijaya Air"),
            ("NBX", "Nabire", "Sriwijaya Air"),
            ("WMX", "Wamena", "Sriwijaya Air"),
            ("TTE", "Ternate", "Sriwijaya Air"),
            ("MDC", "Manado", "Sriwijaya Air"),
            ("SUB", "Surabaya", "Sriwijaya Air"),
            ("UPG", "Makassar", "Sriwijaya Air"),
            ("DPS", "Denpasar", "Sriwijaya Air"),
            ("PNK", "Pontianak", "Sriwijaya Air"),
            ("BEJ", "Berau", "Sriwijaya Air"),
            ("BPN", "Balikpapan", "Sriwijaya Air"),
            ("CGK", "Cengkareng", "Sriwijaya Air"),
            ("PGK", "Pangkal Pinang", "Sriwijaya Air"),
            ("TJQ", "Tanjung Pandan", "Sriwijaya Air"),
            ("BTH", "Batam", "NAM Air"),
            ("BUU", "Muara Teweh", "NAM Air"),
            ("PKN", "Pangkalan Bun", "NAM Air"),
            ("SMQ", "Sampit", "NAM Air"),
            ("SRG", "Semarang", "NAM Air"),
            ("TMC", "Tambolaka", "NAM Air"),
            ("KOE", "Kupang", "NAM Air"),
            ("MOF", "Maumere", "NAM Air"),
            ("CGK-AAP", "CGK (AAP Bening)", "Regulated Agent"),
            ("CGK-APK", "CGK (APK)", "Regulated Agent"),
            ("CGK-GAT", "CGK (GATRANS)", "Regulated Agent"),
            ("CGK-DAP", "CGK (DAPK)", "Regulated Agent"),
            ("CGK-DBM", "CGK (DBM)", "Regulated Agent"),
            ("CGK-SJI", "CGK (SJI)", "Regulated Agent"),
            ("UPG-APLOG", "UPG (APLOG)", "Warehouse/Mitra"),
            ("SUB-APLOG", "SUB (APLOG)", "Warehouse/Mitra")
        ]
        c.executemany("INSERT INTO districts (code, name, category) VALUES (?, ?, ?)", default_districts)
        conn.commit()
    conn.close()

def get_next_cert_number(airline: str, current_date=None) -> str:
    """
    Format nomor: YYMMxxxx (misal: 26100001)
    - YY: 2 digit tahun
    - MM: 2 digit bulan
    - xxxx: 4 digit counter urut kelulusan, reset setiap 24 bulan sekali.
    """
    if current_date is None:
        current_date = datetime.now()

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    c.execute("SELECT cycle_start_date, last_seq FROM cert_sequence WHERE airline = ?", (airline,))
    row = c.fetchone()

    today_str = current_date.strftime("%Y-%m-%d")

    if row is None:
        next_seq = 1
        c.execute("INSERT INTO cert_sequence (airline, cycle_start_date, last_seq) VALUES (?, ?, ?)",
                  (airline, today_str, next_seq))
    else:
        cycle_start_str, last_seq = row
        cycle_start = datetime.strptime(cycle_start_str, "%Y-%m-%d")

        # Cek apakah sudah lewat 24 bulan sejak awal siklus
        if current_date >= (cycle_start + relativedelta(months=24)):
            next_seq = 1
            c.execute("UPDATE cert_sequence SET cycle_start_date = ?, last_seq = ? WHERE airline = ?",
                      (today_str, next_seq, airline))
        else:
            next_seq = last_seq + 1
            c.execute("UPDATE cert_sequence SET last_seq = ? WHERE airline = ?",
                      (next_seq, airline))

    conn.commit()
    conn.close()

    prefix_yymm = current_date.strftime("%y%m") # contoh: 2610
    seq_4digit = f"{next_seq:04d}"              # contoh: 0001
    return f"{prefix_yymm}{seq_4digit}"

def get_districts():
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM districts ORDER BY category, code", conn)
    conn.close()
    return df

def add_district(code, name, category):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO districts (code, name, category) VALUES (?, ?, ?)", (code, name, category))
    conn.commit()
    conn.close()

def save_training_record(data):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        INSERT INTO training_records (
            training_date, full_name, nik, job_role, company,
            district, score, status, cert_no_sj, cert_no_in, expiry_date
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        data['training_date'], data['full_name'], data['nik'], data['job_role'],
        data['company'], data['district'], data['score'], data['status'],
        data.get('cert_no_sj', '-'), data.get('cert_no_in', '-'), data.get('expiry_date', '-')
    ))

    if data['status'] == 'LULUS':
        dt = datetime.strptime(data['training_date'], "%Y-%m-%d")
        due = dt + relativedelta(months=24)
        c.execute('''
            UPDATE districts 
            SET last_training_date = ?, next_due_date = ? 
            WHERE code = ? OR name = ?
        ''', (data['training_date'], due.strftime("%Y-%m-%d"), data['district'], data['district']))
        
    conn.commit()
    conn.close()

def get_training_records():
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM training_records ORDER BY id DESC", conn)
    conn.close()
    return df

# Tambahkan fungsi ini di database.py

def delete_record_by_id(record_id):
    """Menghapus data hasil ujian / sertifikat peserta"""
    conn = sqlite3.connect('dg_training.db')
    c = conn.cursor()
    c.execute("DELETE FROM records WHERE id = ?", (record_id,))
    conn.commit()
    conn.close()

def delete_district_by_id(district_id):
    """Menghapus data distrik"""
    conn = sqlite3.connect('dg_training.db')
    c = conn.cursor()
    c.execute("DELETE FROM districts WHERE id = ?", (district_id,))
    conn.commit()
    conn.close()

def update_district_last_training(district_id, new_last_training_date):
    """Update tanggal last training dan hitung ulang jatuh tempo recurrent (2 tahun)"""
    from datetime import datetime
    conn = sqlite3.connect('dg_training.db')
    c = conn.cursor()
    
    # Hitung expired / next recurrent (misal 2 tahun / 730 hari ke depan)
    try:
        dt = datetime.strptime(str(new_last_training_date), "%Y-%m-%d")
        next_recurrent = dt.replace(year=dt.year + 2).strftime("%Y-%m-%d")
    except Exception:
        next_recurrent = new_last_training_date

    c.execute("""
        UPDATE districts 
        SET last_training = ?, next_recurrent = ?
        WHERE id = ?
    """, (str(new_last_training_date), str(next_recurrent), district_id))
    
    conn.commit()
    conn.close()