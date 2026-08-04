"""
Yasal metinleri veritabanına yükler (idempotent).

    python manage.py load_legal_documents

Metinlerin kaynağı: docs/legal/nishdot_yasal_metinler_v2.1_hukuk_inceleme.html
(İstanbul Nişantaşı Üniversitesi Hukuk Müşavirliği tarafından incelenip uygun
bulunan sürüm 2.1). Bu komut, o belgedeki esas hükümleri DEĞİŞTİRMEDEN,
yalnızca inceleme belgesine özgü kısımları (karar kutuları, imza alanı,
müşavirlik notları) çıkarıp yayına uygun hâle getirir.

Metinler burada — veritabanında değil — tutulur ki sürüm kontrolünde izlenebilsin
ve her ortama aynı şekilde dağıtılabilsin. Panelden yapılan düzenlemeler bu komut
tekrar çalıştırıldığında ÜZERİNE YAZILIR (bkz. --skip-existing).
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from pages.models import LegalDocument

YURURLUK = "3 Ağustos 2026"
SURUM = "2.1"

# Veri sorumlusu iletişim bilgileri. Üniversiteyi işleten tüzel kişiliğin tam
# unvanı netleştiğinde VERI_SORUMLUSU güncellenmelidir (KVKK teknik olarak
# tüzel kişilik unvanını ister; kulüplerin ayrı tüzel kişiliği yoktur).
VERI_SORUMLUSU = "İstanbul Nişantaşı Üniversitesi"
ADRES = (
    "Maslak Mahallesi, Taşyoncası Sokak, Maslak 1453 NeoTech Kampüsü, "
    "34398 Sarıyer / İstanbul"
)
EPOSTA = "dijitaloyuntasarimkulubu@nisantasi.edu.tr"


KVKK = f"""
<p><strong>Yürürlük Tarihi:</strong> {YURURLUK} &nbsp;|&nbsp; <strong>Sürüm:</strong> {SURUM}</p>

<h3>1. Veri Sorumlusunun Kimliği ve İletişim Bilgileri</h3>
<p>6698 sayılı Kişisel Verilerin Korunması Kanunu ("KVKK") uyarınca kişisel verileriniz;
veri sorumlusu sıfatıyla <strong>{VERI_SORUMLUSU}</strong> bünyesinde faaliyet gösteren
<strong>Dijital Oyun Tasarımı Kulübü (Nishdot)</strong> tarafından aşağıda açıklanan
kapsamda işlenmektedir.</p>

<table>
  <tbody>
    <tr><td><strong>Veri Sorumlusu</strong></td><td>{VERI_SORUMLUSU}</td></tr>
    <tr><td><strong>Adres</strong></td><td>{ADRES}</td></tr>
    <tr><td><strong>E-posta</strong></td><td>{EPOSTA}</td></tr>
  </tbody>
</table>

<h3>2. İşlenen Kişisel Verileriniz, İşlenme Amaçları ve Hukuki Sebepleri</h3>
<p>Platformumuza üye olmanız ve etkinliklerimize (Game Jam, Workshop vb.) başvurmanız
kapsamında aşağıdaki verileriniz toplanmaktadır:</p>

<table>
  <thead>
    <tr>
      <th>Veri Kategorisi</th><th>Toplanan Veriler</th><th>İşlenme Amacı</th>
      <th>Hukuki Sebep</th><th>Saklama Süresi</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><strong>Kimlik Bilgileri</strong></td>
      <td>Ad, Soyad, Doğum Tarihi</td>
      <td>Katılımcı doğrulaması, yaş kontrolü</td>
      <td>md. 5/2-f (Meşru menfaat)</td>
      <td>Etkinlik bitiminden itibaren <strong>1 yıl</strong></td>
    </tr>
    <tr>
      <td><strong>T.C. Kimlik No</strong></td>
      <td>T.C. Kimlik Numarası</td>
      <td>Kampüs güvenlik giriş listelerinin hazırlanması</td>
      <td>md. 5/2-f (Meşru menfaat)</td>
      <td>Etkinlik bitiminden itibaren <strong>1 yıl</strong></td>
    </tr>
    <tr>
      <td><strong>İletişim Bilgileri</strong></td>
      <td>E-posta, Telefon No</td>
      <td>Etkinlik süreçlerinde iletişim ve duyuru</td>
      <td>md. 5/2-f (Meşru menfaat)</td>
      <td>Etkinlik bitiminden itibaren <strong>1 yıl</strong>; üyelik varsa üyelik süresince</td>
    </tr>
    <tr>
      <td><strong>Eğitim Bilgileri</strong></td>
      <td>Üniversite, Bölüm, Sınıf</td>
      <td>Öğrenci statüsü doğrulaması, takım eşleştirme</td>
      <td>md. 5/2-f (Meşru menfaat)</td>
      <td>Etkinlik bitiminden itibaren <strong>1 yıl</strong></td>
    </tr>
    <tr>
      <td><strong>Sağlık Verileri</strong> (Opsiyonel)</td>
      <td>Kronik hastalık, alerji</td>
      <td>Acil tıbbi müdahalelerde can güvenliği</td>
      <td>md. 6/2 (Açık Rıza)</td>
      <td>Etkinlik bitiminden sonra <strong>7 iş günü</strong></td>
    </tr>
  </tbody>
</table>

<p>T.C. Kimlik Numarası yalnızca kampüs güvenliği giriş listelerinin hazırlanması
amacıyla talep edilmekte, bu amaç dışında kullanılmamaktadır. Söz konusu veri
sistemimizde <strong>şifrelenerek</strong> saklanır ve yukarıdaki süre sonunda silinir.</p>

<p>Saklama süreleri dolan kayıtlar düzenli aralıklarla çalıştırılan otomatik bir
silme işlemiyle sistemden kaldırılır. Sağlık verileri, amacı etkinlik süresiyle
sınırlı olduğundan diğer verilerden ayrı olarak ve daha kısa sürede silinir.</p>

<h3>3. Kişisel Verilerin Aktarılması</h3>
<p>Toplanan kişisel verileriniz ticari hiçbir amaçla üçüncü şahıslara
<strong>satılmaz, devredilmez veya kiralanmaz</strong>. Yalnızca aşağıdaki taraflarla
paylaşılabilir:</p>

<table>
  <thead>
    <tr><th>Aktarılan Taraf</th><th>Aktarım Amacı</th><th>Hukuki Sebep</th></tr>
  </thead>
  <tbody>
    <tr>
      <td>İstanbul Nişantaşı Üniversitesi Rektörlüğü</td>
      <td>Etkinlik izinleri ve kurumsal raporlama</td>
      <td>md. 5/2-ç</td>
    </tr>
    <tr>
      <td>Üniversite Güvenlik Birimleri</td>
      <td>Kampüs giriş listelerinin oluşturulması</td>
      <td>md. 5/2-f (Meşru menfaat)</td>
    </tr>
    <tr>
      <td>Yetkili Sağlık Kuruluşları</td>
      <td><em>Yalnızca</em> acil tıbbi müdahale gerektiren durumlarda</td>
      <td>md. 6/3</td>
    </tr>
  </tbody>
</table>

<h3>4. Kişisel Veri Toplamanın Yöntemi</h3>
<p>Kişisel verileriniz; nishdot.com.tr adresi üzerinden doldurduğunuz elektronik
başvuru ve üyelik formları aracılığıyla, kısmen veya tamamen otomatik yollarla
toplanmaktadır.</p>

<h3>5. KVKK Madde 11 Kapsamındaki Haklarınız</h3>
<p>KVKK'nın 11. maddesi uyarınca aşağıdaki haklara sahipsiniz:</p>
<ul>
  <li><strong>a)</strong> Kişisel verilerinizin işlenip işlenmediğini <strong>öğrenme</strong>,</li>
  <li><strong>b)</strong> Kişisel verileriniz işlenmişse buna ilişkin <strong>bilgi talep etme</strong>,</li>
  <li><strong>c)</strong> Kişisel verilerinizin işlenme amacını ve bunların amacına uygun
      kullanılıp kullanılmadığını <strong>öğrenme</strong>,</li>
  <li><strong>ç)</strong> Yurt içinde veya yurt dışında kişisel verilerinizin aktarıldığı
      <strong>üçüncü kişileri bilme</strong>,</li>
  <li><strong>d)</strong> Kişisel verilerinizin eksik veya yanlış işlenmiş olması hâlinde
      bunların <strong>düzeltilmesini isteme</strong>,</li>
  <li><strong>e)</strong> KVKK'nın 7. maddesinde öngörülen şartlar çerçevesinde kişisel
      verilerinizin <strong>silinmesini veya yok edilmesini isteme</strong>,</li>
  <li><strong>f)</strong> (d) ve (e) bentleri uyarınca yapılan işlemlerin, kişisel verilerin
      aktarıldığı üçüncü kişilere <strong>bildirilmesini isteme</strong>,</li>
  <li><strong>g)</strong> İşlenen verilerin münhasıran otomatik sistemler vasıtasıyla analiz
      edilmesi suretiyle aleyhinize bir sonucun ortaya çıkmasına <strong>itiraz etme</strong>,</li>
  <li><strong>ğ)</strong> Kişisel verilerinizin kanuna aykırı olarak işlenmesi sebebiyle
      zarara uğramanız hâlinde <strong>zararın giderilmesini talep etme</strong>.</li>
</ul>

<p><strong>Başvuru Yöntemi:</strong> <a href="mailto:{EPOSTA}">{EPOSTA}</a> adresine
kimliğinizi tespit edici bilgiler ile birlikte yazılı olarak başvurabilirsiniz.
Başvurularınız en geç <strong>30 gün</strong> içinde sonuçlandırılacaktır.</p>

<p><strong>Hesap Silme (Unutulma Hakkı) Prosedürü:</strong> Yukarıdaki e-posta adresine
"Hesap Silme Talebi" konulu başvuru gönderilebilir. Talebiniz en geç
<strong>30 gün</strong> içinde işleme alınır.</p>

<h3>6. Açık Rızaya Bağlı İşlemler</h3>
<p>Aşağıdaki işlemler <strong>yalnızca ayrıca ve açıkça onay vermeniz hâlinde</strong>
gerçekleştirilir. Bu onayları vermemeniz etkinliklere katılımınıza engel değildir ve
dilediğiniz zaman <a href="mailto:{EPOSTA}">{EPOSTA}</a> adresine bildirimde bulunarak
geri alabilirsiniz.</p>
<ul>
  <li><strong>Sağlık verileri:</strong> Başvuru formunda beyan ettiğiniz kronik hastalık
      veya alerji bilgileri, yalnızca etkinlik süresince acil tıbbi müdahale gerekmesi
      hâlinde yetkili sağlık personeliyle paylaşılmak üzere işlenir (KVKK md. 6/2).</li>
  <li><strong>Fotoğraf ve video:</strong> Etkinlik sırasında çekilen görüntülerinizin
      Nishdot'un sosyal medya hesaplarında, web sitesinde ve tanıtım materyallerinde
      süresiz, münhasır olmayan ve bedelsiz olarak kullanılmasıdır. Rızanızı geri
      almanız hâlinde görüntüleriniz yeni içeriklerde kullanılmaz; ancak hâlihazırda
      yayımlanmış genel etkinlik kayıtlarının geriye dönük olarak kaldırılması taahhüt
      edilmez.</li>
  <li><strong>Ticari elektronik ileti:</strong> Başvurduğunuz etkinliğe ilişkin
      bilgilendirmelerin dışında, yeni etkinlik ve duyurulara dair e-posta/SMS
      gönderilmesidir (6563 sayılı Elektronik Ticaretin Düzenlenmesi Hakkında Kanun).
      Her iletide yer alan bağlantı ile ücretsiz olarak abonelikten çıkabilirsiniz.</li>
</ul>
"""


GIZLILIK = f"""
<p><strong>Yürürlük Tarihi:</strong> {YURURLUK} &nbsp;|&nbsp; <strong>Sürüm:</strong> {SURUM}</p>

<p>Bu politika, Nishdot Web Platformu'nun (nishdot.com.tr) kişisel verilerinizi nasıl
koruduğunu ve çerezleri nasıl kullandığını açıklar. Hangi verilerin hangi amaçla
işlendiğine dair ayrıntılı bilgi için
<a href="/legal/kvkk/">KVKK Aydınlatma Metni</a>'ni inceleyiniz.</p>

<h3>1. Veri Güvenliği Tedbirleri</h3>
<p>Kişisel verilerinizin güvenliği için alınan başlıca teknik tedbirler:</p>
<ul>
  <li><strong>Şifreli iletişim:</strong> Site ile tarayıcınız arasındaki tüm trafik
      TLS (HTTPS) ile şifrelenir; şifresiz bağlantılar otomatik olarak güvenli
      bağlantıya yönlendirilir.</li>
  <li><strong>Hassas verilerin şifrelenmesi:</strong> T.C. Kimlik Numarası gibi hassas
      veriler veritabanında düz metin olarak tutulmaz; güncel bir simetrik şifreleme
      yöntemi (AES-256) ile şifrelenerek saklanır.</li>
  <li><strong>Parola güvenliği:</strong> Parolalar geri döndürülemez şekilde özetlenerek
      (hash) saklanır; kulüp yöneticileri dâhil hiç kimse parolanızı göremez.</li>
  <li><strong>Kötüye kullanım koruması:</strong> Giriş, kayıt, iletişim ve başvuru
      formları hız sınırlaması ile korunur; ihlal denemeleri kayıt altına alınır.</li>
  <li><strong>Yetki sınırlaması:</strong> Başvuru ve üye verilerine yalnızca yetkili
      kulüp yönetim kurulu üyeleri erişebilir.</li>
</ul>

<h3>2. Çerez (Cookie) Politikası</h3>
<p>Platformumuz, size güvenli ve işlevsel bir hizmet sunabilmek için yalnızca
<strong>zorunlu çerezleri</strong> kullanmaktadır:</p>

<table>
  <thead>
    <tr><th>Çerez Adı</th><th>Amacı</th><th>Sağlayıcı</th><th>Süresi</th></tr>
  </thead>
  <tbody>
    <tr>
      <td><code>sessionid</code></td>
      <td>Kullanıcı oturumunun açık tutulması</td>
      <td>nishdot.com.tr (1. Parti)</td>
      <td>Tarayıcı kapatılınca sona erer</td>
    </tr>
    <tr>
      <td><code>csrftoken</code></td>
      <td>Form güvenlik doğrulaması</td>
      <td>nishdot.com.tr (1. Parti)</td>
      <td>1 yıl</td>
    </tr>
  </tbody>
</table>

<p>Platformumuzda Google Analytics, Facebook Pixel veya herhangi bir üçüncü parti
analiz / pazarlama / reklam çerezi <strong>kullanılmamaktadır</strong>. Kullanılan
çerezler hizmetin çalışması için zorunlu olduğundan, tarayıcınızdan engellemeniz
hâlinde siteye giriş yapma ve form gönderme işlevleri çalışmayabilir.</p>

<h3>3. Üçüncü Taraf Bağlantıları</h3>
<p>Sitemizde kulübün sosyal medya hesaplarına ve katılımcıların oyunlarını yayımladığı
platformlara (itch.io vb.) bağlantılar bulunabilir. Bu sitelerin gizlilik uygulamaları
kendi politikalarına tabidir; Nishdot bu içeriklerden sorumlu değildir.</p>

<h3>4. Politika Değişiklikleri</h3>
<p>Bu politika güncellenebilir. Güncel sürüm her zaman bu sayfada yayımlanır;
yürürlük tarihi sayfanın başında belirtilir.</p>

<h3>5. İletişim</h3>
<p>Gizlilik uygulamalarımıza ilişkin soru ve talepleriniz için:
<a href="mailto:{EPOSTA}">{EPOSTA}</a></p>
"""


SOZLESME = f"""
<p><strong>Yürürlük Tarihi:</strong> {YURURLUK} &nbsp;|&nbsp; <strong>Sürüm:</strong> {SURUM}</p>

<h3>Madde 1 — Taraflar ve Kapsam</h3>
<p>İşbu sözleşme ("Sözleşme"); nishdot.com.tr adresi üzerinden hizmet sunan,
{VERI_SORUMLUSU} bünyesinde faaliyet gösteren Dijital Oyun Tasarımı Kulübü ("Nishdot")
ile Platforma üye olan ve/veya etkinliklere katılan kullanıcı ("Katılımcı") arasında
düzenlenmiştir. Bu Sözleşme, Nishdot'un
<a href="/legal/kvkk/">Kişisel Verilerin İşlenmesine İlişkin Aydınlatma Metni</a> ile
birlikte okunmalıdır.</p>

<h3>Madde 2 — Katılım Koşulları ve Yaş Sınırı</h3>
<ul>
  <li><strong>2.1.</strong> Etkinliklere katılım için kural olarak
      <strong>18 yaşını doldurmuş olmak</strong> gerekmektedir.</li>
  <li><strong>2.2.</strong> 18 yaş altı katılımcılar, yalnızca velisinin/yasal
      temsilcisinin <strong>yazılı izni</strong> ile etkinliklere katılabilir. Sağlık
      Verileri ve Fotoğraf/Video rıza beyanları da veli/yasal temsilci tarafından
      imzalanmalıdır.</li>
  <li><strong>2.3.</strong> Katılımcı, verdiği bilgilerin doğru, eksiksiz ve güncel
      olduğunu kabul ve taahhüt eder.</li>
</ul>

<h3>Madde 3 — Kullanıcı Yükümlülükleri ve Disiplin</h3>
<ul>
  <li><strong>3.1.</strong> Etkinlikler sırasında genel ahlak kurallarına ve üniversite
      disiplin yönetmeliklerine uyulması zorunludur.</li>
  <li><strong>3.2.</strong> İhlal durumunda kademeli yaptırımlar uygulanır:
      (a) Uyarı → (b) Geçici Uzaklaştırma (1 dönem – 1 yıl) → (c) Kalıcı Uzaklaştırma.</li>
  <li><strong>3.3.</strong> Katılımcı, yaptırım kararına karşı <strong>7 gün</strong>
      içinde yazılı itirazda bulunma hakkına sahiptir. İtiraz <strong>15 gün</strong>
      içinde sonuçlandırılır.</li>
</ul>

<h3>Madde 4 — Fikri Mülkiyet ve Telif Hakları</h3>
<ul>
  <li><strong>4.1.</strong> Etkinliklerde üretilen oyunların tüm fikri mülkiyet hakları
      <strong>geliştiren takıma/kişilere aittir</strong>.</li>
  <li><strong>4.2.</strong> Katılımcı, Nishdot'a <strong>münhasır olmayan, süresiz,
      geri alınabilir ve bedelsiz</strong> bir sergileme lisansı verir.</li>
  <li><strong>4.3.</strong> Bu lisans ticari satış hakkı vermez.</li>
  <li><strong>4.4.</strong> Lisans geri alınabilir; ancak önceden yayımlanmış/paylaşılmış
      içeriklerden Nishdot sorumlu tutulamaz.</li>
  <li><strong>4.5.</strong> Üçüncü parti içerik telif sorumluluğu münhasıran katılımcıya
      aittir.</li>
</ul>

<h3>Madde 5 — Sorumluluk Sınırlandırması</h3>
<ul>
  <li><strong>5.1.</strong> Katılımcının dijital varlıklarına (bilgisayar, donanım,
      yazılım) gelebilecek hasarlardan Nishdot sorumlu tutulamaz.</li>
  <li><strong>5.2.</strong> Fiziksel güvenlik yükümlülüğü mekân sahibine/üniversiteye
      aittir. Nishdot, kendi kusuru bulunmadığı sürece sorumlu tutulamaz.</li>
  <li><strong>5.3.</strong> <strong>Yasal Sınırlama:</strong> İşbu Madde 5 kapsamındaki
      sorumluluk sınırlamaları, 6098 sayılı Türk Borçlar Kanunu m. 115 ve 116 uyarınca
      Nishdot'un <strong>kasıt veya ağır ihmali</strong> bulunan hâllerde uygulanmaz.</li>
</ul>

<h3>Madde 6 — Etkinlik İptali, Erteleme ve Program Değişikliği</h3>
<ul>
  <li><strong>6.1.</strong> Nishdot; etkinliği iptal etme, erteleme, yerini değiştirme
      veya programında değişiklik yapma hakkını saklı tutar. Bu hakkın kullanılması
      <strong>gerekçe açıklama zorunluluğuna tabi değildir</strong>. Değişiklikler
      katılımcılara mümkün olan en kısa sürede duyurulur.</li>
  <li><strong>6.2.</strong> Etkinliklere katılım <strong>ücretsizdir</strong>. Bu nedenle
      iptal, erteleme veya program değişikliği hâlinde katılımcının ücret iadesi,
      tazminat veya sair ad altında herhangi bir <strong>talep hakkı doğmaz</strong>.
      Katılımcının etkinliğe katılmak amacıyla yaptığı ulaşım, konaklama ve benzeri
      kişisel harcamalardan Nishdot sorumlu tutulamaz.</li>
  <li><strong>6.3.</strong> Doğal afet, salgın hastalık, savaş, terör, grev, hükümet veya
      üniversite yönetiminin kararları, kampüs ya da mekân tahsisinin iptali, teknik
      altyapı arızaları gibi Nishdot'un kontrolü dışındaki hâller mücbir sebep sayılır;
      bu sayım sınırlayıcı değildir.</li>
  <li><strong>6.4.</strong> İşbu maddedeki sınırlamalar, 6098 sayılı Türk Borçlar Kanunu
      m. 115 ve 116 uyarınca Nishdot'un <strong>kasıt veya ağır ihmali</strong> bulunan
      hâllerde uygulanmaz.</li>
</ul>

<h3>Madde 7 — Sözleşme Değişiklikleri</h3>
<p>Nishdot sözleşmeyi önceden bildirim yaparak değiştirebilir. Değişiklikler
yayımlandığı tarihte yürürlüğe girer.</p>

<h3>Madde 8 — Bölünebilirlik</h3>
<p>Herhangi bir hükmün geçersiz bulunması, kalan hükümlerin geçerliliğini etkilemez.</p>

<h3>Madde 9 — Uygulanacak Hukuk ve Yetkili Mahkeme</h3>
<p>İşbu Sözleşme, Türkiye Cumhuriyeti kanunlarına tabidir. Uyuşmazlıklarda
<strong>İstanbul Mahkemeleri ve İcra Daireleri</strong> yetkilidir. Nishdot etkinlikleri
ücretsizdir; ileride ücretli bir hizmet sunulması hâlinde 6502 sayılı Tüketicinin
Korunması Hakkında Kanun'un emredici yetki kuralları saklıdır.</p>

<h3>Madde 10 — İletişim</h3>
<p>Sözleşmeye ilişkin her türlü bildirim için:
<a href="mailto:{EPOSTA}">{EPOSTA}</a></p>
"""


BELGELER = [
    ("kvkk", "KVKK Aydınlatma Metni", KVKK),
    ("gizlilik", "Gizlilik ve Çerez Politikası", GIZLILIK),
    ("kullanici-sozlesmesi", "Kullanıcı ve Etkinlik Katılım Sözleşmesi", SOZLESME),
]


class Command(BaseCommand):
    help = "Yasal metinleri (KVKK, Gizlilik, Sözleşme) veritabanına yükler/günceller."

    def add_arguments(self, parser):
        parser.add_argument(
            "--skip-existing",
            action="store_true",
            help="Mevcut kayıtların üzerine yazma, yalnızca eksik olanları oluştur.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        skip_existing = options["skip_existing"]

        for slug, title, content in BELGELER:
            body = content.strip()
            mevcut = LegalDocument.objects.filter(slug=slug).first()

            if mevcut and skip_existing:
                self.stdout.write(f"  atlandı   /legal/{slug}/ (zaten var)")
                continue

            if mevcut:
                mevcut.title = title
                mevcut.content = body
                mevcut.save()
                durum = "güncellendi"
            else:
                LegalDocument.objects.create(slug=slug, title=title, content=body)
                durum = "oluşturuldu"

            self.stdout.write(f"  {durum:<12} /legal/{slug}/  ({len(body)} karakter)")

        self.stdout.write(self.style.SUCCESS("Yasal metinler yüklendi."))
