# __sig__: 76a253b5 | build:2026 | dev:609191fb
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from finance.views import makbuz_pdf_indir
from finance.print_views import (
    mustahsil_makbuz, mustahsil_odeme_makbuzu, mustahsil_ekstre,
    musteri_fatura, musteri_ekstre, musteri_tahsilat_makbuzu,
    sevkiyat_irsaliye, gider_makbuzu, gider_raporu,
)
from inventory import views as inv_views
from greennova_core.site_views import anasayfa, yardim

urlpatterns = [
    path('admin/', admin.site.urls),

    # Ana sayfa ve rehber
    path('', anasayfa, name='anasayfa'),
    path('site/yardim/', yardim, name='yardim'),

    # ====================================================
    # INVENTORY — Depo ve QR
    # ====================================================
    path('inventory/scan/', inv_views.qr_scanner_view, name='qr_scanner'),
    path('inventory/mobil-giris/', inv_views.mobil_hizli_giris, name='mobil_hizli_giris'),
    path('inventory/api/scan-palet/<int:palet_id>/', inv_views.scan_palet_api, name='scan_palet_api'),
    path('inventory/api/yukle/', inv_views.paleti_tira_yukle_api, name='paleti_tira_yukle_api'),
    path('inventory/api/offline-sync/', inv_views.offline_sync_api, name='offline_sync_api'),
    path('inventory/api/aktif-sevkiyatlar/', inv_views.aktif_sevkiyatlar_api, name='aktif_sevkiyatlar_api'),

    # ====================================================
    # ATTENDANCE — RFID Yoklama API
    # ====================================================
    path('api/yoklama/', include('attendance.urls')),

    # ====================================================
    # FINANCE — PDF / Yazdırma (eski + yeni)
    # ====================================================
    # Geriye uyumluluk
    path('finance/makbuz/<int:hareket_id>/', makbuz_pdf_indir, name='makbuz_pdf'),

    # Müstahsil belgeleri
    path('finance/yazdir/mustahsil-makbuz/<int:hareket_id>/',
         mustahsil_makbuz, name='mustahsil_makbuz'),
    path('finance/yazdir/mustahsil-odeme/<int:hareket_id>/',
         mustahsil_odeme_makbuzu, name='mustahsil_odeme_makbuzu'),
    path('finance/yazdir/mustahsil-ekstre/<int:mustahsil_id>/',
         mustahsil_ekstre, name='mustahsil_ekstre'),

    # Müşteri belgeleri
    path('finance/yazdir/musteri-fatura/<int:sevkiyat_id>/',
         musteri_fatura, name='musteri_fatura'),
    path('finance/yazdir/musteri-ekstre/<int:musteri_id>/',
         musteri_ekstre, name='musteri_ekstre'),
    path('finance/yazdir/musteri-tahsilat/<int:hareket_id>/',
         musteri_tahsilat_makbuzu, name='musteri_tahsilat_makbuzu'),

    # Sevkiyat
    path('finance/yazdir/sevkiyat/<int:sevkiyat_id>/',
         sevkiyat_irsaliye, name='sevkiyat_irsaliye'),

    # Gider
    path('finance/yazdir/gider/<int:gider_id>/',
         gider_makbuzu, name='gider_makbuzu'),
    path('finance/yazdir/gider-raporu/',
         gider_raporu, name='gider_raporu'),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
