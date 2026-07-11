from django.db import models

class LegalDocument(models.Model):
    title = models.CharField(max_length=200, verbose_name="Başlık")
    slug = models.SlugField(max_length=200, unique=True, help_text="URL uzantısı (örn: kvkk, gizlilik)")
    content = models.TextField(verbose_name="Sözleşme İçeriği (HTML)", help_text="Quill editor veya HTML ile hazırlanan içerik")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Son Güncellenme")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Hukuki Belge"
        verbose_name_plural = "Hukuki Belgeler"
        ordering = ["title"]

    def __str__(self):
        return self.title
