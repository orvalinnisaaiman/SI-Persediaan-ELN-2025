from django.contrib import admin
from . import models

# Register your models here.
admin.site.register(models.supplier)
admin.site.register(models.customer)
admin.site.register(models.bahan)
admin.site.register(models.produk)
admin.site.register(models.pemesanan)
admin.site.register(models.detail_pemesanan_bahan)
admin.site.register(models.detail_pemesanan_produk)
admin.site.register(models.produksi)
admin.site.register(models.detail_produksi)
admin.site.register(models.pengiriman)
admin.site.register(models.detail_pengiriman)
admin.site.register(models.stok_opname)
admin.site.register(models.detail_so_bahan)
admin.site.register(models.detail_so_produk)
admin.site.register(models.kebutuhan_pallet)
admin.site.register(models.pallet_penuh)
admin.site.register(models.pallet_terbuka)