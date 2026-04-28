"""
finance/views.py
Geriye uyumluluk: eski /finance/makbuz/<id>/ URL'si hâlâ çalışır.
Yeni belgeler: finance/print_views.py
"""
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import get_object_or_404, redirect

from .models import CariHareket
from .print_views import mustahsil_makbuz


@staff_member_required
def makbuz_pdf_indir(request, hareket_id):
    """
    Eski URL: /finance/makbuz/<id>/
    Yeni sisteme yönlendir.
    """
    return mustahsil_makbuz(request, hareket_id)
