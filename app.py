import streamlit as st
import pandas as pd
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
import io
import sqlite3
import os

from database import (
    init_db,
    save_training_record,
    get_districts,
    add_district,
    get_training_records,
    get_next_cert_number
)
from exam_data import QUESTIONS
from cert_generator import generate_certificate

# ==================== KONFIGURASI HALAMAN ====================
st.set_page_config(
    page_title="DG Awareness Training - SJ & IN",
    layout="wide",
    page_icon="✈️"
)

# Inisialisasi Database
init_db()

# Daftar Jabatan
JOB_ROLES = [
    "Staf Kargo / Cargo Officer",
    "Porter / Cargo Loader",
    "Loadmaster / Load Control",
    "Supervisor / Duty Manager",
    "Frontliner",
    "Pasasi / Passenger Service",
    "Security Avsec",
    "Lainnya"
]

# ==================== SISTEM AKSES INSTRUKTUR (SIDEBAR) ====================
if "is_instructor" not in st.session_state:
    st.session_state["is_instructor"] = False

# Tampilkan logo di sidebar jika file tersedia
if os.path.exists("logo_sriwijaya.png"):
    st.sidebar.image("logo_sriwijaya.png", use_container_width=True)

st.sidebar.title("Navigasi")

if st.session_state["is_instructor"]:
    menu_options = [
        "Ujian DG Awareness",
        "Dashboard Instruktur & Records",
        "Master Distrik & Jadwal Recurrent"
    ]
    menu = st.sidebar.radio("Navigasi Menu", menu_options)
    
    st.sidebar.markdown("---")
    if st.sidebar.button("🔒 Logout Instruktur"):
        st.session_state["is_instructor"] = False
        st.rerun()
else:
    menu = "Ujian DG Awareness"
    with st.sidebar.expander("🔐 Akses Khusus Instruktur", expanded=False):
        instructor_pin = st.text_input("Masukkan PIN Instruktur:", type="password")
        if st.button("Masuk"):
            # Ganti 'admin123' dengan PIN pilihan Anda jika diperlukan
            if instructor_pin == "Indomiesoto1":
                st.session_state["is_instructor"] = True
                st.success("Login berhasil!")
                st.rerun()
            else:
                st.error("PIN salah!")


# ==================== MENU 1: UJIAN DG AWARENESS ====================
if menu == "Ujian DG Awareness":
    # Header Banner & Logo
    col_logo1, col_title, col_logo2 = st.columns([1.5, 5, 1.5])
    with col_logo1:
        if os.path.exists("logo_sriwijaya.png"):
            st.image("logo_sriwijaya.png", use_container_width=True)
    with col_title:
        st.markdown(
            """
            <div style="text-align: center; padding: 10px 0;">
                <h1 style="color: #0E3B68; margin-bottom: 0px; font-size: 2.2rem; font-weight: 800;">
                    ✈️ Examination DG Awareness
                </h1>
                <h4 style="color: #6C757D; margin-top: 5px; font-weight: 400; letter-spacing: 1px;">
                    Sriwijaya Air & NAM Air Cargo Training System
                </h4>
            </div>
            """,
            unsafe_allow_html=True
        )
    with col_logo2:
        if os.path.exists("logo_namair.png"):
            st.image("logo_namair.png", use_container_width=True)

    st.markdown("<hr style='margin-top: -5px; margin-bottom: 25px; border: 1px solid #E0E0E0;'>", unsafe_allow_html=True)

    with st.expander("📋 Syarat & Ketentuan Kelulusan", expanded=True):
        st.write("""
        - **Durasi Training:** 8 Jam (1 Hari)
        - **Jumlah Soal:** 25 Pilihan Ganda (Bobot 4 Poin/Soal)
        - **Passing Grade Kelulusan:** ≥ 80 Poin (Minimal 20 Jawaban Benar)
        - Peserta yang lulus langsung memperoleh **2 Sertifikat Resmi** (Sriwijaya Air & NAM Air).
        """)

    st.subheader("1. Data Diri Peserta")
    col1, col2 = st.columns(2)
    with col1:
        full_name = st.text_input("Nama Lengkap*")
        nik = st.text_input("NIK / Employee ID*")
        job_role_selected = st.selectbox("Jabatan / Unit Kerja*", JOB_ROLES)
        
        # Kolom dinamis jika peserta memilih "Lainnya"
        if job_role_selected == "Lainnya":
            custom_role = st.text_input("Sebutkan Jabatan / Unit Kerja Anda*")
            job_role = custom_role.strip()
        else:
            job_role = job_role_selected

    with col2:
        company = st.text_input("Perusahaan / Mitra Kerja* (misal: PT Sriwijaya Air / PT Gapura)")
        dist_df = get_districts()
        dist_options = dist_df['code'] + " - " + dist_df['name'] if not dist_df.empty else []
        selected_dist = st.selectbox("Distrik Penugasan*", dist_options)
        training_date = st.date_input("Tanggal Pelaksanaan Training", date.today())

    st.subheader("2. Lembar Soal Ujian (25 Soal)")
    user_answers = {}
    for i, q in enumerate(QUESTIONS):
        st.markdown(f"**Soal {i+1}:** {q['question']}")
        user_answers[i] = st.radio(
            f"Pilih jawaban untuk nomor {i+1}:",
            options=q['options'],
            key=f"q_{i}",
            index=None
        )
        st.write("")

    if st.button("Submit Jawaban & Evaluasi Nilai", type="primary"):
        if not full_name or not nik or not company or not selected_dist or not job_role:
            st.error("Mohon lengkapi seluruh kolom Data Diri Peserta sebelum submit!")
        elif any(ans is None for ans in user_answers.values()):
            st.warning("Pastikan seluruh 25 soal telah dijawab!")
        else:
            correct_count = 0
            for i, q in enumerate(QUESTIONS):
                if user_answers[i] == q['answer']:
                    correct_count += 1

            score = correct_count * 4
            dist_code = selected_dist.split(" - ")[0]
            passed = score >= 80

            st.markdown("---")
            if passed:
                st.balloons()
                st.success(f"🎉 SELAMAT! Anda dinyatakan **LULUS** dengan Nilai: **{score} / 100** (Benar: {correct_count}/25).")

                # Generate Nomor Sertifikat Otomatis
                cert_no_sj = get_next_cert_number("SJ")
                cert_no_in = get_next_cert_number("IN")

                # Simpan ke Database
                save_training_record(
                    full_name=full_name,
                    nik=nik,
                    job_role=job_role,
                    company=company,
                    district=dist_code,
                    training_date=str(training_date),
                    score=score,
                    status="LULUS",
                    cert_no_sj=cert_no_sj,
                    cert_no_in=cert_no_in
                )

                st.subheader("Unduh Sertifikat Kelulusan")
                col_d1, col_d2 = st.columns(2)

                try:
                    pdf_sj = generate_certificate(
                        airline="SJ",
                        name=full_name,
                        cert_no=cert_no_sj,
                        company=company,
                        district=dist_code,
                        training_date_str=str(training_date)
                    )
                    with col_d1:
                        st.download_button(
                            label="📥 Unduh Sertifikat Sriwijaya Air (SJ)",
                            data=pdf_sj,
                            file_name=f"Sertifikat_SJ_{full_name.replace(' ', '_')}.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )
                except Exception as e:
                    st.error(f"Gagal generate sertifikat SJ: {e}")

                try:
                    pdf_in = generate_certificate(
                        airline="IN",
                        name=full_name,
                        cert_no=cert_no_in,
                        company=company,
                        district=dist_code,
                        training_date_str=str(training_date)
                    )
                    with col_d2:
                        st.download_button(
                            label="📥 Unduh Sertifikat NAM Air (IN)",
                            data=pdf_in,
                            file_name=f"Sertifikat_IN_{full_name.replace(' ', '_')}.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )
                except Exception as e:
                    st.error(f"Gagal generate sertifikat IN: {e}")

            else:
                st.error(f"MOHON MAAF, Anda dinyatakan **BELUM LULUS** dengan Nilai: **{score} / 100** (Benar: {correct_count}/25). Passing grade: 80.")
                save_training_record(
                    full_name=full_name,
                    nik=nik,
                    job_role=job_role,
                    company=company,
                    district=dist_code,
                    training_date=str(training_date),
                    score=score,
                    status="TIDAK LULUS",
                    cert_no_sj="-",
                    cert_no_in="-"
                )


# ==================== MENU 2: DASHBOARD INSTRUKTUR & RECORDS ====================
elif menu == "Dashboard Instruktur & Records":
    st.title("📊 Training Records & Audit Report")
    records_df = get_training_records()

    if records_df.empty:
        st.info("Belum ada data riwayat training.")
    else:
        col1, col2 = st.columns(2)
        with col1:
            filter_dist = st.multiselect("Filter Distrik", options=records_df['district'].unique())
        with col2:
            filter_role = st.multiselect("Filter Jabatan", options=records_df['job_role'].unique())

        filtered_df = records_df.copy()
        if filter_dist:
            filtered_df = filtered_df[filtered_df['district'].isin(filter_dist)]
        if filter_role:
            filtered_df = filtered_df[filtered_df['job_role'].isin(filter_role)]

        filtered_df["Hapus"] = False

        st.caption("Centang kotak pada kolom **Hapus**, lalu klik tombol merah di bawah untuk menghapus record percobaan.")

        col_cfg = {
            "Hapus": st.column_config.CheckboxColumn("Hapus", default=False)
        }
        if "id" in filtered_df.columns:
            col_cfg["id"] = st.column_config.NumberColumn("ID", disabled=True)

        edited_records = st.data_editor(
            filtered_df,
            column_config=col_cfg,
            disabled=[col for col in filtered_df.columns if col != "Hapus"],
            hide_index=True,
            use_container_width=True
        )

        to_del_records = edited_records[edited_records["Hapus"] == True]
        if not to_del_records.empty:
            if st.button(f"🗑️ Hapus {len(to_del_records)} Data Record Terpilih", type="primary"):
                conn = sqlite3.connect('dg_training.db')
                c = conn.cursor()
                if 'id' in to_del_records.columns:
                    for rec_id in to_del_records['id']:
                        c.execute("DELETE FROM training_records WHERE id = ?", (rec_id,))
                elif 'cert_no_sj' in to_del_records.columns:
                    for c_no in to_del_records['cert_no_sj']:
                        c.execute("DELETE FROM training_records WHERE cert_no_sj = ?", (c_no,))
                conn.commit()
                conn.close()
                st.toast(f"{len(to_del_records)} data berhasil dihapus!", icon="✅")
                st.rerun()

        # Ekspor Excel & CSV
        output = io.BytesIO()
        export_df = filtered_df.drop(columns=['Hapus'], errors='ignore')
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            export_df.to_excel(writer, index=False, sheet_name='Training_Records')
        excel_data = output.getvalue()

        col_exp1, col_exp2 = st.columns(2)
        with col_exp1:
            st.download_button(
                label="📥 Ekspor Data ke Excel (.xlsx)",
                data=excel_data,
                file_name=f"DG_Training_Records_{date.today().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        with col_exp2:
            st.download_button(
                label="📥 Ekspor Data ke CSV (.csv)",
                data=export_df.to_csv(index=False).encode('utf-8'),
                file_name=f"DG_Training_Records_{date.today().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True
            )

        # ------------------- FITUR UNDUH ULANG SERTIFIKAT -------------------
        st.markdown("---")
        st.subheader("🎓 Cetak / Unduh Ulang Sertifikat Peserta")
        
        # Saring hanya peserta yang LULUS dan memiliki nomor sertifikat
        passed_records = records_df[
            (records_df['status'] == 'LULUS') & 
            (records_df['cert_no_sj'] != '-') & 
            (records_df['cert_no_sj'].notna())
        ].copy()

        if passed_records.empty:
            st.info("Belum ada data peserta yang dinyatakan lulus untuk diunduh sertifikatnya.")
        else:
            options_dict = {}
            for idx, r in passed_records.iterrows():
                label = f"{r['nik']} - {r['full_name']} ({r['district']}) | Tgl: {r['training_date']}"
                options_dict[label] = r

            selected_candidate_label = st.selectbox(
                "Pilih Peserta untuk Dicetak Ulang Sertifikatnya:",
                options=list(options_dict.keys())
            )

            selected_candidate = options_dict[selected_candidate_label]

            st.write(
                f"**Peserta:** {selected_candidate['full_name']} | **Perusahaan:** {selected_candidate['company']} | "
                f"**No Sertifikat SJ:** `{selected_candidate['cert_no_sj']}` | **No Sertifikat IN:** `{selected_candidate['cert_no_in']}`"
            )

            re_col1, re_col2 = st.columns(2)

            with re_col1:
                try:
                    re_pdf_sj = generate_certificate(
                        airline="SJ",
                        name=str(selected_candidate['full_name']),
                        cert_no=str(selected_candidate['cert_no_sj']),
                        company=str(selected_candidate['company']),
                        district=str(selected_candidate['district']),
                        training_date_str=str(selected_candidate['training_date'])
                    )
                    st.download_button(
                        label=f"📄 Unduh Ulang Sertifikat SJ ({selected_candidate['full_name']})",
                        data=re_pdf_sj,
                        file_name=f"Sertifikat_SJ_{str(selected_candidate['full_name']).replace(' ', '_')}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                except Exception as e:
                    st.error(f"Gagal mencetak ulang sertifikat SJ: {e}")

            with re_col2:
                try:
                    re_pdf_in = generate_certificate(
                        airline="IN",
                        name=str(selected_candidate['full_name']),
                        cert_no=str(selected_candidate['cert_no_in']),
                        company=str(selected_candidate['company']),
                        district=str(selected_candidate['district']),
                        training_date_str=str(selected_candidate['training_date'])
                    )
                    st.download_button(
                        label=f"📄 Unduh Ulang Sertifikat IN ({selected_candidate['full_name']})",
                        data=re_pdf_in,
                        file_name=f"Sertifikat_IN_{str(selected_candidate['full_name']).replace(' ', '_')}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                except Exception as e:
                    st.error(f"Gagal mencetak ulang sertifikat IN: {e}")


# ==================== MENU 3: MASTER DISTRIK & RECURRENT ====================
elif menu == "Master Distrik & Jadwal Recurrent":
    st.title("📍 Master Distrik & Monitoring Recurrent (24 Bulan)")

    dist_df = get_districts()

    today = date.today()
    statuses = []
    for _, row in dist_df.iterrows():
        due_str = row['next_due_date']
        if pd.isna(due_str) or not due_str:
            statuses.append("Belum Ada Riwayat Training")
        else:
            try:
                due_dt = datetime.strptime(str(due_str)[:10], "%Y-%m-%d").date()
                diff_days = (due_dt - today).days
                if diff_days < 0:
                    statuses.append("⚠️ Kedaluwarsa (Wajib Recurrent)")
                elif diff_days <= 30:
                    statuses.append(f"🔔 Segera Recurrent ({diff_days} Hari Tersisa)")
                else:
                    statuses.append("✅ Aktif")
            except Exception:
                statuses.append("Format Tanggal Salah")

    dist_df['Status Recurrent'] = statuses
    dist_df['Hapus'] = False

    dist_df['last_training_date'] = pd.to_datetime(dist_df['last_training_date'], errors='coerce').dt.date
    dist_df['next_due_date'] = pd.to_datetime(dist_df['next_due_date'], errors='coerce').dt.date

    st.caption("💡 **Petunjuk:** Klik dua kali pada kolom **Last Training Date** atau **Next Due Date** untuk mengedit tanggal, lalu klik **Simpan Perubahan Jadwal**. Centang **Hapus** untuk menghapus distrik.")

    edited_dist = st.data_editor(
        dist_df[['code', 'name', 'category', 'last_training_date', 'next_due_date', 'Status Recurrent', 'Hapus']],
        column_config={
            "code": st.column_config.TextColumn("Code", disabled=True),
            "name": st.column_config.TextColumn("Name", disabled=True),
            "category": st.column_config.TextColumn("Category", disabled=True),
            "last_training_date": st.column_config.DateColumn("Last Training Date", format="YYYY-MM-DD"),
            "next_due_date": st.column_config.DateColumn("Next Due Date (Reminder)", format="YYYY-MM-DD"),
            "Status Recurrent": st.column_config.TextColumn("Status Recurrent", disabled=True),
            "Hapus": st.column_config.CheckboxColumn("Hapus", default=False)
        },
        disabled=['code', 'name', 'category', 'Status Recurrent'],
        hide_index=True,
        use_container_width=True
    )

    btn_c1, btn_c2 = st.columns(2)

    with btn_c1:
        if st.button("💾 Simpan Perubahan Jadwal (Last Training & Next Due)"):
            conn = sqlite3.connect('dg_training.db')
            c = conn.cursor()
            for idx, r in edited_dist.iterrows():
                old_last = str(dist_df.loc[idx, 'last_training_date']) if pd.notnull(dist_df.loc[idx, 'last_training_date']) else ""
                new_last = str(r['last_training_date']) if pd.notnull(r['last_training_date']) else None
                
                old_due = str(dist_df.loc[idx, 'next_due_date']) if pd.notnull(dist_df.loc[idx, 'next_due_date']) else ""
                new_due = str(r['next_due_date']) if pd.notnull(r['next_due_date']) else None

                if (str(new_last) != old_last) or (str(new_due) != old_due):
                    if new_last and not new_due:
                        try:
                            dt = datetime.strptime(str(new_last)[:10], "%Y-%m-%d").date()
                            new_due = dt.replace(year=dt.year + 2).strftime("%Y-%m-%d")
                        except Exception:
                            new_due = None

                    c.execute("""
                        UPDATE districts 
                        SET last_training_date = ?, next_due_date = ? 
                        WHERE code = ?
                    """, (str(new_last)[:10] if new_last else None, str(new_due)[:10] if new_due else None, r['code']))
            conn.commit()
            conn.close()
            st.success("Jadwal distrik berhasil diperbarui!")
            st.rerun()

    with btn_c2:
        to_del_dist = edited_dist[edited_dist['Hapus'] == True]
        if not to_del_dist.empty:
            if st.button(f"🗑️ Hapus {len(to_del_dist)} Distrik Terpilih", type="primary"):
                conn = sqlite3.connect('dg_training.db')
                c = conn.cursor()
                for c_code in to_del_dist['code']:
                    c.execute("DELETE FROM districts WHERE code = ?", (c_code,))
                conn.commit()
                conn.close()
                st.toast(f"{len(to_del_dist)} distrik berhasil dihapus!", icon="✅")
                st.rerun()

    st.markdown("---")
    st.subheader("Tambah Rute / Distrik Baru")
    with st.form("add_dist_form"):
        c1, c2, c3 = st.columns(3)
        with c1:
            new_code = st.text_input("Kode Distrik / IATA (misal: BDJ)")
        with c2:
            new_name = st.text_input("Nama Kota / Bandara (misal: Banjarmasin)")
        with c3:
            new_cat = st.selectbox("Kategori", ["Sriwijaya Air", "NAM Air", "Regulated Agent", "Mitra Cargo"])
        
        btn_add = st.form_submit_button("Simpan Distrik Baru")
        if btn_add:
            if new_code and new_name:
                add_district(new_code.upper().strip(), new_name.strip(), new_cat)
                st.success(f"Distrik {new_code.upper()} berhasil ditambahkan!")
                st.rerun()
            else:
                st.error("Mohon isi kode dan nama distrik.")