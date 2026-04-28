# __sig__: 76a253b5 | build:2026 | dev:609191fb
from django.db import models
from django.utils import timezone
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db.models import Sum, Q
from decimal import Decimal


# =============================================================
# 1) İŞLETME GİDERLERİ
# =============================================================
class Gider(models.Model):
    KATEGORI_SECENEKLERI = (
        ('elektrik', 'Elektrik Faturası'),
        ('su', 'Su Faturası'),
        ('dogalgaz', 'Doğalgaz Faturası'),
        ('kira', 'Depo/Ofis Kirası'),
        ('personel', 'Personel Maaş/Yevmiye'),
        ('bakim', 'Makine Bakım/Onarım'),
        ('diger', 'Diğer İşletme Giderleri'),
    )
    baslik = models.CharField(max_length=200, verbose_name="Gider Başlığı")
    kategori = models.CharField(max_length=20, choices=KATEGORI_SECENEKLERI, verbose_name="Gider Kategorisi")
    miktar = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Tutar (₺)")
    tarih = models.DateField(default=timezone.now, verbose_name="Harcama Tarihi")
    aciklama = models.TextField(blank=True, null=True, verbose_name="Açıklama")

    class Meta:
        verbose_name = "İşletme Gideri"
        verbose_name_plural = "İşletme Giderleri"
        ordering = ['-tarih']

    def __str__(self):
        return f"{self.get_kategori_display()} - {self.miktar} ₺"


# =============================================================
# 2) MÜSTAHSİL (ÜRETİCİ)
# =============================================================
class Mustahsil(models.Model):
    ad_soyad = models.CharField(max_length=200, verbose_name="Üretici Ad Soyad")
    tc_no = models.CharField(max_length=11, blank=True, null=True, verbose_name="TC Kimlik No")
    telefon = models.CharField(max_length=15, blank=True, null=True, verbose_name="Telefon")
    bolge = models.CharField(max_length=100, verbose_name="Bölge/Köy")
    toplam_borc = models.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal('0.00'),
        verbose_name="Güncel Borcumuz (₺)"
    )

    class Meta:
        verbose_name = "Müstahsil (Üretici)"
        verbose_name_plural = "Müstahsiller"
        ordering = ['ad_soyad']

    def __str__(self):
        # Sadece adı ve bölgeyi döndür — bakiye admin'de ayrı kolon olarak gösterilecek
        return f"{self.ad_soyad} ({self.bolge})"


# =============================================================
# 3) MÜŞTERİ (ALICI) — Mustahsil'den ÖNCE değil, Mustahsil'den SONRA olmalı
#    çünkü Sevkiyat Musteri'ye referans veriyor
# =============================================================
class Musteri(models.Model):
    unvan = models.CharField(max_length=255, verbose_name="Müşteri Ünvanı / Ad Soyad")
    telefon = models.CharField(max_length=15, blank=True, null=True, verbose_name="Telefon")
    bolge = models.CharField(max_length=100, blank=True, null=True, verbose_name="Bölge/Şehir")
    toplam_alacagimiz = models.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal('0.00'),
        verbose_name="Güncel Alacak (₺)"
    )

    class Meta:
        verbose_name = "Müşteri (Alıcı)"
        verbose_name_plural = "Müşteriler"
        ordering = ['unvan']

    def __str__(self):
        return self.unvan


# =============================================================
# 4) CARİ HAREKETLER (Müstahsile)
# =============================================================
class CariHareket(models.Model):
    ISLEM_TIPLERI = (
        ('alimgiris', 'Mal Alım Girişi (Borçlanırız)'),
        ('odeme', 'Ödeme Yapıldı (Borç Azalır)'),
        ('fason_hizmet', 'Fason Hizmet Bedeli (Alacaklanırız)'),
    )
    mustahsil = models.ForeignKey(
        Mustahsil, on_delete=models.CASCADE,
        related_name='hareketler', verbose_name="Müstahsil"
    )
    islem_tipi = models.CharField(max_length=20, choices=ISLEM_TIPLERI, verbose_name="İşlem Tipi")
    miktar = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="Tutar (₺)")
    tarih = models.DateField(default=timezone.now, verbose_name="İşlem Tarihi")
    aciklama = models.TextField(blank=True, null=True, verbose_name="Not/Açıklama")

    class Meta:
        verbose_name = "Cari Hareket"
        verbose_name_plural = "Cari Hareketler"
        ordering = ['-tarih', '-id']


# =============================================================
# 5) SEVKİYAT (TIR)
# =============================================================
class Sevkiyat(models.Model):
    plaka = models.CharField(max_length=20, verbose_name="Araç Plakası")
    sofor_ad = models.CharField(max_length=100, verbose_name="Şoför Ad Soyad")
    musteri = models.ForeignKey(
        Musteri, on_delete=models.CASCADE,
        verbose_name="Alıcı Müşteri", related_name="sevkiyatlar", null=True
    )
    cikis_tarihi = models.DateTimeField(default=timezone.now, verbose_name="Çıkış Tarihi")
    tamamlandi = models.BooleanField(default=False, verbose_name="Teslimat Tamamlandı")
    satis_birim_fiyat = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('0.00'),
        verbose_name="Satış Birim Fiyat (KG/₺)"
    )
    toplam_satis_tutari = models.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal('0.00'),
        editable=False, verbose_name="Toplam Satış Tutarı (₺)"
    )

    class Meta:
        verbose_name = "Sevkiyat / Tır"
        verbose_name_plural = "Sevkiyatlar ve Tırlar"
        ordering = ['-cikis_tarihi']

    def __str__(self):
        return f"{self.plaka} - {self.musteri.unvan if self.musteri else 'Müşteri Yok'}"

    def kar_zarar_durumu(self):
        """
        Kâr = Satış (Net kg × birim fiyat) - Maliyet (paletlerin toplam_tutar)
        """
        toplam_maliyet = self.paletler.aggregate(t=Sum('toplam_tutar'))['t'] or Decimal('0')
        kar = float(self.toplam_satis_tutari or 0) - float(toplam_maliyet)
        return round(kar, 2)

    def save(self, *args, **kwargs):
        # 1. Önce tır kaydını oluştur/güncelle
        super().save(*args, **kwargs)

        # 2. Satış tutarını yeniden hesapla
        toplam_net_kg = self.paletler.aggregate(t=Sum('miktar_kg'))['t'] or Decimal('0')
        yeni_satis_tutari = float(toplam_net_kg) * float(self.satis_birim_fiyat or 0)

        # 3. Değiştiyse güncelle (sonsuz döngüyü önlemek için update_fields)
        if float(self.toplam_satis_tutari or 0) != yeni_satis_tutari:
            self.toplam_satis_tutari = yeni_satis_tutari
            super().save(update_fields=['toplam_satis_tutari'])

        # 4. Tamamlandıysa
        if self.tamamlandi:
            # Paletleri 'çıktı' yap
            self.paletler.all().update(durum='cikti')

            # Müşteriye satış cari hareketi
            if self.musteri:
                hareket_var_mi = MusteriHareket.objects.filter(
                    sevkiyat=self, islem_tipi='satis'
                ).exists()
                if not hareket_var_mi and self.toplam_satis_tutari > 0:
                    MusteriHareket.objects.create(
                        musteri=self.musteri,
                        sevkiyat=self,
                        islem_tipi='satis',
                        miktar=self.toplam_satis_tutari,
                        tarih=timezone.now().date(),
                        aciklama=f"{self.plaka} plakalı tır sevkiyatı otomatik alacak kaydı.",
                        odendi_mi=False
                    )


# =============================================================
# 6) MÜŞTERİ HAREKETLERİ (Müşteriye)
# =============================================================
class MusteriHareket(models.Model):
    ISLEM_TIPLERI = (
        ('satis', 'Satış / Alacak Ekle'),
        ('tahsilat', 'Tahsilat / Ödeme Alındı'),
    )
    musteri = models.ForeignKey(
        Musteri, on_delete=models.CASCADE,
        related_name='hareketler', verbose_name="Müşteri"
    )
    islem_tipi = models.CharField(max_length=20, choices=ISLEM_TIPLERI, verbose_name="İşlem Tipi")
    miktar = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="Tutar (₺)")
    tarih = models.DateField(default=timezone.now, verbose_name="Tarih")
    odendi_mi = models.BooleanField(default=False, verbose_name="Ödeme Kapandı/Ödendi")
    aciklama = models.TextField(blank=True, null=True, verbose_name="Not/Açıklama")
    sevkiyat = models.ForeignKey(
        Sevkiyat, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name="İlgili Tır/Plaka"
    )

    class Meta:
        verbose_name = "Müşteri Hareketi"
        verbose_name_plural = "Müşteri Hareketleri"
        ordering = ['-tarih', '-id']


# =============================================================
# SİNYALLER — Otomatik bakiye güncellemesi
# =============================================================
@receiver([post_save, post_delete], sender=CariHareket)
def guncelle_mustahsil_borcu(sender, instance, **kwargs):
    """Müstahsil bakiyesini cari hareketlerden hesapla."""
    mustahsil = instance.mustahsil
    veriler = CariHareket.objects.filter(mustahsil=mustahsil).aggregate(
        alim=Sum('miktar', filter=Q(islem_tipi='alimgiris')),
        odeme=Sum('miktar', filter=Q(islem_tipi='odeme')),
        fason=Sum('miktar', filter=Q(islem_tipi='fason_hizmet'))
    )
    alim = veriler['alim'] or Decimal('0')
    odeme = veriler['odeme'] or Decimal('0')
    fason = veriler['fason'] or Decimal('0')
    mustahsil.toplam_borc = alim - odeme - fason
    mustahsil.save(update_fields=['toplam_borc'])


@receiver([post_save, post_delete], sender=MusteriHareket)
def guncelle_musteri_bakiyesi(sender, instance, **kwargs):
    """Müşteri alacak bakiyesini hareketlerden hesapla."""
    musteri = instance.musteri
    veriler = MusteriHareket.objects.filter(musteri=musteri).aggregate(
        satis=Sum('miktar', filter=Q(islem_tipi='satis')),
        tahsilat=Sum('miktar', filter=Q(islem_tipi='tahsilat'))
    )
    satis = veriler['satis'] or Decimal('0')
    tahsilat = veriler['tahsilat'] or Decimal('0')
    musteri.toplam_alacagimiz = satis - tahsilat
    musteri.save(update_fields=['toplam_alacagimiz'])
