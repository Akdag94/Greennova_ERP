# GreenNova ERP — Site Views
# Developer: Azat Akdag
# Build ID: 76a253b51f848f4345737a09a19cb86a599614c210c9f09494fd35ebcfbf1eae
# © 2026 GreenNova Tarim. All rights reserved.
# Contact: azat.akdag@greennova

# __sig__: 76a253b5 | build:2026 | dev:609191fb
"""
Ana sayfa (patron paneli) ve yardım bölümü.
Her şeyi tek bakışta göster — karmaşık değil, net ve sade.
"""

from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Sum, Count, Q
from django.shortcuts import render
from django.utils import timezone


# ============================================================
# YARDIMCI: Para formatı
# ============================================================
def _f(sayi):
    try:
        return "{:,.0f}".format(float(sayi or 0)).replace(",", ".")
    except Exception:
        return "0"


def _fk(sayi):
    """Bin'lik formatla, 2 ondalık."""
    try:
        return "{:,.2f}".format(float(sayi or 0)).replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "0,00"


# ============================================================
# ANA SAYFA — PATRON PANELİ
# ============================================================
def anasayfa(request):
    # Geç import (circular import önlemi)
    from inventory.models import Palet, Depo
    from finance.models import (
        Mustahsil, Musteri, Sevkiyat,
        CariHareket, MusteriHareket, Gider
    )

    bugun = date.today()
    bu_hafta_bas = bugun - timedelta(days=bugun.weekday())
    bu_ay_bas = bugun.replace(day=1)
    gecen_ay_bas = (bu_ay_bas - timedelta(days=1)).replace(day=1)
    gecen_ay_son = bu_ay_bas - timedelta(days=1)

    # ---- STOK ----
    stok_paletler = Palet.objects.filter(durum__in=['depoda', 'isleniyor'])
    toplam_stok_kg = stok_paletler.aggregate(t=Sum('miktar_kg'))['t'] or Decimal('0')
    toplam_stok_palet = stok_paletler.count()
    stok_maliyet = stok_paletler.aggregate(t=Sum('toplam_tutar'))['t'] or Decimal('0')

    # Ürün bazlı stok
    urun_stok = stok_paletler.values('urun_cinsi__ad').annotate(
        kg=Sum('miktar_kg'), palet=Count('id')
    ).order_by('-kg')[:6]

    # ---- SEVKİYAT ----
    aktif_tirlar = Sevkiyat.objects.filter(tamamlandi=False).select_related('musteri')
    tamamlanan_tirlar = Sevkiyat.objects.filter(tamamlandi=True)

    # Bu ayki satış
    bu_ay_satis = tamamlanan_tirlar.filter(
        cikis_tarihi__date__gte=bu_ay_bas
    ).aggregate(t=Sum('toplam_satis_tutari'))['t'] or Decimal('0')

    # Geçen ayki satış (karşılaştırma için)
    gecen_ay_satis = tamamlanan_tirlar.filter(
        cikis_tarihi__date__gte=gecen_ay_bas,
        cikis_tarihi__date__lte=gecen_ay_son
    ).aggregate(t=Sum('toplam_satis_tutari'))['t'] or Decimal('0')

    # Bu haftaki satış
    bu_hafta_satis = tamamlanan_tirlar.filter(
        cikis_tarihi__date__gte=bu_hafta_bas
    ).aggregate(t=Sum('toplam_satis_tutari'))['t'] or Decimal('0')

    # Toplam satış (tüm zamanlar)
    toplam_satis = tamamlanan_tirlar.aggregate(
        t=Sum('toplam_satis_tutari')
    )['t'] or Decimal('0')

    # ---- MÜŞTERİ ----
    toplam_musteri_alacak = Musteri.objects.aggregate(
        t=Sum('toplam_alacagimiz')
    )['t'] or Decimal('0')

    # Bekleyen (ödenmemiş) alacaklar
    bekleyen_alacak = MusteriHareket.objects.filter(
        odendi_mi=False, islem_tipi='satis'
    ).aggregate(t=Sum('miktar'))['t'] or Decimal('0')

    # En çok borçlu müşteriler
    en_cok_borc_musteri = Musteri.objects.filter(
        toplam_alacagimiz__gt=0
    ).order_by('-toplam_alacagimiz')[:5]

    # ---- MÜSTAHSİL ----
    toplam_mustahsil_borc = Mustahsil.objects.aggregate(
        t=Sum('toplam_borc')
    )['t'] or Decimal('0')

    # En çok borçlu olunan müstahsiller
    en_cok_borc_mustahsil = Mustahsil.objects.filter(
        toplam_borc__gt=0
    ).order_by('-toplam_borc')[:5]

    # ---- GİDER ----
    bu_ay_gider = Gider.objects.filter(
        tarih__gte=bu_ay_bas
    ).aggregate(t=Sum('miktar'))['t'] or Decimal('0')

    toplam_gider = Gider.objects.aggregate(t=Sum('miktar'))['t'] or Decimal('0')

    # ---- KÂR/ZARAR ----
    net_kar = float(toplam_satis) - float(toplam_gider)
    bu_ay_kar = float(bu_ay_satis) - float(bu_ay_gider)

    # ---- GRAFİK: Son 7 günlük sevkiyat ----
    grafik_gunler = []
    grafik_satis = []
    grafik_kg = []
    for i in range(6, -1, -1):
        gun = bugun - timedelta(days=i)
        gun_satis = tamamlanan_tirlar.filter(
            cikis_tarihi__date=gun
        ).aggregate(t=Sum('toplam_satis_tutari'))['t'] or 0
        gun_kg = Palet.objects.filter(
            sevkiyat__tamamlandi=True,
            sevkiyat__cikis_tarihi__date=gun
        ).aggregate(t=Sum('miktar_kg'))['t'] or 0

        gun_isim = {
            'Monday': 'Pzt', 'Tuesday': 'Sal', 'Wednesday': 'Çar',
            'Thursday': 'Per', 'Friday': 'Cum', 'Saturday': 'Cmt', 'Sunday': 'Paz'
        }.get(gun.strftime('%A'), gun.strftime('%d/%m'))

        grafik_gunler.append(gun_isim)
        grafik_satis.append(float(gun_satis))
        grafik_kg.append(float(gun_kg))

    # ---- DEPO DOLULUK ----
    depolar = Depo.objects.all()

    # ---- AKTIF TIRLARDAKİ PALET ----
    aktif_tir_detay = []
    for tir in aktif_tirlar[:5]:
        kg = tir.paletler.aggregate(t=Sum('miktar_kg'))['t'] or 0
        palet_adet = tir.paletler.count()
        aktif_tir_detay.append({
            'tir': tir,
            'kg': kg,
            'palet_adet': palet_adet,
        })

    context = {
        # Stok
        'toplam_stok_kg': _f(toplam_stok_kg),
        'toplam_stok_palet': toplam_stok_palet,
        'stok_maliyet': _fk(stok_maliyet),
        'urun_stok': urun_stok,

        # Sevkiyat
        'aktif_tir_sayisi': aktif_tirlar.count(),
        'aktif_tir_detay': aktif_tir_detay,

        # Satış
        'bu_hafta_satis': _fk(bu_hafta_satis),
        'bu_ay_satis': _fk(bu_ay_satis),
        'gecen_ay_satis': _fk(gecen_ay_satis),
        'toplam_satis': _fk(toplam_satis),
        'satis_degisim': round(
            ((float(bu_ay_satis) - float(gecen_ay_satis)) / max(float(gecen_ay_satis), 1)) * 100, 1
        ),

        # Müşteri/Alacak
        'toplam_musteri_alacak': _fk(toplam_musteri_alacak),
        'bekleyen_alacak': _fk(bekleyen_alacak),
        'en_cok_borc_musteri': en_cok_borc_musteri,
        'toplam_musteri': Musteri.objects.count(),

        # Müstahsil/Borç
        'toplam_mustahsil_borc': _fk(toplam_mustahsil_borc),
        'en_cok_borc_mustahsil': en_cok_borc_mustahsil,
        'toplam_mustahsil': Mustahsil.objects.count(),

        # Gider
        'bu_ay_gider': _fk(bu_ay_gider),
        'toplam_gider': _fk(toplam_gider),

        # Kâr
        'net_kar': _fk(net_kar),
        'bu_ay_kar': _fk(bu_ay_kar),
        'net_kar_pozitif': net_kar >= 0,
        'bu_ay_kar_pozitif': bu_ay_kar >= 0,

        # Grafik
        'grafik_gunler': grafik_gunler,
        'grafik_satis': grafik_satis,
        'grafik_kg': grafik_kg,

        # Depo
        'depolar': depolar,

        # Tarih
        'bugun': bugun,
    }

    return render(request, 'site/anasayfa.html', context)


# ============================================================
# YARDIM SAYFASI
# ============================================================
def yardim(request):
    """Sistem kullanım rehberi."""
    return render(request, 'site/yardim.html', {
        'baslik': 'Sistem Rehberi',
    })


# ============================================================
# DETAY SAYFALARI — Tıklanınca kim neden ne kadar
# ============================================================
def musteri_detay(request, musteri_id=None):
    from finance.models import Musteri, MusteriHareket
    from django.shortcuts import get_object_or_404

    # Liste modu — tüm müşterileri göster
    if musteri_id is None:
        musteriler = Musteri.objects.order_by('-toplam_alacagimiz')
        return render(request, 'site/detay/musteri_liste.html', {
            'musteriler': musteriler,
            'toplam_alacak': _fk(Musteri.objects.aggregate(t=__import__('django').db.models.Sum('toplam_alacagimiz'))['t'] or 0),
        })

    musteri = get_object_or_404(Musteri, id=musteri_id)
    hareketler = MusteriHareket.objects.filter(
        musteri=musteri
    ).select_related('sevkiyat').order_by('tarih', 'id')

    satirlar = []
    bakiye = Decimal('0')
    toplam_satis = Decimal('0')
    toplam_tahsilat = Decimal('0')

    for h in hareketler:
        if h.islem_tipi == 'satis':
            bakiye += h.miktar
            toplam_satis += h.miktar
        elif h.islem_tipi == 'tahsilat':
            bakiye -= h.miktar
            toplam_tahsilat += h.miktar
        satirlar.append({'hareket': h, 'bakiye': bakiye})

    return render(request, 'site/detay/musteri.html', {
        'musteri': musteri,
        'satirlar': satirlar,
        'bakiye': bakiye,
        'bakiye_goster': _fk(abs(bakiye)),
        'toplam_satis': _fk(toplam_satis),
        'toplam_tahsilat': _fk(toplam_tahsilat),
        'satis_sayisi': hareketler.filter(islem_tipi='satis').count(),
        'tahsilat_sayisi': hareketler.filter(islem_tipi='tahsilat').count(),
        'ekstre_url': f'/finance/yazdir/musteri-ekstre/{musteri.id}/',
    })


def mustahsil_detay(request, mustahsil_id=None):
    from finance.models import Mustahsil, CariHareket
    from django.shortcuts import get_object_or_404

    if mustahsil_id is None:
        mustahsiller = Mustahsil.objects.order_by('-toplam_borc')
        return render(request, 'site/detay/mustahsil_liste.html', {
            'mustahsiller': mustahsiller,
            'toplam_borc': _fk(Mustahsil.objects.aggregate(t=__import__('django').db.models.Sum('toplam_borc'))['t'] or 0),
        })

    mustahsil = get_object_or_404(Mustahsil, id=mustahsil_id)
    hareketler = CariHareket.objects.filter(
        mustahsil=mustahsil
    ).order_by('tarih', 'id')

    satirlar = []
    bakiye = Decimal('0')
    toplam_alim = Decimal('0')
    toplam_odeme = Decimal('0')

    for h in hareketler:
        if h.islem_tipi == 'alimgiris':
            bakiye += h.miktar
            toplam_alim += h.miktar
        elif h.islem_tipi in ('odeme', 'fason_hizmet'):
            bakiye -= h.miktar
            toplam_odeme += h.miktar
        satirlar.append({'hareket': h, 'bakiye': bakiye})

    return render(request, 'site/detay/mustahsil.html', {
        'mustahsil': mustahsil,
        'satirlar': satirlar,
        'bakiye': bakiye,
        'bakiye_goster': _fk(abs(bakiye)),
        'toplam_alim': _fk(toplam_alim),
        'toplam_odeme': _fk(toplam_odeme),
        'alim_sayisi': hareketler.filter(islem_tipi='alimgiris').count(),
        'odeme_sayisi': hareketler.filter(islem_tipi='odeme').count(),
        'ekstre_url': f'/finance/yazdir/mustahsil-ekstre/{mustahsil.id}/',
    })


def gider_detay(request):
    from finance.models import Gider
    from datetime import date
    from django.db.models import Sum, Count

    aktif_kat = request.GET.get('kat', '')
    bugun = date.today()
    bu_ay_bas = bugun.replace(day=1)
    bu_yil_bas = bugun.replace(month=1, day=1)

    giderler_qs = Gider.objects.all().order_by('-tarih')
    if aktif_kat:
        giderler_qs = giderler_qs.filter(kategori=aktif_kat)

    bu_ay = Gider.objects.filter(tarih__gte=bu_ay_bas)
    bu_yil = Gider.objects.filter(tarih__gte=bu_yil_bas)

    from datetime import date as d
    rapor_url = (
        f'/finance/yazdir/gider-raporu/'
        f'?baslangic={bu_ay_bas.strftime("%Y-%m-%d")}&bitis={bugun.strftime("%Y-%m-%d")}'
    )

    return render(request, 'site/detay/giderler.html', {
        'giderler': giderler_qs[:100],
        'toplam': _fk(Gider.objects.aggregate(t=Sum('miktar'))['t'] or 0),
        'toplam_sayi': Gider.objects.count(),
        'bu_ay_toplam': _fk(bu_ay.aggregate(t=Sum('miktar'))['t'] or 0),
        'bu_ay_sayi': bu_ay.count(),
        'bu_yil_toplam': _fk(bu_yil.aggregate(t=Sum('miktar'))['t'] or 0),
        'aktif_kat': aktif_kat,
        'kategoriler': Gider.KATEGORI_SECENEKLERI,
        'rapor_url': rapor_url,
    })
