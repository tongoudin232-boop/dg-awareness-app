import streamlit as st
import pandas as pd
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
import io
import os

from database import (
    init_db,
    save_training_record,
    get_districts,
    add_district,
    update_district_row,
    delete_district_row,
    get_training_records,
    delete_training_record,
    get_next_cert_number,
    reset_cert_sequence,
    clear_all_training_records
)
from exam_data import QUESTIONS
from cert_generator import generate_certificate
from attendance_generator import generate_attendance_pdf, generate_attendance_excel

# ==================== KONFIGURASI HALAMAN ====================
st.set_page_config(
    page_title="DG Awareness Training - SJ & IN",
    layout="wide",
    page_icon="✈️"
)

# Inisialisasi Database Google Sheets
init_db()

# Inisialisasi Session State Login Instruktur
if "is_instructor" not in st.session_state:
    st.session_state["is_instructor"] = False

# ==================== KONTROL TAMPILAN HEADER & MENU ====================
# Sembunyikan Fork, GitHub, dan Menu Bawaan untuk Peserta Umum
if not st.session_state["is_instructor"]:
    st.markdown(
        """
        <style>
        header[data-testid="stHeader"] {
            background-color: transparent !important;
        }
        [data-testid="stToolbar"] {
            display: none !important;
        }
        [data-testid="stDecoration"] {
            display: none !important;
        }
        footer {
            display: none !important;
        }
        [data-testid="collapsedControl"] {
            display: flex !important;
            z-index: 1000001 !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )
else:
    st.markdown(
        """
        <style>
        [data-testid="stToolbar"] {
            display: flex !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

# Daftar Kategori Lengkap Distrik
CATEGORY_OPTIONS = [
    "Sriwijaya Air",
    "NAM Air",
    "Regulated Agent",
    "Mitra Cargo",
    "Warehouse",
    "Jaster"
]

# ==================== 1. VERIFIKASI SERTIFIKAT VIA QR CODE ====================
query_params = st.query_params

if "cert" in query_params:
    cert_query = str(query_params["cert"]).strip()
    
    records_df = get_training_records()
    matched = pd.DataFrame()
    
    if not records_df.empty:
        def clean_cert_val(val):
            if pd.isna(val) or val is None:
                return ""
            s = str(val).strip()
            if s.endswith(".0"):
                s = s[:-2]
            return s

        df_check = records_df.copy()
        df_check['clean_sj'] = df_check['cert_no_sj'].apply(clean_cert_val)
        df_check['clean_in'] = df_check['cert_no_in'].apply(clean_cert_val)

        matched = df_check[
            (df_check['clean_sj'] == cert_query) | 
            (df_check['clean_in'] == cert_query)
        ]
    
    col_vlogo1, col_vtitle, col_vlogo2 = st.columns([1.5, 5, 1.5])
    with col_vlogo1:
        if os.path.exists("logo_sriwijaya.png"):
            st.image("logo_sriwijaya.png", use_container_width=True)
    with col_vtitle:
        st.markdown(
            """
            <div style="text-align: center; padding: 10px 0;">
                <h1 style="color: #0E3B68; margin-bottom: 0px;">✈️ Portal Verifikasi Sertifikat</h1>
                <h4 style="color: #6C757D; margin-top: 5px;">Sriwijaya Air & NAM Air Dangerous Goods Training</h4>
            </div>
            """,
            unsafe_allow_html=True
        )
    with col_vlogo2:
        if os.path.exists("logo_namair.png"):
            st.image("logo_namair.png", use_container_width=True)

    st.markdown("<hr style='border: 1px solid #E0E0E0;'>", unsafe_allow_html=True)
    
    if not matched.empty:
        rec = matched.iloc[0]
        st.success("✅ **SERTIFIKAT RESMI TERVERIFIKASI & TERCATAT DI DATABASE (VALID)**")
        
        col_v1, col_v2 = st.columns(2)
        with col_v1:
            st.markdown(f"**Nama Peserta:** {rec['full_name']}")
            st.markdown(f"**NIK / Employee ID:** {rec['nik']}")
            st.markdown(f"**Perusahaan:** {rec['company']}")
            st.markdown(f"**Jabatan / Posisi:** {rec['job_role']}")
        with col_v2:
            st.markdown(f"**Distrik Pelaksanaan:** {rec['district']}")
            st.markdown(f"**Tanggal Training:** {rec['training_date']}")
            st.markdown(f"**No. Sertifikat Sriwijaya Air:** `{rec['cert_no_sj']}`")
            st.markdown(f"**No. Sertifikat NAM Air:** `{rec['cert_no_in']}`")
        
        st.markdown("---")
        st.subheader("Salinan Resmi Dokumen")
        
        clean_sj_val = clean_cert_val(rec['cert_no_sj'])
        airline_target = "SJ" if clean_sj_val == cert_query else "IN"
        airline_name = "Sriwijaya Air" if airline_target == "SJ" else "NAM Air"
        try:
            cert_pdf = generate_certificate(
                airline=airline_target,
                cert_no=str(cert_query),
                name=str(rec['full_name']),
                training_date_str=str(rec['training_date'])
            )
            st.download_button(
                label=f"📥 Unduh Salinan Sertifikat {airline_name} ({airline_target})",
                data=cert_pdf,
                file_name=f"Salinan_Sertifikat_{rec['full_name']}_{airline_target}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
        except Exception as e:
            st.error(f"Gagal memuat salinan sertifikat: {e}")
            
    else:
        st.error("❌ **DATA SERTIFIKAT TIDAK DITEMUKAN!**")
        st.warning(f"Nomor sertifikat '{cert_query}' tidak terdaftar pada sistem database pelatihan resmi Sriwijaya Air & NAM Air Cargo.")
        
    st.stop()


# ==================== DAFTAR JABATAN ====================
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
            if instructor_pin == "Indomiesoto1":
                st.session_state["is_instructor"] = True
                st.success("Login berhasil!")
                st.rerun()
            else:
                st.error("PIN salah!")


# ==================== MENU 1: UJIAN DG AWARENESS ====================
if menu == "Ujian DG Awareness":
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

    # Tampilan hasil & penguncian form jika sudah disubmit
    if 'exam_result' in st.session_state:
        res = st.session_state['exam_result']
        if res['passed']:
            st.balloons()
            st.success(f"🎉 SELAMAT! Anda dinyatakan **LULUS** dengan Nilai: **{res['score']} / 100** (Benar: {res['correct_count']}/25).")
            st.subheader("Unduh Sertifikat Kelulusan")
            col_d1, col_d2 = st.columns(2)
            with col_d1:
                st.download_button(
                    label="📥 Unduh Sertifikat Sriwijaya Air (SJ)",
                    data=res['pdf_sj'],
                    file_name=f"Sertifikat_SJ_{res['full_name'].replace(' ', '_')}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                    key="btn_download_sj"
                )
            with col_d2:
                st.download_button(
                    label="📥 Unduh Sertifikat NAM Air (IN)",
                    data=res['pdf_in'],
                    file_name=f"Sertifikat_IN_{res['full_name'].replace(' ', '_')}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                    key="btn_download_in"
                )
            st.info("ℹ️ Data ujian Anda telah resmi tersimpan. Silakan simpan dan unduh dokumen sertifikat di atas.")
        else:
            st.error(f"MOHON MAAF, Anda dinyatakan **BELUM LULUS** dengan Nilai: **{res['score']} / 100** (Benar: {res['correct_count']}/25). Passing grade: 80.")
            if st.button("🔄 Ulangi Ujian", type="primary"):
                del st.session_state['exam_result']
                st.rerun()

    else:
        st.subheader("1. Data Diri Peserta")
        col1, col2 = st.columns(2)
        with col1:
            full_name = st.text_input("Nama Lengkap*")
            nik = st.text_input("NIK / Employee ID*")
            phone = st.text_input("No. Handphone / WhatsApp*")
            job_role_selected = st.selectbox("Jabatan / Unit Kerja*", JOB_ROLES)
            
            if job_role_selected == "Lainnya":
                custom_role = st.text_input("Sebutkan Jabatan / Unit Kerja Anda*")
                job_role = custom_role.strip()
            else:
                job_role = job_role_selected

        with col2:
            company = st.text_input("Perusahaan*")
            dist_df = get_districts()
            dist_options = dist_df['code'] + " - " + dist_df['name'] if not dist_df.empty else []
            selected_dist = st.selectbox("Distrik Penugasan*", dist_options)
            training_date = st.date_input("Tanggal Pelaksanaan Training", date.today(), format="DD/MM/YYYY")

        st.subheader("2. Lembar Soal Ujian (25 Soal)")
        
        with st.form("exam_form"):
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

            submit_btn = st.form_submit_button("Submit Jawaban & Evaluasi Nilai", type="primary")

        if submit_btn:
            if not full_name or not nik or not phone or not company or not selected_dist or not job_role:
                st.error("Mohon lengkapi seluruh kolom Data Diri Peserta (termasuk No. Handphone) sebelum submit!")
            elif any(user_answers[i] is None for i in range(len(QUESTIONS))):
                st.warning("Pastikan seluruh 25 soal telah dijawab!")
            else:
                with st.spinner("Sedang memproses evaluasi nilai dan menyimpan sertifikat..."):
                    correct_count = 0
                    for i, q in enumerate(QUESTIONS):
                        selected_val = user_answers[i]
                        raw_ans = q['answer']
                        if isinstance(raw_ans, int):
                            correct_val = q['options'][raw_ans]
                        else:
                            correct_val = str(raw_ans)
                        
                        if str(selected_val).strip().lower() == str(correct_val).strip().lower():
                            correct_count += 1

                    score = correct_count * 4
                    
                    # Pecah kode dan nama distrik agar spesifik
                    dist_parts = selected_dist.split(" - ")
                    dist_code = dist_parts[0].strip()
                    dist_name = dist_parts[1].strip() if len(dist_parts) > 1 else ""
                    
                    passed = score >= 80

                    # Bersihkan format nomor HP dari trailing space
                    clean_phone_str = str(phone).strip()

                    if passed:
                        cert_no_sj = get_next_cert_number("SJ")
                        cert_no_in = get_next_cert_number("IN")
                        exp_date = (training_date + relativedelta(months=24)).strftime("%Y-%m-%d")

                        record_payload = {
                            'training_date': str(training_date),
                            'full_name': full_name.strip(),
                            'nik': nik.strip(),
                            'phone': clean_phone_str,
                            'job_role': job_role.strip(),
                            'company': company.strip(),
                            'district': dist_code,
                            'district_name': dist_name,
                            'score': score,
                            'status': 'LULUS',
                            'cert_no_sj': cert_no_sj,
                            'cert_no_in': cert_no_in,
                            'expiry_date': exp_date
                        }
                        save_training_record(record_payload)

                        pdf_sj = generate_certificate(
                            airline="SJ",
                            cert_no=cert_no_sj,
                            name=full_name.strip(),
                            training_date_str=str(training_date)
                        )

                        pdf_in = generate_certificate(
                            airline="IN",
                            cert_no=cert_no_in,
                            name=full_name.strip(),
                            training_date_str=str(training_date)
                        )

                        st.session_state['exam_result'] = {
                            'passed': True,
                            'score': score,
                            'correct_count': correct_count,
                            'full_name': full_name.strip(),
                            'pdf_sj': pdf_sj,
                            'pdf_in': pdf_in
                        }
                    else:
                        record_payload = {
                            'training_date': str(training_date),
                            'full_name': full_name.strip(),
                            'nik': nik.strip(),
                            'phone': clean_phone_str,
                            'job_role': job_role.strip(),
                            'company': company.strip(),
                            'district': dist_code,
                            'district_name': dist_name,
                            'score': score,
                            'status': 'TIDAK LULUS',
                            'cert_no_sj': '-',
                            'cert_no_in': '-',
                            'expiry_date': '-'
                        }
                        save_training_record(record_payload)
                        st.session_state['exam_result'] = {
                            'passed': False,
                            'score': score,
                            'correct_count': correct_count
                        }
                st.rerun()


# ==================== MENU 2: DASHBOARD INSTRUKTUR & RECORDS ====================
elif menu == "Dashboard Instruktur & Records":
    st.title("📊 Training Records & Audit Report (Google Sheets Cloud)")

    with st.expander("⚙️ **Pengaturan Khusus & Reset Data Percobaan (Trial)**", expanded=False):
        c_tool1, c_tool2 = st.columns(2)
        with c_tool1:
            st.markdown("**1. Reset Nomor Sertifikat ke Urutan 0001**")
            st.caption("Memulai ulang penomoran sertifikat resmi SJ & IN dari nomor urut 0001 di cloud.")
            if st.button("🔄 Reset Nomor Sertifikat ke 1", type="primary"):
                reset_cert_sequence()
                st.success("✅ Nomor sertifikat berhasil di-reset! Sertifikat berikutnya akan terbit dari nomor urut 0001.")
                st.rerun()

        with c_tool2:
            st.markdown("**2. Kosongkan Seluruh Data Percobaan (Trial)**")
            st.caption("Menghapus seluruh riwayat ujian yang ada di tabel Google Sheets.")
            if st.button("⚠️ Hapus Seluruh Data Training", type="secondary"):
                clear_all_training_records()
                st.toast("Seluruh record training berhasil dibersihkan dari cloud!", icon="🗑️")
                st.rerun()

    st.markdown("---")

    records_df = get_training_records()

    if records_df.empty:
        st.info("Belum ada data riwayat training. (Tabel Google Sheets masih kosong)")
    else:
        with st.expander("🗑️ **Hapus Record Spesifik (Berdasarkan ID / Nama)**", expanded=False):
            rec_options = {
                f"ID {r['id']} | {r['full_name']} ({r['district']}) - Tgl: {r['training_date']}": r['id']
                for _, r in records_df.iterrows()
            }
            selected_to_delete = st.selectbox("Pilih data yang ingin dihapus permanen:", list(rec_options.keys()))
            if st.button("Hapus Data Terpilih Ini", type="primary"):
                del_id = rec_options[selected_to_delete]
                delete_training_record(del_id)
                st.success("✅ Data berhasil dihapus permanen dari Google Sheets!")
                st.rerun()

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

        st.dataframe(filtered_df, use_container_width=True, hide_index=True)

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            filtered_df.to_excel(writer, index=False, sheet_name='Training_Records')
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
                data=filtered_df.to_csv(index=False).encode('utf-8'),
                file_name=f"DG_Training_Records_{date.today().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True
            )

        # Penerbitan Daftar Kehadiran (Absensi)
        st.markdown("---")
        st.subheader("📝 Penerbitan Daftar Kehadiran (Absensi) Training")
        st.caption("Gunakan bagian ini untuk menerbitkan absensi resmi per distrik dan per tanggal kegiatan.")

        col_ab1, col_ab2 = st.columns(2)
        with col_ab1:
            all_districts = sorted(records_df['district'].dropna().unique().tolist())
            selected_absensi_dist = st.selectbox("1. Pilih Distrik Penugasan:", options=all_districts)
        with col_ab2:
            dist_records = records_df[records_df['district'] == selected_absensi_dist]
            avail_dates = sorted(dist_records['training_date'].dropna().unique().tolist(), reverse=True)
            if avail_dates:
                selected_absensi_date = st.selectbox("2. Pilih Tanggal Training:", options=avail_dates)
            else:
                selected_absensi_date = None
                st.info("Tidak ada data kegiatan di distrik ini.")

        if selected_absensi_date:
            candidates_att = dist_records[dist_records['training_date'] == selected_absensi_date].copy()
            total_peserta = len(candidates_att)
            st.info(f"Ditemukan **{total_peserta} orang peserta** untuk Distrik **{selected_absensi_dist}** pada tanggal **{selected_absensi_date}**.")

            c_meta1, c_meta2, c_meta3 = st.columns(3)
            with c_meta1:
                mode_training = st.radio("Metode Pelaksanaan:", ["Online", "Offline"], horizontal=True)
            with c_meta2:
                jam_training = st.text_input("Pukul / Waktu Training:", value="13.00 - 17.00")
            with c_meta3:
                nama_instruktur = st.text_input("Nama Instruktur:", value="HADI NURHUDA")

            c_meta4, c_meta5 = st.columns([2, 2])
            with c_meta4:
                default_tempat = f"Station {selected_absensi_dist} ({mode_training.lower()})"
                tempat_training = st.text_input("Tempat Training:", value=default_tempat)
            with c_meta5:
                foto_uploaded = st.file_uploader("Upload Foto Bukti Pelatihan (JPG / PNG):", type=["jpg", "jpeg", "png"])

            if mode_training == "Offline":
                batch_size = 25
                sessions = [candidates_att.iloc[i:i + batch_size] for i in range(0, total_peserta, batch_size)]
                num_sessions = len(sessions)
                st.write(f"📌 *Mode Offline: Dipecah menjadi **{num_sessions} Sesi** (Maksimal 25 peserta/sesi).*")
            else:
                sessions = [candidates_att]
                num_sessions = 1
                st.write("📌 *Mode Online: Seluruh peserta digabung ke dalam 1 lembar absensi.*")

            try:
                dt_obj = datetime.strptime(str(selected_absensi_date)[:10], "%Y-%m-%d")
                hari_id = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"][dt_obj.weekday()]
                bulan_id = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"][dt_obj.month - 1]
                tgl_display = f"{hari_id}, {dt_obj.day} {bulan_id} {dt_obj.year}"
            except Exception:
                tgl_display = str(selected_absensi_date)

            foto_bytes = foto_uploaded.getvalue() if foto_uploaded is not None else None

            for s_idx, session_df in enumerate(sessions):
                sesi_label = f"Sesi {s_idx + 1}" if num_sessions > 1 else "Dokumen Absensi"
                st.markdown(f"#### 📄 Unduh {sesi_label} ({len(session_df)} Peserta)")

                c_btn1, c_btn2, c_btn3 = st.columns(3)

                with c_btn1:
                    try:
                        pdf_sj_att = generate_attendance_pdf(
                            airline="SJ",
                            date_display=tgl_display,
                            time_str=jam_training,
                            venue_str=tempat_training,
                            instructor_name=nama_instruktur,
                            df_session=session_df,
                            photo_bytes=foto_bytes
                        )
                        st.download_button(
                            label=f"📥 PDF Sriwijaya Air ({sesi_label})",
                            data=pdf_sj_att,
                            file_name=f"Absensi_SJ_{selected_absensi_dist}_{selected_absensi_date}_{sesi_label.replace(' ', '_')}.pdf",
                            mime="application/pdf",
                            use_container_width=True,
                            key=f"att_sj_{s_idx}"
                        )
                    except Exception as e:
                        st.error(f"Gagal generate PDF SJ: {e}")

                with c_btn2:
                    try:
                        pdf_in_att = generate_attendance_pdf(
                            airline="IN",
                            date_display=tgl_display,
                            time_str=jam_training,
                            venue_str=tempat_training,
                            instructor_name=nama_instruktur,
                            df_session=session_df,
                            photo_bytes=foto_bytes
                        )
                        st.download_button(
                            label=f"📥 PDF NAM Air ({sesi_label})",
                            data=pdf_in_att,
                            file_name=f"Absensi_IN_{selected_absensi_dist}_{selected_absensi_date}_{sesi_label.replace(' ', '_')}.pdf",
                            mime="application/pdf",
                            use_container_width=True,
                            key=f"att_in_{s_idx}"
                        )
                    except Exception as e:
                        st.error(f"Gagal generate PDF IN: {e}")

                with c_btn3:
                    try:
                        excel_att = generate_attendance_excel(
                            date_display=tgl_display,
                            time_str=jam_training,
                            venue_str=tempat_training,
                            instructor_name=nama_instruktur,
                            df_session=session_df
                        )
                        st.download_button(
                            label=f"📊 Excel (.xlsx) ({sesi_label})",
                            data=excel_att,
                            file_name=f"Absensi_{selected_absensi_dist}_{selected_absensi_date}_{sesi_label.replace(' ', '_')}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True,
                            key=f"att_xls_{s_idx}"
                        )
                    except Exception as e:
                        st.error(f"Gagal generate Excel: {e}")

        # Unduh Ulang Sertifikat
        st.markdown("---")
        st.subheader("🎓 Cetak / Unduh Ulang Sertifikat Peserta")
        
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
                        cert_no=str(selected_candidate['cert_no_sj']),
                        name=str(selected_candidate['full_name']),
                        training_date_str=str(selected_candidate['training_date'])
                    )
                    st.download_button(
                        label=f"📄 Unduh Ulang Sertifikat SJ ({selected_candidate['full_name']})",
                        data=re_pdf_sj,
                        file_name=f"Sertifikat_SJ_{str(selected_candidate['full_name']).replace(' ', '_')}.pdf",
                        mime="application/pdf",
                        use_container_width=True,
                        key="btn_re_sj"
                    )
                except Exception as e:
                    st.error(f"Gagal mencetak ulang sertifikat SJ: {e}")

            with re_col2:
                try:
                    re_pdf_in = generate_certificate(
                        airline="IN",
                        cert_no=str(selected_candidate['cert_no_in']),
                        name=str(selected_candidate['full_name']),
                        training_date_str=str(selected_candidate['training_date'])
                    )
                    st.download_button(
                        label=f"📄 Unduh Ulang Sertifikat IN ({selected_candidate['full_name']})",
                        data=re_pdf_in,
                        file_name=f"Sertifikat_IN_{str(selected_candidate['full_name']).replace(' ', '_')}.pdf",
                        mime="application/pdf",
                        use_container_width=True,
                        key="btn_re_in"
                    )
                except Exception as e:
                    st.error(f"Gagal mencetak ulang sertifikat IN: {e}")


# ==================== MENU 3: MASTER DISTRIK & RECURRENT ====================
elif menu == "Master Distrik & Jadwal Recurrent":
    st.title("📍 Master Distrik & Monitoring Recurrent (24 Bulan)")

    dist_df = get_districts()

    def calculate_status(due_str):
        if pd.isna(due_str) or not due_str or str(due_str).strip() in ['None', '', 'nan', 'NaT']:
            return "Belum Ada Riwayat Training"
        try:
            due_dt = datetime.strptime(str(due_str)[:10], "%Y-%m-%d").date()
            diff_days = (due_dt - date.today()).days
            if diff_days < 0:
                return "⚠️ Kedaluwarsa (Wajib Recurrent)"
            elif diff_days <= 30:
                return f"🔔 Segera Recurrent ({diff_days} Hari Tersisa)"
            else:
                return "✅ Aktif"
        except Exception:
            return "Format Tanggal Salah"

    # Pusat Edit Manual Data Distrik
    with st.expander("✏️ **Pusat Edit Manual Data Distrik & Jadwal Recurrent**", expanded=True):
        if not dist_df.empty:
            dist_map = {}
            for _, d_row in dist_df.iterrows():
                lbl = f"ID {d_row['id']} | {d_row['code']} - {d_row['name']} ({d_row['category']})"
                dist_map[lbl] = d_row

            sel_dist_lbl = st.selectbox("Pilih Distrik yang Ingin Diubah:", list(dist_map.keys()))
            cur_data = dist_map[sel_dist_lbl]

            raw_last = str(cur_data.get('last_training_date', '')).strip()
            raw_due = str(cur_data.get('next_due_date', '')).strip()

            has_valid_history = False
            default_last = date.today()
            default_due = date.today() + relativedelta(months=24)

            if raw_last and raw_last not in ['None', '', 'nan', 'NaT']:
                try:
                    default_last = datetime.strptime(raw_last[:10], "%Y-%m-%d").date()
                    has_valid_history = True
                except Exception:
                    pass

            if raw_due and raw_due not in ['None', '', 'nan', 'NaT']:
                try:
                    default_due = datetime.strptime(raw_due[:10], "%Y-%m-%d").date()
                except Exception:
                    default_due = default_last + relativedelta(months=24)

            with st.form("form_edit_manual_distrik"):
                e_c1, e_c2, e_c3 = st.columns(3)
                with e_c1:
                    edit_code = st.text_input("Kode Distrik (Code)", value=str(cur_data['code']))
                with e_c2:
                    edit_name = st.text_input("Nama Distrik / Stasiun", value=str(cur_data['name']))
                with e_c3:
                    cat_idx = CATEGORY_OPTIONS.index(cur_data['category']) if cur_data['category'] in CATEGORY_OPTIONS else 0
                    edit_cat = st.selectbox("Kategori", CATEGORY_OPTIONS, index=cat_idx)

                st.markdown("---")
                status_history = st.radio(
                    "Status Riwayat Pelatihan:",
                    options=["Ada Riwayat Training", "Belum Ada Riwayat (Kosongkan Tanggal)"],
                    index=0 if has_valid_history else 1,
                    horizontal=True
                )

                e_c4, e_c5 = st.columns(2)
                with e_c4:
                    edit_last_date = st.date_input(
                        "Last Training Date (Klik kalender):",
                        value=default_last,
                        format="DD/MM/YYYY"
                    )
                with e_c5:
                    edit_due_date = st.date_input(
                        "Next Due Date (Klik kalender):",
                        value=default_due,
                        format="DD/MM/YYYY"
                    )

                st.markdown("---")
                b_col1, b_col2 = st.columns([1, 1])
                with b_col1:
                    btn_save_manual = st.form_submit_button("💾 Simpan Perubahan ke Google Sheets", type="primary")
                with b_col2:
                    btn_del_single = st.form_submit_button("🗑️ Hapus Distrik Ini Permanen", type="secondary")

                if btn_save_manual:
                    if status_history == "Ada Riwayat Training":
                        final_last = edit_last_date.strftime("%Y-%m-%d")
                        final_due = edit_due_date.strftime("%Y-%m-%d")
                    else:
                        final_last = ""
                        final_due = ""

                    update_district_row(cur_data['id'], edit_code, edit_name, edit_cat, final_last, final_due)
                    st.success(f"✅ Data ID {cur_data['id']} ({edit_code.strip().upper()} - {edit_name.strip()}) berhasil diperbarui langsung di Google Sheets!")
                    st.rerun()

                if btn_del_single:
                    delete_district_row(cur_data['id'])
                    st.toast(f"Distrik {cur_data['code']} berhasil dihapus permanen dari Google Sheets!", icon="🗑️")
                    st.rerun()

    st.markdown("---")
    st.subheader("📋 Tabel Monitoring Distrik & Recurrent")

    if not dist_df.empty:
        df_display = dist_df.copy()
        
        def format_date_display(d_str):
            if pd.isna(d_str) or not d_str or str(d_str).strip() in ['None', '', 'nan', 'NaT']:
                return "-"
            try:
                return datetime.strptime(str(d_str)[:10], "%Y-%m-%d").strftime("%d-%b-%Y")
            except Exception:
                return str(d_str)

        df_display['Status Recurrent'] = df_display['next_due_date'].apply(calculate_status)
        df_display['Last Training Date'] = df_display['last_training_date'].apply(format_date_display)
        df_display['Next Due Date (Reminder)'] = df_display['next_due_date'].apply(format_date_display)

        st.dataframe(
            df_display[['id', 'code', 'name', 'category', 'Last Training Date', 'Next Due Date (Reminder)', 'Status Recurrent']],
            column_config={
                "id": st.column_config.NumberColumn("ID"),
                "code": st.column_config.TextColumn("Code"),
                "name": st.column_config.TextColumn("Name"),
                "category": st.column_config.TextColumn("Category"),
                "Last Training Date": st.column_config.TextColumn("Last Training Date"),
                "Next Due Date (Reminder)": st.column_config.TextColumn("Next Due Date (Reminder)"),
                "Status Recurrent": st.column_config.TextColumn("Status Recurrent")
            },
            hide_index=True,
            use_container_width=True
        )
    else:
        st.info("Data distrik sedang dimuat dari Google Sheets...")

    st.markdown("---")
    st.subheader("➕ Tambah Rute / Distrik Baru")
    with st.form("add_dist_form"):
        c1, c2, c3 = st.columns(3)
        with c1:
            new_code = st.text_input("Kode Distrik / IATA (misal: BDJ)")
        with c2:
            new_name = st.text_input("Nama Kota / Bandara (misal: Banjarmasin)")
        with c3:
            new_cat = st.selectbox("Kategori", CATEGORY_OPTIONS)
        
        btn_add = st.form_submit_button("Simpan Distrik Baru ke Google Sheets")
        if btn_add:
            if new_code and new_name:
                add_district(new_code.upper().strip(), new_name.strip(), new_cat)
                st.success(f"Distrik {new_code.upper()} berhasil ditambahkan ke Google Sheets!")
                st.rerun()
            else:
                st.error("Mohon isi kode dan nama distrik.")