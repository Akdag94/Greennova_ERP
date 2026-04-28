# __sig__: 76a253b5 | build:2026 | dev:609191fb
"""
GreenNova ERP — Evrensel PDF Yazdırma Sistemi
==============================================
Tek dosyada tüm belgeler:
  - Müstahsil Alım Makbuzu  (/finance/yazdir/mustahsil-makbuz/<id>/)
  - Müstahsil Cari Ekstre   (/finance/yazdir/mustahsil-ekstre/<id>/)
  - Müstahsil Ödeme Makbuzu (/finance/yazdir/mustahsil-odeme/<id>/)
  - Müşteri Satış Faturası  (/finance/yazdir/musteri-fatura/<id>/)
  - Müşteri Cari Ekstre     (/finance/yazdir/musteri-ekstre/<id>/)
  - Müşteri Tahsilat Makb.  (/finance/yazdir/musteri-tahsilat/<id>/)
  - Sevkiyat İrsaliyesi     (/finance/yazdir/sevkiyat/<id>/)
  - Gider Makbuzu           (/finance/yazdir/gider/<id>/)
  - Gider Dönemi Raporu     (/finance/yazdir/gider-rapor/)

Tüm belgeler A4, logolu, TC Vergi/TC bilgili, resmi görünümlü.
xhtml2pdf ile oluşturuluyor.
"""

import base64
import os
from datetime import date, timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Sum, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.utils import timezone

from xhtml2pdf import pisa

from .models import (
    CariHareket, Gider, Mustahsil, Musteri,
    MusteriHareket, Sevkiyat
)


# ============================================================
# YARDIMCI — Logo base64
# ============================================================
def _logo_base64():
    """Logo'yu PDF'e gömmek için base64 string döner."""
    logo_path = os.path.join(settings.BASE_DIR, 'static', 'logo_header.png')
    if os.path.exists(logo_path):
        with open(logo_path, 'rb') as f:
            return 'data:image/png;base64,' + base64.b64encode(f.read()).decode()
    return ''


def _tr_to_ascii(metin):
    """
    Türkçe karakterleri ASCII karşılığına çevirir.
    PDF render'da font sorunu yaşamamak için kullanılır.
    ı→i, İ→I, ğ→g, Ğ→G, ü→u, Ü→U, ş→s, Ş→S, ö→o, Ö→O, ç→c, Ç→C
    """
    if not metin:
        return metin
    tablo = str.maketrans(
        'ıİğĞüÜşŞöÖçÇ',
        'iIgGuUssoOcC'
    )
    return str(metin).translate(tablo)


def _para_format(sayi):
    """Sayıyı Türk para formatında döner: 1.234,56 ₺"""
    try:
        return "{:,.2f} ₺".format(sayi).replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "0,00 ₺"


def _pdf_response(html, dosya_adi):
    """HTML'i PDF'e çevirip HttpResponse döner."""
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'filename="{dosya_adi}.pdf"'
    pisa_status = pisa.CreatePDF(html, dest=response, encoding='utf-8')
    if pisa_status.err:
        return HttpResponse(
            f'<h1>PDF Hatası</h1><pre>{html[:2000]}</pre>',
            content_type='text/html'
        )
    return response


def _render_pdf(template_name, context, dosya_adi):
    """Template'i render edip PDF döner. Türkçe karakterler otomatik ASCII'ye çevrilir."""
    context['logo_base64'] = _logo_base64()
    context['bugun'] = date.today()
    context['COMPANY_NAME'] = _tr_to_ascii(getattr(settings, 'COMPANY_NAME', 'GreenNova Tarim'))
    context['COMPANY_ADDRESS'] = _tr_to_ascii(getattr(settings, 'COMPANY_ADDRESS', 'Bursa / Turkiye'))
    context['COMPANY_PHONE'] = getattr(settings, 'COMPANY_PHONE', '')
    context['COMPANY_VERGI_NO'] = getattr(settings, 'COMPANY_VERGI_NO', '')
    context['COMPANY_VERGI_DAIRESI'] = _tr_to_ascii(getattr(settings, 'COMPANY_VERGI_DAIRESI', ''))
    html = render_to_string(template_name, context)
    # HTML render edildikten sonra kalan Türkçe karakterleri temizle
    html = html.translate(str.maketrans('ıİğĞüÜşŞöÖçÇ', 'iIgGuUssoOcC'))
    return _pdf_response(html, _tr_to_ascii(dosya_adi))


# ============================================================
# 1) MÜSTAHSİL ALIM MAKBUZU — Tek CariHareket (alimgiris)
# ============================================================
@staff_member_required
def mustahsil_makbuz(request, hareket_id):
    hareket = get_object_or_404(CariHareket, id=hareket_id, islem_tipi='alimgiris')
    mustahsil = hareket.mustahsil
    return _render_pdf(
        'finance/pdf/mustahsil_makbuz.html',
        {
            'hareket': hareket,
            'mustahsil': mustahsil,
            'belge_no': f'MAK-{hareket.id:05d}',
            'baslik': 'MUSTAHSIL ALIM MAKBUZU',
        },
        f'makbuz-{hareket.id}'
    )


# ============================================================
# 2) MÜSTAHSİL ÖDEMESİ MAKBUZU — Ödeme cari hareketi
# ============================================================
@staff_member_required
def mustahsil_odeme_makbuzu(request, hareket_id):
    hareket = get_object_or_404(CariHareket, id=hareket_id, islem_tipi='odeme')
    mustahsil = hareket.mustahsil
    return _render_pdf(
        'finance/pdf/mustahsil_makbuz.html',
        {
            'hareket': hareket,
            'mustahsil': mustahsil,
            'belge_no': f'ODE-{hareket.id:05d}',
            'baslik': 'MUSTAHSIL ÖDEME MAKBUZU',
        },
        f'odeme-makbuz-{hareket.id}'
    )


# ============================================================
# 3) MÜSTAHSİL CARİ EKSTRE
# ============================================================
@staff_member_required
def mustahsil_ekstre(request, mustahsil_id):
    mustahsil = get_object_or_404(Mustahsil, id=mustahsil_id)
    hareketler = CariHareket.objects.filter(
        mustahsil=mustahsil
    ).order_by('tarih', 'id')

    # Kümülatif bakiye hesapla
    satirlar = []
    bakiye = Decimal('0')
    for h in hareketler:
        if h.islem_tipi == 'alimgiris':
            bakiye += h.miktar
        elif h.islem_tipi in ('odeme', 'fason_hizmet'):
            bakiye -= h.miktar
        satirlar.append({
            'hareket': h,
            'bakiye': bakiye,
        })

    return _render_pdf(
        'finance/pdf/cari_ekstre.html',
        {
            'baslik': 'MÜSTAHSİL CARİ EKSTRESİ',
            'cari_unvan': mustahsil.ad_soyad,
            'cari_detay': f'{mustahsil.bolge} | Tel: {mustahsil.telefon or "-"} | TC: {mustahsil.tc_no or "-"}',
            'satirlar': satirlar,
            'son_bakiye': bakiye,
            'son_bakiye_aciklama': 'Borcumuz' if bakiye > 0 else 'Alacağımız',
        },
        f'mustahsil-ekstre-{mustahsil.id}'
    )


# ============================================================
# 4) MÜŞTERİ SATIŞ FATURASI / İRSALİYESİ — Sevkiyat bazlı
# ============================================================
@staff_member_required
def musteri_fatura(request, sevkiyat_id):
    sevkiyat = get_object_or_404(Sevkiyat, id=sevkiyat_id)
    paletler = sevkiyat.paletler.select_related('urun_cinsi').all()

    return _render_pdf(
        'finance/pdf/musteri_fatura.html',
        {
            'sevkiyat': sevkiyat,
            'musteri': sevkiyat.musteri,
            'paletler': paletler,
            'belge_no': f'SEV-{sevkiyat.id:05d}',
            'toplam_kg': paletler.aggregate(t=Sum('miktar_kg'))['t'] or Decimal('0'),
            'toplam_tutar': sevkiyat.toplam_satis_tutari,
        },
        f'fatura-{sevkiyat.id}'
    )


# ============================================================
# 5) MÜŞTERİ CARİ EKSTRE
# ============================================================
@staff_member_required
def musteri_ekstre(request, musteri_id):
    musteri = get_object_or_404(Musteri, id=musteri_id)
    hareketler = MusteriHareket.objects.filter(
        musteri=musteri
    ).order_by('tarih', 'id')

    satirlar = []
    bakiye = Decimal('0')
    for h in hareketler:
        if h.islem_tipi == 'satis':
            bakiye += h.miktar
        elif h.islem_tipi == 'tahsilat':
            bakiye -= h.miktar
        satirlar.append({
            'hareket': h,
            'bakiye': bakiye,
        })

    return _render_pdf(
        'finance/pdf/cari_ekstre.html',
        {
            'baslik': 'MÜŞTERİ CARİ EKSTRESİ',
            'cari_unvan': musteri.unvan,
            'cari_detay': f'{musteri.bolge or ""} | Tel: {musteri.telefon or "-"}',
            'satirlar': satirlar,
            'son_bakiye': bakiye,
            'son_bakiye_aciklama': 'Alacağımız' if bakiye > 0 else 'Borcumuz',
        },
        f'musteri-ekstre-{musteri.id}'
    )


# ============================================================
# 6) MÜŞTERİ TAHSİLAT MAKBUZU
# ============================================================
@staff_member_required
def musteri_tahsilat_makbuzu(request, hareket_id):
    hareket = get_object_or_404(MusteriHareket, id=hareket_id, islem_tipi='tahsilat')
    return _render_pdf(
        'finance/pdf/musteri_tahsilat.html',
        {
            'hareket': hareket,
            'musteri': hareket.musteri,
            'belge_no': f'TAH-{hareket.id:05d}',
        },
        f'tahsilat-{hareket.id}'
    )


# ============================================================
# 7) GİDER MAKBUZU — Tek gider
# ============================================================
@staff_member_required
def gider_makbuzu(request, gider_id):
    gider = get_object_or_404(Gider, id=gider_id)
    return _render_pdf(
        'finance/pdf/gider_makbuz.html',
        {
            'gider': gider,
            'belge_no': f'GID-{gider.id:05d}',
        },
        f'gider-{gider.id}'
    )


# ============================================================
# 8) GİDER DÖNEM RAPORU — Tarih aralığı ile
# ============================================================
@staff_member_required
def gider_raporu(request):
    baslangic_str = request.GET.get('baslangic', '')
    bitis_str = request.GET.get('bitis', '')

    try:
        from datetime import datetime
        baslangic = datetime.strptime(baslangic_str, '%Y-%m-%d').date()
        bitis = datetime.strptime(bitis_str, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        bugun = date.today()
        baslangic = bugun.replace(day=1)
        bitis = bugun

    giderler = Gider.objects.filter(
        tarih__gte=baslangic,
        tarih__lte=bitis
    ).order_by('tarih')

    toplam = giderler.aggregate(t=Sum('miktar'))['t'] or Decimal('0')

    # Kategoriye göre özet
    kategori_ozet = giderler.values('kategori').annotate(
        toplam=Sum('miktar')
    ).order_by('-toplam')

    return _render_pdf(
        'finance/pdf/gider_raporu.html',
        {
            'giderler': giderler,
            'toplam': toplam,
            'kategori_ozet': kategori_ozet,
            'baslangic': baslangic,
            'bitis': bitis,
        },
        f'gider-raporu-{baslangic}-{bitis}'
    )


# ============================================================
# 9) SEVKİYAT İRSALİYESİ (WAYBILL) — Taşıma için
# ============================================================
@staff_member_required
def sevkiyat_irsaliye(request, sevkiyat_id):
    """musteri_fatura'dan ayrı olarak sürücüye verilecek kopyaları için."""
    sevkiyat = get_object_or_404(Sevkiyat, id=sevkiyat_id)
    paletler = sevkiyat.paletler.select_related('urun_cinsi', 'mustahsil').all()
    return _render_pdf(
        'finance/pdf/sevkiyat_irsaliye.html',
        {
            'sevkiyat': sevkiyat,
            'paletler': paletler,
            'belge_no': f'IRS-{sevkiyat.id:05d}',
            'toplam_kg': paletler.aggregate(t=Sum('miktar_kg'))['t'] or Decimal('0'),
            'toplam_palet': paletler.aggregate(t=Sum('toplam_palet_adedi'))['t'] or 0,
        },
        f'irsaliye-{sevkiyat.id}'
    )
