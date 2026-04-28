# __sig__: 76a253b5 | build:2026 | dev:609191fb
from django.contrib import admin
from django.db.models import Sum
from django.utils.html import format_html
from django.urls import reverse
from import_export.admin import ImportExportModelAdmin
from .models import Gider, Mustahsil, CariHareket, Sevkiyat, Musteri, MusteriHareket
from inventory.models import Palet

import locale
from decimal import Decimal


def _para(sayi):
    """Türk para formatı: 1.234,56 ₺"""
    try:
        return "{:,.2f} ₺".format(sayi).replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "0,00 ₺"


def _yazdir_btn(url, etiket="📄 Yazdır", renk="#28a745"):
    return format_html(
        '<a href="{}" target="_blank" style="background:{};color:white;padding:3px 9px;'
        'border-radius:5px;text-decoration:none;font-size:11px;font-weight:600;">{}</a>',
        url, renk, etiket
    )


# ============================================================
# MÜŞTERİ
# ============================================================
@admin.register(Musteri)
class MusteriAdmin(ImportExportModelAdmin):
    list_display = ('unvan', 'bolge', 'telefon', 'renkli_alacak', 'islemler')
    search_fields = ('unvan', 'bolge')
    list_per_page = 30

    def renkli_alacak(self, obj):
        b = obj.toplam_alacagimiz
        renk = "#1a3a5e" if b > 0 else "#27ae60" if b < 0 else "#666"
        return format_html('<b style="color:{};">{}</b>', renk, _para(b))
    renkli_alacak.short_description = "Alacağımız"

    def islemler(self, obj):
        ekstre_url = reverse('musteri_ekstre', args=[obj.id])
        return _yazdir_btn(ekstre_url, "📋 Ekstre", "#007bff")
    islemler.short_description = "Belge"


# ============================================================
# MÜŞTERİ HAREKETLERİ
# ============================================================
@admin.register(MusteriHareket)
class MusteriHareketAdmin(ImportExportModelAdmin):
    list_display = ('musteri', 'islem_tipi', 'miktar_formatli', 'tarih', 'durum_etiketi', 'odendi_mi', 'sevkiyat', 'belge_btn')
    list_filter = ('islem_tipi', 'odendi_mi', 'tarih')
    list_editable = ('odendi_mi',)
    search_fields = ('musteri__unvan', 'aciklama')
    autocomplete_fields = ['musteri', 'sevkiyat']
    date_hierarchy = 'tarih'

    def miktar_formatli(self, obj):
        return _para(obj.miktar)
    miktar_formatli.short_description = "Tutar"

    def durum_etiketi(self, obj):
        if obj.odendi_mi:
            return format_html('<span style="background:#28a745;color:white;padding:3px 10px;border-radius:12px;font-size:11px;font-weight:bold;">✅ ÖDENDİ</span>')
        return format_html('<span style="background:#ffc107;color:#333;padding:3px 10px;border-radius:12px;font-size:11px;font-weight:bold;">⏳ BEKLİYOR</span>')
    durum_etiketi.short_description = "Durum"

    def belge_btn(self, obj):
        if obj.islem_tipi == 'tahsilat':
            url = reverse('musteri_tahsilat_makbuzu', args=[obj.id])
            return _yazdir_btn(url, "📄 Makbuz")
        return "—"
    belge_btn.short_description = "Belge"


# ============================================================
# MÜSTAHSİL
# ============================================================
@admin.register(Mustahsil)
class MustahsilAdmin(ImportExportModelAdmin):
    list_display = ('ad_soyad', 'bolge', 'telefon', 'renkli_borc', 'islemler')
    search_fields = ('ad_soyad', 'bolge')
    list_per_page = 30

    def renkli_borc(self, obj):
        b = obj.toplam_borc
        renk = "#1a3a5e" if b > 0 else "#666"
        return format_html('<b style="color:{};">{}</b>', renk, _para(b))
    renkli_borc.short_description = "Borcumuz"

    def islemler(self, obj):
        ekstre_url = reverse('mustahsil_ekstre', args=[obj.id])
        return _yazdir_btn(ekstre_url, "📋 Ekstre", "#007bff")
    islemler.short_description = "Belge"


# ============================================================
# CARİ HAREKETLER
# ============================================================
@admin.register(CariHareket)
class CariHareketAdmin(ImportExportModelAdmin):
    list_display = ('mustahsil', 'islem_tipi', 'miktar_formatli', 'tarih', 'makbuz_link')
    list_filter = ('islem_tipi', 'tarih')
    search_fields = ('mustahsil__ad_soyad',)
    autocomplete_fields = ['mustahsil']
    date_hierarchy = 'tarih'

    def miktar_formatli(self, obj):
        return _para(obj.miktar)
    miktar_formatli.short_description = "Tutar"

    def makbuz_link(self, obj):
        if obj.islem_tipi == 'alimgiris':
            url = reverse('mustahsil_makbuz', args=[obj.id])
            return _yazdir_btn(url, "📄 Alım Makbuzu")
        elif obj.islem_tipi == 'odeme':
            url = reverse('mustahsil_odeme_makbuzu', args=[obj.id])
            return _yazdir_btn(url, "📄 Ödeme Makbuzu", "#007bff")
        return "—"
    makbuz_link.short_description = "Belge"


# ============================================================
# SEVKİYAT (TIR)
# ============================================================
class PaletInline(admin.TabularInline):
    model = Palet
    extra = 0
    fields = ('palet_no', 'urun_cinsi', 'miktar_kg', 'toplam_palet_adedi', 'durum')
    readonly_fields = ('palet_no', 'urun_cinsi', 'miktar_kg', 'toplam_palet_adedi')
    can_delete = False
    show_change_link = True


@admin.register(Sevkiyat)
class SevkiyatAdmin(ImportExportModelAdmin):
    list_display = ('plaka', 'musteri', 'toplam_tonaj', 'palet_sayisi_ozeti',
                    'toplam_satis_tutari_goster', 'kar_durumu', 'tamamlandi', 'belgeler')
    list_filter = ('tamamlandi', 'cikis_tarihi', 'musteri')
    search_fields = ('plaka', 'sofor_ad', 'musteri__unvan')
    inlines = [PaletInline]
    autocomplete_fields = ['musteri']
    list_per_page = 25
    date_hierarchy = 'cikis_tarihi'

    def toplam_satis_tutari_goster(self, obj):
        return format_html('<b style="color:#007bff;">{}</b>',
                           _para(obj.toplam_satis_tutari or 0))
    toplam_satis_tutari_goster.short_description = "Satış Tutarı"

    def kar_durumu(self, obj):
        try:
            kar = obj.kar_zarar_durumu()
            if kar is None:
                kar = 0
            renk = "#28a745" if kar >= 0 else "#dc3545"
            simge = "▲" if kar >= 0 else "▼"
            return format_html('<b style="color:{};">{} {}</b>', renk, simge, _para(kar))
        except Exception:
            return format_html('<span style="color:gray;">—</span>')
    kar_durumu.short_description = "Kâr/Zarar"

    def toplam_tonaj(self, obj):
        # None hatasını önle
        toplam = obj.paletler.aggregate(t=Sum('miktar_kg'))['t']
        return f"{toplam or 0} KG"
    toplam_tonaj.short_description = "Tonaj"

    def palet_sayisi_ozeti(self, obj):
        adet = obj.paletler.aggregate(t=Sum('toplam_palet_adedi'))['t'] or 0
        return format_html('<b>{} Palet</b>', adet)
    palet_sayisi_ozeti.short_description = "Paletler"

    def belgeler(self, obj):
        fatura_url = reverse('musteri_fatura', args=[obj.id])
        irsaliye_url = reverse('sevkiyat_irsaliye', args=[obj.id])
        return format_html(
            '{} {}',
            _yazdir_btn(fatura_url, "🧾 Fatura"),
            _yazdir_btn(irsaliye_url, "📦 İrsaliye", "#6f42c1"),
        )
    belgeler.short_description = "Belgeler"

    def changelist_view(self, request, extra_context=None):
        from .models import Gider
        gelir = Sevkiyat.objects.aggregate(t=Sum('toplam_satis_tutari'))['t'] or 0
        gider_toplam = Gider.objects.aggregate(t=Sum('miktar'))['t'] or 0
        borc = Mustahsil.objects.aggregate(t=Sum('toplam_borc'))['t'] or 0
        alacak = Musteri.objects.aggregate(t=Sum('toplam_alacagimiz'))['t'] or 0
        bekleyen = MusteriHareket.objects.filter(
            odendi_mi=False, islem_tipi='satis'
        ).aggregate(t=Sum('miktar'))['t'] or 0

        extra_context = extra_context or {}
        extra_context['ozet_veriler'] = {
            'gelir': _para(gelir),
            'gider': _para(gider_toplam),
            'borc': _para(borc),
            'alacak': _para(alacak),
            'bekleyen': _para(bekleyen),
            'net': _para(float(gelir) - float(gider_toplam)),
        }
        return super().changelist_view(request, extra_context=extra_context)


# ============================================================
# GİDER
# ============================================================
@admin.register(Gider)
class GiderAdmin(ImportExportModelAdmin):
    list_display = ('baslik', 'kategori_goster', 'miktar_formatli', 'tarih', 'belge_btn')
    list_filter = ('kategori', 'tarih')
    search_fields = ('baslik', 'aciklama')
    date_hierarchy = 'tarih'
    list_per_page = 30
    change_list_template = 'admin/finance/gider_change_list.html'

    def kategori_goster(self, obj):
        return obj.get_kategori_display()
    kategori_goster.short_description = "Kategori"

    def miktar_formatli(self, obj):
        return format_html('<b style="color:#dc3545;">{}</b>', _para(obj.miktar))
    miktar_formatli.short_description = "Tutar"

    def belge_btn(self, obj):
        url = reverse('gider_makbuzu', args=[obj.id])
        return _yazdir_btn(url, "📄 Makbuz", "#dc3545")
    belge_btn.short_description = "Belge"

    def changelist_view(self, request, extra_context=None):
        """Dönem raporu linki ekle."""
        from datetime import date
        bugun = date.today()
        baslangic = bugun.replace(day=1).strftime('%Y-%m-%d')
        bitis = bugun.strftime('%Y-%m-%d')
        rapor_url = reverse('gider_raporu') + f'?baslangic={baslangic}&bitis={bitis}'

        extra_context = extra_context or {}
        extra_context['gider_raporu_url'] = rapor_url
        return super().changelist_view(request, extra_context=extra_context)


# ============================================================
# ADMIN BAŞLIKLARI
# ============================================================
admin.site.index_title = "GreenNova ERP - Yönetim Paneli"
admin.site.site_header = "GreenNova Tarım"
