"""
E-posta Doğrulama Tokenı
=========================

Şifre sıfırlama token'ıyla aynı altyapı (HMAC + zaman damgası, veritabanına
yazılmaz) — farklı hash girdisi ve farklı tuzla.

Neden last_login ve parola hash'i YOK?
    Varsayılan PasswordResetTokenGenerator ikisini de hash'e katar. Kayıt akışı
    token'ı üretir üretmez login() çağırıyor ve login() last_login'i
    güncelliyor; dahil etseydik her link doğar doğmaz geçersiz olurdu.

    - is_verified hash'te → link bir kez kullanılınca ölür.
    - email hash'te       → adres değişirse eski link ölür.
    - Süre: PASSWORD_RESET_TIMEOUT (Django varsayılanı 3 gün).
"""

from django.contrib.auth.tokens import PasswordResetTokenGenerator


class EmailVerificationTokenGenerator(PasswordResetTokenGenerator):
    # Farklı tuz: şifre sıfırlama token'ı doğrulama linkinde (ya da tersi) geçmez.
    key_salt = "users.tokens.EmailVerificationTokenGenerator"

    def _make_hash_value(self, user, timestamp):
        return f"{user.pk}{user.email}{user.is_verified}{timestamp}"


email_verification_token = EmailVerificationTokenGenerator()
