import streamlit as st
import os

st.set_page_config(
    page_title="Home - Sriwijaya Air & NAM Air Training & Authorization",
    page_icon="✈️",
    layout="wide"
)

# ==================== KONTROL TAMPILAN HEADER & MOBILE ====================
st.markdown(
    """
    <style>
    /* 1. BERI TIANG PENYANGGA PADA HEADER AGAR TIDAK KEMPIS SAAT TOMBOL KANAN HILANG */
    [data-testid="stHeader"] {
        min-height: 4.5rem !important;
        background: transparent !important;
    }
    
    /* 2. JADIKAN TOMBOL KANAN (FORK, GITHUB, TITIK TIGA) KACA/TRANSPARAN (KEBAL KLIK) */
    [data-testid="stToolbarActions"],
    .stAppDeployButton,
    #MainMenu {
        opacity: 0 !important;
        pointer-events: none !important;
    }
    
    /* 3. MUNCULKAN PANAH SIDEBAR DENGAN KOTAK BIRU GELAP AGAR KONTRAS */
    [data-testid="collapsedControl"] {
        display: flex !important;
        visibility: visible !important;
        opacity: 1 !important;
        background-color: #0b1d3a !important;
        border-radius: 8px !important;
        padding: 5px !important;
        margin-top: 5px !important;
        margin-left: 5px !important;
        z-index: 999999 !important;
    }
    [data-testid="collapsedControl"] svg {
        fill: #ffffff !important;
        color: #ffffff !important;
    }
    
    /* 4. MATIKAN TULISAN "HOSTED WITH STREAMLIT" DI POJOK BAWAH */
    [class*="viewerBadge"] {
        display: none !important;
    }

    /* 5. SEMBUNYIKAN MENU "APP" DI SIDEBAR */
    [data-testid="stSidebarNav"] ul li:first-child {
        display: none !important;
    }
    
    /* 6. SEMBUNYIKAN GARIS WARNA-WARNI & FOOTER STREAMLIT */
    [data-testid="stDecoration"], footer {
        display: none !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Custom Styling mimicking the dark blue banner
st.markdown("""
<style>
    .main-banner {
        background-color: #0b1d3a;
        padding: 40px;
        border-radius: 8px;
        color: white;
        margin-bottom: 25px;
    }
    .main-banner h1 {
        font-size: 2.5rem;
        font-weight: 700;
        margin-bottom: 5px;
        letter-spacing: 1px;
    }
    .main-banner h3 {
        font-size: 1.5rem;
        color: #4da6ff;
        margin-bottom: 20px;
        font-weight: 500;
    }
    .main-banner p {
        font-size: 1.1rem;
        line-height: 1.6;
        color: #e0e0e0;
        margin-top: 15px;
    }
</style>

<div class="main-banner">
    <h1>TRAINING & AUTHORIZATION</h1>
    <h3>MANAGEMENT SYSTEM</h3>
    <p style="font-size: 0.95rem; color: #b3d1ff; letter-spacing: 0.5px; text-transform: uppercase; font-weight: 600; margin-bottom: 25px;">
        DANGEROUS GOODS • COMPETENCY • AUTHORIZATION
    </p>
    <hr style="border-color: #1f3a60; margin-bottom: 25px;">
    <h2 style="font-size: 1.8rem; font-weight: 600; color: #ffffff; margin-bottom: 15px;">Welcome to Our Digital Training Portal</h2>
    <p>Selamat datang di platform digital pelatihan, evaluasi kompetensi, dan pengelolaan otorisasi personel Sriwijaya Air, NAM Air, serta mitra kerja.</p>
    <p>Platform ini hadir untuk mendukung peningkatan kompetensi, kepatuhan terhadap regulasi, dan penerapan standar keselamatan dalam kegiatan operasional penerbangan.</p>
</div>
""", unsafe_allow_html=True)

# Menampilkan gambar pesawat berdampingan
if os.path.exists("aircraft_tails.png"):
    st.image("aircraft_tails.png", use_container_width=True, caption="Sriwijaya Air & NAM Air Fleet Operations")
else:
    st.info("💡 Pastikan file gambar 'aircraft_tails.png' berada di direktori utama Anda.")