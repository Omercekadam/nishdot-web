"""
Core Models — Soyut Temel Modeller
====================================

Bu modüldeki sınıflar doğrudan veritabanı tablosu OLUŞTURMAZ.
abstract = True olduğu için sadece miras alan modellere alan sağlar.

Kullanım:
    from core.models import TimeStampedModel

    class Event(TimeStampedModel):
        title = models.CharField(max_length=200)
        ...

    Bu şekilde Event modeli otomatik olarak created_at ve updated_at
    alanlarına sahip olur.
"""

from django.db import models


class TimeStampedModel(models.Model):
    """
    Tüm modellerin miras alacağı soyut temel model.

    Her kayıt için otomatik oluşturma ve güncelleme tarihi sağlar.
    Bu alanlar kullanıcı tarafından düzenlenemez — Django tarafından
    otomatik yönetilir.

    Attributes:
        created_at: Kaydın ilk oluşturulma tarihi. Bir kez yazılır,
                    sonra değişmez (auto_now_add=True).
        updated_at: Kaydın son güncellenme tarihi. Her save() çağrısında
                    otomatik güncellenir (auto_now=True).
    """

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Oluşturulma tarihi",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Son güncelleme tarihi",
    )

    class Meta:
        abstract = True
        # Varsayılan sıralama: en yeni kayıt en üstte.
        # Miras alan modeller bunu override edebilir.
        ordering = ["-created_at"]
