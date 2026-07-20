# Nishdot Web Platform - Tam Kapsamlı VDS Deployment Rehberi 🚀

Bu doküman, projeyi bilgisayarınızdan çıkarıp bir **VDS (Sanal Sunucu)** üzerinde canlıya (Production) almak için ihtiyacınız olan **her adımı** sıfırdan, eksiksiz ve en ince ayrıntısına kadar anlatmaktadır.

---

## 🌐 1. ADIM: Domain (Alan Adı) ve VDS Eşleştirmesi

Kullanıcıların `nishdot.com.tr` yazdığında sunucunuza ulaşabilmesi için domaini VDS'e bağlamanız gerekir.

1. Domaini satın aldığınız firmanın (GoDaddy, Turhost, Natro vb.) paneline giriş yapın.
2. **DNS Yönetimi** (veya Gelişmiş DNS Ayarları) sekmesine gidin.
3. Yeni bir **A Kaydı (A Record)** oluşturun:
   - **İsim / Host / Ad:** `@` (veya boş bırakın)
   - **Değer / Hedef / IP Adresi:** VDS Sunucunuzun IP Adresini yazın (Örn: `192.168.1.50`)
   - **TTL:** Varsayılan (veya 1 Saat) bırakabilirsiniz.
4. İkinci bir **A Kaydı** daha oluşturun (www yönlendirmesi için):
   - **İsim / Host / Ad:** `www`
   - **Değer / Hedef:** Yine VDS Sunucunuzun IP Adresi
   
*Not: Bu ayarın tüm dünyaya yayılması bazen 15 dakika, bazen 24 saat sürebilir. Ancak genelde çok kısa sürer.*

---

## 🛡️ 2. ADIM: VDS'e İlk Giriş ve Siber Güvenlik

Sunucunuzu kiraladıktan sonra size bir IP adresi ve "root" şifresi verilir. Bilgisayarınızın terminalini (CMD/PowerShell veya Mac Terminal) açın ve sunucuya bağlanın:

```bash
ssh root@sunucu_ip_adresiniz
```
*(Şifrenizi yazarken ekranda karakterler görünmez, yazıp Enter'a basın.)*

**Sistemi Güncelleyin:**
```bash
apt update && apt upgrade -y
```

**Güvenlik Kalkanlarını (UFW ve Fail2Ban) Kurun:**
Sunucunuzu internetteki botlardan ve saldırılardan korumak hayati önem taşır.
```bash
apt install -y ufw fail2ban
```
Sadece web sitesine (80 ve 443) ve SSH bağlantısına (22) izin verip diğer tüm kapıları kapatın:
```bash
ufw allow 80
ufw allow 443
ufw allow 22
ufw enable
```
`Y` diyerek onaylayın. Fail2Ban'i başlatın (şifre deneyen botları otomatik engeller):
```bash
systemctl enable fail2ban
systemctl start fail2ban
```

---

## 📦 3. ADIM: Gerekli Altyapıların Kurulumu

Projeyi çalıştırmak için Nginx, PostgreSQL, Redis ve Python ortamlarını sunucuya indirin:
```bash
apt install -y python3-pip python3-venv python3-dev libpq-dev postgresql postgresql-contrib nginx curl redis-server git
```

---

## 🗄️ 4. ADIM: PostgreSQL Veritabanı Kurulumu

Django projeniz canlıdayken SQLite yerine çok daha güçlü olan PostgreSQL kullanmalıdır.
PostgreSQL paneline girin:
```bash
su - postgres
psql
```

Açılan SQL konsolunda aşağıdaki komutları sırayla çalıştırın (Lütfen `guclu_bir_sifre_belirleyin` kısmına kendi güvenli şifrenizi yazın):
```sql
CREATE DATABASE nishdot_db;
CREATE USER nishdot_user WITH PASSWORD 'guclu_bir_sifre_belirleyin';
ALTER ROLE nishdot_user SET client_encoding TO 'utf8';
ALTER ROLE nishdot_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE nishdot_user SET timezone TO 'Europe/Istanbul';
GRANT ALL PRIVILEGES ON DATABASE nishdot_db TO nishdot_user;
\q
```
Veritabanından çıkmak için:
```bash
exit
```

**Redis'i (Önbellekleme İçin) Başlatın:**
```bash
systemctl enable redis-server
systemctl start redis-server
```

---

## 📂 5. ADIM: Projeyi Sunucuya Çekme (Gizli/Private Repo Ayarı)

Web sitelerinin sunucuda tutulduğu standart klasör olan `/var/www/` dizinine gidelim:
```bash
cd /var/www
mkdir nishdot-web
```

**ÖNEMLİ: Projeniz Private (Gizli) bir repo olduğu için, sunucuyu GitHub'a tanıtmalıyız.** Bunun en güvenli ve kalıcı yolu SSH Key (Deploy Key) kullanmaktır.

1. Sunucuda yeni bir SSH anahtarı oluşturun:
```bash
ssh-keygen -t ed25519 -C "vds-sunucu"
```
*(Çıkan tüm sorulara hiçbir şey yazmadan doğrudan Enter'a basarak geçin).*

2. Oluşturulan anahtarı ekrana yazdırın ve kopyalayın:
```bash
cat ~/.ssh/id_ed25519.pub
```
*(Ekranda `ssh-ed25519 AAA...` ile başlayan uzun bir metin çıkacak. Hepsini kopyalayın).*

3. GitHub'a gidin:
   - Projenizin sayfasına girin.
   - **Settings** -> sol menüden **Deploy keys** sekmesine tıklayın.
   - **Add deploy key** butonuna basın.
   - Title kısmına "VDS Sunucu", Key kısmına ise kopyaladığınız metni yapıştırın.
   - *Not: Sadece çekme (pull) işlemi yapacağımız için "Allow write access" kutusunu İŞARETLEMEYİN.*
   - "Add key" diyerek kaydedin.

4. Şimdi repoyu güvenle indirebiliriz (HTTPS yerine SSH linkini kullanıyoruz):
```bash
git clone git@github.com:Omercekadam/nishdot-web.git /var/www/nishdot-web
cd /var/www/nishdot-web
```

---

## 🐍 6. ADIM: Python Sanal Ortamı ve Kütüphaneler

Sunucuda Python paketlerinin karışmaması için sanal ortam (venv) oluşturun:
```bash
python3 -m venv venv
source venv/bin/activate
```
Gerekli Django kütüphanelerini yükleyin:
```bash
pip install -r requirements/production.txt
```
> Not: `gunicorn` ve `psycopg[binary]` (PostgreSQL sürücüsü, psycopg **v3**) zaten
> `requirements/production.txt` içinde tanımlıdır — ayrıca yüklemeye gerek yoktur.
> (Eski talimatlardaki `psycopg2-binary` YANLIŞTIR, kullanmayın.)

---

## 🔐 7. ADIM: .env Dosyasının Hazırlanması

Güvenlik bilgilerini (Şifreler, Secret Key vb.) GitHub'a yüklemediğimiz için, sunucuda bunu elle oluşturmalıyız.
```bash
nano .env
```
Önce **FERNET_KEY** (kişisel veri şifreleme anahtarı) üretin ve kopyalayın:
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

İçerisine şu bilgileri yapıştırın (Şifrenizi ve domaininizi kendinize göre güncelleyin):
```env
DJANGO_SECRET_KEY=buraya_rastgele_uzun_karisik_bir_sifre_yazin
FERNET_KEY=yukarida_urettiginiz_fernet_anahtari
DJANGO_DEBUG=False
DJANGO_SETTINGS_MODULE=nishdot.settings.production
DJANGO_ALLOWED_HOSTS=nishdot.com.tr,www.nishdot.com.tr,sunucu_ip_adresiniz
DJANGO_CSRF_TRUSTED_ORIGINS=https://nishdot.com.tr,https://www.nishdot.com.tr
DATABASE_URL=postgres://nishdot_user:guclu_bir_sifre_belirleyin@127.0.0.1:5432/nishdot_db
REDIS_URL=redis://127.0.0.1:6379/1

# SMTP Hesap 1 (Doğrulama mailleri)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=dogrulama_mailiniz@gmail.com
SMTP_PASSWORD=google_uygulama_sifresi

# SMTP Hesap 2 (Game Jam / İletişim)
SMTP2_SERVER=smtp.gmail.com
SMTP2_PORT=587
SMTP2_USERNAME=ikinci_mailiniz@gmail.com
SMTP2_PASSWORD=google_uygulama_sifresi
```
*(Kaydetmek için `CTRL+X` yapın, `Y` tuşuna basın ve `Enter`'a basın.)*

Dosyayı yalnızca sahibinin okuyabilmesi için izinlerini kısıtlayın:
```bash
chmod 600 .env
```

> ⚠️ **FERNET_KEY hakkında kritik uyarı:** Bu anahtar, kayıtlı T.C. Kimlik
> numaralarının şifresini çözmek için gereklidir. **Bir kez belirledikten sonra
> DEĞİŞTİRMEYİN** — değişirse tüm şifreli kayıtlar okunamaz hale gelir. Zorunlu
> bir rotasyon gerekirse, önce eski anahtarla çözüp yenisiyle şifreleyen bir veri
> migration'ı yazılmalıdır.
>
> **Mevcut canlı sistemde ilk kez FERNET_KEY ekliyorsanız:** SECRET_KEY'i bu
> adımda DEĞİŞTİRMEYİN. Önce kodu deploy edip `migrate` çalıştırın (bu, eski
> SECRET_KEY türevli anahtarla şifrelenmiş verileri yeni FERNET_KEY'e taşır),
> ANCAK ondan SONRA SECRET_KEY'i yenileyin.

---

## ⚙️ 8. ADIM: Veritabanını Hazırlama ve Statik Dosyalar

Veritabanı tablolarını oluşturun ve CSS/JS dosyalarını tek bir klasörde toplayın:
```bash
export DJANGO_SETTINGS_MODULE=nishdot.settings.production
python manage.py migrate
python manage.py createsuperuser
```
*(Superuser oluştururken sizden sitenin yönetim paneli için admin kullanıcı adı ve şifre isteyecektir.)*

Şimdi statik dosyaları toplayın:
```bash
python manage.py collectstatic --noinput
```

---

## 🚀 9. ADIM: Gunicorn Servisi (7/24 Çalışma)

Projenin terminal kapansa bile arka planda sonsuza kadar çalışması için Gunicorn servisi oluşturmalıyız.
```bash
nano /etc/systemd/system/gunicorn.service
```
Önce web uygulamasını çalıştıracak **ayrıcalıksız bir kullanıcı** oluşturun.
Uygulama `root` olarak çalışmamalı — bir güvenlik açığı istismar edilirse
saldırgan doğrudan tüm sunucuya root erişimi kazanır:
```bash
adduser --system --group --no-create-home nishdot
chown -R nishdot:www-data /var/www/nishdot-web
```

İçerisine yapıştırın:
```ini
[Unit]
Description=gunicorn daemon for Nishdot
After=network.target

[Service]
User=nishdot
Group=www-data
WorkingDirectory=/var/www/nishdot-web
Environment="DJANGO_SETTINGS_MODULE=nishdot.settings.production"
ExecStart=/var/www/nishdot-web/venv/bin/gunicorn --access-logfile - --workers 3 --bind unix:/run/gunicorn.sock nishdot.wsgi:application

[Install]
WantedBy=multi-user.target
```
*(Kaydedip çıkın: CTRL+X, Y, Enter)*

> Not: `nishdot` kullanıcısının `.env` dosyasını okuyabildiğinden emin olun
> (`chown nishdot:www-data .env` yeterlidir; izin `chmod 600` kalabilir).

Servisi başlatın:
```bash
systemctl start gunicorn
systemctl enable gunicorn
```

---

## 🌍 10. ADIM: Nginx (Web Sunucusu) Konfigürasyonu

Dış dünyadan 80 portuna (İnternete) gelen istekleri alıp Django (Gunicorn) sistemine iletecek köprüyü kuruyoruz.
```bash
nano /etc/nginx/sites-available/nishdot
```
İçerisine yapıştırın (Domainleri güncelleyin):
```nginx
server {
    listen 80;
    server_name nishdot.com.tr www.nishdot.com.tr;

    location = /favicon.ico { access_log off; log_not_found off; }
    
    # CSS, JS ve Resim dosyalarını Nginx üzerinden çok hızlı sunuyoruz
    location /static/ {
        root /var/www/nishdot-web;
        expires 30d;
        add_header Cache-Control "public, max-age=2592000";
    }

    location /media/ {
        root /var/www/nishdot-web;
        expires 30d;
        add_header Cache-Control "public, max-age=2592000";
    }

    location / {
        include proxy_params;
        # Django'nun HTTPS'i doğru algılaması için ŞART (SECURE_PROXY_SSL_HEADER).
        # Bu başlık olmadan sonsuz yönlendirme (redirect loop) yaşanır.
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Host $host;
        proxy_pass http://unix:/run/gunicorn.sock;
    }
}
```
> Not: Ubuntu'nun varsayılan `proxy_params` dosyası genelde `X-Forwarded-Proto`
> başlığını zaten içerir; yukarıda açıkça belirtmek her durumda güvenlidir.
*(Kaydedip çıkın: CTRL+X, Y, Enter)*

Nginx'i aktifleştirin ve yeniden başlatın:
```bash
ln -s /etc/nginx/sites-available/nishdot /etc/nginx/sites-enabled
rm /etc/nginx/sites-enabled/default
nginx -t
systemctl restart nginx
```

---

## 🔒 11. ADIM: Ücretsiz SSL Sertifikası (HTTPS)

Kullanıcıların siteye "Güvenli Değil" uyarısı olmadan girebilmesi için Let's Encrypt kuralım:
```bash
apt install -y python3-certbot-nginx
certbot --nginx -d nishdot.com.tr -d www.nishdot.com.tr
```
*(Size e-posta soracaktır, e-postanızı girin, şartları kabul edin (Y). Otomatik olarak Nginx ayarlarınızı güncelleyecek ve sitenizi HTTPS yapacaktır.)*

**Tebrikler! Sistem şu an tamamen yayında!** 🎉

---
---

## 🔄 GELECEKTE NASIL GÜNCELLEME (UPDATE) YAPACAĞIM?

Sistem canlıya alındıktan haftalar veya aylar sonra bilgisayarınızda yeni bir kod yazdınız, tasarımı değiştirdiniz ve GitHub'a yüklediniz. Bunu VDS'teki canlı siteye yansıtmak için **sadece şu adımları** uygulamanız yeterlidir:

**1. Sunucuya Bağlanın ve Klasöre Gidin:**
```bash
ssh root@sunucu_ip_adresiniz
cd /var/www/nishdot-web
```

**2. Yeni Kodları GitHub'dan Çekin:**
```bash
git pull origin main
```

**3. Sanal Ortamı Aktif Edin:**
```bash
source venv/bin/activate
```

**4. (Sadece Yeni Kütüphane Varsa) Kütüphaneleri Güncelleyin:**
Eğer `requirements.txt` dosyasına yeni bir paket eklediyseniz:
```bash
pip install -r requirements/production.txt
```

**5. Veritabanı ve CSS/JS Güncellemesi:**
Eğer `models.py` içinde değişiklik yaptıysanız (yeni bir tablo, sütun eklendiyse) veya Tailwind CSS derlediyseniz:
```bash
export DJANGO_SETTINGS_MODULE=nishdot.settings.production
python manage.py migrate
python manage.py collectstatic --noinput
```

**6. Son Olarak Gunicorn'u Yeniden Başlatın:**
Yazdığınız yeni Python kodlarının algılanması için servisi yeniden başlatmak şarttır:
```bash
systemctl restart gunicorn
```

İşte bu kadar! Siteniz yeni sürümüyle saniyeler içerisinde çalışmaya devam edecektir.

---

## ⚠️ BU GÜVENLİK GÜNCELLEMESİNİ İLK KEZ DEPLOY EDERKEN (tek seferlik)

Bu sürümde bağımlılık, ayar ve şifreleme değişiklikleri var. Sunucuda **sırayla**:

```bash
cd /var/www/nishdot-web
git pull origin main
source venv/bin/activate

# 1) Yeni bağımlılıklar (nh3, cryptography)
pip install -r requirements/production.txt

# 2) .env'e FERNET_KEY ve (varsa) DJANGO_CSRF_TRUSTED_ORIGINS ekleyin
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
nano .env          # FERNET_KEY=... satırını ekleyin
chmod 600 .env

# 3) Migrasyonlar — bu adım mevcut T.C. Kimlik verilerini yeni anahtara taşır
export DJANGO_SETTINGS_MODULE=nishdot.settings.production
python manage.py migrate
python manage.py collectstatic --noinput

# 4) Nginx'e X-Forwarded-Proto başlığını ekleyip (10. ADIM) test edin
nginx -t && systemctl reload nginx

# 5) Gunicorn'u ayrıcalıksız kullanıcıya taşıyın (9. ADIM) ve yeniden başlatın
systemctl daemon-reload
systemctl restart gunicorn

# 6) HER ŞEY ÇALIŞTIKTAN SONRA sırları yenileyin:
#    - DJANGO_SECRET_KEY (dikkat: tüm oturumlar kapanır)
#    - İki Gmail uygulama şifresi (Google Hesabı > Uygulama Şifreleri)
#    Ardından: systemctl restart gunicorn
```

> Dağıtımdan önce güvenlik ayarlarını doğrulamak için:
> `python manage.py check --deploy` çalıştırın (0 uyarı beklenir).
