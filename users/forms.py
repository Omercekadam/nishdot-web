from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm

User = get_user_model()

class UserRegisterForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': '••••••••',
            'required': True
        }),
        label="Şifre"
    )
    password_confirm = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': '••••••••',
            'required': True
        }),
        label="Şifre Tekrar"
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Ad'}),
            'last_name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Soyad'}),
            'email': forms.EmailInput(attrs={'class': 'form-input', 'placeholder': 'ornek@email.com'}),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Bu e-posta adresiyle kayıtlı bir hesap zaten var.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        password_confirm = cleaned_data.get("password_confirm")

        if password and password_confirm and password != password_confirm:
            self.add_error('password_confirm', "Şifreler eşleşmiyor.")

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        # E-posta'dan otomatik kullanıcı adı oluşturma (örnek@gmail.com -> örnek_gmail_com)
        email = self.cleaned_data["email"]
        base_username = email.split('@')[0]
        username = base_username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1
        user.username = username

        if commit:
            user.save()
        return user


class UserLoginForm(AuthenticationForm):
    username = forms.EmailField(
        label="E-Posta",
        widget=forms.EmailInput(attrs={
            'class': 'form-input',
            'placeholder': 'ornek@email.com',
            'required': True
        })
    )
    password = forms.CharField(
        label="Şifre",
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': '••••••••',
            'required': True
        })
    )

    def clean(self):
        email = self.cleaned_data.get("username")
        password = self.cleaned_data.get("password")

        if email is not None and password:
            from django.contrib.auth import authenticate
            try:
                user_obj = User.objects.get(email=email)
                actual_username = user_obj.username
            except User.DoesNotExist:
                actual_username = email

            self.user_cache = authenticate(
                self.request, username=actual_username, password=password
            )
            if self.user_cache is None:
                raise self.get_invalid_login_error()
            # E-posta doğrulaması girişi engellemez; doğrulanmamış hesap
            # yalnızca uyarı bandını görür (bkz. components/verify_banner.html).
            self.confirm_login_allowed(self.user_cache)

        return self.cleaned_data


class UserProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'phone_number', 'birth_date', 'university', 'department', 'portfolio_url']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Ad'}),
            'last_name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Soyad'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-input', 'placeholder': '05XX XXX XX XX'}),

            'birth_date': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            'university': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Örn: İstanbul Nişantaşı Üniversitesi'}),
            'department': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Örn: Dijital Oyun Tasarımı'}),
            'portfolio_url': forms.Textarea(attrs={'class': 'form-input', 'placeholder': 'Birden fazla link eklemek için her linki yeni bir satıra yazabilirsiniz.\nÖrn:\nhttps://github.com/...\nhttps://artstation.com/...', 'rows': 3}),
        }
