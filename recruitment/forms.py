import re

from django import forms

from .models import BoardApplication

TEXTAREA = {"class": "form-input", "rows": 4}


class BoardApplicationForm(forms.ModelForm):
    positions = forms.MultipleChoiceField(
        choices=BoardApplication.Position.choices,
        widget=forms.CheckboxSelectMultiple,
        label="Hangi pozisyonda sorumluluk almak istersin? (Birden fazla seçilebilir)",
        error_messages={"required": "En az bir pozisyon seç."},
    )

    class Meta:
        model = BoardApplication
        fields = [
            "department", "grade", "phone",
            "motivation", "club_opinion", "project_idea",
            "positions", "experience", "weekly_hours", "portfolio", "extra",
        ]
        # Sorular geçen yılın Google Formu'yla birebir; son üçü (haftalık süre,
        # telefon, portfolyo) 2026-2027 döneminde eklendi.
        labels = {
            "department": "Bölüm",
            "grade": "Sınıf",
            "phone": "Telefon numarası",
            "motivation": "Neden ekibimize katılmak istiyorsun?",
            "club_opinion": "Kulübümüzün şu anki durumu hakkında ne düşünüyorsun? "
                            "Sence neleri iyi yapıyoruz, neleri geliştirebiliriz?",
            "project_idea": "Yönetim ekibine katıldığında hayata geçirmek istediğin bir proje veya fikir var mı? "
                            "Varsa kısaca bahsedebilir misin?",
            "experience": "Daha önce bu alan(lar)la ilgili bir deneyimin oldu mu?",
            "weekly_hours": "Kulübe haftada kaç saat ayırabilirsin?",
            "portfolio": "Portfolyo veya örnek çalışma linkin var mı?",
            "extra": "Ekibimize ve sana dair bizim sormayı unuttuğumuz, ama senin eklemek istediğin "
                     "herhangi bir şey var mı?",
        }
        help_texts = {
            "phone": "Mülakat ve sonuç için sana buradan ulaşacağız.",
            "portfolio": "Birden fazla link varsa her birini yeni satıra yaz.",
        }
        widgets = {
            "department": forms.TextInput(attrs={"class": "form-input", "placeholder": "Örn: Dijital Oyun Tasarımı"}),
            "grade": forms.RadioSelect,
            "phone": forms.TextInput(attrs={"class": "form-input", "placeholder": "05XX XXX XX XX", "inputmode": "tel"}),
            "motivation": forms.Textarea(attrs=TEXTAREA),
            "club_opinion": forms.Textarea(attrs=TEXTAREA),
            "project_idea": forms.Textarea(attrs=TEXTAREA),
            "experience": forms.Textarea(attrs=TEXTAREA),
            "weekly_hours": forms.RadioSelect,
            "portfolio": forms.Textarea(attrs={"class": "form-input", "rows": 2, "placeholder": "https://..."}),
            "extra": forms.Textarea(attrs=TEXTAREA),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Django, varsayılanı olmayan seçmeli alanlara boş "---------" seçeneği
        # ekler ve radyo düğmesinde onu seçili gösterir; zorunlu sorularda gereksiz.
        for alan in ("grade", "weekly_hours"):
            self.fields[alan].choices = [c for c in self.fields[alan].choices if c[0]]

    def clean_phone(self):
        telefon = self.cleaned_data["phone"].strip()
        if len(re.sub(r"\D", "", telefon)) < 10:
            raise forms.ValidationError("Geçerli bir telefon numarası yaz.")
        return telefon

    def clean_positions(self):
        # Modelde virgüllü metin olarak saklanır (bkz. BoardApplication.positions).
        return ",".join(self.cleaned_data["positions"])
