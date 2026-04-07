from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

# Views Importları
from finance.views import makbuz_pdf_indir
from inventory import views as inv_views

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # --- INVENTORY (DEPO) YOLLARI ---
    # QR Tarayıcı Ekranı (Tır Yükleme)
    path('inventory/scan/', inv_views.qr_scanner_view, name='qr_scanner'),
    
    # QR API'leri
    path('inventory/api/scan-palet/<int:palet_id>/', inv_views.scan_palet_api, name='scan_palet_api'),
    path('inventory/api/yukle/', inv_views.paleti_tira_yukle_api, name='paleti_tira_yukle_api'),
    
    # YENİ: Mobil Saha Hızlı Giriş (Fotoğraflı Mal Kabul)
    path('inventory/mobil-giris/', inv_views.mobil_hizli_giris, name='mobil_hizli_giris'),

    # --- DİĞER YOLLAR ---
    # Yoklama API yolu (Cihazlar için)
    path('api/yoklama/', include('attendance.urls')), 
    
    # Müstahsil Makbuz PDF yolu (Yazdır butonu için)
    path('finance/makbuz/<int:hareket_id>/', makbuz_pdf_indir, name='makbuz_pdf'),
]

# QR Kod ve Medya dosyaları (Fotoğraflar vb.) için servis yolu
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)