from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView

urlpatterns = [
    path('', RedirectView.as_view(url='/login/', permanent=False)),
    path('', include('inventory.urls')),
    path('admin/', admin.site.urls),
]
