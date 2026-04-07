from django.urls import path
from . import views

urlpatterns = [
    # Cihaz veriyi tam olarak bu adrese gönderecek
    path('okut/', views.kart_okut, name='kart_okut'),
]