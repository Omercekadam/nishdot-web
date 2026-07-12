# Nishdot Web Platform - v1.0 (Production)

![Nishdot Logo](docs/design/desktop-homepage.png) *(Dijital Oyun Tasarımı Kulübü - Nishdot)*

İstanbul Nişantaşı Üniversitesi Dijital Oyun Tasarımı Kulübü (Nishdot) için geliştirilen resmi web platformu. Bu proje, kulüp üyelerini bir araya getirmeyi, etkinlikleri duyurmayı ve özellikle Game Jam süreçlerini modern bir arayüzle otomatize etmeyi amaçlayan dinamik, siberpunk esintili bir yönetim sistemidir.

Proje geliştirme süreci başarıyla tamamlanmış ve canlı sunucularda (Ubuntu VDS, Nginx, Gunicorn) yayına alınmıştır.

## 🚀 Öne Çıkan Özellikler

Platform, kullanıcı deneyimini merkeze alan sistemlerle donatıldı ve etkinlik yönetimi yapısı kusursuz bir mimariye oturtuldu:

- **Gelişmiş Etkinlik Yönetimi (Karargah - Dashboard):**
  - Sadece Game Jam'leri değil; Workshop, Buluşma, Seminer ve diğer tüm etkinlikleri tek bir merkezden oluşturma ve yönetme imkanı.
  - **Zengin Metin Editörü (Rich Text Editor):** Etkinlik açıklamalarını HTML bilmeden kalın, italik, liste ve başlık gibi formatlarla şık bir şekilde yazmayı sağlayan Quill.js entegrasyonu.
  - **Dinamik Başvuru Kontrolü:** Başvuruları tek tuşla tüm etkinlik türleri için açıp kapatabilme (`is_applications_open` evrensel mimarisi).
  - **Akıllı Görsel Kırpma:** Etkinlik afişlerini tam 16:9 oranında yüklerken tarayıcı üzerinde canlı kırpma (Cropper.js) özelliği.

- **Otomatize Edilmiş Başvuru ve Mail Sistemi (Yeni):**
  - Game Jam ve etkinlik başvurularını paneller üzerinden "Onaylandı" veya "Reddedildi" olarak işaretleme.
  - **Toplu Mail Gönderimi:** Yönetici panelinden tek tıkla onaylanan ve reddedilen kullanıcılara asenkron olarak (spam'e düşmeyi engelleyecek gecikmelerle) mail gönderimi.
  - Onay maillerine dinamik olarak WhatsApp Topluluk katılım linki ve sosyal medya hesaplarını dahil etme.

- **Kullanıcı Paneli & Profil Yönetimi:**
  - Üyelerin profillerini düzenleyebilecekleri, detaylı bilgilerini (TC, Telefon, Portfolyo vb. sadece gerekli durumlarda) güvenle yönetebilecekleri "Ajan" (Agent) profili stili panel.
  - Yapılan tüm Game Jam ve etkinlik başvurularını listeleyip, takım ve katılım detaylarını (Salt-Okunur modda) inceleyebilecekleri özel arayüz.
  
- **Duyuru Merkezi & Broadcast Sistemi (HQ):**
  - Yönetim kurulunun etkinlikleri ve kulüp haberlerini duyurabileceği gelişmiş yayın merkezi.
  - **Akıllı Hedef Kitle (Target Audience):** Duyuruları "Tüm Üyelere", "Sadece Yönetim Kuruluna" veya "Özel Seçilmiş Kullanıcılara" gönderebilme.
  - **İnteraktif Bildirimler:** Üyelerin okudukları duyuruları panolarından şık bir animasyonla gizleyebildiği (Dismiss) kişiselleştirilmiş deneyim.

- **Güvenlik ve Performans (Production Ready):**
  - **Redis Tabanlı Rate Limiting:** Login ve kayıt formlarında brute-force saldırılarına karşı `django-ratelimit` ve Redis entegrasyonu.
  - Nginx Reverse Proxy üzerinden gerçek istemci IP (X-Real-IP) takibi ile güvenli loglama ve kısıtlama.
  - Güvenli parola yapılandırmaları, ortam değişkenleri (`.env`) izolasyonu ve `DEBUG=False` mimarisi.

- **Siberpunk & Kusursuz Tema (Design Polish):**
  - Tailwind CSS ile tamamen milimetrik olarak hizalanmış pürüzsüz arayüz hatları.
  - Siyah/Çinko mat arka planlar ve "Nish Pembesi" (`#eb596d`) ile neon kontrastı.
  - Modallar, özel kaydırma çubukları (custom scrollbar), empty state (boş durum) uyarıları ve mikro-animasyonlarla zenginleştirilmiş akıcı deneyim.

## 💻 Teknoloji Yığını

- **Backend:** Python 3.12+, Django 5.x
- **Frontend:** Django Templates + Tailwind CSS v4 (Vanilla JS ile SPA hissiyatı)
- **Veritabanı:** SQLite (Geliştirme) / PostgreSQL (Production)
- **Önbellek & Güvenlik:** Redis (Rate Limiting & Caching)
- **Sunucu & Deployment:** Ubuntu VDS, Nginx, Gunicorn, systemd
- **Özel Eklentiler:** Quill.js (Rich Text), Cropper.js (Görsel İşleme)
- **Ortam Yönetimi:** `django-environ` ile güvenli ortam değişkenleri


## 🛠️ Kurulum (Geliştiriciler İçin)

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
*(Geliştirme süreci bittiği için `requirements.txt` dosyasını ana dizinden de kurabilirsiniz, projenin klasör yapısına göre uygun olanı seçiniz.)*

### 4. Frontend (Tailwind CSS) Derleme
Projeyi geliştirirken Tailwind'in anlık derlenmesi için yeni bir terminalde şu komutu çalıştırın:
```bash
npx @tailwindcss/cli -i ./static/css/input.css -o ./static/css/output.css --watch
```

### 5. Ortam Değişkenleri (Environment Variables)
Ana dizindeki `.env.example` dosyasının kopyasını oluşturup adını `.env` yapın ve içindeki bilgileri doldurun:
```bash
cp .env.example .env
```
Geliştirme için `DJANGO_SETTINGS_MODULE=nishdot.settings.development` kullanıldığından emin olun.

### 6. Veritabanı ve Çalıştırma
```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

---

*Made with ❤️ by Nishdot Web Team.*
