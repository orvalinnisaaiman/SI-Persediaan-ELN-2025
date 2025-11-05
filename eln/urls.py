from django.contrib import admin
from django.urls import path, include, reverse, NoReverseMatch
from django.shortcuts import redirect

def root_redirect(request):
    # urutan prioritas: ganti sesuai kebiasaanmu
    for name in ('base', 'login'):
        try:
            return redirect(reverse(name))
        except NoReverseMatch:
            pass
    # fallback terakhir kalau nama URL di atas nggak ada
    return redirect('/accounts/login/')

urlpatterns = [
    path('', root_redirect, name='root'),
    path('', include('inventory.urls')),   # sesuaikan app utama
    path('admin/', admin.site.urls),
]
