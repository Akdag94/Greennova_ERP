from django.db import models
from django.utils import timezone
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db.models import Sum, Q

# --- İŞLETME GİDERLERİ ---
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

    def __str__(self):
        return f"{self.get_kategori_display()} - {self.miktar} ₺"

# --- MÜSTAHSİL (ÜRETİCİ) ---
class Mustahsil(models.Model):
    ad_soyad = models.CharField(max_length=200, verbose_name="Üretici Ad Soyad")
    tc_no = models.CharField(max_length=11, blank=True, null=True, verbose_name="TC Kimlik No")
    telefon = models.CharField(max_length=15, blank=True, null=True, verbose_name="Telefon")
    bolge = models.CharField(max_length=100, verbose_name="Bölge/Köy")
    # Büyük rakamlar için hane sayısı 15 yapıldı
    toplam_borc = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name="Güncel Borcumuz (₺)")

    class Meta:
        verbose_name = "Müstahsil (Üretici)"
        verbose_name_plural = "Müstahsiller"

    def __str__(self):
        return f"{self.ad_soyad} ({self.bolge}) - Bakiye: {self.toplam_borc} ₺"

# --- CARİ HAREKETLER ---
class CariHareket(models.Model):
    ISLEM_TIPLERI = (
        ('alimgiris', 'Mal Alım Girişi (Borçlanırız)'),
        ('odeme', 'Ödeme Yapıldı (Borç Azalır)'),
        ('fason_hizmet', 'Fason Hizmet Bedeli (Alacaklanırız)'),
    )
    mustahsil = models.ForeignKey(Mustahsil, on_delete=models.CASCADE, related_name='hareketler', verbose_name="Müstahsil")
    islem_tipi = models.CharField(max_length=20, choices=ISLEM_TIPLERI, verbose_name="İşlem Tipi")
    miktar = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="Tutar (₺)")
    tarih = models.DateField(default=timezone.now, verbose_name="İşlem Tarihi")
    aciklama = models.TextField(blank=True, null=True, verbose_name="Not/Açıklama")

    class Meta:
        verbose_name = "Cari Hareket"
        verbose_name_plural = "Cari Hareketler"

# --- SEVKİYAT / TIR YÖNETİMİ ---
class Sevkiyat(models.Model):
    plaka = models.CharField(max_length=20, verbose_name="Araç Plakası")
    sofor_ad = models.CharField(max_length=100, verbose_name="Şoför Ad Soyad")
    # Gideceği yer artık Müşteriler listesinden seçilecek
    musteri = models.ForeignKey('Musteri', on_delete=models.CASCADE, verbose_name="Alıcı Müşteri", related_name="sevkiyatlar", null=True)
    cikis_tarihi = models.DateTimeField(default=timezone.now, verbose_name="Çıkış Tarihi")
    tamamlandi = models.BooleanField(default=False, verbose_name="Teslimat Tamamlandı")
    satis_birim_fiyat = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Satış Birim Fiyat (KG/₺)")
    toplam_satis_tutari = models.DecimalField(max_digits=15, decimal_places=2, default=0, editable=False, verbose_name="Toplam Satış Tutarı (₺)")

    class Meta:
        verbose_name = "Sevkiyat / Tır"
        verbose_name_plural = "Sevkiyatlar ve Tırlar"

    def __str__(self):
        # En güvenli hali budur, musteri yoksa bile hata vermez
        return f"{self.plaka} - {self.musteri.unvan if self.musteri else 'Müşteri Yok'}"

    def kar_zarar_durumu(self):
        # MUDANYA HESABI: 
        # Maliyet: Kantar Kilosu (Brüt) üzerinden ödediğimiz (toplam_tutar)
        # Satış: Paketlenen (Net) Kilo üzerinden kazandığımız (toplam_satis_tutari)
        # Çıkma malların alış maliyeti 0 olduğu için kârı yükseltecektir.
        toplam_maliyet = self.paletler.aggregate(Sum('toplam_tutar'))['toplam_tutar__sum'] or 0
        kar = float(self.toplam_satis_tutari) - float(toplam_maliyet)
        return round(kar, 2)

    def save(self, *args, **kwargs):
        # 1. Önce tır kaydını oluştur/güncelle (ID oluşması için önemli)
        super().save(*args, **kwargs)
        
        # 2. Satış Tutarı Hesaplama: Tırdaki paletlerin NET kilosu üzerinden
        toplam_net_kg = self.paletler.aggregate(Sum('miktar_kg'))['miktar_kg__sum'] or 0
        yeni_satis_tutari = float(toplam_net_kg) * float(self.satis_birim_fiyat)
        
        # 3. Eğer tutar değiştiyse güncelle (Sonsuz döngüyü önlemek için update_fields kullanıyoruz)
        if float(self.toplam_satis_tutari) != yeni_satis_tutari:
            self.toplam_satis_tutari = yeni_satis_tutari
            super().save(update_fields=['toplam_satis_tutari'])

        # 4. TESLİMAT TAMAMLANDIYSA YAPILACAKLAR
        if self.tamamlandi:
            # A) Paletleri 'çıktı' statüsüne çek
            self.paletler.all().update(durum='cikti')
            
            # B) Müşteriye Otomatik Alacak (Borç) Kaydı Oluştur
            if self.musteri:
                # Daha önce bu tır için bir satış kaydı oluşturulmuş mu bak (Mükerrer kaydı önler)
                hareket_var_mi = MusteriHareket.objects.filter(sevkiyat=self, islem_tipi='satis').exists()
                
                if not hareket_var_mi:
                    MusteriHareket.objects.create(
                        musteri=self.musteri,
                        sevkiyat=self,
                        islem_tipi='satis',
                        miktar=self.toplam_satis_tutari,
                        tarih=timezone.now().date(),
                        aciklama=f"{self.plaka} plakalı tır sevkiyatı otomatik alacak kaydı.",
                        odendi_mi=False
                    )

# --- OTOMATİK BORÇ HESAPLAMA SİNYALİ ---
@receiver([post_save, post_delete], sender=CariHareket)
def guncelle_mustahsil_borcu(sender, instance, **kwargs):
    mustahsil = instance.mustahsil
    veriler = CariHareket.objects.filter(mustahsil=mustahsil).aggregate(
        alim=Sum('miktar', filter=Q(islem_tipi='alimgiris')),
        odeme=Sum('miktar', filter=Q(islem_tipi='odeme')),
        fason=Sum('miktar', filter=Q(islem_tipi='fason_hizmet'))
    )
    alim = veriler['alim'] or 0
    odeme = veriler['odeme'] or 0
    fason = veriler['fason'] or 0
    
    # Müstahsile Kantar (Brüt) üzerinden borçlanıyoruz.
    # Çıkma malın maliyeti 0 olduğu için borç hesabını etkilemez.
    mustahsil.toplam_borc = alim - odeme - fason
    mustahsil.save()

   # --- MÜŞTERİ (ALICI) ---
class Musteri(models.Model):
    unvan = models.CharField(max_length=255, verbose_name="Müşteri Ünvanı / Ad Soyad")
    telefon = models.CharField(max_length=15, blank=True, null=True, verbose_name="Telefon")
    bolge = models.CharField(max_length=100, blank=True, null=True, verbose_name="Bölge/Şehir")
    toplam_alacagimiz = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name="Güncel Alacak (₺)")

    class Meta:
        verbose_name = "Müşteri (Alıcı)"
        verbose_name_plural = "Müşteriler"

    def __str__(self):
        return f"{self.unvan} - Bakiye: {self.toplam_alacagimiz} ₺"

# --- MÜŞTERİ HAREKETLERİ ---
class MusteriHareket(models.Model):
    ISLEM_TIPLERI = (
        ('satis', 'Satış / Alacak Ekle'),
        ('tahsilat', 'Tahsilat / Ödeme Alındı'),
    )
    musteri = models.ForeignKey(Musteri, on_delete=models.CASCADE, related_name='hareketler', verbose_name="Müşteri")
    islem_tipi = models.CharField(max_length=20, choices=ISLEM_TIPLERI, verbose_name="İşlem Tipi")
    miktar = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="Tutar (₺)")
    tarih = models.DateField(default=timezone.now, verbose_name="Tarih")
    
    # 🔥 İSTEDİĞİN ÖDENDİ İŞARETİ
    odendi_mi = models.BooleanField(default=False, verbose_name="Ödeme Kapandı/Ödendi")
    
    aciklama = models.TextField(blank=True, null=True, verbose_name="Not/Açıklama")
    sevkiyat = models.ForeignKey('Sevkiyat', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="İlgili Tır/Plaka")

    class Meta:
        verbose_name = "Müşteri Hareketi"
        verbose_name_plural = "Müşteri Hareketleri"

# --- OTOMATİK HESAPLAMA SİNYALİ ---
@receiver([post_save, post_delete], sender=MusteriHareket)
def guncelle_musteri_bakiyesi(sender, instance, **kwargs):
    musteri = instance.musteri
    veriler = MusteriHareket.objects.filter(musteri=musteri).aggregate(
        satis=Sum('miktar', filter=Q(islem_tipi='satis')),
        tahsilat=Sum('miktar', filter=Q(islem_tipi='tahsilat'))
    )
    satis = veriler['satis'] or 0
    tahsilat = veriler['tahsilat'] or 0
    musteri.toplam_alacagimiz = satis - tahsilat
    musteri.save()