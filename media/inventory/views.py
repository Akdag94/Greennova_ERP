# __sig__: 76a253b5 | build:2026 | dev:609191fb
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.utils import timezone
import json

from .models import Palet, UrunKategorisi, Depo
from finance.models import Sevkiyat, Mustahsil


# =============================================================
# 1) QR Tarama Ekranı (Tır Yükleme İçin)
# =============================================================
@login_required
def qr_scanner_view(request):
    return render(request, 'inventory/qr_scanner.html')


# =============================================================
# 2) PALET BİLGİSİ + AKTİF TIR LİSTESİ
# =============================================================
@login_required
def scan_palet_api(request, palet_id):
    """QR'dan gelen palet ID ile palet ve mevcut tır listesini döner."""
    try:
        try:
            palet = Palet.objects.select_related('urun_cinsi', 'sevkiyat').get(id=palet_id)
        except (Palet.DoesNotExist, ValueError):
            return JsonResponse({
                'status': 'error',
                'message': f'Geçersiz Kod: {palet_id} ID numaralı palet bulunamadı!'
            })

        if palet.durum in ('yuklendi', 'cikti'):
            tir_plaka = palet.sevkiyat.plaka if palet.sevkiyat else "Bilinmiyor"
            status_text = "teslim edilmiş" if palet.durum == 'cikti' else "yüklenmiş"
            return JsonResponse({
                'status': 'warning',
                'message': f'Bu palet (#{palet.palet_no}) zaten {status_text} ({tir_plaka})!',
            })

        # ✅ DÜZELTİLDİ: F() yerine .annotate() kullanılmalı
        aktif_tirlar_qs = Sevkiyat.objects.filter(
            tamamlandi=False
        ).select_related('musteri').values(
            'id', 'plaka'
        )

        # Müşteri unvanını ekle
        aktif_tirlar = []
        for s in Sevkiyat.objects.filter(tamamlandi=False).select_related('musteri'):
            aktif_tirlar.append({
                'id': s.id,
                'plaka': s.plaka,
                'varis_yeri': s.musteri.unvan if s.musteri else 'Müşteri Yok',
            })

        if not aktif_tirlar:
            return JsonResponse({
                'status': 'error',
                'message': 'Sistemde yükleme yapılabilecek aktif bir tır (Sevkiyat) bulunamadı!'
            })

        return JsonResponse({
            'status': 'success',
            'palet_id': palet.id,
            'palet_no': palet.palet_no,
            'kg': str(palet.miktar_kg or 0),
            'brut_kg': str(palet.brut_miktar_kg),
            'fire': str(palet.fire_miktar_kg),
            'palet_adedi': palet.toplam_palet_adedi,
            'urun': palet.urun_cinsi.ad if palet.urun_cinsi else "Belirtilmemiş",
            'tirlar': aktif_tirlar
        })

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'Sistem Hatası: {str(e)}'})


# =============================================================
# 3) PALETİ TIRA YÜKLE
# =============================================================
@login_required
@csrf_exempt
@require_http_methods(['POST'])
def paleti_tira_yukle_api(request):
    """Tek paleti tıra bağla."""
    palet_id = request.POST.get('palet_id')
    sevkiyat_id = request.POST.get('sevkiyat_id')

    if not palet_id or not sevkiyat_id:
        return JsonResponse({'status': 'error', 'message': 'palet_id ve sevkiyat_id zorunlu'}, status=400)

    try:
        with transaction.atomic():
            palet = Palet.objects.select_for_update().get(id=palet_id)
            sevkiyat = Sevkiyat.objects.get(id=sevkiyat_id)

            # Idempotent: aynı palet aynı tıra zaten yüklü ise OK döndür
            if palet.sevkiyat_id == sevkiyat.id and palet.durum == 'yuklendi':
                return JsonResponse({
                    'status': 'success',
                    'message': f'✅ {palet.palet_no} zaten bu tıra yüklü.',
                    'idempotent': True
                })

            if palet.durum in ('yuklendi', 'cikti') and palet.sevkiyat_id != sevkiyat.id:
                return JsonResponse({
                    'status': 'error',
                    'message': f"Bu palet başka bir tıra ({palet.sevkiyat.plaka if palet.sevkiyat else '?'}) yüklü!"
                })

            palet.sevkiyat = sevkiyat
            palet.durum = 'yuklendi'
            palet.save()

        return JsonResponse({
            'status': 'success',
            'message': f"✅ {palet.palet_no} No'lu palet {sevkiyat.plaka} tırına başarıyla eklendi!"
        })
    except Palet.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Palet bulunamadı'}, status=404)
    except Sevkiyat.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Sevkiyat bulunamadı'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f"Yükleme Başarısız: {str(e)}"})


# =============================================================
# 4) MOBİL HIZLI MAL KABUL
# =============================================================
@login_required
def mobil_hizli_giris(request):
    if request.method == "POST":
        try:
            urun_id = request.POST.get('urun_id')
            mustahsil_id = request.POST.get('mustahsil_id')
            depo_id = request.POST.get('depo_id')
            miktar = request.POST.get('miktar')
            brut = request.POST.get('brut') or miktar
            fiyat = request.POST.get('fiyat', 0)
            foto = request.FILES.get('foto')

            yeni_palet = Palet.objects.create(
                urun_cinsi_id=urun_id,
                mustahsil_id=mustahsil_id,
                depo_konumu_id=depo_id or None,
                brut_miktar_kg=brut,
                miktar_kg=miktar,
                birim_fiyat=fiyat,
                urun_fotografi=foto
            )
            messages.success(request, f"✅ Palet #{yeni_palet.palet_no} başarıyla oluşturuldu!")
            return redirect('mobil_hizli_giris')
        except Exception as e:
            messages.error(request, f"❌ Hata oluştu: {e}")

    context = {
        'urunler': UrunKategorisi.objects.all(),
        'mustahsiller': Mustahsil.objects.all().order_by('ad_soyad'),
        'depolar': Depo.objects.all(),
    }
    return render(request, 'inventory/mobil_hizli_giris.html', context)


# =============================================================
# 5) 🔥 OFFLINE SYNC API — PWA için BATCH gönderim
#    Telefonda biriken taramaları toplu işle
# =============================================================
@login_required
@csrf_exempt
@require_http_methods(['POST'])
def offline_sync_api(request):
    """
    PWA çevrimdışıyken biriken taramaları sıralı işler.

    POST body:
    {
        "operations": [
            {
                "client_id": "uuid-1",          // idempotent guard
                "type": "load_palet",            // load_palet | scan_only
                "palet_id": 12,
                "sevkiyat_id": 5,
                "scanned_at": "2026-04-27T14:30:00Z"
            },
            ...
        ]
    }

    Yanıt:
    {
        "results": [
            {"client_id": "uuid-1", "status": "ok|conflict|error", "message": "..."},
            ...
        ]
    }
    """
    try:
        body = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Geçersiz JSON'}, status=400)

    operations = body.get('operations', [])
    if not isinstance(operations, list):
        return JsonResponse({'error': "'operations' bir liste olmalı"}, status=400)

    results = []

    for op in operations:
        client_id = op.get('client_id', '')
        op_type = op.get('type', 'load_palet')
        palet_id = op.get('palet_id')
        sevkiyat_id = op.get('sevkiyat_id')

        try:
            if op_type == 'load_palet':
                if not palet_id or not sevkiyat_id:
                    results.append({
                        'client_id': client_id,
                        'status': 'error',
                        'message': 'palet_id ve sevkiyat_id zorunlu'
                    })
                    continue

                with transaction.atomic():
                    try:
                        palet = Palet.objects.select_for_update().get(id=palet_id)
                    except Palet.DoesNotExist:
                        results.append({
                            'client_id': client_id, 'status': 'error',
                            'message': f'Palet #{palet_id} bulunamadı'
                        })
                        continue

                    try:
                        sevkiyat = Sevkiyat.objects.get(id=sevkiyat_id)
                    except Sevkiyat.DoesNotExist:
                        results.append({
                            'client_id': client_id, 'status': 'error',
                            'message': f'Sevkiyat #{sevkiyat_id} bulunamadı'
                        })
                        continue

                    # CONFLICT RESOLUTION:
                    # Palet zaten bu tıra bağlıysa idempotent OK
                    if palet.sevkiyat_id == sevkiyat.id and palet.durum == 'yuklendi':
                        results.append({
                            'client_id': client_id, 'status': 'ok',
                            'message': f'{palet.palet_no} zaten yüklü (idempotent)',
                            'idempotent': True
                        })
                        continue

                    # Başka tıra yüklenmişse veya teslim edilmişse → çakışma
                    if palet.durum in ('yuklendi', 'cikti') and palet.sevkiyat_id != sevkiyat.id:
                        results.append({
                            'client_id': client_id, 'status': 'conflict',
                            'message': f'{palet.palet_no} başka bir tıra ({palet.sevkiyat.plaka if palet.sevkiyat else "?"}) yüklenmiş'
                        })
                        continue

                    palet.sevkiyat = sevkiyat
                    palet.durum = 'yuklendi'
                    palet.save()

                    results.append({
                        'client_id': client_id, 'status': 'ok',
                        'message': f'{palet.palet_no} → {sevkiyat.plaka} yüklendi',
                        'palet_no': palet.palet_no,
                        'kg': str(palet.miktar_kg or 0)
                    })
            else:
                results.append({
                    'client_id': client_id, 'status': 'error',
                    'message': f'Bilinmeyen operasyon tipi: {op_type}'
                })

        except Exception as e:
            results.append({
                'client_id': client_id, 'status': 'error',
                'message': f'Sistem hatası: {str(e)}'
            })

    return JsonResponse({
        'results': results,
        'processed_at': timezone.now().isoformat()
    })


# =============================================================
# 6) AKTİF SEVKİYATLAR (PWA cache için)
# =============================================================
@login_required
def aktif_sevkiyatlar_api(request):
    """PWA başlangıçta önbelleğe alacak sevkiyat listesi."""
    sevkiyatlar = Sevkiyat.objects.filter(
        tamamlandi=False
    ).select_related('musteri').order_by('-cikis_tarihi')[:50]

    data = [{
        'id': s.id,
        'plaka': s.plaka,
        'sofor': s.sofor_ad,
        'musteri': s.musteri.unvan if s.musteri else 'Müşteri Yok',
        'cikis': s.cikis_tarihi.isoformat() if s.cikis_tarihi else '',
    } for s in sevkiyatlar]

    return JsonResponse({'sevkiyatlar': data})
