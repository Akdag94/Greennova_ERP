from django.db import models
from django.conf import settings
from django.contrib.auth import get_user_model

# Projedeki aktif kullanıcı modelini (Personel) çekiyoruz
User = get_user_model()

class Yoklama(models.Model):
    ISLEM_SECENEKLERI = (
        ('giris', 'Giriş Yaptı'),
        ('cikis', 'Çıkış Yaptı'),
    )
    
    personel = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="Personel")
    islem_tipi = models.CharField(max_length=10, choices=ISLEM_SECENEKLERI, verbose_name="İşlem Tipi")
    tarih_saat = models.DateTimeField(auto_now_add=True, verbose_name="İşlem Zamanı")

    class Meta:
        verbose_name = "Yoklama"
        verbose_name_plural = "Yoklama"

    def __str__(self):
        ad = self.personel.get_full_name() or self.personel.username
        zaman = self.tarih_saat.strftime("%d.%m.%Y %H:%M")
        return f"{ad} - {self.get_islem_tipi_display()} ({zaman})"

# 🔥 HATAYI ÇÖZEN GÜNCEL RAPOR MODELİ
class PersonelRapor(User):
    class Meta:
        proxy = True
        verbose_name = "Personel Mesai Raporu"
        verbose_name_plural = "📊 Personel Mesai Raporları"