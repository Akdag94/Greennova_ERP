from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import Personel


@admin.register(Personel)
class PersonelAdmin(BaseUserAdmin):
    list_display = ('username', 'get_full_name', 'email', 'rol', 'departman', 'is_active')
    list_filter = ('rol', 'is_active', 'is_staff')
    search_fields = ('username', 'first_name', 'last_name', 'email', 'rfid_kart_no')

    # BaseUserAdmin fieldsets'ine ek alanları ekle
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Greennova Bilgileri', {
            'fields': ('rol', 'departman', 'telefon', 'rfid_kart_no'),
        }),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Greennova Bilgileri', {
            'fields': ('rol', 'departman', 'telefon', 'rfid_kart_no',
                       'first_name', 'last_name', 'email'),
        }),
    )
