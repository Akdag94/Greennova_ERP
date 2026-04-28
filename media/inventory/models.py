# __sig__: 76a253b5 | build:2026 | dev:609191fb
from django.db import models
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db.models import Sum
import qrcode
from io import BytesIO
from django.core.files import File
from PIL import Image
from decimal import Decimal


class Depo(models.Model):
    ad = models.CharField(max_length=100, verbose_name="Depo/Oda Adı")
    kapasite_palet = models.IntegerField(verbose_name="Palet Kapasitesi")
    sicaklik = models.CharField(max_length=50, blank=True, null=True, verbose_name="İdeal Sıcaklık")

    class Meta:
        verbose_name = "Depo/Oda"
        verbose_name_plural = "Depolar ve Odalar"

    def mevcut_palet_sayisi(self):
        return self.palet_set.filter(durum__in=['depoda', 'isleniyor']).count()

    def doluluk_orani(self):
        if self.kapasite_palet > 0:
            oran = (self.mevcut_palet_sayisi() / self.kapasite_palet) * 100
            return round(oran, 1)
        return 0

    def __str__(self):
        return f"{self.ad} (%{self.doluluk_orani()} Dolu)"


class UrunKategorisi(models.Model):
    ad = models.CharField(max_length=100, verbose_name="Ürün Cinsi (Örn: Elma)")

    class Meta:
        verbose_name = "Ürün Cinsi"
        verbose_name_plural = "Ürün Cinsleri"

    def __str__(self):
        return self.ad


class Palet(models.Model):
    DURUM_SECENEKLERI = (
        ('depoda', 'Depoda Bekliyor'),
        ('isleniyor', 'İşleniyor/Paketlemede'),
        ('yuklendi', 'Tıra Yüklendi'),
        ('sevk', 'Sevkiyatta/Yolda'),
        ('cikti', 'Teslim Edildi'),
    )

    MULKIYET_SECENEKLERI = (
        ('oz_mal', 'Greennova Öz Malı'),
        ('fason', 'Fason Müşteri Malı'),
    )

    toplam_palet_adedi = models.PositiveIntegerField(
        default=1,
        verbose_name="Toplam Palet Adedi",
        help_text="İşleme sonucu çıkan palet sayısı"
    )

    palet_no = models.CharField(
        max_length=50, unique=True, blank=True, null=True,
        verbose_name="Palet ID / Barkod (Boş bırakılabilir)"
    )

    urun_fotografi = models.ImageField(
        upload_to='palet_fotos/%Y/%m/%d/', blank=True, null=True,
        verbose_name="Ürün Fotoğrafı (Kalite Kontrol)"
    )

    mulkiyet_tipi = models.CharField(
        max_length=20, choices=MULKIYET_SECENEKLERI,
        default='oz_mal', verbose_name="Mülkiyet"
    )
    urun_cinsi = models.ForeignKey(UrunKategorisi, on_delete=models.CASCADE, verbose_name="Ürün")
    mustahsil = models.ForeignKey('finance.Mustahsil', on_delete=models.CASCADE, verbose_name="Sahibi")
    sevkiyat = models.ForeignKey(
        'finance.Sevkiyat', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='paletler', verbose_name="Yüklendiği Tır"
    )
    depo_konumu = models.ForeignKey(
        Depo, on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name="Bulunduğu Oda"
    )

    brut_miktar_kg = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('0'),
        verbose_name="Kantar Giriş (Brüt KG)"
    )
    miktar_kg = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        verbose_name="Paketlenen / Stok (Net KG)"
    )
    fire_miktar_kg = models.DecimalField(
        max_digits=10, decimal_places=2, editable=False,
        default=Decimal('0'), verbose_name="İşleme Farkı (Fire/Çıkma)"
    )

    birim_fiyat = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('0'),
        verbose_name="Birim Fiyat (₺)"
    )
    toplam_tutar = models.DecimalField(
        max_digits=12, decimal_places=2, editable=False,
        default=Decimal('0'), verbose_name="Toplam Tutar (Ödemeye Esas)"
    )

    giris_tarihi = models.DateField(auto_now_add=True, verbose_name="Depoya Giriş Tarihi")
    durum = models.CharField(
        max_length=20, choices=DURUM_SECENEKLERI,
        default='isleniyor', verbose_name="Durum"
    )

    isleme_notu = models.TextField(blank=True, null=True, verbose_name="İşleme/Fason Notu")
    qr_kod = models.ImageField(upload_to='qr_codes/', blank=True, null=True, verbose_name="QR Kod")

    @property
    def guncel_durum(self):
        if self.sevkiyat:
            if self.sevkiyat.tamamlandi:
                return "✅ Teslim Edildi"
            return f"🚚 Tırda ({self.sevkiyat.plaka})"
        return self.get_durum_display()

    class Meta:
        verbose_name = "Palet Takibi"
        verbose_name_plural = "Depodaki Paletler"
        ordering = ['-id']

    def __str__(self):
        return f"Palet #{self.palet_no} ({self.get_durum_display()})"

    def save(self, *args, **kwargs):
        # 1. ÖDEME MATEMATİĞİ (Brüt KG x Birim Fiyat)
        try:
            self.toplam_tutar = Decimal(str(self.brut_miktar_kg or 0)) * Decimal(str(self.birim_fiyat or 0))
        except Exception:
            self.toplam_tutar = Decimal('0')

        # 2. İŞLEME FARKI (Brüt - Net)
        if self.brut_miktar_kg and self.miktar_kg:
            self.fire_miktar_kg = Decimal(str(self.brut_miktar_kg)) - Decimal(str(self.miktar_kg))
        else:
            self.fire_miktar_kg = Decimal('0')

        # 3. DURUM SENKRONİZASYONU (sevkiyat ile)
        if self.sevkiyat:
            if self.sevkiyat.tamamlandi:
                self.durum = 'cikti'
            else:
                self.durum = 'yuklendi'
        else:
            if self.durum in ['yuklendi', 'cikti']:
                self.durum = 'depoda'

        # 4. Depo seçildiyse ve hala isleniyor durumundaysa otomatik depoda yap
        if self.depo_konumu and self.durum == 'isleniyor' and not self.sevkiyat:
            self.durum = 'depoda'

        # 5. OTOMATİK PALET NO
        if not self.palet_no:
            last_palet = Palet.objects.order_by('id').last()
            next_id = (last_palet.id + 1) if last_palet else 1
            self.palet_no = f"PLT-{next_id}"

        super().save(*args, **kwargs)

        # 6. QR KOD (yalnızca yoksa, ID üretildikten sonra)
        if not self.qr_kod:
            try:
                qr = qrcode.QRCode(version=1, box_size=10, border=4)
                qr.add_data(str(self.id))
                qr.make(fit=True)
                img = qr.make_image(fill_color="black", back_color="white")

                buffer = BytesIO()
                img.save(buffer, format="PNG")
                fname = f'qr-{self.id}.png'
                self.qr_kod.save(fname, File(buffer), save=False)
                super().save(update_fields=['qr_kod'])
            except Exception as e:
                # QR oluşturma hatası tüm save'i bozmasın
                print(f"QR Kod oluşturma hatası: {e}")


# =============================================================
# SİNYAL: Palet kaydedildiğinde otomatik cari hareket
# =============================================================
@receiver(post_save, sender=Palet)
def mustahsil_otomatik_cari_hareket(sender, instance, created, **kwargs):
    """Yeni palet kaydı → müstahsile borçlanma."""
    from finance.models import CariHareket
    if created and instance.toplam_tutar and instance.toplam_tutar > 0:
        CariHareket.objects.create(
            mustahsil=instance.mustahsil,
            islem_tipi='alimgiris',
            miktar=instance.toplam_tutar,
            aciklama=f"Kantar Kaydı: Palet #{instance.palet_no} ({instance.brut_miktar_kg} KG x {instance.birim_fiyat} TL)"
        )
