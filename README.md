# Nishdot Web Platform - Beta Sürümü

![Nishdot Logo](docs/design/desktop-homepage.png) *(Dijital Oyun Tasarımı Kulübü)*

İstanbul Nişantaşı Üniversitesi Dijital Oyun Tasarımı Kulübü (Nishdot) için geliştirilen resmi web platformu. Bu proje, kulüp üyelerini bir araya getirmeyi, etkinlikleri duyurmayı ve özellikle Game Jam süreçlerini modern bir arayüzle otomatize etmeyi amaçlayan dinamik bir sistemdir.

## 🌟 Beta Sürümü Gelişmeleri (Milestone Tamamlandı)

Projenin temel mimarisinin ardından, kullanıcı deneyimini merkeze alan sistemler başarıyla sisteme entegre edildi ve platform "Beta" aşamasına ulaştı:

- **Gelişmiş Kullanıcı Paneli (Dashboard):** 
  - Üyelerin profillerini düzenleyebilecekleri, "Ad, Soyad, TC, Telefon, Portfolyo" gibi detaylı bilgilerini yönetebilecekleri yönetim paneli.
  - Öğrencilerin yaptıkları Game Jam başvurularını listeleyebileceği, detaylarını (Salt-Okunur modda) şık bir pencerede inceleyebileceği özel arayüz.
  
- **Duyuru Merkezi & Broadcast Sistemi (HQ):**
  - Yönetim kurulunun (Admin/Board) etkinlikleri ve kulüp haberlerini duyurabileceği gelişmiş yayın merkezi.
  - **Akıllı Hedef Kitle (Target Audience):** Duyuruları "Tüm Üyelere", "Sadece Yönetim Kuruluna" veya "Özel Seçilmiş Kullanıcılara" gönderebilme esnekliği.
  - **Çift Yönlü İletişim:** Duyuruları hem kullanıcıların site içi panosuna (Dashboard) yansıtma hem de tek tuşla SMTP üzerinden e-posta olarak gönderme özelliği.
  - **İnteraktif Bildirimler:** Üyelerin okudukları duyuruları panolarından şık bir animasyonla "gizleyebildiği" (Dismiss) kişiselleştirilmiş okuma deneyimi.

- **Matchmaker (Takım Eşleştirici) Altyapısı:**
  - Kullanıcıların "Ekip Arıyorum" veya "Ekibim Var" durumlarını takip eden arayüz bileşenleri.
  - Yönetim tarafından bir eşleşme yapıldığında (Takım atandığında) öğrencinin panelinde şık bir bildirimle takım bilgisinin gösterilmesi.

- **Siberpunk & Kusursuz Tema (Design Polish):** 
  - Tailwind CSS JIT ile tamamen milimetrik olarak hizalanmış pürüzsüz arayüz hatları. Modallar, Z-Index hiyerarşileri, karanlık tema kontrastları ve boş durum (Empty State) mesajlarıyla zenginleştirilmiş kullanıcı deneyimi.

## 🚧 Sıradaki Hedefler (Optimizasyon & Deployment)

- **Production Ortamına Geçiş:** Sistemin canlı sunuculara, PostgreSQL ve Nginx/Gunicorn konfigürasyonlarıyla aktarılması.
- **Güvenlik ve Optimizasyon Testleri:** Veritabanı N+1 sorgularının detaylı analizi, önbellekleme (Caching) stratejilerinin uygulanması.
- **Discord Entegrasyonu:** Duyuru merkezinden atılan mesajların doğrudan Discord sunucusuna da Webhook aracılığıyla iletilmesi.

## 🛠 Teknoloji Yığını

- **Backend:** Python 3.12+, Django 6.0.6
- **Frontend:** Django Templates + Tailwind CSS v4 (Monolitik Mimari - SPA yok)
- **Veritabanı:** SQLite (Geliştirme) / PostgreSQL (Production)
- **Ortam Yönetimi:** `django-environ` ile güvenli ortam değişkenleri

## 🏗 Proje Mimarisi ("No Vibe Coding")

Bu proje, **"No Vibe Coding"** manifestosu ile geliştirilmektedir.
- Katı bir mimari disiplin izlenir (PEP 8, İngilizce isimlendirme).
- **Split Settings:** `base.py`, `development.py`, `production.py` olarak ayrılmış ortam ayarları.
- **N+1 Sorgu Yasağı:** View'larda her zaman `select_related` ve `prefetch_related` kullanımı zorunludur.
- Tasarımda katı spacing kuralları, mat karanlık detaylar ve özenli UI/UX kararları esastır.

## 🚀 Kurulum (Geliştiriciler İçin)

### 1. Repoyu Klonlayın
```bash
git clone https://github.com/Omercekadam/nishdot-web.git
cd nishdot-web
```

### 2. Sanal Ortam (Virtual Environment)
```bash
python -m venv venv
# Windows: venv\Scripts\activate
# macOS/Linux: source venv/bin/activate
```

### 3. Bağımlılıkları Yükleyin
```bash
pip install -r requirements/development.txt
```

### 4. Frontend (Tailwind CSS) Derleme
```bash
npx tailwindcss -i ./static/css/input.css -o ./static/css/output.css --watch
```

### 5. Veritabanı ve Çalıştırma
```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```
