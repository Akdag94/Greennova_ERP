# __sig__: 76a253b5 | build:2026 | dev:c4a8f3b2
from django.contrib import admin
from django.db.models import Sum
from django.utils.html import format_html
from django.urls import reverse
from import_export.admin import ImportExportModelAdmin
from .models import Gider, Mustahsil, CariHareket, Sevkiyat, Musteri, MusteriHareket
from inventory.models import Palet  # PaletInline için gerekli
from decimal import Decimal


def _para(sayi):
    try:
        return "{:,.2f} ₺".format(float(sayi or 0)).replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "0,00 ₺"


def _renk_para(sayi, pozitif_renk="#1a6b3c", negatif_renk="#c0392b", sifir_renk="#888"):
    """
    Para değerini renkli göster.
    pozitif_renk: yeşil (iyi durum)
    negatif_renk: kırmızı (olumsuz durum)
    """
    try:
        val = float(sayi or 0)
    except Exception:
        val = 0
    if val > 0:
        renk = pozitif_renk
        isaret = "+"
    elif val < 0:
        renk = negatif_renk
        isaret = ""
    else:
        renk = sifir_renk
        isaret = ""
    return format_html(
        '<b style="color:{};font-size:13px;">{}{}</b>',
        renk, isaret, _para(val)
    )


def _btn(url, etiket, renk="#28a745", yeni_sekme=True):
    """Tek düğme — taşmaz, satır içi blok."""
    hedef = 'target="_blank"' if yeni_sekme else ''
    return format_html(
        '<a href="{}" {} style="display:inline-block;background:{};color:#fff;'
        'padding:3px 8px;border-radius:4px;text-decoration:none;'
        'font-size:11px;font-weight:600;white-space:nowrap;margin:1px;">{}</a>',
        url, hedef, renk, etiket
    )


def _btn_group(*butonlar):
    """Birden fazla butonu yan yana, taşmadan göster."""
    html = '<div style="display:flex;flex-wrap:wrap;gap:3px;align-items:center;">'
    for b in butonlar:
        html += str(b)
    html += '</div>'
    return format_html(html)


# ============================================================
# MÜŞTERİ
# ============================================================
@admin.register(Musteri)
class MusteriAdmin(ImportExportModelAdmin):
    list_display = ('unvan', 'bolge', 'telefon', 'alacak_goster', 'belgeler')
    search_fields = ('unvan', 'bolge', 'telefon')
    list_per_page = 30

    def alacak_goster(self, obj):
        b = obj.toplam_alacagimiz
        # Alacak: pozitif → bize borçlu (mavi/koyu)
        # Negatif → biz borçluyuz (kırmızı)
        if b > 0:
            return format_html(
                '<b style="color:#1a3a6e;font-size:13px;">📥 {}</b>',
                _para(b)
            )
        elif b < 0:
            return format_html(
                '<b style="color:#c0392b;font-size:13px;">📤 {}</b>',
                _para(abs(b))
            )
        return format_html('<span style="color:#888;">0,00 ₺</span>')
    alacak_goster.short_description = "📥 Alacağımız"

    def belgeler(self, obj):
        ekstre = _btn(reverse('musteri_ekstre', args=[obj.id]), "📋 Ekstre", "#0056b3")
        detay = _btn(f'/site/detay/musteri/{obj.id}/', "🔍 Detay", "#6c757d")
        return _btn_group(ekstre, detay)
    belgeler.short_description = "İşlemler"


# ============================================================
# MÜŞTERİ HAREKETLERİ
# ============================================================
@admin.register(MusteriHareket)
class MusteriHareketAdmin(ImportExportModelAdmin):
    list_display = ('musteri', 'islem_tipi_goster', 'miktar_goster', 'tarih', 'durum_goster', 'odendi_mi', 'belge_btn')
    list_filter = ('islem_tipi', 'odendi_mi', 'tarih')
    list_editable = ('odendi_mi',)
    search_fields = ('musteri__unvan', 'aciklama')
    autocomplete_fields = ['musteri', 'sevkiyat']
    date_hierarchy = 'tarih'
    list_per_page = 30

    def islem_tipi_goster(self, obj):
        if obj.islem_tipi == 'satis':
            return format_html('<span style="background:#dce8ff;color:#0056b3;padding:2px 8px;border-radius:10px;font-size:11px;font-weight:700;">📤 SATIŞ</span>')
        return format_html('<span style="background:#d4edda;color:#155724;padding:2px 8px;border-radius:10px;font-size:11px;font-weight:700;">📥 TAHSİLAT</span>')
    islem_tipi_goster.short_description = "İşlem"

    def miktar_goster(self, obj):
        if obj.islem_tipi == 'satis':
            return format_html('<b style="color:#0056b3;">{}</b>', _para(obj.miktar))
        return format_html('<b style="color:#155724;">+{}</b>', _para(obj.miktar))
    miktar_goster.short_description = "Tutar"

    def durum_goster(self, obj):
        if obj.odendi_mi:
            return format_html('<span style="color:#155724;font-weight:700;">✅ Kapandı</span>')
        return format_html('<span style="color:#856404;font-weight:700;">⏳ Bekliyor</span>')
    durum_goster.short_description = "Durum"

    def belge_btn(self, obj):
        if obj.islem_tipi == 'tahsilat':
            return _btn(reverse('musteri_tahsilat_makbuzu', args=[obj.id]), "📄 Makbuz")
        return format_html('<span style="color:#ccc;">—</span>')
    belge_btn.short_description = "Belge"


# ============================================================
# MÜSTAHSİL
# ============================================================
@admin.register(Mustahsil)
class MustahsilAdmin(ImportExportModelAdmin):
    list_display = ('ad_soyad', 'bolge', 'telefon', 'borc_goster', 'belgeler')
    search_fields = ('ad_soyad', 'bolge', 'tc_no')
    list_per_page = 30

    def borc_goster(self, obj):
        b = obj.toplam_borc
        # Borç: pozitif → biz borçluyuz (kırmızı/turuncu)
        if b > 0:
            return format_html(
                '<b style="color:#c0392b;font-size:13px;">🔴 {}</b>',
                _para(b)
            )
        elif b < 0:
            return format_html(
                '<b style="color:#155724;font-size:13px;">🟢 {}</b>',
                _para(abs(b))
            )
        return format_html('<span style="color:#888;">✅ Sıfır</span>')
    borc_goster.short_description = "🔴 Borcumuz"

    def belgeler(self, obj):
        ekstre = _btn(reverse('mustahsil_ekstre', args=[obj.id]), "📋 Ekstre", "#0056b3")
        detay = _btn(f'/site/detay/mustahsil/{obj.id}/', "🔍 Detay", "#6c757d")
        return _btn_group(ekstre, detay)
    belgeler.short_description = "İşlemler"


# ============================================================
# CARİ HAREKETLER
# ============================================================
@admin.register(CariHareket)
class CariHareketAdmin(ImportExportModelAdmin):
    list_display = ('mustahsil', 'islem_goster', 'miktar_goster', 'tarih', 'makbuz_btn')
    list_filter = ('islem_tipi', 'tarih')
    search_fields = ('mustahsil__ad_soyad', 'aciklama')
    autocomplete_fields = ['mustahsil']
    date_hierarchy = 'tarih'
    list_per_page = 30

    def islem_goster(self, obj):
        renkler = {
            'alimgiris': ('#fff3cd', '#856404', '📦 ALIM'),
            'odeme': ('#d4edda', '#155724', '💸 ÖDEME'),
            'fason_hizmet': ('#d1ecf1', '#0c5460', '🔧 FASON'),
        }
        bg, fg, etiket = renkler.get(obj.islem_tipi, ('#f8f9fa', '#333', '?'))
        return format_html(
            '<span style="background:{};color:{};padding:2px 8px;border-radius:10px;font-size:11px;font-weight:700;">{}</span>',
            bg, fg, etiket
        )
    islem_goster.short_description = "İşlem"

    def miktar_goster(self, obj):
        if obj.islem_tipi == 'alimgiris':
            return format_html('<b style="color:#c0392b;">{}</b>', _para(obj.miktar))
        return format_html('<b style="color:#155724;">+{}</b>', _para(obj.miktar))
    miktar_goster.short_description = "Tutar"

    def makbuz_btn(self, obj):
        if obj.islem_tipi == 'alimgiris':
            return _btn(reverse('mustahsil_makbuz', args=[obj.id]), "📄 Alım Makbuzu")
        elif obj.islem_tipi == 'odeme':
            return _btn(reverse('mustahsil_odeme_makbuzu', args=[obj.id]), "📄 Ödeme Makbuzu", "#0056b3")
        return format_html('<span style="color:#ccc;">—</span>')
    makbuz_btn.short_description = "Belge"


# ============================================================
# SEVKİYAT
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
    list_display = (
        'plaka', 'musteri_kisa', 'tonaj_goster',
        'satis_goster', 'kar_goster', 'tamamlandi', 'belgeler'
    )
    list_filter = ('tamamlandi', 'cikis_tarihi', 'musteri')
    search_fields = ('plaka', 'sofor_ad', 'musteri__unvan')
    inlines = [PaletInline]
    autocomplete_fields = ['musteri']
    list_per_page = 25
    date_hierarchy = 'cikis_tarihi'

    def musteri_kisa(self, obj):
        return obj.musteri.unvan if obj.musteri else '—'
    musteri_kisa.short_description = "Müşteri"

    def tonaj_goster(self, obj):
        kg = obj.paletler.aggregate(t=Sum('miktar_kg'))['t'] or 0
        adet = obj.paletler.aggregate(t=Sum('toplam_palet_adedi'))['t'] or 0
        return format_html('<span style="font-size:12px;"><b>{} KG</b><br><span style="color:#888;">{} palet</span></span>', int(kg), adet)
    tonaj_goster.short_description = "Yük"

    def satis_goster(self, obj):
        return format_html('<b style="color:#0056b3;">{}</b>', _para(obj.toplam_satis_tutari or 0))
    satis_goster.short_description = "Satış"

    def kar_goster(self, obj):
        try:
            kar = obj.kar_zarar_durumu() or 0
            if kar >= 0:
                return format_html('<b style="color:#155724;">▲ {}</b>', _para(kar))
            return format_html('<b style="color:#c0392b;">▼ {}</b>', _para(abs(kar)))
        except Exception:
            return format_html('<span style="color:#ccc;">—</span>')
    kar_goster.short_description = "Kâr/Zarar"

    def belgeler(self, obj):
        fatura = _btn(reverse('musteri_fatura', args=[obj.id]), "🧾 Fatura")
        irsaliye = _btn(reverse('sevkiyat_irsaliye', args=[obj.id]), "📦 İrsaliye", "#6f42c1")
        return _btn_group(fatura, irsaliye)
    belgeler.short_description = "Belgeler"

    def changelist_view(self, request, extra_context=None):
        gelir = Sevkiyat.objects.aggregate(t=Sum('toplam_satis_tutari'))['t'] or 0
        gider_t = Gider.objects.aggregate(t=Sum('miktar'))['t'] or 0
        borc = Mustahsil.objects.aggregate(t=Sum('toplam_borc'))['t'] or 0
        alacak = Musteri.objects.aggregate(t=Sum('toplam_alacagimiz'))['t'] or 0
        bekleyen = MusteriHareket.objects.filter(
            odendi_mi=False, islem_tipi='satis'
        ).aggregate(t=Sum('miktar'))['t'] or 0
        extra_context = extra_context or {}
        extra_context['ozet_veriler'] = {
            'gelir': _para(gelir),
            'gider': _para(gider_t),
            'borc': _para(borc),
            'alacak': _para(alacak),
            'bekleyen': _para(bekleyen),
            'net': _para(float(gelir) - float(gider_t)),
        }
        return super().changelist_view(request, extra_context=extra_context)


# ============================================================
# GİDER
# ============================================================
@admin.register(Gider)
class GiderAdmin(ImportExportModelAdmin):
    list_display = ('baslik', 'kategori_goster', 'miktar_goster', 'tarih', 'belge_btn')
    list_filter = ('kategori', 'tarih')
    search_fields = ('baslik', 'aciklama')
    date_hierarchy = 'tarih'
    list_per_page = 30
    change_list_template = 'admin/finance/gider_change_list.html'

    def kategori_goster(self, obj):
        return obj.get_kategori_display()
    kategori_goster.short_description = "Kategori"

    def miktar_goster(self, obj):
        return format_html('<b style="color:#c0392b;">— {}</b>', _para(obj.miktar))
    miktar_goster.short_description = "Tutar"

    def belge_btn(self, obj):
        return _btn(reverse('gider_makbuzu', args=[obj.id]), "📄 Makbuz", "#c0392b")
    belge_btn.short_description = "Belge"

    def changelist_view(self, request, extra_context=None):
        from datetime import date
        bugun = date.today()
        baslangic = bugun.replace(day=1).strftime('%Y-%m-%d')
        bitis = bugun.strftime('%Y-%m-%d')
        rapor_url = reverse('gider_raporu') + f'?baslangic={baslangic}&bitis={bitis}'
        extra_context = extra_context or {}
        extra_context['gider_raporu_url'] = rapor_url
        return super().changelist_view(request, extra_context=extra_context)


admin.site.index_title = "GreenNova ERP - Yönetim"
admin.site.site_header = "GreenNova Tarım"
admin.site.site_title = "GreenNova ERP"