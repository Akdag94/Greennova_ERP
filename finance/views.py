from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa
from .models import CariHareket

def makbuz_pdf_indir(request, hareket_id):
    hareket = get_object_or_404(CariHareket, id=hareket_id)
    template_path = 'admin/finance/makbuz_pdf.html'
    context = {'hareket': hareket, 'tarih': hareket.tarih}
    
    response = HttpResponse(content_type='application/pdf')
    # Dosya adını plaka veya müstahsil adı yapabiliriz
    response['Content-Disposition'] = f'filename="makbuz_{hareket.id}.pdf"'
    
    template = get_template(template_path)
    html = template.render(context)

    # PDF oluşturma
    pisa_status = pisa.CreatePDF(html, dest=response)
    
    if pisa_status.err:
        return HttpResponse('PDF oluşturulurken bir hata oluştu <pre>' + html + '</pre>')
    return response