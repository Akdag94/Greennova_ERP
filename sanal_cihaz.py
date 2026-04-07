import requests

API_URL = "http://127.0.0.1:8000/api/yoklama/okut/"
print("--- GREENNOVA KART OKUYUCU SIMULATORU ---")
print("Cikmak icin 'q' tusuna basin.\n")

while True:
    kart_no = input("Lutfen Karti Okutun: ")
    
    if kart_no.lower() == 'q':
        break
        
    veri = {"rfid_kart_no": kart_no}
    
    try:
        cevap = requests.post(API_URL, json=veri)
        sonuc = cevap.json()
        
        if cevap.status_code == 200:
            print(f"✅ {sonuc['mesaj']} (Islem: {sonuc['islem']})\n")
        else:
            print(f"❌ HATA: {sonuc.get('hata')}\n")
    except Exception:
        print("❌ HATA: Sunucuya ulasilamiyor. Django acik mi?\n")