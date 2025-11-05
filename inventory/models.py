from django.db import models

# Create your models here.
class supplier(models.Model):
    id_supplier = models.AutoField(primary_key=True)
    nama_supplier = models.CharField(max_length=100)
    nomor_telepon_supplier = models.CharField(max_length=50)
    alamat_supplier = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return str(self.nama_supplier)

class customer(models.Model):
    id_customer = models.AutoField(primary_key=True)
    nama_customer = models.CharField(max_length=100)
    nomor_telepon_customer = models.CharField(max_length=50)
    alamat_customer = models.TextField()
    
    def __str__(self):
        return str(self.nama_customer)
    
class bahan(models.Model):
    id_bahan = models.AutoField(primary_key=True)
    nama_bahan = models.CharField(max_length=100)
    jenis_bahan = models.CharField(max_length=100)
    
    def __str__(self):
        return str(self.nama_bahan)
    
class produk(models.Model):
    id_produk = models.AutoField(primary_key=True)
    nama_produk = models.CharField(max_length=100)
    jenis_produk = models.CharField(max_length=100)
    kapasitas_pallet = models.PositiveIntegerField()
    safety_stock = models.PositiveIntegerField(default=0)
    
    def __str__(self):
        return str(self.nama_produk)
    
class pemesanan(models.Model):
    id_pemesanan = models.AutoField(primary_key=True)
    id_supplier = models.ForeignKey(supplier, on_delete=models.CASCADE)
    tanggal_pemesanan = models.DateField()
    
    def __str__(self):
        return str(self.id_pemesanan)
    
class detail_pemesanan_bahan(models.Model):
    id_detail_pemesanan = models.AutoField(primary_key=True)
    id_pemesanan = models.ForeignKey(pemesanan, on_delete=models.CASCADE)
    id_bahan = models.ForeignKey(bahan, on_delete=models.CASCADE)
    jumlah_bahan_masuk = models.PositiveIntegerField()
    
    def __str__(self):
        return "{} - {}".format(self.id_pemesanan.tanggal_pemesanan,self.id_bahan)

class detail_pemesanan_produk(models.Model):
    id_detail_pemesanan = models.AutoField(primary_key=True)
    id_pemesanan = models.ForeignKey(pemesanan, on_delete=models.CASCADE)
    id_produk = models.ForeignKey(produk, on_delete=models.CASCADE)
    jumlah_produk_masuk = models.PositiveIntegerField()
    
    def __str__(self):
        return "{} - {}".format(self.id_pemesanan.tanggal_pemesanan,self.id_produk)

class produksi(models.Model):
    id_produksi = models.AutoField(primary_key=True)
    tanggal_produksi = models.DateField()
    
    def __str__(self):
        return str(self.id_produksi)
    
class detail_produksi(models.Model):
    id_detail_produksi = models.AutoField(primary_key=True)
    id_produksi = models.ForeignKey(produksi, on_delete=models.CASCADE)
    id_produk = models.ForeignKey(produk, on_delete=models.CASCADE)
    id_bahan = models.ForeignKey(bahan, on_delete=models.CASCADE)
    jumlah_produk  = models.PositiveIntegerField()
    jumlah_reject = models.PositiveIntegerField(null=True, blank=True)
    jumlah_fg = models.PositiveIntegerField(null=True, blank=True)
    jumlah_bahan_keluar = models.PositiveIntegerField()
    
    STATUS_QC_CHOICES = [
        ('belum', 'Belum diperiksa'),
        ('sedang', 'Sedang diperiksa'),
        ('sudah', 'Sudah diperiksa'),
    ]
    status_qc = models.CharField(
        max_length=10,
        choices=STATUS_QC_CHOICES,
        default='belum'
    )
    
    def __str__(self):
        return "{} - {}".format(self.id_produksi.tanggal_produksi,self.id_produk)
    
    
class pengiriman(models.Model):
    id_pengiriman = models.AutoField(primary_key=True)
    tanggal_pengiriman = models.DateField()
    id_customer = models.ForeignKey(customer, on_delete=models.CASCADE)
    nomor_sj = models.CharField(max_length=100)
    
    def __str__(self):
        return str(self.id_pengiriman)
    
class detail_pengiriman(models.Model):
    id_detail_pengiriman = models.AutoField(primary_key=True)
    id_pengiriman = models.ForeignKey(pengiriman, on_delete=models.CASCADE)
    id_produk = models.ForeignKey(produk, on_delete=models.CASCADE)
    jumlah_produk_dikirim = models.PositiveIntegerField()
    
    def __str__(self):
        return "{} - {}".format(self.id_pengiriman.tanggal_pengiriman, self.id_customer)
    
class stok_opname(models.Model):
    id_stok_opname = models.AutoField(primary_key=True)
    tanggal_stok_opname = models.DateField()
    
    def __str__(self):
        return str(self.id_stok_opname)
    
class detail_so_bahan(models.Model):
    id_detail_so_bahan = models.AutoField(primary_key=True)
    id_stok_opname = models.ForeignKey(stok_opname, on_delete=models.CASCADE)
    id_bahan = models.ForeignKey(bahan, on_delete=models.CASCADE)
    stok_fisik_bahan = models.PositiveIntegerField()
    
    def __str__(self):
        return "{} - {}".format(self.id_stok_opname, self.id_bahan)
    
class detail_so_produk(models.Model):
    id_detail_so_produk = models.AutoField(primary_key=True)
    id_stok_opname = models.ForeignKey(stok_opname, on_delete=models.CASCADE)
    id_produk = models.ForeignKey(produk, on_delete=models.CASCADE)
    stok_fisik_produk = models.PositiveIntegerField()
    
    def __str__(self):
        return "{} - {}".format(self.id_stok_opname, self.id_produk)
    
class kebutuhan_pallet(models.Model):
    id_kebutuhan = models.AutoField(primary_key=True)
    id_bahan = models.ForeignKey(bahan, on_delete=models.CASCADE)
    kebutuhan = models.PositiveIntegerField()
    mm_per_roll = models.PositiveIntegerField(default=0)
    
    def __str__(self):
        return "{} - {}".format(self.id_bahan, self.kebutuhan)
    
class pallet_penuh(models.Model):
    AUTO = "AUTO"
    MANUAL = "MANUAL"
    EVENT_TYPES = [(AUTO, "Auto Close"), (MANUAL, "Manual Close")]

    id_pallet_penuh = models.AutoField(primary_key=True)
    id_produk = models.ForeignKey(produk, on_delete=models.CASCADE)
    id_detail_produksi = models.ForeignKey(
        detail_produksi, on_delete=models.SET_NULL, null=True, blank=True, related_name="events_menutup"
    )
    id_detail_pemesanan_produk = models.ForeignKey(detail_pemesanan_produk, on_delete=models.SET_NULL,
    null=True, blank=True)
    jumlah_pallet_penuh = models.PositiveIntegerField()
    tanggal_event = models.DateField()
    event_type = models.CharField(max_length=10, choices=EVENT_TYPES, default=AUTO)

    def __str__(self): return f"{self.id_produk} - wrap {self.jumlah_pallet_penuh} pallet @ {self.tanggal_event}"
    
class pallet_terbuka(models.Model):
    id_pallet_terbuka = models.AutoField(primary_key=True)
    id_produk = models.ForeignKey(produk, on_delete=models.CASCADE)
    sisa_item = models.PositiveIntegerField()
    tanggal_update = models.DateField()
    
    def __str__(self):
        return "{} - {}".format(self.id_produk, self.sisa_item)
    