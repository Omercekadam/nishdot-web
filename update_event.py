import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nishdot.settings.development')
django.setup()

from events.models import Event

description_html = """<p class="mb-4">2025’in bitmesine sayılı gün kala daha ne beklenebilir ki?</p>

<p class="mb-6">Cevabı basit: Yılı kapatmanın en iyi yolu, <strong>NishYear Jam 2025</strong>.</p>

<p class="mb-6">
  26–27–28 Aralık tarihlerinde<br>
  Nişantaşı Üniversitesi Kağıthane Kampüsünde buluşuyoruz.
</p>

<p class="mb-6">NishYear Jam 2025, sadece bir gamejam değil;</p>

<div class="flex flex-col gap-4 mt-6 mb-8">
  <div class="flex gap-3 items-start">
    <span class="text-xl">🎮</span>
    <p>yılın yorgunluğunu son kez oyuna dönüştürdüğümüz</p>
  </div>
  <div class="flex gap-3 items-start">
    <span class="text-xl">🍔</span>
    <p>“acaba aç kalır mıyız?” sorusunu tamamen unutturan, fazlasıyla doyurucu ve gerçekten fena yemeklerin olduğu (kimse aç kalmıyor, söz)</p>
  </div>
  <div class="flex gap-3 items-start">
    <span class="text-xl">🏆</span>
    <p>jam boyunca faydalanabileceğiniz workshoplar, turnuvalar ve etkinlikler</p>
  </div>
  <div class="flex gap-3 items-start">
    <span class="text-xl">🎯</span>
    <p>alanında deneyimli mentörlerin süreç boyunca gerçekten yanınızda olduğu</p>
  </div>
  <div class="flex gap-3 items-start">
    <span class="text-xl">🎁</span>
    <p>katılan herkesin karşılıksız kalmadığı bir üretim alanı.</p>
  </div>
</div>

<p>
  İster ilk gamejam’in olsun, ister onlarcasını geride bırakmış ol;<br>
  burada amaç sadece bir şeyler yetiştirmek değil, 2025’i birlikte üreterek kapatmanın keyfini yaşamak.
</p>"""

Event.objects.filter(slug='nishyear-jam-2025').update(description=description_html)
print('Description HTML updated!')
