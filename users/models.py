from django.contrib.auth.models import AbstractUser
from django.db import models

class Personel(AbstractUser):
    # Roller için seçenekler
    ROL_SECENEKLERI = (
        ('admin', 'Sistem Yöneticisi'),
        ('manager', 'Bölüm Yöneticisi'),
        ('staff', 'Personel'),
    )

    rol = models.CharField(max_length=20, choices=ROL_SECENEKLERI, default='staff', verbose_name="Sistem Rolü")
    departman = models.CharField(max_length=100, blank=True, null=True, verbose_name="Departman")
    telefon = models.CharField(max_length=15, blank=True, null=True, verbose_name="Telefon Numarası")
    
    # İleride kart okutulduğunda eşleşecek olan eşsiz kart numarası
    rfid_kart_no = models.CharField(max_length=50, blank=True, null=True, unique=True, verbose_name="RFID Kart Numarası")

    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.get_rol_display()}"