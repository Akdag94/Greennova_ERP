from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.utils.html import format_html
from .models import Yoklama, PersonelRapor
from django.contrib.auth import get_user_model
User = get_user_model() # Artık User senin 'users.Personel' modelini temsil eder

# 📋 1. PERSONEL DETAYINDA GÖRÜNECEK MESAİ TABLOSU (INLINE)
class YoklamaInline(admin.TabularInline):
    model = Yoklama
    extra = 0
    readonly_fields = ('islem_tipi', 'tarih_saat', 'calisma_suresi_ozet')
    fields = ('islem_tipi', 'tarih_saat', 'calisma_suresi_ozet')
    ordering = ('-tarih_saat',)
    verbose_name = "Mesai Kaydı"
    verbose_name_plural = "🚀 Personel Geçmiş Mesai Hareketleri"
    can_delete = False 

    def calisma_suresi_ozet(self, obj):
        if obj.islem_tipi == 'cikis':
            giris = Yoklama.objects.filter(
                personel=obj.personel,
                islem_tipi='giris',
                tarih_saat__lt=obj.tarih_saat,
                tarih_saat__date=obj.tarih_saat.date()
            ).order_by('-tarih_saat').first()

            if giris:
                fark = obj.tarih_saat - giris.tarih_saat
                sn = int(fark.total_seconds())
                return format_html('<b style="color: #20c997;">⏱️ {} sa {} dk</b>', sn // 3600, (sn // 60) % 60)
        return "-"
    calisma_suresi_ozet.short_description = "Çalışma Süresi"

# 👤 2. USER ADMİN'İ YENİDEN TANIMLIYORUZ (HATASIZ)
try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass

@admin.register(User)
class PersonelAdmin(BaseUserAdmin):
    inlines = (YoklamaInline,)
    list_display = BaseUserAdmin.list_display + ('mesai_durumu',)

    def mesai_durumu(self, obj):
        return format_html('<b style="color: #28a745;">✅ Aktif Takip</b>')
    mesai_durumu.short_description = "MESAİ DURUMU"

# 📊 3. YENİ: PERSONEL MESAİ RAPORLARI (SADECE OKUNUR BÖLÜM)
@admin.register(PersonelRapor)
class PersonelRaporAdmin(admin.ModelAdmin):
    list_display = ('personel_adi', 'toplam_mesai_bilgisi', 'son_hareket', 'rapor_linki')
    readonly_fields = ('personel_bilgi_paneli', 'gunluk_mesai_dokumu_tablosu')
    fields = ('personel_bilgi_paneli', 'gunluk_mesai_dokumu_tablosu')

    # 🚫 MANUEL MÜDAHALEYİ TAMAMEN KAPATTIK
    def has_add_permission(self, request): return False
    def has_delete_permission(self, request, obj=None): return False
    def has_change_permission(self, request, obj=None): return False

    def personel_adi(self, obj):
        return obj.get_full_name() or obj.username
    personel_adi.short_description = "PERSONEL"

    def rapor_linki(self, obj):
        return format_html('<span style="color: #28a745; font-weight: bold;">🔍 Raporu Görüntüle</span>')
    rapor_linki.short_description = "İŞLEM"

    def toplam_mesai_bilgisi(self, obj):
        cikislar = Yoklama.objects.filter(personel=obj, islem_tipi='cikis')
        toplam_sn = 0
        for cikis in cikislar:
            giris = Yoklama.objects.filter(
                personel=obj, islem_tipi='giris', 
                tarih_saat__lt=cikis.tarih_saat, tarih_saat__date=cikis.tarih_saat.date()
            ).order_by('-tarih_saat').first()
            if giris:
                toplam_sn += (cikis.tarih_saat - giris.tarih_saat).total_seconds()
        saat = int(toplam_sn // 3600)
        dakika = int((toplam_sn // 60) % 60)
        return f"{saat} sa {dakika} dk"
    toplam_mesai_bilgisi.short_description = "TOPLAM ÇALIŞMA"

    def son_hareket(self, obj):
        son = Yoklama.objects.filter(personel=obj).order_by('-tarih_saat').first()
        return son.tarih_saat.strftime("%d.%m.%Y %H:%M") if son else "-"

    def personel_bilgi_paneli(self, obj):
        return format_html("<h3>Personel Mesai Analiz Raporu: {}</h3>", obj.get_full_name() or obj.username)

    def gunluk_mesai_dokumu_tablosu(self, obj):
        kayitlar = Yoklama.objects.filter(personel=obj, islem_tipi='cikis').order_by('-tarih_saat')
        html = """
        <table style="width:100%; border-collapse: collapse; background: #1e1e1e; color: #e0e0e0; border-radius: 10px;">
            <thead><tr style="background: #28a745; color: white;">
                <th style="padding: 12px; text-align: left;">TARİH</th>
                <th style="padding: 12px; text-align: left;">GÜNLÜK ÇALIŞMA SÜRESİ</th>
            </tr></thead><tbody>
        """
        for cikis in kayitlar:
            giris = Yoklama.objects.filter(
                personel=obj, islem_tipi='giris', 
                tarih_saat__lt=cikis.tarih_saat, tarih_saat__date=cikis.tarih_saat.date()
            ).order_by('-tarih_saat').first()
            sure = "Hata: Giriş Yok"
            if giris:
                fark = cikis.tarih_saat - giris.tarih_saat
                sn = int(fark.total_seconds())
                sure = f"{sn//3600} sa {(sn//60)%60} dk"
            html += f'<tr style="border-bottom: 1px solid #333;"><td style="padding: 12px;">{cikis.tarih_saat.strftime("%d.%m.%Y")}</td><td style="padding: 12px; font-weight: bold; color: #28a745;">⏱️ {sure}</td></tr>'
        html += "</tbody></table>"
        return format_html(html)

# 📋 4. ANA YOKLAMA LİSTESİ (ÇALIŞAN KISIM)
@admin.register(Yoklama)
class YoklamaAdmin(admin.ModelAdmin):
    list_display = ('personel_ad', 'islem_durumu', 'tarih_kolonu', 'saat_kolonu', 'gunluk_mesai_ozeti')
    list_filter = ('islem_tipi', 'tarih_saat', 'personel')
    search_fields = ('personel__first_name', 'personel__last_name', 'personel__username')
    list_per_page = 20
    ordering = ('-tarih_saat',)

    def personel_ad(self, obj):
        full_name = obj.personel.get_full_name()
        return full_name if full_name else obj.personel.username
    personel_ad.short_description = "PERSONEL"

    def islem_durumu(self, obj):
        color = "#28a745" if obj.islem_tipi == 'giris' else "#ffc107"
        icon = "➡️ GİRİŞ" if obj.islem_tipi == 'giris' else "⬅️ ÇIKIŞ"
        return format_html(
            '<b style="color: {}; background: {}15; padding: 4px 10px; border-radius: 6px; border: 1px solid {};">{}</b>',
            color, color, color, icon
        )
    islem_durumu.short_description = "İŞLEM TİPİ"

    def tarih_kolonu(self, obj): return obj.tarih_saat.strftime("%d.%m.%Y")
    def saat_kolonu(self, obj): return obj.tarih_saat.strftime("%H:%M:%S")

    def gunluk_mesai_ozeti(self, obj):
        if obj.islem_tipi == 'cikis':
            giris_kaydi = Yoklama.objects.filter(
                personel=obj.personel, islem_tipi='giris',
                tarih_saat__lt=obj.tarih_saat, tarih_saat__date=obj.tarih_saat.date()
            ).order_by('-tarih_saat').first()
            if giris_kaydi:
                fark = obj.tarih_saat - giris_kaydi.tarih_saat
                sn = int(fark.total_seconds())
                return format_html('<span style="color: #20c997; font-weight: bold;">⏱️ {} sa {} dk</span>', sn//3600, (sn//60)%60)
        return "-"
    gunluk_mesai_ozeti.short_description = "TOPLAM ÇALIŞMA"