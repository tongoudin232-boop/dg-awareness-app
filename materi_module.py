import streamlit as st
import os

def render_materi_module():
    st.markdown(
        """
        <div style="background: linear-gradient(135deg, #0E3B68 0%, #1a5276 100%); padding: 25px; border-radius: 12px; margin-bottom: 25px; color: white;">
            <h1 style="color: white; margin-bottom: 5px; font-size: 2.2rem;">📘 Modul Pelatihan Dangerous Goods Awareness</h1>
            <p style="color: #d4e6f1; font-size: 1.1rem; margin-bottom: 0px;">
                Panduan Komprehensif Regulasi & Penanganan Kargo Berbahaya — Sriwijaya Air & NAM Air Cargo
            </p>
            <p style="color: #aed6f1; font-size: 0.9rem; margin-top: 5px;">
                Instruktur: <b>Hadi Nurhuda</b> | Edisi: <b>Oktober 2026</b>
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.info("💡 **Petunjuk Belajar Peserta:** Pelajari seluruh materi pada tab di bawah ini sebelum memulai **Ujian DG Awareness**. Passing grade kelulusan adalah **≥ 80 poin**.")

    tabs = st.tabs([
        "1. Dasar & Bisnis Proses Kargo",
        "2. Aspek Hukum & Lisensi",
        "3. Klasifikasi 9 Kelas DG",
        "4. Prosedur Penanganan DG",
        "5. Ketentuan Penumpang (DGR 2.3.A)",
        "6. Dokumen Pengiriman & Referensi"
    ])

    # ==================== TAB 1 ====================
    with tabs[0]:
        st.header("1. Definisi & Alur Bisnis Proses Kargo")
        
        st.markdown("""
        ### Apa itu Kargo?
        **Kargo (Cargo)** adalah semua barang (*goods*) yang dikirim melalui udara, laut, atau darat baik antar wilayah/kota di dalam negeri maupun antar negara, yang dilengkapi dengan dokumen pengangkutan resmi.
        """)

        col_cg1, col_cg2 = st.columns(2)
        with col_cg1:
            st.markdown("""
            <div style="background-color: #f8f9fa; border-left: 5px solid #28a745; padding: 15px; border-radius: 6px;">
                <h4 style="color: #28a745; margin-top: 0;">📦 General Cargo</h4>
                <p>Barang-barang umum yang <b>tidak membutuhkan penanganan khusus</b> (<i>special handling</i>), namun tetap wajib memenuhi standar keselamatan (<i>safety</i>) dan keamanan penerbangan (<i>security</i>).</p>
                <b>Contoh:</b> Pakaian, suku cadang non-magnetik/non-DG, tekstil, barang manufaktur kering.
            </div>
            """, unsafe_allow_html=True)
        
        with col_cg2:
            st.markdown("""
            <div style="background-color: #f8f9fa; border-left: 5px solid #e67e22; padding: 15px; border-radius: 6px;">
                <h4 style="color: #e67e22; margin-top: 0;">⚠️ Special Cargo</h4>
                <p>Kiriman yang membutuhkan <b>penanganan khusus</b> (<i>special handling</i>) mulai dari proses penerimaan (acceptance), penimbunan/penyimpanan, penarikan, hingga pemuatan ke pesawat.</p>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("---")
        st.subheader("9 Kategori Special Cargo:")
        
        sc_cols = st.columns(3)
        with sc_cols[0]:
            st.markdown("""
            1. **Perishable Cargo (PER):** Barang mudah rusak/busuk (daging segar, ikan, buah, sayur, organ tubuh manusia/darah, farmasi).
            2. **Wet Cargo (WET):** Barang yang mengandung/menghasilkan cairan (sampel air, cairan non-DG, bibit ikan hidup).
            3. **Electronic Goods (ELI/ELM):** Handphone, laptop, gadget (syarat khusus: kondisi baru & perlindungan baterai).
            """)
        with sc_cols[1]:
            st.markdown("""
            4. **Live Animals (AVI):** Hewan hidup (mamalia, unggas, reptil, ikan hias, DOC).
            5. **Diplomatic Pouch (DIP):** Surat/arsip resmi antar negara bersegel diplomatik resmi.
            6. **Valuable Goods (VAL):** Barang bernilai tinggi (> $1.000/kg, emas, uang tunai, permata).
            """)
        with sc_cols[2]:
            st.markdown("""
            7. **Heavy Cargo (HEA):** Muatan berat > 75 kg per koli.
            8. **Dangerous Goods (DG):** Zat/artikel dengan risiko kimia, radiasi, atau bahaya ledak.
            9. **Human Remains (HUM):** Jenazah peti atau abu kremasi.
            """)

        st.markdown("---")
        st.subheader("Alur Makro Transportasi Udara (Bisnis Proses Kargo)")
        
        col_flow1, col_flow2 = st.columns(2)
        with col_flow1:
            st.markdown("""
            #### 🛫 Outgoing (Keberangkatan):
            1. **Shipper / Agent Cargo:** Menyerahkan barang dan dokumen pelengkap.
            2. **Regulated Agent (RA):** Pemeriksaan keamanan sinar X-Ray & verifikasi dokumen PTI/CSD.
            3. **Warehouse (Lini 1):** Penimbangan, verifikasi label, build-up ULD / pallet.
            4. **Proses Penarikan:** Dari Gudang Lini 1 menuju ke apron / sisi pesawat (*Aircraft*).
            5. **Aircraft Loading:** Pemuatan ke kompartemen kargo pesawat sesuai LIR (*Loading Instruction*).
            """)
        with col_flow2:
            st.markdown("""
            #### 🛬 Incoming (Kedatangan):
            1. **Unloading dari Aircraft:** Pembongkaran kargo dari kompartemen pesawat.
            2. **Warehouse Incoming (Lini 1):** Serah terima dari ramp dan verifikasi fisik koli vs manifest.
            3. **Warehouse Incoming (Lini 2):** Penyimpanan sementara di gudang penyerahan.
            4. **Distribusi / Transport Darat:** Pengambilan oleh agen / armada logistik.
            5. **Consignee:** Penerimaan barang oleh penerima akhir.
            """)

        st.markdown("---")
        st.subheader("Faktor Kapasitas Kargo Pesawat & Prioritas")
        st.write("**3 Aspek Utama Kapasitas:**")
        st.markdown("""
        * **Kemampuan Daya Angkut (Payload):** Batas berat maksimum yang diizinkan (*Maximum Zero Fuel Weight / Performance limit*).
        * **Volume Ruang Kompartemen:** Dimensi fisik (Panjang x Lebar x Tinggi) pintu dan lambung kargo pesawat.
        * **Operational Reason:** Cuaca buruk, jarak tempuh, estimasi bahan bakar cadangan (*burnoff/trip fuel*).
        """)
        st.warning("🚨 **CARGO PRIORITY ONBOARD NO. 1:** **AOG (Aircraft On Ground) Sparepart** — Komponen suku cadang pesawat teknis mendapat prioritas muat tertinggi di atas muatan komersial lainnya.")

    # ==================== TAB 2 ====================
    with tabs[1]:
        st.header("2. Aspek Legal, Regulasi, dan Lisensi Kecakapan")
        
        st.markdown("""
        Pengangkutan barang berbahaya wajib tunduk pada undang-undang dan aturan internasional terkini:
        
        ### Landasan Hukum Regulasi Penerbangan:
        * **Undang-Undang No. 1 Tahun 2009** — Tentang Penerbangan Nasional.
        * **PM 32 Tahun 2022** — Peraturan Keselamatan Penerbangan Sipil Bagian 92 (PKPS / CASR Part 92) mengenai Keselamatan Pengangkutan Barang Berbahaya Dengan Pesawat Udara.
        * **KP 412 Tahun 2014** — Petunjuk Teknis Keselamatan Pengangkutan Barang Berbahaya dengan Pesawat Udara.
        * **KP 571 Tahun 2015** — Izin Pengangkutan Barang Berbahaya dengan Pesawat Udara.
        * **ICAO Annex 18** — *Technical Instructions for the Safe Transport of Dangerous Goods by Air*.
        * **IATA Dangerous Goods Regulations (DGR)** — Edisi 66 (2025/2026) dan edisi pembaruan terkini.
        """)

        st.markdown("---")
        st.subheader("Sertifikat Kecakapan Personel (DG License):")
        
        lic_col1, lic_col2 = st.columns(2)
        with lic_col1:
            st.markdown("""
            <div style="background-color: #eef2f7; border: 1px solid #0E3B68; border-radius: 8px; padding: 15px;">
                <h4 style="color: #0E3B68; margin-top:0;">📜 DG Initial Type A</h4>
                <p>Pelatihan dan lisensi kecakapan resmi khusus untuk personel pengirim barang: <b>SHIPPERS STAFF (Pengirim Barang)</b>.</p>
            </div>
            """, unsafe_allow_html=True)
            
        with lic_col2:
            st.markdown("""
            <div style="background-color: #eef2f7; border: 1px solid #0E3B68; border-radius: 8px; padding: 15px;">
                <h4 style="color: #0E3B68; margin-top:0;">📜 DG Initial Type B</h4>
                <p>Pelatihan dan lisensi kecakapan resmi khusus untuk personel penanganan gudang bandara: <b>WAREHOUSE STAFF (Petugas Gudang)</b>.</p>
            </div>
            """, unsafe_allow_html=True)

    # ==================== TAB 3 ====================
    with tabs[2]:
        st.header("3. Klasifikasi 9 Kelas Barang Berbahaya (9 Classes of DG)")
        st.markdown("""
        **Definisi Dangerous Goods:** Artikel atau zat yang dapat menimbulkan bahaya terhadap kesehatan, keselamatan, properti, atau lingkungan saat diangkut dengan pesawat udara.
        """)

        c_dg1, c_dg2, c_dg3 = st.columns(3)

        with c_dg1:
            st.markdown("""
            <div style="border: 1px solid #e0e0e0; border-radius: 8px; padding: 12px; margin-bottom: 12px; background: #fff;">
                <h4 style="color: #c0392b; margin-top:0;">💥 KELAS 1: EXPLOSIVE</h4>
                <p style="font-size: 0.9rem;">Zat/artikel yang memiliki bahaya ledakan.</p>
                <ul style="font-size: 0.85rem; padding-left: 18px;">
                    <li><b>Divisi:</b> 1.1, 1.2, 1.3, 1.4, 1.5, 1.6</li>
                    <li><b>Catatan Khusus:</b> <b>1.4S</b> adalah bahan peledak yang terlindung baik sehingga efek luar sangat minim.</li>
                    <li><b>Contoh:</b> Bom, Kembang Api, Amunisi, Flare.</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)

            with st.markdown("""
            <div style="border: 1px solid #e0e0e0; border-radius: 8px; padding: 12px; margin-bottom: 12px; background: #fff;">
                <h4 style="color: #d35400; margin-top:0;">🔥 KELAS 4: FLAMMABLE SOLID</h4>
                <p style="font-size: 0.9rem;">Padatan mudah menyala & bahan rentan terbakar.</p>
                <ul style="font-size: 0.85rem; padding-left: 18px;">
                    <li><b>4.1:</b> Flammable Solid (mudah terbakar karena gesekan).</li>
                    <li><b>4.2:</b> Spontaneously Combustible (dapat menyala spontan terpapar udara).</li>
                    <li><b>4.3:</b> Dangerous When Wet (mengeluarkan gas mudah terbakar jika kena air).</li>
                    <li><b>Contoh:</b> Korek api, fosfor putih, belerang, natrium, kalsium karbida, serbuk magnesium.</li>
                </ul>
            </div>
            """, unsafe_allow_html=True):
                pass

            st.markdown("""
            <div style="border: 1px solid #e0e0e0; border-radius: 8px; padding: 12px; margin-bottom: 12px; background: #fff;">
                <h4 style="color: #f39c12; margin-top:0;">☢️ KELAS 7: RADIOACTIVE MATERIAL</h4>
                <p style="font-size: 0.9rem;">Bahan yang memancarkan radiasi pengion berbahaya.</p>
                <ul style="font-size: 0.85rem; padding-left: 18px;">
                    <li><b>Kategori Label:</b> Cat I (Putih), Cat II (Kuning), Cat III (Kuning).</li>
                    <li>Wajib dilengkapi Transport Index (TI).</li>
                    <li><b>Contoh:</b> Uranium, isotop medis, bahan penangkal radiasi industri.</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)

        with c_dg2:
            st.markdown("""
            <div style="border: 1px solid #e0e0e0; border-radius: 8px; padding: 12px; margin-bottom: 12px; background: #fff;">
                <h4 style="color: #27ae60; margin-top:0;">💨 KELAS 2: GASES</h4>
                <p style="font-size: 0.9rem;">Gas terkompresi, cair, atau kriogenik.</p>
                <ul style="font-size: 0.85rem; padding-left: 18px;">
                    <li><b>2.1:</b> Gas Mudah Terbakar (LPG, Propana, Aerosol).</li>
                    <li><b>2.2:</b> Gas Tidak Mudah Terbakar, Tidak Beracun (Oksigen, Nitrogen cair, CO2).</li>
                    <li><b>2.3:</b> Gas Beracun (HANYA boleh pesawat kargo / CAO).</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)

            st.markdown("""
            <div style="border: 1px solid #e0e0e0; border-radius: 8px; padding: 12px; margin-bottom: 12px; background: #fff;">
                <h4 style="color: #f1c40f; margin-top:0;">🧪 KELAS 5: OXIDIZING & ORGANIC PEROXIDE</h4>
                <p style="font-size: 0.9rem;">Zat pengoksidasi dan peroksida organik.</p>
                <ul style="font-size: 0.85rem; padding-left: 18px;">
                    <li><b>5.1:</b> Zat Pengoksidasi (mudah memicu pembakaran zat lain).</li>
                    <li><b>5.2:</b> Peroksida Organik (sangat sensitif benturan/panas).</li>
                    <li><b>Contoh:</b> Hidrogen Peroksida pekat, Pupuk Amonium Nitrat, Generator Oksigen Kimia.</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)

            st.markdown("""
            <div style="border: 1px solid #e0e0e0; border-radius: 8px; padding: 12px; margin-bottom: 12px; background: #fff;">
                <h4 style="color: #2c3e50; margin-top:0;">🧪 KELAS 8: CORROSIVE</h4>
                <p style="font-size: 0.9rem;">Bahan yang menghancurkan jaringan kulit dan merusak logam pesawat.</p>
                <ul style="font-size: 0.85rem; padding-left: 18px;">
                    <li>Dapat merusak struktur paduan aluminium pesawat bila bocor.</li>
                    <li><b>Contoh:</b> Asam Sulfat, Asam Klorida, Natrium Hidroksida (Soda api), Air aki basah.</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)

        with c_dg3:
            st.markdown("""
            <div style="border: 1px solid #e0e0e0; border-radius: 8px; padding: 12px; margin-bottom: 12px; background: #fff;">
                <h4 style="color: #e74c3c; margin-top:0;">🛢️ KELAS 3: FLAMMABLE LIQUID</h4>
                <p style="font-size: 0.9rem;">Cairan yang mudah terbakar menghasilkan uap.</p>
                <ul style="font-size: 0.85rem; padding-left: 18px;">
                    <li>Titik nyala (*Flash Point*) rendah.</li>
                    <li><b>Contoh:</b> Bensin, Avtur, Cat berbasis minyak, Aseton, Alkohol teknis, Parfum berkonsentrasi tinggi.</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)

            st.markdown("""
            <div style="border: 1px solid #e0e0e0; border-radius: 8px; padding: 12px; margin-bottom: 12px; background: #fff;">
                <h4 style="color: #8e44ad; margin-top:0;">☠️ KELAS 6: TOXIC & INFECTIOUS</h4>
                <p style="font-size: 0.9rem;">Bahan racun berbahaya dan zat penular infeksi.</p>
                <ul style="font-size: 0.85rem; padding-left: 18px;">
                    <li><b>6.1:</b> Toxic Substance (racun sianida, pestisida, timbal).</li>
                    <li><b>6.2:</b> Infectious Substance (virus aktif, sampel lab biologis, limbah medis infeksius).</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)

            st.markdown("""
            <div style="border: 1px solid #e0e0e0; border-radius: 8px; padding: 12px; margin-bottom: 12px; background: #fff;">
                <h4 style="color: #34495e; margin-top:0;">🔋 KELAS 9: MISCELLANEOUS</h4>
                <p style="font-size: 0.9rem;">Zat berbahaya lain-lain di luar 8 kelas di atas.</p>
                <ul style="font-size: 0.85rem; padding-left: 18px;">
                    <li><b>Contoh Utama:</b> Baterai Lithium (Ion & Metal), Dry Ice (CO2 padat), Mesin/Kendaraan, Magnetized Material (mengganggu kompas pesawat).</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)

    # ==================== TAB 4 ====================
    with tabs[3]:
        st.header("4. Prosedur Penanganan DG (Handling Procedure)")
        st.markdown("""
        Seringnya terjadi *incident/accident* yang berkaitan dengan barang berbahaya mewajibkan 4 pilar tahapan penanganan:
        """)

        p_cols = st.columns(4)
        with p_cols[0]:
            st.markdown("""
            #### 01. IDENTIFICATION
            * Menentukan apakah suatu barang termasuk DG atau tidak.
            * Memeriksa Proper Shipping Name (PSN) dan UN Number.
            * Verifikasi apakah barang berstatus **FORBIDDEN** (Dilarang dibawa dalam kondisi apapun).
            """)
        with p_cols[1]:
            st.markdown("""
            #### 02. PACKAGING
            * Kemasan harus memenuhi standar UN Specification.
            * Contoh kode: `4G/X20/S/21/RI/DKP001`
            * Kemasan harus mampu menahan perubahan suhu, getaran, dan tekanan udara tinggi.
            """)
        with p_cols[2]:
            st.markdown("""
            #### 03. LABELLING & MARKING
            * Label bahaya (*Hazard Label*) belah ketupat.
            * Label penanganan (*Handling Label*): *This Way Up*, *Magnetized Material*, *Cargo Aircraft Only*.
            * Penulisan alamat pengirim/penerima dan tanda UN yang jelas.
            """)
        with p_cols[3]:
            st.markdown("""
            #### 04. HANDLING & DOCS
            * Acceptance Checklist oleh petugas berlisensi.
            * Pemeriksaan kebocoran atau kerusakan sebelum muat.
            * Pembuatan dokumen **NOTOC** (*Notice to Commander*) kepada Pilot in Command.
            """)

        st.markdown("---")
        st.subheader("Bedah Kode Kemasan PBB (UN Specification Marking):")
        st.code("UN 4G / X20 / S / 21 / RI / DKP001", language="text")
        st.markdown("""
        * **UN (Simbol):** Standar sertifikasi resmi Perserikatan Bangsa-Bangsa.
        * **4G:** Tipe kemasan (4 = Kotak/Boxes, G = Fibreboard/Karton).
        * **X:** Tingkat kelompok bahaya kemasan / *Packing Group*:
            * **X** = Packing Group I (Tingkat Bahaya Sangat Tinggi / High Hazard).
            * **Y** = Packing Group II (Tingkat Bahaya Sedang / Medium Hazard).
            * **Z** = Packing Group III (Tingkat Bahaya Rendah / Low Hazard).
        * **20:** Berat kotor maksimum yang diuji dalam kilogram (20 Kg).
        * **S:** Berisi bahan padat (*Solid*) atau kemasan dalam (*Inner packagings*).
        * **21:** Tahun pembuatan kemasan (Tahun 2021).
        * **RI:** Negara pembuat / pendaftar sertifikasi (Republik Indonesia).
        * **DKP001:** Kode identitas lembaga otoritas/pabrik pembuat yang berizin resmi.
        """)

    # ==================== TAB 5 ====================
    with tabs[4]:
        st.header("5. Ketentuan Barang Bawaan Penumpang (IATA DGR Table 2.3.A)")
        st.markdown("""
        Regulasi ketat untuk barang berbahaya yang dibawa oleh penumpang atau awak pesawat (*Passenger & Crew*):
        """)

        st.markdown("---")
        st.subheader("🚫 Kategori FORBIDDEN (DILARANG TOTAL):")
        st.error("""
        Dilarang dibawa di badan, bagasi kabin, maupun bagasi tercatat:
        1. **Perangkat Pelumpuh:** Semprotan merica (*Mace/pepper spray*), gas air mata.
        2. **Senjata Kejut Listrik:** Taser atau stun gun yang mengandung bahan pemicu ledak/baterai litium.
        3. **Koper Keamanan Khusus:** Tas/kotak uang dengan sistem piroteknik terintegrasi.
        4. **Smart Baggage (Koper Pintar):** Yang baterainya tidak bisa dilepas (*non-removable*) dengan lithium metal > 0.3g atau > 2.7 Wh.
        5. **Korek Api Khusus:** Korek api gas biru (*blue flame torch lighter*), korek *strike-anywhere*.
        6. **Sistem Oksigen Cair:** *Liquid oxygen systems*.
        """)

        st.markdown("---")
        st.subheader("🔋 Aturan Baterai Lithium & Power Bank:")
        
        bp_cols = st.columns(3)
        with bp_cols[0]:
            st.markdown("""
            #### 1. Kapasitas Standar (≤ 100 Wh)
            * Smartphone, laptop, tablet standar.
            * **Power Bank:** **HANYA BOLEH DI KABIN** (DILARANG di bagasi tercatat).
            * Maksimal 20 buah baterai cadangan per orang.
            * Izin maskapai: **Tidak Diperlukan**.
            """)
        with bp_cols[1]:
            st.markdown("""
            #### 2. Kapasitas Ekstra (100 Wh - 160 Wh)
            * Baterai laptop kapasitas besar, drone profesional, alat kamera film.
            * **Wajib Izin Maskapai.**
            * Baterai cadangan maksimal **2 buah** dan **WAJIB DI KABIN**.
            """)
        with bp_cols[2]:
            st.markdown("""
            #### 3. Baterai > 160 Wh
            * **DILARANG DIBAWA PENUMPANG**.
            * Wajib dikirimkan sebagai **Kargo Resmi DG (Cargo Air Waybill)** dengan penanganan khusus.
            """)

        st.markdown("---")
        st.subheader("Ketentuan Khusus Barang Penumpang Lainnya:")
        st.markdown("""
        * **Korek Api & Pemantik Kecil:** Maksimal 1 bungkus safety matches atau 1 korek gas kecil per orang. **HANYA BOLEH DI BADAN (On One's Person)**. Dilarang ditaruh di dalam tas kabin maupun bagasi tercatat.
        * **Rokok Elektrik (Vape):** **HANYA BOLEH DI KABIN**. Dilarang keras digunakan atau diisi dayanya (*recharge*) selama berada di dalam pesawat.
        * **Minuman Beralkohol:**
            * Alkohol ≤ 24%: Tidak ada batasan khusus kargo kabin/bagasi.
            * Alkohol > 24% s/d 70%: Maksimal 5 Liter per orang dalam kemasan ritel resmi.
            * Alkohol > 70%: **Dilarang total**.
        * **Amunisi Olahraga/Dinas:** Hanya Divisi **1.4S**, maksimal **5 kg gross** per orang, wajib di **Bagasi Tercatat** dan **Wajib Izin Maskapai**.
        * **Kursi Roda Berbaterai:** Wajib masuk **Bagasi Tercatat**, baterai diisolasi/dimatikan, dan **Wajib Lapor Pilot (NOTOC)**.
        """)

    # ==================== TAB 6 ====================
    with tabs[5]:
        st.header("6. Dokumen Pengiriman & Referensi Manual Standar")
        
        st.markdown("""
        Setiap penerimaan dan pengangkutan barang berbahaya wajib disertai dokumen resmi yang sah:
        """)

        st.markdown("""
        ### Dokumen Kunci Pengangkutan Udara:
        1. **Surat Muatan Udara (SMU) / Air Waybill (AWB):** Bukti perjanjian kontrak pengangkutan udara antara pengirim (*shipper*) dan maskapai penerbangan (*carrier*). Berisi rute penerbangan, tanggal, koli, berat, dan informasi penanganan khusus.
        2. **Shipper's Declaration for Dangerous Goods (DGD / SHIPDEC):** Formulir resmi berwarna tepi garis merah yang wajib diisi dan ditandatangani oleh Shipper berlisensi Type A, menyatakan bahwa barang telah diklasifikasikan, dikemas, dan diberi label sesuai regulasi IATA DGR.
        3. **Notice to Commander (NOTOC):** Formulir pemberitahuan resmi tertulis yang diserahkan kepada Pilot in Command (Kapten Penerbang) sebelum keberangkatan mengenai lokasi dan jenis DG yang dimuat di kompartemen pesawat.
        4. **Pemberitahuan Tentang Isi (PTI):** Surat pernyataan pengirim mengenai isi kargo yang sebenarnya.
        5. **Consignment Security Declaration (CSD):** Dokumen bukti pemeriksaan keamanan kargo oleh Regulated Agent (RA).
        """)

        st.markdown("---")
        st.subheader("Manual Book Standar IATA yang Wajib Diketahui:")
        st.markdown("""
        * **DGR (Dangerous Goods Regulations):** Buku pedoman regulasi pengangkutan barang berbahaya edisi terbaru.
        * **PCR (Perishable Cargo Regulations):** Regulasi penanganan barang yang mudah rusak/membusuk.
        * **LAR (Live Animals Regulations):** Standar internasional dan kandang untuk pengangkutan hewan hidup.
        * **ICHM (IATA Cargo Handling Manual):** Manual standar prosedur penanganan kargo di gudang dan apron bandara.
        """)