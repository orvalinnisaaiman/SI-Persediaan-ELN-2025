from django.contrib import admin
from django.urls import path, include
from inventory import views as inv

urlpatterns = [
    # Root langsung ke halaman login kamu
    path('', inv.loginview, name='login'),

    # Halaman utama setelah login
    path('base', inv.base, name='base'),

    # Auth actions
    path('performlogin', inv.performlogin, name='performlogin'),
    path('performlogout', inv.performlogout, name='performlogout'),

    # Sisanya biar tetap diambil dari app
    path('', include('inventory.urls')),

    path('admin/', admin.site.urls),
]
