# Nishdot Web Platform - Sunucu Kurulum ve Deployment Rehberi

Bu döküman, projenin canlı sunucuya (VPS) yüklenmesi sırasında sıfırdan yapılacak olan kurulum adımlarını, siber güvenlik önlemlerini ve güncelleme adımlarını içerir.

## 0. Alan Adı (Domain) Yönlendirmesi
`nishdot.com.tr` alan adınızı satın aldığınız firmanın (Örn: GoDaddy, Turhost vb.) DNS ayarlarına girerek sunucunuza yönlendirmeniz gerekir:
1. DNS Yönetimi sayfasına gidin.
2. Yeni bir **A Kaydı (A Record)** oluşturun.
3. İsim/Host kısmına `@` veya boş bırakın, Hedef/Değer kısmına **VPS Sunucunuzun IP Adresini** yazın.
4. Aynı şekilde İsim/Host kısmına `www` yazarak bir A kaydı daha oluşturun ve yine sunucu IP adresini yazın.
*(Not: DNS yönlendirmelerinin tüm dünyada aktif olması birkaç saat sürebilir.)*

## 1. Sunucu Hazırlığı ve Siber Güvenlik (İlk Giriş)
Sunucuya SSH ile bağlandıktan sonra sistem paketlerini güncelleyin:
```bash
sudo apt update && sudo apt upgrade -y
```

**Siber Güvenlik Önlemleri:**
Sistemi hackerlara ve botlara karşı korumak için Güvenlik Duvarı (UFW) ve Fail2Ban kurun:
```bash
sudo apt install -y ufw fail2ban
# Sadece HTTP, HTTPS ve SSH bağlantılarına izin verin
sudo ufw allow 80
sudo ufw allow 443
sudo ufw allow 22
sudo ufw enable
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```
*(Güvenlik duvarı artık gereksiz tüm portları kapattı, Fail2Ban ise şifre deneyen botları banlayacaktır.)*

Gerekli olan temel web bileşenlerini kurun:
```bash
sudo apt install -y python3-pip python3-venv python3-dev libpq-dev postgresql postgresql-contrib nginx curl redis-server git
```

## 2. PostgreSQL Veritabanı Kurulumu
Django'nun verilerini tutacağı canlı veritabanını oluşturun:
```bash
sudo -u postgres psql

# Çıkan ekranda şu SQL komutlarını çalıştırın (Şifreyi kendi güvenli şifrenizle değiştirin):
CREATE DATABASE nishdot_db;
CREATE USER nishdot_user WITH PASSWORD 'guclu_bir_sifre';
ALTER ROLE nishdot_user SET client_encoding TO 'utf8';
ALTER ROLE nishdot_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE nishdot_user SET timezone TO 'Europe/Istanbul';
GRANT ALL PRIVILEGES ON DATABASE nishdot_db TO nishdot_user;
\q
```

## 3. Redis Kurulumu (Önbellekleme İçin)
Redis zaten yukarıdaki adımda kuruldu. Sadece çalıştığından emin olun:
```bash
sudo systemctl enable redis-server
sudo systemctl start redis-server
```

## 4. Projeyi Sunucuya Çekme
```bash
cd /var/www
sudo mkdir nishdot-web
sudo chown $USER:$USER nishdot-web
git clone https://github.com/Omercekadam/nishdot-web.git /var/www/nishdot-web
cd /var/www/nishdot-web
```

## 5. Sanal Ortam ve Kütüphanelerin Kurulumu
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements/production.txt
```

## 6. Çevre Değişkenleri (.env)
Proje kök dizininde nano ile `.env` dosyası oluşturun:
```bash
nano .env
```
İçine şu bilgileri girin (Domain bilginizi buraya ekleyin):
```env
DJANGO_SECRET_KEY=sizin_rastgele_uretilen_guvenli_anahtariniz
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=nishdot.com.tr,www.nishdot.com.tr,sunucu_ip_adresi
DATABASE_URL=postgres://nishdot_user:guclu_bir_sifre@127.0.0.1:5432/nishdot_db
REDIS_URL=redis://127.0.0.1:6379/1
```

## 7. Migration ve Static Dosyaları Toplama
```bash
export DJANGO_SETTINGS_MODULE=nishdot.settings.production
python manage.py migrate
python manage.py createsuperuser
python manage.py collectstatic --noinput
```

## 8. Gunicorn Service (Arka Plan Servisi)
Gunicorn'un sunucu her açıldığında otomatik çalışması için bir servis dosyası oluşturun:
```bash
sudo nano /etc/systemd/system/gunicorn.service
```
İçerisine şu ayarları yapıştırın:
```ini
[Unit]
Description=gunicorn daemon for Nishdot
After=network.target

[Service]
User=root
Group=www-data
WorkingDirectory=/var/www/nishdot-web
Environment="DJANGO_SETTINGS_MODULE=nishdot.settings.production"
ExecStart=/var/www/nishdot-web/venv/bin/gunicorn --access-logfile - --workers 5 --bind unix:/run/gunicorn.sock nishdot.wsgi:application

[Install]
WantedBy=multi-user.target
```
Servisi başlatın:
```bash
sudo systemctl start gunicorn
sudo systemctl enable gunicorn
```

## 9. Nginx Konfigürasyonu (Domain Ayarı)
```bash
sudo nano /etc/nginx/sites-available/nishdot
```
Şu konfigürasyonu yapıştırın (`server_name` kısmında domain yazmaktadır):
```nginx
server {
    listen 80;
    server_name nishdot.com.tr www.nishdot.com.tr;

    location = /favicon.ico { access_log off; log_not_found off; }
    
    # Statik Dosyalar (CSS, JS) ve Medya (Resimler) - 30 Gün Cache!
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
        proxy_pass http://unix:/run/gunicorn.sock;
    }
}
```

Nginx'i aktifleştirin ve yeniden başlatın:
```bash
sudo ln -s /etc/nginx/sites-available/nishdot /etc/nginx/sites-enabled
sudo rm /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx
```

Sistem artık çalışmaktadır! SSL/TLS sertifikası (HTTPS) için sunucuda şu komutu çalıştırarak ücretsiz Let's Encrypt kurulumu yapabilirsiniz:
```bash
sudo apt install python3-certbot-nginx
sudo certbot --nginx -d nishdot.com.tr -d www.nishdot.com.tr
```

---

## 🔄 Sistemi Güncelleme (Update Rehberi)
Gelecekte kodda bir değişiklik yaptığınızda ve bu güncellemeyi canlı sunucuya aktarmak istediğinizde şu adımları izlemelisiniz:

1. Sunucuya SSH ile bağlanın ve proje klasörüne gidin:
```bash
cd /var/www/nishdot-web
```

2. GitHub'dan yeni kodları çekin:
```bash
git pull origin main
```

3. Sanal ortamı aktif edip yeni kütüphane varsa kurun:
```bash
source venv/bin/activate
pip install -r requirements/production.txt
```

4. Veritabanında (Migration) veya CSS dosyalarında (Static) bir değişiklik varsa güncelleyin:
```bash
export DJANGO_SETTINGS_MODULE=nishdot.settings.production
python manage.py migrate
python manage.py collectstatic --noinput
```

5. Gunicorn servisini yeniden başlatarak değişikliklerin aktif olmasını sağlayın:
```bash
sudo systemctl restart gunicorn
```
*(Bitti! Güncellemeleriniz anında yayına alınmıştır.)*
