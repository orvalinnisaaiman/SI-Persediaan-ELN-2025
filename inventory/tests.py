from django.test import TestCase, Client
from . import models
from django.contrib.auth.models import User, Group
from datetime import date
from django.db.models import Sum

# Create your tests here.
class StokProdukLogicTest(TestCase):
    
    def setUp(self):
        self.client = Client()
        self.group = Group.objects.create(name='ppic')
        self.user = User.objects.create_user(username='ppic', password='123')
        self.user.groups.add(self.group)
        self.client.login(username='ppic', password='123')
        
        self.customer = models.customer.objects.create(
            nama_customer="PT X",
            nomor_telepon_customer="08123456789",
            alamat_customer="Jakarta"
        )

        # Produk NON-EOE
        self.produk_non = models.produk.objects.create(
            nama_produk="207 x 111",
            jenis_produk="Can 307",
            kapasitas_pallet=100,
            safety_stock=0
        )

        # Produk EOE 
        self.produk_eoe = models.produk.objects.create(
            nama_produk="EOE 207",
            jenis_produk="EOE",
            kapasitas_pallet=100,
            safety_stock=0
        )

        prod = models.produksi.objects.create(tanggal_produksi=date.today())
        models.detail_produksi.objects.create(
            id_produksi=prod,
            id_produk=self.produk_non,
            id_bahan=models.bahan.objects.create(nama_bahan="Test", jenis_bahan="A"),
            jumlah_produk=100,
            jumlah_bahan_keluar=5,
            jumlah_reject=0,
        )

        pem = models.pemesanan.objects.create(
            id_supplier=models.supplier.objects.create(
                nama_supplier="Aespa",
                nomor_telepon_supplier="081", alamat_supplier="-"
            ),
            tanggal_pemesanan=date.today()
        )
        models.detail_pemesanan_produk.objects.create(
            id_pemesanan=pem,
            id_produk=self.produk_eoe,
            jumlah_produk_masuk=200
        )

        peng = models.pengiriman.objects.create(
            tanggal_pengiriman=date.today(),
            id_customer=self.customer,
            nomor_sj="SJ-001"
        )
        models.detail_pengiriman.objects.create(
            id_pengiriman=peng,
            id_produk=self.produk_non,
            jumlah_produk_dikirim=50
        )
        models.detail_pengiriman.objects.create(
            id_pengiriman=peng,
            id_produk=self.produk_eoe,
            jumlah_produk_dikirim=50
        )

    def test_stok_non_eoe(self):
        masuk = 100 
        keluar = 50 
        expected_stok = masuk - keluar
        
        stok = models.detail_pengiriman.objects.filter(
            id_produk=self.produk_non
        ).aggregate(total=Sum("jumlah_produk_dikirim"))["total"]
        
        hasil = (100 - (stok or 0))

        self.assertEqual(hasil, expected_stok)

    def test_stok_eoe(self):
        masuk = 200  
        keluar = 50
        expected_stok = masuk - keluar

        stok_keluar = models.detail_pengiriman.objects.filter(
            id_produk=self.produk_eoe
        ).aggregate(total=Sum("jumlah_produk_dikirim"))["total"]

        hasil = (200 - (stok_keluar or 0))

        self.assertEqual(hasil, expected_stok)
