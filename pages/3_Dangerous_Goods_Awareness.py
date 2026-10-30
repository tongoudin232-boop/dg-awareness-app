import streamlit as st
from datetime import date
from dateutil.relativedelta import relativedelta
import os

st.set_page_config(
    page_title="Dangerous Goods Awareness - Sriwijaya Air & NAM Air",
    page_icon="⚠️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inisialisasi Session State
if "is_instructor" not in st.session_state:
    st.session_state["is_instructor"] = False

if "current_page" not in st.session_state:
    st.session_state["current_page"] = "Modul Materi DG Awareness"

# ==================== KONTROL TAMPILAN HEADER & MOBILE ====================
if not st.session_state["is_instructor"]:
    st.markdown(
        """
        <style>
        [data-testid="stToolbar"] { display: none !important; }
        [data-testid="stDecoration"] { display: none !important; }
        footer { display: none !important; }
        [data-testid="stStatusWidget"],
        .viewerBadge_container__1QSob,
        .viewerBadge_link__1S137,
        div[class*="viewerBadge"],
        div[class*="ProfileBadge"],
        div[class*="StatusWidget"],
        div[data-testid="stActionButton"],
        a[href*="share.streamlit.io/user"],
        div[data-baseweb="popover"],
        div[role="tooltip"],
        #MainMenu {
            display: none !important;
            visibility: hidden !important;
            opacity: 0 !important;
            pointer-events: none !important;
        }
        [data-testid="collapsedControl"] {
            display: flex !important;
            visibility: visible !important;
            opacity: 1 !important;
            z-index: 999999 !important;
            top: 10px !important;
            left: 10px !important;
            background: #0E3B68 !important;
            color: #ffffff !important;
            border-radius: 8px !important;
            padding: 4px !important;
        }
        [data-testid="collapsedControl"] svg {
            fill: #ffffff !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

# ==================== SISTEM AKSES INSTRUKTUR (SIDEBAR) ====================
if os.path.exists("logo_sriwijaya.png"):
    st.sidebar.image("logo_sriwijaya.png", use_container_width=True)

st.sidebar.title("Navigasi Utama")

if st.session_state["is_instructor"]:
    menu_options = [
        "Modul Materi DG Awareness",
        "Ujian DG Awareness",
        "Dashboard Instruktur (WIP)"
    ]
    cur_idx = menu_options.index(st.session_state["current_page"]) if st.session_state["current_page"] in menu_options else 0
    selected_menu = st.sidebar.radio("Pilih Menu:", menu_options, index=cur_idx)
    st.session_state["current_page"] = selected_menu

    st.sidebar.markdown("---")
    if st.sidebar.button("🔒 Logout Instruktur"):
        st.session_state["is_instructor"] = False
        st.session_state["current_page"] = "Modul Materi DG Awareness"
        st.rerun()
else:
    participant_options = ["Modul Materi DG Awareness", "Ujian DG Awareness"]
    p_idx = participant_options.index(st.session_state["current_page"]) if st.session_state["current_page"] in participant_options else 0
    selected_p = st.sidebar.radio("Pilih Menu:", participant_options, index=p_idx)
    st.session_state["current_page"] = selected_p

    with st.sidebar.expander("🔐 Akses Khusus Instruktur", expanded=False):
        instructor_pin = st.text_input("Masukkan PIN Instruktur:", type="password")
        if st.button("Masuk"):
            if instructor_pin == "5678":
                st.session_state["is_instructor"] = True
                st.success("Login berhasil!")
                st.rerun()
            else:
                st.error("PIN salah!")

if not st.session_state["is_instructor"]:
    nav_c1, nav_c2 = st.columns(2)
    with nav_c1:
        if st.button("📘 Baca Modul Materi", use_container_width=True, type="primary" if st.session_state["current_page"] == "Modul Materi DG Awareness" else "secondary"):
            st.session_state["current_page"] = "Modul Materi DG Awareness"
            st.rerun()
    with nav_c2:
        if st.button("✍️ Kerjakan Ujian DG", use_container_width=True, type="primary" if st.session_state["current_page"] == "Ujian DG Awareness" else "secondary"):
            st.session_state["current_page"] = "Ujian DG Awareness"
            st.rerun()
    st.markdown("<hr style='margin-top: 5px; margin-bottom: 20px;'>", unsafe_allow_html=True)

menu = st.session_state["current_page"]

SOAL_UJIAN_RESMI = [
    {"no": 1, "q": "Klasifikasi Dangerous Goods dibagi menjadi?", "options": ["a) 1 class", "b) 7 Class", "c) 9 Class", "d) 8 Class"], "a": "c) 9 Class"},
    {"no": 2, "q": "Manakah zat/artikel di bawah ini yang termasuk dalam kategori DG Class-1 (Explosive)?", "options": ["a) Natrium Klorida", "b) Bomb, Amunisi & Kembang Api", "c) Magnet", "d) Asam Sulfat"], "a": "b) Bomb, Amunisi & Kembang Api"},
    {"no": 3, "q": "Manakah zat/artikel di bawah ini yang termasuk dalam kategori DG Class-2 (Gases)?", "options": ["a) Gas Oksigen", "b) Bensin", "c) Alkohol", "d) Parfum"], "a": "a) Gas Oksigen"},
    {"no": 4, "q": "Manakah zat/artikel di bawah ini yang termasuk dalam kategori DG Class-3 (Flammable Liquid)?", "options": ["a) Gas Oksigen", "b) Bensin", "c) Air Aki", "d) Gas karbondioksida"], "a": "b) Bensin"},
    {"no": 5, "q": "Manakah zat/artikel di bawah ini yang termasuk dalam kategori DG Class-4 (Flammable Solid)?", "options": ["a) Gas Oksigen", "b) Aceton", "c) Sulfur, logam alkali", "d) Gas karbondioksida"], "a": "c) Sulfur, logam alkali"},
    {"no": 6, "q": "Manakah zat/artikel di bawah ini yang termasuk dalam kategori DG Class-5 (Oxidizing Substances & Organic peroxide)?", "options": ["a) Hidrogen peroksida", "b) Oksigen Generator", "c) Jawaban a & b (benar)", "d) Gas karbondioksida"], "a": "c) Jawaban a & b (benar)"},
    {"no": 7, "q": "Manakah zat/artikel di bawah ini yang termasuk dalam kategori DG Class-6 (Toxic & Infectious Substances)?", "options": ["a) Sianida", "b) Bensin", "c) Sampel virus", "d) Jawaban a & c (benar)"], "a": "d) Jawaban a & c (benar)"},
    {"no": 8, "q": "Manakah zat/artikel di bawah ini yang termasuk dalam kategori DG Class-7 (Radioaktive Material)?", "options": ["a) Natrium Benzoat", "b) Uranium", "c) Aluminium", "d) Lithium"], "a": "b) Uranium"},
    {"no": 9, "q": "Manakah zat/artikel di bawah ini yang termasuk dalam kategori DG Class-8 (Corrosive)?", "options": ["a) Kalsium", "b) Plutonium", "c) Asam sulfat", "d) Lithium"], "a": "c) Asam sulfat"},
    {"no": 10, "q": "Manakah zat/artikel di bawah ini yang termasuk dalam kategori DG Class-9 (Miscellaneous Material)?", "options": ["a) Magnet Material", "b) Jawaban a & d (benar)", "c) Air Aki", "d) Lithium Battery"], "a": "b) Jawaban a & d (benar)"},
    {"no": 11, "q": "Dangerous Goods Class 6 (Toxic & Infectious Substances) terbagi menjadi sub divisi?", "options": ["a) 6.1, 6.2", "b) 6.1, 6.2, 6.3", "c) 6.1", "d) 6.1, 6.2, 6.3, 6.4"], "a": "a) 6.1, 6.2"},
    {"no": 12, "q": "Dangerous Goods Class 5 (Oxidizing Substances & Organic Peroxide) terbagi menjadi sub divisi?", "options": ["a) 5.1", "b) 5.1, 5.2, 5.3, 5.4", "c) 5.1, 5.2", "d) 5.1, 5.2, 5.3"], "a": "c) 5.1, 5.2"},
    {"no": 13, "q": "Dangerous Goods Class 4 (Flammable Solid) terbagi menjadi sub divisi?", "options": ["a) 4.1, 4.2, 4.3, 4.4, 4.5", "b) 4.1", "c) 4.1, 4.2, 4.3", "d) 4.1, 4.2"], "a": "c) 4.1, 4.2, 4.3"},
    {"no": 14, "q": "Dangerous Goods Class 2 (Gases) terbagi menjadi sub divisi?", "options": ["a) 2.1, 2.2, 2.3", "b) 2.1, 2.2", "c) 2.1, 2.2, 2.3, 2.4, 2.5", "d) 2.1"], "a": "a) 2.1, 2.2, 2.3"},
    {"no": 15, "q": "Packing Group I dengan kode (X) menandakan tingkat bahaya?", "options": ["a) Medium Danger", "b) High Danger", "c) Low Danger", "d) Small Danger"], "a": "b) High Danger"},
    {"no": 16, "q": "Packing Group II dengan kode (Y) menandakan tingkat bahaya?", "options": ["a) High Danger", "b) Low Danger", "c) Small Danger", "d) Medium Danger"], "a": "d) Medium Danger"},
    {"no": 17, "q": "Packing Group III dengan kode (Z) menandakan tingkat bahaya?", "options": ["a) High Danger", "b) Medium Danger", "c) Low Danger", "d) Small Danger"], "a": "c) Low Danger"},
    {"no": 18, "q": "MSDS adalah lembar petunjuk yang berisikan informasi dari sebuah bahan/produk meliputi sifat kimiawi, jenis bahaya yang ditimbulkan, cara penanganan serta tindakan khusus dalam keadaan darurat. MSDS adalah singkatan dari?", "options": ["a) Material Security Data Safety", "b) Material Safety Data Security", "c) Material Safety Data Sheet", "d) Material Sheet Data Safety"], "a": "c) Material Safety Data Sheet"},
    {"no": 19, "q": "Yang dimaksud dengan Limitasi Dangerous Goods kategori Forbidden/Dilarang adalah:", "options": ["a) Artikel/Zat yang tidak boleh diangkut pada penerbangan dalam keadaan dan kondisi apapun.", "b) Artikel/zat yang diangkut pada penerbangan normal dalam kemasan tertentu.", "c) Artikel/zat yang diangkut pada penerbangan dalam kondisi tertentu.", "d) Artikel/zat yang diangkut pada penerbangan dengan Batasan tertentu."], "a": "a) Artikel/Zat yang tidak boleh diangkut pada penerbangan dalam keadaan dan kondisi apapun."},
    {"no": 20, "q": "Dangerous Goods dikelompokkan pada Group Pengepakan (Packing Group) yang relevan berdasarkan tingkat bahayanya yang terbagi menjadi berapa kelompok packing group?", "options": ["a) 2 Packing Group", "b) 1 Packing Group", "c) 3 Packing Group", "d) 4 Packing Group"], "a": "c) 3 Packing Group"},
    {"no": 21, "q": "Tindakan apa yang harus dilakukan ketika terjadi insiden kebocoran DG Class 3?", "options": ["a) Padamkan api menggunakan air", "b) Taburkan pasir / serbuk kayu pada tampakan TUMPAHAN", "c) Cegah semua sumber api", "d) b dan c benar"], "a": "d) b dan c benar"},
    {"no": 22, "q": "Tindakan apa yang harus dilakukan ketika terjadi insiden paket yang mengandung baterai lithium mengeluarkan asap?", "options": ["a) Berada diposisi menghadap arah angin", "b) Berada diposisi berlawanan arah angin", "c) b dan d benar", "d) Hubungi PKP-PK"], "a": "c) b dan d benar"},
    {"no": 23, "q": "Pilih pernyataan yang benar bagi penumpang yang ingin membawa Smart Baggage (removable batteries)?", "options": ["a) Baterai harus dilepas dan dibawa ke dalam kabin", "b) Hanya boleh dibawa apabila dalam keadaan kosong", "c) Harus masuk bagasi kabin"], "a": "a) Baterai harus dilepas dan dibawa ke dalam kabin"},
    {"no": 24, "q": "Manakah dari kelas barang berbahaya (Dangerous Goods) berikut yang secara tegas dinyatakan tidak diangkut oleh Sriwijaya Air?", "options": ["a) Class 2.1", "b) Class 6.2", "c) Class 7", "d) Class 8"], "a": "c) Class 7"},
    {"no": 25, "q": "Tempat penyimpanan yang benar untuk 'small cigarette lighter' selama penerbangan adalah..", "options": ["a) Saku celana", "b) Saku jaket", "c) Bagasi kabin", "d) a dan b benar"], "a": "d) a dan b benar"}
]

if menu == "Modul Materi DG Awareness":
    st.markdown("""
    <div style='background-color:#1e4c7a; padding: 25px; border-radius: 10px; color: white;'>
        <h2 style='color: white; margin-top: 0;'>Modul Pelatihan Dangerous Goods Awareness</h2>
        <p style='margin-bottom: 0;'>Panduan Komprehensif Regulasi & Penanganan Kargo Berbahaya — Sriwijaya Air & NAM Air Cargo</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    st.info("💡 Petunjuk Belajar Peserta: Pelajari seluruh materi pada tab di bawah ini sebelum memulai Ujian DG Awareness. Passing grade kelulusan adalah ≥ 80 poin.")

    st.markdown("""
    ---
    ### **1. PENGERTIAN DANGEROUS GOODS**
    **Dangerous Goods (Barang Berbahaya)** adalah benda atau zat yang berisiko membahayakan kesehatan, keselamatan, aset properti, maupun lingkungan hidup dan keberadaannya ada di dalam daftar barang berbahaya menurut *IATA Dangerous Goods Regulations (DGR)* atau yang diklasifikasikan berdasarkan regulasi tersebut.

    ### **2. BATASAN BARANG BERBAHAYA (LIMITATION)**
    Terdapat 3 jenis batasan pengangkutan barang berbahaya melalui udara:
    1. **Barang Berbahaya yang DILARANG (Forbidden) diangkut dalam keadaan apapun.** Contoh: Bahan peledak cair yang mudah menguap.
    2. **Barang Berbahaya yang DILARANG diangkut kecuali mendapat pengecualian khusus (Exemption).** Contoh: Material infeksius tingkat tinggi, atau hewan berpenyakit.
    3. **Barang Berbahaya yang DAPAT diangkut sebagai kargo.** Syaratnya harus mematuhi semua aturan berat, pengemasan, label, dan dokumen DGD (Dangerous Goods Declaration).

    > **CATATAN KHUSUS SRIWIJAYA AIR & NAM AIR:**
    > Maskapai PT Sriwijaya Air dan PT NAM Air secara tegas **DILARANG (TIDAK MENERIMA)** pengangkutan Barang Berbahaya Kelas 7 (*Radioactive Material*).
    
    ---
    ### **3. KLASIFIKASI 9 KELAS DANGEROUS GOODS**
    PBB (United Nations) mengelompokkan bahaya menjadi 9 kelas utama:
    * **Class 1 - Explosives (Bahan Peledak):** Amunisi, kembang api, suar.
    * **Class 2 - Gases (Gas):** Dibagi menjadi 2.1 (Gas mudah terbakar - Butana), 2.2 (Gas tidak mudah terbakar & tidak beracun - Oksigen, Nitrogen), 2.3 (Gas Beracun).
    * **Class 3 - Flammable Liquids (Cairan Mudah Menyala):** Bensin, avtur, alkohol, aseton, cat, parfum cair.
    * **Class 4 - Flammable Solids (Padatan Mudah Menyala):** Belerang/sulfur, fosfor, logam alkali (seperti kalium).
    * **Class 5 - Oxidizing & Organic Peroxides:**
      * 5.1: Bahan Oksidator (Oksigen generator kimia).
      * 5.2: Peroksida Organik (Hidrogen peroksida, pemutih keras).
    * **Class 6 - Toxic & Infectious:** 
      * 6.1: Zat beracun (Sianida, pestisida). 
      * 6.2: Zat Infeksius (Sampel darah virus/bakteri berbahaya, limbah medis).
    * **Class 7 - Radioactive Materials:** Uranium, Plutonium, isotop medis. *(TIDAK DIANGKUT SJ/IN).*
    * **Class 8 - Corrosives (Zat Korosif):** Asam sulfat, air aki, soda api, raksa/merkuri.
    * **Class 9 - Miscellaneous (Zat Berbahaya Lainnya):** Baterai Lithium (Ion & Metal), kendaraan bertenaga mesin, magnet kuat, *Dry Ice* (Es Kering).

    ---
    ### **4. PACKING GROUP (TINGKAT BAHAYA & PENGEMASAN)**
    Bahan berbahaya dikelompokkan ke dalam 3 *Packing Group (PG)* berdasarkan tingkat keparahan risikonya untuk menentukan ketebalan dan kekuatan kemasan:
    * **PG I (Great Danger / Bahaya Sangat Tinggi):** Disimbolkan dengan kode pengujian "X". (Contoh: Sianida sangat beracun).
    * **PG II (Medium Danger / Bahaya Menengah):** Disimbolkan dengan kode pengujian "Y". (Contoh: Bensin).
    * **PG III (Minor Danger / Bahaya Rendah):** Disimbolkan dengan kode pengujian "Z". (Contoh: Cairan parfum).

    ---
    ### **5. LABELING & MARKING**
    * **Hazard Labels:** Berbentuk belah ketupat (45 derajat), menampilkan simbol bahaya kelas 1-9 (contoh: simbol api merah untuk kelas 3).
    * **Handling Labels:** Label instruksi penanganan seperti *Cargo Aircraft Only (CAO)*, arah panah *This Way Up*, atau *Cryogenic Liquid*.
    * **Marking:** Nomor UN (contoh: UN 1863), Proper Shipping Name (PSN), nama & alamat Shipper dan Consignee, berat isi.

    ---
    ### **6. TANGGUNG JAWAB OPERASIONAL LOA (Sesuai Role)**
    * **SHIPPER / PACKER:** Bertanggung jawab penuh atas keabsahan MSDS (*Material Safety Data Sheet*), pengemasan yang menggunakan *UN Specification Packaging*, pelabelan yang akurat, serta mengisi dokumen *Shipper's Declaration for Dangerous Goods (DGD)*.
    * **ACCEPTANCE (Regulated Agent / Ground Handling):** Melakukan pemeriksaan dokumen (AWB & DGD) dan fisik kargo menggunakan formulir *Dangerous Goods Acceptance Checklist* yang diterbitkan oleh IATA. Kargo yang cacat/bocor harus langsung ditolak (REJECT).
    * **CARGO LOADER & LOAD MASTER:** Bertanggung jawab dalam penyusunan (*stowing*) dan pemisahan (*segregation*) di perut pesawat (kompartemen). Barang korosif (Class 8) dilarang diletakkan berdampingan dengan benda yang mudah bereaksi, serta barang beracun (Class 6) dilarang berdekatan dengan bahan makanan/hewan hidup. Load Master wajib menyampaikan dokumen **NOTOC (Notice to Captain)** kepada Pilot sebelum *take-off*.

    ---
    ### **7. EMERGENCY RESPONSE (PROSEDUR DARURAT)**
    Jika terjadi tumpahan (spillage) atau insiden kebocoran DG:
    1. Jauhi tumpahan dan cari posisi yang **Beralawanan Arah Angin** (*upwind*) agar tidak menghirup uap beracun.
    2. Identifikasi bahan melalui label atau buku MSDS (jika aman).
    3. Isolasi area (buat parameter keamanan).
    4. Hubungi tim tanggap darurat bandara (PKP-PK / ARFF).
    5. Untuk tumpahan zat mudah terbakar (Class 3), taburkan serbuk kayu/pasir/absorbent, **DILARANG menggunakan air** langsung yang dapat menyebarkan api/reaksi. Untuk baterai Lithium yang berasap, segera amankan dari sumber panas.
    """)
    
    st.markdown("---")
    st.markdown("<div style='text-align: center;'>", unsafe_allow_html=True)
    if st.button("🚀 Sudah Memahami Materi? Mulai Ujian DG Sekarang", type="primary", use_container_width=True):
        st.session_state["current_page"] = "Ujian DG Awareness"
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


elif menu == "Ujian DG Awareness":
    st.markdown("### ⚠️ Modul Pelatihan & Ujian Dangerous Goods Awareness")
    st.caption("Panduan Komprehensif Regulasi & Penanganan Kargo Berbahaya — Sriwijaya Air & NAM Air Cargo")
    
    st.subheader("Evaluasi Kompetensi DG Awareness")
    st.write("Jawab 25 butir pertanyaan berikut dengan teliti. Passing Grade: **≥ 80 poin**.")
    with st.form("form_exam_dg_standalone", clear_on_submit=False):
        answers = {}
        for q_item in SOAL_UJIAN_RESMI:
            st.markdown(f"**Soal {q_item['no']}:** {q_item['q']}")
            answers[q_item['no']] = st.radio(
                f"Pilih jawaban untuk nomor {q_item['no']}:",
                options=q_item["options"],
                index=None,
                key=f"dg_q_{q_item['no']}"
            )
            st.write("")
            
        if st.form_submit_button("Submit Evaluasi DG Awareness", type="primary"):
            unanswered = [q["no"] for q in SOAL_UJIAN_RESMI if answers[q["no"]] is None]
            if unanswered:
                st.error("Harap jawab semua soal terlebih dahulu!")
            else:
                skor_benar = sum(4 for q in SOAL_UJIAN_RESMI if answers[q["no"]] == q["a"])
                score = skor_benar * 4
                if score >= 80:
                    st.success(f"🎉 SELAMAT! Anda LULUS dengan skor **{score}/100**. (Catatan: Untuk menerbitkan LoA resmi, pastikan Anda juga mengikuti prosedur Ujian di menu Letter of Authorization dengan memasukkan NIK terdaftar)")
                else:
                    st.error(f"Nilai Anda {score}/100 (Passing Grade: 80). Silakan baca kembali materi dan ulangi.")

elif menu == "Dashboard Instruktur (WIP)":
    st.header("⚙️ Panel Manajemen Instruktur")
    st.info("Fitur manajemen materi dan bank soal sedang dalam pengembangan.")
