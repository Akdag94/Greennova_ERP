from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from .models import Palet, UrunKategorisi, Depo
from finance.models import Sevkiyat, Mustahsil
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages

# 1. QR Tarama Ekranı (Tır Yükleme İçin)
def qr_scanner_view(request):
    return render(request, 'inventory/qr_scanner.html')

# 2. QR OKUTULUNCA: Palet Bilgisi ve Tır Listesini Getirir
def scan_palet_api(request, palet_id):
    try:
        try:
            palet = Palet.objects.get(id=palet_id)
        except (Palet.DoesNotExist, ValueError):
            return JsonResponse({
                'status': 'error', 
                'message': f'Geçersiz Kod: {palet_id} ID numaralı palet bulunamadı!'
            }, status=200)
        
        if palet.durum == 'yuklendi' or palet.durum == 'cikti':
            tir_plaka = palet.sevkiyat.plaka if palet.sevkiyat else "Bilinmiyor"
            status_text = "teslim edilmiş" if palet.durum == 'cikti' else "yüklenmiş"
            return JsonResponse({
                'status': 'warning',
                'message': f'Bu palet (#{palet.palet_no}) zaten {status_text} ({tir_plaka})!',
            })

        # HATA DÜZELTİLDİ: varis_yeri -> gidecegi_yer yapıldı
        aktif_tirlar = Sevkiyat.objects.filter(tamamlandi=False).values('id', 'plaka', 'gidecegi_yer')
        
        if not aktif_tirlar.exists():
            return JsonResponse({
                'status': 'error',
                'message': 'Sistemde yükleme yapılabilecek aktif bir tır (Sevkiyat) bulunamadı!'
            })

        # GÜNCELLEME: 'palet_adedi' verisi JSON'a eklendi
        return JsonResponse({
            'status': 'success',
            'palet_id': palet.id,
            'palet_no': palet.palet_no,
            'kg': str(palet.miktar_kg or 0),       # Paketlenen Net KG
            'brut_kg': str(palet.brut_miktar_kg),  # Kantar KG
            'fire': str(palet.fire_miktar_kg),     # Fire KG
            'palet_adedi': palet.toplam_palet_adedi, # ARADIĞIN VERİ BURADA
            'urun': palet.urun_cinsi.ad if palet.urun_cinsi else "Belirtilmemiş",
            'tirlar': list(aktif_tirlar)
        })

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'Sistem Hatası: {str(e)}'}, status=200)

# 3. TIR SEÇİLİNCE: Paleti seçilen tıra bağlar
@csrf_exempt
def paleti_tira_yukle_api(request):
    if request.method == "POST":
        palet_id = request.POST.get('palet_id')
        sevkiyat_id = request.POST.get('sevkiyat_id')
        
        try:
            palet = Palet.objects.get(id=palet_id)
            sevkiyat = Sevkiyat.objects.get(id=sevkiyat_id)
            
            palet.sevkiyat = sevkiyat
            palet.durum = 'yuklendi'
            palet.save()
            
            return JsonResponse({
                'status': 'success',
                'message': f'✅ {palet.palet_no} No\'lu palet {sevkiyat.plaka} tırına başarıyla eklendi!'
            })
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f"Yükleme Başarısız: {str(e)}"}, status=200)
            
    return JsonResponse({'status': 'error', 'message': 'Geçersiz istek metodu.'}, status=405)

# --- MOBİL SAHA HIZLI GİRİŞ ---
def mobil_hizli_giris(request):
    """
    Sahada telefonla fotoğraf çekip hızlıca palet oluşturma ekranı.
    """
    if request.method == "POST":
        try:
            urun_id = request.POST.get('urun_id')
            mustahsil_id = request.POST.get('mustahsil_id')
            depo_id = request.POST.get('depo_id')
            miktar = request.POST.get('miktar')
            fiyat = request.POST.get('fiyat', 0)
            foto = request.FILES.get('foto') 

            yeni_palet = Palet.objects.create(
                urun_cinsi_id=urun_id,
                mustahsil_id=mustahsil_id,
                depo_konumu_id=depo_id,
                miktar_kg=miktar,
                birim_fiyat=fiyat,
                urun_fotografi=foto 
            )
            messages.success(request, f"Palet #{yeni_palet.palet_no} başarıyla oluşturuldu!")
        except Exception as e:
            messages.error(request, f"Hata oluştu: {e}")

    context = {
        'urunler': UrunKategorisi.objects.all(),
        'mustahsiller': Mustahsil.objects.all(),
        'depolar': Depo.objects.all(),
    }
    return render(request, 'inventory/mobil_hizli_giris.html', context)