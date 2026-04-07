from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import get_user_model
from .models import Yoklama
import json

Personel = get_user_model()

# Cihazların güvenlik engeline takılmadan istek atabilmesi için csrf_exempt kullanıyoruz
@csrf_exempt 
def kart_okut(request):
    if request.method == 'POST':
        try:
            # Gelen veriyi oku
            data = json.loads(request.body)
            rfid_no = data.get('rfid_kart_no')

            if not rfid_no:
                return JsonResponse({'hata': 'Kart numarası gönderilmedi.'}, status=400)

            # Bu kart numarasına sahip personeli veritabanında bul
            personel = Personel.objects.filter(rfid_kart_no=rfid_no).first()

            if personel:
                # Personelin o günkü son hareketine bak (İçeride mi yoksa dışarıda mı?)
                son_hareket = Yoklama.objects.filter(personel=personel).order_by('-tarih_saat').first()
                
                # Eğer son hareketi 'giriş' ise, şimdi 'çıkış' yapıyordur. Aksi halde 'giriş' yapıyordur.
                if son_hareket and son_hareket.islem_tipi == 'giris':
                    yeni_islem = 'cikis'
                else:
                    yeni_islem = 'giris'

                # Yeni yoklama kaydını oluştur ve veritabanına kaydet
                Yoklama.objects.create(personel=personel, islem_tipi=yeni_islem)
                
                mesaj = f"Hos geldin, {personel.first_name}!" if yeni_islem == 'giris' else f"Iyi gunler, {personel.first_name}!"
                return JsonResponse({'durum': 'basarili', 'mesaj': mesaj, 'islem': yeni_islem})
            
            else:
                return JsonResponse({'hata': 'Sistemde bu karta tanimli personel bulunamadi.'}, status=404)

        except Exception as e:
            return JsonResponse({'hata': str(e)}, status=500)
    
    return JsonResponse({'hata': 'Sadece POST istekleri kabul edilir.'}, status=405)