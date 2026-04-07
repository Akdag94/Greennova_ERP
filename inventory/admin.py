from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Sum, Q
from django.shortcuts import render
from django.http import HttpResponseRedirect
from import_export.admin import ImportExportModelAdmin
from datetime import timedelta
from django.utils import timezone

# Modeller
from .models import Depo, UrunKategorisi, Palet
from finance.models import Sevkiyat, Gider

# --- 1. ÖZEL FİLTRE: STOK GÖRÜNÜMÜ ---
class StokDurumuFiltresi(admin.SimpleListFilter):
    title = 'Stok Görünümü'
    parameter_name = 'stok_durumu'

    def lookups(self, request, model_admin):
        return (
            ('aktif', 'Sadece Aktif Stok (Depo)'),
            ('gecmis', 'Sadece Teslim Edilenler'),
            ('hepsi', 'Tüm Kayıtlar (Geçmiş Dahil)'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'aktif' or self.value() is None:
            return queryset.exclude(durum='cikti')
        if self.value() == 'gecmis':
            return queryset.filter(durum='cikti')
        return queryset

# --- 2. TOPLU SEVKİYAT EYLEMİ ---
@admin.action(description='Seçili paletleri sevkiyata yükle')
def toplu_sevkiyata_yukle(modeladmin, request, queryset):
    if 'apply' in request.POST:
        sevkiyat_id = request.POST.get('sevkiyat_id')
        sevkiyat = Sevkiyat.objects.get(id=sevkiyat_id)
        count = 0
        for palet in queryset:
            if palet.durum in ['depoda', 'stokta', 'isleniyor']:
                palet.sevkiyat = sevkiyat
                palet.durum = 'yuklendi'
                palet.save()
                count += 1
        modeladmin.message_user(request, f"{count} adet palet {sevkiyat.plaka} aracına yüklendi.")
        return HttpResponseRedirect(f"/admin/finance/sevkiyat/{sevkiyat_id}/change/")

    return render(request, 'admin/sevkiyat_secim.html', {
        'paletler': queryset,
        'sevkiyatlar': Sevkiyat.objects.filter(tamamlandi=False),
    })

# --- 3. DEPO ADMİN ---
@admin.register(Depo)
class DepoAdmin(ImportExportModelAdmin):
    list_display = ('ad', 'kapasite_palet', 'mevcut_doluluk', 'doluluk_grafigi', 'sicaklik')
    search_fields = ('ad',)

    def mevcut_doluluk(self, obj):
        return f"{obj.mevcut_palet_sayisi()} / {obj.kapasite_palet} Palet"
    mevcut_doluluk.short_description = "Doluluk Durumu"

    def doluluk_grafigi(self, obj):
        oran = obj.doluluk_orani()
        renk = "#28a745" if oran <= 70 else "#ffc107" if oran <= 90 else "#dc3545"
        return format_html(
            '<div style="width:100px; background:#eee; border-radius:5px; border:1px solid #ccc;">'
            '<div style="width:{}px; background:{}; height:12px; border-radius:4px;"></div>'
            '</div> <small>%{}</small>', oran, renk, oran
        )
    doluluk_grafigi.short_description = "Doluluk Oranı"

# --- 4. ÜRÜN CİNSİ ADMİN ---
@admin.register(UrunKategorisi)
class UrunKategorisiAdmin(ImportExportModelAdmin):
    list_display = ('ad', 'toplam_stok_kg', 'aktif_palet_sayisi')
    search_fields = ('ad',)

    def toplam_stok_kg(self, obj):
        toplam = obj.palet_set.filter(durum__in=['depoda', 'stokta', 'isleniyor']).aggregate(Sum('miktar_kg'))['miktar_kg__sum'] or 0
        return format_html('<b>{} KG</b>', toplam)
    toplam_stok_kg.short_description = "Toplam Stok (Depo)"

    def aktif_palet_sayisi(self, obj):
        return obj.palet_set.filter(durum__in=['depoda', 'stokta', 'isleniyor']).count()
    aktif_palet_sayisi.short_description = "Palet Adedi"

# --- 5. PALET ADMİN ---
@admin.register(Palet)
class PaletAdmin(ImportExportModelAdmin):
    list_display = ('palet_no', 'urun_cinsi', 'foto_onizleme', 'toplam_palet_adedi', 'brut_miktar_kg', 'miktar_kg', 'isleme_farki_gosterge', 'durum_gosterge', 'qr_kod_onizleme')
    list_filter = (StokDurumuFiltresi, 'durum', 'depo_konumu', 'urun_cinsi')
    search_fields = ('palet_no', 'mustahsil__ad_soyad')
    readonly_fields = ('qr_kod_onizleme', 'foto_onizleme', 'fire_miktar_kg') 
    autocomplete_fields = ['mustahsil', 'depo_konumu', 'urun_cinsi']
    actions = [toplu_sevkiyata_yukle]
    
    fields = (
        'urun_cinsi', 'mustahsil', 'depo_konumu', 
        'brut_miktar_kg', 'miktar_kg', 'toplam_palet_adedi', 
        'birim_fiyat', 'palet_no', 'sevkiyat', 'durum', 'urun_fotografi'
    )

    def isleme_farki_gosterge(self, obj):
        return format_html('<b style="color: #666;">{} KG</b>', obj.fire_miktar_kg)
    isleme_farki_gosterge.short_description = "İç Fark (Fire)"

    def foto_onizleme(self, obj):
        if obj.urun_fotografi:
            return format_html(
                '<a href="{0}" target="_blank"><img src="{0}" width="55" height="55" style="border-radius:8px; border:1px solid #ddd; object-fit:cover;" /></a>', 
                obj.urun_fotografi.url
            )
        return format_html('<span style="color: #999;">📸 Foto Yok</span>')
    foto_onizleme.short_description = "Ürün Görseli"

    def durum_gosterge(self, obj):
        if obj.sevkiyat:
            if obj.sevkiyat.tamamlandi:
                color, icon, text = "#28a745", "✅", f"Teslim Edildi ({obj.sevkiyat.plaka})"
            else:
                color, icon, text = "#ffc107", "🚚", f"Tırda ({obj.sevkiyat.plaka})"
        else:
            color, icon, text = "#6c757d", "🏠", obj.get_durum_display()

        return format_html(
            '<b style="color: {0}; background: {0}15; padding: 4px 8px; border-radius: 5px;">{1} {2}</b>',
            color, icon, text
        )
    durum_gosterge.short_description = "GÜNCEL DURUM"

    def qr_kod_onizleme(self, obj):
        if obj.qr_kod:
            return format_html(
                '<a href="{0}" target="_blank"><img src="{0}" width="45" height="45" style="border-radius:5px; border:1px solid #ddd; transition: 0.3s;" onmouseover="this.style.transform=\'scale(1.2)\'" onmouseout="this.style.transform=\'scale(1)\'" /></a>', 
                obj.qr_kod.url
            )
        return "Yok"
    qr_kod_onizleme.short_description = "Karekod"

# --- 6. DASHBOARD İSTATİSTİKLERİ ---
def get_admin_stats(request):
    stok_kg = Palet.objects.filter(durum__in=['depoda', 'stokta', 'isleniyor']).aggregate(Sum('miktar_kg'))['miktar_kg__sum'] or 0
    ciro = Sevkiyat.objects.aggregate(Sum('toplam_satis_tutari'))['toplam_satis_tutari__sum'] or 0
    gider = Gider.objects.aggregate(Sum('miktar'))['miktar__sum'] or 0
    
    sevkiyatlar = Sevkiyat.objects.all()
    toplam_sevkiyat_kari = sum(float(s.kar_zarar_durumu()) for s in sevkiyatlar)
    net_kar = float(toplam_sevkiyat_kari) - float(gider)

    # 📈 EKSİK OLAN GRAFİK VERİSİ BURAYA EKLENDİ:
    bugun = timezone.now().date()
    gunler = []
    tonajlar = []
    gun_ismleri = {'Monday': 'Pzt', 'Tuesday': 'Sal', 'Wednesday': 'Çar', 'Thursday': 'Per', 'Friday': 'Cum', 'Saturday': 'Cmt', 'Sunday': 'Paz'}
    
    for i in range(6, -1, -1):
        tarih = bugun - timedelta(days=i)
        gun_adi = gun_ismleri.get(tarih.strftime('%A'))
        gunluk_toplam = Palet.objects.filter(sevkiyat__cikis_tarihi__date=tarih, sevkiyat__tamamlandi=True).aggregate(Sum('miktar_kg'))['miktar_kg__sum'] or 0
        gunler.append(gun_adi)
        tonajlar.append(float(gunluk_toplam))

    return {
        'stok_kg': f"{float(stok_kg):,.0f}".replace(",", "."),
        'ciro': f"{float(ciro):,.2f}".replace(",", "."),
        'gider': f"{float(gider):,.2f}".replace(",", "."),
        'net_kar': f"{float(net_kar):,.2f}".replace(",", "."),
        'net_kar_sayi': float(net_kar),
        'grafik_gunler': gunler,   # Yeni
        'grafik_veriler': tonajlar, # Yeni
    }

# Admin Site Ayarları
admin.site.index_title = "GreenNova ERP - Yönetim Paneli"
admin.site.site_header = "GreenNova Tarım"
admin.site.index_template = "admin/index.html"

original_index = admin.site.index
def custom_index(request, extra_context=None):
    extra_context = extra_context or {}
    extra_context.update(get_admin_stats(request))
    return original_index(request, extra_context)

admin.site.index = custom_index