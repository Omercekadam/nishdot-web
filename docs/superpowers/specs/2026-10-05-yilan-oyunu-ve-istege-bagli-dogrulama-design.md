# Yılan Oyunu + İsteğe Bağlı E-posta Doğrulaması — Tasarım

- **Tarih:** 2026-10-05
- **Dal:** `oyun-ve-dogrulama`
- **Yedek etiketi:** `yedek/stand-oncesi` → `24d4142` (değişiklik öncesi son `main`)
- **Teslim:** stand haftasından önceki gece canlıya; öncesinde ekip lokalde test eder

## 1. Bağlam ve hedef

Kulüp stand haftası bir haftadan kısa süre sonra başlıyor. Standa gelenlerin ve evdeki üyelerin
sitede oynayabileceği, en yüksek skoru tutan bir oyun ve küçük ödüllü bir liderlik tablosu
isteniyor. Amaç eğlence + stand haftasının asıl işi olan **üye toplama**.

Aynı çalışmada üyelikteki e-posta doğrulaması zorunlu olmaktan çıkıyor. Mevcut sistemde
6 haneli kod 15 dakikada geçersizleşiyor (`OTP_VALIDITY_MINUTES = 15`) ve mail kayıt isteğinin
içinde senkron gönderiliyor; mail geç gelirse veya spam'e düşerse kişi kodu bulduğunda kod
ölmüş oluyor ve hesaba giremiyor. Bu, oyunun "skoru kaydetmek için üye ol" akışını da
doğrudan tıkıyor.

## 2. Alınan kararlar

| Konu | Karar | Gerekçe |
|---|---|---|
| Oyun | Yılan | Bir haftadan kısa sürede en düşük risk; 1-3 dakikalık eller hızlı tekrara uygun |
| Hile önleme | Hafif korkuluklar; sunucuda tekrar oynatma **yok** | Ödüller küçük; JS ve Python'da aynı oyunu birebir tutturma riskini almaya değmez |
| Oyun erişimi | Herkes oynar, skoru tabloya kaydetmek için üye olur | Üyeliği motivasyonun en yüksek olduğu ana koyar |
| Tabloda görünen ad | Ad + soyadın baş harfi ("Ömer S.") | Moderasyon gerektirmez, tanınabilirliği düşük |
| E-posta doğrulaması | Hiçbir şeyi kilitlemez, sadece hatırlatır; yalnızca ödül için şart | Etkinlik başvurusu zaten hesapsız açık; kilitlemek sadece üye olanı cezalandırır |
| Doğrulama yöntemi | 15 dakikalık kod yerine 3 gün geçerli link | Mail ne zaman gelirse gelsin çalışır |
| Konum | Ana sayfada Etkinlikler ile Hakkımızda arasında bölüm; tablo oyunun altında | Ziyaretçinin zaten geldiği yer; ayrı sayfa ve QR gereksiz |
| Ömür | Stand haftası sonrası admin'den kapatılır | Deploy veya kod geri alma gerektirmez |
| KVKK metni | **Değiştirilmez**; oyun bölümünde tek satırlık bildirim | Kullanıcı kararı |

## 3. Kapsam

**Dahil (MVP):** Parça A'nın tamamı · ana sayfada oyun bölümü · skor gönderimi + hafif
korkuluklar · üye olmadan yapılan skorun girişte sahiplenilmesi · liderlik tablosu ·
admin'den yönetilen yarışma penceresi ve aç/kapa anahtarı · Django admin üzerinden moderasyon
· genel mesaj bileşeni.

**Kapsam dışı:** sunucuda tekrar oynatma ve bot tespiti · seçilebilir oyuncu adı · birden
fazla oyun · ayrı oyun sayfası, QR, stand ekranı · e-posta değiştirme ekranı · KVKK metni
değişikliği · özel yönetim paneli sayfası.

## 4. Parça A — İsteğe bağlı e-posta doğrulaması

Bu parça kalıcıdır; oyunun aç/kapa anahtarından bağımsızdır.

### 4.1 Akış

| Şu an | Yeni |
|---|---|
| Kayıt → 6 haneli kod (15 dk) → kod girilmeden giriş yok | Kayıt → **anında giriş** → mailde doğrulama linki (3 gün geçerli) |
| Mail gönderilemezse kayıt 502 döner | Mail gönderilemezse kayıt yine başarılı; hata loglanır, kullanıcı banttan tekrar ister |
| Doğrulanmamış hesap giriş yapamaz | Giriş serbest; hiçbir işlem kilitlenmez |

### 4.2 Bileşenler

- **Kayıt** (`users/api.py` → `register_api_view`): kullanıcı `is_verified=False` ile oluşturulur,
  `login(request, user)` çağrılır (tek `ModelBackend` olduğu için backend argümanı gerekmez),
  ardından doğrulama maili gönderilir. Mail hatası `logger.exception` ile loglanır, yanıt yine
  başarılıdır. Yanıt, güvenli bir `redirect` adresi döner: istekle gelen `next`
  `url_has_allowed_host_and_scheme` ile doğrulanır, geçersizse `/`. Artık OTP alanları
  doldurulmaz.
- **Kayıt sayfası** (`templates/users/register.html`): OTP adımı ve tekrar-gönder JS'i kaldırılır.
  Sayfa URL'deki `next`'i kayıt isteğiyle gönderir; başarıda `redirect` adresine gider.
  "Zaten hesabın var mı?" bağlantısı `next`'i taşır.
- **Giriş** (`users/forms.py`): doğrulanmamış hesabı reddeden kontrol kaldırılır. Giriş sayfasındaki
  "Kayıt ol" bağlantısı `next`'i taşır. `LoginView` `next`'i zaten destekler.
- **Doğrulama linki**: `GET /auth/dogrula/<uidb64>/<token>/` (ad: `users:verify_email`).
  Geçerliyse `is_verified=True`, başarı mesajı, `/`'e yönlendirme. Geçersiz/süresi dolmuşsa hata
  mesajı ("Link geçersiz veya süresi dolmuş; giriş yapıp yeni link isteyebilirsin") ve
  yönlendirme. Zaten doğrulanmışsa bilgi mesajı. Giriş yapmış olmak gerekmez.
- **Doğrulama maili**: yeni `templates/emails/verify_email.html` + konu şablonu; görünüm mevcut
  OTP mailinin düzenini izler. Mutlak link `request.build_absolute_uri(reverse(...))` ile üretilir.
  Mailde spam klasörü notu bulunur.
- **Uyarı bandı** (`templates/components/verify_banner.html`, `base.html`'de navbar'ın hemen
  altında): `user.is_authenticated and not user.is_verified` ise görünür; kapatılamaz.
  Metin: *"E-posta adresini henüz doğrulamadın. Gelen kutunu ve spam klasörünü kontrol et."* +
  "Tekrar gönder" butonu (CSRF'li küçük form, JS gerekmez).
- **Tekrar gönder**: `POST /auth/dogrulama-gonder/` (ad: `users:resend_verification`),
  `login_required`, django-ratelimit `key='user', rate='3/h', block=False`. Başarıda bilgi mesajı;
  sınır aşılınca uyarı mesajı ve mevcut `_log_rate_limited` yardımcısıyla `SecurityLog` kaydı.
  Güvenli `HTTP_REFERER`'e, yoksa `/`'e döner. Zaten doğrulanmış kullanıcıda mail göndermeden döner.

### 4.3 Doğrulama tokenı

`users/tokens.py` içinde `PasswordResetTokenGenerator`'dan türeyen
`EmailVerificationTokenGenerator`. `_make_hash_value` yalnızca `user.pk`, `user.email`,
`user.is_verified` ve `timestamp` içerir:

- `is_verified` hash'te olduğu için link **bir kez kullanılınca geçersizleşir**.
- `email` hash'te olduğu için adres değişirse eski link ölür.
- Varsayılan üst sınıfın aksine `last_login` ve parola hash'i **dahil edilmez** — kayıt
  token'ı ürettikten hemen sonra `login()` çağırıp `last_login`'i güncellediği için, dahil
  edilseydi her yeni link doğar doğmaz geçersiz olurdu.
- Süre `PASSWORD_RESET_TIMEOUT` (Django varsayılanı 3 gün).

### 4.4 Genel mesaj bileşeni

`templates/components/messages.html`, `base.html`'de uyarı bandının altında. Django mesajlarını
seviyeye göre renklendirilmiş, kapatılabilir şeritler olarak gösterir. Çift gösterim olmaması
için `templates/users/login.html` ve `templates/users/dashboard.html`'deki yerel mesaj döngüleri
kaldırılır. Yan fayda: `events/views.py`'nin "başvurular kapalı" mesajı şu an hiçbir sayfada
görünmüyor; bileşenle görünür hale gelir.

### 4.5 Korunanlar ve kaldırılanlar

- **Kaldırılır:** OTP giriş arayüzü, `api_verify` ve `api_resend_otp` uç noktaları ve URL'leri,
  bunlara ait yardımcılar (`_generate_otp`, `send_otp_email`), OTP odaklı testler.
- **Korunur (bilerek):** `CustomUser.verification_code` ve `code_expires_at` alanları
  kullanılmadan modelde kalır. Silinirlerse eski koda dönmek şema geri almayı gerektirir;
  korunurlarsa `yedek/stand-oncesi` etiketine dönüş tek komuttur. Temizlik stand haftası
  sonrasına bırakılır. `SecurityLog.ActionType.OTP_ABUSE` geçmiş kayıtlar için kalır.
- Etkileri: kodu kaçırıp takılı kalmış eski hesaplar giriş yapabilir hale gelir ve bandı görür.

### 4.6 Testler

- Kayıt sonrası oturum açıktır, `is_verified=False`'tur, yanıt güvenli `next`'i döner;
  dış alan adına işaret eden `next` reddedilip `/` döner.
- Mail gönderimi istisna fırlatsa da kayıt başarılıdır.
- Doğrulanmamış kullanıcı giriş yapabilir.
- Geçerli link `is_verified=True` yapar; aynı link ikinci kez geçersizdir; bozuk token ve
  bozuk `uidb64` reddedilir.
- Tekrar gönder giriş ister; 4. istek sınıra takılır ve `SecurityLog` yazılır.
- Bant doğrulanmamış kullanıcıda görünür; doğrulanmış kullanıcıda ve anonimde görünmez.
- Mesaj bileşeni mesajı bir kez gösterir (giriş sayfasında çift gösterim yok).

## 5. Parça B — Yılan oyunu ve liderlik tablosu

Yeni Django uygulaması: `arcade` (`INSTALLED_APPS`'e eklenir).

### 5.1 Ana sayfa yerleşimi

- `templates/pages/home.html`'de `#events` ile `#about` arasına
  `{% include "arcade/_section.html" %}` → `<section id="oyun" class="... scroll-mt-20">`.
- Navbar'da Etkinlikler ile Hakkımızda arasına `{% url 'pages:home' %}#oyun` bağlantısı; mevcut
  scrollspy'a dahil olur.
- Bölüm sırası: başlık ve kısa açıklama → tuval + başlangıç/bitiş katmanları → yön tuşları
  (yalnızca dokunmatik) → KVKK bildirimi → liderlik tablosu.
- Bölüm, navbar bağlantısı ve `snake.js` yalnızca aç/kapa anahtarı açıkken render edilir.

### 5.2 Oyun (istemci)

`static/js/snake.js` — kütüphanesiz, `defer` ile yüklenir. Yapılandırma bölümdeki `data-*`
niteliklerinden okunur (API URL'leri, giriş/kayıt URL'leri, oturum durumu).

- **Kurallar:** 20×20 ızgara; başlangıç uzunluğu 3; saniyede 8 adımla başlar, her yemde
  +0,25 adım/sn (üst sınır 16); duvara veya kendine çarpınca biter; **skor = yenen yem sayısı**;
  teorik üst sınır 397. Yem boş hücrelere rastgele düşer.
- **Döngü:** `requestAnimationFrame` + biriktiricili sabit adım; oyun zamanı kare hızından
  bağımsız olarak gerçek zamanı izler.
- **Girdi:** ok tuşları ve WASD; tik başına en fazla 2 yön değişikliği tamponlanır; 180°
  geri dönüş yok sayılır. Dokunmatikte tuval üstünde kaydırma (eşik ~24px) ve tuvalin altında
  4 yön tuşu.
- **Sayfa kaydırma kilidi:** oyun sürerken pencere `keydown`'ında ok tuşları ve boşluk için
  `preventDefault`; tuvalde `touch-action: none`, yön tuşlarında `touch-action: manipulation`.
  Oyun bitince kilit kalkar.
- **Duraklatma yok.** `visibilitychange` ile sekme gizlenirse oyun biter ve skor
  `fetch(..., {keepalive: true})` ile gönderilir (keepalive özel başlığa, yani CSRF başlığına
  izin verir).
- **Akış:** "Başla" → `POST basla/` → bilet → oyun → bitiş → `POST bitir/` → bitiş katmanında
  skor, en iyi skor, "Tekrar"; anonimse "Tabloya girmek için üye ol" ve "Giriş yap"
  (`/auth/register/?next=/%23oyun`, `/auth/login/?next=/%23oyun`). Giriş yapmış kullanıcının
  skoru bitişte otomatik kaydedilir. Yanıttaki tablo DOM'da güncellenir.
- **Görünüm:** koyu zemin, marka pembesi (`#EB596D`) yılan, parlayan yem; tuval
  `min(100%, 480px)` genişlikte, kare, `devicePixelRatio` ile keskin. Skor bir `aria-live`
  alanında metin olarak da yazılır.
- Yeni Tailwind sınıfları nedeniyle `npm run build:css` gerekir.

### 5.3 Veri modeli

`Competition` (`TimeStampedModel`'den):

| Alan | Tür | Not |
|---|---|---|
| `name` | CharField(120) | |
| `starts_at`, `ends_at` | DateTimeField | `clean()`: bitiş başlangıçtan sonra olmalı |
| `is_visible` | BooleanField, varsayılan `False` | "Ana sayfada göster" — aç/kapa anahtarı |

Sıralama `-starts_at`. `Competition.current()` → `is_visible=True` olanların en yenisi ya da
`None`. `status` → `"upcoming" | "live" | "ended"`.

`GameRun`:

| Alan | Tür | Not |
|---|---|---|
| `user` | FK User, `null=True`, `on_delete=CASCADE` | `null` = sahiplenilmemiş; hesap silinince skorları da gider |
| `score` | PositiveIntegerField | 0–397 |
| `duration_ms` | PositiveIntegerField | istemcinin bildirdiği oyun süresi |
| `nonce` | CharField(32), **unique** | biletin tek kullanımlık olmasını veritabanı garanti eder |
| `is_disqualified` | BooleanField, varsayılan `False` | |
| `created_at` | DateTimeField, `auto_now_add`, indeksli | yarışma penceresi bu alanla süzülür |

`GameRun` bir yarışmaya FK ile bağlanmaz; pencere zaman damgasıyla belirlenir.

### 5.4 API ve korkuluklar

Her iki uç da `Competition.current()` yoksa **404** döner. Standart CSRF koruması geçerlidir:
`_section.html` token'ı `data-csrf="{{ csrf_token }}"` ile verir — bu aynı zamanda anonim
ziyaretçiye CSRF çerezinin gönderilmesini garanti eder (şablon token'a dokunmazsa Django çerezi
set etmez ve ilk gönderim 403 alır). İstemci `X-CSRFToken` başlığı yollar.

**`POST /oyun/api/basla/`** → `{"bilet": ...}`. Bilet,
`signing.dumps({"n": secrets.token_hex(16), "t": <sunucu ms>}, salt="arcade.run")`.
Veritabanına yazmaz.

**`POST /oyun/api/bitir/`** — gövde `{bilet, skor, sure_ms}`:

1. `skor` ve `sure_ms` tamsayı; `0 ≤ skor ≤ 397`, `0 < sure_ms ≤ 1 800 000`
2. `signing.loads(bilet, salt="arcade.run", max_age=1800)` — imza geçersiz veya 30 dk'dan eski
   ise ret
3. Sunucu saatiyle geçen süre: `şimdi − t + 2000 ≥ sure_ms` — değilse ret
4. `GameRun` oluşturulur; `nonce` çakışması (`IntegrityError`) ret demektir
5. Giriş yapmışsa `user=request.user`; değilse `user=None` ve kaydın kimliği
   `request.session["arcade_pending"]` listesine eklenir (en fazla 20)
6. Yanıt: `{"kaydedildi": true, "bekliyor": <anonim mi>, "tablo": [...ilk 10...],
   "sen": {"sira": n, "en_iyi": s} | null}`

Her ret 400 ve gövdede yalnızca `"Skor kaydedilemedi."` — sebep açıklanmaz; sunucu logu
WARNING seviyesinde sebebi yazar.

**Hız sınırı:** her iki uçta django-ratelimit `key='user_or_ip', rate='1200/h', block=False`;
aşımda 429 ve yeni `SecurityLog.ActionType.GAME_SPAM` ("Oyun Skoru (Spam) Sınırı") kaydı;
IP `core.http.get_client_ip` ile alınır. *Not: tasarım turunda "saatte 30" denmişti; bu yanlıştı.
Yeni başlayan biri 5-10 saniyede ölüp yeniden başlar ve 30 sınırına dakikalar içinde takılır;
üstelik kampüs Wi-Fi'ında öğrencilerin çoğu aynı genel IP'den çıkar. Sınırın işi yalnızca
veritabanını sel baskınından korumaktır; tablonun bütünlüğünü 3. adımdaki süre kontrolü
korur — yüksek skor iddiası, o süre kadar beklemeyi gerektirir.*

`SecurityLog`'a yeni seçenek eklemek `dashboard` uygulamasında bir migration doğurur.

### 5.5 Sahipsiz skorun sahiplenilmesi

`arcade/signals.py`'de `user_logged_in` alıcısı, `ArcadeConfig.ready()`'de bağlanır:
oturumdaki `arcade_pending` listesini alır ve siler; o kimliklerden `user=None` olan ve son
24 saatte oluşturulanları `update(user=user)` ile kullanıcıya bağlar.

Django `login()` anonim oturumdan girişte oturum anahtarını yeniler ama verisini korur; kayıt
artık `login()` çağırdığı için akış yeni üyelerde de çalışır. Skor aynı tarayıcıda sahiplenilir;
telefonda oynayıp bilgisayarda üye olan kişinin skoru sahipsiz kalır ve 24 saatte silinir
(bilinen sınır).

### 5.6 Liderlik tablosu kuralları

`arcade/services.py` → `leaderboard(competition, limit=10, user=None)`:

- Kapsam: `starts_at ≤ created_at ≤ ends_at`, `user` dolu, `is_disqualified=False`.
- Her oyuncunun **en iyi** skoru sayılır; eşitlikte o skora **daha önce** ulaşan üstte.
- Uygulama: koşular `(-score, created_at)` sırasıyla okunur, her kullanıcının ilk görülen kaydı
  alınır. Veri ölçeği yüzler/binler mertebesinde; gerekirse sonradan önbelleklenir.
- Döner: ilk `limit` satır (`sira`, `ad`, `skor`, `bu_sen_misin`) + `user` verilmişse onun
  `sira` ve `en_iyi` değeri.
- **Görünen ad:** `first_name` + boşluk + `last_name`'in ilk harfi + "." (ör. "Ömer S.").
  Baş harf Türkçe kurallarla büyütülür (`i` → `İ`, `ı` → `I`; Python'un `upper()`'ı `i`'yi
  `I` yapar). Ad boşsa "Oyuncu".
- Duruma göre bölüm metni:

| Durum | Gösterim |
|---|---|
| `upcoming` | Tablo yok; *"Yarışma {gün saat}'te başlıyor — şimdiden ısın."* Skorlar kaydedilir ama sıralamaya girmez |
| `live` | Canlı tablo |
| `ended` | Donmuş final tablo; *"Yarışma bitti."* Oyun anahtar kapatılana kadar oynanabilir; skorlar kaydedilir ama sıralamaya girmez |

- Giriş yapmış kullanıcının satırı vurgulanır; ilk 10'da değilse tablonun altında
  *"Senin sıran: #37 · en iyin 12"*.
- Tabloda yer alan doğrulanmamış kullanıcıya: *"Ödül kazanırsan sana ulaşabilmemiz için
  e-postanı doğrula."*
- `pages/views.py` → `HomePageView` bağlamına `arcade` (yarışma, durum, tablo, kullanıcı satırı)
  eklenir.

### 5.7 Aç/kapa anahtarı

- `arcade/context_processors.py` → `{"arcade_visible": Competition.current() is not None}`;
  navbar her sayfada olduğu için `settings`'teki `context_processors`'a eklenir.
- Kapalıyken: ana sayfada bölüm yok, navbar'da bağlantı yok, `snake.js` yüklenmez, API 404.
- Stand haftası sonrası tek işlem: admin'de yarışmanın "Ana sayfada göster" kutusunu kaldırmak.

### 5.8 Moderasyon

`arcade/admin.py`:

- `CompetitionAdmin`: ad, başlangıç, bitiş, `is_visible` (liste içinden düzenlenebilir).
- `GameRunAdmin`: oyuncu (görünen ad), e-posta, doğrulandı mı (boolean), skor, süre, tarih,
  diskalifiye; filtreler (diskalifiye, tarih); e-posta/ad araması; `-score` sıralama;
  "Diskalifiye et" ve "Diskalifiyeyi kaldır" aksiyonları. Diskalifiye skor tablodan anında düşer.

### 5.9 KVKK bildirimi

KVKK metni değiştirilmez. Oyun bölümünde, oynamadan önce görülecek yerde (tuvalin altında)
kalıcı tek satır: *"Skorunu kaydettiğinde adın ve soyadının baş harfi tabloda herkese açık
görünür."* Giriş yapmış kullanıcıda skor bitişte otomatik kaydedildiği için bildirim
oynamadan önce görünür olmalıdır.

### 5.10 Veri saklama

`pages/management/commands/purge_expired_data.py`'ye üçüncü adım: 24 saatten eski sahipsiz
koşular ve 365 günden eski tüm koşular silinir; `--dry-run` desteklenir.

### 5.11 Testler

- `basla`: anahtar açıkken bilet döner; kapalıyken 404.
- `bitir`: geçerli gönderim kaydedilir; bilet ikinci kez reddedilir; imzası bozuk veya 30 dk'dan
  eski bilet reddedilir; geçen süreden uzun `sure_ms` reddedilir; `skor > 397` reddedilir;
  ret gövdesi sebep sızdırmaz; hız sınırı aşımı 429 + `SecurityLog`.
- Anonim gönderim sahipsiz kaydedilir; giriş yapınca ve kayıt olunca kullanıcıya bağlanır;
  24 saatten eski sahipsiz kayıt bağlanmaz.
- Tablo: kişi başı en iyi skor; eşitlikte erken olan üstte; diskalifiye ve sahipsiz hariç;
  pencere dışı hariç; kullanıcının sırası doğru; görünen ad biçimi ("ilker yılmaz" → "ilker Y.",
  "Ömer ince" → "Ömer İ.").
- Anahtar: kapalıyken ana sayfada `id="oyun"` ve navbar bağlantısı yok; açıkken var.
- Temizlik: sahipsiz eski koşu ve 1 yıllık koşu silinir; `--dry-run` silmez.
- **JS oyunu için otomatik test yok;** ekip testi kontrol listesiyle doğrulanır (bkz. §6).

## 6. Yedek, test, yayın ve geri dönüş

0. **Yedek (tamamlandı):** `yedek/stand-oncesi` etiketi `24d4142`'de; tüm iş
   `oyun-ve-dogrulama` dalında. `main`'e ekip testi onaylanana kadar dokunulmaz.
1. **Geliştirme:** dal üzerinde, CI yeşil (ruff, `check`, `makemigrations --check`, testler,
   `check --deploy`). `static/css/output.css` derlenip commit'lenir — sunucuda npm yoktur,
   yalnızca `collectstatic` çalışır.
2. **Ekip testi (lokal):** dalı çek → `pip install -r requirements/development.txt` →
   `migrate` → `npm run build:css` → `runserver 0.0.0.0:8000` → admin'de "Ana sayfada göster"
   açık bir yarışma oluştur. Kontrol listesi:
   - Masaüstünde ok tuşları/WASD; oyun sürerken sayfa kaymıyor
   - Telefonda (aynı Wi-Fi, bilgisayarın IP'si) kaydırma ve yön tuşları; tuval üstünde sayfa
     sürüklenmiyor
   - Sekme değişince oyun bitiyor ve skor gönderiliyor
   - Üye değilken oyna → "üye ol" → `#oyun`'a dön → skor tabloda, oturum açık
   - Giriş yapmışken skor otomatik kaydediliyor, tablo yenilenmeden güncelleniyor
   - Uyarı bandı görünüyor; doğrulama linki çalışıyor, band kayboluyor
   - Admin'de diskalifiye edilen skor tablodan düşüyor
   - "Ana sayfada göster" kapatılınca bölüm ve navbar bağlantısı kayboluyor
3. **Gece-öncesi yayın:**
   1. Sunucuda `pg_dump` ile veritabanı yedeği
   2. Dal `main`'e birleştirilir; push ekipte
   3. `git pull` → `migrate` → `collectstatic --noinput` → `systemctl restart gunicorn`
   4. Admin'de yarışma: başlangıç = stand haftası açılışı, "Ana sayfada göster" açık
   5. Canlıda 5 dakikalık duman testi (bir oyun, bir kayıt akışı)
4. **Geri dönüş:**

   | Sorun | İşlem | Kayıp |
   |---|---|---|
   | Oyunda sorun | Admin'de "Ana sayfada göster" kapatılır | Yok, deploy yok |
   | Kayıt/giriş bozuldu | `git checkout yedek/stand-oncesi` + restart | Yok; OTP alanları korunduğu için şema uyumlu, yeni tablolar eski kod tarafından yok sayılır |
   | Her şey ters gitti | `pg_dump` yedeği geri yüklenir | Yayından sonraki kayıtlar |

5. **Stand haftası sonrası:** admin'de "Ana sayfada göster" kaldırılır. Final sıralama ödül için
   admin'de kalır. Ayrı bir işte: kullanılmayan OTP alanlarının temizliği.

## 7. Kabul kriterleri

- Üye olmayan biri ana sayfada oynar, "üye ol"a basar, kaydı bitirince oturumu açık şekilde
  `#oyun`'a döner ve az önceki skoru tabloda görünür.
- Doğrulanmamış kullanıcı giriş yapabilir, her sayfada bandı görür; mailindeki linke tıklayınca
  doğrulanır ve band kaybolur — mail 1 gün sonra açılsa bile.
- Telefonda oyun oynanırken sayfa kaymaz.
- Anahtar kapalıyken ana sayfada oyuna dair hiçbir şey yoktur ve API 404 döner.
- CI yeşildir.

## 8. Bilinen sınırlar

- Skorlar istemcide hesaplanır; korkuluklar bariz sahteliği ve sel baskınını durdurur, kararlı
  bir hileciyi durdurmaz. Ödüller küçük olduğu için bilinçli kabul; nihai karar admin'deki
  diskalifiye yetkisidir.
- Sahiplenme aynı tarayıcıyla sınırlıdır.
- E-postasını yanlış yazan kullanıcı doğrulama maili alamaz; doğru adresle yeniden kayıt olur
  veya admin'den düzeltilir.
- E-postanın neden spam'e düştüğü (gönderen hesap itibarı vb.) bu çalışmanın kapsamında değildir;
  3 gün geçerli link gecikmenin etkisini ortadan kaldırır.
