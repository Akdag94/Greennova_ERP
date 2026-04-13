from django.contrib import admin
from django.db.models import Sum, Q
from django.utils.html import format_html
from import_export.admin import ImportExportModelAdmin
from .models import Gider, Mustahsil, CariHareket, Sevkiyat, Musteri, MusteriHareket 
from inventory.models import Palet

# --- MÜŞTERİ (ALICI) YÖNETİMİ ---
@admin.register(Musteri)
class MusteriAdmin(ImportExportModelAdmin):
    list_display = ('unvan', 'bolge', 'telefon', 'renkli_alacak_bakiyesi')
    search_fields = ('unvan', 'bolge')

    def renkli_alacak_bakiyesi(self, obj):
        bakiye = obj.toplam_alacagimiz
        renk = "#28a745" if bakiye > 0 else "#666"
        bakiye_formatli = "{:,.2f} ₺".format(bakiye).replace(",", "X").replace(".", ",").replace("X", ".")
        return format_html('<b style="color: {};">{}</b>', renk, bakiye_formatli)
    renkli_alacak_bakiyesi.short_description = "Güncel Alacağımız"

# --- MÜŞTERİ HAREKETLERİ ---
@admin.register(MusteriHareket)
class MusteriHareketAdmin(ImportExportModelAdmin):
    list_display = ('musteri', 'islem_tipi', 'miktar_formatli', 'tarih', 'durum_etiketi', 'odendi_mi', 'sevkiyat')
    list_filter = ('islem_tipi', 'odendi_mi', 'tarih')
    list_editable = ('odendi_mi',)
    search_fields = ('musteri__unvan', 'aciklama')
    autocomplete_fields = ['musteri', 'sevkiyat']

    def miktar_formatli(self, obj):
        return f"{obj.miktar:,.2f} ₺".replace(",", "X").replace(".", ",").replace("X", ".")
    miktar_formatli.short_description = "Tutar"

    def durum_etiketi(self, obj):
        if obj.odendi_mi:
            return format_html('<span style="background: #28a745; color: white; padding: 3px 10px; border-radius: 12px; font-size: 11px; font-weight: bold;">✅ ÖDENDİ</span>')
        return format_html('<span style="background: #ffc107; color: black; padding: 3px 10px; border-radius: 12px; font-size: 11px; font-weight: bold;">⏳ BEKLİYOR</span>')
    durum_etiketi.short_description = "Durum"

# --- MÜSTAHSİL & GİDER ---
@admin.register(Mustahsil)
class MustahsilAdmin(ImportExportModelAdmin):
    list_display = ('ad_soyad', 'bolge', 'telefon', 'toplam_borc')
    search_fields = ('ad_soyad', 'bolge')

@admin.register(CariHareket)
class CariHareketAdmin(ImportExportModelAdmin):
    list_display = ('mustahsil', 'islem_tipi', 'miktar', 'tarih', 'makbuz_link')
    list_filter = ('islem_tipi', 'tarih')
    search_fields = ('mustahsil__ad_soyad',)
    autocomplete_fields = ['mustahsil']

    def makbuz_link(self, obj):
        if obj.islem_tipi == 'alimgiris':
            return format_html('<a href="/finance/makbuz/{}/" target="_blank" style="background:#28a745;color:white;padding:3px 8px;border-radius:4px;text-decoration:none;">📄 Yazdır</a>', obj.id)
        return "-"

    # 🔥 CARİ HAREKETLER LİSTESİNDE DASHBOARD GÖRÜNSÜN DERSEN BURAYA DA EKLİYORUZ:
    def changelist_view(self, request, extra_context=None):
        gelir = Sevkiyat.objects.aggregate(Sum('toplam_satis_tutari'))['toplam_satis_tutari__sum'] or 0
        gider = Gider.objects.aggregate(Sum('miktar'))['miktar__sum'] or 0
        borc = Mustahsil.objects.aggregate(Sum('toplam_borc'))['toplam_borc__sum'] or 0
        alacak = Musteri.objects.aggregate(Sum('toplam_alacagimiz'))['toplam_alacagimiz__sum'] or 0
        
        extra_context = extra_context or {}
        extra_context['ozet_veriler'] = {
            'gelir': "{:,.2f}".format(gelir).replace(",", "X").replace(".", ",").replace("X", "."),
            'gider': "{:,.2f}".format(gider).replace(",", "X").replace(".", ",").replace("X", "."),
            'borc': "{:,.2f}".format(borc).replace(",", "X").replace(".", ",").replace("X", "."),
            'alacak': "{:,.2f}".format(alacak).replace(",", "X").replace(".", ",").replace("X", "."),
            'net': "{:,.2f}".format(float(gelir) - float(gider)).replace(",", "X").replace(".", ",").replace("X", "."),
        }
        return super().changelist_view(request, extra_context=extra_context)

@admin.register(Gider)
class GiderAdmin(ImportExportModelAdmin):
    list_display = ('baslik', 'kategori', 'miktar', 'tarih')
    list_filter = ('kategori', 'tarih')
    search_fields = ('baslik', 'aciklama')

# --- SEVKİYAT (TIR) YÖNETİMİ ---
class PaletInline(admin.TabularInline):
    model = Palet
    extra = 0
    fields = ('palet_no', 'urun_cinsi', 'miktar_kg', 'toplam_palet_adedi', 'durum')
    readonly_fields = ('palet_no', 'urun_cinsi', 'miktar_kg', 'toplam_palet_adedi')

@admin.register(Sevkiyat)
class SevkiyatAdmin(ImportExportModelAdmin):
    # list_display içine 'toplam_satis_tutari_goster' fonksiyonunu ekledik
    list_display = ('plaka', 'gidecegi_yer', 'toplam_tonaj', 'palet_sayisi_ozeti', 'toplam_satis_tutari_goster', 'kar_durumu', 'tamamlandi')
    list_filter = ('tamamlandi', 'cikis_tarihi')
    search_fields = ('plaka', 'sofor_ad')
    inlines = [PaletInline]

    # --- YENİ: Toplam Satış Tutarı (Mal Bedeli) Gösterimi ---
    def toplam_satis_tutari_goster(self, obj):
        # Modelindeki toplam_satis_tutari alanını TL formatında gösterir
        tutar = obj.toplam_satis_tutari or 0
        tutar_formatli = "{:,.2f} ₺".format(tutar).replace(",", "X").replace(".", ",").replace("X", ".")
        return format_html('<b style="color: #007bff;">{}</b>', tutar_formatli)
    toplam_satis_tutari_goster.short_description = "Toplam Mal Bedeli"

    # --- GÜNCELLEME: Kar Durumu ---
    def kar_durumu(self, obj):
        try:
            # Modelindeki kar_zarar_durumu() fonksiyonunu çağırıyoruz
            kar = obj.kar_zarar_durumu()
            if kar is None: kar = 0
            
            renk = "#28a745" if kar >= 0 else "#dc3545"
            simge = "▲" if kar >= 0 else "▼"
            kar_formatli = "{:,.2f} ₺".format(kar).replace(",", "X").replace(".", ",").replace("X", ".")
            
            return format_html('<b style="color: {};">{} {}</b>', renk, simge, kar_formatli)
        except Exception as e:
            # Eğer modeldeki fonksiyonda hata varsa admin panelinde hatayı küçük harfle gösterir
            return format_html('<span style="color: gray;">Hesap hatası: {}</span>', str(e)[:20])
    kar_durumu.short_description = "Net Kâr/Zarar"

    # Diğer fonksiyonların (tonaj, palet özeti, changelist_view) aynen kalsın...
    # 🔥 SEVKİYAT LİSTESİNDE DASHBOARD GÖRÜNSÜN DERSEN BURAYA DA EKLİYORUZ:
    def changelist_view(self, request, extra_context=None):
        gelir = Sevkiyat.objects.aggregate(Sum('toplam_satis_tutari'))['toplam_satis_tutari__sum'] or 0
        gider = Gider.objects.aggregate(Sum('miktar'))['miktar__sum'] or 0
        borc = Mustahsil.objects.aggregate(Sum('toplam_borc'))['toplam_borc__sum'] or 0
        alacak = Musteri.objects.aggregate(Sum('toplam_alacagimiz'))['toplam_alacagimiz__sum'] or 0
        
        extra_context = extra_context or {}
        extra_context['ozet_veriler'] = {
            'gelir': "{:,.2f}".format(gelir).replace(",", "X").replace(".", ",").replace("X", "."),
            'gider': "{:,.2f}".format(gider).replace(",", "X").replace(".", ",").replace("X", "."),
            'borc': "{:,.2f}".format(borc).replace(",", "X").replace(".", ",").replace("X", "."),
            'alacak': "{:,.2f}".format(alacak).replace(",", "X").replace(".", ",").replace("X", "."),
            'net': "{:,.2f}".format(float(gelir) - float(gider)).replace(",", "X").replace(".", ",").replace("X", "."),
        }
        return super().changelist_view(request, extra_context=extra_context)
    

    def toplam_tonaj(self, obj):
        toplam = obj.paletler.aggregate(Sum('miktar_kg'))['miktar_kg__sum'] or 0
        return f"{toplam} KG"

    def palet_sayisi_ozeti(self, obj):
        adet = obj.paletler.aggregate(Sum('toplam_palet_adedi'))['toplam_palet_adedi__sum'] or 0
        return format_html('<b>{} Palet</b>', adet)

        
    

# Admin Genel Başlıkları
admin.site.index_title = "GreenNova ERP - Yönetim Paneli"
admin.site.site_header = "GreenNova Tarım"