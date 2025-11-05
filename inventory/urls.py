from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.loginview, name='login'),
    path('performlogin', views.performlogin, name="performlogin"),
    path('performlogout', views.performlogout, name="performlogout"),
    path('base/', views.base,name='base'),
    
    #CRUD SUPPLIER
    path('create_supplier/', views.create_supplier, name = 'create_supplier'),
    path('read_supplier/', views.read_supplier, name = "read_supplier"),
    path('update_supplier/<str:id>/', views.update_supplier, name='update_supplier'),
    path('delete_supplier/<str:id>/', views.delete_supplier, name='delete_supplier'),

    #CRUD CUSTOMER
    path('create_customer/', views.create_customer, name = 'create_customer'),
    path('read_customer/', views.read_customer, name = "read_customer"),
    path('update_customer/<str:id>/', views.update_customer, name='update_customer'),
    path('delete_customer/<str:id>/', views.delete_customer, name='delete_customer'),

    #CRUD BAHAN
    path('create_bahan/', views.create_bahan, name = 'create_bahan'),
    path('read_bahan/', views.read_bahan, name = "read_bahan"),
    path('update_bahan/<str:id>/', views.update_bahan, name='update_bahan'),
    path('delete_bahan/<str:id>/', views.delete_bahan, name='delete_bahan'),
  
    #CRUD PRODUK
    path('create_produk/', views.create_produk, name = 'create_produk'),
    path('read_produk/', views.read_produk, name = "read_produk"),
    path('update_produk/<str:id>/', views.update_produk, name='update_produk'),
    path('delete_produk/<str:id>/', views.delete_produk, name='delete_produk'),
  
    #CRUD PEMESANAN
    path('create_pemesanan/', views.create_pemesanan, name = 'create_pemesanan'),
    path('read_pemesanan/', views.read_pemesanan, name = "read_pemesanan"),
    # drill-down per dokumen (per pemesanan)
    path('pemesanan/<int:id_pemesanan>/bahan/',  views.read_detail_pemesanan_bahan,  name='read_detail_pemesanan_bahan'),
    path('pemesanan/<int:id_pemesanan>/produk/', views.read_detail_pemesanan_produk, name='read_detail_pemesanan_produk'),
    # index global detail (lintas dokumen) - opsional tapi kamu minta ada
    path('pemesanan/detail-bahan/',  views.read_detail_bahan,  name='read_detail_bahan'),
    path('pemesanan/detail-produk/', views.read_detail_produk, name='read_detail_produk'),
    # update pemesanan & detail
    path('update_pemesanan/detail-bahan/<int:id_detail>/',  views.update_detail_pemesanan_bahan,  name='update_detail_pemesanan_bahan'),
    path('update_pemesanan/detail-produk/<int:id_detail>/', views.update_detail_pemesanan_produk, name='update_detail_pemesanan_produk'),
    path('update_pemesanan/<int:id>', views.update_pemesanan, name='update_pemesanan'),
    # delete pemesanan & detail
    path('delete_pemesanan/<int:id_pemesanan>/', views.delete_pemesanan, name='delete_pemesanan'),
    path('delete_pemesanan/detail-bahan/<int:id_detail>/', views.delete_detail_pemesanan_bahan, name='delete_detail_pemesanan_bahan'),
    path('delete_pemesanan/detail-produk/<int:id_detail>/', views.delete_detail_pemesanan_produk, name='delete_detail_pemesanan_produk'),
   
    #CRUD PRODUKSI
    path('create_produksi/', views.create_produksi, name = 'create_produksi'),
    path('read_produksi/', views.read_produksi, name = "read_produksi"),
    path('update_produksi/<str:id>/', views.update_produksi, name='update_produksi'),
    path("update_produksi/qc/<int:id>/", views.update_qc_produksi, name="update_qc_produksi"),
    path('delete_produksi/<int:id_produksi>/', views.delete_produksi, name='delete_produksi'),
    path('delete_produksi/detail/<int:id_detail>/', views.delete_produksi, name='delete_detail_produksi'),
    path('produksi/<int:id_detail>/set-qc-status/', views.set_qc_status, name='set_qc_status'),
    
    #CRUD PENGIRIMAN
    path('create_pengiriman/', views.create_pengiriman, name = 'create_pengiriman'),
    path('read_pengiriman/', views.read_pengiriman, name = "read_pengiriman"),
    path('update_pengiriman/<str:id>/', views.update_pengiriman, name='update_pengiriman'),
    path('delete_pengiriman/<int:id_pengiriman>/', views.delete_pengiriman, name='delete_pengiriman'),
    path('delete_pengiriman/detail/<int:id_detail>/', views.delete_pengiriman, name='delete_detail_pengiriman'),
    
    #CRUD STOK OPNAME
    # parent
    path('stok-opname/', views.read_stok_opname, name='read_stok_opname'),
    path('create_stok_opname/', views.create_stok_opname, name='create_stok_opname'),
    path('update_stok_opname/<int:id>', views.update_stok_opname, name='update_stok_opname'),
    path('delete_stok_opname/<int:id>', views.delete_stok_opname, name='delete_stok_opname'),
    # drill-down per dokumen (detail per so)
    path('stok-opname/<int:id_stok_opname>/bahan/',  views.read_detail_so_bahan,  name='read_detail_so_bahan'),
    path('stok-opname/<int:id_stok_opname>/produk/', views.read_detail_so_produk, name='read_detail_so_produk'),
    # indeks global detail (daftar detail bahan dan produk)
    path('stok-opname/detail-bahan/',  views.read_so_bahan,  name='read_so_bahan'),
    path('stok-opname/detail-produk/', views.read_so_produk, name='read_so_produk'),
    # update detail
    path('update_stok-opname/detail-bahan/<int:id_detail>',  views.update_detail_so_bahan,  name='update_detail_so_bahan'),
    path('update_stok-opname/detail-produk/<int:id_detail>', views.update_detail_so_produk, name='update_detail_so_produk'),
    # delete detail
    path('delete_stok-opname/detail-bahan/<int:id_detail>/', views.delete_detail_so_bahan, name='delete_detail_so_bahan'),
    path('delete_stok-opname/detail-produk/<int:id_detail>/', views.delete_detail_so_produk, name='delete_detail_so_produk'),

    # PALLET & WRAPPING
    path('read_pallet/', views.read_pallet, name='read_pallet'),
    path('pallet/manual-wrap/<int:id_produk>/', views.wrap_manual, name='wrap_manual'),

    # KEBUTUHAN PALLET (global per bahan)
    path('kebutuhan-pallet/', views.read_kebutuhan_pallet, name='read_kebutuhan_pallet'),
    path('create_kebutuhan-pallet/', views.create_kebutuhan_pallet, name='create_kebutuhan_pallet'),
    path('update_kebutuhan-pallet/<int:id>/', views.update_kebutuhan_pallet, name='update_kebutuhan_pallet'),
    path('delete_kebutuhan-pallet/<int:id>/', views.delete_kebutuhan_pallet, name='delete_kebutuhan_pallet'),
    
    #LAPORAN REKAPITULASI STOK
    path('laporan_rekapitulasi_stok/', views.laporan_rekapitulasi_stok, name='laporan_rekapitulasi_stok'),
    path('laporan_rekapitulasi_stok/pdf/', views.laporan_rekapitulasi_stok_pdf, name='laporan_rekapitulasi_stok_pdf'),
    
    #LAPORAN ALIRAN BARANG
    path('laporan_aliran_barang/', views.laporan_aliran_barang, name='laporan_aliran_barang'),
    path('laporan_aliran_barang/pdf/', views.laporan_aliran_barang_pdf, name='laporan_aliran_barang_pdf'),
    
    # Laporan Pengiriman
    path('laporan_pengiriman/', views.laporan_pengiriman, name='laporan_pengiriman'),
    path('laporan_pengiriman/pdf/', views.laporan_pengiriman_pdf, name='laporan_pengiriman_pdf'),

    # Laporan Stok Opname
    path('laporan_stok_opname/', views.laporan_stok_opname, name='laporan_stok_opname'),
    path('laporan_stok_opname/pdf/', views.laporan_stok_opname_pdf, name='laporan_stok_opname_pdf'),


]