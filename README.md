# Nishdot Web Platform - Project Documentation

This document is the absolute source of truth for the Nishdot Web Platform. It details the architecture, apps, models, frontend stack, deployment configurations, and all technical decisions. This file is designed to provide 100% context to developers and AI assistants (like Claude Code) onboarding to the project.

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
- **`users/`**: Custom user model and authentication (OTP-based email verification).
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

### 3.2 `users` App
- **Models:** 
  - `CustomUser`: Extends `AbstractUser`. Uses `email` as unique identifier. Has Roles (`MEMBER`, `BOARD`, `ADMIN`). Includes profile data (University, Department, Portfolio, Phone, National ID) and OTP fields (`is_verified`, `verification_code`, `code_expires_at`).
- **Auth Flow:** Registration requires Name, Surname, Email, Password. An OTP is sent asynchronously (using `asgiref.sync.sync_to_async`). Login requires a verified email.
- **Forms:** `UserRegisterForm`, `UserLoginForm`, `UserProfileUpdateForm`.

### 3.3 `events` App
- **Models:**
  - `Event`: Base model for all activities. Types: Game Jam, Workshop, Meetup, Talk, Other. Contains dates, locations, cover image, and thumbnail (auto-compressed to WebP in `save()` method).
  - `EventApplication`: Applications for non-Jam events. Includes KVKK checks and National ID hashing for security.
  - `Raffle` & `RaffleParticipant`: For live event giveaways. Participants scan a QR code to join dynamically.
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
- **Setup:** Defined in `package.json`. Compiles using `npx tailwindcss -i ./static/css/input.css -o ./static/css/output.css --watch`.
- **JS Strategy:** Mostly Vanilla JS directly in HTML templates (`<script>` tags) using the `fetch` API to communicate with Django JSON endpoints.
- **Components:** Reusable UI pieces found in `templates/components/` (navbar, footer).

## 5. Security & Rate Limiting
- **Rate Limiting:** `django-ratelimit` protects sensitive endpoints: Login, Register, Contact, and Event Applications.
- **SecurityLog:** Automatically logs rate limit breaches. Board members can review these in the Dashboard.
- **Data Protection:** 
  - Passwords hashed by Django.
  - Sensitive PII (National IDs) encrypted via Fernet (AES-256) derived from Django `SECRET_KEY`.

## 6. Self-Healing Storage
- Event galleries (`EventImage`) and Game cover images have auto-cleanup logic.
- If a physical file is deleted via the Dashboard Storage Manager (`api_storage_delete`), related DB records are automatically deleted.
- Viewing a gallery via API (`api_event_gallery`) checks if files exist on disk, and auto-deletes orphaned DB records. Frontend templates also contain `onerror` fallbacks to hide broken images.

## 7. Environment Variables (.env)
Required variables for the project:
```env
DJANGO_SECRET_KEY=your-secret-key
DJANGO_DEBUG=True/False
DJANGO_SETTINGS_MODULE=nishdot.settings.development # or production
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,yourdomain.com
DATABASE_URL=sqlite:///db.sqlite3 # or postgres url
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email
SMTP_PASSWORD=your-app-password
```
