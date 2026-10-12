import streamlit as st
import pandas as pd
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
import io
import sqlite3

from database import (
    init_db,
    get_districts,
    add_district,
    save_training_record,
    get_training_records,
    get_next_cert_number
)
from exam_data import QUESTIONS
from cert_generator import generate_certificate

st.set_page_config(page_title="DG Awareness Training - SJ & IN", layout="wide", page_icon="✈️")
init_db()

menu = st.sidebar.radio("Navigasi Menu", [
    "Ujian DG Awareness",
    "Dashboard Instruktur & Records",
    "Master Distrik & Jadwal Recurrent"
])

JOB_ROLES = [
    "Staf Kargo / Cargo Officer",
    "Porter / Cargo Loader",
    "Loadmaster / Load Control",
    "Supervisor / Duty Manager",
    "Frontliner",
    "Pasasi / Passenger Service",
    "Quality Control (QC)",
    "Aviation Security (Avsec)",
    "Ground Support Equipment (GSE)",
    "Lainnya (Custom)"
]

# ==================== MENU 1: UJIAN DG AWARENESS ====================
if menu == "Ujian DG Awareness":
    st.title("✈️ Examination DG Awareness")
    st.caption("Sriwijaya Air & NAM Air Cargo Training System")

    with st.expander("Syarat & Ketentuan Kelulusan", expanded=True):
        st.write("- Durasi Training: 8 Jam (1 Hari)")
        st.write("- Jumlah Soal: 25 Pilihan Ganda (Bobot 4 Poin/Soal)")
        st.write("- Passing Grade Kelulusan: **≥ 80 Poin** (Minimal 20 Jawaban Benar)")
        st.write("- Peserta yang lulus langsung memperoleh **2 Sertifikat Resmi (Sriwijaya Air & NAM Air)**.")

    st.subheader("1. Data Diri Peserta")
    col1, col2 = st.columns(2)
    with col1:
        full_name = st.text_input("Nama Lengkap*")
        nik = st.text_input("Nomor Induk Karyawan (NIK)*")
        phone = st.text_input("Nomor Handphone (WhatsApp)*")
        selected_role = st.selectbox("Jabatan / Posisi*", JOB_ROLES)
        if selected_role == "Lainnya (Custom)":
            final_job_role = st.text_input("Sebutkan Jabatan Anda*")
        else:
            final_job_role = selected_role

    with col2:
        company = st.text_input("Perusahaan / Mitra Kerja* (misal: PT Sriwijaya Air / PT Gapura)")
        districts_df = get_districts()
        district_list = districts_df['code'].tolist()
        district = st.selectbox("Distrik / Station Penempatan*", district_list)
        photo = st.file_uploader("Unggah Pas Foto Peserta*", type=["jpg", "png", "jpeg"])

    st.markdown("---")
    st.subheader("2. Lembar Soal Ujian")

    with st.form("exam_form"):
        user_answers = {}
        for q in QUESTIONS:
            st.markdown(f"**Soal {q['id']}:** {q['question']}")
            user_answers[q['id']] = st.radio(
                f"Pilih jawaban untuk soal no {q['id']}:",
                q['options'],
                index=None,
                key=f"q_{q['id']}",
                label_visibility="collapsed"
            )
            st.write("")

        submitted = st.form_submit_button("Submit Jawaban & Evaluasi Nilai", use_container_width=True)

    if submitted:
        if not full_name or not nik or not final_job_role or not company:
            st.error("Mohon lengkapi seluruh kolom identitas peserta sebelum submit.")
        else:
            score = 0
            for q in QUESTIONS:
                selected_ans = user_answers.get(q['id'])
                if selected_ans is not None:
                    correct_ans_str = q['options'][q['answer']]
                    if selected_ans == correct_ans_str:
                        score += 4

            training_date_str = date.today().strftime("%Y-%m-%d")
            expiry_date_str = (date.today() + relativedelta(months=24)).strftime("%Y-%m-%d")
            today_formal = date.today().strftime("%d %B %Y")

            st.markdown("---")
            if score >= 80:
                st.success(f"🎉 **SELAMAT! ANDA DINYATAKAN LULUS** dengan Nilai: **{score} / 100**")

                # Generate nomor urut 8 digit (YYMMxxxx) dengan auto-reset per 24 bulan
                cert_sj = get_next_cert_number("SJ")
                cert_in = get_next_cert_number("IN")

                save_training_record({
                    "training_date": training_date_str,
                    "full_name": full_name,
                    "nik": nik,
                    "job_role": final_job_role,
                    "company": company,
                    "district": district,
                    "score": score,
                    "status": "LULUS",
                    "cert_no_sj": cert_sj,
                    "cert_no_in": cert_in,
                    "expiry_date": expiry_date_str
                })

                pdf_sj = generate_certificate("SJ", cert_sj, full_name, today_formal)
                pdf_in = generate_certificate("IN", cert_in, full_name, today_formal)

                c1, c2 = st.columns(2)
                with c1:
                    st.download_button(
                        label="📥 Unduh Sertifikat Sriwijaya Air (PDF)",
                        data=pdf_sj,
                        file_name=f"CERTIFICATE_SJ_{cert_sj}_{full_name.replace(' ', '_')}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                with c2:
                    st.download_button(
                        label="📥 Unduh Sertifikat NAM Air (PDF)",
                        data=pdf_in,
                        file_name=f"CERTIFICATE_IN_{cert_in}_{full_name.replace(' ', '_')}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
            else:
                st.error(f"❌ **MOHON MAAF, NILAI ANDA BELUM MEMENUHI PASSING GRADE (80 Poin)**. Nilai Anda: **{score} / 100**")
                st.warning("Silakan pelajari kembali materi DG Awareness dan ulangi pengerjaan soal ujian.")
                save_training_record({
                    "training_date": training_date_str,
                    "full_name": full_name,
                    "nik": nik,
                    "job_role": final_job_role,
                    "company": company,
                    "district": district,
                    "score": score,
                    "status": "TIDAK LULUS",
                    "cert_no_sj": "-",
                    "cert_no_in": "-",
                    "expiry_date": "-"
                })

# ==================== MENU 2: DASHBOARD & TRAINING RECORDS ====================
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

        # Konfigurasi kolom tabel
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

        # Tombol Hapus Data Record
        to_del_records = edited_records[edited_records["Hapus"] == True]
        if not to_del_records.empty:
            if st.button(f"🗑️ Hapus {len(to_del_records)} Data Record Terpilih", type="primary"):
                conn = sqlite3.connect('dg_training.db')
                c = conn.cursor()
                
                # Cek identifier baris (menggunakan id atau cert_no_sj)
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

    # Konversi kedua kolom tanggal agar dapat diedit secara interaktif
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

    # 1. Simpan perubahan tanggal last_training_date & next_due_date
    with btn_c1:
        if st.button("💾 Simpan Perubahan Jadwal (Last Training & Next Due)"):
            conn = sqlite3.connect('dg_training.db')
            c = conn.cursor()
            for idx, r in edited_dist.iterrows():
                old_last = str(dist_df.loc[idx, 'last_training_date']) if pd.notnull(dist_df.loc[idx, 'last_training_date']) else ""
                new_last = str(r['last_training_date']) if pd.notnull(r['last_training_date']) else None
                
                old_due = str(dist_df.loc[idx, 'next_due_date']) if pd.notnull(dist_df.loc[idx, 'next_due_date']) else ""
                new_due = str(r['next_due_date']) if pd.notnull(r['next_due_date']) else None

                # Jika tanggal ada yang berubah
                if (str(new_last) != old_last) or (str(new_due) != old_due):
                    # Jika next_due_date kosong tetapi last_training diisi, hitung otomatis +2 tahun
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

    # 2. Hapus distrik terpilih
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