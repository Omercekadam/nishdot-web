# Nishdot Web Platform — Teknik Mimari Dokümantasyonu

> Bu dosya projenin **teknik referans kaynağıdır**. Mimariyi, uygulamaları, modelleri,
> frontend yığınını, deployment yapılandırmalarını ve tüm teknik kararları detaylandırır.
> Projeye yeni katılan geliştiricilere (ve Claude Code gibi yapay zekâ asistanlarına)
> %100 bağlam sağlamak için tasarlanmıştır.
>
> Projenin genel tanıtımı için ana [README.md](../README.md) dosyasına bakın.

## 1. Project Overview & Architecture
- **Framework:** Django 6.0+ (Python)
- **Frontend Stack:** Tailwind CSS 3.4 (via postcss/autoprefixer), Vanilla JS, Django Templates
- **Database:** SQLite (development), PostgreSQL (production)
- **Caching & Sessions:** Redis (production) via `django-redis`
- **Deployment:** Nginx + Gunicorn on Ubuntu VDS
- **Environment Management:** `django-environ` reading from `.env`

## 2. Directory Structure & Root Configs
- **`nishdot/`**: Main configuration package. Uses a split settings approach:
  - `settings/base.py`: Common settings.
  - `settings/development.py`: Local settings (SQLite, Debug Toolbar).
  - `settings/production.py`: VDS settings (PostgreSQL, Redis, Security Headers).
- **`core/`**: Abstract base models and core utilities.
- **`users/`**: Custom user model and authentication (optional email verification via a 3-day link).
- **`arcade/`**: Stand-week snake game — competition window, signed-ticket score API, leaderboard.
- **`events/`**: Event management (Game Jams, Workshops, Meetups). Gallery, applications, raffles.
- **`jams/`**: Game Jam specific logic extending Events.
- **`pages/`**: Static pages (Home) and Legal Documents. Contact form logic.
- **`dashboard/`**: Staff/Board member management panel (`/management/`).
- **`templates/`**: Global templates using Tailwind classes.
- **`static/`**: Global static assets (`css/input.css` compiles to `css/output.css`).

## 3. Django Applications & Models Detail

### 3.1 `core` App
- **Models:**
  - `TimeStampedModel`: Abstract base class adding `created_at` and `updated_at` to all inheriting models.
- **Utilities:**
  - `core/crypto.py`: Fernet (AES-256) tabanlı şifreleme yardımcıları. `FERNET_KEY` ayarı `SECRET_KEY`'den bağımsızdır — böylece `SECRET_KEY` rotasyonu şifreli veriyi bozmaz.
  - `core/templatetags/sanitize.py`: `nh3` ile sunucu tarafı HTML sanitizasyonu (`|safe` yerine `|sanitize`).

### 3.2 `users` App
- **Models:**
  - `CustomUser`: Extends `AbstractUser`. Uses `email` as unique identifier. Has Roles (`MEMBER`, `BOARD`, `ADMIN`). Includes profile data (University, Department, Portfolio, Phone, National ID) and verification fields (`is_verified`; legacy `verification_code`, `code_expires_at`).
- **Auth Flow:** Registration requires Name, Surname, Email, Password. The user is logged in immediately and a verification link (`users/tokens.py`, valid `PASSWORD_RESET_TIMEOUT` = 3 days) is emailed. Verification locks nothing; unverified users see a reminder banner. `verification_code` / `code_expires_at` are legacy fields kept for rollback compatibility.
- **Forms:** `UserRegisterForm`, `UserLoginForm`, `UserProfileUpdateForm`.

### 3.3 `events` App
- **Models:**
  - `Event`: Base model for all activities. Types: Game Jam, Workshop, Meetup, Talk, Other. Contains dates, locations, cover image, and thumbnail (auto-compressed to WebP in `save()` method). `is_pinned` ile ana sayfada öne sabitlenebilir.
  - `EventApplication`: Applications for non-Jam events. Includes KVKK checks and National ID hashing for security.
  - `Raffle` & `RaffleParticipant`: For live event giveaways. Participants scan a QR code to join dynamically. `guest_name` alanı sayesinde yöneticiler hesabı olmayan misafirleri elle ekleyebilir.
  - `EventImage`: Photo gallery for events. Auto-compresses to JPEG on save.
  - `EventGame`: Games produced in past events/jams.

### 3.4 `jams` App
- **Models:**
  - `GameJam`: OneToOne linked to `Event`. Adds deadline, max team size, available roles, and custom questions.
  - `JamApplication`: Complex application form. Includes team status (Solo, Has Team, Looking), role, experience level.
  - `SuggestedTeam`: Matchmaking feature allowing board members to group solo participants into teams.
- **Security Detail:** National IDs (T.C. Kimlik) are hashed for uniqueness checks, and securely encrypted using `cryptography.fernet` (AES-256) for storage.

### 3.5 `pages` App
- **Models:**
  - `LegalDocument`: Dynamic legal pages (slug based, e.g., KVKK, Privacy Policy).
- **Views/APIs:** `HomePageView`, `contact_api_view` (Async email sending with rate limiting).
- **SEO:** `pages/sitemaps.py` — `StaticViewSitemap`, `EventSitemap` (yalnızca yayında/tamamlanmış etkinlikler), `LegalDocumentSitemap`.

### 3.6 `dashboard` App
The nerve center for admins/board members (`/management/`).
- **Models:**
  - `MeetingNote`: Internal club meeting notes.
  - `BoardTask`: Kanban board tasks (Admin, Event, Design, Tech, Social).
  - `ClubAsset`: Finance/Equipment tracking.
  - `Announcement`: Site/Discord/Email notifications.
  - `SecurityLog`: Logs rate limit breaches (Spam/Brute Force).
- **Features:**
  - Event Builder, Kanban Drag & Drop, Member Directory, Storage Manager.
  - **Storage Manager:** Allows admins to physically delete files from the server. Automatically cleans up orphaned DB records (Self-Healing).

## 4. Frontend & Styling (Tailwind CSS)
- **Setup:** Defined in `package.json`. Compiles using `npm run build:css` (veya geliştirme için `npm run watch:css`).
- **JS Strategy:** Mostly Vanilla JS directly in HTML templates (`<script>` tags) using the `fetch` API to communicate with Django JSON endpoints.
- **Components:** Reusable UI pieces found in `templates/components/` (navbar, footer).
- **Vendored Assets:** Quill (zengin metin editörü) ve Cropper.js `static/vendor/` altında kendi sunucumuzda barındırılır — CDN erişim/SRI kırılganlığı yaşandığı için dış bağımlılık kaldırıldı.

## 5. Security & Rate Limiting
- **Rate Limiting:** `django-ratelimit` protects sensitive endpoints: Login, Register, Contact, and Event Applications.
  - Nginx arkasında gerçek istemci IP'si için `RATELIMIT_IP_META_KEY = "HTTP_X_REAL_IP"`.
- **SecurityLog:** Automatically logs rate limit breaches. Board members can review these in the Dashboard.
- **Data Protection:**
  - Passwords hashed by Django.
  - Sensitive PII (National IDs) encrypted via Fernet (AES-256) using a dedicated `FERNET_KEY`.
- **Admin Hardening:** Django admin varsayılan `/admin/` yerine `/yonetim/` altındadır.

## 6. Self-Healing Storage
- Event galleries (`EventImage`) and Game cover images have auto-cleanup logic.
- If a physical file is deleted via the Dashboard Storage Manager (`api_storage_delete`), related DB records are automatically deleted.
- Viewing a gallery via API (`api_event_gallery`) checks if files exist on disk, and auto-deletes orphaned DB records. Frontend templates also contain `onerror` fallbacks to hide broken images.

## 7. Environment Variables (.env)
Required variables for the project:
```env
DJANGO_SECRET_KEY=your-secret-key
FERNET_KEY=base64-encoded-fernet-key      # T.C. Kimlik şifreleme anahtarı
DJANGO_DEBUG=True/False
DJANGO_SETTINGS_MODULE=nishdot.settings.development # or production
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,yourdomain.com
DATABASE_URL=sqlite:///db.sqlite3 # or postgres url
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email
SMTP_PASSWORD=your-app-password
```
