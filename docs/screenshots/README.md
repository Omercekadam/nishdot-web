# Ekran Görüntüleri

Ana [README.md](../../README.md) dosyası bu klasördeki **7 görseli** referans alır.
Dosya adları birebir aşağıdaki gibi olmalı, yoksa README'de kırık görsel çıkar.

## Gerekli dosyalar

| Dosya adı | Nereden | Ne görünmeli |
|---|---|---|
| `home.png` | `https://nishdot.com.tr` | Hero (kayan foto şeridi + başlık + "Aramıza Katıl!") ve altındaki etkinlik kartları. Sayfanın üst ~2 ekranı yeterli. |
| `event-detail.png` | Bir etkinliğe tıkla → `/events/<slug>/` | Afiş, tarih/konum bilgi kartı, açıklama ve varsa foto galeri. |
| `apply-wizard.png` | Bir game jam'de "Başvur" → `/events/<slug>/apply/` | 3 adımlı sihirbazın adım göstergesi görünen ilk adımı. |
| `dashboard.png` | `/management/` (personel girişi gerekli) | Başvuru listesi ve metrik kartları. |
| `event-builder.png` | `/management/events/` → "Yeni Etkinlik Aç" | Açık modal: başlık, tarihler, Quill editörü görünsün. |
| `kanban.png` | `/management/tasks/` | Sütunlara dağılmış görev kartları. |
| `raffle-draw.png` | `/management/raffles/` → bir çekilişte "Çekiliş Yap" | Katılımcı listesi veya kazanan ekranı. |

## Nasıl çekilir

**Tarayıcıdan (en pratik):**

1. Pencereyi **1440px** genişliğe getir (Chrome DevTools → cihaz araç çubuğu → `Responsive` → genişlik `1440`).
2. Tam sayfa görüntü için: `F12` → `Ctrl+Shift+P` → `Capture full size screenshot` yaz → Enter.
   Sadece görünen alan yeterliyse `Capture screenshot` seç.
3. İnen dosyayı yukarıdaki tablodaki adla bu klasöre koy.

**Kısa yol (Windows):** `Win + Shift + S` ile bölge seçip kaydet.

## İpuçları

- **Gerçek içerikle çek.** Boş liste veya test verisi ("Deneme Jam", lorem ipsum) yerine
  yayındaki gerçek etkinlikleri göster — portfolyoda en çok bu fark eder.
- **Kişisel veri sızdırma.** Panel görüntülerinde başvuran ad-soyad, e-posta, telefon ve
  T.C. kimlik sütunları görünüyorsa bulanıklaştır veya o sütunları kırp. `dashboard.png`
  ve başvuru listeleri için bu özellikle önemli.
- **Koyu tema** sitenin kimliği — tarayıcının açık temalı çerçevesini kadraja alma.
- Dosya boyutunu makul tut (tercihen her biri < 1 MB). Gerekirse
  [squoosh.app](https://squoosh.app) ile sıkıştır.

## Mobil görünüm eklemek istersen

DevTools'ta `iPhone 14 Pro` seçip aynı yöntemle çek, `home-mobile.png` olarak kaydet ve
ana README'nin ekran görüntüleri bölümüne ekle.
