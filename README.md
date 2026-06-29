# Nishdot Web Platform

![Nishdot Logo](docs/design/desktop-homepage.png) *(Dijital Oyun Tasarımı Kulübü)*

İstanbul Nişantaşı Üniversitesi Dijital Oyun Tasarımı Kulübü (Nishdot) için geliştirilen resmi web platformu. Bu proje, kulüp üyelerini bir araya getirmeyi, etkinlikleri duyurmayı ve özellikle Game Jam süreçlerini modern bir arayüzle otomatize etmeyi amaçlayan dinamik bir sistemdir.

## 🌟 Güncel Durum ve Geliştirilen Özellikler (Faz 4 Tamamlandı)

Projenin temel mimarisi, veritabanı altyapısı ve frontend UI/UX entegrasyonları büyük ölçüde tamamlanmıştır:

- **Siberpunk & Karanlık Tema (Dark Mode):** Tamamen Tailwind CSS JIT derleyicisi ile geliştirilen, yüksek kaliteli UI/UX detaylarına sahip "premium" tasarım.
- **Dinamik Etkinlik Sistemi:** Admin panelinden yönetilebilen, ana sayfada listelenen etkinlik ve Game Jam altyapısı.
- **Akıllı Başvuru Sihirbazı (Apply Wizard):** 
  - 3 adımlı, JavaScript destekli akıcı form deneyimi.
  - T.C. Kimlik ve E-Posta bazlı "Mükerrer Başvuru (Unique Constraint)" koruma mekanizmaları.
  - Özel form doğrulama (HTML5 & JS) ve güvenlik önlemleri.
- **Güvenli Yönetim Paneli:** Brute-force saldırılarına karşı standart yoldan gizlenmiş, `/yonetim/` adresi üzerinden erişilen yetkili paneli.

## 🚧 Sıradaki Hedefler (Yol Haritası)

- **Faz 5 - Kullanıcı Sistemi (Auth & Dashboard):** Öğrencilerin .edu.tr uzantılı mail adresleriyle kayıt olabileceği, kendi başvurularını takip edebileceği Profil Ekranı.
- **Faz 6 - Matchmaker (Takım Eşleştirici):** "Ekip arıyorum" diyen geliştirici ve tasarımcıları, eksik rolleri tamamlayacak şekilde otomatik eşleştiren akıllı algoritma.
- **Faz 7 - Kurumsal Sayfalar:** Ana sayfadaki eksik bilgi alanlarının (About Us, Contact Us) tamamlanması.

## 🛠 Teknoloji Yığını

- **Backend:** Python 3.12+, Django 6.0.6
- **Frontend:** Django Templates + Tailwind CSS (Monolitik Mimari - SPA yok)
- **Veritabanı:** SQLite (Geliştirme) / PostgreSQL (Production)
- **Ortam Yönetimi:** `django-environ` ile güvenli ortam değişkenleri

## 🏗 Proje Mimarisi ("No Vibe Coding")

Bu proje, **"No Vibe Coding"** manifestosu ile geliştirilmektedir.
- Katı bir mimari disiplin izlenir (PEP 8, İngilizce isimlendirme).
- **Split Settings:** `base.py`, `development.py`, `production.py` olarak ayrılmış ortam ayarları.
- **N+1 Sorgu Yasağı:** View'larda her zaman `select_related` ve `prefetch_related` kullanımı zorunludur.
- Tasarımda katı spacing kuralları, neon detaylar ve özenli UI/UX kararları esastır.

## 🚀 Kurulum (Geliştiriciler İçin)

Projeyi bilgisayarınızda çalıştırmak için aşağıdaki adımları izleyin:

### 1. Repoyu Klonlayın
```bash
git clone https://github.com/KULLANICI_ADINIZ/nishdot-web.git
cd nishdot-web
```

### 2. Sanal Ortam (Virtual Environment) Oluşturun
```bash
python -m venv venv
```

**Sanal ortamı aktif edin:**
- Windows: `venv\Scripts\activate`
- macOS/Linux: `source venv/bin/activate`

### 3. Bağımlılıkları Yükleyin
```bash
pip install -r requirements/development.txt
```

### 4. Ortam Değişkenlerini Ayarlayın
Proje dizininde (manage.py ile aynı yerde) bir `.env` dosyası oluşturun. Repodaki `.env.example` dosyasını referans alabilirsiniz.

### 5. Frontend (Tailwind CSS) Derleme
```bash
npx tailwindcss -i ./static/css/input.css -o ./static/css/output.css --watch
```

### 6. Veritabanını Hazırlayın
```bash
python manage.py migrate
```

### 7. Yönetici Hesabı Oluşturun ve Sunucuyu Çalıştırın
```bash
python manage.py createsuperuser
python manage.py runserver
```

Tarayıcınızda `http://127.0.0.1:8000/yonetim/` adresine giderek admin paneline giriş yapabilirsiniz.
