# Nishdot Web — Kod Denetim Raporu

**Tarih:** 19 Temmuz 2026
**Kapsam:** Tüm kod tabanı (backend, frontend, deployment dokümantasyonu)
**Ortam:** Django 6.0 + PostgreSQL + Redis + Gunicorn + Nginx (Ubuntu VDS), canlı: nishdot.com.tr

> ⚠️ **Not:** Bu rapor güvenlik açıklarının konumlarını içerir. Repo herkese açıksa (public) bu dosyayı commit etmeyin; private ise sorun yok.

---

## Genel Değerlendirme

Proje sağlam bir temele sahip: ayarlar base/development/production olarak ayrılmış, production'da `DEBUG=False`, HSTS, güvenli cookie'ler ve SSL yönlendirmesi aktif; sırlar `.env`'den okunuyor ve `.env`, `db.sqlite3`, `media/` doğru şekilde gitignore'da; hiçbir yerde `@csrf_exempt` yok ve tüm formlarda CSRF koruması eksiksiz; admin paneli `/yonetim/` altına taşınmış; form tabanlı görünümlerde rate limit var. Deployment dokümanı da (Nginx + Gunicorn + certbot + UFW/fail2ban) genel olarak bilinçli yazılmış.

Bununla birlikte **7 kritik güvenlik bulgusu**, **8 fonksiyonel bug** ve çok sayıda kalite/SEO/performans iyileştirme fırsatı tespit edildi. Aşağıda önem sırasına göre listelenmiştir.

---

## 🔴 KRİTİK — Güvenlik (öncelik: hemen)

### 1. E-posta doğrulama tamamen atlatılabiliyor
- **Konum:** `users/urls.py:22` → `users/views.py:39-43` (`UserRegisterView.form_valid`)
- **Sorun:** Canlı arayüz OTP'li API akışını (`/hesap/api/register/` + `/hesap/api/verify/`) kullanıyor, ancak eski form tabanlı kayıt görünümü hâlâ `/auth/register/` adresinde yayında. Bu görünüm `form.save()` sonrası **OTP doğrulaması istemeden** kullanıcıyı oluşturup anında `login()` ediyor. Doğrudan form POST'u atan biri, `is_verified=False` olmasına rağmen oturum açmış hesap elde eder — tüm doğrulama kapısı boşa düşer.
- **Çözüm:** Rotayı kaldırın ya da `form_valid` içinde login yapmayıp OTP doğrulama adımına yönlendirin. Ayrıca `LoginRequiredMixin` kullanan yerlerde `is_verified` kontrolünün de yapıldığını gözden geçirin.

### 2. OTP API'lerinde rate limit ve deneme sınırı yok
- **Konum:** `users/api.py` — `register_api_view` (60), `verify_otp_api_view` (152), `resend_otp_api_view` (126)
- **Sorun:** Form görünümlerinde `@ratelimit` varken API görünümlerinde hiç yok. 6 haneli kod (`random.randint(100000, 999999)`) düz metin karşılaştırılıyor, deneme sayacı/kilit yok → ~10⁶ ihtimal brute-force edilebilir. `resend` ucu sınırsız → istenen adrese **mail bombing** yapılabilir. Ayrıca "Kullanıcı bulunamadı" / "zaten doğrulanmış" gibi farklı mesajlar **kullanıcı enumeration**'a izin veriyor.
- **Çözüm:** Üç uca da `@ratelimit` ekleyin (ör. verify: 5/15dk per user+IP, resend: 3/saat), kullanıcı başına deneme sayacı + geçici kilit tutun (Redis uygun), hata mesajlarını tek tipleştirin. OTP'yi hash'leyerek saklamak da iyi pratik.

### 3. Misafirlerin T.C. Kimlik numaraları düz metin saklanıyor (KVKK)
- **Konum:** `events/models.py:211` (`EventApplication.national_id`), yazan yer `events/views.py:140`
- **Sorun:** `JamApplication` TC kimlik numarasını Fernet (AES) ile şifrelerken (`jams/models.py:132-140`), `EventApplication` aynı veriyi **şifresiz** kaydediyor. Ek olarak her iki modeldeki tekillik hash'i **tuzsuz SHA-256**: 11 haneli, checksum'lı bir sayı uzayı için saniyeler içinde geri çevrilebilir — DB sızarsa hash'ler de kimlik numarasını ifşa eder.
- **Çözüm:** `EventApplication.save()`'e JamApplication ile aynı şifrelemeyi ekleyin + mevcut kayıtları şifreleyen bir data migration yazın. Hash'i HMAC-SHA256 (gizli anahtarla) yapın.

### 4. Şifreleme anahtarı SECRET_KEY'den türetiliyor
- **Konum:** `jams/models.py:8-11` (`get_fernet`)
- **Sorun:** Fernet anahtarı `settings.SECRET_KEY`'den türetiliyor. SECRET_KEY'i döndürdüğünüz an **tüm şifreli TC numaraları kalıcı olarak çözülemez** hale gelir. Ayrıca `save()` yalnızca `len(national_id) == 11` ise şifreliyor — bozuk bir değer düz metin kaydedilir (`jams/models.py:133`).
- **Çözüm:** `.env`'e bağımsız bir `FERNET_KEY` ekleyin; eski anahtarla çözüp yenisiyle şifreleyen bir re-encrypt migration yazın. Bu yapılmadan SECRET_KEY rotasyonu YAPMAYIN (sıralama için yol haritasına bakın). Uzunluk kontrolünü de "11 değilse reddet" şeklinde değiştirin.

### 5. Sır yönetimi ve rotasyon ihtiyacı
- **Konum:** `.env` (repoya dahil değil — doğru)
- **Sorun:** SECRET_KEY ve iki Gmail uygulama şifresi düz metin duruyor; bu denetim sırasında dosya içeriği inceleme araçlarına da göründü. İhtiyatlılık gereği rotasyon önerilir.
- **Çözüm (sıralı):** (1) Bulgu #4'teki FERNET_KEY ayrıştırmasını tamamlayın → (2) SECRET_KEY'i yenileyin (not: tüm oturumlar ve şifre sıfırlama linkleri geçersiz olur — bilinçli yapın) → (3) iki Gmail uygulama şifresini Google hesabından yenileyin → (4) sunucuda `chmod 600 .env`.

### 6. Production ayar eksikleri (Nginx arkası)
- **Konum:** `nishdot/settings/production.py`
- **Sorun:**
  - `SECURE_PROXY_SSL_HEADER` tanımlı değil. SSL Nginx'te sonlanıp Gunicorn'a unix soketten düz HTTP gittiği için `request.is_secure()` False döner; `SECURE_SSL_REDIRECT=True` ile birleşince sonsuz yönlendirme döngüsü riski doğar (şu an site çalışıyorsa Nginx config'i telafi ediyor olabilir ama ayar eksik).
  - `CSRF_TRUSTED_ORIGINS` tanımlı değil (Django 4+ HTTPS POST'larda gerekebilir).
  - `deployment_instructions.md:201`: Gunicorn systemd servisi **`User=root`** ile çalışıyor. Uygulamada bir açık istismar edilirse saldırgan doğrudan root olur.
- **Çözüm:** `SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")` ve `CSRF_TRUSTED_ORIGINS = ["https://nishdot.com.tr", "https://www.nishdot.com.tr"]` ekleyin; Nginx'te `proxy_set_header X-Forwarded-Proto $scheme;` olduğundan emin olun. Sunucuda ayrıcalıksız bir `nishdot` kullanıcısı oluşturup servisi ona taşıyın.

### 7. Depolama silme ucunda path-traversal ön ek atlatması
- **Konum:** `dashboard/views.py:1020-1023` (`api_storage_delete`)
- **Sorun:** `full_path.startswith(os.path.abspath(MEDIA_ROOT))` kontrolü, `media` ile başlayan kardeş dizinler için de (`media_backup/…` gibi) True döner. Superuser'a kısıtlı olsa da dosya + DB kaydı silen bir uç.
- **Çözüm:** `os.path.commonpath([full_path, MEDIA_ROOT]) == MEDIA_ROOT` karşılaştırması (veya `pathlib` `Path.is_relative_to`) kullanın.

---

## 🟠 BUG — Fonksiyonel hatalar

### 8. Jam başvurusunda `national_id` eksikse 500 hatası
- **Konum:** `events/views.py:68-69`
- `national_id = request.POST.get('national_id')` None dönebilir; `national_id.encode('utf-8')` `try` bloğundan **önce** çalıştığı için `AttributeError` → yakalanmamış 500. Null-check ekleyin / hash'i try içine alın.

### 9. Çekiliş katılımı GET isteğiyle veritabanına yazıyor
- **Konum:** `events/views.py:165` (`RaffleJoinView.get_context_data` içindeki `get_or_create`)
- WhatsApp/Discord link önizlemesi, tarayıcı prefetch'i veya bir crawler bile kullanıcıyı çekilişe "katılmış" yapabilir. Katılımı onay butonlu bir POST'a taşıyın (GET yalnızca bilgi sayfası göstersin).

### 10. Taslak/iptal edilmiş etkinlikler herkese açık
- **Konum:** `events/views.py:6-9` (`EventDetailView`)
- `get_queryset` status filtrelemiyor; slug'ı bilen/tahmin eden herkes draft etkinliği görür. `get_queryset`'te yayında olmayanları staff dışına kapatın.

### 11. Font Awesome hiç yüklenmiyor — dashboard ikonları kırık
- **Konum:** `templates/dashboard/*` genelinde ve `templates/events/event_detail.html:183` — `fas fa-*` sınıfları kullanılıyor ama hiçbir şablonda Font Awesome `<link>`/kit yok.
- Tüm yönetim panelinde ve etkinlik galerisinde ikonlar boş görünüyor. Ya FA'yı `dashboard/base.html`'e ekleyin ya da (daha iyisi, CDN bağımlılığı olmadan) inline SVG'ye geçin.

### 12. Görsel sıkıştırmada yanlış dosya boyutu
- **Konum:** `events/models.py:85, 184, 274`
- `InMemoryUploadedFile`'a `sys.getsizeof(output)` veriliyor — bu Python nesnesinin bellek boyutudur, dosyanın byte uzunluğu değil. `output.getbuffer().nbytes` kullanın.

### 13. Kırılgan slug üretimi
- **Konum:** `dashboard/views.py:90`
- `slugify(title) + f"-{Event.objects.count()}"`: `count()` silmelerden sonra tekrar eder (yarış durumu + çakışma → IntegrityError generic hataya yutulur, satır 116). Tamamı Türkçe karakterli bir başlık `slugify`'da boşalıp `-3` gibi bir slug üretebilir. `slugify(title, allow_unicode=False)` + çakışmada rastgele sonek döngüsü kullanın.

### 14. `api_update_task_status` gelen değeri doğrulamıyor
- **Konum:** `dashboard/views.py:313-322`
- Keyfî `new_status` yazılıyor (oysa `update_application_status:675` choices'a karşı doğruluyor). Choices doğrulaması ekleyin.

### 15. Mail gönderimi request döngüsünü bloke ediyor / güvenilmez
- **Konum:** `pages/api.py:115-118` ("arka planda" yorumuna rağmen `async_to_sync` ile senkron 2 SMTP el sıkışması), `dashboard/views.py:546-547` (daemon olmayan thread), `775`
- Her iletişim formu gönderimi bir Gunicorn worker'ı SMTP süresince kilitliyor; thread'li gönderimlerde worker yeniden başlarsa mail sessizce kaybolur. Kalıcı çözüm: hafif bir kuyruk (Redis zaten kurulu → `django-rq` pratik bir seçim). Kısa vadede: thread'lere `daemon=True` + loglama.

---

## 🟡 ORTA — Güvenlik/İçerik

### 16. `|safe` ile ham HTML basılıyor (stored-XSS yüzeyi)
- **Konum:** `templates/events/event_detail.html:168` (`event.description|safe`), `templates/pages/legal_document.html:59` (`document.content|safe`)
- Quill'den gelen HTML sanitizasyonsuz. BOARD rolündeki bir kullanıcı (veya ele geçirilmiş bir staff hesabı) herkese açık sayfaya `<script>` enjekte edebilir. Kaydetme anında `nh3` (Rust tabanlı, hızlı) veya `bleach` ile beyaz-liste sanitizasyonu yapın.

### 17. CDN scriptlerinde SRI yok
- Quill (`cdn.quilljs.com`), cropper.js (`cdnjs`), canvas-confetti (`jsdelivr`) `integrity=` olmadan yükleniyor. CDN ele geçirilirse sayfalarınızda keyfî JS çalışır. SRI hash'i ekleyin veya paketleri `static/vendor/` altına alın (ikincisi ayrıca kullanılabilirlik açısından daha sağlam).

### 18. Statik dosyalarda cache-busting yok → deploy sonrası bayat CSS
- `production.py`'de `ManifestStaticFilesStorage` yok; Nginx `/static/`'i 30 gün cache'liyor (`deployment_instructions.md:235-239`). Tailwind'i yeniden derleyip deploy ettiğinizde dönen kullanıcılar 30 güne kadar eski CSS görebilir. `STORAGES` ayarına `ManifestStaticFilesStorage` ekleyin (şablonlarda `{% static %}` zaten kullanıldığı için tek ayarlık iş).

---

## 🟢 KALİTE / SEO / PERFORMANS

19. **Repo şişkinliği (~380 MB tracked):** `nishyearafis.png` (19,6 MB) hem `static/images/` hem `docs/design/` altında; `static/images/hero/*.JPG` orijinalleri (5-9 MB/adet) commit'li ama şablonlar yalnızca `.webp` sürümlerini kullanıyor (`pages/home.html:15-93`); `docs/design/` tek başına ~171 MB. 40 GB SSD'li VDS'te her clone/pull bu yükü taşıyor. Kullanılmayan JPG'leri ve kopyaları silin; istenirse ayrı bir adımda `git filter-repo` ile geçmiş temizliği (dikkatli, koordineli yapılmalı).
20. **SEO/sosyal eksikleri:** OG/Twitter meta yok (Discord/WhatsApp/Instagram paylaşımlarında önizleme kartı çıkmaz), canonical yok, `robots.txt` ve `sitemap.xml` yok (Django'nun `sitemap` framework'ü hazır). `base.html`'e blok tabanlı og:title/og:description/og:image ekleyin; etkinlik detayında kapak görselini og:image yapın.
21. **404/500 özel sayfaları yok** (yalnızca `pages/429.html` var) — `templates/404.html` ve `templates/500.html` ekleyin.
22. **`print()` kalıntıları:** `users/api.py:34,36`; `dashboard/views.py:544,769`; `events/models.py:277`; `pages/api.py:35,37,81,83` → `logging` modülüne geçin, production'da dosyaya/journald'a log yazın (şu an LOGGING ayarı da yok).
23. **`str(e)` istemciye sızıyor:** `dashboard/views.py` (~19 yer), `users/api.py` (81,149,174), `pages/api.py:124` — iç hata detayını JSON'da döndürmek bilgi sızıntısıdır; generic mesaj + sunucu tarafı log.
24. **Üç config mekanizması karışık:** `django-environ` (settings), `python-decouple` (`dashboard/views.py:492-515`), `os.getenv` (`pages/api.py:47-75`). Tekine (django-environ) standardize edin; `python-decouple`'ı requirements'tan çıkarın.
25. **N+1 ve ağır istekler:** `dashboard/views.py:451-454` üye başına `attended_meetings.count()`; `StorageManagerView:979-999` her istekte tüm media ağacını senkron geziyor (annotate + cache önerilir).
26. **Bağımlılık hijyeni:** `Django>=6.0` üst sınırsız (yeni major'a otomatik atlar — `Django>=6.0,<6.1` pinleyin); `django-cryptography` requirements'ta ama kullanılmıyor (kod doğrudan `cryptography.fernet` kullanıyor) — çıkarın; deploy dokümanı `psycopg2-binary` derken requirements `psycopg[binary]` (v3) — dokümanı düzeltin; `.gitignore:51` `package-lock.json`'u ignore ediyor — lock dosyası commit'lenmeli.
27. **Ölü kod/varlık:** `jams/services.py run_matchmaker` + `SuggestedTeam` hiçbir URL'e bağlı değil; `static/css/styles.css` (48 KB) hiçbir şablonda referanslı değil; `seed_event.py` / `update_event.py` kökte duran dev scriptleri (management command yapılmalı veya silinmeli).
28. **Test/CI/lint yok:** tüm `tests.py` dosyaları 3 satırlık stub; CI yok; linter/formatter yok. `.agents/AGENTS.md` PEP 8 şart koşuyor ama hiçbir şey bunu uygulamıyor. Events admin'de yalnızca `Event` kayıtlı (Raffle, EventApplication, EventImage admin'den görünmüyor).
29. **Tailwind düzeni:** `package.json`'da hem `tailwindcss ^3.4` hem `@tailwindcss/cli ^4.3` (v4 kalıntı — kaldırın); `build:css`/`watch:css` npm script'i yok (derleme el yordamıyla); `tailwind.config.js` content globs `dashboard/` app dizinini içermiyor (şu an dashboard şablonları global `templates/` altında olduğu için çalışıyor ama kırılgan).

---

## Yol Haritası

### Aşama 1 — Acil güvenlik (tek oturumluk iş)
Bulgular **1-10**: register bypass, OTP rate limit + kilit, EventApplication şifreleme + HMAC hash, FERNET_KEY ayrıştırma + re-encrypt migration, proxy/CSRF ayarları, path-traversal düzeltmesi, 500 bug'ı, GET-write çekiliş, draft sızıntısı.

**Ardından sunucuda (manuel, sizin yapmanız gerekenler — sırayla):**
1. `.env`'e `FERNET_KEY` ekle (kod deploy edildikten sonra re-encrypt migration çalıştır)
2. `DJANGO_SECRET_KEY`'i yenile (oturumlar/şifre sıfırlama linkleri geçersiz olur)
3. İki Gmail uygulama şifresini Google hesabından yenileyip `.env`'i güncelle
4. `chmod 600 .env`
5. Ayrıcalıksız kullanıcı oluştur, Gunicorn servisini `User=root`'tan ona taşı
6. Nginx'te `proxy_set_header X-Forwarded-Proto $scheme;` doğrula
7. `git pull && venv/bin/python manage.py migrate && venv/bin/python manage.py collectstatic --noinput && systemctl restart gunicorn`

### Aşama 2 — Buglar ve içerik güvenliği (1-2 oturum)
Bulgular **11-18**: Font Awesome/SVG ikonlar, görsel boyut düzeltmesi, slug üretimi, status doğrulama, mail kuyruğu (django-rq), `|safe` sanitizasyonu (nh3), SRI/vendoring, ManifestStaticFilesStorage.

### Aşama 3 — Temizlik + SEO (1 oturum)
Bulgular **19-27**: repo görsel temizliği, OG/meta + sitemap + robots.txt + 404/500 sayfaları, print→logging, str(e) temizliği, config tekleştirme, N+1, bağımlılık pinleme, ölü kod.

### Aşama 4 — Sürdürülebilirlik (devamlı)
- **Test:** `pytest` + `pytest-django` ile önce kritik akışlar: kayıt/OTP (bypass regresyonu dahil!), etkinlik başvurusu, çekiliş, dashboard yetki kontrolleri.
- **CI:** GitHub Actions — her push'ta `ruff check` + `pytest`; main'e merge öncesi zorunlu.
- **Lint/format:** `ruff` (lint + format tek araç) + `pre-commit`.
- **Rutin:** ayda bir `pip list --outdated`, her deploy öncesi `python manage.py check --deploy`, Django güvenlik sürümlerini takip (6.0.x patch'leri).
- **Süreç:** değişiklikleri önce lokalde `development` ayarıyla test et → commit → sunucuda tek komutluk update runbook'u (mevcut dokümandaki akış iyi). İleride staging düşünülebilir ama bu ölçekte şart değil.

---

## Sonraki oturum için not

Aşama 1'e başlarken bu raporu referans verin: *"docs/denetim-raporu-2026-07-19.md'deki Aşama 1'i uygula"* demeniz yeterli.
