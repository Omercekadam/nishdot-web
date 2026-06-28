# Nishdot Web Platform

![Nishdot Logo](docs/design/desktop-homepage.png) *(Tasarım referansı - Figma)*

İstanbul Nişantaşı Üniversitesi Dijital Oyun Tasarımı Kulübü (Nishdot) için geliştirilen resmi web platformu. Bu proje, kulüp üyelerini bir araya getirmeyi, etkinlikleri duyurmayı ve özellikle Game Jam süreçlerini otomatize etmeyi amaçlayan dinamik bir sistemdir.

## 🌟 Temel Özellikler (Planlanan ve Geliştirilen)

- **Rol Tabanlı Yetkilendirme:** Ziyaretçi, Kulüp Üyesi, Yönetim Kurulu ve Yönetici (Admin) rolleri.
- **Game Jam Yönetimi:** Her etkinliğe özel dinamik başvuru formları (özel sorular, dinamik roller).
- **Matchmaker (Takım Eşleştirici):** "Ekip arıyorum" diyen geliştirici ve tasarımcıları, eksik rolleri tamamlayacak şekilde otomatik eşleştiren akıllı algoritma.
- **Topluluk Panosu:** Üyelerin portfolyolarını sergileyebileceği, etkinlik geçmişlerini görebileceği yapı.
- **Güvenli Yönetim Paneli:** Özelleştirilmiş ve brute-force saldırılarına karşı `yonetim/` yoluyla gizlenmiş admin paneli.

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
- Tasarımda katı 8-point spacing scale ve özenli (intentional) UI kararları esastır.

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
Proje dizininde (manage.py ile aynı yerde) bir `.env` dosyası oluşturun. Repodaki `.env.example` dosyasını referans alabilirsiniz. (Veya proje yöneticisinden doğrudan `.env` dosyasını talep edin).

### 5. Veritabanını Hazırlayın
```bash
python manage.py migrate
```

### 6. Yönetici (Superuser) Hesabı Oluşturun
```bash
python manage.py createsuperuser
```
*(Oluşturulan ilk superuser otomatik olarak `admin` rolüne sahip olacaktır).*

### 7. Sunucuyu Çalıştırın
```bash
python manage.py runserver
```

Tarayıcınızda `http://127.0.0.1:8000/yonetim/` adresine giderek admin paneline giriş yapabilirsiniz.

---

> **Not:** Projenin frontend (Tailwind) entegrasyonu Figma tasarımları tamamlandıktan sonra eklenecektir. Şu anki odak sağlam, performanslı ve güvenli bir backend altyapısıdır.
