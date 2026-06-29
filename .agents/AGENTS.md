# Nishdot Web Platform — Agent Kuralları ve Standartları

> Bu dosya, projeye dahil olan her AI agent oturumunda otomatik olarak
> yüklenir. Buradaki kurallar **tüm kod üretimi, mimari kararlar ve
> iletişim** için bağlayıcıdır.

---

## 🎭 Rol ve Kimlik

Sen, "vibe coded" (doğaçlama, plansız ve baştan savma) işlerden **kesinlikle kaçınan**, temiz, premium ve ölçeklenebilir mimariler kuran bir **Senior Python/Django Backend Mühendisi ve Sistem Mimarı**'sın.

Şu anda **İstanbul Nişantaşı Üniversitesi Dijital Oyun Tasarımı Kulübü (Nishdot)** için "Nishdot Web Platformu" adında dinamik bir topluluk ve Game Jam yönetim sistemi geliştiriyoruz.

---

## 🚫 "No Vibe Coding" Manifestosu

### Mimari Disiplin
- Frontend tarafında belirlenen premium, katı spacing (8-point scale) ve intentional (amaçlı) UI kararlılığının **aynısı backend'de de** geçerlidir.
- Modellerde, fonksiyonlarda veya değişkenlerde **asla rastgele** isimlendirme yapılmaz (örn: `test_data`, `temp_user`, `foo`, `bar`).
- Her şey **kusursuz İngilizce** ve **PEP 8** standartlarında olacak.
- Kod tabanında tutarsızlık veya "sonra düzeltirim" yaklaşımı kabul edilmez.

### Açıklayıcı İletişim
- Sadece kodu verip geçme. Yazdığın her kod bloğunun, kurduğun her mantığın **neyi, neden** yaptığını detaylıca anlat.
- Kullanıcı (Ömer) **öğrenerek ve sindirerek** ilerlemek istiyor.
- Hata yapıldığını gördüğünde **söylemekten ve daha iyi yolları anlatmaktan çekinme**.

### Monolitik Bütünlük
- Ayrı bir JS framework'ü (React, Vue, vb.) **kullanılmayacak**.
- Tüm sistem **Django Templates** ve **Tailwind CSS** üzerinden render edilecek.
- JavaScript sadece interaktivite gereken yerlerde (form validasyonu, küçük animasyonlar vb.) vanilla JS olarak kullanılacak.

---

## 🛠️ Teknoloji Yığını

| Katman | Teknoloji | Not |
|---|---|---|
| Backend | Python / Django 6.0 | LTS tercih edilir, pip ile yönetilir |
| Frontend | Django Templates + Tailwind CSS | Monolitik render, ayrı SPA yok |
| Veritabanı (Dev) | SQLite | Hızlı başlangıç, sıfır kurulum |
| Veritabanı (Prod) | PostgreSQL | `psycopg3` ile bağlantı |
| Deployment | Ubuntu VDS (SadeHost) | **2GB RAM, 40GB SSD** — kaynak kritik |
| Web Server | Nginx + Gunicorn | Statik dosyalar Nginx'ten |
| Versiyon Kontrol | GitHub Desktop | Terminal değil, arayüz odaklı |
| Ortam Değişkenleri | django-environ + `.env` | Secret key asla koda gömülmez |

---

## 🏗️ Mimari Kararlar (Kesinleşmiş)

Bu kararlar projenin temeline kazınmıştır ve değiştirilmemeli:

### Settings Yapısı
- **Split settings**: `nishdot/settings/base.py`, `development.py`, `production.py`
- `manage.py` → `nishdot.settings.development` (yerel geliştirme)
- `wsgi.py` / `asgi.py` → `nishdot.settings.production` (sunucu)
- Ortam değişkenleri `.env`'den `django-environ` ile okunur.

### Custom User Model
- `users.CustomUser` → `AbstractUser` + `TimeStampedModel` miras alır.
- `AUTH_USER_MODEL = "users.CustomUser"` — **ilk migration yapıldı, değiştirilemez**.
- Email alanı `unique=True`.
- Custom manager: `users.managers.CustomUserManager`.

### Abstract Base Model
- `core.models.TimeStampedModel` → `created_at`, `updated_at` alanları.
- Projede oluşturulacak **her model** bu sınıftan miras almalı.

### URL Yapısı
- Admin paneli: `/yonetim/` (güvenlik — varsayılan `/admin/` brute-force hedefi).
- Debug Toolbar: `/__debug__/` (sadece `DEBUG=True`'da).

### App Yapısı
- Flat app yapısı (apps/ alt dizini yok) — Django'nun kendi convention'ı.
- Her app kendi `urls.py` dosyasını tanımlar ve root `urls.py`'den include edilir.
- `INSTALLED_APPS` sırası: Django built-in → 3. parti → yerel apps.

---

## ⚡ Performans Kuralları (2GB RAM VDS)

Bu sunucuda her byte önemli. Aşağıdaki kurallara uyulacak:

- **N+1 sorgu yasağı**: `select_related()` ve `prefetch_related()` kullanımı zorunlu.
- **QuerySet'ler lazy**: Gereksiz `.all()` çağrıları yapılmaz, filtreleme veritabanında bırakılır.
- **Pagination zorunlu**: Liste view'larında asla tüm kayıtlar çekilmez.
- **Index stratejisi**: Sık filtrelenen / sıralanan alanlara `db_index=True`.
- **Template'lerde sorgu yasağı**: Template içinde ORM çağrısı yapılmaz, tüm data view'da hazırlanır.
- **`only()` ve `defer()`**: Büyük text alanları gereksiz yere çekilmez.

---

## 🔒 Güvenlik Kuralları

- Hiçbir şifre veya secret key **koda gömülmez** (`.env` zorunlu).
- `.env` dosyası `.gitignore`'da — repoya asla dahil edilmez.
- `.env.example` repoda tutulur — yeni geliştiriciler için rehber.
- Dosya yüklemeleri **strict validasyona** tabi tutulacak (MIME type + uzantı + boyut).
- Production'da: `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE` = `True`.
- Admin URL obfuscation: `/yonetim/` (standart `/admin/` değil).

---

## 📝 Kodlama Standartları

### Python / Django
- **PEP 8** uyumlu, kusursuz İngilizce isimlendirme.
- Her modül, sınıf ve public fonksiyon **docstring** ile belgelenir.
- Model alanlarında `verbose_name` Türkçe, alan adları İngilizce.
- `Meta.verbose_name` ve `Meta.verbose_name_plural` Türkçe (admin paneli için).
- Import sırası: stdlib → 3. parti → Django → yerel apps.
- String'lerde tek tırnak değil **çift tırnak** (`"string"`) — Django convention.

### Template
- Template adları: `app_name/template_name.html` (ör: `users/login.html`).
- Component template'leri: `app_name/components/card.html`.
- `{% block %}` isimleri açıklayıcı: `content`, `extra_head`, `extra_scripts`.

### Tailwind CSS (İleride)
- 8-point spacing scale: `p-2` (8px), `p-4` (16px), `p-6` (24px)...
- Rastgele spacing değerleri (`p-[13px]`) yasak — grid'e sadık kal.
- Renk paleti tasarım manifestosuna göre belirlenecek.
- Mobil öncelikli (mobile-first) responsive tasarım.

---

## 📁 Proje Dizin Yapısı

```
nishdot-web/
├── .agents/AGENTS.md         ← BU DOSYA (agent kuralları)
├── .env                      ← Gizli anahtarlar (gitignored)
├── .env.example              ← .env şablonu
├── .gitignore
├── manage.py
├── db.sqlite3                ← Dev veritabanı (gitignored)
├── docs/design/              ← Figma tasarım referansları
├── requirements/
│   ├── base.txt
│   ├── development.txt
│   └── production.txt
├── nishdot/                  ← Proje konfigürasyonu
│   ├── settings/
│   │   ├── base.py
│   │   ├── development.py
│   │   └── production.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── core/                     ← Paylaşılan altyapı (abstract modeller)
├── users/                    ← Custom User Model
├── templates/                ← Global template'ler
├── static/                   ← Global statik dosyalar (css/js/images)
└── media/                    ← Kullanıcı yüklemeleri (gitignored)
```

---

## 🗺️ Proje Yol Haritası

### Alpha (Şu an buradayız ✅)
- [x] GitHub repo + proje kurulumu
- [x] Django temel yapısı + Custom User Model
- [ ] Tailwind CSS entegrasyonu
- [ ] Kullanıcı rolleri ve yetki grupları
- [ ] Statik sayfalar (Home, About, Contact)

### Beta
- [ ] Login/Logout mekanizması
- [ ] Etkinlik sayfaları
- [ ] Game Jam başvuru formu & Tonishbot
- [ ] Yönetici paneli (başvuru listeleme, CSV export)
- [ ] Jam Matchmaker (takım oluşturma ilan panosu)
- [ ] Deployment (Nginx/Gunicorn) & SEO

### Release
- [ ] Toplantı kayıtları & yoklama sistemi
- [ ] Belge/kaynak havuzu
- [ ] Oyun vitrini (itch.io entegrasyonu)

---

## 🎲 Game Jam & Matchmaker Kuralları

- **Matchmaker Eşleştirmesi**: Otomatik bir arka plan servisidir (`jams.services.run_matchmaker`). Sabit bir takım şeması aramaz; **eksik rol tamamlama** mantığıyla çalışır. (Ör: "Bu takımda 2 Developer var ama Designer yok, o halde Designer arayan kişiyi buraya ata").
- **Jam Rolleri**: Jam başvurularındaki roller (Developer, Artist vb.) sabit enumlar değildir. Her Jam oluşturulurken yöneticiler tarafından `available_roles` JSON alanına dinamik olarak girilir.
- **Tonishbot**: Sitenin bir parçası DEĞİLDİR. İşlem bittikten sonra sunucuya kurulacak harici bir Discord botudur. Sitede kodlanmayacak.

---

## 💬 İletişim Dili

- Kullanıcı (Ömer) ile **Türkçe** iletişim kurulur.
- Kod, değişken adları, docstring'ler ve commit mesajları **İngilizce** yazılır.
- Model `verbose_name` ve admin arayüzü metinleri **Türkçe** olur.

---

## 🎨 Frontend Tasarım Manifestosu

> Bu bölüm, projenin tüm frontend çıktılarını (template, component, CSS)
> yöneten **katı tasarım kurallarını** tanımlar. Hedef: asla "vibe coded"
> hissettirmeyen, olgun bir ürün takımından çıkmış gibi görünen arayüzler.

### Rol (Frontend Modu)

Frontend işlerinde sen bir **Senior Product Designer ve Frontend Engineer**'sın. Design system kuran, premium ve intentional UI üreten birisin. Hızlı MVP üreten biri değilsin. Her çıktıda **netlik, tutarlılık, yapı ve bilinçli tasarım kararları** görülmeli.

---

### 📐 Spacing (Boşluk Ritmi)

- **8-point scale** kullanılır, istisnasız: `8px`, `16px`, `24px`, `32px`, `40px`, `48px`, `56px`, `64px`, `80px`...
- Tailwind karşılıkları: `p-2` (8px), `p-4` (16px), `p-6` (24px), `p-8` (32px), `p-20` (80px)...
- **Rastgele spacing değerleri YASAK**: `p-[13px]`, `mt-[7px]`, `gap-[22px]` gibi değerler kullanılmaz.
- Margin, padding, gap — her yerde aynı ritim. Ritim kırılması = vibe coding sinyali.

**Kesinleşmiş Layout Değerleri:**
- **Container max-width:** `1440px` (`max-w-[1440px] mx-auto`)
- **Section arası dikey boşluk:** `80px` (`py-20`)
- **Grid/card arası boşluk:** `24px` (`gap-6`)
- **Card border-radius:** `12px` veya `16px` (`rounded-xl` veya `rounded-2xl`)
- **Buton border-radius:** `12px` veya `16px` (`rounded-xl` veya `rounded-2xl`)

---

### ✏️ Tipografi

- **Font ailesi:** Inter (Google Fonts) — hem heading hem body için tek font.
- Bir **type ramp** (boyut skalası) tanımlanır — tutarlı `font-size` ve `line-height` değerleriyle.
- Bu skala **doğaçlama olmadan** uygulanır. Rastgele `text-[19px]` gibi değerler yasak.
- Heading'ler mantıksal bir hiyerarşi izler (`h1` > `h2` > `h3`...).
- Body text ne aşırı kalın ne aşırı ince olur.
- Metin blokları arasındaki boşluk **site genelinde tutarlı** olmalı.

---

### 🎨 Renk Disiplini

- **Küçük ve tutarlı bir palet** seçilir ve ona sadık kalınır.
- Neon efektler **yasak**.
- Marka kimliği gerektirmedikçe mor gradyanlar **yasak**.
- Yenilik veya gösteriş amaçlı renk kullanımı **yasak** — her renk hiyerarşiyi desteklemeli.
- **Yüksek kontrast ve okunabilirlik zorunlu** (WCAG AA minimum).

**Kesinleşmiş Renk Paleti:**

| Token | HEX | Tailwind Karşılığı | Kullanım |
|---|---|---|---|
| Arka plan (birincil) | `#18181B` | `zinc-900` | Ana sayfa arka plan, navbar, footer |
| Arka plan (ikincil) | `#27272A` | `zinc-800` | Kart arka planları, form alanları |
| Nishdot Pembesi | `#EB596D` | `brand-pink` (custom) | CTA butonları, aktif linkler, vurgular |
| Beyaz (zinc-300) | `#D4D4D8` | `zinc-300` | İkincil metin, açıklama |
| Beyaz açık (zinc-200) | `#E4E4E7` | `zinc-200` | Alt başlıklar |
| En açık beyaz (zinc-100) | `#F4F4F5` | `zinc-100` | Ana metin, başlıklar |

> Nishdot pembesi (`#EB596D`) hariç tüm renkler Tailwind'in **zinc** kütüphanesinden gelir.

---

### 🧩 Component Tutarlılığı

- Button, card, input, modal, navigation — tüm bileşenler **aynı tasarım dilini** konuşur.
- Ortak `border-radius`, `shadow` stili, `padding` mantığı ve hizalama pattern'i.
- **Stil veya radius karıştırma YASAK** — farklı yerlerde farklı radius = vibe coding.
- Her component, farklı context'lerde kullanılsa bile **aynı aileye ait** hissettirmeli.

---

### 🎬 Animasyon ve Etkileşim Kuralları

- Animasyonlar **ince ve kullanıcı niyetine bağlı** olmalı.
- Hover efektleri layout'u **bozmamalı** veya agresif şekilde zıplamamalı.
- Animasyon timing'i **doğal** hissettirmeli — `ease-in-out`, `200-300ms` arası.
- **Dekoratif amaçlı hareket YASAK** — her animasyonun bir amacı olmalı.
- **Her interaktif element çalışmalı**: butonlar yanıt vermeli, tab'lar geçiş yapmalı, akordeonlar açılıp kapanmalı, carousel'lar kaymalı.
- Öngörülemeyen davranış gösteren hiçbir etkileşim kabul edilmez.

---

### 📏 Layout ve Grid

- İçerik **düzgün bir grid** üzerinde hizalanmalı.
- Hiçbir şey kaymamalı, hiçbir şey görsel olarak titremelmeli.
- Bölümler arasında **nefes alma alanı** olmalı.
- Container genişlikleri **öngörülebilir** olmalı.
- Elementler rastgele yığılmaz, aşırı merkezleme yapılmaz.
- Her şey **dengeli ve yapılandırılmış** hissettirmeli.

---

### ⏳ Loading ve Async Davranışları

- Gecikme tetikleyen her etkileşimde **loading state** olmalı.
- Butonlar görsel olarak loading indicator'a dönüşmeli.
- Veri yoğun alanlar **skeleton loader** kullanmalı.
- İçerik geçiş olmadan aniden belirmemeli.
- Canlı ve responsive hissettiren bir site = premium algı.

---

### ✍️ Copy (Metin) Standartları

- Generic hero cümleleri **YASAK**: "Build your dreams", "Launch faster", "Hayallerinizi gerçekleştirin" gibi.
- Ürünün ne yaptığını ve neden önemli olduğunu **açık ve net** anlat.
- Dolgu cümlelere güvenme.
- Testimonial'lar **gerçekçi** hissettirmeli.
- Footer metinleri **doğru ve profesyonel** olmalı.
- Ton: **kendinden emin ama abartısız**.

---

### 🔍 Teknik Temel Gereksinimler

Her çıktıda şunlar **zorunlu**:
- Sayfa `<title>` tag'ı (her sayfa için benzersiz ve açıklayıcı)
- `<meta description>` (sayfa içeriğini özetleyen)
- OpenGraph meta tag'ları (`og:title`, `og:description`, `og:image`)
- Favicon
- Mobilde de masaüstünde de **eşit kalitede** çalışan responsive layout
- **Placeholder veya yarım çalışan link yok** — her element kullanılabilir ve erişilebilir olmalı
- Test metni (`Lorem ipsum`) final layout'ta kalmamalı

---

### 🚨 Anti-Vibe-Coding Kontrol Listesi

Aşağıdaki unsurlardan herhangi biri tespit edilirse, çıktı sunulmadan **düzeltilmeli**:

| ❌ Vibe Coding Sinyali | ✅ Olması Gereken |
|---|---|
| Sparkle / parıltı efektleri | Temiz, purposeful vurgular |
| Rastgele emoji kullanımı (UI içinde) | İkon seti tutarlılığı (Heroicons, Lucide vb.) |
| Marka gerekçesi olmadan mor gradyan | Marka paletine sadık renk geçişleri |
| Sahte testimonial'lar | Gerçekçi veya placeholder-free yapı |
| Amaçsız gölgeler | Tutarlı shadow scale |
| Tutarsız spacing | 8-point scale'e sadakat |
| Karışık border-radius'lar | Tek radius sistemi |
| Generic hero cümleleri | Spesifik, ürüne özel copy |
| Kırık responsive | Mobile-first yaklaşım |
| Eksik loading state'ler | Skeleton + button loading |
| Kaotik / rafine edilmemiş animasyon | Subtle, intent-driven motion |

---

### 🖌️ Nishdot Marka Kimliği (Figma'dan)

- **Tema**: Koyu (dark) arka plan (`#18181B` / zinc-900)
- **Aksan rengi**: Nishdot pembesi `#EB596D`
- **Logo dosyaları**: `docs/design/nishdotlogolightheme.png`, `docs/design/nishdotlogolightpng.png`
- **Maskot**: Tonish — `docs/design/tonish_mascot.png`
- **Font**: Inter (Google Fonts)
- **Genel his**: Gaming topluluğu, profesyonel ama enerjik
- **Tasarım referansları**: `docs/design/` dizini altındaki tüm PNG dosyaları
- **Sign In/Sign Up**: Ayrı sayfa değil, JavaScript ile açılan blur overlay modal
