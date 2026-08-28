# Denetim Takibi ve Teknik Borç Kapatma — Uygulama Planı

> **Agent'lar için:** GEREKLİ ALT BECERİ: Bu planı görev görev uygulamak için
> superpowers:subagent-driven-development (önerilen) veya
> superpowers:executing-plans kullanın. Adımlar takip için checkbox (`- [ ]`)
> söz dizimi kullanır.

**Hedef:** 27 Ağustos 2026 kod incelemesinde doğrulanan 6 hatayı kapatmak, ölü
kalan Matchmaker özelliğini panele bağlayarak tamamlamak ve denetim raporundan
geriye kalan sürdürülebilirlik borcunu (lint + CI + eksik testler) ödemek.

**Mimari:** Mevcut mimariye sadık kalınır — yeni bağımlılık yok, yeni app yok,
JS framework yok. Tek yeni modül `core/http.py` (paylaşılan IP yardımcısı).
Matchmaker mevcut `jams/services.py` servisinin üzerine `dashboard` app'inde
ince bir view + template katmanı ekler. Her davranış değişikliği önce testle
kilitlenir (TDD), sonra uygulanır.

**Teknoloji Yığını:** Django 6.0.6, Python 3.14 (venv), SQLite (dev), Tailwind
CSS 3.4, vanilla JS, ruff, pre-commit, GitHub Actions.

**Spec:** Bu belgenin §0 "Bulgular" bölümü + [`docs/denetim-raporu-2026-07-19.md`](../../denetim-raporu-2026-07-19.md)
(madde 27 ölü kod, madde 28 test/CI/lint eksikliği).

---

## Global Kısıtlar

Her görevin gereksinimleri bu bölümü örtük olarak içerir.

- **Commit YAPILMAZ.** Kullanıcı değişiklikleri GitHub Desktop ile kendisi
  commit eder. Görev sonlarında `git add`/`git commit` çalıştırmayın; bunun
  yerine belirtilen doğrulama komutunu çalıştırıp çıktısını raporlayın.
- **Dil:** Kod, değişken adları ve docstring'ler **İngilizce**; model
  `verbose_name`, kullanıcıya dönen mesajlar ve arayüz metinleri **Türkçe**.
  (Yerleşik istisna: `jams/services.py` ve `purge_expired_data.py` içinde zaten
  Türkçe yerel değişken adları var — o dosyalarda mevcut üsluba uyun.)
- **PEP 8**, çift tırnak (`"string"`), import sırası: stdlib → 3. parti →
  Django → yerel app.
- **Tailwind:** 8-point spacing (`p-2`/`p-4`/`p-6`/`p-8`), radius yalnızca
  `rounded-xl` veya `rounded-2xl`, renk paleti zinc-900/zinc-800 + `brand-pink`
  (`#EB596D`). Rastgele değer (`p-[13px]`) yasak.
- **Performans:** Liste view'larında `select_related()`/`prefetch_related()`
  zorunlu; template içinde ORM çağrısı yasak.
- **Güvenlik:** Tüm dashboard uçları `@staff_member_required` + `@require_POST`;
  istemciye `str(e)` sızdırılmaz, detay `logger.exception()` ile loglanır ve
  kullanıcıya `GENERIC_API_ERROR` döner.
- **Yeni bağımlılık eklenmez** — istisna: Görev 9'da yalnızca geliştirme
  bağımlılığı olarak `ruff` ve `pre-commit`.
- **Test komutu:** `venv/Scripts/python.exe manage.py test` (Windows).
  Tüm görevlerin sonunda paketin tamamı yeşil olmalı.

---

## §0 Bulgular (Spec)

| # | Bulgu | Konum | Durum |
|---|---|---|---|
| B1 | Lokal ortam çalışmıyor: `nh3` kurulu değil, `.env`'de `FERNET_KEY` yok, 7 migration uygulanmamış | `venv/`, `.env`, `db.sqlite3` | Doğrulandı |
| B2 | Duyuru sorgusunda parantez hatası: `published_to_site=True` kısıtı board/members dalında devre dışı kalıyor | `users/views.py:70-83` | Doğrulandı (latent) |
| B3 | `SecurityLog` `REMOTE_ADDR` yazıyor, rate limit `HTTP_X_REAL_IP` okuyor; Nginx arkasında yanlış/boş IP | `users/views.py:50`, `users/api.py:52`, `pages/api.py:109`, `events/views.py:57` | Doğrulandı |
| B4 | `JamApplication.applicant` hiç set edilmiyor; panel başvuruları yalnızca e-posta ile eşleştiriyor | `events/views.py:113-147`, `users/views.py:64-67` | Doğrulandı |
| B5 | `EventApplication` tekilliği yalnızca view'da; DB kısıtı yok → yarış durumunda çift kayıt | `events/models.py:236-241`, `events/views.py:150-190` | Doğrulandı |
| B6 | `unique_national_id_per_jam` kısıtı boş hash'i ayırt etmiyor: T.C. kimliği olmayan ikinci başvuru `IntegrityError` veriyor | `jams/models.py:145-148` | Doğrulandı (DB şemasından) |
| B7 | `api_save_event` `event_type`'ı doğrulamıyor; oluşturulan her etkinlik zorla `PUBLISHED` — panelden taslak açılamıyor | `dashboard/views.py:63-145` | Doğrulandı |
| B8 | `run_matchmaker` + `SuggestedTeam` hiçbir URL'e bağlı değil (ölü kod); takım adı numaralandırması 1,3,5… diye atlıyor; reddedilmiş başvurular da eşleştiriliyor | `jams/services.py` | Doğrulandı |
| B9 | Lint/format aracı ve CI yok; `jams/`, `pages/`, `dashboard/` testleri 3 satırlık stub | Depo geneli | Doğrulandı |

**B1 detayı — lokal ortamın gerçek durumu:**

```
venv:      nh3 YOK; django-cryptography ve python-decouple artık (requirements'tan çıkarılmış)
.env:      FERNET_KEY satırı YOK  → core.crypto.get_fernet() ImproperlyConfigured fırlatır
db.sqlite3 uygulanmayan migration'lar:
           events   0008_eventimage
           events   0009_event_is_pinned_raffleparticipant_guest_name_and_more
           events   0010_eventapplication_kvkk_accepted_and_more
           jams     0008_reencrypt_national_ids
           jams     0009_jamapplication_health_consent_and_more
           pages    0001_initial
           dashboard 0009_alter_securitylog_action
veri:      3 JamApplication (eski SECRET_KEY türevli anahtarla şifreli),
           53 kullanıcı, 49 çekiliş katılımcısı, 5 etkinlik, 9 duyuru
```

**Kritik sıra:** `FERNET_KEY` **migrate'ten ÖNCE** eklenmelidir. `jams/0008_reencrypt_national_ids`
kayıt varken `FERNET_KEY` yoksa `RuntimeError` ile durur.

---

## Dosya Yapısı

**Oluşturulacak:**

| Dosya | Sorumluluk |
|---|---|
| `core/http.py` | `get_client_ip(request)` — tek gerçek IP kaynağı |
| `events/migrations/0011_eventapplication_uniqueness.py` | `EventApplication` tekillik kısıtları |
| `jams/migrations/0010_fix_national_id_hash_constraint.py` | Boş hash'i kısıttan muaf tutan koşullu kısıt |
| `templates/dashboard/matchmaker.html` | Takım eşleştirme ekranı |
| `ruff.toml` | Lint yapılandırması (paket sanılmasın diye `pyproject.toml` değil) |
| `.pre-commit-config.yaml` | Commit öncesi ruff |
| `.github/workflows/ci.yml` | Her push'ta ruff + test |

**Değiştirilecek:**

| Dosya | Değişiklik |
|---|---|
| `.env` | `FERNET_KEY` (lokal, gitignored) |
| `requirements/development.txt` | `ruff`, `pre-commit` |
| `users/views.py` | B2 duyuru sorgusu, B3 IP, B4 başvuru sorgusu |
| `users/api.py`, `pages/api.py`, `events/views.py` | B3 IP |
| `events/views.py` | B4 `applicant`, B5 `IntegrityError` |
| `events/models.py`, `jams/models.py` | B5/B6 `Meta.constraints` |
| `dashboard/views.py` | B7 doğrulama, Matchmaker view'ları |
| `dashboard/urls.py` | Matchmaker rotaları |
| `templates/dashboard/base.html` | Kenar çubuğuna Matchmaker linki |
| `templates/dashboard/events.html` | Yayın durumu seçici |
| `jams/services.py` | B8 servis düzeltmeleri |
| `core/tests.py`, `events/tests.py`, `users/tests.py` | Yeni testler |
| `jams/tests.py`, `pages/tests.py`, `dashboard/tests.py` | Stub → gerçek test |

---

## Görev 1: Lokal geliştirme ortamını çalışır hâle getir

Diğer her görevin ön koşulu. Bu görev bitmeden hiçbir test çalıştırılamaz.

**Dosyalar:**
- Değiştir: `.env` (gitignored — depoya girmez)
- Değiştir: `db.sqlite3` (gitignored)

**Arayüzler:**
- Üretir: Çalışan `venv` + güncel şema. Sonraki tüm görevler
  `venv/Scripts/python.exe manage.py test` komutunun çalışmasına dayanır.

- [ ] **Adım 1: Mevcut kırıklığı gözle doğrula**

```bash
venv/Scripts/python.exe manage.py check
```

Beklenen: `InvalidTemplateLibrary: ... No module named 'nh3'` ile başarısız.

- [ ] **Adım 2: Geliştirme bağımlılıklarını kur**

```bash
venv/Scripts/python.exe -m pip install -r requirements/development.txt
```

`nh3`, `django-debug-toolbar`, `django-extensions` gelir.

- [ ] **Adım 3: Requirements'tan çıkarılmış artık paketleri kaldır**

```bash
venv/Scripts/python.exe -m pip uninstall -y django-cryptography python-decouple django-appconf
```

Gerekçe: `django-cryptography` denetim raporu madde 26'da kaldırıldı (kod
doğrudan `cryptography.fernet` kullanıyor), `python-decouple` madde 24'te
tekleştirildi (tek konfigürasyon mekanizması `django-environ`).
`django-appconf` yalnızca `django-cryptography`'nin bağımlılığıydı.

- [ ] **Adım 4: FERNET_KEY üret**

```bash
venv/Scripts/python.exe -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Çıktıyı kopyalayın.

- [ ] **Adım 5: FERNET_KEY'i .env'e ekle**

`.env` dosyasında `DJANGO_SECRET_KEY=` satırının hemen altına ekleyin:

```env
# Kişisel veri (T.C. Kimlik No) şifreleme anahtarı — SECRET_KEY'den bağımsız.
FERNET_KEY=<adim-4-ciktisi>
```

**UYARI:** Bu adım Adım 6'dan **önce** yapılmalıdır. `jams/0008_reencrypt_national_ids`
migration'ı `FERNET_KEY` yoksa `RuntimeError` fırlatır.

- [ ] **Adım 6: Sistem kontrolünün geçtiğini doğrula**

```bash
venv/Scripts/python.exe manage.py check
```

Beklenen: `System check identified no issues (0 silenced).`

- [ ] **Adım 7: Bekleyen migration'ları listele**

```bash
venv/Scripts/python.exe manage.py showmigrations --plan | grep "\[ \]"
```

Beklenen: 7 satır (events 0008/0009/0010, jams 0008/0009, pages 0001,
dashboard 0009).

- [ ] **Adım 8: Migrate et**

```bash
venv/Scripts/python.exe manage.py migrate
```

Beklenen: 7 migration uygulanır, hata yok.

Not: `jams.0008_reencrypt_national_ids` mevcut 3 test kaydını eski
`SECRET_KEY` türevli anahtardan yeni `FERNET_KEY`'e taşır. Lokal `SECRET_KEY`
o kayıtlar oluşturulduğundan beri değiştiyse çözme başarısız olur ve migration
o kayıtları **sessizce atlar** (hata vermez, `_plaintext()` `None` döner).
Bu 3 kayıt test verisidir; okunamaz kalması sorun değildir.

- [ ] **Adım 9: Test paketini çalıştır**

```bash
venv/Scripts/python.exe manage.py test
```

Beklenen: `Ran 27 tests ... OK`

- [ ] **Adım 10: Yasal metinleri yükle (lokalde eksikse)**

```bash
venv/Scripts/python.exe manage.py load_legal_documents --skip-existing
```

Beklenen: 3 belge (`kvkk`, `gizlilik`, `kullanici-sozlesmesi`) oluşturuldu veya
atlandı. Bu olmadan `templates/components/footer.html` içindeki linkler 404 verir.

- [ ] **Adım 11: Doğrulama**

```bash
venv/Scripts/python.exe manage.py test && venv/Scripts/python.exe manage.py showmigrations --plan | grep -c "\[ \]"
```

Beklenen: testler OK, bekleyen migration sayısı `0`.

---

## Görev 2: Duyuru sorgusundaki parantez hatasını düzelt (B2)

**Dosyalar:**
- Değiştir: `users/views.py:57-88` (`DashboardView.get_context_data`)
- Test: `users/tests.py` (yeni `AnnouncementVisibilityTests` sınıfı)

**Arayüzler:**
- Tüketir: `dashboard.models.Announcement`, `users.models.CustomUser.Role`
- Üretir: Davranış değişikliği yok, imza değişmiyor.

**Sorunun kökü:** `query |= Q(target_audience="board")` ifadesi
`published_to_site=True` kısıtının dışına düşüyor. Django'nun ürettiği Q:

```
(OR: (AND: published_to_site=True, (OR: all, custom_users)), target_audience='board')
```

Sonuç: yalnızca e-posta olarak gönderilmek üzere oluşturulan
(`published_to_site=False`) ama hedef kitlesi "board" veya "members" olan bir
duyuru, site içi panelde de görünür. Mevcut veride hiçbir duyuru bu iki hedefi
kullanmadığı için hata **henüz tetiklenmiyor** — ilk hedefli e-posta
duyurusunda tetiklenecek.

- [ ] **Adım 1: Başarısız testi yaz**

`users/tests.py` dosyasının sonuna ekleyin:

```python
class AnnouncementVisibilityTests(TestCase):
    """Site içi duyurular yalnızca published_to_site=True ise görünmeli."""

    def setUp(self):
        self.uye = User.objects.create_user(
            username="uye", email="uye@example.com", password="x", is_verified=True
        )
        self.yonetim = User.objects.create_user(
            username="yk", email="yk@example.com", password="x",
            is_verified=True, is_staff=True, role=User.Role.BOARD,
        )

    def _duyuru(self, baslik, hedef, yayinda):
        from dashboard.models import Announcement
        return Announcement.objects.create(
            title=baslik, content="icerik",
            target_audience=hedef, published_to_site=yayinda,
        )

    def _panel_duyurulari(self, kullanici):
        self.client.force_login(kullanici)
        resp = self.client.get(reverse("users:dashboard"))
        self.assertEqual(resp.status_code, 200)
        return {d.title for d in resp.context["announcements"]}

    def test_email_only_board_announcement_hidden_from_site(self):
        """REGRESYON: published_to_site=False olan 'board' duyurusu sızmamalı."""
        self._duyuru("sadece-mail-board", "board", yayinda=False)
        self.assertNotIn("sadece-mail-board", self._panel_duyurulari(self.yonetim))

    def test_email_only_members_announcement_hidden_from_site(self):
        """REGRESYON: published_to_site=False olan 'members' duyurusu sızmamalı."""
        self._duyuru("sadece-mail-uye", "members", yayinda=False)
        self.assertNotIn("sadece-mail-uye", self._panel_duyurulari(self.uye))

    def test_published_board_announcement_visible_to_board(self):
        self._duyuru("yayinda-board", "board", yayinda=True)
        self.assertIn("yayinda-board", self._panel_duyurulari(self.yonetim))

    def test_board_announcement_hidden_from_regular_member(self):
        self._duyuru("yayinda-board", "board", yayinda=True)
        self.assertNotIn("yayinda-board", self._panel_duyurulari(self.uye))

    def test_published_all_announcement_visible_to_everyone(self):
        self._duyuru("herkese", "all", yayinda=True)
        self.assertIn("herkese", self._panel_duyurulari(self.uye))
        self.assertIn("herkese", self._panel_duyurulari(self.yonetim))

    def test_consented_announcement_visible_when_published(self):
        """6563 sayılı Kanun e-posta/SMS gönderimini düzenler; kullanıcının
        kendi isteğiyle girdiği panelde içerik göstermek ticari elektronik
        ileti değildir. 'consented' hedefi site içinde 'all' gibi davranır."""
        self._duyuru("onaylilara", "consented", yayinda=True)
        self.assertIn("onaylilara", self._panel_duyurulari(self.uye))
```

- [ ] **Adım 2: Testin başarısız olduğunu doğrula**

```bash
venv/Scripts/python.exe manage.py test users.tests.AnnouncementVisibilityTests -v 2
```

Beklenen: `test_email_only_board_announcement_hidden_from_site` ve
`test_email_only_members_announcement_hidden_from_site` FAIL;
`test_consented_announcement_visible_when_published` FAIL.

- [ ] **Adım 3: Import'ları modül seviyesine taşı**

`users/views.py` dosyasının en üstündeki import bloğunu şu hâle getirin
(fonksiyon içi import'lar kaldırılıyor — AGENTS.md import sırası kuralı):

```python
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView
from django.db.models import Q
from django.shortcuts import redirect, render
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView
from django_ratelimit.decorators import ratelimit

from dashboard.models import Announcement, SecurityLog
from jams.models import JamApplication

from .forms import UserLoginForm, UserProfileUpdateForm, UserRegisterForm

User = get_user_model()
```

- [ ] **Adım 4: Duyuru sorgusunu düzelt**

`users/views.py` içindeki `DashboardView.get_context_data` gövdesinde, duyuru
bloğunu şununla değiştirin:

```python
        # Hedef kitle koşulu ayrı bir Q'da toplanır; published_to_site kısıtı
        # bunun DIŞINDA kalırsa (eski hâli) yalnızca e-posta olarak gönderilen
        # duyurular da site panelinde görünüyordu.
        hedef = Q(target_audience="all") | Q(custom_users=user)

        if user.is_staff or user.role in (User.Role.BOARD, User.Role.ADMIN):
            hedef |= Q(target_audience="board")
        else:
            hedef |= Q(target_audience="members")

        # 6563 sayılı Kanun e-posta/SMS gönderimini düzenler; kullanıcının kendi
        # isteğiyle açtığı panelde içerik göstermek ticari elektronik ileti
        # değildir. Bu yüzden "consented" hedefi site içinde herkese açıktır.
        hedef |= Q(target_audience="consented")

        announcements = (
            Announcement.objects
            .filter(Q(published_to_site=True) & hedef)
            .exclude(dismissed_by=user)
            .distinct()
            .order_by("-created_at")
        )
```

- [ ] **Adım 5: Testlerin geçtiğini doğrula**

```bash
venv/Scripts/python.exe manage.py test users -v 2
```

Beklenen: tüm `users` testleri PASS.

- [ ] **Adım 6: Tüm paketi doğrula**

```bash
venv/Scripts/python.exe manage.py test
```

Beklenen: OK, 33 test.

---

## Görev 3: Güvenlik loglarına gerçek istemci IP'sini yaz (B3)

**Dosyalar:**
- Oluştur: `core/http.py`
- Değiştir: `users/views.py:48-52`, `users/api.py:50-56`, `pages/api.py:106-112`, `events/views.py:55-60`
- Test: `core/tests.py` (yeni `ClientIpTests` sınıfı)

**Arayüzler:**
- Üretir: `core.http.get_client_ip(request) -> str` — her zaman boş olmayan bir
  string döner. Görev 11'deki dashboard testleri bunu kullanmaz; yalnızca
  yukarıdaki 4 çağrı yeri kullanır.

**Sorunun kökü:** `nishdot/settings/production.py:119` rate limit için
`RATELIMIT_IP_META_KEY = "HTTP_X_REAL_IP"` tanımlıyor, ama dört `SecurityLog`
çağrısı da `request.META.get("REMOTE_ADDR", "")` okuyor. Nginx unix soketi
arkasında bu değer proxy'yi gösterir veya boş gelir. `GenericIPAddressField`
PostgreSQL'de `inet` tipine karşılık geldiği için boş string kayıt sırasında
`DataError` verir — yani rate limit tetiklendiğinde log ya yanlış IP yazıyor
ya da hiç yazılamıyor.

- [ ] **Adım 1: Başarısız testi yaz**

`core/tests.py` dosyasının sonuna ekleyin:

```python
class ClientIpTests(TestCase):
    """SecurityLog, rate limit ile AYNI IP kaynağını kullanmalı."""

    def setUp(self):
        from django.test import RequestFactory
        self.factory = RequestFactory()

    def _istek(self, **meta):
        from core.http import get_client_ip
        request = self.factory.get("/")
        request.META.update(meta)
        return get_client_ip(request)

    @override_settings(RATELIMIT_IP_META_KEY="HTTP_X_REAL_IP")
    def test_prefers_configured_meta_key(self):
        """Production'da proxy'nin IP'si değil, X-Real-IP okunmalı."""
        ip = self._istek(HTTP_X_REAL_IP="203.0.113.7", REMOTE_ADDR="127.0.0.1")
        self.assertEqual(ip, "203.0.113.7")

    @override_settings(RATELIMIT_IP_META_KEY="HTTP_X_REAL_IP")
    def test_falls_back_to_remote_addr_when_header_missing(self):
        ip = self._istek(REMOTE_ADDR="198.51.100.4")
        self.assertEqual(ip, "198.51.100.4")

    def test_uses_remote_addr_when_no_meta_key_configured(self):
        """Development'ta RATELIMIT_IP_META_KEY tanımlı değil."""
        ip = self._istek(REMOTE_ADDR="198.51.100.9")
        self.assertEqual(ip, "198.51.100.9")

    def test_never_returns_empty_string(self):
        """GenericIPAddressField boş string kabul etmez (PostgreSQL inet)."""
        from core.http import FALLBACK_IP
        self.assertEqual(self._istek(REMOTE_ADDR=""), FALLBACK_IP)

    @override_settings(RATELIMIT_IP_META_KEY="HTTP_X_FORWARDED_FOR")
    def test_takes_first_address_from_comma_list(self):
        """X-Forwarded-For virgüllü liste olabilir; ilki gerçek istemcidir."""
        ip = self._istek(HTTP_X_FORWARDED_FOR="203.0.113.7, 10.0.0.1", REMOTE_ADDR="10.0.0.1")
        self.assertEqual(ip, "203.0.113.7")
```

`core/tests.py` dosyasının en üstündeki import satırına `override_settings`
ekleyin:

```python
from django.test import TestCase, override_settings
```

- [ ] **Adım 2: Testin başarısız olduğunu doğrula**

```bash
venv/Scripts/python.exe manage.py test core.tests.ClientIpTests -v 2
```

Beklenen: `ModuleNotFoundError: No module named 'core.http'` ile 5 hata.

- [ ] **Adım 3: core/http.py dosyasını oluştur**

```python
"""
İstemci IP Adresi Yardımcıları
===============================

SecurityLog kayıtlarının, django-ratelimit ile AYNI IP kaynağını kullanmasını
sağlar. Bu iki yer ayrışırsa panelde görünen IP ile hız sınırının saydığı IP
farklı olur ve loglar işe yaramaz hâle gelir.
"""

from django.conf import settings

# GenericIPAddressField boş string kabul etmez (PostgreSQL'de inet tipi
# DataError verir). Hiçbir kaynak IP vermezse bu sentinel yazılır — kayıt
# kaybolmaktansa "bilinmiyor" olarak görünmesi yeğdir.
FALLBACK_IP = "0.0.0.0"


def get_client_ip(request):
    """
    İsteğin gerçek istemci IP adresini döndürür.

    Nginx arkasında REMOTE_ADDR proxy'nin kendi adresini gösterir (unix soket
    kullanılıyorsa boş string). Production ayarlarında django-ratelimit
    RATELIMIT_IP_META_KEY üzerinden X-Real-IP okur; bu fonksiyon aynı ayarı
    izleyerek iki taraf arasındaki tutarsızlığı ortadan kaldırır.

    Args:
        request: Django HttpRequest nesnesi.

    Returns:
        Boş olmayan bir IP adresi string'i. Hiçbir kaynak değer vermezse
        FALLBACK_IP döner.
    """
    meta_key = getattr(settings, "RATELIMIT_IP_META_KEY", "") or "REMOTE_ADDR"

    raw = request.META.get(meta_key) or request.META.get("REMOTE_ADDR") or ""

    # X-Forwarded-For biçimindeki başlıklar "istemci, proxy1, proxy2" olabilir;
    # zincirin ilk adresi gerçek istemcidir.
    ip = raw.split(",")[0].strip()

    return ip or FALLBACK_IP
```

- [ ] **Adım 4: Testin geçtiğini doğrula**

```bash
venv/Scripts/python.exe manage.py test core.tests.ClientIpTests -v 2
```

Beklenen: `Ran 5 tests ... OK`

- [ ] **Adım 5: users/views.py çağrı yerini güncelle**

`users/views.py` içindeki `UserLoginView.post` gövdesinde, `SecurityLog.objects.create(`
çağrısının `ip_address=` satırını değiştirin:

```python
            SecurityLog.objects.create(
                ip_address=get_client_ip(request),
                action=SecurityLog.ActionType.LOGIN_BRUTE_FORCE,
                user_agent=request.META.get("HTTP_USER_AGENT", ""),
            )
```

Dosyanın en üstündeki import bloğunda, `from dashboard.models import ...`
satırının **hemen üstüne** ekleyin:

```python
from core.http import get_client_ip
```

- [ ] **Adım 6: users/api.py çağrı yerini güncelle**

`users/api.py` içindeki `_log_rate_limited` fonksiyonunu şununla değiştirin:

```python
def _log_rate_limited(request, action=None):
    SecurityLog.objects.create(
        ip_address=get_client_ip(request),
        action=action or SecurityLog.ActionType.OTP_ABUSE,
        user_agent=request.META.get("HTTP_USER_AGENT", ""),
    )
```

Dosyanın en üstünde `from dashboard.models import SecurityLog` satırının
**hemen üstüne** ekleyin:

```python
from core.http import get_client_ip
```

- [ ] **Adım 7: pages/api.py çağrı yerini güncelle**

`pages/api.py` içindeki `contact_api_view` gövdesinde, `SecurityLog.objects.create(`
çağrısını şununla değiştirin:

```python
        SecurityLog.objects.create(
            ip_address=get_client_ip(request),
            action=SecurityLog.ActionType.CONTACT_SPAM,
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )
```

Dosyanın en üstünde `from dashboard.models import SecurityLog` satırının
**hemen üstüne** ekleyin:

```python
from core.http import get_client_ip
```

- [ ] **Adım 8: events/views.py çağrı yerini güncelle**

`events/views.py` içindeki `EventApplyWizardView.post` gövdesinde,
`SecurityLog.objects.create(` çağrısını şununla değiştirin:

```python
            SecurityLog.objects.create(
                ip_address=get_client_ip(request),
                action=SecurityLog.ActionType.APPLY_SPAM,
                user_agent=request.META.get("HTTP_USER_AGENT", ""),
            )
```

Dosyanın en üstündeki çok satırlı `from core.crypto import (...)` bloğunu
kapatan `)` satırının **hemen altına** ekleyin:

```python
from core.http import get_client_ip
```

- [ ] **Adım 9: Kalan REMOTE_ADDR kullanımı olmadığını doğrula**

```bash
grep -rn "REMOTE_ADDR" --include="*.py" . | grep -v venv | grep -v core/http.py
```

Beklenen: yalnızca `nishdot/settings/production.py` içindeki açıklama yorumu
kalmalı; hiçbir `SecurityLog.objects.create` çağrısı çıkmamalı.

- [ ] **Adım 10: Doğrulama**

```bash
venv/Scripts/python.exe manage.py test
```

Beklenen: OK, 38 test.

- [ ] **Adım 11: Sunucu tarafı doğrulaması (kullanıcı yapar, opsiyonel)**

Canlıda hatanın gerçekten tetiklenip tetiklenmediğini görmek için:

```bash
sudo journalctl -u gunicorn --since "30 days ago" | grep -i "invalid input syntax for type inet"
```

Çıktı varsa hata canlıda log kaybına yol açıyordu; bu görev onu kapatır.

---

## Görev 4: Jam başvurularını kullanıcı hesabına bağla (B4)

**Dosyalar:**
- Değiştir: `events/views.py:113-147` (`JamApplication.objects.create` çağrısı)
- Değiştir: `users/views.py:62-67` (`DashboardView` başvuru sorgusu)
- Test: `events/tests.py` (yeni `JamApplicantLinkTests` sınıfı)

**Arayüzler:**
- Tüketir: `jams.models.JamApplication.applicant` (zaten mevcut, hep NULL)
- Tüketir: Görev 2 Adım 3'te düzenlenen `users/views.py` import bloğu — bu görevin
  Adım 4'ü `Q`, `Announcement`, `User` ve `UserProfileUpdateForm` adlarının modül
  seviyesinde import edilmiş olmasına dayanır. Görev 2 atlanmışsa önce o adımı yapın.
- Üretir: Davranış değişikliği — giriş yapmış kullanıcının jam başvurusu artık
  hesabına bağlanır.

**Sorunun kökü:** `EventApplication` girişte kullanıcıyı bağlıyor
(`events/views.py:171`) ama `JamApplication.objects.create(...)` `applicant`
parametresini hiç geçmiyor — alan her zaman NULL. `users/views.DashboardView`
bu yüzden başvuruları e-posta ile eşleştiriyor; kullanıcı e-postasını
değiştirirse kendi başvurusunu göremiyor.

- [ ] **Adım 1: Başarısız testi yaz**

`events/tests.py` dosyasının sonuna ekleyin:

```python
class JamApplicantLinkTests(TestCase):
    """Giriş yapmış kullanıcının jam başvurusu hesabına bağlanmalı."""

    def setUp(self):
        from jams.models import GameJam

        cache.clear()   # bkz. MediaConsentOptionalTests — rate limit sızıntısı

        self.event = make_event(
            Event.Status.PUBLISHED, slug="baglanti-jam",
            event_type=Event.EventType.GAME_JAM,
        )
        self.jam = GameJam.objects.create(
            event=self.event,
            application_deadline=timezone.now() + timedelta(days=5),
            max_team_size=5,
        )
        self.url = reverse("events:apply", kwargs={"slug": self.event.slug})
        self.user = User.objects.create_user(
            username="basvuran", email="basvuran@example.com",
            password="x", is_verified=True,
        )

    def _payload(self, **extra):
        data = {
            "kvkk_accepted": "on",
            "full_name": "Bağlantı Testi",
            "national_id": "12345678950",
            "email": "basvuran@example.com",
            "phone_number": "05001112233",
            "birth_date": "2002-01-01",
            "university": "İstanbul Nişantaşı Üniversitesi",
            "department": "Dijital Oyun Tasarımı",
            "grade": "3",
            "emergency_contact": "Veli Kişi - 05009998877",
            "team_status": "solo",
            "jam_role": "Developer",
            "experience_level": "Intermediate",
            "motivation": "Katılmak istiyorum.",
        }
        data.update(extra)
        return data

    def test_logged_in_applicant_is_linked(self):
        from jams.models import JamApplication

        self.client.force_login(self.user)
        self.client.post(self.url, data=self._payload())

        app = JamApplication.objects.get(jam=self.jam)
        self.assertEqual(app.applicant, self.user)

    def test_anonymous_applicant_stays_null(self):
        from jams.models import JamApplication

        self.client.post(self.url, data=self._payload())

        app = JamApplication.objects.get(jam=self.jam)
        self.assertIsNone(app.applicant)

    def test_dashboard_finds_application_after_email_change(self):
        """REGRESYON: e-posta değişse bile başvuru panelde görünmeli."""
        self.client.force_login(self.user)
        self.client.post(self.url, data=self._payload())

        self.user.email = "yeni-adres@example.com"
        self.user.save(update_fields=["email"])

        resp = self.client.get(reverse("users:dashboard"))
        self.assertEqual(len(resp.context["applications"]), 1)

    def test_dashboard_still_finds_application_by_email(self):
        """Hesap açılmadan yapılmış eski başvurular e-postayla eşleşmeye devam etmeli."""
        from jams.models import JamApplication

        self.client.post(self.url, data=self._payload())   # anonim başvuru
        self.client.force_login(self.user)

        resp = self.client.get(reverse("users:dashboard"))
        self.assertEqual(len(resp.context["applications"]), 1)
        self.assertIsNone(JamApplication.objects.get(jam=self.jam).applicant)
```

- [ ] **Adım 2: Testin başarısız olduğunu doğrula**

```bash
venv/Scripts/python.exe manage.py test events.tests.JamApplicantLinkTests -v 2
```

Beklenen: `test_logged_in_applicant_is_linked` ve
`test_dashboard_finds_application_after_email_change` FAIL.

- [ ] **Adım 3: Başvuruyu kullanıcıya bağla**

`events/views.py` içinde, jam dalındaki `JamApplication.objects.create(` çağrısında
`jam=jam,` satırının hemen altına ekleyin:

```python
                    applicant=request.user if request.user.is_authenticated else None,
```

- [ ] **Adım 4: Panel sorgusunu genişlet**

`users/views.py` içindeki `DashboardView.get_context_data` gövdesinde, başvuru
sorgusunu şununla değiştirin:

```python
        # Başvuru ya hesaba doğrudan bağlıdır (yeni kayıtlar) ya da yalnızca
        # e-posta ile eşleşir (hesap açılmadan önce yapılmış eski başvurular).
        # select_related olmadan şablondaki jam.event.title her satırda iki
        # ekstra sorgu atar.
        applications = (
            JamApplication.objects
            .filter(Q(applicant=user) | Q(email__iexact=user.email))
            .select_related("jam__event")
            .distinct()
            .order_by("-created_at")
        )
```

Bu bloğun üstündeki `user_email = self.request.user.email` satırını silin ve
`user = self.request.user` satırının duyuru bloğundan **önce** tanımlandığından
emin olun. Metodun tamamı şu hâle gelmelidir:

```python
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Başvuru ya hesaba doğrudan bağlıdır (yeni kayıtlar) ya da yalnızca
        # e-posta ile eşleşir (hesap açılmadan önce yapılmış eski başvurular).
        # select_related olmadan şablondaki jam.event.title her satırda iki
        # ekstra sorgu atar.
        applications = (
            JamApplication.objects
            .filter(Q(applicant=user) | Q(email__iexact=user.email))
            .select_related("jam__event")
            .distinct()
            .order_by("-created_at")
        )

        # Hedef kitle koşulu ayrı bir Q'da toplanır; published_to_site kısıtı
        # bunun DIŞINDA kalırsa (eski hâli) yalnızca e-posta olarak gönderilen
        # duyurular da site panelinde görünüyordu.
        hedef = Q(target_audience="all") | Q(custom_users=user)

        if user.is_staff or user.role in (User.Role.BOARD, User.Role.ADMIN):
            hedef |= Q(target_audience="board")
        else:
            hedef |= Q(target_audience="members")

        # 6563 sayılı Kanun e-posta/SMS gönderimini düzenler; kullanıcının kendi
        # isteğiyle açtığı panelde içerik göstermek ticari elektronik ileti
        # değildir. Bu yüzden "consented" hedefi site içinde herkese açıktır.
        hedef |= Q(target_audience="consented")

        announcements = (
            Announcement.objects
            .filter(Q(published_to_site=True) & hedef)
            .exclude(dismissed_by=user)
            .distinct()
            .order_by("-created_at")
        )

        context["applications"] = applications
        context["announcements"] = announcements
        if "form" not in context:
            context["form"] = UserProfileUpdateForm(instance=user)
        return context
```

- [ ] **Adım 5: Testlerin geçtiğini doğrula**

```bash
venv/Scripts/python.exe manage.py test events.tests.JamApplicantLinkTests users -v 2
```

Beklenen: hepsi PASS.

- [ ] **Adım 6: Doğrulama**

```bash
venv/Scripts/python.exe manage.py test
```

Beklenen: OK, 42 test.

---

## Görev 5: Başvuru tekilliğini veritabanı kısıtıyla garanti et (B5, B6)

**Dosyalar:**
- Değiştir: `events/models.py:236-241` (`EventApplication.Meta`)
- Değiştir: `jams/models.py:145-148` (`JamApplication.Meta.constraints`)
- Oluştur: `events/migrations/0011_eventapplication_uniqueness.py`
- Oluştur: `jams/migrations/0010_fix_national_id_hash_constraint.py`
- Değiştir: `events/views.py:165-190` (non-jam dalı `IntegrityError` yakalaması)
- Test: `events/tests.py` (yeni `ApplicationUniquenessTests` sınıfı)

**Arayüzler:**
- Tüketir: Görev 4'teki `events/views.py` değişiklikleri (aynı dosya, farklı blok)
- Üretir: Şema kısıtları. Sonraki görevler etkilenmez.

**İki ayrı sorun:**

**B5** — `EventApplication` tekilliği yalnızca `filter().exists()` ile view'da
kontrol ediliyor. Kullanıcı gönder tuşuna iki kez basarsa iki istek arasında
yarış oluşur ve çift kayıt yazılabilir. `JamApplication`'da DB kısıtı var,
burada yok.

**B6** — `jams_jamapplication` tablosundaki gerçek kısıt:
`CONSTRAINT "unique_national_id_per_jam" UNIQUE ("jam_id", "national_id_hash")`
ve `national_id_hash varchar(64) NOT NULL`. Yani T.C. kimliği olmayan iki
başvuru aynı jam'de `''` hash'i paylaşır ve ikincisi `IntegrityError` alır.
View jam başvurularında T.C. kimliğini zorunlu tuttuğu için arayüzden
tetiklenmiyor, ama admin panelinden veya shell'den eklenen kayıt patlar.
Aynı tuzağa `EventApplication` için düşmemek gerekir: orada Nişantaşı
öğrencilerinin hash'i **her zaman** boştur.

- [ ] **Adım 1: Başarısız testi yaz**

`events/tests.py` dosyasının sonuna ekleyin:

```python
class ApplicationUniquenessTests(TestCase):
    """Tekillik view'da değil, veritabanı kısıtıyla garanti edilmeli."""

    def setUp(self):
        cache.clear()
        self.event = make_event(Event.Status.PUBLISHED, slug="tekillik-etkinlik")

    def _basvuru(self, email, national_id="", **extra):
        return EventApplication.objects.create(
            event=self.event, full_name="Test Kişi", email=email,
            university="X", department="Y", grade="1",
            is_nisantasi_student=not national_id,
            national_id=national_id, **extra,
        )

    def test_duplicate_email_rejected_by_database(self):
        from django.db import IntegrityError, transaction

        self._basvuru("ayni@example.com")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self._basvuru("ayni@example.com")

    def test_duplicate_national_id_rejected_by_database(self):
        from django.db import IntegrityError, transaction

        self._basvuru("bir@example.com", national_id="12345678950")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self._basvuru("iki@example.com", national_id="12345678950")

    def test_multiple_applicants_without_national_id_allowed(self):
        """REGRESYON: T.C. kimliği alınmayan öğrencilerin hash'i '' olur —
        koşullu kısıt olmazsa ikinci öğrenci kaydedilemez."""
        self._basvuru("ogrenci1@example.com")
        self._basvuru("ogrenci2@example.com")
        self.assertEqual(EventApplication.objects.filter(event=self.event).count(), 2)

    def test_same_email_allowed_on_different_events(self):
        digeri = make_event(Event.Status.PUBLISHED, slug="baska-etkinlik")
        self._basvuru("ayni@example.com")
        EventApplication.objects.create(
            event=digeri, full_name="Test Kişi", email="ayni@example.com",
            university="X", department="Y", grade="1", is_nisantasi_student=True,
        )
        self.assertEqual(EventApplication.objects.count(), 2)


class JamApplicationEmptyHashTests(TestCase):
    """REGRESYON: T.C. kimliği olmayan iki jam başvurusu çakışmamalı."""

    def setUp(self):
        from jams.models import GameJam

        self.event = make_event(
            Event.Status.PUBLISHED, slug="bos-hash-jam",
            event_type=Event.EventType.GAME_JAM,
        )
        self.jam = GameJam.objects.create(
            event=self.event,
            application_deadline=timezone.now() + timedelta(days=5),
            max_team_size=5,
        )

    def test_two_applications_without_national_id_allowed(self):
        from jams.models import JamApplication

        JamApplication.objects.create(
            jam=self.jam, full_name="Bir", email="bir@example.com",
            jam_role="Developer", team_status="solo", kvkk_accepted=True,
        )
        JamApplication.objects.create(
            jam=self.jam, full_name="İki", email="iki@example.com",
            jam_role="Artist", team_status="solo", kvkk_accepted=True,
        )
        self.assertEqual(JamApplication.objects.filter(jam=self.jam).count(), 2)
```

- [ ] **Adım 2: Testin başarısız olduğunu doğrula**

```bash
venv/Scripts/python.exe manage.py test events.tests.ApplicationUniquenessTests events.tests.JamApplicationEmptyHashTests -v 2
```

Beklenen: `test_duplicate_email_rejected_by_database`,
`test_duplicate_national_id_rejected_by_database` FAIL (kısıt yok, hata
fırlatılmıyor); `test_two_applications_without_national_id_allowed` FAIL
(`IntegrityError: UNIQUE constraint failed`).

- [ ] **Adım 3: EventApplication.Meta'ya kısıtları ekle**

`events/models.py` içinde `EventApplication.Meta` sınıfını şununla değiştirin:

```python
    class Meta(TimeStampedModel.Meta):
        verbose_name = "Etkinlik Başvurusu"
        verbose_name_plural = "Etkinlik Başvuruları"
        constraints = [
            models.UniqueConstraint(
                fields=["event", "email"],
                name="unique_event_application_per_email",
            ),
            # Koşul ŞART: Nişantaşı öğrencilerinden T.C. kimlik alınmadığı için
            # hash alanı '' kalır. Koşulsuz bir kısıt, aynı etkinliğe kaydolan
            # ikinci öğrenciyi IntegrityError ile reddederdi.
            models.UniqueConstraint(
                fields=["event", "national_id_hash"],
                condition=~models.Q(national_id_hash=""),
                name="unique_event_application_per_national_id",
            ),
        ]
```

- [ ] **Adım 4: JamApplication kısıtını koşullu hâle getir**

`jams/models.py` içinde `JamApplication.Meta.constraints` listesini şununla
değiştirin:

```python
        constraints = [
            models.UniqueConstraint(fields=["jam", "email"], name="unique_application_per_jam"),
            # Koşul ŞART: T.C. kimliği girilmemiş başvurularda hash '' olur ve
            # koşulsuz kısıt aynı jam'deki ikinci böyle kaydı reddederdi.
            models.UniqueConstraint(
                fields=["jam", "national_id_hash"],
                condition=~models.Q(national_id_hash=""),
                name="unique_national_id_per_jam",
            ),
        ]
```

- [ ] **Adım 5: Migration'ları üret**

```bash
venv/Scripts/python.exe manage.py makemigrations events jams
```

Beklenen: `events/migrations/0011_*.py` ve `jams/migrations/0010_*.py`
oluşturulur. Dosya adları planda öngörülenden farklı olabilir — sorun değil,
Django'nun ürettiği adı kullanın.

- [ ] **Adım 6: Üretilen migration'ı gözden geçir**

```bash
cat events/migrations/0011_*.py jams/migrations/0010_*.py
```

`jams` migration'ında önce `RemoveConstraint`, sonra `AddConstraint`
bulunmalıdır (aynı isimli kısıt değiştiriliyor). `events` migration'ında iki
`AddConstraint` olmalıdır.

- [ ] **Adım 7: Migrate et**

```bash
venv/Scripts/python.exe manage.py migrate
```

Beklenen: hatasız. Lokal veride çakışma yok (kontrol edildi: 0 çift e-posta,
0 çift hash).

- [ ] **Adım 8: Yarış durumunu view'da kullanıcıya anlamlı mesajla göster**

`events/views.py` içinde, jam **dışı** dalın `try` bloğundaki `except Exception:`
satırının **üstüne** ayrı bir `except` ekleyin:

```python
            except IntegrityError:
                # Kullanıcı gönder tuşuna iki kez bastıysa view'daki exists()
                # kontrolü ile INSERT arasında yarış oluşur; DB kısıtı yakalar.
                error_msg = "Bu etkinliğe zaten kayıtlısınız. Bir sorun olduğunu düşünüyorsanız lütfen bizimle iletişime geçin."
                return self.render_to_response(self.get_context_data(error=error_msg))
```

`IntegrityError` zaten `events/views.py` başında import edilmiş durumda
(`from django.db import IntegrityError`) — yeni import gerekmez.

- [ ] **Adım 9: Testlerin geçtiğini doğrula**

```bash
venv/Scripts/python.exe manage.py test events -v 2
```

Beklenen: tüm `events` testleri PASS.

- [ ] **Adım 10: Doğrulama**

```bash
venv/Scripts/python.exe manage.py test
```

Beklenen: OK, 47 test.

- [ ] **Adım 11: Canlıya alma notunu deployment dokümanına ekle**

`deployment_instructions.md` dosyasının sonundaki
"⚠️ BU GÜVENLİK GÜNCELLEMESİNİ İLK KEZ DEPLOY EDERKEN" bölümünün **altına**
yeni bir bölüm ekleyin:

````markdown
---

## ⚠️ TEKİLLİK KISITLARI EKLENİRKEN (tek seferlik)

`events/0011` ve `jams/0010` migration'ları veritabanına tekillik kısıtı ekler.
Canlıda çift kayıt varsa migration `IntegrityError` ile durur ve deploy yarıda
kalır. **Migrate etmeden ÖNCE** çakışma olup olmadığını kontrol edin:

```bash
cd /var/www/nishdot-web
source venv/bin/activate
export DJANGO_SETTINGS_MODULE=nishdot.settings.production
python manage.py shell -c "
from django.db.models import Count
from events.models import EventApplication
from jams.models import JamApplication

for ad, qs, alanlar in [
    ('EventApplication e-posta', EventApplication.objects, ('event', 'email')),
    ('EventApplication kimlik', EventApplication.objects.exclude(national_id_hash=''), ('event', 'national_id_hash')),
    ('JamApplication kimlik', JamApplication.objects.exclude(national_id_hash=''), ('jam', 'national_id_hash')),
]:
    cakisan = qs.values(*alanlar).annotate(n=Count('id')).filter(n__gt=1)
    print(f'{ad}: {len(cakisan)} cakisma')
    for c in cakisan:
        print('   ', c)
"
```

Hepsi `0 cakisma` diyorsa doğrudan `migrate` edebilirsiniz. Çakışma varsa,
her grupta **en eski** kaydı tutup diğerlerini panelden veya admin'den elle
silin — migration'ın kişisel veriyi kendi başına silmesine izin verilmez.
````

---

## Görev 6: Etkinlik oluşturucuda tip doğrulaması ve taslak desteği (B7)

**Dosyalar:**
- Değiştir: `dashboard/views.py:63-145` (`api_save_event`)
- Değiştir: `templates/dashboard/events.html:134-144` (tip seçicinin altına durum seçici), `templates/dashboard/events.html:269-313` (`openEventModal`), `templates/dashboard/events.html:352-366` (formData)
- Test: `dashboard/tests.py` (yeni `EventBuilderValidationTests` sınıfı)

**Arayüzler:**
- Tüketir: `events.models.Event.EventType`, `events.models.Event.Status`
- Üretir: `api_save_event` artık `status` POST alanını kabul eder (opsiyonel;
  verilmezse yeni etkinlik `published`, mevcut etkinlik dokunulmadan kalır).

**Sorunun kökü:** `api_save_event` `event_type`'ı choices'a karşı doğrulamıyor —
`data.get("event_type", Event.EventType.GAME_JAM)` ile gelen keyfî string
doğrudan `CharField`'a yazılıyor. Ayrıca yeni etkinlik her zaman
`status=Event.Status.PUBLISHED` ile oluşturuluyor; `visible_events_for()` taslak
desteklediği hâlde panelden taslak açmak mümkün değil.

- [ ] **Adım 1: Başarısız testi yaz**

`dashboard/tests.py` dosyasının tamamını şununla değiştirin:

```python
"""
Etkinlik oluşturucu doğrulama testleri.
"""
import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from events.models import Event

User = get_user_model()


class EventBuilderValidationTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            username="builder", email="builder@example.com", password="x", is_staff=True
        )
        self.client.force_login(self.staff)
        self.url = reverse("dashboard:api_save_event")

    def _payload(self, **extra):
        data = {
            "title": "Test Atölyesi",
            "description": "<p>Açıklama</p>",
            "event_type": Event.EventType.WORKSHOP,
            "start_date": "2026-09-01T10:00",
            "end_date": "2026-09-01T18:00",
            "location": "Kampüs",
            "is_applications_open": "true",
        }
        data.update(extra)
        return data

    def test_valid_event_is_created_as_published_by_default(self):
        resp = self.client.post(self.url, data=self._payload())
        self.assertEqual(resp.status_code, 200)
        etkinlik = Event.objects.get(title="Test Atölyesi")
        self.assertEqual(etkinlik.status, Event.Status.PUBLISHED)

    def test_draft_status_is_honoured(self):
        resp = self.client.post(self.url, data=self._payload(status=Event.Status.DRAFT))
        self.assertEqual(resp.status_code, 200)
        etkinlik = Event.objects.get(title="Test Atölyesi")
        self.assertEqual(etkinlik.status, Event.Status.DRAFT)

    def test_invalid_event_type_rejected(self):
        resp = self.client.post(self.url, data=self._payload(event_type="hacker"))
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(Event.objects.filter(title="Test Atölyesi").exists())

    def test_invalid_status_rejected(self):
        resp = self.client.post(self.url, data=self._payload(status="yayinda-degil"))
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(Event.objects.filter(title="Test Atölyesi").exists())

    def test_status_can_be_changed_on_existing_event(self):
        resp = self.client.post(self.url, data=self._payload())
        etkinlik_id = json.loads(resp.content)["event_id"]

        self.client.post(self.url, data=self._payload(
            event_id=etkinlik_id, status=Event.Status.COMPLETED,
        ))
        etkinlik = Event.objects.get(id=etkinlik_id)
        self.assertEqual(etkinlik.status, Event.Status.COMPLETED)

    def test_non_staff_cannot_save_event(self):
        self.client.logout()
        resp = self.client.post(self.url, data=self._payload())
        self.assertNotEqual(resp.status_code, 200)
        self.assertFalse(Event.objects.filter(title="Test Atölyesi").exists())
```

- [ ] **Adım 2: Testin başarısız olduğunu doğrula**

```bash
venv/Scripts/python.exe manage.py test dashboard -v 2
```

Beklenen: `test_draft_status_is_honoured`, `test_invalid_event_type_rejected`,
`test_invalid_status_rejected`, `test_status_can_be_changed_on_existing_event`
FAIL.

- [ ] **Adım 3: api_save_event'e doğrulama ekle**

`dashboard/views.py` içinde `api_save_event` fonksiyonunda,
`event_type = data.get('event_type', Event.EventType.GAME_JAM)` satırının
hemen **altına** ekleyin:

```python

        # Choices doğrulaması: CharField keyfî string kabul eder, model
        # seviyesinde full_clean() çağrılmadığı için burada kapatılmalı.
        if event_type not in Event.EventType.values:
            return JsonResponse(
                {'success': False, 'error': 'Geçersiz etkinlik tipi.'}, status=400
            )

        # Durum opsiyoneldir: yeni etkinlikte varsayılan "yayında", mevcut
        # etkinlikte gönderilmezse dokunulmaz.
        status = data.get('status') or None
        if status is not None and status not in Event.Status.values:
            return JsonResponse(
                {'success': False, 'error': 'Geçersiz etkinlik durumu.'}, status=400
            )
```

- [ ] **Adım 4: Mevcut etkinlikte durumu güncelle**

Aynı fonksiyonda, `if event_id:` dalında `event.is_applications_open = is_open`
satırının hemen **altına** ekleyin:

```python
                if status is not None:
                    event.status = status
```

- [ ] **Adım 5: Yeni etkinlikte durumu kullan**

Aynı fonksiyonda, `else:` dalındaki `Event.objects.create(` çağrısında
`status=Event.Status.PUBLISHED,` satırını şununla değiştirin:

```python
                    status=status or Event.Status.PUBLISHED,
```

- [ ] **Adım 6: Testin geçtiğini doğrula**

```bash
venv/Scripts/python.exe manage.py test dashboard -v 2
```

Beklenen: `Ran 6 tests ... OK`

- [ ] **Adım 7: Şablona durum seçicisini ekle**

`templates/dashboard/events.html` içinde, "Tip Seçimi" bloğunu (`<!-- Tip Seçimi -->`
yorumuyla başlayan `div`) kapsayan `</div>` etiketinden sonra, "Kapak Görseli"
bloğunun **üstüne** ekleyin:

```html
                    <!-- Yayın Durumu -->
                    <div class="col-span-full">
                        <label for="evPublishStatus" class="block text-sm font-medium text-zinc-300 mb-2">Yayın Durumu</label>
                        <select id="evPublishStatus" class="w-full bg-zinc-950 border border-zinc-800 text-white rounded-xl px-4 py-3 focus:outline-none focus:border-brand-pink transition-all">
                            <option value="published">Yayında</option>
                            <option value="draft">Taslak (yalnızca yönetim görür)</option>
                            <option value="completed">Tamamlandı</option>
                            <option value="cancelled">İptal Edildi</option>
                        </select>
                        <p class="text-xs text-zinc-500 mt-2">Taslak etkinlikler ana sayfada listelenmez ve doğrudan bağlantıyla açılamaz.</p>
                    </div>
```

- [ ] **Adım 8: Modal açılışında durumu doldur**

Aynı dosyada, `openEventModal` fonksiyonunda **iki** yere ekleme yapılır.

(a) Formun sıfırlandığı blokta, şu satırın hemen **altına**:

```javascript
        document.getElementById('evStatus').checked = true;
```

ekleyin:

```javascript
        document.getElementById('evPublishStatus').value = "published";
```

(b) Mevcut etkinliğin okunduğu `if (dataDiv) {` bloğunda, şu satırın hemen
**altına**:

```javascript
                document.getElementById('evStatus').checked = dataDiv.getAttribute('data-isopen') === 'true';
```

ekleyin:

```javascript
                document.getElementById('evPublishStatus').value = dataDiv.getAttribute('data-status') || 'published';
```

Not: Bu dosya `dataset` değil `getAttribute` kullanıyor; mevcut üsluba uyun.

- [ ] **Adım 9: Veri deposuna status özniteliğini ekle**

Aynı dosyada, `<!-- Modal Data Store -->` bölümünde şu satırın hemen **altına**:

```html
         data-isopen="{{ event.is_applications_open|yesno:'true,false' }}"
```

ekleyin:

```html
         data-status="{{ event.status }}"
```

- [ ] **Adım 10: formData'ya status'ü ekle**

Aynı dosyada, `eventForm` submit handler'ında
`formData.append('is_applications_open', document.getElementById('evStatus').checked);`
satırının hemen **altına** ekleyin:

```javascript
        formData.append('status', document.getElementById('evPublishStatus').value);
```

Not: `evStatus` mevcut kodda **başvuruların açık olup olmadığı** onay kutusudur;
yeni eklenen `evPublishStatus` ise etkinliğin yayın durumudur. İkisi ayrı
alanlardır, karıştırmayın.

- [ ] **Adım 11: Tarayıcıda elle doğrula**

```bash
venv/Scripts/python.exe manage.py runserver
```

`http://127.0.0.1:8000/management/events/` adresinde staff hesabıyla:
1. Yeni etkinlik oluştur, durumu "Taslak" seç → kaydet
2. Ana sayfada (`/`) etkinliğin **görünmediğini** doğrula
3. Panelden durumu "Yayında" yap → ana sayfada göründüğünü doğrula

- [ ] **Adım 12: Doğrulama**

```bash
venv/Scripts/python.exe manage.py test
```

Beklenen: OK, 53 test.

---

## Görev 7: Matchmaker servisini düzelt ve testle (B8, 1/2)

**Dosyalar:**
- Değiştir: `jams/services.py` (tamamı)
- Test: `jams/tests.py` (stub → gerçek test)

**Arayüzler:**
- Üretir: `jams.services.run_matchmaker(jam: GameJam) -> list[SuggestedTeam]` —
  imza aynı kalır. Görev 8'deki `api_run_matchmaker` bunu çağırır.
- Üretir: `jams.services.reset_matchmaker(jam: GameJam) -> int` — jam'in tüm
  önerilen takımlarını siler, silinen takım sayısını döndürür. Görev 8'deki
  `api_reset_matchmaker` bunu çağırır.

**Üç sorun:**
1. `f"Takım {jam.suggested_teams.count() + len(suggested_teams) + 1}"` — `count()`
   döngü içinde yeniden sorgulanıp yeni oluşturulanları da saydığı için
   `len(suggested_teams)` ile çift sayım oluyor; takım adları 1, 3, 5… diye atlıyor.
2. Reddedilmiş başvurular da eşleştiriliyor.
3. Üye ataması `member.save(update_fields=[...])` ile üye başına bir sorgu atıyor.

- [ ] **Adım 1: Başarısız testi yaz**

`jams/tests.py` dosyasının tamamını şununla değiştirin:

```python
"""
Matchmaker servisi testleri.
"""
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from events.models import Event
from jams.models import GameJam, JamApplication, SuggestedTeam
from jams.services import reset_matchmaker, run_matchmaker


class MatchmakerTests(TestCase):
    def setUp(self):
        simdi = timezone.now()
        self.event = Event.objects.create(
            title="Eşleştirme Jam", slug="eslestirme-jam", description="x",
            event_type=Event.EventType.GAME_JAM, status=Event.Status.PUBLISHED,
            start_date=simdi, end_date=simdi + timedelta(days=2), location="Kampüs",
        )
        self.jam = GameJam.objects.create(
            event=self.event, application_deadline=simdi, max_team_size=4,
        )

    def _basvuru(self, ad, rol, team_status=JamApplication.TeamStatus.LOOKING,
                 status=JamApplication.ApplicationStatus.PENDING):
        return JamApplication.objects.create(
            jam=self.jam, full_name=ad, email=f"{ad.lower()}@example.com",
            jam_role=rol, team_status=team_status, status=status,
            kvkk_accepted=True,
        )

    def test_groups_different_roles_into_one_team(self):
        self._basvuru("Ali", "Developer")
        self._basvuru("Veli", "2D Artist")
        self._basvuru("Ayse", "Game Designer")

        takimlar = run_matchmaker(self.jam)

        self.assertEqual(len(takimlar), 1)
        self.assertEqual(takimlar[0].members.count(), 3)

    def test_respects_max_team_size(self):
        for i, rol in enumerate(["Developer", "2D Artist", "3D Artist", "Game Designer", "Sound Designer"]):
            self._basvuru(f"Kisi{i}", rol)

        takimlar = run_matchmaker(self.jam)

        self.assertEqual(takimlar[0].members.count(), 4)   # max_team_size=4

    def test_rejected_applicants_are_excluded(self):
        self._basvuru("Ali", "Developer")
        self._basvuru("Veli", "2D Artist")
        self._basvuru("Red", "3D Artist", status=JamApplication.ApplicationStatus.REJECTED)

        takimlar = run_matchmaker(self.jam)

        isimler = {u.full_name for u in takimlar[0].members.all()}
        self.assertNotIn("Red", isimler)

    def test_only_looking_applicants_are_matched(self):
        self._basvuru("Ali", "Developer")
        self._basvuru("Veli", "2D Artist")
        self._basvuru("Solo", "3D Artist", team_status=JamApplication.TeamStatus.SOLO)
        self._basvuru("Ekipli", "Sound Designer", team_status=JamApplication.TeamStatus.HAS_TEAM)

        takimlar = run_matchmaker(self.jam)

        isimler = {u.full_name for u in takimlar[0].members.all()}
        self.assertEqual(isimler, {"Ali", "Veli"})

    def test_single_leftover_is_not_teamed_alone(self):
        self._basvuru("Yalniz", "Developer")

        takimlar = run_matchmaker(self.jam)

        self.assertEqual(takimlar, [])
        self.assertEqual(SuggestedTeam.objects.filter(jam=self.jam).count(), 0)

    def test_team_names_are_sequential(self):
        """REGRESYON: eski kod 1, 3, 5... diye numaralandırıyordu."""
        for i, rol in enumerate(["Developer", "2D Artist", "3D Artist", "Game Designer"]):
            self._basvuru(f"A{i}", rol)
        for i, rol in enumerate(["Developer", "2D Artist", "3D Artist", "Game Designer"]):
            self._basvuru(f"B{i}", rol)

        takimlar = run_matchmaker(self.jam)

        self.assertEqual([t.name for t in takimlar], ["Takım 1", "Takım 2"])

    def test_already_assigned_applicants_are_skipped(self):
        self._basvuru("Ali", "Developer")
        self._basvuru("Veli", "2D Artist")
        run_matchmaker(self.jam)

        self._basvuru("Yeni1", "3D Artist")
        self._basvuru("Yeni2", "Sound Designer")
        ikinci = run_matchmaker(self.jam)

        self.assertEqual(len(ikinci), 1)
        self.assertEqual(ikinci[0].name, "Takım 2")
        self.assertEqual({u.full_name for u in ikinci[0].members.all()}, {"Yeni1", "Yeni2"})

    def test_reset_clears_teams_and_unlinks_members(self):
        self._basvuru("Ali", "Developer")
        self._basvuru("Veli", "2D Artist")
        run_matchmaker(self.jam)

        silinen = reset_matchmaker(self.jam)

        self.assertEqual(silinen, 1)
        self.assertEqual(SuggestedTeam.objects.filter(jam=self.jam).count(), 0)
        self.assertEqual(
            JamApplication.objects.filter(jam=self.jam, suggested_team__isnull=False).count(), 0
        )

    def test_reset_does_not_delete_applications(self):
        self._basvuru("Ali", "Developer")
        self._basvuru("Veli", "2D Artist")
        run_matchmaker(self.jam)

        reset_matchmaker(self.jam)

        self.assertEqual(JamApplication.objects.filter(jam=self.jam).count(), 2)
```

- [ ] **Adım 2: Testin başarısız olduğunu doğrula**

```bash
venv/Scripts/python.exe manage.py test jams -v 2
```

Beklenen: `ImportError: cannot import name 'reset_matchmaker'` ile toplu hata.

- [ ] **Adım 3: jams/services.py dosyasını yeniden yaz**

Dosyanın tamamını şununla değiştirin:

```python
"""
Matchmaker Servisi
===================

"Ekip arıyorum" diyen jam başvurucularını rollere göre gruplayarak yönetim
kuruluna takım ÖNERİSİ üretir. Öneriler otomatik onaylanmaz — panelden
incelenip onaylanır veya reddedilir (bkz. SuggestedTeam.Status).

Algoritma sabit bir takım şeması aramaz; "eksik rol tamamlama" mantığıyla
çalışır: her turda mevcut rollerden birer kişi alınarak mümkün olduğunca
çeşitli bir takım kurulur.
"""

from collections import defaultdict

from django.db import transaction

from .models import GameJam, JamApplication, SuggestedTeam

# Rolü boş bırakılmış başvurular için grup anahtarı.
ROLSUZ = "Belirtilmemiş"

# Tek kişilik "takım" önerilmez — bu sayının altındaki grup dağıtılır.
MIN_TAKIM_BOYUTU = 2


def run_matchmaker(jam: GameJam) -> list[SuggestedTeam]:
    """
    Jam için takım önerileri üretir.

    Yalnızca team_status="looking" olan, henüz bir takıma atanmamış ve
    REDDEDİLMEMİŞ başvurular değerlendirilir. Tekrar çağrıldığında önceki
    takımlara dokunmaz, yalnızca boştaki başvuruları eşleştirir.

    Args:
        jam: Eşleştirmenin çalıştırılacağı GameJam.

    Returns:
        Bu çağrıda oluşturulan SuggestedTeam listesi (mevcut takımlar dâhil değil).
    """
    basvurular = list(
        JamApplication.objects
        .filter(
            jam=jam,
            team_status=JamApplication.TeamStatus.LOOKING,
            suggested_team__isnull=True,
        )
        .exclude(status=JamApplication.ApplicationStatus.REJECTED)
        .order_by("created_at")
    )

    if not basvurular:
        return []

    rol_gruplari = defaultdict(list)
    for basvuru in basvurular:
        rol_gruplari[basvuru.jam_role or ROLSUZ].append(basvuru)

    olusturulanlar = []
    # Sayaç döngü DIŞINDA bir kez okunur. Eski kod her turda count() çağırıp
    # üstüne len(olusturulanlar) eklediği için takım adları 1, 3, 5... diye
    # atlıyordu.
    sira = jam.suggested_teams.count()

    with transaction.atomic():
        while True:
            dolu_roller = [rol for rol, grup in rol_gruplari.items() if grup]
            if not dolu_roller:
                break

            uyeler = []
            for rol in dolu_roller:
                if len(uyeler) >= jam.max_team_size:
                    break
                uyeler.append(rol_gruplari[rol].pop(0))

            if len(uyeler) < MIN_TAKIM_BOYUTU:
                # Eşleşecek kimse kalmadı: tek kişiyi listeye geri koyup çık.
                artan = uyeler[0]
                rol_gruplari[artan.jam_role or ROLSUZ].insert(0, artan)
                break

            sira += 1
            takim = SuggestedTeam.objects.create(jam=jam, name=f"Takım {sira}")

            # Toplu update: üye başına ayrı save() çağırmak yerine tek sorgu.
            # JamApplication.save() içindeki şifreleme mantığı da atlanmış olur
            # (zaten şifreli veriye tekrar dokunmaya gerek yok).
            JamApplication.objects.filter(
                id__in=[uye.id for uye in uyeler]
            ).update(suggested_team=takim)

            olusturulanlar.append(takim)

    return olusturulanlar


def reset_matchmaker(jam: GameJam) -> int:
    """
    Jam'in tüm takım önerilerini siler ve üyelerin bağlantısını çözer.

    Başvuru kayıtlarına DOKUNMAZ — yalnızca öneri katmanı temizlenir.
    JamApplication.suggested_team alanı on_delete=SET_NULL olduğu için
    takımlar silindiğinde bağlantı otomatik çözülür.

    Args:
        jam: Sıfırlanacak GameJam.

    Returns:
        Silinen takım sayısı.
    """
    with transaction.atomic():
        takimlar = SuggestedTeam.objects.filter(jam=jam)
        sayi = takimlar.count()
        takimlar.delete()
    return sayi
```

- [ ] **Adım 4: Testlerin geçtiğini doğrula**

```bash
venv/Scripts/python.exe manage.py test jams -v 2
```

Beklenen: `Ran 9 tests ... OK`

- [ ] **Adım 5: Doğrulama**

```bash
venv/Scripts/python.exe manage.py test
```

Beklenen: OK, 62 test.

---

## Görev 8: Matchmaker'ı panele bağla (B8, 2/2)

**Dosyalar:**
- Değiştir: `dashboard/views.py` (dosya sonuna 4 yeni view)
- Değiştir: `dashboard/urls.py` (4 yeni rota)
- Oluştur: `templates/dashboard/matchmaker.html`
- Değiştir: `templates/dashboard/base.html` (kenar çubuğuna link)
- Test: `dashboard/tests.py` (yeni `MatchmakerPanelTests` sınıfı)

**Arayüzler:**
- Tüketir: `jams.services.run_matchmaker`, `jams.services.reset_matchmaker` (Görev 7)
- Üretir: URL adları — `dashboard:matchmaker`, `dashboard:api_run_matchmaker`,
  `dashboard:api_update_team_status`, `dashboard:api_reset_matchmaker`

- [ ] **Adım 1: Başarısız testi yaz**

`dashboard/tests.py` dosyasının sonuna ekleyin:

```python
class MatchmakerPanelTests(TestCase):
    def setUp(self):
        from datetime import timedelta

        from django.utils import timezone

        from jams.models import GameJam, JamApplication

        self.staff = User.objects.create_user(
            username="mm", email="mm@example.com", password="x", is_staff=True
        )
        simdi = timezone.now()
        self.event = Event.objects.create(
            title="Panel Jam", slug="panel-jam", description="x",
            event_type=Event.EventType.GAME_JAM, status=Event.Status.PUBLISHED,
            start_date=simdi, end_date=simdi + timedelta(days=2), location="Kampüs",
        )
        self.jam = GameJam.objects.create(
            event=self.event, application_deadline=simdi, max_team_size=4,
        )
        for ad, rol in [("Ali", "Developer"), ("Veli", "2D Artist")]:
            JamApplication.objects.create(
                jam=self.jam, full_name=ad, email=f"{ad.lower()}@example.com",
                jam_role=rol, team_status=JamApplication.TeamStatus.LOOKING,
                kvkk_accepted=True,
            )

    def test_page_requires_staff(self):
        resp = self.client.get(reverse("dashboard:matchmaker"))
        self.assertNotEqual(resp.status_code, 200)

    def test_staff_can_open_page(self):
        self.client.force_login(self.staff)
        resp = self.client.get(reverse("dashboard:matchmaker"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["jam"], self.jam)

    def test_run_creates_teams(self):
        from jams.models import SuggestedTeam

        self.client.force_login(self.staff)
        resp = self.client.post(
            reverse("dashboard:api_run_matchmaker"),
            data=json.dumps({"jam_id": self.jam.id}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(json.loads(resp.content)["created"], 1)
        self.assertEqual(SuggestedTeam.objects.filter(jam=self.jam).count(), 1)

    def test_non_staff_cannot_run(self):
        from jams.models import SuggestedTeam

        resp = self.client.post(
            reverse("dashboard:api_run_matchmaker"),
            data=json.dumps({"jam_id": self.jam.id}),
            content_type="application/json",
        )
        self.assertNotEqual(resp.status_code, 200)
        self.assertEqual(SuggestedTeam.objects.filter(jam=self.jam).count(), 0)

    def test_team_status_can_be_approved(self):
        from jams.models import SuggestedTeam

        self.client.force_login(self.staff)
        self.client.post(
            reverse("dashboard:api_run_matchmaker"),
            data=json.dumps({"jam_id": self.jam.id}),
            content_type="application/json",
        )
        takim = SuggestedTeam.objects.get(jam=self.jam)

        resp = self.client.post(
            reverse("dashboard:api_update_team_status"),
            data=json.dumps({"team_id": takim.id, "status": "approved"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)

        takim.refresh_from_db()
        self.assertEqual(takim.status, SuggestedTeam.Status.APPROVED)
        self.assertEqual(takim.reviewed_by, self.staff)
        self.assertIsNotNone(takim.reviewed_at)

    def test_invalid_team_status_rejected(self):
        from jams.models import SuggestedTeam

        self.client.force_login(self.staff)
        self.client.post(
            reverse("dashboard:api_run_matchmaker"),
            data=json.dumps({"jam_id": self.jam.id}),
            content_type="application/json",
        )
        takim = SuggestedTeam.objects.get(jam=self.jam)

        resp = self.client.post(
            reverse("dashboard:api_update_team_status"),
            data=json.dumps({"team_id": takim.id, "status": "hacker"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)
        takim.refresh_from_db()
        self.assertEqual(takim.status, SuggestedTeam.Status.PENDING)

    def test_reset_removes_teams(self):
        from jams.models import SuggestedTeam

        self.client.force_login(self.staff)
        self.client.post(
            reverse("dashboard:api_run_matchmaker"),
            data=json.dumps({"jam_id": self.jam.id}),
            content_type="application/json",
        )

        resp = self.client.post(
            reverse("dashboard:api_reset_matchmaker"),
            data=json.dumps({"jam_id": self.jam.id}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(SuggestedTeam.objects.filter(jam=self.jam).count(), 0)
```

- [ ] **Adım 2: Testin başarısız olduğunu doğrula**

```bash
venv/Scripts/python.exe manage.py test dashboard.tests.MatchmakerPanelTests -v 2
```

Beklenen: `NoReverseMatch: 'matchmaker' is not a valid view function or pattern name`.

- [ ] **Adım 3: View'ları ekle**

`dashboard/views.py` dosyasının **sonuna** ekleyin:

```python
# ==============================================================================
# Matchmaker (Takım Eşleştirme)
# ==============================================================================

from django.utils import timezone

from jams.models import SuggestedTeam
from jams.services import reset_matchmaker, run_matchmaker


class MatchmakerView(StaffRequiredMixin, TemplateView):
    """Jam bazında takım önerilerini gösterir ve yönetir."""

    template_name = "dashboard/matchmaker.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        all_jams = GameJam.objects.select_related("event").order_by("-created_at")
        jam_id = self.request.GET.get("jam")

        if jam_id:
            jam = all_jams.filter(id=jam_id).first()
        else:
            jam = all_jams.first()

        context["all_jams"] = all_jams
        context["jam"] = jam

        if not jam:
            return context

        # prefetch_related olmadan her takım kartı üye listesi için ayrı sorgu atar.
        context["teams"] = (
            SuggestedTeam.objects
            .filter(jam=jam)
            .prefetch_related("members")
            .order_by("created_at")
        )
        context["unmatched_count"] = (
            JamApplication.objects
            .filter(
                jam=jam,
                team_status=JamApplication.TeamStatus.LOOKING,
                suggested_team__isnull=True,
            )
            .exclude(status=JamApplication.ApplicationStatus.REJECTED)
            .count()
        )
        return context


@staff_member_required
@require_POST
def api_run_matchmaker(request):
    """Seçili jam için takım önerileri üretir."""
    try:
        data = json.loads(request.body)
        jam = get_object_or_404(GameJam, id=data.get("jam_id"))

        olusturulanlar = run_matchmaker(jam)

        return JsonResponse({"success": True, "created": len(olusturulanlar)})
    except Exception:
        logger.exception("Matchmaker çalıştırılamadı")
        return JsonResponse({"success": False, "error": GENERIC_API_ERROR}, status=400)


@staff_member_required
@require_POST
def api_update_team_status(request):
    """Önerilen takımı onaylar veya reddeder."""
    try:
        data = json.loads(request.body)
        new_status = data.get("status")

        if new_status not in SuggestedTeam.Status.values:
            return JsonResponse({"success": False, "error": "Geçersiz durum."}, status=400)

        team = get_object_or_404(SuggestedTeam, id=data.get("team_id"))
        team.status = new_status
        team.reviewed_by = request.user
        team.reviewed_at = timezone.now()
        team.save(update_fields=["status", "reviewed_by", "reviewed_at", "updated_at"])

        return JsonResponse({"success": True})
    except Exception:
        logger.exception("Takım durumu güncellenemedi")
        return JsonResponse({"success": False, "error": GENERIC_API_ERROR}, status=400)


@staff_member_required
@require_POST
def api_reset_matchmaker(request):
    """Jam'in tüm takım önerilerini siler (başvurulara dokunmaz)."""
    try:
        data = json.loads(request.body)
        jam = get_object_or_404(GameJam, id=data.get("jam_id"))

        silinen = reset_matchmaker(jam)

        return JsonResponse({"success": True, "deleted": silinen})
    except Exception:
        logger.exception("Matchmaker sıfırlanamadı")
        return JsonResponse({"success": False, "error": GENERIC_API_ERROR}, status=400)
```

- [ ] **Adım 4: Rotaları ekle**

`dashboard/urls.py` içinde, `# Raffles` yorumunun **üstüne** ekleyin:

```python
    # Matchmaker (Takım Eşleştirme)
    path('matchmaker/', views.MatchmakerView.as_view(), name='matchmaker'),
    path('api/run-matchmaker/', views.api_run_matchmaker, name='api_run_matchmaker'),
    path('api/matchmaker/team-status/', views.api_update_team_status, name='api_update_team_status'),
    path('api/matchmaker/reset/', views.api_reset_matchmaker, name='api_reset_matchmaker'),

```

- [ ] **Adım 5: Şablonu oluştur**

`templates/dashboard/matchmaker.html`:

```html
{% extends 'dashboard/base.html' %}
{% load static %}

{% block title %}Takım Eşleştirme | Nishdot{% endblock %}

{% block dashboard_content %}
<div class="py-8 px-4 sm:px-6 lg:px-8">
    <div class="max-w-7xl mx-auto">

        <!-- Başlık -->
        <div class="flex flex-col md:flex-row md:items-center justify-between mb-8 gap-4">
            <div class="flex items-center gap-4">
                <div>
                    <h1 class="text-3xl font-bold text-white tracking-tight">Takım Eşleştirme</h1>
                    <p class="text-zinc-400 mt-1">
                        {% if jam %}{{ jam.event.title }}{% else %}Aktif Game Jam bulunamadı{% endif %}
                    </p>
                </div>

                {% if all_jams %}
                <form method="get" class="ml-4 border-l border-zinc-700 pl-4">
                    <label for="jam-select" class="sr-only">Etkinlik Seç</label>
                    <select name="jam" id="jam-select" onchange="this.form.submit()" class="bg-zinc-800 border border-zinc-700 text-zinc-300 rounded-xl px-3 py-2 text-sm focus:outline-none focus:border-brand-pink cursor-pointer shadow-lg">
                        {% for j in all_jams %}
                            <option value="{{ j.id }}" {% if j.id == jam.id %}selected{% endif %}>{{ j.event.title }}</option>
                        {% endfor %}
                    </select>
                </form>
                {% endif %}
            </div>

            {% if jam %}
            <div class="flex gap-3">
                <button id="btnReset" class="btn-outline flex items-center gap-2">
                    Önerileri Sıfırla
                </button>
                <button id="btnRun" class="bg-brand-pink text-white px-6 py-2 rounded-xl font-medium hover:bg-opacity-90 transition-colors flex items-center gap-2 shadow-[0_0_15px_rgba(235,89,109,0.3)]">
                    Eşleştirmeyi Çalıştır
                </button>
            </div>
            {% endif %}
        </div>

        {% if jam %}
        <!-- Nasıl çalışır -->
        <div class="bg-zinc-800/30 border border-zinc-700/50 rounded-2xl p-6 mb-8">
            <h2 class="text-white font-semibold mb-2">Nasıl çalışır?</h2>
            <p class="text-zinc-400 text-sm leading-relaxed">
                Yalnızca <strong class="text-zinc-200">&ldquo;Ekip Arıyorum&rdquo;</strong> diyen ve
                reddedilmemiş başvurular değerlendirilir. Algoritma sabit bir takım şeması aramaz;
                her takıma farklı rollerden birer kişi koyarak eksik rolleri tamamlamaya çalışır.
                Üretilen takımlar <strong class="text-zinc-200">öneridir</strong> &mdash; siz
                onaylayana kadar katılımcılara duyurulmaz. Eşleştirmeyi tekrar çalıştırmak mevcut
                takımlara dokunmaz, yalnızca boştaki başvuruları değerlendirir.
            </p>
        </div>

        <!-- Özet -->
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
            <div class="bg-zinc-800/50 border border-zinc-700/50 rounded-2xl p-6 backdrop-blur-sm">
                <p class="text-zinc-400 text-sm font-medium">Önerilen Takım</p>
                <p class="text-3xl font-bold text-white mt-2">{{ teams|length }}</p>
            </div>
            <div class="bg-zinc-800/50 border border-zinc-700/50 rounded-2xl p-6 backdrop-blur-sm">
                <p class="text-zinc-400 text-sm font-medium">Eşleşmeyi Bekleyen</p>
                <p class="text-3xl font-bold text-white mt-2">{{ unmatched_count }}</p>
            </div>
            <div class="bg-zinc-800/50 border border-zinc-700/50 rounded-2xl p-6 backdrop-blur-sm">
                <p class="text-zinc-400 text-sm font-medium">Maksimum Takım Boyutu</p>
                <p class="text-3xl font-bold text-white mt-2">{{ jam.max_team_size }}</p>
            </div>
        </div>

        <!-- Takım Kartları -->
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {% for team in teams %}
            <div class="bg-zinc-800/30 border border-zinc-700/50 rounded-2xl overflow-hidden backdrop-blur-sm" id="team-card-{{ team.id }}">
                <div class="flex items-center justify-between p-6 border-b border-zinc-700/50">
                    <h3 class="text-xl font-bold text-white">{{ team.name }}</h3>
                    <span class="team-badge px-3 py-1 rounded-full text-xs font-bold border
                        {% if team.status == 'approved' %}bg-green-500/10 text-green-400 border-green-500/25
                        {% elif team.status == 'rejected' %}bg-red-500/10 text-red-400 border-red-500/25
                        {% else %}bg-yellow-500/10 text-yellow-400 border-yellow-500/25{% endif %}"
                        data-team-id="{{ team.id }}">
                        {{ team.get_status_display }}
                    </span>
                </div>

                <ul class="p-6 space-y-4">
                    {% for member in team.members.all %}
                    <li class="flex items-center justify-between gap-4">
                        <div class="min-w-0">
                            <p class="text-white font-medium truncate">{{ member.full_name }}</p>
                            <p class="text-zinc-500 text-xs truncate">{{ member.email }}</p>
                        </div>
                        <span class="text-brand-pink text-xs font-semibold whitespace-nowrap">{{ member.jam_role }}</span>
                    </li>
                    {% empty %}
                    <li class="text-zinc-500 text-sm">Bu takımda üye kalmamış.</li>
                    {% endfor %}
                </ul>

                <div class="flex gap-2 p-6 pt-0">
                    <button onclick="setTeamStatus({{ team.id }}, 'approved')" class="flex-1 bg-green-600/20 text-green-400 border border-green-600/30 hover:bg-green-600/30 px-4 py-2 rounded-xl text-sm font-medium transition-colors">
                        Onayla
                    </button>
                    <button onclick="setTeamStatus({{ team.id }}, 'rejected')" class="flex-1 bg-red-600/20 text-red-400 border border-red-600/30 hover:bg-red-600/30 px-4 py-2 rounded-xl text-sm font-medium transition-colors">
                        Reddet
                    </button>
                </div>

                {% if team.reviewed_by %}
                <p class="px-6 pb-6 text-xs text-zinc-500">
                    {{ team.reviewed_by.get_full_name|default:team.reviewed_by.username }} tarafından
                    {{ team.reviewed_at|date:"d M Y H:i" }} tarihinde incelendi.
                </p>
                {% endif %}
            </div>
            {% empty %}
            <div class="col-span-full bg-zinc-800/30 border border-zinc-700/50 rounded-2xl p-12 text-center text-zinc-500">
                <p>Henüz takım önerisi yok. &ldquo;Eşleştirmeyi Çalıştır&rdquo; ile başlayın.</p>
            </div>
            {% endfor %}
        </div>
        {% else %}
        <div class="bg-zinc-800/30 border border-zinc-700/50 rounded-2xl p-12 text-center text-zinc-500">
            <p>Sistemde kayıtlı bir Game Jam bulunmuyor. Önce Etkinlik Oluşturucu'dan bir jam açın.</p>
        </div>
        {% endif %}
    </div>
</div>
{% endblock %}

{% block extra_scripts %}
<script>
    const csrfToken = '{{ csrf_token }}';
    {% if jam %}
    const jamId = {{ jam.id }};
    {% endif %}

    async function postJson(url, payload) {
        const res = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify(payload)
        });
        return res.json();
    }

    const btnRun = document.getElementById('btnRun');
    if (btnRun) {
        btnRun.addEventListener('click', async () => {
            const originalText = btnRun.innerText;
            btnRun.disabled = true;
            btnRun.innerText = 'Eşleştiriliyor...';

            try {
                const result = await postJson("{% url 'dashboard:api_run_matchmaker' %}", { jam_id: jamId });
                if (result.success) {
                    if (result.created === 0) {
                        alert('Eşleştirilecek yeni başvuru bulunamadı.');
                        btnRun.disabled = false;
                        btnRun.innerText = originalText;
                    } else {
                        window.location.reload();
                    }
                } else {
                    alert('Hata: ' + result.error);
                    btnRun.disabled = false;
                    btnRun.innerText = originalText;
                }
            } catch (err) {
                alert('Bağlantı hatası: ' + err.message);
                btnRun.disabled = false;
                btnRun.innerText = originalText;
            }
        });
    }

    const btnReset = document.getElementById('btnReset');
    if (btnReset) {
        btnReset.addEventListener('click', async () => {
            if (!confirm('Tüm takım önerileri silinecek. Başvurular silinmez. Devam edilsin mi?')) return;

            btnReset.disabled = true;
            btnReset.innerText = 'Sıfırlanıyor...';

            try {
                const result = await postJson("{% url 'dashboard:api_reset_matchmaker' %}", { jam_id: jamId });
                if (result.success) {
                    window.location.reload();
                } else {
                    alert('Hata: ' + result.error);
                    btnReset.disabled = false;
                    btnReset.innerText = 'Önerileri Sıfırla';
                }
            } catch (err) {
                alert('Bağlantı hatası: ' + err.message);
                btnReset.disabled = false;
                btnReset.innerText = 'Önerileri Sıfırla';
            }
        });
    }

    async function setTeamStatus(teamId, status) {
        const badge = document.querySelector(`.team-badge[data-team-id="${teamId}"]`);
        const oncekiMetin = badge.innerText;
        badge.innerText = '...';

        try {
            const result = await postJson("{% url 'dashboard:api_update_team_status' %}", {
                team_id: teamId, status: status
            });

            if (result.success) {
                window.location.reload();
            } else {
                alert('Hata: ' + result.error);
                badge.innerText = oncekiMetin;
            }
        } catch (err) {
            alert('Bağlantı hatası: ' + err.message);
            badge.innerText = oncekiMetin;
        }
    }
</script>
{% endblock %}
```

- [ ] **Adım 6: Kenar çubuğuna link ekle**

`templates/dashboard/base.html` içinde, "Etkinlik Oluşturucu" linkini kapsayan
`</a>` etiketinden sonra, "Toplantı Notları" linkinin **üstüne** ekleyin:

```html
                <a href="{% url 'dashboard:matchmaker' %}" class="flex items-center gap-3 px-3 py-2 rounded-lg transition-colors {% if request.resolver_match.url_name == 'matchmaker' %}bg-brand-pink/10 text-brand-pink font-medium{% else %}text-zinc-400 hover:bg-zinc-800 hover:text-white{% endif %}">
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
                    </svg>
                    Takım Eşleştirme
                </a>
```

- [ ] **Adım 7: Testlerin geçtiğini doğrula**

```bash
venv/Scripts/python.exe manage.py test dashboard -v 2
```

Beklenen: `Ran 13 tests ... OK`

- [ ] **Adım 8: Tarayıcıda elle doğrula**

```bash
venv/Scripts/python.exe manage.py runserver
```

`http://127.0.0.1:8000/management/matchmaker/` adresinde staff hesabıyla:
1. Kenar çubuğunda "Takım Eşleştirme" linkinin göründüğünü ve aktif olduğunda
   pembe vurgulandığını doğrula
2. Jam seçicinin çalıştığını doğrula
3. "Eşleştirmeyi Çalıştır" → takım kartlarının geldiğini doğrula
4. Bir takımı "Onayla" → rozetin yeşile döndüğünü ve alt satırda inceleyen
   kişi/tarih yazısının çıktığını doğrula
5. "Önerileri Sıfırla" → onay diyaloğu çıktığını ve kartların silindiğini doğrula
6. Mobil genişlikte (DevTools 375px) kartların tek sütuna düştüğünü doğrula

- [ ] **Adım 9: Doğrulama**

```bash
venv/Scripts/python.exe manage.py test
```

Beklenen: OK, 69 test.

---

## Görev 9: Lint altyapısını kur ve mevcut ihlalleri temizle (B9, 1/3)

**Dosyalar:**
- Oluştur: `ruff.toml`
- Oluştur: `.pre-commit-config.yaml`
- Değiştir: `requirements/development.txt`
- Değiştir: `events/models.py`, `jams/views.py`, `users/forms.py`, `dashboard/views.py` (kullanılmayan import'lar)

**Arayüzler:**
- Üretir: `ruff check .` komutu — Görev 10'daki CI bunu çalıştırır.

**Not:** Yapılandırma `pyproject.toml` yerine `ruff.toml`'a yazılır; bu depo bir
Python paketi değil ve `pyproject.toml` eklemek araçların onu paket sanmasına
yol açar.

- [ ] **Adım 1: ruff ve pre-commit'i geliştirme bağımlılıklarına ekle**

`requirements/development.txt` dosyasının sonuna ekleyin:

```
# Lint + format (tek araç). CI'da da aynı sürüm çalışır.
ruff>=0.14,<1.0

# Commit öncesi otomatik lint. Kurulum: pre-commit install
pre-commit>=4.0,<5.0
```

- [ ] **Adım 2: Kur**

```bash
venv/Scripts/python.exe -m pip install -r requirements/development.txt
```

- [ ] **Adım 3: ruff.toml dosyasını oluştur**

```toml
# Nishdot Web Platform — Ruff yapılandırması
#
# Kural seti bilinçli olarak dar tutuldu: ruff'un varsayılanı (pyflakes + temel
# pycodestyle hataları) mevcut kod tabanını gürültüye boğmadan gerçek hataları
# yakalar. Import sıralaması (I) ve modernizasyon (UP) kuralları ileride,
# ayrı bir temizlik turunda açılabilir.

line-length = 120
target-version = "py312"

exclude = [
    "venv",
    "node_modules",
    "*/migrations/*",   # Django üretiyor, elle düzenlenmiyor
    "staticfiles",
]

[lint]
select = ["E4", "E7", "E9", "F"]
ignore = [
    "F403",   # "from .base import *" — split settings deseninin doğal parçası
    "F405",   # yukarıdakinin türevi
]

[lint.per-file-ignores]
# Settings dosyaları yıldız import'la base'i genişletir.
"nishdot/settings/*.py" = ["F401"]

[format]
quote-style = "double"
indent-style = "space"
```

- [ ] **Adım 4: Mevcut ihlalleri listele**

```bash
venv/Scripts/ruff.exe check .
```

Beklenen ihlaller (denetimde önceden tespit edildi):

| Dosya | Satır | Kural | Sorun |
|---|---|---|---|
| `events/models.py` | 62, 179, 289 | F401 | `import sys` kullanılmıyor (`sys.getsizeof` düzeltmesinden kalma) |
| `jams/views.py` | 1 | F401 | `from django.shortcuts import render` kullanılmıyor |
| `users/forms.py` | 3 | F401 | `UserCreationForm` kullanılmıyor |
| `dashboard/views.py` | 149 | F401 | `EventGame` bu fonksiyonda kullanılmıyor |
| `dashboard/views.py` | 1213 | F401 | `import os` bu fonksiyonda kullanılmıyor |

Gerçek çıktı bundan farklıysa listeye uyun, plana değil.

- [ ] **Adım 5: events/models.py içindeki ölü import'ları sil**

`Event.save()`, `EventGame.save()` ve `EventImage.save()` metotlarının başındaki
üç `import sys` satırını silin. (`import os` ve `BytesIO`/`PIL` import'ları
kullanılıyor, onlara dokunmayın.)

- [ ] **Adım 6: jams/views.py dosyasını temizle**

Dosyanın tamamını şununla değiştirin:

```python
# Jam'lere özgü herkese açık bir görünüm henüz yok.
# Jam başvuruları events.views.EventApplyWizardView üzerinden alınır,
# takım eşleştirme yönetimi dashboard.views.MatchmakerView'dedir.
```

- [ ] **Adım 7: users/forms.py import'unu düzelt**

3. satırı şununla değiştirin:

```python
from django.contrib.auth.forms import AuthenticationForm
```

- [ ] **Adım 8: dashboard/views.py içindeki ölü import'ları sil**

`api_event_games_list` fonksiyonundaki:

```python
    from events.models import Event, EventGame
```

satırını şununla değiştirin:

```python
    from events.models import Event
```

`api_event_gallery` fonksiyonundaki `import os` satırını silin.

- [ ] **Adım 9: Lint'in temiz olduğunu doğrula**

```bash
venv/Scripts/ruff.exe check .
```

Beklenen: `All checks passed!`

- [ ] **Adım 10: Testlerin hâlâ geçtiğini doğrula**

```bash
venv/Scripts/python.exe manage.py test
```

Beklenen: OK, 69 test. (Import silme davranışı değiştirmemeli.)

- [ ] **Adım 11: .pre-commit-config.yaml dosyasını oluştur**

```yaml
# Commit öncesi otomatik kontroller.
# Kurulum (bir kez): venv/Scripts/pre-commit.exe install
#
# GitHub Desktop ile commit atarken de çalışır — hook git seviyesindedir.
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.14.0
    hooks:
      - id: ruff
        args: [--fix]

  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v6.0.0
    hooks:
      - id: trailing-whitespace
        exclude: ^(static/vendor/|.*\.min\.(js|css)$)
      - id: end-of-file-fixer
        exclude: ^(static/vendor/|static/css/output\.css$|.*\.min\.(js|css)$)
      - id: check-yaml
      - id: check-merge-conflict
      - id: check-added-large-files
        args: [--maxkb=2048]
```

`check-added-large-files` özellikle önemli: denetim raporu madde 19'da depo
~380 MB'a şişmişti; 2 MB üstü bir dosya artık kazara commit'lenemez.

- [ ] **Adım 12: Hook'u kur ve tüm dosyalarda çalıştır**

```bash
venv/Scripts/pre-commit.exe install
venv/Scripts/pre-commit.exe run --all-files
```

İlk çalıştırmada `trailing-whitespace` ve `end-of-file-fixer` bazı dosyaları
düzeltebilir. Düzeltilen dosyaları gözden geçirin; `static/css/output.css`
(Tailwind üretimi) ve `static/vendor/` dosyalarına dokunulmamalı.

- [ ] **Adım 13: Doğrulama**

```bash
venv/Scripts/ruff.exe check . && venv/Scripts/python.exe manage.py test
```

Beklenen: `All checks passed!` ve testler OK.

---

## Görev 10: GitHub Actions CI kur (B9, 2/3)

**Dosyalar:**
- Oluştur: `.github/workflows/ci.yml`

**Arayüzler:**
- Tüketir: Görev 9'daki `ruff.toml`, Görev 1-8'deki test paketi.

- [ ] **Adım 1: Workflow dosyasını oluştur**

`.github/workflows/ci.yml`:

```yaml
# Her push ve pull request'te lint + test çalıştırır.
#
# Sır (secret) GEREKMEZ: SECRET_KEY ve FERNET_KEY her koşuda yeniden üretilir,
# çünkü testler kalıcı veri kullanmaz (her test kendi geçici SQLite DB'sini kurar).
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  lint-and-test:
    runs-on: ubuntu-latest

    steps:
      - name: Depoyu indir
        uses: actions/checkout@v4

      - name: Python 3.12 kur
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip
          cache-dependency-path: requirements/*.txt

      - name: Bağımlılıkları kur
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements/development.txt

      - name: Ortam değişkenlerini üret
        run: |
          echo "DJANGO_SECRET_KEY=ci-only-$(python -c 'import secrets; print(secrets.token_urlsafe(32))')" >> $GITHUB_ENV
          echo "FERNET_KEY=$(python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')" >> $GITHUB_ENV
          echo "DJANGO_SETTINGS_MODULE=nishdot.settings.development" >> $GITHUB_ENV
          echo "DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1" >> $GITHUB_ENV
          echo "DATABASE_URL=sqlite:///ci.sqlite3" >> $GITHUB_ENV

      - name: Lint (ruff)
        run: ruff check .

      - name: Django sistem kontrolü
        run: python manage.py check

      - name: Eksik migration var mı?
        run: python manage.py makemigrations --check --dry-run

      - name: Testler
        run: python manage.py test --verbosity 2

      - name: Production ayarlarının güvenlik denetimi
        env:
          DJANGO_SETTINGS_MODULE: nishdot.settings.production
          DATABASE_URL: postgres://ci:ci@127.0.0.1:5432/ci
          REDIS_URL: redis://127.0.0.1:6379/1
        run: python manage.py check --deploy --fail-level WARNING
```

Son adım (`check --deploy`) production ayarlarının HSTS, güvenli çerez ve SSL
yönlendirme kontrollerini doğrular; veritabanına bağlanmaz, yalnızca ayarları
okur.

- [ ] **Adım 2: Workflow'u lokalde simüle et**

```bash
venv/Scripts/ruff.exe check . && venv/Scripts/python.exe manage.py check && venv/Scripts/python.exe manage.py makemigrations --check --dry-run && venv/Scripts/python.exe manage.py test
```

Beklenen: dört komut da başarılı. `makemigrations --check` "No changes detected"
demeli — demiyorsa Görev 5'te üretilmemiş bir model değişikliği kalmış demektir.

- [ ] **Adım 3: check --deploy'u lokalde dene**

```bash
DJANGO_SETTINGS_MODULE=nishdot.settings.production DATABASE_URL=postgres://ci:ci@127.0.0.1:5432/ci venv/Scripts/python.exe manage.py check --deploy --fail-level WARNING
```

Beklenen: `System check identified no issues`. Uyarı çıkarsa
`nishdot/settings/production.py` içinde eksik ayar var demektir — düzeltip
tekrar deneyin.

- [ ] **Adım 4: Doğrulama**

```bash
ls -la .github/workflows/ci.yml && venv/Scripts/python.exe manage.py test
```

Beklenen: dosya mevcut, testler OK. CI'ın gerçekten çalıştığı, kullanıcı
değişiklikleri GitHub'a push ettiğinde Actions sekmesinden görülecek.

---

## Görev 11: Kritik akışların test kapsamını tamamla (B9, 3/3)

**Dosyalar:**
- Değiştir: `pages/tests.py` (stub → gerçek test)
- Değiştir: `dashboard/tests.py` (yetki testleri eklenir)

**Arayüzler:**
- Tüketir: Önceki tüm görevler. Yeni üretim kodu yazılmaz — yalnızca test.

**Gerekçe:** Denetim raporu madde 28: "Personel olmayan kullanıcı yönetim
uçlarını çağıramıyor" tek bir uç için test edilmiş (`api_toggle_event_pin`),
ama panelde 35 uç var. Bir dekoratörün unutulması sessizce yetki açığı yaratır.

- [ ] **Adım 1: Dashboard yetki testini yaz**

`dashboard/tests.py` dosyasının sonuna ekleyin:

```python
class DashboardAuthorizationTests(TestCase):
    """
    Panelin TÜM uçları staff yetkisi istemeli.

    Bu test URL tablosunu gezerek çalışır — yeni bir uç eklendiğinde ayrıca
    test yazmak gerekmez, dekoratör unutulursa burada patlar.
    """

    # Bilerek tüm GİRİŞ YAPMIŞ kullanıcılara açık olan uçlar. Üye kendi
    # panelindeki duyuruyu gizleyebilmelidir; bu yüzden üye testinden muaftır.
    # Anonim testten muaf DEĞİLDİR (@login_required korumalı).
    UYEYE_ACIK = {"api_dismiss_announcement"}

    def setUp(self):
        self.uye = User.objects.create_user(
            username="sirandan", email="sirandan@example.com", password="x"
        )

    def _rotalar(self):
        """dashboard/urls.py içindeki her rotayı (ad, url) olarak üretir."""
        from django.urls import NoReverseMatch

        from dashboard import urls as dashboard_urls

        # Parametre alan rotalar için sahte değer yeterli: yetki kontrolü
        # get_object_or_404'ten ÖNCE çalışır, nesnenin var olması gerekmez.
        aday_kwargs = ({}, {"pk": 1}, {"announcement_id": 1})

        for pattern in dashboard_urls.urlpatterns:
            ad = pattern.name
            url = None
            for kwargs in aday_kwargs:
                try:
                    url = reverse(f"dashboard:{ad}", kwargs=kwargs)
                    break
                except NoReverseMatch:
                    continue
            self.assertIsNotNone(url, f"{ad} için URL üretilemedi — aday_kwargs'a ekleyin")
            yield ad, url

    def _erisilemez_olmali(self, ad, url, kim):
        get = self.client.get(url)
        post = self.client.post(url, data="{}", content_type="application/json")
        self.assertNotEqual(get.status_code, 200, f"{ad}: {kim} GET ile 200 aldı")
        self.assertNotEqual(post.status_code, 200, f"{ad}: {kim} POST ile 200 aldı")

    def test_anonymous_cannot_reach_any_endpoint(self):
        for ad, url in self._rotalar():
            with self.subTest(uc=ad):
                self._erisilemez_olmali(ad, url, "anonim")

    def test_regular_member_cannot_reach_any_endpoint(self):
        self.client.force_login(self.uye)
        for ad, url in self._rotalar():
            if ad in self.UYEYE_ACIK:
                continue
            with self.subTest(uc=ad):
                self._erisilemez_olmali(ad, url, "üye")


class StorageManagerAuthorizationTests(TestCase):
    """Depolama yöneticisi staff değil, SUPERUSER ister (dosya siler)."""

    def setUp(self):
        self.staff = User.objects.create_user(
            username="sadecestaff", email="s@example.com", password="x", is_staff=True
        )

    def test_staff_without_superuser_cannot_open_storage_manager(self):
        self.client.force_login(self.staff)
        resp = self.client.get(reverse("dashboard:storage_manager"))
        self.assertNotEqual(resp.status_code, 200)

    def test_staff_without_superuser_cannot_delete_files(self):
        self.client.force_login(self.staff)
        resp = self.client.post(
            reverse("dashboard:api_storage_delete"),
            data=json.dumps({"path": "events/covers/x.webp"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 403)
```

- [ ] **Adım 2: Testi çalıştır ve gerçek açıkları incele**

```bash
venv/Scripts/python.exe manage.py test dashboard.tests.DashboardAuthorizationTests dashboard.tests.StorageManagerAuthorizationTests -v 2
```

`subTest` sayesinde her uç ayrı raporlanır. **Bir uç başarısız olursa bu bir
plan hatası değil, gerçek bir yetki açığıdır** — ilgili view'a
`@staff_member_required` (fonksiyon) veya `StaffRequiredMixin` (sınıf) ekleyip
tekrar çalıştırın. Bulduğunuz her açığı bu belgenin §0 tablosuna yeni satır
olarak ekleyin.

- [ ] **Adım 3: pages testlerini yaz**

`pages/tests.py` dosyasının tamamını şununla değiştirin:

```python
"""
Herkese açık sayfa, SEO ve iletişim formu testleri.
"""
import json
from datetime import timedelta

from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from events.models import Event
from pages.models import LegalDocument


class SitemapTests(TestCase):
    """sitemap.xml yalnızca yayında ve tamamlanmış içeriği listelemeli."""

    def setUp(self):
        simdi = timezone.now()
        ortak = {
            "description": "x", "event_type": Event.EventType.WORKSHOP,
            "start_date": simdi, "end_date": simdi + timedelta(hours=2),
            "location": "Kampüs",
        }
        Event.objects.create(title="Yayında", slug="yayinda", status=Event.Status.PUBLISHED, **ortak)
        Event.objects.create(title="Taslak", slug="taslak", status=Event.Status.DRAFT, **ortak)
        LegalDocument.objects.create(title="KVKK", slug="kvkk", content="<p>metin</p>")

    def test_sitemap_lists_published_event(self):
        resp = self.client.get("/sitemap.xml")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "/events/yayinda/")

    def test_sitemap_hides_draft_event(self):
        """REGRESYON: taslak etkinlik arama motoruna bildirilmemeli."""
        resp = self.client.get("/sitemap.xml")
        self.assertNotContains(resp, "/events/taslak/")

    def test_sitemap_lists_legal_document(self):
        resp = self.client.get("/sitemap.xml")
        self.assertContains(resp, "/legal/kvkk/")


class RobotsTxtTests(TestCase):
    def test_robots_disallows_management_paths(self):
        resp = self.client.get("/robots.txt")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "text/plain")
        icerik = resp.content.decode()
        self.assertIn("Disallow: /management/", icerik)
        self.assertIn("Disallow: /yonetim/", icerik)
        self.assertIn("Sitemap: https://nishdot.com.tr/sitemap.xml", icerik)


class LegalDocumentTests(TestCase):
    def test_document_content_is_sanitized(self):
        """REGRESYON: yasal belge içeriği |safe ile değil |sanitize ile basılmalı."""
        LegalDocument.objects.create(
            title="Test", slug="test-belge",
            content='<p>güvenli</p><script>alert(1)</script>',
        )
        resp = self.client.get(reverse("pages:legal_document", kwargs={"slug": "test-belge"}))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "güvenli")
        self.assertNotContains(resp, "<script>")

    def test_missing_document_returns_404(self):
        resp = self.client.get(reverse("pages:legal_document", kwargs={"slug": "yok"}))
        self.assertEqual(resp.status_code, 404)


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    RATELIMIT_ENABLE=False,
)
class ContactApiTests(TestCase):
    def setUp(self):
        cache.clear()
        self.url = reverse("pages:api_contact")

    def _gonder(self, **extra):
        veri = {
            "full_name": "Test Kişi",
            "email": "test@example.com",
            "subject": "Konu",
            "message": "Mesaj",
        }
        veri.update(extra)
        return self.client.post(self.url, data=json.dumps(veri), content_type="application/json")

    def test_valid_submission_accepted(self):
        resp = self._gonder()
        self.assertEqual(resp.status_code, 200)

    def test_missing_field_rejected(self):
        resp = self._gonder(message="")
        self.assertEqual(resp.status_code, 400)

    def test_invalid_json_rejected(self):
        resp = self.client.post(self.url, data="bu json degil", content_type="application/json")
        self.assertEqual(resp.status_code, 400)

    def test_get_not_allowed(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 405)


class HomePageTests(TestCase):
    def test_home_page_renders(self):
        resp = self.client.get(reverse("pages:home"))
        self.assertEqual(resp.status_code, 200)

    def test_draft_event_not_listed_on_home(self):
        simdi = timezone.now()
        Event.objects.create(
            title="Gizli Taslak", slug="gizli-taslak", description="x",
            event_type=Event.EventType.WORKSHOP, status=Event.Status.DRAFT,
            start_date=simdi, end_date=simdi + timedelta(hours=2), location="Kampüs",
        )
        resp = self.client.get(reverse("pages:home"))
        self.assertNotContains(resp, "Gizli Taslak")
```

- [ ] **Adım 4: pages testlerini çalıştır**

```bash
venv/Scripts/python.exe manage.py test pages -v 2
```

Beklenen: `Ran 12 tests ... OK`

İletişim testinin `EMAIL_BACKEND` override'ı önemli: gerçek SMTP'ye bağlanmayı
engeller. Mail gönderimi daemon thread'de yapıldığı için test bitiminde thread
hâlâ çalışıyor olabilir — `locmem` backend'i ile bu zararsızdır.

- [ ] **Adım 5: Tam doğrulama**

```bash
venv/Scripts/ruff.exe check . && venv/Scripts/python.exe manage.py test
```

Beklenen: `All checks passed!` ve `Ran 85 tests ... OK`
(27 mevcut + 58 yeni; Görev 11 Adım 2'de yetki açığı bulunursa sayı değişebilir.)

---

## Kapanış: Canlıya alma kontrol listesi

Tüm görevler bittikten sonra kullanıcının yapacakları:

- [ ] **1. Değişiklikleri gözden geçir**

```bash
git status && git diff --stat
```

`.env` ve `db.sqlite3` listede **görünmemeli** (gitignore'da).

- [ ] **2. GitHub Desktop ile commit ve push et**

Önerilen commit bölümlemesi (her biri bağımsız gözden geçirilebilir):
1. `Lokal gelistirme ortamini onar` — yalnızca `.env` (commit'lenmez, atla)
2. `Duyuru sorgusundaki parantez hatasini duzelt`
3. `Guvenlik loglarina gercek istemci IP'sini yaz`
4. `Jam basvurularini kullanici hesabina bagla`
5. `Basvuru tekilligini veritabani kisitiyla garanti et`
6. `Etkinlik olusturucuya tip dogrulamasi ve taslak destegi ekle`
7. `Matchmaker servisini duzelt ve testle`
8. `Matchmaker'i yonetim paneline bagla`
9. `Ruff ve pre-commit altyapisini kur`
10. `GitHub Actions CI ekle`
11. `Kritik akislarin test kapsamini tamamla`

- [ ] **3. CI'ın yeşil olduğunu doğrula**

GitHub → Actions sekmesi → son koşu yeşil olmalı.

- [ ] **4. Sunucuda çakışma kontrolü yap**

Görev 5 Adım 11'de `deployment_instructions.md`'ye eklenen sorguyu çalıştırın.
Hepsi `0 cakisma` demeden migrate ETMEYİN.

- [ ] **5. Deploy et**

```bash
cd /var/www/nishdot-web
git pull origin main
source venv/bin/activate
pip install -r requirements/production.txt
export DJANGO_SETTINGS_MODULE=nishdot.settings.production
python manage.py migrate
python manage.py collectstatic --noinput
sudo systemctl restart gunicorn
```

- [ ] **6. Canlıda duman testi**

1. `https://nishdot.com.tr/` açılıyor mu?
2. `/management/matchmaker/` staff hesabıyla açılıyor mu?
3. Bir etkinliği panelden taslağa çevir → ana sayfadan kaybolduğunu doğrula →
   geri yayına al
4. Hatalı şifreyle 6 kez giriş dene → `/management/` panelinde güvenlik logunun
   **gerçek IP** ile düştüğünü doğrula (Görev 3'ün canlı doğrulaması)

- [ ] **7. purge_expired_data cron'unu kur (henüz kurulmadıysa)**

```bash
sudo crontab -e
```

Ekleyin:

```
0 4 1 * * cd /var/www/nishdot-web && DJANGO_SETTINGS_MODULE=nishdot.settings.production venv/bin/python manage.py purge_expired_data
```

KVKK m.7 imha yükümlülüğü için gereklidir; komut yazılmış ama zamanlanmamış
durumda.

---

## Kapsam dışı bırakılanlar

Bu plan bilinçli olarak şunları içermez:

| Konu | Neden |
|---|---|
| README yol haritası (mobil hamburger menü, `schema.org` JSON-LD, etkinlik listeleme sayfası, hero lazy-loading, Discord webhook) | Hata değil, yeni özellik. Ayrı bir plan gerektirir. |
| Mail kuyruğu (`django-rq`) | Denetim raporu madde 15'in kalıcı çözümü. Yeni bağımlılık + Redis worker servisi gerektirir; mevcut daemon thread çözümü kabul edilebilir çalışıyor. |
| `api_raffle_pick_winner` içinde `secrets.choice` | `random.choice` sahne çekilişi için yeterli; pratik fark yok. |
| Depo geçmişindeki büyük görsellerin `git filter-repo` ile temizlenmesi | Geçmişi yeniden yazar, koordinasyon gerektirir. `.gitignore` zaten yeni eklemeleri engelliyor, `check-added-large-files` hook'u ikinci savunma hattı. |
| `docs/denetim-raporu-2026-07-19.md` dosyasının depodan kaldırılması | Raporun kendi uyarısına rağmen bilinçli bir karar olabilir; kullanıcının tercihi. Açıkların tamamı kapatıldığı için pratik risk düşük. |
