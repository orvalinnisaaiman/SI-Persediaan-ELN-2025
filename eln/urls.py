# eln/urls.py
from django.contrib import admin
from django.urls import path, include, reverse, NoReverseMatch
from django.shortcuts import redirect

def root_redirect(request):
    # urutkan sesuai target kamu
    for name in ('base', 'login'):
        try:
            return redirect(reverse(name))
        except NoReverseMatch:
            pass
    # fallback terakhir (ubah kalau perlu)
    return redirect('/login/')

urlpatterns = [
    path('', root_redirect, name='root'),
    path('', include('inventory.urls')),   # sesuaikan kalau app utamamu beda
    path('admin/', admin.site.urls),
]
