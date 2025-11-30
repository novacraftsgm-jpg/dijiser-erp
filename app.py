from flask import Flask, request, jsonify, send_from_directory
import sqlite3
import json
from datetime import datetime
import os
from mailjet_rest import Client

app = Flask(__name__, static_folder='.', static_url_path='')

DATABASE = 'erp_database.db'

def get_db():
    conn = sqlite3.connect(DATABASE, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS licenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        license_code TEXT UNIQUE NOT NULL,
        company_name TEXT NOT NULL,
        admin_password TEXT DEFAULT 'admin123',
        is_active INTEGER DEFAULT 1,
        created_at TEXT
    )''')
    
    # Ürün Kataloğu (Protera Ürünleri - Tedarik, Lojistik, Servis vb.)
    c.execute('''CREATE TABLE IF NOT EXISTS protera_products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_code TEXT UNIQUE NOT NULL,
        product_name TEXT NOT NULL,
        description TEXT,
        monthly_price REAL DEFAULT 1250,
        is_active INTEGER DEFAULT 1,
        icon TEXT,
        color TEXT,
        created_at TEXT
    )''')
    
    # Lisans-Ürün İlişkisi (Hangi firma hangi ürünleri kullanıyor)
    c.execute('''CREATE TABLE IF NOT EXISTS license_products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        license_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        is_active INTEGER DEFAULT 1,
        activated_at TEXT,
        expires_at TEXT,
        created_at TEXT,
        FOREIGN KEY (license_id) REFERENCES licenses(id),
        FOREIGN KEY (product_id) REFERENCES protera_products(id)
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        license_code TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL,
        role TEXT DEFAULT 'Kullanıcı',
        yetkiler TEXT,
        created_at TEXT
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        license_code TEXT NOT NULL,
        proje_kodu TEXT NOT NULL,
        proje_adi TEXT NOT NULL,
        santiye_sefi TEXT,
        lokasyon TEXT,
        baslangic_tarihi TEXT,
        bitis_tarihi TEXT,
        butce REAL DEFAULT 0,
        durum TEXT DEFAULT 'Aktif',
        aciklama TEXT,
        created_at TEXT
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        license_code TEXT NOT NULL,
        urun_kodu TEXT NOT NULL,
        urun_adi TEXT NOT NULL,
        birim TEXT NOT NULL,
        stok_miktari REAL DEFAULT 0,
        minimum_stok REAL DEFAULT 10,
        created_at TEXT
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS suppliers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        license_code TEXT NOT NULL,
        tedarikci_adi TEXT NOT NULL,
        tedarikci_email TEXT,
        tedarikci_telefon TEXT,
        tedarikci_adres TEXT,
        created_at TEXT
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        license_code TEXT NOT NULL,
        talep_no TEXT NOT NULL,
        proje_id INTEGER,
        talep_eden TEXT,
        departman TEXT,
        aciliyet TEXT DEFAULT 'Normal',
        aciklama TEXT,
        durum TEXT DEFAULT 'Beklemede',
        created_at TEXT
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS request_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        license_code TEXT NOT NULL,
        talep_id INTEGER NOT NULL,
        urun_id INTEGER NOT NULL,
        urun_kodu TEXT,
        urun_adi TEXT,
        miktar REAL NOT NULL,
        birim TEXT,
        beklenen_teslim TEXT,
        aciklama TEXT,
        created_at TEXT
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS offers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        license_code TEXT NOT NULL,
        teklif_no TEXT NOT NULL,
        talep_id INTEGER NOT NULL,
        tedarikci_id INTEGER NOT NULL,
        tedarikci_adi TEXT,
        birim_fiyat REAL,
        toplam_fiyat REAL,
        odeme_vadesi TEXT,
        teslim_suresi TEXT,
        notlar TEXT,
        onaylandi INTEGER DEFAULT 0,
        created_at TEXT
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        license_code TEXT NOT NULL,
        siparis_no TEXT NOT NULL,
        talep_id INTEGER,
        talep_no TEXT,
        tedarikci_id INTEGER,
        tedarikci_adi TEXT,
        siparis_urunleri TEXT,
        genel_toplam REAL DEFAULT 0,
        teslim_tarihi TEXT,
        aciklama TEXT,
        teslim_durumu TEXT,
        teslim_miktarlari TEXT,
        teslim_uyumsuzluk TEXT,
        durum TEXT DEFAULT 'Beklemede',
        created_at TEXT
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS stock_movements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        license_code TEXT NOT NULL,
        urun_id INTEGER NOT NULL,
        urun_kodu TEXT,
        urun_adi TEXT,
        hareket_tipi TEXT NOT NULL,
        miktar REAL NOT NULL,
        birim TEXT,
        aciklama TEXT,
        created_at TEXT
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS invoices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        license_code TEXT NOT NULL,
        siparis_id INTEGER,
        siparis_no TEXT,
        tedarikci_adi TEXT,
        fatura_no TEXT NOT NULL,
        fatura_tarihi TEXT,
        fatura_tutari REAL,
        notlar TEXT,
        created_at TEXT
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS user_activities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        license_code TEXT NOT NULL,
        user_id INTEGER NOT NULL,
        user_email TEXT,
        activity_type TEXT NOT NULL,
        activity_description TEXT,
        related_id INTEGER,
        created_at TEXT
    )''')
    
    try:
        c.execute("ALTER TABLE offers ADD COLUMN odeme_vadesi TEXT")
    except: pass
    try:
        c.execute("ALTER TABLE offers ADD COLUMN onaylandi INTEGER DEFAULT 0")
    except: pass
    try:
        c.execute("ALTER TABLE offers ADD COLUMN urun_fiyatlari TEXT")
    except: pass
    try:
        c.execute("ALTER TABLE orders ADD COLUMN teslim_tarihi TEXT")
    except: pass
    try:
        c.execute("ALTER TABLE orders ADD COLUMN aciklama TEXT")
    except: pass
    try:
        c.execute("ALTER TABLE orders ADD COLUMN teslim_durumu TEXT")
    except: pass
    try:
        c.execute("ALTER TABLE orders ADD COLUMN teslim_miktarlari TEXT")
    except: pass
    try:
        c.execute("ALTER TABLE orders ADD COLUMN teslim_uyumsuzluk TEXT")
    except: pass
    try:
        c.execute("ALTER TABLE invoices ADD COLUMN matrah REAL")
    except: pass
    try:
        c.execute("ALTER TABLE invoices ADD COLUMN kdv_orani INTEGER")
    except: pass
    try:
        c.execute("ALTER TABLE invoices ADD COLUMN kdv_tutari REAL")
    except: pass
    try:
        c.execute("ALTER TABLE invoices ADD COLUMN fatura_urunleri TEXT")
    except: pass
    try:
        c.execute("ALTER TABLE stock_movements ADD COLUMN kaynak_depo TEXT")
    except: pass
    try:
        c.execute("ALTER TABLE stock_movements ADD COLUMN hedef_depo TEXT")
    except: pass
    try:
        c.execute("ALTER TABLE products ADD COLUMN ana_kategori TEXT")
    except: pass
    try:
        c.execute("ALTER TABLE products ADD COLUMN alt_kategori TEXT")
    except: pass
    try:
        c.execute("ALTER TABLE products ADD COLUMN alt_kategori_2 TEXT")
    except: pass
    
    try:
        c.execute("ALTER TABLE licenses ADD COLUMN paket_tipi TEXT DEFAULT 'standart'")
    except: pass
    try:
        c.execute("ALTER TABLE licenses ADD COLUMN baslangic_tarihi TEXT")
    except: pass
    try:
        c.execute("ALTER TABLE licenses ADD COLUMN bitis_tarihi TEXT")
    except: pass
    try:
        c.execute("ALTER TABLE licenses ADD COLUMN aylik_ucret REAL DEFAULT 0")
    except: pass
    try:
        c.execute("ALTER TABLE licenses ADD COLUMN iletisim_email TEXT")
    except: pass
    try:
        c.execute("ALTER TABLE licenses ADD COLUMN iletisim_telefon TEXT")
    except: pass
    
    c.execute('''CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        license_code TEXT NOT NULL,
        seviye INTEGER NOT NULL,
        kategori_adi TEXT NOT NULL,
        ust_kategori_id INTEGER,
        created_at TEXT
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS project_statuses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        license_code TEXT NOT NULL,
        durum_adi TEXT NOT NULL,
        sira INTEGER DEFAULT 0,
        created_at TEXT
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS super_admins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        ad_soyad TEXT,
        created_at TEXT
    )''')
    
    # ==================== LOJISTIK TABLOLARI ====================
    
    # Lojistik Kullanıcıları
    c.execute('''CREATE TABLE IF NOT EXISTS loj_users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        license_code TEXT NOT NULL,
        email TEXT NOT NULL,
        password TEXT NOT NULL,
        ad_soyad TEXT,
        role TEXT DEFAULT 'Kullanıcı',
        yetkiler TEXT,
        telefon TEXT,
        created_at TEXT,
        UNIQUE(license_code, email)
    )''')
    
    # Araçlar
    c.execute('''CREATE TABLE IF NOT EXISTS loj_araclar (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        license_code TEXT NOT NULL,
        plaka TEXT NOT NULL,
        marka TEXT,
        model TEXT,
        yil INTEGER,
        arac_tipi TEXT,
        kapasite_ton REAL,
        kapasite_m3 REAL,
        yakit_tipi TEXT,
        sigorta_bitis TEXT,
        muayene_bitis TEXT,
        kasko_bitis TEXT,
        km_sayaci INTEGER DEFAULT 0,
        durum TEXT DEFAULT 'Aktif',
        notlar TEXT,
        created_at TEXT
    )''')
    
    # Sürücüler
    c.execute('''CREATE TABLE IF NOT EXISTS loj_suruculer (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        license_code TEXT NOT NULL,
        ad_soyad TEXT NOT NULL,
        tc_no TEXT,
        telefon TEXT,
        email TEXT,
        adres TEXT,
        ehliyet_sinifi TEXT,
        ehliyet_no TEXT,
        ehliyet_bitis TEXT,
        src_belgesi TEXT,
        src_bitis TEXT,
        psikoteknik_bitis TEXT,
        maas REAL DEFAULT 0,
        ise_giris TEXT,
        zimmetli_arac_id INTEGER,
        durum TEXT DEFAULT 'Aktif',
        notlar TEXT,
        created_at TEXT
    )''')
    
    # Müşteriler
    c.execute('''CREATE TABLE IF NOT EXISTS loj_musteriler (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        license_code TEXT NOT NULL,
        musteri_kodu TEXT,
        firma_adi TEXT NOT NULL,
        yetkili_kisi TEXT,
        telefon TEXT,
        email TEXT,
        adres TEXT,
        vergi_no TEXT,
        vergi_dairesi TEXT,
        odeme_vadesi INTEGER DEFAULT 0,
        notlar TEXT,
        created_at TEXT
    )''')
    
    # Sevkiyatlar
    c.execute('''CREATE TABLE IF NOT EXISTS loj_sevkiyatlar (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        license_code TEXT NOT NULL,
        sevkiyat_no TEXT NOT NULL,
        musteri_id INTEGER,
        musteri_adi TEXT,
        arac_id INTEGER,
        plaka TEXT,
        surucu_id INTEGER,
        surucu_adi TEXT,
        yuklenme_adresi TEXT,
        yuklenme_il TEXT,
        teslimat_adresi TEXT,
        teslimat_il TEXT,
        yuk_cinsi TEXT,
        yuk_miktari REAL,
        yuk_birimi TEXT,
        navlun REAL DEFAULT 0,
        maliyet REAL DEFAULT 0,
        planlanan_yuklenme TEXT,
        planlanan_teslimat TEXT,
        gercek_yuklenme TEXT,
        gercek_teslimat TEXT,
        mesafe_km INTEGER DEFAULT 0,
        durum TEXT DEFAULT 'Planlandı',
        notlar TEXT,
        created_at TEXT
    )''')
    
    # Yakıt Kayıtları
    c.execute('''CREATE TABLE IF NOT EXISTS loj_yakit (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        license_code TEXT NOT NULL,
        arac_id INTEGER NOT NULL,
        plaka TEXT,
        surucu_id INTEGER,
        surucu_adi TEXT,
        tarih TEXT,
        litre REAL,
        birim_fiyat REAL,
        toplam_tutar REAL,
        km_sayaci INTEGER,
        yakit_tipi TEXT,
        istasyon TEXT,
        notlar TEXT,
        created_at TEXT
    )''')
    
    # Araç Bakım Kayıtları
    c.execute('''CREATE TABLE IF NOT EXISTS loj_bakim (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        license_code TEXT NOT NULL,
        arac_id INTEGER NOT NULL,
        plaka TEXT,
        bakim_tipi TEXT,
        bakim_tarihi TEXT,
        sonraki_bakim_km INTEGER,
        sonraki_bakim_tarih TEXT,
        yapilan_isler TEXT,
        tutar REAL DEFAULT 0,
        servis_adi TEXT,
        km_sayaci INTEGER,
        notlar TEXT,
        created_at TEXT
    )''')
    
    # Lojistik Faturaları
    c.execute('''CREATE TABLE IF NOT EXISTS loj_faturalar (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        license_code TEXT NOT NULL,
        fatura_no TEXT NOT NULL,
        fatura_tipi TEXT,
        musteri_id INTEGER,
        musteri_adi TEXT,
        sevkiyat_id INTEGER,
        sevkiyat_no TEXT,
        fatura_tarihi TEXT,
        vade_tarihi TEXT,
        matrah REAL DEFAULT 0,
        kdv_orani INTEGER DEFAULT 18,
        kdv_tutari REAL DEFAULT 0,
        toplam_tutar REAL DEFAULT 0,
        odeme_durumu TEXT DEFAULT 'Ödenmedi',
        notlar TEXT,
        created_at TEXT
    )''')
    
    # Gider Kayıtları
    c.execute('''CREATE TABLE IF NOT EXISTS loj_giderler (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        license_code TEXT NOT NULL,
        gider_tipi TEXT,
        arac_id INTEGER,
        plaka TEXT,
        tarih TEXT,
        tutar REAL DEFAULT 0,
        aciklama TEXT,
        belge_no TEXT,
        created_at TEXT
    )''')
    
    # Lojistik Aktivite Logları
    c.execute('''CREATE TABLE IF NOT EXISTS loj_aktiviteler (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        license_code TEXT NOT NULL,
        user_id INTEGER,
        user_email TEXT,
        aktivite_tipi TEXT,
        aciklama TEXT,
        ilgili_id INTEGER,
        created_at TEXT
    )''')
    
    # ==================== PROTERA SERVİS TABLOLARI ====================
    
    # Servis Kullanıcıları
    c.execute('''CREATE TABLE IF NOT EXISTS servis_users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        license_code TEXT NOT NULL,
        email TEXT NOT NULL,
        password TEXT NOT NULL,
        ad_soyad TEXT,
        telefon TEXT,
        role TEXT DEFAULT 'Kullanıcı',
        yetkiler TEXT DEFAULT '[]',
        durum TEXT DEFAULT 'Aktif',
        created_at TEXT
    )''')
    
    # Servis Müşterileri
    c.execute('''CREATE TABLE IF NOT EXISTS servis_musteriler (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        license_code TEXT NOT NULL,
        musteri_kodu TEXT,
        musteri_tipi TEXT DEFAULT 'Bireysel',
        ad_soyad TEXT,
        firma_adi TEXT,
        telefon TEXT,
        telefon2 TEXT,
        email TEXT,
        adres TEXT,
        il TEXT,
        ilce TEXT,
        vergi_no TEXT,
        vergi_dairesi TEXT,
        notlar TEXT,
        created_at TEXT
    )''')
    
    # Servis Cihazları/Ürünler (Müşteriye Ait)
    c.execute('''CREATE TABLE IF NOT EXISTS servis_cihazlar (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        license_code TEXT NOT NULL,
        musteri_id INTEGER NOT NULL,
        cihaz_tipi TEXT,
        marka TEXT,
        model TEXT,
        seri_no TEXT,
        garanti_bitis TEXT,
        kurulum_tarihi TEXT,
        adres TEXT,
        notlar TEXT,
        created_at TEXT
    )''')
    
    # Servis Teknisyenleri
    c.execute('''CREATE TABLE IF NOT EXISTS servis_teknisyenler (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        license_code TEXT NOT NULL,
        ad_soyad TEXT NOT NULL,
        telefon TEXT,
        email TEXT,
        uzmanlik_alani TEXT,
        bolge TEXT,
        maas REAL DEFAULT 0,
        ise_giris TEXT,
        durum TEXT DEFAULT 'Aktif',
        notlar TEXT,
        created_at TEXT
    )''')
    
    # Arıza/Servis Kayıtları (İş Emirleri)
    c.execute('''CREATE TABLE IF NOT EXISTS servis_arizalar (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        license_code TEXT NOT NULL,
        ariza_no TEXT NOT NULL,
        musteri_id INTEGER,
        musteri_adi TEXT,
        musteri_telefon TEXT,
        cihaz_id INTEGER,
        cihaz_bilgisi TEXT,
        ariza_tipi TEXT,
        ariza_tanimi TEXT,
        oncelik TEXT DEFAULT 'Normal',
        teknisyen_id INTEGER,
        teknisyen_adi TEXT,
        randevu_tarihi TEXT,
        randevu_saati TEXT,
        baslama_tarihi TEXT,
        bitis_tarihi TEXT,
        yapilan_islem TEXT,
        durum TEXT DEFAULT 'Beklemede',
        iscilik_tutari REAL DEFAULT 0,
        parca_tutari REAL DEFAULT 0,
        toplam_tutar REAL DEFAULT 0,
        garanti_kapsaminda INTEGER DEFAULT 0,
        musteri_notu TEXT,
        teknisyen_notu TEXT,
        created_at TEXT
    )''')
    
    # Parça Kategorileri (Firma bazlı özel kategoriler)
    c.execute('''CREATE TABLE IF NOT EXISTS servis_parca_kategoriler (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        license_code TEXT NOT NULL,
        kategori_adi TEXT NOT NULL,
        varsayilan INTEGER DEFAULT 0,
        created_at TEXT
    )''')
    
    # Yedek Parça Stoku
    c.execute('''CREATE TABLE IF NOT EXISTS servis_parcalar (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        license_code TEXT NOT NULL,
        parca_kodu TEXT,
        parca_adi TEXT NOT NULL,
        kategori TEXT,
        marka TEXT,
        uyumlu_modeller TEXT,
        birim TEXT DEFAULT 'Adet',
        stok_miktari REAL DEFAULT 0,
        min_stok REAL DEFAULT 0,
        alis_fiyati REAL DEFAULT 0,
        satis_fiyati REAL DEFAULT 0,
        raf_konum TEXT,
        notlar TEXT,
        created_at TEXT
    )''')
    
    # Parça Kullanım Kayıtları
    c.execute('''CREATE TABLE IF NOT EXISTS servis_parca_kullanim (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        license_code TEXT NOT NULL,
        ariza_id INTEGER NOT NULL,
        parca_id INTEGER NOT NULL,
        parca_adi TEXT,
        miktar REAL DEFAULT 1,
        birim_fiyat REAL DEFAULT 0,
        toplam_tutar REAL DEFAULT 0,
        created_at TEXT
    )''')
    
    # Servis Faturaları
    c.execute('''CREATE TABLE IF NOT EXISTS servis_faturalar (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        license_code TEXT NOT NULL,
        fatura_no TEXT NOT NULL,
        ariza_id INTEGER,
        ariza_no TEXT,
        musteri_id INTEGER,
        musteri_adi TEXT,
        fatura_tarihi TEXT,
        vade_tarihi TEXT,
        iscilik_tutari REAL DEFAULT 0,
        parca_tutari REAL DEFAULT 0,
        matrah REAL DEFAULT 0,
        kdv_orani INTEGER DEFAULT 20,
        kdv_tutari REAL DEFAULT 0,
        toplam_tutar REAL DEFAULT 0,
        odeme_durumu TEXT DEFAULT 'Ödenmedi',
        notlar TEXT,
        created_at TEXT
    )''')
    
    # Servis Aktivite Logları
    c.execute('''CREATE TABLE IF NOT EXISTS servis_aktiviteler (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        license_code TEXT NOT NULL,
        user_id INTEGER,
        user_email TEXT,
        aktivite_tipi TEXT,
        aciklama TEXT,
        ilgili_id INTEGER,
        created_at TEXT
    )''')
    
    c.execute("SELECT * FROM licenses WHERE license_code = 'DEMO-2024'")
    if not c.fetchone():
        now = datetime.now().isoformat()
        c.execute("INSERT INTO licenses (license_code, company_name, created_at) VALUES (?, ?, ?)",
                  ('DEMO-2024', 'Demo Şirket A.Ş.', now))
        c.execute("INSERT INTO users (license_code, email, password, role, yetkiler, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                  ('DEMO-2024', 'admin@demo.com', '123456', 'Yönetim', '[]', now))
        c.execute("INSERT INTO users (license_code, email, password, role, yetkiler, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                  ('DEMO-2024', 'satinalma@demo.com', '123456', 'Satınalma', '[]', now))
        c.execute("INSERT INTO users (license_code, email, password, role, yetkiler, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                  ('DEMO-2024', 'kullanici@demo.com', '123456', 'Kullanıcı', '[]', now))
        
        c.execute("INSERT INTO products (license_code, urun_kodu, urun_adi, birim, stok_miktari, minimum_stok, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                  ('DEMO-2024', 'URN-001', 'Çimento 42.5', 'Ton', 50, 20, now))
        c.execute("INSERT INTO products (license_code, urun_kodu, urun_adi, birim, stok_miktari, minimum_stok, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                  ('DEMO-2024', 'URN-002', 'Demir 12mm', 'Ton', 30, 15, now))
        c.execute("INSERT INTO products (license_code, urun_kodu, urun_adi, birim, stok_miktari, minimum_stok, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                  ('DEMO-2024', 'URN-003', 'Kum', 'm³', 100, 50, now))
        c.execute("INSERT INTO products (license_code, urun_kodu, urun_adi, birim, stok_miktari, minimum_stok, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                  ('DEMO-2024', 'URN-004', 'Tuğla', 'Adet', 5000, 1000, now))
        
        c.execute("INSERT INTO suppliers (license_code, tedarikci_adi, tedarikci_email, tedarikci_telefon, created_at) VALUES (?, ?, ?, ?, ?)",
                  ('DEMO-2024', 'ABC Yapı Malzemeleri', 'info@abcyapi.com', '0212 555 0101', now))
        c.execute("INSERT INTO suppliers (license_code, tedarikci_adi, tedarikci_email, tedarikci_telefon, created_at) VALUES (?, ?, ?, ?, ?)",
                  ('DEMO-2024', 'XYZ İnşaat Tic.', 'satis@xyz.com', '0216 444 0202', now))
        
        c.execute("INSERT INTO projects (license_code, proje_kodu, proje_adi, lokasyon, durum, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                  ('DEMO-2024', 'PRJ-0001', 'Merkez Ofis İnşaatı', 'İstanbul/Kadıköy', 'Aktif', now))
        
        c.execute("INSERT INTO project_statuses (license_code, durum_adi, sira, created_at) VALUES (?, ?, ?, ?)",
                  ('DEMO-2024', 'Aktif', 1, now))
        c.execute("INSERT INTO project_statuses (license_code, durum_adi, sira, created_at) VALUES (?, ?, ?, ?)",
                  ('DEMO-2024', 'Planlama', 2, now))
        c.execute("INSERT INTO project_statuses (license_code, durum_adi, sira, created_at) VALUES (?, ?, ?, ?)",
                  ('DEMO-2024', 'Tamamlandı', 3, now))
        c.execute("INSERT INTO project_statuses (license_code, durum_adi, sira, created_at) VALUES (?, ?, ?, ?)",
                  ('DEMO-2024', 'İptal', 4, now))
    
    c.execute("SELECT * FROM super_admins WHERE email = 'superadmin@sistem.com'")
    if not c.fetchone():
        now = datetime.now().isoformat()
        c.execute("INSERT INTO super_admins (email, password, ad_soyad, created_at) VALUES (?, ?, ?, ?)",
                  ('superadmin@sistem.com', 'super123', 'Sistem Yöneticisi', now))
    
    # Ürün Kataloğu - Varsayılan ürünler
    c.execute("SELECT * FROM protera_products WHERE product_code = 'tedarik'")
    if not c.fetchone():
        now = datetime.now().isoformat()
        c.execute('''INSERT INTO protera_products (product_code, product_name, description, monthly_price, is_active, icon, color, created_at) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                  ('tedarik', 'Protera Tedarik', 'Satınalma ve Proje Yönetim Sistemi', 1250, 1, '📦', '#667eea', now))
        c.execute('''INSERT INTO protera_products (product_code, product_name, description, monthly_price, is_active, icon, color, created_at) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                  ('lojistik', 'Protera Lojistik', 'Filo ve Sevkiyat Yönetim Sistemi', 1250, 1, '🚛', '#10b981', now))
        c.execute('''INSERT INTO protera_products (product_code, product_name, description, monthly_price, is_active, icon, color, created_at) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                  ('servis', 'Protera Servis', 'Teknik Servis Yönetim Sistemi', 1250, 1, '🔧', '#f59e0b', now))
        c.execute('''INSERT INTO protera_products (product_code, product_name, description, monthly_price, is_active, icon, color, created_at) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                  ('depo', 'Protera Depo', 'Depo Yönetim Sistemi', 1250, 0, '🏭', '#8b5cf6', now))
        c.execute('''INSERT INTO protera_products (product_code, product_name, description, monthly_price, is_active, icon, color, created_at) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                  ('insaat', 'Protera İnşaat', 'Şantiye Yönetim Sistemi', 1250, 0, '🏗️', '#ef4444', now))
    
    # Mevcut lisanslar için ürün atamaları yap
    c.execute("SELECT COUNT(*) FROM license_products")
    if c.fetchone()[0] == 0:
        c.execute("SELECT id FROM licenses")
        licenses = c.fetchall()
        c.execute("SELECT id, product_code FROM protera_products WHERE is_active = 1")
        active_products = c.fetchall()
        now = datetime.now().isoformat()
        for lic in licenses:
            for prod in active_products:
                c.execute('''INSERT INTO license_products (license_id, product_id, is_active, activated_at, created_at) 
                            VALUES (?, ?, 1, ?, ?)''', (lic['id'], prod['id'], now, now))
    
    # Lojistik Demo Verileri
    c.execute("SELECT * FROM loj_users WHERE email = 'lojistik@demo.com'")
    if not c.fetchone():
        now = datetime.now().isoformat()
        
        # Demo Lojistik Kullanıcıları
        c.execute("INSERT INTO loj_users (license_code, email, password, ad_soyad, role, yetkiler, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                  ('DEMO-2024', 'lojistik@demo.com', '123456', 'Lojistik Admin', 'Yönetim', '[]', now))
        c.execute("INSERT INTO loj_users (license_code, email, password, ad_soyad, role, yetkiler, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                  ('DEMO-2024', 'operasyon@demo.com', '123456', 'Operasyon Sorumlusu', 'Operasyon', '[]', now))
        
        # Demo Araçlar
        c.execute('''INSERT INTO loj_araclar (license_code, plaka, marka, model, yil, arac_tipi, kapasite_ton, yakit_tipi, 
                    sigorta_bitis, muayene_bitis, km_sayaci, durum, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  ('DEMO-2024', '34 ABC 123', 'Mercedes', 'Actros 1844', 2021, 'Tır', 25, 'Dizel', '2025-06-15', '2025-03-20', 185000, 'Aktif', now))
        c.execute('''INSERT INTO loj_araclar (license_code, plaka, marka, model, yil, arac_tipi, kapasite_ton, yakit_tipi, 
                    sigorta_bitis, muayene_bitis, km_sayaci, durum, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  ('DEMO-2024', '34 DEF 456', 'Volvo', 'FH16 750', 2022, 'Tır', 28, 'Dizel', '2025-08-10', '2025-05-15', 120000, 'Aktif', now))
        c.execute('''INSERT INTO loj_araclar (license_code, plaka, marka, model, yil, arac_tipi, kapasite_ton, yakit_tipi, 
                    sigorta_bitis, muayene_bitis, km_sayaci, durum, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  ('DEMO-2024', '34 GHI 789', 'Ford', 'Cargo 1833', 2020, 'Kamyon', 18, 'Dizel', '2025-04-25', '2025-02-10', 210000, 'Aktif', now))
        c.execute('''INSERT INTO loj_araclar (license_code, plaka, marka, model, yil, arac_tipi, kapasite_ton, yakit_tipi, 
                    sigorta_bitis, muayene_bitis, km_sayaci, durum, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  ('DEMO-2024', '06 JKL 012', 'Scania', 'R500', 2023, 'Tır', 30, 'Dizel', '2025-12-01', '2025-09-30', 45000, 'Aktif', now))
        
        # Demo Sürücüler
        c.execute('''INSERT INTO loj_suruculer (license_code, ad_soyad, tc_no, telefon, ehliyet_sinifi, ehliyet_bitis, 
                    src_belgesi, src_bitis, maas, ise_giris, durum, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  ('DEMO-2024', 'Ahmet Yılmaz', '12345678901', '0532 111 2233', 'E', '2027-05-15', 'SRC1', '2026-03-20', 45000, '2020-03-01', 'Aktif', now))
        c.execute('''INSERT INTO loj_suruculer (license_code, ad_soyad, tc_no, telefon, ehliyet_sinifi, ehliyet_bitis, 
                    src_belgesi, src_bitis, maas, ise_giris, durum, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  ('DEMO-2024', 'Mehmet Kaya', '23456789012', '0533 222 3344', 'E', '2026-08-10', 'SRC1', '2025-11-15', 42000, '2019-06-15', 'Aktif', now))
        c.execute('''INSERT INTO loj_suruculer (license_code, ad_soyad, tc_no, telefon, ehliyet_sinifi, ehliyet_bitis, 
                    src_belgesi, src_bitis, maas, ise_giris, durum, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  ('DEMO-2024', 'Ali Demir', '34567890123', '0534 333 4455', 'E', '2028-02-28', 'SRC1', '2026-07-10', 48000, '2021-01-10', 'Aktif', now))
        c.execute('''INSERT INTO loj_suruculer (license_code, ad_soyad, tc_no, telefon, ehliyet_sinifi, ehliyet_bitis, 
                    src_belgesi, src_bitis, maas, ise_giris, durum, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  ('DEMO-2024', 'Hasan Çelik', '45678901234', '0535 444 5566', 'E', '2025-11-20', 'SRC1', '2025-09-05', 40000, '2022-04-01', 'Aktif', now))
        
        # Demo Müşteriler
        c.execute('''INSERT INTO loj_musteriler (license_code, musteri_kodu, firma_adi, yetkili_kisi, telefon, email, 
                    adres, vergi_no, vergi_dairesi, odeme_vadesi, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  ('DEMO-2024', 'MUS-001', 'ABC Gıda San. Tic. A.Ş.', 'Mustafa Özkan', '0212 555 1122', 'info@abcgida.com', 
                   'Organize Sanayi Bölgesi 5. Cadde No:12 Gebze/Kocaeli', '1234567890', 'Gebze', 30, now))
        c.execute('''INSERT INTO loj_musteriler (license_code, musteri_kodu, firma_adi, yetkili_kisi, telefon, email, 
                    adres, vergi_no, vergi_dairesi, odeme_vadesi, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  ('DEMO-2024', 'MUS-002', 'XYZ Tekstil Ltd. Şti.', 'Ayşe Yıldız', '0216 444 3344', 'satis@xyztekstil.com', 
                   'Merter Tekstil Merkezi A Blok Kat:3 Güngören/İstanbul', '9876543210', 'Merter', 45, now))
        c.execute('''INSERT INTO loj_musteriler (license_code, musteri_kodu, firma_adi, yetkili_kisi, telefon, email, 
                    adres, vergi_no, vergi_dairesi, odeme_vadesi, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  ('DEMO-2024', 'MUS-003', 'Mega İnşaat Malzemeleri', 'Kemal Arslan', '0312 333 5566', 'mega@megainsaat.com', 
                   'Sanayi Sitesi 2. Blok No:45 Ostim/Ankara', '5678901234', 'Ostim', 60, now))
        
        # Demo Sevkiyatlar
        c.execute('''INSERT INTO loj_sevkiyatlar (license_code, sevkiyat_no, musteri_id, musteri_adi, arac_id, plaka, 
                    surucu_id, surucu_adi, yuklenme_adresi, yuklenme_il, teslimat_adresi, teslimat_il, yuk_cinsi, 
                    yuk_miktari, yuk_birimi, navlun, planlanan_yuklenme, planlanan_teslimat, durum, created_at) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  ('DEMO-2024', 'SVK-00001', 1, 'ABC Gıda San. Tic. A.Ş.', 1, '34 ABC 123', 1, 'Ahmet Yılmaz',
                   'Ambarlı Liman, Avcılar/İstanbul', 'İstanbul', 'OSB 5. Cadde No:12 Gebze/Kocaeli', 'Kocaeli',
                   'Gıda Ürünleri', 22, 'Ton', 8500, '2024-11-28 08:00', '2024-11-28 14:00', 'Yolda', now))
        c.execute('''INSERT INTO loj_sevkiyatlar (license_code, sevkiyat_no, musteri_id, musteri_adi, arac_id, plaka, 
                    surucu_id, surucu_adi, yuklenme_adresi, yuklenme_il, teslimat_adresi, teslimat_il, yuk_cinsi, 
                    yuk_miktari, yuk_birimi, navlun, planlanan_yuklenme, planlanan_teslimat, durum, created_at) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  ('DEMO-2024', 'SVK-00002', 2, 'XYZ Tekstil Ltd. Şti.', 2, '34 DEF 456', 2, 'Mehmet Kaya',
                   'Merter Tekstil Merkezi, İstanbul', 'İstanbul', 'Antalya Serbest Bölge', 'Antalya',
                   'Tekstil Ürünleri', 18, 'Ton', 15000, '2024-11-29 06:00', '2024-11-29 18:00', 'Planlandı', now))
        c.execute('''INSERT INTO loj_sevkiyatlar (license_code, sevkiyat_no, musteri_id, musteri_adi, arac_id, plaka, 
                    surucu_id, surucu_adi, yuklenme_adresi, yuklenme_il, teslimat_adresi, teslimat_il, yuk_cinsi, 
                    yuk_miktari, yuk_birimi, navlun, planlanan_yuklenme, planlanan_teslimat, gercek_teslimat, durum, created_at) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  ('DEMO-2024', 'SVK-00003', 3, 'Mega İnşaat Malzemeleri', 3, '34 GHI 789', 3, 'Ali Demir',
                   'İstanbul Çimento Fabrikası', 'İstanbul', 'Ostim Sanayi No:45, Ankara', 'Ankara',
                   'Çimento', 15, 'Ton', 12000, '2024-11-27 07:00', '2024-11-27 19:00', '2024-11-27 18:30', 'Teslim Edildi', now))
    
    # Servis Demo Verileri
    c.execute("SELECT * FROM servis_users WHERE email = 'servis@demo.com'")
    if not c.fetchone():
        now = datetime.now().isoformat()
        
        # Demo Servis Kullanıcıları
        c.execute("INSERT INTO servis_users (license_code, email, password, ad_soyad, telefon, role, durum, yetkiler, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                  ('DEMO-2024', 'servis@demo.com', '123456', 'Servis Yöneticisi', '0532 100 0001', 'Yönetim', 'Aktif', '[]', now))
        c.execute("INSERT INTO servis_users (license_code, email, password, ad_soyad, telefon, role, durum, yetkiler, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                  ('DEMO-2024', 'teknisyen@demo.com', '123456', 'Demo Teknisyen', '0532 100 0002', 'Teknisyen', 'Aktif', '[]', now))
        
        # Demo Müşteriler
        c.execute('''INSERT INTO servis_musteriler (license_code, musteri_kodu, musteri_tipi, ad_soyad, firma_adi, 
                    telefon, email, adres, il, ilce, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  ('DEMO-2024', 'MUS-0001', 'Bireysel', 'Ahmet Yılmaz', '', '0532 111 2233', 'ahmet@email.com', 
                   'Atatürk Cad. No:25 D:4', 'İstanbul', 'Kadıköy', now))
        c.execute('''INSERT INTO servis_musteriler (license_code, musteri_kodu, musteri_tipi, ad_soyad, firma_adi, 
                    telefon, email, adres, il, ilce, vergi_no, vergi_dairesi, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  ('DEMO-2024', 'MUS-0002', 'Kurumsal', '', 'ABC Plaza Yönetimi', '0216 444 5566', 'info@abcplaza.com', 
                   'İş Merkezi Blv. No:100', 'İstanbul', 'Ümraniye', '1234567890', 'Ümraniye', now))
        c.execute('''INSERT INTO servis_musteriler (license_code, musteri_kodu, musteri_tipi, ad_soyad, firma_adi, 
                    telefon, email, adres, il, ilce, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  ('DEMO-2024', 'MUS-0003', 'Bireysel', 'Fatma Demir', '', '0533 222 3344', 'fatma.demir@email.com', 
                   'Bahçe Sok. No:15', 'İstanbul', 'Beşiktaş', now))
        
        # Demo Teknisyenler
        c.execute('''INSERT INTO servis_teknisyenler (license_code, ad_soyad, telefon, email, uzmanlik_alani, 
                    bolge, maas, ise_giris, durum, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  ('DEMO-2024', 'Mehmet Usta', '0534 111 0001', 'mehmet@servis.com', 'Klima, Kombi', 
                   'Kadıköy, Üsküdar', 35000, '2022-03-15', 'Aktif', now))
        c.execute('''INSERT INTO servis_teknisyenler (license_code, ad_soyad, telefon, email, uzmanlik_alani, 
                    bolge, maas, ise_giris, durum, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  ('DEMO-2024', 'Ali Tekniker', '0535 222 0002', 'ali@servis.com', 'Beyaz Eşya', 
                   'Beşiktaş, Şişli', 32000, '2023-01-10', 'Aktif', now))
        c.execute('''INSERT INTO servis_teknisyenler (license_code, ad_soyad, telefon, email, uzmanlik_alani, 
                    bolge, maas, ise_giris, durum, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  ('DEMO-2024', 'Hasan Elektrik', '0536 333 0003', 'hasan@servis.com', 'Asansör, Elektrik', 
                   'Ümraniye, Ataşehir', 38000, '2021-06-20', 'Aktif', now))
        
        # Demo Cihazlar
        c.execute('''INSERT INTO servis_cihazlar (license_code, musteri_id, cihaz_tipi, marka, model, seri_no, 
                    garanti_bitis, kurulum_tarihi, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  ('DEMO-2024', 1, 'Klima', 'Samsung', 'AR12TXHQASINEU', 'SM2024001122', '2026-06-15', '2024-06-15', now))
        c.execute('''INSERT INTO servis_cihazlar (license_code, musteri_id, cihaz_tipi, marka, model, seri_no, 
                    garanti_bitis, kurulum_tarihi, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  ('DEMO-2024', 2, 'Klima', 'Daikin', 'FTXM35R', 'DK2023005566', '2025-08-20', '2023-08-20', now))
        c.execute('''INSERT INTO servis_cihazlar (license_code, musteri_id, cihaz_tipi, marka, model, seri_no, 
                    garanti_bitis, kurulum_tarihi, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  ('DEMO-2024', 2, 'Asansör', 'Kone', 'MonoSpace 500', 'KN2020007788', '2025-03-10', '2020-03-10', now))
        c.execute('''INSERT INTO servis_cihazlar (license_code, musteri_id, cihaz_tipi, marka, model, seri_no, 
                    garanti_bitis, kurulum_tarihi, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  ('DEMO-2024', 3, 'Kombi', 'Baymak', 'Eco Four 24', 'BM2022003344', '2024-11-01', '2022-11-01', now))
        c.execute('''INSERT INTO servis_cihazlar (license_code, musteri_id, cihaz_tipi, marka, model, seri_no, 
                    garanti_bitis, kurulum_tarihi, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  ('DEMO-2024', 3, 'Buzdolabı', 'Arçelik', '5088 NFEY', 'AR2023009900', '2025-04-15', '2023-04-15', now))
        
        # Demo Parçalar
        c.execute('''INSERT INTO servis_parcalar (license_code, parca_kodu, parca_adi, kategori, marka, 
                    stok_miktari, min_stok, alis_fiyati, satis_fiyati, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  ('DEMO-2024', 'PRC-0001', 'Klima Kompresör', 'Kompresör', 'Samsung', 5, 2, 2500, 3500, now))
        c.execute('''INSERT INTO servis_parcalar (license_code, parca_kodu, parca_adi, kategori, marka, 
                    stok_miktari, min_stok, alis_fiyati, satis_fiyati, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  ('DEMO-2024', 'PRC-0002', 'Fan Motoru', 'Fan Motoru', 'Genel', 12, 5, 350, 550, now))
        c.execute('''INSERT INTO servis_parcalar (license_code, parca_kodu, parca_adi, kategori, marka, 
                    stok_miktari, min_stok, alis_fiyati, satis_fiyati, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  ('DEMO-2024', 'PRC-0003', 'Klima Kartı', 'Kart', 'Daikin', 3, 2, 1200, 1800, now))
        c.execute('''INSERT INTO servis_parcalar (license_code, parca_kodu, parca_adi, kategori, marka, 
                    stok_miktari, min_stok, alis_fiyati, satis_fiyati, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  ('DEMO-2024', 'PRC-0004', 'Kombi Pompa', 'Pompa', 'Baymak', 8, 3, 800, 1200, now))
        c.execute('''INSERT INTO servis_parcalar (license_code, parca_kodu, parca_adi, kategori, marka, 
                    stok_miktari, min_stok, alis_fiyati, satis_fiyati, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  ('DEMO-2024', 'PRC-0005', 'Termostat Sensör', 'Sensör', 'Genel', 20, 10, 75, 150, now))
        c.execute('''INSERT INTO servis_parcalar (license_code, parca_kodu, parca_adi, kategori, marka, 
                    stok_miktari, min_stok, alis_fiyati, satis_fiyati, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  ('DEMO-2024', 'PRC-0006', 'Klima Filtresi', 'Filtre', 'Genel', 50, 20, 25, 75, now))
        
        # Demo Arızalar/İş Emirleri
        c.execute('''INSERT INTO servis_arizalar (license_code, ariza_no, musteri_id, musteri_adi, cihaz_id, cihaz_bilgisi,
                    ariza_tipi, ariza_tanimi, oncelik, teknisyen_id, teknisyen_adi, randevu_tarihi, randevu_saati, durum, created_at) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  ('DEMO-2024', 'SRV-202411-0001', 1, 'Ahmet Yılmaz', 1, 'Klima - Samsung AR12TXHQASINEU',
                   'Soğutmuyor', 'Klima çalışıyor ama soğutmuyor, kompresör sesi normal', 'Normal', 
                   1, 'Mehmet Usta', '2024-11-29', '10:00', 'Atandı', now))
        c.execute('''INSERT INTO servis_arizalar (license_code, ariza_no, musteri_id, musteri_adi, cihaz_id, cihaz_bilgisi,
                    ariza_tipi, ariza_tanimi, oncelik, durum, created_at) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  ('DEMO-2024', 'SRV-202411-0002', 2, 'ABC Plaza Yönetimi', 3, 'Asansör - Kone MonoSpace 500',
                   'Çalışmıyor', 'Asansör 3. katta takılı kaldı, acil müdahale gerekiyor', 'Acil', 'Beklemede', now))
        c.execute('''INSERT INTO servis_arizalar (license_code, ariza_no, musteri_id, musteri_adi, cihaz_id, cihaz_bilgisi,
                    ariza_tipi, ariza_tanimi, oncelik, teknisyen_id, teknisyen_adi, randevu_tarihi, durum, created_at) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  ('DEMO-2024', 'SRV-202411-0003', 3, 'Fatma Demir', 4, 'Kombi - Baymak Eco Four 24',
                   'Hata Kodu', 'E01 hata kodu veriyor, ısıtmıyor', 'Yüksek', 
                   1, 'Mehmet Usta', '2024-11-28', 'İşlemde', now))

    conn.commit()
    conn.close()

@app.route('/')
def landing():
    return send_from_directory('.', 'landing.html')

@app.route('/hakkimizda')
def hakkimizda():
    return send_from_directory('.', 'hakkimizda.html')

@app.route('/giris')
def giris():
    return send_from_directory('.', 'index.html')

@app.route('/superadmin')
def superadmin_page():
    return send_from_directory('.', 'index.html')

@app.route('/lojistik')
def lojistik_giris():
    return send_from_directory('.', 'lojistik.html')

@app.route('/lojistik/')
def lojistik_giris_slash():
    return send_from_directory('.', 'lojistik.html')

@app.route('/tedarik-login')
def tedarik_login():
    return send_from_directory('.', 'index.html')

@app.route('/lojistik-login')
def lojistik_login():
    return send_from_directory('.', 'lojistik.html')

@app.route('/servis-login')
def servis_login():
    return send_from_directory('.', 'servis.html')

@app.route('/api/licenses/<license_code>')
def get_license_info(license_code):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM licenses WHERE license_code = ?", (license_code,))
    lic = c.fetchone()
    conn.close()
    
    if not lic:
        return jsonify({'success': False, 'message': 'Lisans bulunamadı'})
    
    lic_dict = dict(lic)
    lic_dict['aktif'] = lic_dict.get('is_active', 1) == 1
    return jsonify(lic_dict)

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email', '').strip()
    password = data.get('password', '').strip()
    
    conn = get_db()
    c = conn.cursor()
    
    c.execute("SELECT * FROM users WHERE email = ? AND password = ?", (email, password))
    user = c.fetchone()
    
    if not user:
        conn.close()
        return jsonify({'success': False, 'message': 'Geçersiz e-posta veya şifre!'})
    
    license_code = user['license_code']
    
    c.execute("SELECT * FROM licenses WHERE license_code = ?", (license_code,))
    license_row = c.fetchone()
    conn.close()
    
    if not license_row:
        return jsonify({'success': False, 'message': 'Lisans bulunamadı! Lütfen yöneticinize başvurun.'})
    
    license_aktif = license_row['is_active'] == 1
    license_suresi_doldu = False
    kalan_gun = None
    
    if license_row['bitis_tarihi']:
        try:
            bitis = datetime.strptime(license_row['bitis_tarihi'], '%Y-%m-%d')
            bugun = datetime.now()
            kalan = (bitis - bugun).days
            kalan_gun = kalan
            if kalan < 0:
                license_suresi_doldu = True
        except:
            pass
    
    if license_suresi_doldu:
        return jsonify({'success': False, 'message': 'Lisans süreniz dolmuştur! Lütfen lisansınızı yenileyin.'})
    
    conn2 = get_db()
    c2 = conn2.cursor()
    now = datetime.now().isoformat()
    c2.execute('''INSERT INTO user_activities (license_code, user_id, user_email, activity_type, activity_description, created_at)
                VALUES (?, ?, ?, ?, ?, ?)''',
              (license_code, user['id'], user['email'], 'login', 'Sisteme giriş yaptı', now))
    conn2.commit()
    conn2.close()
    
    return jsonify({
        'success': True,
        'user': {
            'id': user['id'],
            'license_code': user['license_code'],
            'email': user['email'],
            'role': user['role'],
            'yetkiler': user['yetkiler'],
            'company_name': license_row['company_name'] if license_row else 'Şirket'
        },
        'license_info': {
            'aktif': license_aktif,
            'paket': license_row['paket_tipi'] if license_row else None,
            'bitis_tarihi': license_row['bitis_tarihi'] if license_row else None,
            'kalan_gun': kalan_gun
        }
    })

@app.route('/api/projects', methods=['GET', 'POST'])
def projects():
    license_code = request.args.get('license_code') or request.json.get('license_code')
    conn = get_db()
    c = conn.cursor()
    
    if request.method == 'GET':
        c.execute("SELECT * FROM projects WHERE license_code = ? ORDER BY id DESC", (license_code,))
        rows = c.fetchall()
        conn.close()
        return jsonify([dict(row) for row in rows])
    
    data = request.json
    now = datetime.now().isoformat()
    c.execute("SELECT COUNT(*) FROM projects WHERE license_code = ?", (license_code,))
    count = c.fetchone()[0] + 1
    proje_kodu = f"PRJ-{str(count).zfill(4)}"
    
    c.execute('''INSERT INTO projects (license_code, proje_kodu, proje_adi, santiye_sefi, lokasyon, 
                baslangic_tarihi, bitis_tarihi, butce, durum, aciklama, created_at) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
              (license_code, proje_kodu, data.get('proje_adi'), data.get('santiye_sefi'),
               data.get('lokasyon'), data.get('baslangic_tarihi'), data.get('bitis_tarihi'),
               data.get('butce', 0), data.get('durum', 'Aktif'), data.get('aciklama'), now))
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'proje_kodu': proje_kodu})

@app.route('/api/projects/<int:id>', methods=['DELETE'])
def delete_project(id):
    license_code = request.args.get('license_code')
    if not license_code:
        return jsonify({'success': False, 'message': 'Lisans kodu gerekli!'})
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM projects WHERE id = ? AND license_code = ?", (id, license_code))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/products', methods=['GET', 'POST'])
def products():
    license_code = request.args.get('license_code') or (request.json.get('license_code') if request.json else None)
    conn = get_db()
    c = conn.cursor()
    
    if request.method == 'GET':
        c.execute("SELECT * FROM products WHERE license_code = ? ORDER BY id DESC", (license_code,))
        rows = c.fetchall()
        conn.close()
        return jsonify([dict(row) for row in rows])
    
    data = request.json
    now = datetime.now().isoformat()
    c.execute('''INSERT INTO products (license_code, urun_kodu, urun_adi, birim, stok_miktari, minimum_stok, ana_kategori, alt_kategori, alt_kategori_2, created_at) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
              (license_code, data.get('urun_kodu'), data.get('urun_adi'), data.get('birim'),
               data.get('stok_miktari', 0), data.get('minimum_stok', 0), 
               data.get('ana_kategori', ''), data.get('alt_kategori', ''), data.get('alt_kategori_2', ''), now))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/products/<int:id>', methods=['PUT', 'DELETE'])
def update_product(id):
    conn = get_db()
    c = conn.cursor()
    
    if request.method == 'DELETE':
        c.execute("DELETE FROM products WHERE id = ?", (id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    
    data = request.json
    c.execute("UPDATE products SET stok_miktari = ? WHERE id = ?", (data.get('stok_miktari'), id))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/suppliers', methods=['GET', 'POST'])
def suppliers():
    license_code = request.args.get('license_code') or (request.json.get('license_code') if request.json else None)
    conn = get_db()
    c = conn.cursor()
    
    if request.method == 'GET':
        c.execute("SELECT * FROM suppliers WHERE license_code = ? ORDER BY id DESC", (license_code,))
        rows = c.fetchall()
        conn.close()
        return jsonify([dict(row) for row in rows])
    
    data = request.json
    now = datetime.now().isoformat()
    c.execute('''INSERT INTO suppliers (license_code, tedarikci_adi, tedarikci_email, tedarikci_telefon, tedarikci_adres, created_at) 
                VALUES (?, ?, ?, ?, ?, ?)''',
              (license_code, data.get('tedarikci_adi'), data.get('tedarikci_email'),
               data.get('tedarikci_telefon'), data.get('tedarikci_adres'), now))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/suppliers/<int:id>', methods=['DELETE'])
def delete_supplier(id):
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM suppliers WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/requests', methods=['GET', 'POST'])
def requests_api():
    license_code = request.args.get('license_code') or (request.json.get('license_code') if request.json else None)
    conn = get_db()
    c = conn.cursor()
    
    if request.method == 'GET':
        c.execute("SELECT * FROM requests WHERE license_code = ? ORDER BY id DESC", (license_code,))
        rows = c.fetchall()
        result = []
        for row in rows:
            r = dict(row)
            c.execute("SELECT * FROM request_items WHERE talep_id = ?", (row['id'],))
            r['items'] = [dict(item) for item in c.fetchall()]
            result.append(r)
        conn.close()
        return jsonify(result)
    
    data = request.json
    now = datetime.now().isoformat()
    c.execute("SELECT COUNT(*) FROM requests WHERE license_code = ?", (license_code,))
    count = c.fetchone()[0] + 1
    talep_no = f"TLP-{str(count).zfill(5)}"
    
    c.execute('''INSERT INTO requests (license_code, talep_no, proje_id, talep_eden, departman, aciliyet, aciklama, durum, created_at) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
              (license_code, talep_no, data.get('proje_id'), data.get('talep_eden'),
               data.get('departman'), data.get('aciliyet', 'Normal'), data.get('aciklama'), 'Beklemede', now))
    talep_id = c.lastrowid
    
    for item in data.get('items', []):
        c.execute('''INSERT INTO request_items (license_code, talep_id, urun_id, urun_kodu, urun_adi, miktar, birim, beklenen_teslim, aciklama, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  (license_code, talep_id, item.get('urun_id'), item.get('urun_kodu'), item.get('urun_adi'),
                   item.get('miktar'), item.get('birim'), item.get('beklenen_teslim'), item.get('aciklama'), now))
    
    if data.get('user_id') and data.get('user_email'):
        c.execute('''INSERT INTO user_activities (license_code, user_id, user_email, activity_type, activity_description, related_id, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)''',
                  (license_code, data.get('user_id'), data.get('user_email'), 'request_create', f'Talep oluşturdu: {talep_no}', talep_id, now))
    
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'talep_no': talep_no})

@app.route('/api/requests/<int:id>', methods=['PUT', 'DELETE'])
def update_request(id):
    conn = get_db()
    c = conn.cursor()
    
    if request.method == 'DELETE':
        c.execute("DELETE FROM request_items WHERE talep_id = ?", (id,))
        c.execute("DELETE FROM requests WHERE id = ?", (id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    
    data = request.json
    c.execute("UPDATE requests SET durum = ? WHERE id = ?", (data.get('durum'), id))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/offers', methods=['GET', 'POST'])
def offers():
    license_code = request.args.get('license_code') or (request.json.get('license_code') if request.json else None)
    conn = get_db()
    c = conn.cursor()
    
    if request.method == 'GET':
        c.execute("SELECT * FROM offers WHERE license_code = ? ORDER BY id DESC", (license_code,))
        rows = c.fetchall()
        conn.close()
        return jsonify([dict(row) for row in rows])
    
    data = request.json
    now = datetime.now().isoformat()
    c.execute("SELECT COUNT(*) FROM offers WHERE license_code = ?", (license_code,))
    count = c.fetchone()[0] + 1
    teklif_no = f"TKL-{str(count).zfill(5)}"
    
    c.execute('''INSERT INTO offers (license_code, teklif_no, talep_id, tedarikci_id, tedarikci_adi, birim_fiyat, toplam_fiyat, urun_fiyatlari, odeme_vadesi, teslim_suresi, notlar, onaylandi, created_at) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
              (license_code, teklif_no, data.get('talep_id'), data.get('tedarikci_id'),
               data.get('tedarikci_adi'), data.get('birim_fiyat'), data.get('toplam_fiyat'),
               data.get('urun_fiyatlari'), data.get('odeme_vadesi'), data.get('teslim_suresi'), 
               data.get('notlar'), 0, now))
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'teklif_no': teklif_no})

@app.route('/api/offers/<int:id>/approve', methods=['PUT'])
def approve_offer(id):
    data = request.json
    license_code = data.get('license_code')
    
    conn = get_db()
    c = conn.cursor()
    
    c.execute("SELECT * FROM offers WHERE id = ? AND license_code = ?", (id, license_code))
    offer = c.fetchone()
    if not offer:
        conn.close()
        return jsonify({'success': False, 'message': 'Teklif bulunamadı veya yetkiniz yok!'})
    
    c.execute("UPDATE offers SET onaylandi = 1 WHERE id = ? AND license_code = ?", (id, license_code))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/orders', methods=['GET', 'POST'])
def orders():
    license_code = request.args.get('license_code') or (request.json.get('license_code') if request.json else None)
    conn = get_db()
    c = conn.cursor()
    
    if request.method == 'GET':
        c.execute("SELECT * FROM orders WHERE license_code = ? ORDER BY id DESC", (license_code,))
        rows = c.fetchall()
        conn.close()
        return jsonify([dict(row) for row in rows])
    
    data = request.json
    now = datetime.now().isoformat()
    c.execute("SELECT COUNT(*) FROM orders WHERE license_code = ?", (license_code,))
    count = c.fetchone()[0] + 1
    siparis_no = f"SIP-{str(count).zfill(5)}"
    
    c.execute('''INSERT INTO orders (license_code, siparis_no, talep_id, talep_no, tedarikci_id, tedarikci_adi, siparis_urunleri, genel_toplam, teslim_tarihi, aciklama, durum, created_at) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
              (license_code, siparis_no, data.get('talep_id'), data.get('talep_no'),
               data.get('tedarikci_id'), data.get('tedarikci_adi'), 
               json.dumps(data.get('siparis_urunleri', [])), data.get('genel_toplam', 0),
               data.get('teslim_tarihi'), data.get('aciklama'), 'Beklemede', now))
    order_id = c.lastrowid
    
    if data.get('user_id') and data.get('user_email'):
        c.execute('''INSERT INTO user_activities (license_code, user_id, user_email, activity_type, activity_description, related_id, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)''',
                  (license_code, data.get('user_id'), data.get('user_email'), 'order_create', f'Sipariş oluşturdu: {siparis_no}', order_id, now))
    
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'siparis_no': siparis_no})

@app.route('/api/orders/<int:id>', methods=['PUT'])
def update_order(id):
    conn = get_db()
    c = conn.cursor()
    data = request.json
    c.execute("UPDATE orders SET durum = ? WHERE id = ?", (data.get('durum'), id))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/orders/<int:id>/teslim', methods=['PUT'])
def teslim_al(id):
    conn = get_db()
    c = conn.cursor()
    data = request.json
    license_code = data.get('license_code')
    teslimler = data.get('teslimler', [])
    has_discrepancy = data.get('has_discrepancy', False)
    discrepancy_msg = data.get('discrepancy_msg', '')
    now = datetime.now().isoformat()
    
    c.execute("SELECT * FROM orders WHERE id = ? AND license_code = ?", (id, license_code))
    order = c.fetchone()
    if not order:
        conn.close()
        return jsonify({'success': False, 'message': 'Sipariş bulunamadı veya yetkiniz yok!'})
    
    for teslim in teslimler:
        urun_id = teslim.get('urun_id')
        teslim_miktar = float(teslim.get('teslim_miktar', 0))
        
        if teslim_miktar > 0:
            c.execute("SELECT * FROM products WHERE id = ?", (urun_id,))
            product = c.fetchone()
            if product:
                current_stock = float(product['stok_miktari'] or 0)
                new_stock = current_stock + teslim_miktar
                c.execute("UPDATE products SET stok_miktari = ? WHERE id = ?", (new_stock, urun_id))
                
                c.execute('''INSERT INTO stock_movements (license_code, urun_id, urun_kodu, urun_adi, hareket_tipi, miktar, birim, aciklama, created_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                          (license_code, urun_id, product['urun_kodu'], product['urun_adi'], 
                           'Giriş', teslim_miktar, product['birim'], f'Sipariş teslim alındı', now))
    
    teslim_durumu = 'Uyumsuzluk Var' if has_discrepancy else 'Tamamlandı'
    c.execute('''UPDATE orders SET durum = ?, teslim_durumu = ?, teslim_miktarlari = ?, teslim_uyumsuzluk = ? 
                 WHERE id = ? AND license_code = ?''', 
              ('Teslim Alındı', teslim_durumu, json.dumps(teslimler), discrepancy_msg if has_discrepancy else None, id, license_code))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/stock-movements', methods=['GET', 'POST'])
def stock_movements():
    license_code = request.args.get('license_code') or (request.json.get('license_code') if request.json else None)
    conn = get_db()
    c = conn.cursor()
    
    if request.method == 'GET':
        c.execute("SELECT * FROM stock_movements WHERE license_code = ? ORDER BY id DESC", (license_code,))
        rows = c.fetchall()
        conn.close()
        return jsonify([dict(row) for row in rows])
    
    data = request.json
    now = datetime.now().isoformat()
    urun_id = data.get('urun_id')
    miktar = float(data.get('miktar', 0))
    hareket_tipi = data.get('hareket_tipi')
    
    c.execute("SELECT * FROM products WHERE id = ?", (urun_id,))
    product = c.fetchone()
    if not product:
        conn.close()
        return jsonify({'success': False, 'message': 'Ürün bulunamadı!'})
    
    current_stock = float(product['stok_miktari'] or 0)
    
    if hareket_tipi == 'Çıkış' and miktar > current_stock:
        conn.close()
        return jsonify({'success': False, 'message': f'Yetersiz stok! Mevcut: {current_stock}'})
    
    new_stock = current_stock + miktar if hareket_tipi == 'Giriş' else current_stock - miktar
    
    c.execute("UPDATE products SET stok_miktari = ? WHERE id = ?", (new_stock, urun_id))
    
    c.execute('''INSERT INTO stock_movements (license_code, urun_id, urun_kodu, urun_adi, hareket_tipi, miktar, birim, aciklama, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
              (license_code, urun_id, product['urun_kodu'], product['urun_adi'], 
               hareket_tipi, miktar, product['birim'], data.get('aciklama'), now))
    
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'new_stock': new_stock})

@app.route('/api/invoices', methods=['GET', 'POST'])
def invoices():
    license_code = request.args.get('license_code') or (request.json.get('license_code') if request.json else None)
    conn = get_db()
    c = conn.cursor()
    
    if request.method == 'GET':
        c.execute("SELECT * FROM invoices WHERE license_code = ? ORDER BY id DESC", (license_code,))
        rows = c.fetchall()
        conn.close()
        return jsonify([dict(row) for row in rows])
    
    data = request.json
    now = datetime.now().isoformat()
    
    c.execute('''INSERT INTO invoices (license_code, siparis_id, siparis_no, tedarikci_adi, fatura_no, fatura_tarihi, 
                matrah, kdv_orani, kdv_tutari, fatura_tutari, fatura_urunleri, notlar, created_at) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
              (license_code, data.get('siparis_id'), data.get('siparis_no'),
               data.get('tedarikci_adi'), data.get('fatura_no'), data.get('fatura_tarihi'),
               data.get('matrah'), data.get('kdv_orani'), data.get('kdv_tutari'),
               data.get('fatura_tutari'), data.get('fatura_urunleri'), data.get('notlar'), now))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/invoices/<int:id>', methods=['DELETE'])
def delete_invoice(id):
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM invoices WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/license/activate', methods=['POST'])
def activate_license():
    data = request.json
    user_license_code = data.get('user_license_code', '').strip()
    new_license_code = data.get('new_license_code', '').strip()
    
    conn = get_db()
    c = conn.cursor()
    
    c.execute("SELECT * FROM licenses WHERE license_code = ?", (new_license_code,))
    new_license = c.fetchone()
    
    if not new_license:
        conn.close()
        return jsonify({'success': False, 'message': 'Geçersiz lisans kodu!'})
    
    if new_license['is_active'] == 1 and new_license['license_code'] != user_license_code:
        conn.close()
        return jsonify({'success': False, 'message': 'Bu lisans kodu başka bir firma tarafından kullanılıyor!'})
    
    c.execute("UPDATE users SET license_code = ? WHERE license_code = ?", (new_license_code, user_license_code))
    c.execute("UPDATE licenses SET is_active = 1 WHERE license_code = ?", (new_license_code,))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': 'Lisans başarıyla aktif edildi!'})

@app.route('/api/license/info', methods=['GET'])
def license_info():
    license_code = request.args.get('license_code')
    
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM licenses WHERE license_code = ?", (license_code,))
    license_row = c.fetchone()
    conn.close()
    
    if not license_row:
        return jsonify({'success': False, 'message': 'Lisans bulunamadı!'})
    
    kalan_gun = None
    if license_row['bitis_tarihi']:
        try:
            bitis = datetime.strptime(license_row['bitis_tarihi'], '%Y-%m-%d')
            bugun = datetime.now()
            kalan_gun = (bitis - bugun).days
        except:
            pass
    
    return jsonify({
        'success': True,
        'license': {
            'license_code': license_row['license_code'],
            'company_name': license_row['company_name'],
            'is_active': license_row['is_active'] == 1,
            'paket_tipi': license_row['paket_tipi'],
            'baslangic_tarihi': license_row['baslangic_tarihi'],
            'bitis_tarihi': license_row['bitis_tarihi'],
            'kalan_gun': kalan_gun
        }
    })

@app.route('/api/users', methods=['GET', 'POST'])
def users():
    license_code = request.args.get('license_code') or (request.json.get('license_code') if request.json else None)
    conn = get_db()
    c = conn.cursor()
    
    if request.method == 'GET':
        c.execute("SELECT id, license_code, email, role, yetkiler, created_at FROM users WHERE license_code = ? ORDER BY id", (license_code,))
        rows = c.fetchall()
        conn.close()
        return jsonify([dict(row) for row in rows])
    
    data = request.json
    now = datetime.now().isoformat()
    
    c.execute("SELECT * FROM users WHERE email = ?", (data.get('email'),))
    if c.fetchone():
        conn.close()
        return jsonify({'success': False, 'message': 'Bu e-posta sistemde zaten kayıtlı!'})
    
    c.execute('''INSERT INTO users (license_code, email, password, role, yetkiler, created_at) 
                VALUES (?, ?, ?, ?, ?, ?)''',
              (license_code, data.get('email'), data.get('password'),
               data.get('role', 'Kullanıcı'), json.dumps(data.get('yetkiler', [])), now))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/users/<int:id>', methods=['DELETE'])
def delete_user(id):
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/categories', methods=['GET', 'POST'])
def categories():
    license_code = request.args.get('license_code') or (request.json.get('license_code') if request.json else None)
    conn = get_db()
    c = conn.cursor()
    
    if request.method == 'GET':
        c.execute("SELECT * FROM categories WHERE license_code = ? ORDER BY seviye, id", (license_code,))
        rows = c.fetchall()
        conn.close()
        return jsonify([dict(row) for row in rows])
    
    data = request.json
    now = datetime.now().isoformat()
    c.execute('''INSERT INTO categories (license_code, seviye, kategori_adi, ust_kategori_id, created_at) 
                VALUES (?, ?, ?, ?, ?)''',
              (license_code, data.get('seviye'), data.get('kategori_adi'), data.get('ust_kategori_id'), now))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/categories/<int:id>', methods=['PUT', 'DELETE'])
def update_delete_category(id):
    license_code = request.args.get('license_code') or (request.json.get('license_code') if request.json else None)
    conn = get_db()
    c = conn.cursor()
    
    if request.method == 'DELETE':
        c.execute("SELECT * FROM categories WHERE ust_kategori_id = ?", (id,))
        children = c.fetchall()
        if children:
            conn.close()
            return jsonify({'success': False, 'message': 'Bu kategorinin alt kategorileri var! Önce onları silin.'})
        c.execute("DELETE FROM categories WHERE id = ? AND license_code = ?", (id, license_code))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    
    data = request.json
    new_name = data.get('kategori_adi')
    if not new_name:
        conn.close()
        return jsonify({'success': False, 'message': 'Kategori adı gerekli!'})
    
    c.execute("UPDATE categories SET kategori_adi = ? WHERE id = ? AND license_code = ?", 
              (new_name, id, license_code))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/project-statuses', methods=['GET', 'POST'])
def project_statuses():
    license_code = request.args.get('license_code') or (request.json.get('license_code') if request.json else None)
    if not license_code:
        return jsonify({'success': False, 'message': 'License code required'}), 400
    
    conn = get_db()
    c = conn.cursor()
    
    if request.method == 'GET':
        c.execute("SELECT * FROM project_statuses WHERE license_code = ? ORDER BY sira", (license_code,))
        statuses = [dict(row) for row in c.fetchall()]
        conn.close()
        if not statuses:
            now = datetime.now().isoformat()
            conn = get_db()
            c = conn.cursor()
            default_statuses = [('Aktif', 1), ('Planlama', 2), ('Tamamlandı', 3), ('İptal', 4)]
            for durum, sira in default_statuses:
                c.execute("INSERT INTO project_statuses (license_code, durum_adi, sira, created_at) VALUES (?, ?, ?, ?)",
                          (license_code, durum, sira, now))
            conn.commit()
            c.execute("SELECT * FROM project_statuses WHERE license_code = ? ORDER BY sira", (license_code,))
            statuses = [dict(row) for row in c.fetchall()]
            conn.close()
        return jsonify(statuses)
    
    data = request.json
    durum_adi = data.get('durum_adi')
    if not durum_adi:
        conn.close()
        return jsonify({'success': False, 'message': 'Durum adı gerekli!'})
    
    c.execute("SELECT MAX(sira) FROM project_statuses WHERE license_code = ?", (license_code,))
    max_sira = c.fetchone()[0] or 0
    
    c.execute("INSERT INTO project_statuses (license_code, durum_adi, sira, created_at) VALUES (?, ?, ?, ?)",
              (license_code, durum_adi, max_sira + 1, datetime.now().isoformat()))
    conn.commit()
    new_id = c.lastrowid
    conn.close()
    return jsonify({'success': True, 'id': new_id})

@app.route('/api/project-statuses/<int:id>', methods=['PUT', 'DELETE'])
def update_delete_project_status(id):
    license_code = request.args.get('license_code') or (request.json.get('license_code') if request.json else None)
    conn = get_db()
    c = conn.cursor()
    
    if request.method == 'DELETE':
        c.execute("DELETE FROM project_statuses WHERE id = ? AND license_code = ?", (id, license_code))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    
    data = request.json
    new_name = data.get('durum_adi')
    if not new_name:
        conn.close()
        return jsonify({'success': False, 'message': 'Durum adı gerekli!'})
    
    c.execute("UPDATE project_statuses SET durum_adi = ? WHERE id = ? AND license_code = ?", 
              (new_name, id, license_code))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/dashboard', methods=['GET'])
def dashboard():
    license_code = request.args.get('license_code')
    conn = get_db()
    c = conn.cursor()
    
    c.execute("SELECT COUNT(*) FROM projects WHERE license_code = ? AND durum = 'Aktif'", (license_code,))
    aktif_projeler = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM requests WHERE license_code = ? AND durum = 'Beklemede'", (license_code,))
    bekleyen_talepler = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM orders WHERE license_code = ?", (license_code,))
    toplam_siparis = c.fetchone()[0]
    
    c.execute("SELECT * FROM products WHERE license_code = ? AND stok_miktari < minimum_stok", (license_code,))
    kritik_stoklar = [dict(row) for row in c.fetchall()]
    
    c.execute("SELECT COALESCE(SUM(genel_toplam), 0) FROM orders WHERE license_code = ?", (license_code,))
    toplam_satin_alma = c.fetchone()[0] or 0
    
    c.execute("SELECT COALESCE(SUM(genel_toplam), 0) FROM orders WHERE license_code = ? AND durum = 'Tamamlandı'", (license_code,))
    tamamlanan_tutar = c.fetchone()[0] or 0
    
    c.execute("SELECT COALESCE(SUM(genel_toplam), 0) FROM orders WHERE license_code = ? AND durum = 'Beklemede'", (license_code,))
    bekleyen_tutar = c.fetchone()[0] or 0
    
    c.execute("SELECT COUNT(*) FROM suppliers WHERE license_code = ?", (license_code,))
    toplam_tedarikci = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM products WHERE license_code = ?", (license_code,))
    toplam_urun = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM invoices WHERE license_code = ?", (license_code,))
    toplam_fatura = c.fetchone()[0]
    
    c.execute("SELECT COALESCE(SUM(fatura_tutari), 0) FROM invoices WHERE license_code = ?", (license_code,))
    toplam_fatura_tutar = c.fetchone()[0] or 0
    
    c.execute("""SELECT * FROM user_activities WHERE license_code = ? 
                ORDER BY created_at DESC LIMIT 20""", (license_code,))
    son_aktiviteler = [dict(row) for row in c.fetchall()]
    
    c.execute("""SELECT user_email, COUNT(*) as talep_sayisi 
                FROM user_activities WHERE license_code = ? AND activity_type = 'request_create'
                GROUP BY user_email ORDER BY talep_sayisi DESC LIMIT 5""", (license_code,))
    en_cok_talep = [dict(row) for row in c.fetchall()]
    
    c.execute("""SELECT user_email, COUNT(*) as siparis_sayisi 
                FROM user_activities WHERE license_code = ? AND activity_type = 'order_create'
                GROUP BY user_email ORDER BY siparis_sayisi DESC LIMIT 5""", (license_code,))
    en_cok_siparis = [dict(row) for row in c.fetchall()]
    
    c.execute("""SELECT user_email, MAX(created_at) as son_giris 
                FROM user_activities WHERE license_code = ? AND activity_type = 'login'
                GROUP BY user_email ORDER BY son_giris DESC LIMIT 10""", (license_code,))
    son_girisler = [dict(row) for row in c.fetchall()]
    
    conn.close()
    return jsonify({
        'aktif_projeler': aktif_projeler,
        'bekleyen_talepler': bekleyen_talepler,
        'toplam_siparis': toplam_siparis,
        'kritik_stok_sayisi': len(kritik_stoklar),
        'kritik_stoklar': kritik_stoklar,
        'toplam_satin_alma': toplam_satin_alma,
        'tamamlanan_tutar': tamamlanan_tutar,
        'bekleyen_tutar': bekleyen_tutar,
        'toplam_tedarikci': toplam_tedarikci,
        'toplam_urun': toplam_urun,
        'toplam_fatura': toplam_fatura,
        'toplam_fatura_tutar': toplam_fatura_tutar,
        'son_aktiviteler': son_aktiviteler,
        'en_cok_talep': en_cok_talep,
        'en_cok_siparis': en_cok_siparis,
        'son_girisler': son_girisler
    })

import secrets
import hashlib

super_admin_sessions = {}

def generate_super_admin_token(admin_id):
    token = secrets.token_hex(32)
    super_admin_sessions[token] = {
        'admin_id': admin_id,
        'created_at': datetime.now().isoformat()
    }
    return token

def verify_super_admin_token():
    token = request.headers.get('X-Super-Admin-Token')
    if not token or token not in super_admin_sessions:
        return None
    return super_admin_sessions[token]

def require_super_admin():
    session = verify_super_admin_token()
    if not session:
        return jsonify({'success': False, 'message': 'Yetkisiz erişim! Lütfen giriş yapın.'}), 401
    return None

@app.route('/api/super-admin/login', methods=['POST'])
def super_admin_login():
    data = request.json
    email = data.get('email', '').strip()
    password = data.get('password', '').strip()
    
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM super_admins WHERE email = ? AND password = ?", (email, password))
    admin = c.fetchone()
    conn.close()
    
    if admin:
        token = generate_super_admin_token(admin['id'])
        return jsonify({
            'success': True,
            'token': token,
            'admin': {
                'id': admin['id'],
                'email': admin['email'],
                'ad_soyad': admin['ad_soyad']
            }
        })
    return jsonify({'success': False, 'message': 'Geçersiz e-posta veya şifre!'})

@app.route('/api/super-admin/logout', methods=['POST'])
def super_admin_logout():
    token = request.headers.get('X-Super-Admin-Token')
    if token and token in super_admin_sessions:
        del super_admin_sessions[token]
    return jsonify({'success': True})

@app.route('/api/super-admin/dashboard', methods=['GET'])
def super_admin_dashboard():
    auth_error = require_super_admin()
    if auth_error:
        return auth_error
    
    conn = get_db()
    c = conn.cursor()
    
    c.execute("SELECT COUNT(*) FROM licenses")
    toplam_firma = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM licenses WHERE is_active = 1")
    aktif_firma = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM licenses WHERE is_active = 0")
    pasif_firma = c.fetchone()[0]
    
    today = datetime.now().strftime('%Y-%m-%d')
    c.execute("SELECT COUNT(*) FROM licenses WHERE bitis_tarihi IS NOT NULL AND bitis_tarihi <= date(?, '+7 days') AND bitis_tarihi >= ?", (today, today))
    yaklasan_biten = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM licenses WHERE bitis_tarihi IS NOT NULL AND bitis_tarihi < ?", (today,))
    suresi_dolan = c.fetchone()[0]
    
    c.execute("SELECT SUM(aylik_ucret) FROM licenses WHERE is_active = 1")
    aylik_gelir = c.fetchone()[0] or 0
    
    c.execute("""SELECT * FROM licenses WHERE bitis_tarihi IS NOT NULL 
                 AND bitis_tarihi <= date(?, '+30 days') AND bitis_tarihi >= ?
                 ORDER BY bitis_tarihi ASC LIMIT 10""", (today, today))
    yaklasan_bitenler = [dict(row) for row in c.fetchall()]
    
    # Ürün bazlı istatistikler
    c.execute("SELECT * FROM protera_products ORDER BY id")
    urunler = [dict(row) for row in c.fetchall()]
    
    urun_istatistikleri = []
    for urun in urunler:
        # Bu ürünü kullanan aktif firma sayısı
        c.execute("""SELECT COUNT(DISTINCT lp.license_id) FROM license_products lp 
                    JOIN licenses l ON lp.license_id = l.id 
                    WHERE lp.product_id = ? AND lp.is_active = 1 AND l.is_active = 1""", (urun['id'],))
        aktif_firma_sayisi = c.fetchone()[0]
        
        # Kullanıcı sayısı (ürüne göre)
        kullanici_sayisi = 0
        if urun['product_code'] == 'tedarik':
            c.execute("SELECT COUNT(*) FROM users")
            kullanici_sayisi = c.fetchone()[0]
        elif urun['product_code'] == 'lojistik':
            c.execute("SELECT COUNT(*) FROM loj_users")
            kullanici_sayisi = c.fetchone()[0]
        elif urun['product_code'] == 'servis':
            c.execute("SELECT COUNT(*) FROM servis_users")
            kullanici_sayisi = c.fetchone()[0]
        
        urun_istatistikleri.append({
            'id': urun['id'],
            'product_code': urun['product_code'],
            'product_name': urun['product_name'],
            'icon': urun['icon'],
            'color': urun['color'],
            'is_active': urun['is_active'],
            'aktif_firma': aktif_firma_sayisi,
            'kullanici_sayisi': kullanici_sayisi,
            'monthly_price': urun['monthly_price']
        })
    
    # Toplam kullanıcı sayısı (tüm sistemler)
    c.execute("SELECT COUNT(*) FROM users")
    tedarik_users = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM loj_users")
    lojistik_users = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM servis_users")
    servis_users = c.fetchone()[0]
    toplam_kullanici = tedarik_users + lojistik_users + servis_users
    
    conn.close()
    return jsonify({
        'toplam_firma': toplam_firma,
        'aktif_firma': aktif_firma,
        'pasif_firma': pasif_firma,
        'yaklasan_biten': yaklasan_biten,
        'suresi_dolan': suresi_dolan,
        'aylik_gelir': aylik_gelir,
        'yaklasan_bitenler': yaklasan_bitenler,
        'urun_istatistikleri': urun_istatistikleri,
        'toplam_kullanici': toplam_kullanici,
        'kullanici_dagilimi': {
            'tedarik': tedarik_users,
            'lojistik': lojistik_users,
            'servis': servis_users
        }
    })

@app.route('/api/super-admin/licenses', methods=['GET', 'POST'])
def super_admin_licenses():
    auth_error = require_super_admin()
    if auth_error:
        return auth_error
    
    conn = get_db()
    c = conn.cursor()
    
    if request.method == 'GET':
        include_products = request.args.get('includeProducts', 'false') == 'true'
        
        c.execute("""SELECT l.*, 
                     (SELECT COUNT(*) FROM users WHERE license_code = l.license_code) as kullanici_sayisi,
                     (SELECT COUNT(*) FROM projects WHERE license_code = l.license_code) as proje_sayisi
                     FROM licenses l ORDER BY l.created_at DESC""")
        licenses_raw = c.fetchall()
        
        # Ürün bilgilerini tek sorguda al (N+1 sorunu çözümü)
        product_map = {}
        if include_products:
            c.execute("SELECT * FROM protera_products ORDER BY id")
            all_products = [dict(row) for row in c.fetchall()]
            
            c.execute("""SELECT lp.license_id, lp.product_id, lp.is_active, lp.activated_at, lp.expires_at
                        FROM license_products lp""")
            all_license_products = c.fetchall()
            
            # License ID'ye göre ürün atamalarını grupla
            lp_map = {}
            for lp in all_license_products:
                lid = lp['license_id']
                if lid not in lp_map:
                    lp_map[lid] = {}
                lp_map[lid][lp['product_id']] = {
                    'is_active': lp['is_active'],
                    'activated_at': lp['activated_at'].split('T')[0] if lp['activated_at'] and 'T' in str(lp['activated_at']) else lp['activated_at'],
                    'expires_at': lp['expires_at'].split('T')[0] if lp['expires_at'] and 'T' in str(lp['expires_at']) else lp['expires_at']
                }
            
            # Her lisans için ürün listesini hazırla
            for lic_row in licenses_raw:
                lid = lic_row['id']
                urunler = []
                for prod in all_products:
                    lp_info = lp_map.get(lid, {}).get(prod['id'], {})
                    urunler.append({
                        'product_code': prod['product_code'],
                        'product_name': prod['product_name'],
                        'icon': prod['icon'],
                        'color': prod['color'],
                        'firma_aktif': lp_info.get('is_active', 0),
                        'activated_at': lp_info.get('activated_at'),
                        'expires_at': lp_info.get('expires_at')
                    })
                product_map[lid] = urunler
        
        licenses = []
        today = datetime.now().strftime('%Y-%m-%d')
        for row in licenses_raw:
            lic = dict(row)
            if lic.get('bitis_tarihi'):
                bitis = datetime.strptime(lic['bitis_tarihi'], '%Y-%m-%d')
                kalan_gun = (bitis - datetime.now()).days
                lic['kalan_gun'] = kalan_gun
                if kalan_gun < 0:
                    lic['durum_renk'] = 'kirmizi'
                elif kalan_gun <= 7:
                    lic['durum_renk'] = 'sari'
                else:
                    lic['durum_renk'] = 'yesil'
            else:
                lic['kalan_gun'] = None
                lic['durum_renk'] = 'gri'
            
            if include_products:
                lic['urunler'] = product_map.get(lic['id'], [])
            
            licenses.append(lic)
        conn.close()
        return jsonify(licenses)
    
    data = request.json
    license_code = data.get('license_code', '').strip().upper()
    company_name = data.get('company_name', '').strip()
    iletisim_email = data.get('iletisim_email', '')
    iletisim_telefon = data.get('iletisim_telefon', '')
    products = data.get('products', [])
    
    if not license_code or not company_name:
        conn.close()
        return jsonify({'success': False, 'message': 'Lisans kodu ve firma adı gerekli!'})
    
    if not products:
        conn.close()
        return jsonify({'success': False, 'message': 'En az bir sistem seçmelisiniz!'})
    
    c.execute("SELECT * FROM licenses WHERE license_code = ?", (license_code,))
    if c.fetchone():
        conn.close()
        return jsonify({'success': False, 'message': 'Bu lisans kodu zaten kullanılıyor!'})
    
    now = datetime.now().isoformat()
    today = datetime.now().strftime('%Y-%m-%d')
    
    # İlk ürünün tarihlerini lisans tarihi olarak kullan
    first_prod = products[0] if products else {}
    baslangic_tarihi = first_prod.get('activated_at', today)
    bitis_tarihi = first_prod.get('expires_at', '')
    
    c.execute("""INSERT INTO licenses (license_code, company_name, paket_tipi, baslangic_tarihi, 
                bitis_tarihi, aylik_ucret, iletisim_email, iletisim_telefon, is_active, created_at) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?)""",
              (license_code, company_name, 'standart', baslangic_tarihi, bitis_tarihi, 
               0, iletisim_email, iletisim_telefon, now))
    
    license_id = c.lastrowid
    
    # Seçilen ürünleri license_products tablosuna ekle
    for prod in products:
        product_code = prod.get('product_code')
        activated_at = prod.get('activated_at', today)
        expires_at = prod.get('expires_at', '')
        
        c.execute("SELECT id FROM protera_products WHERE product_code = ?", (product_code,))
        prod_row = c.fetchone()
        if prod_row:
            c.execute("""INSERT INTO license_products (license_id, product_id, is_active, activated_at, expires_at) 
                        VALUES (?, ?, 1, ?, ?)""",
                      (license_id, prod_row['id'], activated_at, expires_at if expires_at else None))
    
    admin_email = data.get('admin_email', f'admin@{license_code.lower()}.com')
    admin_password = data.get('admin_password', '123456')
    
    # Tedarik seçildiyse users tablosuna ekle
    tedarik_selected = any(p.get('product_code') == 'tedarik' for p in products)
    if tedarik_selected:
        c.execute("""INSERT INTO users (license_code, email, password, role, yetkiler, created_at) 
                    VALUES (?, ?, ?, 'Yönetim', '[]', ?)""",
                  (license_code, admin_email, admin_password, now))
        
        default_statuses = [('Aktif', 1), ('Planlama', 2), ('Tamamlandı', 3), ('İptal', 4)]
        for durum, sira in default_statuses:
            c.execute("INSERT INTO project_statuses (license_code, durum_adi, sira, created_at) VALUES (?, ?, ?, ?)",
                      (license_code, durum, sira, now))
    
    # Lojistik seçildiyse loj_users tablosuna ekle
    lojistik_selected = any(p.get('product_code') == 'lojistik' for p in products)
    if lojistik_selected:
        c.execute("""INSERT INTO loj_users (license_code, email, password, ad_soyad, role, yetkiler, created_at) 
                    VALUES (?, ?, ?, ?, 'Yönetim', '[]', ?)""",
                  (license_code, admin_email, admin_password, 'Admin', now))
    
    # Servis seçildiyse servis_users tablosuna ekle
    servis_selected = any(p.get('product_code') == 'servis' for p in products)
    if servis_selected:
        c.execute("""INSERT INTO servis_users (license_code, email, password, ad_soyad, role, durum, yetkiler, created_at) 
                    VALUES (?, ?, ?, ?, 'Yönetim', 'Aktif', '[]', ?)""",
                  (license_code, admin_email, admin_password, 'Admin', now))
    
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'license_code': license_code})

@app.route('/api/super-admin/licenses/<int:id>', methods=['GET', 'PUT', 'DELETE'])
def super_admin_license_detail(id):
    auth_error = require_super_admin()
    if auth_error:
        return auth_error
    
    conn = get_db()
    c = conn.cursor()
    
    if request.method == 'GET':
        c.execute("SELECT * FROM licenses WHERE id = ?", (id,))
        lic = c.fetchone()
        if not lic:
            conn.close()
            return jsonify({'success': False, 'message': 'Lisans bulunamadı!'})
        
        lic_dict = dict(lic)
        license_code = lic['license_code']
        
        # Tedarik istatistikleri
        c.execute("SELECT COUNT(*) FROM users WHERE license_code = ?", (license_code,))
        lic_dict['tedarik_kullanici_sayisi'] = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM projects WHERE license_code = ?", (license_code,))
        lic_dict['proje_sayisi'] = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM products WHERE license_code = ?", (license_code,))
        lic_dict['urun_sayisi'] = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM suppliers WHERE license_code = ?", (license_code,))
        lic_dict['tedarikci_sayisi'] = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM orders WHERE license_code = ?", (license_code,))
        lic_dict['siparis_sayisi'] = c.fetchone()[0]
        
        # Lojistik istatistikleri
        c.execute("SELECT COUNT(*) FROM loj_users WHERE license_code = ?", (license_code,))
        lic_dict['lojistik_kullanici_sayisi'] = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM loj_araclar WHERE license_code = ?", (license_code,))
        lic_dict['arac_sayisi'] = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM loj_suruculer WHERE license_code = ?", (license_code,))
        lic_dict['surucu_sayisi'] = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM loj_sevkiyatlar WHERE license_code = ?", (license_code,))
        lic_dict['sevkiyat_sayisi'] = c.fetchone()[0]
        
        # Servis istatistikleri
        c.execute("SELECT COUNT(*) FROM servis_users WHERE license_code = ?", (license_code,))
        lic_dict['servis_kullanici_sayisi'] = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM servis_musteriler WHERE license_code = ?", (license_code,))
        lic_dict['servis_musteri_sayisi'] = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM servis_arizalar WHERE license_code = ?", (license_code,))
        lic_dict['ariza_sayisi'] = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM servis_teknisyenler WHERE license_code = ?", (license_code,))
        lic_dict['teknisyen_sayisi'] = c.fetchone()[0]
        
        # Aktif ürünler
        c.execute("""SELECT pp.* FROM protera_products pp 
                    JOIN license_products lp ON pp.id = lp.product_id 
                    WHERE lp.license_id = ? AND lp.is_active = 1""", (id,))
        aktif_urunler = [dict(row) for row in c.fetchall()]
        lic_dict['aktif_urunler'] = aktif_urunler
        
        # Tüm ürünlerin durumu
        c.execute("""SELECT pp.*, 
                    COALESCE(lp.is_active, 0) as firma_aktif,
                    lp.activated_at, lp.expires_at
                    FROM protera_products pp 
                    LEFT JOIN license_products lp ON pp.id = lp.product_id AND lp.license_id = ?
                    ORDER BY pp.id""", (id,))
        tum_urunler = []
        for row in c.fetchall():
            urun = dict(row)
            # Tarihleri normalize et (YYYY-MM-DD)
            if urun.get('activated_at') and 'T' in str(urun['activated_at']):
                urun['activated_at'] = urun['activated_at'].split('T')[0]
            if urun.get('expires_at') and 'T' in str(urun['expires_at']):
                urun['expires_at'] = urun['expires_at'].split('T')[0]
            tum_urunler.append(urun)
        lic_dict['tum_urunler'] = tum_urunler
        
        # Kullanıcı listesi (tüm sistemler)
        kullanicilar = []
        c.execute("SELECT id, email, '' as ad_soyad, role, 'tedarik' as sistem FROM users WHERE license_code = ?", (license_code,))
        for row in c.fetchall():
            kullanicilar.append(dict(row))
        c.execute("SELECT id, email, ad_soyad, role, 'lojistik' as sistem FROM loj_users WHERE license_code = ?", (license_code,))
        for row in c.fetchall():
            kullanicilar.append(dict(row))
        c.execute("SELECT id, email, ad_soyad, role, 'servis' as sistem FROM servis_users WHERE license_code = ?", (license_code,))
        for row in c.fetchall():
            kullanicilar.append(dict(row))
        lic_dict['kullanicilar'] = kullanicilar
        
        conn.close()
        return jsonify(lic_dict)
    
    if request.method == 'DELETE':
        c.execute("SELECT license_code FROM licenses WHERE id = ?", (id,))
        row = c.fetchone()
        if row:
            lc = row['license_code']
            c.execute("DELETE FROM users WHERE license_code = ?", (lc,))
            c.execute("DELETE FROM projects WHERE license_code = ?", (lc,))
            c.execute("DELETE FROM products WHERE license_code = ?", (lc,))
            c.execute("DELETE FROM suppliers WHERE license_code = ?", (lc,))
            c.execute("DELETE FROM requests WHERE license_code = ?", (lc,))
            c.execute("DELETE FROM request_items WHERE license_code = ?", (lc,))
            c.execute("DELETE FROM offers WHERE license_code = ?", (lc,))
            c.execute("DELETE FROM orders WHERE license_code = ?", (lc,))
            c.execute("DELETE FROM stock_movements WHERE license_code = ?", (lc,))
            c.execute("DELETE FROM invoices WHERE license_code = ?", (lc,))
            c.execute("DELETE FROM project_statuses WHERE license_code = ?", (lc,))
            c.execute("DELETE FROM licenses WHERE id = ?", (id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    
    data = request.json
    c.execute("""UPDATE licenses SET 
                company_name = ?,
                paket_tipi = ?,
                baslangic_tarihi = ?,
                bitis_tarihi = ?,
                aylik_ucret = ?,
                iletisim_email = ?,
                iletisim_telefon = ?,
                is_active = ?
                WHERE id = ?""",
              (data.get('company_name'), data.get('paket_tipi'), data.get('baslangic_tarihi'),
               data.get('bitis_tarihi'), data.get('aylik_ucret', 0), data.get('iletisim_email'),
               data.get('iletisim_telefon'), data.get('is_active', 1), id))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

# Ürün Atama/Kaldırma/Güncelleme
@app.route('/api/super-admin/licenses/<int:id>/products', methods=['POST'])
def super_admin_license_products(id):
    auth_error = require_super_admin()
    if auth_error:
        return auth_error
    
    data = request.json
    product_id = data.get('product_id')
    action = data.get('action')  # 'add', 'remove', 'update'
    activated_at = data.get('activated_at', '').strip() if data.get('activated_at') else ''
    expires_at = data.get('expires_at', '').strip() if data.get('expires_at') else ''
    
    # Tarih formatı normalize et (YYYY-MM-DD)
    def normalize_date(date_str, default_days=0):
        if not date_str:
            return (datetime.now() + timedelta(days=default_days)).strftime('%Y-%m-%d')
        # Eğer ISO timestamp ise sadece tarih kısmını al
        if 'T' in date_str:
            return date_str.split('T')[0]
        return date_str
    
    conn = get_db()
    c = conn.cursor()
    now = datetime.now().strftime('%Y-%m-%d')
    
    if action == 'add':
        activated_at = normalize_date(activated_at, 0)
        expires_at = normalize_date(expires_at, 365)
        
        c.execute("SELECT id FROM license_products WHERE license_id = ? AND product_id = ?", (id, product_id))
        existing = c.fetchone()
        if existing:
            c.execute("UPDATE license_products SET is_active = 1, activated_at = ?, expires_at = ? WHERE license_id = ? AND product_id = ?",
                     (activated_at, expires_at, id, product_id))
        else:
            c.execute("INSERT INTO license_products (license_id, product_id, is_active, activated_at, expires_at, created_at) VALUES (?, ?, 1, ?, ?, ?)",
                     (id, product_id, activated_at, expires_at, now))
    elif action == 'remove':
        c.execute("UPDATE license_products SET is_active = 0 WHERE license_id = ? AND product_id = ?", (id, product_id))
    elif action == 'update':
        if not activated_at or not expires_at:
            conn.close()
            return jsonify({'success': False, 'message': 'Başlangıç ve bitiş tarihleri gerekli!'})
        activated_at = normalize_date(activated_at, 0)
        expires_at = normalize_date(expires_at, 365)
        c.execute("UPDATE license_products SET activated_at = ?, expires_at = ? WHERE license_id = ? AND product_id = ?",
                 (activated_at, expires_at, id, product_id))
    
    conn.commit()
    conn.close()
    return jsonify({'success': True})

# Ürün Kataloğu Listesi
@app.route('/api/super-admin/products', methods=['GET'])
def super_admin_products():
    auth_error = require_super_admin()
    if auth_error:
        return auth_error
    
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM protera_products ORDER BY id")
    rows = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify(rows)

@app.route('/api/super-admin/licenses/<int:id>/extend', methods=['POST'])
def super_admin_extend_license(id):
    auth_error = require_super_admin()
    if auth_error:
        return auth_error
    
    data = request.json
    yeni_bitis = data.get('bitis_tarihi')
    
    if not yeni_bitis:
        return jsonify({'success': False, 'message': 'Yeni bitiş tarihi gerekli!'})
    
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE licenses SET bitis_tarihi = ?, is_active = 1 WHERE id = ?", (yeni_bitis, id))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

# ==================== LOJISTIK API ENDPOINTS ====================

@app.route('/api/lojistik/login', methods=['POST'])
def lojistik_api_login():
    data = request.json
    email = data.get('email', '').strip()
    password = data.get('password', '').strip()
    
    conn = get_db()
    c = conn.cursor()
    
    c.execute("SELECT * FROM loj_users WHERE email = ? AND password = ?", (email, password))
    user = c.fetchone()
    
    if not user:
        conn.close()
        return jsonify({'success': False, 'message': 'Geçersiz e-posta veya şifre!'})
    
    license_code = user['license_code']
    c.execute("SELECT * FROM licenses WHERE license_code = ?", (license_code,))
    license_row = c.fetchone()
    conn.close()
    
    if not license_row:
        return jsonify({'success': False, 'message': 'Lisans bulunamadı!'})
    
    return jsonify({
        'success': True,
        'user': {
            'id': user['id'],
            'license_code': user['license_code'],
            'email': user['email'],
            'ad_soyad': user['ad_soyad'],
            'role': user['role'],
            'yetkiler': user['yetkiler'],
            'company_name': license_row['company_name']
        }
    })

@app.route('/api/lojistik/dashboard', methods=['GET'])
def lojistik_dashboard():
    license_code = request.args.get('license_code')
    conn = get_db()
    c = conn.cursor()
    
    # Araç sayıları
    c.execute("SELECT COUNT(*) FROM loj_araclar WHERE license_code = ? AND durum = 'Aktif'", (license_code,))
    aktif_arac = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM loj_araclar WHERE license_code = ?", (license_code,))
    toplam_arac = c.fetchone()[0]
    
    # Sürücü sayıları
    c.execute("SELECT COUNT(*) FROM loj_suruculer WHERE license_code = ? AND durum = 'Aktif'", (license_code,))
    aktif_surucu = c.fetchone()[0]
    
    # Müşteri sayısı
    c.execute("SELECT COUNT(*) FROM loj_musteriler WHERE license_code = ?", (license_code,))
    musteri_sayisi = c.fetchone()[0]
    
    # Sevkiyat durumları
    c.execute("SELECT COUNT(*) FROM loj_sevkiyatlar WHERE license_code = ? AND durum = 'Planlandı'", (license_code,))
    planlanan_sevkiyat = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM loj_sevkiyatlar WHERE license_code = ? AND durum = 'Yolda'", (license_code,))
    yoldaki_sevkiyat = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM loj_sevkiyatlar WHERE license_code = ? AND durum = 'Teslim Edildi'", (license_code,))
    tamamlanan_sevkiyat = c.fetchone()[0]
    
    # Aylık gelir
    c.execute("SELECT COALESCE(SUM(navlun), 0) FROM loj_sevkiyatlar WHERE license_code = ? AND durum = 'Teslim Edildi'", (license_code,))
    toplam_gelir = c.fetchone()[0]
    
    # Son sevkiyatlar
    c.execute("SELECT * FROM loj_sevkiyatlar WHERE license_code = ? ORDER BY id DESC LIMIT 5", (license_code,))
    son_sevkiyatlar = [dict(row) for row in c.fetchall()]
    
    # Yaklaşan bakım/sigorta/muayene uyarıları
    bugun = datetime.now().strftime('%Y-%m-%d')
    yedi_gun_sonra = (datetime.now() + __import__('datetime').timedelta(days=30)).strftime('%Y-%m-%d')
    
    c.execute("""SELECT plaka, 'Sigorta' as tip, sigorta_bitis as tarih FROM loj_araclar 
                WHERE license_code = ? AND sigorta_bitis BETWEEN ? AND ?
                UNION ALL
                SELECT plaka, 'Muayene' as tip, muayene_bitis as tarih FROM loj_araclar 
                WHERE license_code = ? AND muayene_bitis BETWEEN ? AND ?
                ORDER BY tarih""", (license_code, bugun, yedi_gun_sonra, license_code, bugun, yedi_gun_sonra))
    uyarilar = [dict(row) for row in c.fetchall()]
    
    conn.close()
    
    return jsonify({
        'aktif_arac': aktif_arac,
        'toplam_arac': toplam_arac,
        'aktif_surucu': aktif_surucu,
        'musteri_sayisi': musteri_sayisi,
        'planlanan_sevkiyat': planlanan_sevkiyat,
        'yoldaki_sevkiyat': yoldaki_sevkiyat,
        'tamamlanan_sevkiyat': tamamlanan_sevkiyat,
        'toplam_gelir': toplam_gelir,
        'son_sevkiyatlar': son_sevkiyatlar,
        'uyarilar': uyarilar
    })

@app.route('/api/lojistik/araclar', methods=['GET', 'POST'])
def lojistik_araclar():
    license_code = request.args.get('license_code') or (request.json.get('license_code') if request.json else None)
    conn = get_db()
    c = conn.cursor()
    
    if request.method == 'GET':
        c.execute("SELECT * FROM loj_araclar WHERE license_code = ? ORDER BY id DESC", (license_code,))
        rows = c.fetchall()
        conn.close()
        return jsonify([dict(row) for row in rows])
    
    data = request.json
    now = datetime.now().isoformat()
    c.execute('''INSERT INTO loj_araclar (license_code, plaka, marka, model, yil, arac_tipi, kapasite_ton, 
                kapasite_m3, yakit_tipi, sigorta_bitis, muayene_bitis, kasko_bitis, km_sayaci, durum, notlar, created_at) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
              (license_code, data.get('plaka'), data.get('marka'), data.get('model'), data.get('yil'),
               data.get('arac_tipi'), data.get('kapasite_ton'), data.get('kapasite_m3'), data.get('yakit_tipi'),
               data.get('sigorta_bitis'), data.get('muayene_bitis'), data.get('kasko_bitis'), 
               data.get('km_sayaci', 0), data.get('durum', 'Aktif'), data.get('notlar'), now))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/lojistik/araclar/<int:id>', methods=['PUT', 'DELETE'])
def lojistik_arac_detail(id):
    conn = get_db()
    c = conn.cursor()
    
    if request.method == 'DELETE':
        c.execute("DELETE FROM loj_araclar WHERE id = ?", (id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    
    data = request.json
    c.execute('''UPDATE loj_araclar SET plaka = ?, marka = ?, model = ?, yil = ?, arac_tipi = ?, 
                kapasite_ton = ?, kapasite_m3 = ?, yakit_tipi = ?, sigorta_bitis = ?, muayene_bitis = ?, 
                kasko_bitis = ?, km_sayaci = ?, durum = ?, notlar = ? WHERE id = ?''',
              (data.get('plaka'), data.get('marka'), data.get('model'), data.get('yil'),
               data.get('arac_tipi'), data.get('kapasite_ton'), data.get('kapasite_m3'), data.get('yakit_tipi'),
               data.get('sigorta_bitis'), data.get('muayene_bitis'), data.get('kasko_bitis'),
               data.get('km_sayaci'), data.get('durum'), data.get('notlar'), id))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/lojistik/suruculer', methods=['GET', 'POST'])
def lojistik_suruculer():
    license_code = request.args.get('license_code') or (request.json.get('license_code') if request.json else None)
    conn = get_db()
    c = conn.cursor()
    
    if request.method == 'GET':
        c.execute("SELECT * FROM loj_suruculer WHERE license_code = ? ORDER BY id DESC", (license_code,))
        rows = c.fetchall()
        conn.close()
        return jsonify([dict(row) for row in rows])
    
    data = request.json
    now = datetime.now().isoformat()
    c.execute('''INSERT INTO loj_suruculer (license_code, ad_soyad, tc_no, telefon, email, adres, ehliyet_sinifi, 
                ehliyet_no, ehliyet_bitis, src_belgesi, src_bitis, psikoteknik_bitis, maas, ise_giris, 
                zimmetli_arac_id, durum, notlar, created_at) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
              (license_code, data.get('ad_soyad'), data.get('tc_no'), data.get('telefon'), data.get('email'),
               data.get('adres'), data.get('ehliyet_sinifi'), data.get('ehliyet_no'), data.get('ehliyet_bitis'),
               data.get('src_belgesi'), data.get('src_bitis'), data.get('psikoteknik_bitis'),
               data.get('maas', 0), data.get('ise_giris'), data.get('zimmetli_arac_id'),
               data.get('durum', 'Aktif'), data.get('notlar'), now))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/lojistik/suruculer/<int:id>', methods=['PUT', 'DELETE'])
def lojistik_surucu_detail(id):
    conn = get_db()
    c = conn.cursor()
    
    if request.method == 'DELETE':
        c.execute("DELETE FROM loj_suruculer WHERE id = ?", (id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    
    data = request.json
    c.execute('''UPDATE loj_suruculer SET ad_soyad = ?, tc_no = ?, telefon = ?, email = ?, adres = ?, 
                ehliyet_sinifi = ?, ehliyet_no = ?, ehliyet_bitis = ?, src_belgesi = ?, src_bitis = ?, 
                psikoteknik_bitis = ?, maas = ?, ise_giris = ?, zimmetli_arac_id = ?, durum = ?, notlar = ? WHERE id = ?''',
              (data.get('ad_soyad'), data.get('tc_no'), data.get('telefon'), data.get('email'),
               data.get('adres'), data.get('ehliyet_sinifi'), data.get('ehliyet_no'), data.get('ehliyet_bitis'),
               data.get('src_belgesi'), data.get('src_bitis'), data.get('psikoteknik_bitis'),
               data.get('maas'), data.get('ise_giris'), data.get('zimmetli_arac_id'),
               data.get('durum'), data.get('notlar'), id))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/lojistik/musteriler', methods=['GET', 'POST'])
def lojistik_musteriler():
    license_code = request.args.get('license_code') or (request.json.get('license_code') if request.json else None)
    conn = get_db()
    c = conn.cursor()
    
    if request.method == 'GET':
        c.execute("SELECT * FROM loj_musteriler WHERE license_code = ? ORDER BY id DESC", (license_code,))
        rows = c.fetchall()
        conn.close()
        return jsonify([dict(row) for row in rows])
    
    data = request.json
    now = datetime.now().isoformat()
    c.execute("SELECT COUNT(*) FROM loj_musteriler WHERE license_code = ?", (license_code,))
    count = c.fetchone()[0] + 1
    musteri_kodu = f"MUS-{str(count).zfill(3)}"
    
    c.execute('''INSERT INTO loj_musteriler (license_code, musteri_kodu, firma_adi, yetkili_kisi, telefon, email, 
                adres, vergi_no, vergi_dairesi, odeme_vadesi, notlar, created_at) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
              (license_code, musteri_kodu, data.get('firma_adi'), data.get('yetkili_kisi'), data.get('telefon'),
               data.get('email'), data.get('adres'), data.get('vergi_no'), data.get('vergi_dairesi'),
               data.get('odeme_vadesi', 0), data.get('notlar'), now))
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'musteri_kodu': musteri_kodu})

@app.route('/api/lojistik/musteriler/<int:id>', methods=['PUT', 'DELETE'])
def lojistik_musteri_detail(id):
    conn = get_db()
    c = conn.cursor()
    
    if request.method == 'DELETE':
        c.execute("DELETE FROM loj_musteriler WHERE id = ?", (id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    
    data = request.json
    c.execute('''UPDATE loj_musteriler SET firma_adi = ?, yetkili_kisi = ?, telefon = ?, email = ?, adres = ?, 
                vergi_no = ?, vergi_dairesi = ?, odeme_vadesi = ?, notlar = ? WHERE id = ?''',
              (data.get('firma_adi'), data.get('yetkili_kisi'), data.get('telefon'), data.get('email'),
               data.get('adres'), data.get('vergi_no'), data.get('vergi_dairesi'),
               data.get('odeme_vadesi'), data.get('notlar'), id))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/lojistik/sevkiyatlar', methods=['GET', 'POST'])
def lojistik_sevkiyatlar():
    license_code = request.args.get('license_code') or (request.json.get('license_code') if request.json else None)
    conn = get_db()
    c = conn.cursor()
    
    if request.method == 'GET':
        c.execute("SELECT * FROM loj_sevkiyatlar WHERE license_code = ? ORDER BY id DESC", (license_code,))
        rows = c.fetchall()
        conn.close()
        return jsonify([dict(row) for row in rows])
    
    data = request.json
    now = datetime.now().isoformat()
    c.execute("SELECT COUNT(*) FROM loj_sevkiyatlar WHERE license_code = ?", (license_code,))
    count = c.fetchone()[0] + 1
    sevkiyat_no = f"SVK-{str(count).zfill(5)}"
    
    c.execute('''INSERT INTO loj_sevkiyatlar (license_code, sevkiyat_no, musteri_id, musteri_adi, arac_id, plaka, 
                surucu_id, surucu_adi, yuklenme_adresi, yuklenme_il, teslimat_adresi, teslimat_il, yuk_cinsi, 
                yuk_miktari, yuk_birimi, navlun, maliyet, planlanan_yuklenme, planlanan_teslimat, mesafe_km, 
                durum, notlar, created_at) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
              (license_code, sevkiyat_no, data.get('musteri_id'), data.get('musteri_adi'), data.get('arac_id'),
               data.get('plaka'), data.get('surucu_id'), data.get('surucu_adi'), data.get('yuklenme_adresi'),
               data.get('yuklenme_il'), data.get('teslimat_adresi'), data.get('teslimat_il'), data.get('yuk_cinsi'),
               data.get('yuk_miktari'), data.get('yuk_birimi'), data.get('navlun', 0), data.get('maliyet', 0),
               data.get('planlanan_yuklenme'), data.get('planlanan_teslimat'), data.get('mesafe_km', 0),
               data.get('durum', 'Planlandı'), data.get('notlar'), now))
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'sevkiyat_no': sevkiyat_no})

@app.route('/api/lojistik/sevkiyatlar/<int:id>', methods=['GET', 'PUT', 'DELETE'])
def lojistik_sevkiyat_detail(id):
    conn = get_db()
    c = conn.cursor()
    
    if request.method == 'GET':
        c.execute("SELECT * FROM loj_sevkiyatlar WHERE id = ?", (id,))
        row = c.fetchone()
        conn.close()
        if row:
            return jsonify(dict(row))
        return jsonify({'success': False, 'message': 'Sevkiyat bulunamadı!'})
    
    if request.method == 'DELETE':
        c.execute("DELETE FROM loj_sevkiyatlar WHERE id = ?", (id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    
    data = request.json
    
    # Önce mevcut verileri al (kısmi güncelleme için)
    c.execute("SELECT * FROM loj_sevkiyatlar WHERE id = ?", (id,))
    existing = c.fetchone()
    if not existing:
        conn.close()
        return jsonify({'success': False, 'message': 'Sevkiyat bulunamadı!'})
    
    existing_data = dict(existing)
    
    # Sadece gönderilen alanları güncelle, diğerlerini koru
    c.execute('''UPDATE loj_sevkiyatlar SET musteri_id = ?, musteri_adi = ?, arac_id = ?, plaka = ?, 
                surucu_id = ?, surucu_adi = ?, yuklenme_adresi = ?, yuklenme_il = ?, teslimat_adresi = ?, 
                teslimat_il = ?, yuk_cinsi = ?, yuk_miktari = ?, yuk_birimi = ?, navlun = ?, maliyet = ?, 
                planlanan_yuklenme = ?, planlanan_teslimat = ?, gercek_yuklenme = ?, gercek_teslimat = ?, 
                mesafe_km = ?, durum = ?, notlar = ? WHERE id = ?''',
              (data.get('musteri_id', existing_data.get('musteri_id')), 
               data.get('musteri_adi', existing_data.get('musteri_adi')), 
               data.get('arac_id', existing_data.get('arac_id')), 
               data.get('plaka', existing_data.get('plaka')),
               data.get('surucu_id', existing_data.get('surucu_id')), 
               data.get('surucu_adi', existing_data.get('surucu_adi')), 
               data.get('yuklenme_adresi', existing_data.get('yuklenme_adresi')), 
               data.get('yuklenme_il', existing_data.get('yuklenme_il')),
               data.get('teslimat_adresi', existing_data.get('teslimat_adresi')), 
               data.get('teslimat_il', existing_data.get('teslimat_il')), 
               data.get('yuk_cinsi', existing_data.get('yuk_cinsi')), 
               data.get('yuk_miktari', existing_data.get('yuk_miktari')),
               data.get('yuk_birimi', existing_data.get('yuk_birimi')), 
               data.get('navlun', existing_data.get('navlun')), 
               data.get('maliyet', existing_data.get('maliyet')), 
               data.get('planlanan_yuklenme', existing_data.get('planlanan_yuklenme')),
               data.get('planlanan_teslimat', existing_data.get('planlanan_teslimat')), 
               data.get('gercek_yuklenme', existing_data.get('gercek_yuklenme')), 
               data.get('gercek_teslimat') if 'gercek_teslimat' in data else existing_data.get('gercek_teslimat'),
               data.get('mesafe_km', existing_data.get('mesafe_km')), 
               data.get('durum', existing_data.get('durum')), 
               data.get('notlar', existing_data.get('notlar')), id))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/lojistik/yakit', methods=['GET', 'POST'])
def lojistik_yakit():
    license_code = request.args.get('license_code') or (request.json.get('license_code') if request.json else None)
    conn = get_db()
    c = conn.cursor()
    
    if request.method == 'GET':
        c.execute("SELECT * FROM loj_yakit WHERE license_code = ? ORDER BY id DESC", (license_code,))
        rows = c.fetchall()
        conn.close()
        return jsonify([dict(row) for row in rows])
    
    data = request.json
    now = datetime.now().isoformat()
    toplam = float(data.get('litre', 0)) * float(data.get('birim_fiyat', 0))
    
    c.execute('''INSERT INTO loj_yakit (license_code, arac_id, plaka, surucu_id, surucu_adi, tarih, litre, 
                birim_fiyat, toplam_tutar, km_sayaci, yakit_tipi, istasyon, notlar, created_at) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
              (license_code, data.get('arac_id'), data.get('plaka'), data.get('surucu_id'), data.get('surucu_adi'),
               data.get('tarih'), data.get('litre'), data.get('birim_fiyat'), toplam,
               data.get('km_sayaci'), data.get('yakit_tipi'), data.get('istasyon'), data.get('notlar'), now))
    
    # Araç km güncellemesi
    if data.get('arac_id') and data.get('km_sayaci'):
        c.execute("UPDATE loj_araclar SET km_sayaci = ? WHERE id = ?", (data.get('km_sayaci'), data.get('arac_id')))
    
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/lojistik/yakit/<int:id>', methods=['DELETE'])
def lojistik_yakit_delete(id):
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM loj_yakit WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/lojistik/bakim', methods=['GET', 'POST'])
def lojistik_bakim():
    license_code = request.args.get('license_code') or (request.json.get('license_code') if request.json else None)
    conn = get_db()
    c = conn.cursor()
    
    if request.method == 'GET':
        c.execute("SELECT * FROM loj_bakim WHERE license_code = ? ORDER BY id DESC", (license_code,))
        rows = c.fetchall()
        conn.close()
        return jsonify([dict(row) for row in rows])
    
    data = request.json
    now = datetime.now().isoformat()
    c.execute('''INSERT INTO loj_bakim (license_code, arac_id, plaka, bakim_tipi, bakim_tarihi, sonraki_bakim_km, 
                sonraki_bakim_tarih, yapilan_isler, tutar, servis_adi, km_sayaci, notlar, created_at) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
              (license_code, data.get('arac_id'), data.get('plaka'), data.get('bakim_tipi'), data.get('bakim_tarihi'),
               data.get('sonraki_bakim_km'), data.get('sonraki_bakim_tarih'), data.get('yapilan_isler'),
               data.get('tutar', 0), data.get('servis_adi'), data.get('km_sayaci'), data.get('notlar'), now))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/lojistik/bakim/<int:id>', methods=['DELETE'])
def lojistik_bakim_delete(id):
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM loj_bakim WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/lojistik/faturalar', methods=['GET', 'POST'])
def lojistik_faturalar():
    license_code = request.args.get('license_code') or (request.json.get('license_code') if request.json else None)
    conn = get_db()
    c = conn.cursor()
    
    if request.method == 'GET':
        c.execute("SELECT * FROM loj_faturalar WHERE license_code = ? ORDER BY id DESC", (license_code,))
        rows = c.fetchall()
        conn.close()
        return jsonify([dict(row) for row in rows])
    
    data = request.json
    now = datetime.now().isoformat()
    matrah = float(data.get('matrah', 0))
    kdv_orani = int(data.get('kdv_orani', 18))
    kdv_tutari = matrah * kdv_orani / 100
    toplam = matrah + kdv_tutari
    
    c.execute('''INSERT INTO loj_faturalar (license_code, fatura_no, fatura_tipi, musteri_id, musteri_adi, 
                sevkiyat_id, sevkiyat_no, fatura_tarihi, vade_tarihi, matrah, kdv_orani, kdv_tutari, 
                toplam_tutar, odeme_durumu, notlar, created_at) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
              (license_code, data.get('fatura_no'), data.get('fatura_tipi'), data.get('musteri_id'),
               data.get('musteri_adi'), data.get('sevkiyat_id'), data.get('sevkiyat_no'),
               data.get('fatura_tarihi'), data.get('vade_tarihi'), matrah, kdv_orani, kdv_tutari,
               toplam, data.get('odeme_durumu', 'Ödenmedi'), data.get('notlar'), now))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/lojistik/faturalar/<int:id>', methods=['PUT', 'DELETE'])
def lojistik_fatura_detail(id):
    conn = get_db()
    c = conn.cursor()
    
    if request.method == 'DELETE':
        c.execute("DELETE FROM loj_faturalar WHERE id = ?", (id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    
    data = request.json
    c.execute("UPDATE loj_faturalar SET odeme_durumu = ? WHERE id = ?", (data.get('odeme_durumu'), id))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/lojistik/giderler', methods=['GET', 'POST'])
def lojistik_giderler():
    license_code = request.args.get('license_code') or (request.json.get('license_code') if request.json else None)
    conn = get_db()
    c = conn.cursor()
    
    if request.method == 'GET':
        c.execute("SELECT * FROM loj_giderler WHERE license_code = ? ORDER BY id DESC", (license_code,))
        rows = c.fetchall()
        conn.close()
        return jsonify([dict(row) for row in rows])
    
    data = request.json
    now = datetime.now().isoformat()
    c.execute('''INSERT INTO loj_giderler (license_code, gider_tipi, arac_id, plaka, tarih, tutar, aciklama, belge_no, created_at) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
              (license_code, data.get('gider_tipi'), data.get('arac_id'), data.get('plaka'),
               data.get('tarih'), data.get('tutar', 0), data.get('aciklama'), data.get('belge_no'), now))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/lojistik/giderler/<int:id>', methods=['DELETE'])
def lojistik_gider_delete(id):
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM loj_giderler WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/lojistik/users', methods=['GET', 'POST'])
def lojistik_users():
    license_code = request.args.get('license_code') or (request.json.get('license_code') if request.json else None)
    conn = get_db()
    c = conn.cursor()
    
    if request.method == 'GET':
        c.execute("SELECT id, license_code, email, ad_soyad, role, yetkiler, telefon, created_at FROM loj_users WHERE license_code = ? ORDER BY id", (license_code,))
        rows = c.fetchall()
        conn.close()
        return jsonify([dict(row) for row in rows])
    
    data = request.json
    now = datetime.now().isoformat()
    c.execute('''INSERT INTO loj_users (license_code, email, password, ad_soyad, role, yetkiler, telefon, created_at) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
              (license_code, data.get('email'), data.get('password', '123456'), data.get('ad_soyad'),
               data.get('role', 'Kullanıcı'), data.get('yetkiler', '[]'), data.get('telefon'), now))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/lojistik/users/<int:id>', methods=['PUT', 'DELETE'])
def lojistik_user_detail(id):
    conn = get_db()
    c = conn.cursor()
    
    if request.method == 'DELETE':
        c.execute("DELETE FROM loj_users WHERE id = ?", (id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    
    data = request.json
    if data.get('password'):
        c.execute("UPDATE loj_users SET email = ?, password = ?, ad_soyad = ?, role = ?, yetkiler = ?, telefon = ? WHERE id = ?",
                  (data.get('email'), data.get('password'), data.get('ad_soyad'), data.get('role'), 
                   data.get('yetkiler', '[]'), data.get('telefon'), id))
    else:
        c.execute("UPDATE loj_users SET email = ?, ad_soyad = ?, role = ?, yetkiler = ?, telefon = ? WHERE id = ?",
                  (data.get('email'), data.get('ad_soyad'), data.get('role'), data.get('yetkiler', '[]'), data.get('telefon'), id))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

# ==================== PROTERA SERVİS API ====================

@app.route('/servis')
def servis_page():
    return send_from_directory('.', 'servis.html')

@app.route('/api/servis/login', methods=['POST'])
def servis_api_login():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM servis_users WHERE email = ? AND password = ?", (email, password))
    user = c.fetchone()
    conn.close()
    
    if user:
        user_dict = dict(user)
        user_dict.pop('password', None)
        return jsonify({'success': True, 'user': user_dict})
    return jsonify({'success': False, 'message': 'E-posta veya şifre hatalı!'})

@app.route('/api/servis/dashboard')
def servis_dashboard():
    license_code = request.args.get('license_code')
    conn = get_db()
    c = conn.cursor()
    
    # Bekleyen işler
    c.execute("SELECT COUNT(*) FROM servis_arizalar WHERE license_code = ? AND durum = 'Beklemede'", (license_code,))
    bekleyen = c.fetchone()[0]
    
    # Devam eden işler
    c.execute("SELECT COUNT(*) FROM servis_arizalar WHERE license_code = ? AND durum IN ('Atandı', 'Yolda', 'İşlemde')", (license_code,))
    devam_eden = c.fetchone()[0]
    
    # Bu ay tamamlanan
    c.execute("SELECT COUNT(*) FROM servis_arizalar WHERE license_code = ? AND durum = 'Tamamlandı' AND created_at >= date('now', 'start of month')", (license_code,))
    tamamlanan = c.fetchone()[0]
    
    # Aktif teknisyen
    c.execute("SELECT COUNT(*) FROM servis_teknisyenler WHERE license_code = ? AND durum = 'Aktif'", (license_code,))
    aktif_teknisyen = c.fetchone()[0]
    
    # Acil arızalar
    c.execute("SELECT COUNT(*) FROM servis_arizalar WHERE license_code = ? AND oncelik = 'Acil' AND durum NOT IN ('Tamamlandı', 'İptal')", (license_code,))
    acil = c.fetchone()[0]
    
    # Bu ay gelir
    c.execute("SELECT COALESCE(SUM(toplam_tutar), 0) FROM servis_faturalar WHERE license_code = ? AND odeme_durumu = 'Ödendi' AND fatura_tarihi >= date('now', 'start of month')", (license_code,))
    gelir = c.fetchone()[0]
    
    # Bugünkü randevular
    c.execute("""SELECT a.*, m.ad_soyad as musteri_adi_full, m.firma_adi 
                FROM servis_arizalar a 
                LEFT JOIN servis_musteriler m ON a.musteri_id = m.id 
                WHERE a.license_code = ? AND a.randevu_tarihi = date('now') 
                ORDER BY a.randevu_saati""", (license_code,))
    bugun_randevular = [dict(row) for row in c.fetchall()]
    
    # Kritik stok
    c.execute("SELECT * FROM servis_parcalar WHERE license_code = ? AND stok_miktari <= min_stok ORDER BY stok_miktari", (license_code,))
    kritik_stok = [dict(row) for row in c.fetchall()]
    
    conn.close()
    
    return jsonify({
        'bekleyen': bekleyen,
        'devam_eden': devam_eden,
        'tamamlanan': tamamlanan,
        'aktif_teknisyen': aktif_teknisyen,
        'acil': acil,
        'gelir': gelir,
        'bugun_randevular': bugun_randevular,
        'kritik_stok': kritik_stok
    })

# Müşteriler
@app.route('/api/servis/musteriler', methods=['GET', 'POST'])
def servis_musteriler():
    license_code = request.args.get('license_code') or (request.json.get('license_code') if request.json else None)
    conn = get_db()
    c = conn.cursor()
    
    if request.method == 'GET':
        c.execute("SELECT * FROM servis_musteriler WHERE license_code = ? ORDER BY id DESC", (license_code,))
        rows = c.fetchall()
        conn.close()
        return jsonify([dict(row) for row in rows])
    
    data = request.json
    now = datetime.now().isoformat()
    
    # Müşteri kodu oluştur
    c.execute("SELECT COUNT(*) FROM servis_musteriler WHERE license_code = ?", (license_code,))
    count = c.fetchone()[0] + 1
    musteri_kodu = data.get('musteri_kodu') or f"MUS-{count:04d}"
    
    c.execute('''INSERT INTO servis_musteriler (license_code, musteri_kodu, musteri_tipi, ad_soyad, firma_adi, 
                telefon, telefon2, email, adres, il, ilce, vergi_no, vergi_dairesi, notlar, created_at) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
              (license_code, musteri_kodu, data.get('musteri_tipi', 'Bireysel'), data.get('ad_soyad'), data.get('firma_adi'),
               data.get('telefon'), data.get('telefon2'), data.get('email'), data.get('adres'),
               data.get('il'), data.get('ilce'), data.get('vergi_no'), data.get('vergi_dairesi'), data.get('notlar'), now))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/servis/musteriler/<int:id>', methods=['GET', 'PUT', 'DELETE'])
def servis_musteri_detail(id):
    conn = get_db()
    c = conn.cursor()
    
    if request.method == 'GET':
        c.execute("SELECT * FROM servis_musteriler WHERE id = ?", (id,))
        row = c.fetchone()
        conn.close()
        if row:
            return jsonify(dict(row))
        return jsonify({'success': False})
    
    if request.method == 'DELETE':
        c.execute("DELETE FROM servis_musteriler WHERE id = ?", (id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    
    data = request.json
    c.execute('''UPDATE servis_musteriler SET musteri_kodu = ?, musteri_tipi = ?, ad_soyad = ?, firma_adi = ?,
                telefon = ?, telefon2 = ?, email = ?, adres = ?, il = ?, ilce = ?, 
                vergi_no = ?, vergi_dairesi = ?, notlar = ? WHERE id = ?''',
              (data.get('musteri_kodu'), data.get('musteri_tipi'), data.get('ad_soyad'), data.get('firma_adi'),
               data.get('telefon'), data.get('telefon2'), data.get('email'), data.get('adres'),
               data.get('il'), data.get('ilce'), data.get('vergi_no'), data.get('vergi_dairesi'), data.get('notlar'), id))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

# Cihazlar
@app.route('/api/servis/cihazlar', methods=['GET', 'POST'])
def servis_cihazlar():
    license_code = request.args.get('license_code') or (request.json.get('license_code') if request.json else None)
    musteri_id = request.args.get('musteri_id')
    conn = get_db()
    c = conn.cursor()
    
    if request.method == 'GET':
        if musteri_id:
            c.execute("""SELECT c.*, m.ad_soyad as musteri_adi, m.firma_adi, m.musteri_tipi 
                        FROM servis_cihazlar c 
                        LEFT JOIN servis_musteriler m ON c.musteri_id = m.id 
                        WHERE c.license_code = ? AND c.musteri_id = ? ORDER BY c.id DESC""", (license_code, musteri_id))
        else:
            c.execute("""SELECT c.*, 
                        CASE WHEN m.musteri_tipi = 'Kurumsal' THEN m.firma_adi ELSE m.ad_soyad END as musteri_adi
                        FROM servis_cihazlar c 
                        LEFT JOIN servis_musteriler m ON c.musteri_id = m.id 
                        WHERE c.license_code = ? ORDER BY c.id DESC""", (license_code,))
        rows = c.fetchall()
        conn.close()
        return jsonify([dict(row) for row in rows])
    
    data = request.json
    now = datetime.now().isoformat()
    c.execute('''INSERT INTO servis_cihazlar (license_code, musteri_id, cihaz_tipi, marka, model, seri_no, 
                garanti_bitis, kurulum_tarihi, adres, notlar, created_at) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
              (license_code, data.get('musteri_id'), data.get('cihaz_tipi'), data.get('marka'), data.get('model'),
               data.get('seri_no'), data.get('garanti_bitis'), data.get('kurulum_tarihi'), data.get('adres'), data.get('notlar'), now))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/servis/cihazlar/<int:id>', methods=['GET', 'PUT', 'DELETE'])
def servis_cihaz_detail(id):
    conn = get_db()
    c = conn.cursor()
    
    if request.method == 'GET':
        c.execute("SELECT * FROM servis_cihazlar WHERE id = ?", (id,))
        row = c.fetchone()
        conn.close()
        if row:
            return jsonify(dict(row))
        return jsonify({'success': False})
    
    if request.method == 'DELETE':
        c.execute("DELETE FROM servis_cihazlar WHERE id = ?", (id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    
    data = request.json
    c.execute('''UPDATE servis_cihazlar SET musteri_id = ?, cihaz_tipi = ?, marka = ?, model = ?, seri_no = ?,
                garanti_bitis = ?, kurulum_tarihi = ?, adres = ?, notlar = ? WHERE id = ?''',
              (data.get('musteri_id'), data.get('cihaz_tipi'), data.get('marka'), data.get('model'),
               data.get('seri_no'), data.get('garanti_bitis'), data.get('kurulum_tarihi'), data.get('adres'), data.get('notlar'), id))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

# Teknisyenler
@app.route('/api/servis/teknisyenler', methods=['GET', 'POST'])
def servis_teknisyenler():
    license_code = request.args.get('license_code') or (request.json.get('license_code') if request.json else None)
    conn = get_db()
    c = conn.cursor()
    
    if request.method == 'GET':
        c.execute("SELECT * FROM servis_teknisyenler WHERE license_code = ? ORDER BY id DESC", (license_code,))
        rows = c.fetchall()
        conn.close()
        return jsonify([dict(row) for row in rows])
    
    data = request.json
    now = datetime.now().isoformat()
    c.execute('''INSERT INTO servis_teknisyenler (license_code, ad_soyad, telefon, email, uzmanlik_alani, 
                bolge, maas, ise_giris, durum, notlar, created_at) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
              (license_code, data.get('ad_soyad'), data.get('telefon'), data.get('email'), data.get('uzmanlik_alani'),
               data.get('bolge'), data.get('maas', 0), data.get('ise_giris'), data.get('durum', 'Aktif'), data.get('notlar'), now))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/servis/teknisyenler/<int:id>', methods=['GET', 'PUT', 'DELETE'])
def servis_teknisyen_detail(id):
    conn = get_db()
    c = conn.cursor()
    
    if request.method == 'GET':
        c.execute("SELECT * FROM servis_teknisyenler WHERE id = ?", (id,))
        row = c.fetchone()
        conn.close()
        if row:
            return jsonify(dict(row))
        return jsonify({'success': False})
    
    if request.method == 'DELETE':
        c.execute("DELETE FROM servis_teknisyenler WHERE id = ?", (id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    
    data = request.json
    c.execute('''UPDATE servis_teknisyenler SET ad_soyad = ?, telefon = ?, email = ?, uzmanlik_alani = ?,
                bolge = ?, maas = ?, ise_giris = ?, durum = ?, notlar = ? WHERE id = ?''',
              (data.get('ad_soyad'), data.get('telefon'), data.get('email'), data.get('uzmanlik_alani'),
               data.get('bolge'), data.get('maas', 0), data.get('ise_giris'), data.get('durum'), data.get('notlar'), id))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

# Arızalar (İş Emirleri)
@app.route('/api/servis/arizalar', methods=['GET', 'POST'])
def servis_arizalar():
    license_code = request.args.get('license_code') or (request.json.get('license_code') if request.json else None)
    durum = request.args.get('durum')
    conn = get_db()
    c = conn.cursor()
    
    if request.method == 'GET':
        if durum:
            c.execute("""SELECT a.*, 
                        CASE WHEN m.musteri_tipi = 'Kurumsal' THEN m.firma_adi ELSE m.ad_soyad END as musteri_adi,
                        m.telefon as musteri_telefon,
                        c.cihaz_tipi || ' - ' || c.marka || ' ' || COALESCE(c.model, '') as cihaz_bilgisi
                        FROM servis_arizalar a 
                        LEFT JOIN servis_musteriler m ON a.musteri_id = m.id 
                        LEFT JOIN servis_cihazlar c ON a.cihaz_id = c.id 
                        WHERE a.license_code = ? AND a.durum = ? ORDER BY a.id DESC""", (license_code, durum))
        else:
            c.execute("""SELECT a.*, 
                        CASE WHEN m.musteri_tipi = 'Kurumsal' THEN m.firma_adi ELSE m.ad_soyad END as musteri_adi,
                        m.telefon as musteri_telefon,
                        c.cihaz_tipi || ' - ' || c.marka || ' ' || COALESCE(c.model, '') as cihaz_bilgisi
                        FROM servis_arizalar a 
                        LEFT JOIN servis_musteriler m ON a.musteri_id = m.id 
                        LEFT JOIN servis_cihazlar c ON a.cihaz_id = c.id 
                        WHERE a.license_code = ? ORDER BY 
                        CASE a.durum 
                            WHEN 'Beklemede' THEN 1 
                            WHEN 'Atandı' THEN 2 
                            WHEN 'Yolda' THEN 3 
                            WHEN 'İşlemde' THEN 4 
                            ELSE 5 
                        END, a.id DESC""", (license_code,))
        rows = c.fetchall()
        conn.close()
        return jsonify([dict(row) for row in rows])
    
    data = request.json
    now = datetime.now().isoformat()
    
    # Arıza no oluştur
    c.execute("SELECT COUNT(*) FROM servis_arizalar WHERE license_code = ?", (license_code,))
    count = c.fetchone()[0] + 1
    ariza_no = f"SRV-{datetime.now().strftime('%Y%m')}-{count:04d}"
    
    # Müşteri adını al
    musteri_adi = ''
    if data.get('musteri_id'):
        c.execute("SELECT ad_soyad, firma_adi, musteri_tipi FROM servis_musteriler WHERE id = ?", (data.get('musteri_id'),))
        musteri = c.fetchone()
        if musteri:
            musteri_adi = musteri['firma_adi'] if musteri['musteri_tipi'] == 'Kurumsal' else musteri['ad_soyad']
    
    # Cihaz bilgisini al
    cihaz_bilgisi = ''
    if data.get('cihaz_id'):
        c.execute("SELECT cihaz_tipi, marka, model FROM servis_cihazlar WHERE id = ?", (data.get('cihaz_id'),))
        cihaz = c.fetchone()
        if cihaz:
            cihaz_bilgisi = f"{cihaz['cihaz_tipi']} - {cihaz['marka']} {cihaz['model'] or ''}"
    
    c.execute('''INSERT INTO servis_arizalar (license_code, ariza_no, musteri_id, musteri_adi, cihaz_id, cihaz_bilgisi,
                ariza_tipi, ariza_tanimi, oncelik, randevu_tarihi, randevu_saati, musteri_notu, durum, created_at) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
              (license_code, ariza_no, data.get('musteri_id'), musteri_adi, data.get('cihaz_id'), cihaz_bilgisi,
               data.get('ariza_tipi'), data.get('ariza_tanimi'), data.get('oncelik', 'Normal'),
               data.get('randevu_tarihi'), data.get('randevu_saati'), data.get('musteri_notu'), 'Beklemede', now))
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'ariza_no': ariza_no})

@app.route('/api/servis/arizalar/<int:id>', methods=['GET', 'PUT', 'DELETE'])
def servis_ariza_detail(id):
    conn = get_db()
    c = conn.cursor()
    
    if request.method == 'GET':
        c.execute("""SELECT a.*, 
                    CASE WHEN m.musteri_tipi = 'Kurumsal' THEN m.firma_adi ELSE m.ad_soyad END as musteri_adi,
                    m.telefon as musteri_telefon
                    FROM servis_arizalar a 
                    LEFT JOIN servis_musteriler m ON a.musteri_id = m.id 
                    WHERE a.id = ?""", (id,))
        row = c.fetchone()
        conn.close()
        if row:
            return jsonify(dict(row))
        return jsonify({'success': False})
    
    if request.method == 'DELETE':
        c.execute("DELETE FROM servis_arizalar WHERE id = ?", (id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    
    data = request.json
    c.execute('''UPDATE servis_arizalar SET ariza_tipi = ?, ariza_tanimi = ?, oncelik = ?,
                randevu_tarihi = ?, randevu_saati = ?, musteri_notu = ? WHERE id = ?''',
              (data.get('ariza_tipi'), data.get('ariza_tanimi'), data.get('oncelik'),
               data.get('randevu_tarihi'), data.get('randevu_saati'), data.get('musteri_notu'), id))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/servis/arizalar/<int:id>/ata', methods=['PUT'])
def servis_ariza_ata(id):
    data = request.json
    conn = get_db()
    c = conn.cursor()
    
    # Teknisyen adını al
    teknisyen_adi = ''
    if data.get('teknisyen_id'):
        c.execute("SELECT ad_soyad FROM servis_teknisyenler WHERE id = ?", (data.get('teknisyen_id'),))
        teknisyen = c.fetchone()
        if teknisyen:
            teknisyen_adi = teknisyen['ad_soyad']
    
    c.execute('''UPDATE servis_arizalar SET teknisyen_id = ?, teknisyen_adi = ?, 
                randevu_tarihi = ?, randevu_saati = ?, durum = 'Atandı' WHERE id = ?''',
              (data.get('teknisyen_id'), teknisyen_adi, data.get('randevu_tarihi'), data.get('randevu_saati'), id))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/servis/arizalar/<int:id>/durum', methods=['PUT'])
def servis_ariza_durum(id):
    data = request.json
    durum = data.get('durum')
    conn = get_db()
    c = conn.cursor()
    
    # Durum güncelle
    if durum == 'İşlemde':
        c.execute("UPDATE servis_arizalar SET durum = ?, baslama_tarihi = ? WHERE id = ?", 
                  (durum, datetime.now().isoformat(), id))
    else:
        c.execute("UPDATE servis_arizalar SET durum = ? WHERE id = ?", (durum, id))
    
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/servis/arizalar/<int:id>/tamamla', methods=['PUT'])
def servis_ariza_tamamla(id):
    data = request.json
    conn = get_db()
    c = conn.cursor()
    
    # Parça tutarını hesapla
    parca_tutari = 0
    parcalar = data.get('parcalar', [])
    for p in parcalar:
        miktar = float(p.get('miktar', 0))
        fiyat = float(p.get('birim_fiyat', 0))
        parca_tutari += miktar * fiyat
        
        # Parça kullanım kaydı
        c.execute('''INSERT INTO servis_parca_kullanim (license_code, ariza_id, parca_id, parca_adi, miktar, birim_fiyat, toplam_tutar, created_at)
                    VALUES ((SELECT license_code FROM servis_arizalar WHERE id = ?), ?, ?, 
                    (SELECT parca_adi FROM servis_parcalar WHERE id = ?), ?, ?, ?, ?)''',
                  (id, id, p.get('parca_id'), p.get('parca_id'), miktar, fiyat, miktar * fiyat, datetime.now().isoformat()))
        
        # Stok düş
        c.execute("UPDATE servis_parcalar SET stok_miktari = stok_miktari - ? WHERE id = ?", (miktar, p.get('parca_id')))
    
    iscilik = float(data.get('iscilik_tutari', 0))
    toplam = iscilik + parca_tutari
    
    c.execute('''UPDATE servis_arizalar SET durum = 'Tamamlandı', bitis_tarihi = ?, yapilan_islem = ?,
                teknisyen_notu = ?, iscilik_tutari = ?, parca_tutari = ?, toplam_tutar = ?, 
                garanti_kapsaminda = ? WHERE id = ?''',
              (datetime.now().isoformat(), data.get('yapilan_islem'), data.get('teknisyen_notu'),
               iscilik, parca_tutari, toplam, 1 if data.get('garanti_kapsaminda') else 0, id))
    
    conn.commit()
    conn.close()
    return jsonify({'success': True})

# Parçalar
# Parça Kategorileri
@app.route('/api/servis/parca-kategoriler', methods=['GET', 'POST'])
def servis_parca_kategoriler():
    license_code = request.args.get('license_code') or (request.json.get('license_code') if request.json else None)
    conn = get_db()
    c = conn.cursor()
    
    if request.method == 'GET':
        c.execute("SELECT * FROM servis_parca_kategoriler WHERE license_code = ? ORDER BY varsayilan DESC, kategori_adi", (license_code,))
        rows = c.fetchall()
        conn.close()
        return jsonify([dict(row) for row in rows])
    
    data = request.json
    now = datetime.now().isoformat()
    
    # Aynı kategori var mı kontrol et
    c.execute("SELECT id FROM servis_parca_kategoriler WHERE license_code = ? AND kategori_adi = ?", 
              (license_code, data.get('kategori_adi')))
    existing = c.fetchone()
    if existing:
        conn.close()
        return jsonify({'success': False, 'message': 'Bu kategori zaten mevcut'})
    
    c.execute('''INSERT INTO servis_parca_kategoriler (license_code, kategori_adi, varsayilan, created_at) 
                VALUES (?, ?, ?, ?)''',
              (license_code, data.get('kategori_adi'), data.get('varsayilan', 0), now))
    conn.commit()
    new_id = c.lastrowid
    conn.close()
    return jsonify({'success': True, 'id': new_id})

@app.route('/api/servis/parca-kategoriler/<int:id>', methods=['DELETE'])
def servis_parca_kategori_delete(id):
    conn = get_db()
    c = conn.cursor()
    
    # Varsayılan kategorileri silme
    c.execute("SELECT varsayilan FROM servis_parca_kategoriler WHERE id = ?", (id,))
    row = c.fetchone()
    if row and row['varsayilan'] == 1:
        conn.close()
        return jsonify({'success': False, 'message': 'Varsayılan kategoriler silinemez'})
    
    c.execute("DELETE FROM servis_parca_kategoriler WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/servis/parcalar', methods=['GET', 'POST'])
def servis_parcalar():
    license_code = request.args.get('license_code') or (request.json.get('license_code') if request.json else None)
    conn = get_db()
    c = conn.cursor()
    
    if request.method == 'GET':
        c.execute("SELECT * FROM servis_parcalar WHERE license_code = ? ORDER BY id DESC", (license_code,))
        rows = c.fetchall()
        conn.close()
        return jsonify([dict(row) for row in rows])
    
    data = request.json
    now = datetime.now().isoformat()
    
    # Parça kodu oluştur
    c.execute("SELECT COUNT(*) FROM servis_parcalar WHERE license_code = ?", (license_code,))
    count = c.fetchone()[0] + 1
    parca_kodu = data.get('parca_kodu') or f"PRC-{count:04d}"
    
    c.execute('''INSERT INTO servis_parcalar (license_code, parca_kodu, parca_adi, kategori, marka, uyumlu_modeller,
                birim, stok_miktari, min_stok, alis_fiyati, satis_fiyati, raf_konum, notlar, created_at) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
              (license_code, parca_kodu, data.get('parca_adi'), data.get('kategori'), data.get('marka'),
               data.get('uyumlu_modeller'), data.get('birim', 'Adet'), data.get('stok_miktari', 0),
               data.get('min_stok', 0), data.get('alis_fiyati', 0), data.get('satis_fiyati', 0),
               data.get('raf_konum'), data.get('notlar'), now))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/servis/parcalar/<int:id>', methods=['GET', 'PUT', 'DELETE'])
def servis_parca_detail(id):
    conn = get_db()
    c = conn.cursor()
    
    if request.method == 'GET':
        c.execute("SELECT * FROM servis_parcalar WHERE id = ?", (id,))
        row = c.fetchone()
        conn.close()
        if row:
            return jsonify(dict(row))
        return jsonify({'success': False})
    
    if request.method == 'DELETE':
        c.execute("DELETE FROM servis_parcalar WHERE id = ?", (id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    
    data = request.json
    c.execute('''UPDATE servis_parcalar SET parca_kodu = ?, parca_adi = ?, kategori = ?, marka = ?,
                uyumlu_modeller = ?, stok_miktari = ?, min_stok = ?, alis_fiyati = ?, satis_fiyati = ?,
                raf_konum = ?, notlar = ? WHERE id = ?''',
              (data.get('parca_kodu'), data.get('parca_adi'), data.get('kategori'), data.get('marka'),
               data.get('uyumlu_modeller'), data.get('stok_miktari', 0), data.get('min_stok', 0),
               data.get('alis_fiyati', 0), data.get('satis_fiyati', 0), data.get('raf_konum'), data.get('notlar'), id))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

# Faturalar
@app.route('/api/servis/faturalar', methods=['GET', 'POST'])
def servis_faturalar():
    license_code = request.args.get('license_code') or (request.json.get('license_code') if request.json else None)
    conn = get_db()
    c = conn.cursor()
    
    if request.method == 'GET':
        c.execute("""SELECT f.*, a.ariza_no 
                    FROM servis_faturalar f 
                    LEFT JOIN servis_arizalar a ON f.ariza_id = a.id 
                    WHERE f.license_code = ? ORDER BY f.id DESC""", (license_code,))
        rows = c.fetchall()
        conn.close()
        return jsonify([dict(row) for row in rows])
    
    data = request.json
    now = datetime.now().isoformat()
    
    # Arıza no'yu al
    ariza_no = ''
    if data.get('ariza_id'):
        c.execute("SELECT ariza_no FROM servis_arizalar WHERE id = ?", (data.get('ariza_id'),))
        ariza = c.fetchone()
        if ariza:
            ariza_no = ariza['ariza_no']
    
    c.execute('''INSERT INTO servis_faturalar (license_code, fatura_no, ariza_id, ariza_no, musteri_id, musteri_adi,
                fatura_tarihi, vade_tarihi, iscilik_tutari, parca_tutari, matrah, kdv_orani, kdv_tutari, 
                toplam_tutar, odeme_durumu, notlar, created_at) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
              (license_code, data.get('fatura_no'), data.get('ariza_id'), ariza_no, data.get('musteri_id'),
               data.get('musteri_adi'), data.get('fatura_tarihi'), data.get('vade_tarihi'),
               data.get('iscilik_tutari', 0), data.get('parca_tutari', 0), data.get('matrah', 0),
               data.get('kdv_orani', 20), data.get('kdv_tutari', 0), data.get('toplam_tutar', 0),
               data.get('odeme_durumu', 'Ödenmedi'), data.get('notlar'), now))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/servis/faturalar/<int:id>', methods=['GET', 'PUT', 'DELETE'])
def servis_fatura_detail(id):
    conn = get_db()
    c = conn.cursor()
    
    if request.method == 'GET':
        c.execute("SELECT * FROM servis_faturalar WHERE id = ?", (id,))
        row = c.fetchone()
        conn.close()
        if row:
            return jsonify(dict(row))
        return jsonify({'success': False})
    
    if request.method == 'DELETE':
        c.execute("DELETE FROM servis_faturalar WHERE id = ?", (id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    
    data = request.json
    c.execute('''UPDATE servis_faturalar SET fatura_no = ?, fatura_tarihi = ?, vade_tarihi = ?,
                iscilik_tutari = ?, parca_tutari = ?, matrah = ?, kdv_orani = ?, kdv_tutari = ?,
                toplam_tutar = ?, odeme_durumu = ?, notlar = ? WHERE id = ?''',
              (data.get('fatura_no'), data.get('fatura_tarihi'), data.get('vade_tarihi'),
               data.get('iscilik_tutari', 0), data.get('parca_tutari', 0), data.get('matrah', 0),
               data.get('kdv_orani', 20), data.get('kdv_tutari', 0), data.get('toplam_tutar', 0),
               data.get('odeme_durumu'), data.get('notlar'), id))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

# Kullanıcılar
@app.route('/api/servis/users', methods=['GET', 'POST'])
def servis_users():
    license_code = request.args.get('license_code') or (request.json.get('license_code') if request.json else None)
    conn = get_db()
    c = conn.cursor()
    
    if request.method == 'GET':
        c.execute("SELECT id, license_code, email, ad_soyad, telefon, role, durum, created_at FROM servis_users WHERE license_code = ? ORDER BY id", (license_code,))
        rows = c.fetchall()
        conn.close()
        return jsonify([dict(row) for row in rows])
    
    data = request.json
    now = datetime.now().isoformat()
    c.execute('''INSERT INTO servis_users (license_code, email, password, ad_soyad, telefon, role, durum, yetkiler, created_at) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
              (license_code, data.get('email'), data.get('password', '123456'), data.get('ad_soyad'),
               data.get('telefon'), data.get('role', 'Kullanıcı'), data.get('durum', 'Aktif'), '[]', now))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/servis/users/<int:id>', methods=['PUT', 'DELETE'])
def servis_user_detail(id):
    conn = get_db()
    c = conn.cursor()
    
    if request.method == 'DELETE':
        c.execute("DELETE FROM servis_users WHERE id = ?", (id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    
    data = request.json
    if data.get('password'):
        c.execute("UPDATE servis_users SET email = ?, password = ?, ad_soyad = ?, telefon = ?, role = ?, durum = ? WHERE id = ?",
                  (data.get('email'), data.get('password'), data.get('ad_soyad'), data.get('telefon'), 
                   data.get('role'), data.get('durum'), id))
    else:
        c.execute("UPDATE servis_users SET email = ?, ad_soyad = ?, telefon = ?, role = ?, durum = ? WHERE id = ?",
                  (data.get('email'), data.get('ad_soyad'), data.get('telefon'), data.get('role'), data.get('durum'), id))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

