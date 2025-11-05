from django.shortcuts import render, redirect
from . import models
from datetime import datetime, timedelta, date
import calendar
from django.http import HttpResponse
from django.contrib import messages
from django.contrib.auth import login , logout, authenticate
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from .decorators import role_required
from django.forms import DateInput
import json
from django.db.models import F,Q,Sum,Value, Prefetch, Subquery, OuterRef
import math
# try:
#     from weasyprint import HTML
# except Exception:
#     HTML = None

from django.template.loader import render_to_string
import tempfile
from django.urls import reverse
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.utils.http import urlencode
from django.utils.timezone import now
from django.utils import timezone
from collections import defaultdict
from django.core.paginator import Paginator


# Create your views here.
def loginview(request):
    if request.user.is_authenticated:
        group = None
        if request.user.groups.exists():
            group = request.user.groups.all()[0].name

        if group in ['ppic','finance', 'manajer']:
            return redirect('base')
        elif group == 'produksi':
            return redirect('read_produksi')
        elif group == 'qc':
            return redirect('read_produksi')
        else :
            return redirect('read_produk')
    else:
        return render(request,"base/login.html")
    
def performlogin(request):
    if request.method != "POST":
        return HttpResponse("Method not Allowed")
    else:
        username_login = request.POST['username']
        password_login = request.POST['password']
        userobj = authenticate(request, username=username_login,password=password_login)
        if userobj is not None:
            login(request, userobj)
            messages.success(request,"Login success")
            if userobj.groups.filter(name='ppic').exists() or userobj.groups.filter(name='finance').exists() or userobj.groups.filter(name='manajer').exists():
                return redirect("base")
            elif userobj.groups.filter(name='produksi').exists() :
                return redirect("read_produksi")
            elif  userobj.groups.filter(name='qc').exists() :
                return redirect('read_produksi')
        else:
            messages.error(request,"Username atau Password salah !!!")
            return redirect("login")


@login_required(login_url="login")
def logoutview(request):
    logout(request)
    messages.info(request,"Berhasil Logout")
    return redirect('login')

@login_required(login_url="login")
def performlogout(request):
    logout(request)
    return redirect("login")

def _in_group(user, name):
    return user.groups.filter(name=name).exists()


'''DASHBOARD/BASE'''
@login_required(login_url='login')
@role_required(['ppic', 'finance', 'manajer'])
def base(request):
    bahanobj = models.bahan.objects.all().count()
    produkobj = models.produk.objects.all().count()
    pemesananprodukobj = models.detail_pemesanan_produk.objects.all()
    
    # === Barang Jadi : EOE only ===
    eoe_q = (
    Q(nama_produk__iregex=r'(^|[^A-Za-z0-9])EOE([^A-Za-z0-9]|$)') |
    Q(nama_produk__iregex=r'\bBottom\s+End\b')
    )
    eoe_ids = set(
        models.produk.objects
        .filter(eoe_q)
        .values_list('id_produk', flat=True)
    )

    # === Barang Jadi : Hasil Produksi ===
    produk_list = models.produk.objects.all()
    produk_labels = []
    produk_stok = []
    total_stok_produk = 0

    for produk in produk_list:
        if produk.id_produk in eoe_ids:
            total_masuk = models.detail_pemesanan_produk.objects.filter(id_produk=produk).aggregate(total=Sum('jumlah_produk_masuk'))['total'] or 0
        else:
            total_masuk = models.detail_produksi.objects.filter(id_produk=produk).aggregate(total=Sum('jumlah_produk'))['total'] or 0
        
        total_keluar = models.detail_pengiriman.objects.filter(id_produk=produk).aggregate(total=Sum('jumlah_produk_dikirim'))['total'] or 0
        stok = total_masuk - total_keluar
        produk_labels.append(produk.nama_produk)
        produk_stok.append(stok)
        total_stok_produk += stok

    # === Bahan Pembantu ===
    bahan_list = models.bahan.objects.filter(jenis_bahan__icontains='pembantu')
    bahan_labels = []
    bahan_stok = []
    total_stok_bahan_pembantu = 0
    
    for bahan in bahan_list:
        total_masuk = models.detail_pemesanan_bahan.objects.filter(id_bahan=bahan).aggregate(total=Sum('jumlah_bahan_masuk'))['total'] or 0
        
        total_keluar = models.detail_produksi.objects.filter(id_bahan=bahan).aggregate(total=Sum('jumlah_bahan_keluar'))['total'] or 0
        stok = total_masuk - total_keluar
        bahan_labels.append(bahan.nama_bahan)
        bahan_stok.append(stok)
        total_stok_bahan_pembantu += stok

    context = {
        'bahanobj': bahanobj,
        'produkobj': produkobj,
        'pemesananprodukobj':pemesananprodukobj,
        'produk_labels': json.dumps(produk_labels),
        'produk_stok': json.dumps(produk_stok),
        'bahan_labels': json.dumps(bahan_labels),
        'bahan_stok': json.dumps(bahan_stok),
        'total_stok_produk': total_stok_produk,
        'total_stok_bahan_pembantu': total_stok_bahan_pembantu,
    }
    return render(request, 'base/dashboard.html', context)


''' SUPPLIER '''
# READ SUPPLIER
@role_required(['ppic','finance'])
def read_supplier(request):
    supplierobj = models.supplier.objects.all().order_by('nama_supplier')
    # if not supplierobj.exists():
    #     messages.error(request, "Data supplier tidak ditemukan!")
        
    return render(request, 'supplier/read_supplier.html', {
        'supplierobj':supplierobj
    })
    
#CREATE SUPPLIER
@login_required(login_url='login')
@role_required(['ppic'])
def create_supplier(request):
    if request.method == 'GET':
        return render(request, 'supplier/create_supplier.html')
    
    else:
        nama_supplier = request.POST['nama_supplier']
        nomor_telepon_supplier = request.POST['nomor_telepon_supplier']
        alamat_supplier = request.POST['alamat_supplier']
        
        supplierobj = models.supplier.objects.filter(nama_supplier = nama_supplier)
        if supplierobj.exists():
            messages.error(request, 'Nama Supplier Sudah Ada')
            return redirect('create_supplier')
        else:
            nomor_telepon_supplier = request.POST['nomor_telepon_supplier']
            alamat_supplier = request.POST['alamat_supplier']
        models.supplier(
            nama_supplier = nama_supplier,
            nomor_telepon_supplier = nomor_telepon_supplier,
            alamat_supplier = alamat_supplier
        ).save()
        
        messages.success(request, "Data Supplier Berhasil Ditambahkan")
    return redirect('read_supplier')

#UPDATE SUPPLIER
@login_required(login_url='login')
@role_required(['ppic'])
def update_supplier(request, id):
    try:
        getsupplierobj = models.supplier.objects.get(id_supplier = id)
    except models.supplier.DoesNotExist:
        messages.error(request,"Supplier Tidak Ditemukan!")
        return redirect('read_supplier')
    
    if request.method == 'GET':
        return render(request, 'supplier/update_supplier.html', {
            'getsupplierobj':getsupplierobj
        })
    else:
        nama_supplier = request.POST["nama_supplier"]
        if models.supplier.objects.filter(nama_supplier = nama_supplier).exclude(id_supplier = id).exists():
            messages.error(request, "Nama Supplier Sudah Ada!")
            return render(request, 'supplier/update_supplier.html', {
                'getsupplierobj' : getsupplierobj
            })
        
        getsupplierobj.nama_supplier = nama_supplier
        getsupplierobj.nomor_telepon_supplier = request.POST["nomor_telepon_supplier"]
        getsupplierobj.alamat_supplier = request.POST["alamat_supplier"]
        getsupplierobj.save()
        messages.success(request, "Data Supplier Berhasil Diperbarui")
        return redirect('read_supplier')
    
#DELETE SUPPLIER
@login_required(login_url="login")
@role_required(['ppic'])
def delete_supplier(request ,id):
    getsupplierobj = models.supplier.objects.get(id_supplier = id)
    getsupplierobj.delete()
    messages.success(request, "Data Supplier Berhasil Dihapus")
    return redirect('read_supplier')

'''CUSTOMER'''
#READ CUSTOMER
@role_required(['ppic','finance'])
def read_customer(request):
    customerobj = models.customer.objects.all()
    # if not customerobj.exists():
    #     messages.error(request, "Data customer tidak ditemukan!")
        
    return render(request, 'customer/read_customer.html', {
        'customerobj':customerobj
    })
    
#CREATE CUSTOMER
@login_required(login_url='login')
@role_required(['ppic'])
def create_customer(request):
    if request.method == 'GET':
        return render(request, 'customer/create_customer.html')
    
    else:
        nama_customer = request.POST['nama_customer']
        nomor_telepon_customer = request.POST['nomor_telepon_customer']
        alamat_customer = request.POST['alamat_customer']
        
        customerobj = models.customer.objects.filter(nama_customer = nama_customer)
        if customerobj.exists():
            messages.error(request, 'Nama Customer Sudah Ada')
            return redirect('create_customer')
        else:
            nomor_telepon_customer = request.POST['nomor_telepon_customer']
            alamat_customer = request.POST['alamat_customer']
        models.customer(
            nama_customer = nama_customer,
            nomor_telepon_customer = nomor_telepon_customer,
            alamat_customer = alamat_customer
        ).save()
        
        messages.success(request, "Data Customer Berhasil Ditambahkan")
    return redirect('read_customer')

#UPDATE CUSTOMER
@login_required(login_url='login')
@role_required(['ppic'])
def update_customer(request, id):
    try:
        getcustomerobj = models.customer.objects.get(id_customer = id)
    except models.customer.DoesNotExist:
        messages.error(request,"Customer Tidak Ditemukan!")
        return redirect('read_customer')
    
    if request.method == 'GET':
        return render(request, 'customer/update_customer.html', {
            'getcustomerobj':getcustomerobj
        })
    else:
        nama_customer = request.POST["nama_customer"]
        if models.customer.objects.filter(nama_customer = nama_customer).exclude(id_customer = id).exists():
            messages.error(request, "Nama Customer Sudah Ada!")
            return render(request, 'customer/update_customer.html', {
                'getcustomerobj' : getcustomerobj
            })
        
        getcustomerobj.nama_customer = nama_customer
        getcustomerobj.nomor_telepon_customer = request.POST["nomor_telepon_customer"]
        getcustomerobj.alamat_customer = request.POST["alamat_customer"]
        getcustomerobj.save()
        messages.success(request, "Data Customer Berhasil Diperbarui")
        return redirect('read_customer')

#DELETE CUSTOMER
@login_required(login_url="login")
@role_required(['ppic'])
def delete_customer(request ,id):
    getcustomerobj = models.customer.objects.get(id_customer = id)
    getcustomerobj.delete()
    messages.success(request, "Data Customer Berhasil Dihapus")
    return redirect('read_customer')

'''BAHAN'''
#READ BAHAN
@login_required(login_url="login")
@role_required(['ppic','finance','produksi'])
def read_bahan(request):
    # --- Subquery: ambil SO terakhir per bahan (tanggal & qty fisik) ---
    last_so_bahan_qs = (
        models.detail_so_bahan.objects
        .filter(id_bahan=OuterRef('pk'))
        .order_by('-id_stok_opname__tanggal_stok_opname')
    )

    # Ambil bahan + annotate info SO terakhir
    bahan_list = list(
        models.bahan.objects
        .all()
        .order_by('jenis_bahan', 'nama_bahan')
        .annotate(
            so_terakhir_tanggal=Subquery(last_so_bahan_qs.values('id_stok_opname__tanggal_stok_opname')[:1]),
            so_terakhir_stok=Subquery(last_so_bahan_qs.values('stok_fisik_bahan')[:1]),
        )
    )

    # === MASUK dari pemesanan (roll/pcs) ===
    masuk_rows = (
        models.detail_pemesanan_bahan.objects
        .values('id_bahan')
        .annotate(total=Sum('jumlah_bahan_masuk'))
    )
    masuk_map = {r['id_bahan']: (r['total'] or 0) for r in masuk_rows}

    # === KELUAR untuk Bahan Baku (dipakai di produksi) ===
    keluar_rows = (
        models.detail_produksi.objects
        .values('id_bahan')
        .annotate(total=Sum('jumlah_bahan_keluar'))
    )
    keluar_map = {r['id_bahan']: (r['total'] or 0) for r in keluar_rows}

    # === Aturan pallet: mm per pallet & mm per roll untuk Bahan Pembantu ===
    keb_qs = models.kebutuhan_pallet.objects.values('id_bahan', 'kebutuhan', 'mm_per_roll')
    keb_map = {
        r['id_bahan']: (int(r['kebutuhan'] or 0), int(r['mm_per_roll'] or 0))
        for r in keb_qs
    }

    # Total pallet penuh kumulatif (AUTO + MANUAL)
    total_pallet = models.pallet_penuh.objects.aggregate(
        total=Sum('jumlah_pallet_penuh')
    )['total'] or 0

    def is_pallet_name(nm: str) -> bool:
        s = (nm or '').lower()
        return ('pallet' in s) or ('palet' in s)

    # === Hitung stok per bahan (SATU loop) ===
    for b in bahan_list:
        so_fisik = getattr(b, 'so_terakhir_stok', None)
        if so_fisik is not None:
            # Pakai stok fisik dari SO terakhir
            b.stok = int(so_fisik or 0)
        else:
            # Fallback: hitung stok sistem kumulatif
            masuk = int(masuk_map.get(b.id_bahan, 0) or 0)
            jenis = (b.jenis_bahan or '').lower()
            nama  = (b.nama_bahan or '').lower()

            if 'pembantu' in jenis:
                if is_pallet_name(nama):
                    # Pallet: keluar = total pallet penuh
                    keluar = int(total_pallet)
                    b.stok = masuk - keluar
                elif b.id_bahan in keb_map:
                    # Wrapping (roll): keluar = (per_pallet_mm * total_pallet) // mm_per_roll
                    per_pallet_mm, mm_per_roll = keb_map[b.id_bahan]
                    if per_pallet_mm > 0 and mm_per_roll > 0 and total_pallet > 0:
                        total_mm  = per_pallet_mm * int(total_pallet)
                        used_roll = total_mm // mm_per_roll
                        sisa_mm   = total_mm %  mm_per_roll
                    else:
                        total_mm = used_roll = sisa_mm = 0
                    b.stok = masuk - used_roll
                    # info opsional untuk UI
                    b.konsumsi_mm_total = total_mm
                    b.sisa_mm_terbuka   = sisa_mm
                    b.mm_per_roll       = mm_per_roll
                else:
                    # Pembantu lain yang tidak terdaftar kebutuhan → anggap tidak dipakai (atau handle sendiri)
                    b.stok = masuk
            else:
                # Bahan Baku: keluar dari produksi
                keluar = int(keluar_map.get(b.id_bahan, 0) or 0)
                b.stok = masuk - keluar

    is_ppic = request.user.groups.filter(name='ppic').exists()
    return render(request, 'bahan/read_bahan.html', {
        'bahanobj': bahan_list,
        'is_ppic': is_ppic,
    })

    
#CREATE BAHAN
@login_required(login_url='login')
@role_required(['ppic'])
def create_bahan(request):
    if request.method == 'GET':
        return render(request, 'bahan/create_bahan.html')
    
    else:
        nama_bahan = request.POST['nama_bahan']
        jenis_bahan = request.POST['jenis_bahan']
        
        bahanobj = models.bahan.objects.filter(nama_bahan = nama_bahan)
        if bahanobj.exists():
            messages.error(request, 'Nama bahan Sudah Ada')
            return redirect('create_bahan')
        else:
            jenis_bahan = request.POST['jenis_bahan']
        models.bahan(
            nama_bahan = nama_bahan,
            jenis_bahan = jenis_bahan,
        ).save()
        
        messages.success(request, "Data Bahan Berhasil Ditambahkan")
    return redirect('read_bahan')

#UPDATE BAHAN
@login_required(login_url='login')
@role_required(['ppic'])
def update_bahan(request, id):
    try:
        getbahanobj = models.bahan.objects.get(id_bahan = id)
    except models.bahan.DoesNotExist:
        messages.error(request,"Bahan Tidak Ditemukan!")
        return redirect('read_bahan')
    
    if request.method == 'GET':
        return render(request, 'bahan/update_bahan.html', {
            'getbahanobj':getbahanobj
        })
    else:
        nama_bahan = request.POST["nama_bahan"]
        if models.bahan.objects.filter(nama_bahan = nama_bahan).exclude(id_bahan = id).exists():
            messages.error(request, "Nama Bahan Sudah Ada!")
            return render(request, 'bahan/update_bahan.html', {
                'getbahanobj' : getbahanobj
            })
        
        getbahanobj.nama_bahan = nama_bahan
        getbahanobj.jenis_bahan = request.POST["jenis_bahan"]
        getbahanobj.save()
        messages.success(request, "Data Bahan Berhasil Diperbarui")
        return redirect('read_bahan')

#DELETE BAHAN
@login_required(login_url="login")
@role_required(['ppic'])
def delete_bahan(request ,id):
    getbahanobj = models.bahan.objects.get(id_bahan = id)
    getbahanobj.delete()
    messages.success(request, "Data Bahan Berhasil Dihapus")
    return redirect('read_bahan')

'''PRODUK'''
#READ PRODUK
@login_required(login_url='login')
@role_required(['ppic','finance','produksi','qc'])
def read_produk(request):
    # --- Subquery: ambil SO terakhir per produk (tanggal & qty fisik) ---
    last_so_qs = (
        models.detail_so_produk.objects
        .filter(id_produk=OuterRef('pk'))
        .order_by('-id_stok_opname__tanggal_stok_opname')
    )
    produk_list = list(
        models.produk.objects
        .all()
        .order_by('nama_produk')
        .annotate(
            so_terakhir_tanggal=Subquery(last_so_qs.values('id_stok_opname__tanggal_stok_opname')[:1]),
            so_terakhir_stok=Subquery(last_so_qs.values('stok_fisik_produk')[:1]),
        )
    )

    # Klasifikasi produk EOE/Bottom End 
    eoe_q = (
        Q(nama_produk__iregex=r'(^|[^A-Za-z0-9])EOE([^A-Za-z0-9]|$)') |
        Q(nama_produk__iregex=r'\bBottom\s+End\b')
    )
    eoe_ids = set(
        models.produk.objects
        .filter(eoe_q)
        .values_list('id_produk', flat=True)
    )

    #  MASUK via PRODUKSI (untuk non-EOE) 
    masuk_prod_rows = (
        models.detail_produksi.objects
        .exclude(id_produk__in=eoe_ids)
        .values('id_produk')
        .annotate(total=Sum('jumlah_produk'))
    )
    masuk_prod_map = {r['id_produk']: (r['total'] or 0) for r in masuk_prod_rows}

    # MASUK via PEMESANAN (untuk EOE)  
    pemesanan_detail_model = models.detail_pemesanan_produk 

    masuk_pesan_rows = (
        pemesanan_detail_model.objects
        .filter(id_produk__in=eoe_ids)
        .values('id_produk')
        .annotate(total=Sum('jumlah_produk_masuk'))
    )
    masuk_pesan_map = {r['id_produk']: (r['total'] or 0) for r in masuk_pesan_rows}

    # KELUAR via PENGIRIMAN (untuk semua produk)
    keluar_rows = (
        models.detail_pengiriman.objects
        .values('id_produk')
        .annotate(total=Sum('jumlah_produk_dikirim'))
    )
    keluar_map = {r['id_produk']: (r['total'] or 0) for r in keluar_rows}

    # Hitung STOK per produk
    for p in produk_list:
        if p.so_terakhir_stok is not None:
            p.stok = int(p.so_terakhir_stok or 0)
        else:
            if p.id_produk in eoe_ids:
                masuk = masuk_pesan_map.get(p.id_produk, 0)  
            else:
                masuk = masuk_prod_map.get(p.id_produk, 0)  

            keluar = keluar_map.get(p.id_produk, 0)
            p.stok = (masuk or 0) - (keluar or 0)
            
        # pastikan safety_stock ada (default 0 kalau null)
        p_safety = getattr(p, 'safety_stock', 0) or 0
        p.safety_ok = (p.stok or 0) >= p_safety
        p.status_label = "Stok Aman" if p.safety_ok else "Stok Tidak Aman"
        p.safety_gap = (p.stok or 0) - p_safety  # kalau negatif berarti kurang

    return render(request, 'produk/read_produk.html', {
        'produkobj': produk_list,
    })

        

#CREATE PRODUK
@login_required(login_url='login')
@role_required(['ppic'])
def create_produk(request):
    if request.method == 'GET':
        return render(request, 'produk/create_produk.html')
    
    else:
        nama_produk = request.POST['nama_produk']
        jenis_produk = request.POST['jenis_produk']
        kapasitas_pallet = request.POST['kapasitas_pallet']
        safety_stock = request.POST['safety_stock']
        
        produkobj = models.produk.objects.filter(nama_produk = nama_produk)
        if produkobj.exists():
            messages.error(request, 'Nama Produk Sudah Ada')
            return redirect('create_produk')
        else:
            jenis_produk = request.POST['jenis_produk']
            kapasitas_pallet = request.POST['kapasitas_pallet']
            safety_stock = request.POST['safety_stock']
        models.produk(
            nama_produk = nama_produk,
            jenis_produk = jenis_produk,
            kapasitas_pallet = kapasitas_pallet,
            safety_stock = safety_stock,
        ).save()
        
        messages.success(request, "Data Produk Berhasil Ditambahkan")
    return redirect('read_produk')

#UPDATE PRODUK
@login_required(login_url='login')
@role_required(['ppic'])
def update_produk(request, id):
    try:
        getprodukobj = models.produk.objects.get(id_produk = id)
    except models.produk.DoesNotExist:
        messages.error(request,"Produk Tidak Ditemukan!")
        return redirect('read_produk')
    
    if request.method == 'GET':
        return render(request, 'produk/update_produk.html', {
            'getprodukobj':getprodukobj
        })
    else:
        nama_produk = request.POST["nama_produk"]
        if models.produk.objects.filter(nama_produk = nama_produk).exclude(id_produk = id).exists():
            messages.error(request, "Nama Produk Sudah Ada!")
            return render(request, 'produk/update_produk.html', {
                'getprodukobj' : getprodukobj
            })
        
        getprodukobj.nama_produk = nama_produk
        getprodukobj.jenis_produk = request.POST["jenis_produk"]
        getprodukobj.kapasitas_pallet = request.POST["kapasitas_pallet"]
        getprodukobj.safety_stock = request.POST["safety_stock"]
        getprodukobj.save()
        messages.success(request, "Data Produk Berhasil Diperbarui")
        return redirect('read_produk')

#DELETE PRODUK
@login_required(login_url="login")
@role_required(['ppic'])
def delete_produk(request ,id):
    getprodukobj = models.produk.objects.get(id_produk = id)
    getprodukobj.delete()
    messages.success(request, "Data Produk Berhasil Dihapus")
    return redirect('read_produk')

'''PEMESANAN'''
#READ PEMESANAN
@login_required(login_url='login')
@role_required(['ppic','finance'])
def read_pemesanan(request):
    pemesananobj = (models.pemesanan.objects
          .select_related('id_supplier')
          .prefetch_related('detail_pemesanan_bahan_set','detail_pemesanan_produk_set')
          .order_by('tanggal_pemesanan','id_pemesanan'))
    rows = [{
        'id': p.id_pemesanan,
        'tanggal': p.tanggal_pemesanan,
        'supplier': p.id_supplier.nama_supplier,
        'n_bahan': p.detail_pemesanan_bahan_set.count(),
        'n_produk': p.detail_pemesanan_produk_set.count(),
    } for p in pemesananobj]
    is_ppic = request.user.groups.filter(name='ppic').exists()
    return render(request, 'pemesanan/read_pemesanan.html', {'rows': rows, 'is_ppic': is_ppic})

@role_required(['ppic','finance'])
def read_detail_pemesanan_bahan(request, id_pemesanan):
    p = get_object_or_404(
        models.pemesanan.objects.select_related('id_supplier')
        .prefetch_related('detail_pemesanan_bahan_set__id_bahan'),
        id_pemesanan=id_pemesanan
    )
    is_ppic = request.user.groups.filter(name='ppic').exists()
    return render(request, 'pemesanan/read_detail_pemesanan_bahan.html', {
        'p': p, 'details': p.detail_pemesanan_bahan_set.all(), 'is_ppic': is_ppic
    })

@role_required(['ppic','finance'])
def read_detail_pemesanan_produk(request, id_pemesanan):
    p = get_object_or_404(
        models.pemesanan.objects.select_related('id_supplier')
        .prefetch_related('detail_pemesanan_produk_set__id_produk'),
        id_pemesanan=id_pemesanan
    )
    is_ppic = request.user.groups.filter(name='ppic').exists()
    return render(request, 'pemesanan/read_detail_pemesanan_produk.html', {
        'p': p, 'details': p.detail_pemesanan_produk_set.all(), 'is_ppic': is_ppic
    })


@role_required(['ppic','finance'])
def read_detail_bahan(request):
    qs = (models.detail_pemesanan_bahan.objects
          .select_related('id_pemesanan__id_supplier','id_bahan')
          .order_by('id_pemesanan__tanggal_pemesanan','id_detail_pemesanan'))

    # filter opsional
    tmin = request.GET.get('tmin'); tmax = request.GET.get('tmax')
    supplier = request.GET.get('supplier'); bahan = request.GET.get('bahan')
    if tmin: qs = qs.filter(id_pemesanan__tanggal_pemesanan__gte=tmin)
    if tmax: qs = qs.filter(id_pemesanan__tanggal_pemesanan__lte=tmax)
    if supplier: qs = qs.filter(id_pemesanan__id_supplier__id_supplier=supplier)
    if bahan: qs = qs.filter(id_bahan__id_bahan=bahan)

    page_obj = Paginator(qs, 25).get_page(request.GET.get('page'))
    return render(request, 'pemesanan/read_detail_bahan.html', {
        'page_obj': page_obj,
        'supplierobj': models.supplier.objects.all().order_by('nama_supplier'),
        'bahanobj': models.bahan.objects.all().order_by('nama_bahan'),
        'tmin': tmin, 'tmax': tmax, 'supplier_sel': supplier, 'bahan_sel': bahan,
    })

@login_required(login_url="login")
@role_required(['ppic','finance'])
def read_detail_produk(request):
    qs = (models.detail_pemesanan_produk.objects
          .select_related('id_pemesanan__id_supplier','id_produk')
          .order_by('id_pemesanan__tanggal_pemesanan','id_detail_pemesanan'))

    # ❗ hanya produk EOE & Bottom End
    eoe_q = (
        Q(nama_produk__iregex=r'(^|[^A-Za-z0-9])EOE([^A-Za-z0-9]|$)') |
        Q(nama_produk__iregex=r'\bBottom\s+End\b')
    )

    tmin = request.GET.get('tmin'); tmax = request.GET.get('tmax')
    supplier = request.GET.get('supplier'); produk = request.GET.get('produk')
    if tmin: qs = qs.filter(id_pemesanan__tanggal_pemesanan__gte=tmin)
    if tmax: qs = qs.filter(id_pemesanan__tanggal_pemesanan__lte=tmax)
    if supplier: qs = qs.filter(id_pemesanan__id_supplier__id_supplier=supplier)
    if produk: qs = qs.filter(id_produk__id_produk=produk)

    page_obj = Paginator(qs, 25).get_page(request.GET.get('page'))
    return render(request, 'pemesanan/read_detail_produk.html', {
        'page_obj': page_obj,
        'supplierobj': models.supplier.objects.all().order_by('nama_supplier'),
        'produkobj': models.produk.objects.filter(eoe_q).order_by('nama_produk'),
        'tmin': tmin, 'tmax': tmax, 'supplier_sel': supplier, 'produk_sel': produk,
    })


    
#CREATE PEMESANAN
@login_required(login_url='login')
@role_required(['ppic'])
def create_pemesanan(request):
    supplierobj = models.supplier.objects.all().order_by('nama_supplier')
    bahanobj    = models.bahan.objects.all().order_by('nama_bahan')
    
    # ❗ hanya produk EOE & Bottom End
    eoe_q = (
        Q(nama_produk__iregex=r'(^|[^A-Za-z0-9])EOE([^A-Za-z0-9]|$)') |
        Q(nama_produk__iregex=r'\bBottom\s+End\b')
    )
    produkobj   = models.produk.objects.filter(eoe_q).order_by('nama_produk')
    
    if request.method == 'GET':
        return render(request, 'pemesanan/create_pemesanan.html', {
            'supplierobj': supplierobj, 'bahanobj': bahanobj, 'produkobj': produkobj
        })

    id_supplier = request.POST.get('nama_supplier')
    tanggal_pemesanan     = request.POST.get('tanggal_pemesanan')

    if not (id_supplier and tanggal_pemesanan):
        messages.error(request, "Tanggal dan supplier wajib diisi.")
        return render(request, 'pemesanan/create_pemesanan.html', {
            'supplierobj': supplierobj, 'bahanobj': bahanobj, 'produkobj': produkobj
        })

    try:
        tanggal  = datetime.strptime(tanggal_pemesanan, '%Y-%m-%d').date()
        supplier = models.supplier.objects.get(id_supplier=id_supplier)
    except ValueError:
        messages.error(request, "Format tanggal tidak valid.")
        return render(request, 'pemesanan/create_pemesanan.html', {
            'supplierobj': supplierobj, 'bahanobj': bahanobj, 'produkobj': produkobj
        })
    except models.supplier.DoesNotExist:
        messages.error(request, "Supplier tidak ditemukan.")
        return render(request, 'pemesanan/create_pemesanan.html', {
            'supplierobj': supplierobj, 'bahanobj': bahanobj, 'produkobj': produkobj
        })

    bahan_ids   = request.POST.getlist('bahan_id[]')
    bahan_qtys  = request.POST.getlist('bahan_qty[]')
    produk_ids  = request.POST.getlist('produk_id[]')
    produk_qtys = request.POST.getlist('produk_qty[]')

    if not any(bahan_ids) and not any(produk_ids):
        messages.error(request, "Minimal isi salah satu detail (bahan atau produk).")
        return render(request, 'pemesanan/create_pemesanan.html', {
            'supplierobj': supplierobj, 'bahanobj': bahanobj, 'produkobj': produkobj
        })

    with transaction.atomic():
        p = models.pemesanan.objects.create(id_supplier=supplier, tanggal_pemesanan=tanggal)

        for bid, q in zip(bahan_ids, bahan_qtys):
            if not bid or not q: continue
            qty = int(q)
            if qty <= 0: continue
            try:
                b = models.bahan.objects.get(id_bahan=bid)
            except models.bahan.DoesNotExist:
                continue
            models.detail_pemesanan_bahan.objects.create(
                id_pemesanan=p, id_bahan=b, jumlah_bahan_masuk=qty
            )

        for pid, q in zip(produk_ids, produk_qtys):
            if not pid or not q: continue
            qty = int(q)
            if qty <= 0: continue
            try:
                pr = models.produk.objects.get(id_produk=pid)
            except models.produk.DoesNotExist:
                continue
            models.detail_pemesanan_produk.objects.create(
                id_pemesanan=p, id_produk=pr, jumlah_produk_masuk=qty
            )

            # di dalam loop for pid, q in zip(produk_ids, produk_qtys):
            dp = models.detail_pemesanan_produk.objects.create(
                id_pemesanan=p, id_produk=pr, jumlah_produk_masuk=qty
            )
            # panggil setelah create
            _wrap_eoe_from_pemesanan(dp)
            
    messages.success(request, "Data Pemesanan Berhasil Ditambahkan")
    return redirect('read_pemesanan')

#UPDATE PEMESANAN
@login_required(login_url='login')
@role_required(['ppic'])
def update_pemesanan(request, id):
    detail = get_object_or_404(models.pemesanan, id_pemesanan=id)

    supplierobj = models.supplier.objects.all().order_by('nama_supplier')
    bahanobj    = models.bahan.objects.all().order_by('nama_bahan')

    if request.method == "POST":
        id_supplier = request.POST.get("supplier")
        id_bahan    = request.POST.get("nama_bahan")
        qty_str     = request.POST.get("jumlah_bahan_masuk")
        tanggal_pemesanan     = request.POST.get("tanggal_pemesanan")

        # Validasi sederhana
        if not (id_supplier and id_bahan and qty_str and tanggal_pemesanan):
            messages.error(request, "Semua field wajib diisi.")
            return render(request, 'pemesanan/update_pemesanan.html', {
                'detail': detail,
                'supplierobj': supplierobj,
                'bahanobj': bahanobj,
            })

        try:
            qty = int(qty_str)
            if qty <= 0:
                raise ValueError
        except ValueError:
            messages.error(request, "Kuantitas harus berupa angka > 0.")
            return render(request, 'pemesanan/update_pemesanan.html', {
                'detail': detail,
                'supplierobj': supplierobj,
                'bahanobj': bahanobj,
            })

        try:
            tanggal = datetime.strptime(tanggal_pemesanan, '%Y-%m-%d').date()
        except ValueError:
            messages.error(request, "Format tanggal tidak valid.")
            return render(request, 'pemesanan/update_pemesanan.html', {
                'detail': detail,
                'supplierobj': supplierobj,
                'bahanobj': bahanobj,
            })

        try:
            supplier = models.supplier.objects.get(id_supplier=id_supplier)
            bahan    = models.bahan.objects.get(id_bahan=id_bahan)
        except (models.supplier.DoesNotExist, models.bahan.DoesNotExist):
            messages.error(request, "Supplier atau bahan tidak ditemukan.")
            return render(request, 'pemesanan/update_pemesanan.html', {
                'detail': detail,
                'supplierobj': supplierobj,
                'bahanobj': bahanobj,
            })

        # Simpan perubahan (parent dulu, lalu detail)
        with transaction.atomic():
            parent = detail.id_pemesanan
            parent.id_supplier = supplier
            parent.tanggal_pemesanan = tanggal
            parent.save()

            detail.id_bahan = bahan
            detail.jumlah_bahan_masuk = qty
            detail.save()

        messages.success(request, "Data pemesanan berhasil diperbarui!")
        return redirect('read_pemesanan')

    # GET: render form
    return render(request, 'pemesanan/update_pemesanan.html', {
        'detail': detail,
        'supplierobj': supplierobj,
        'bahanobj': bahanobj,
    })

@login_required(login_url='login')
@role_required(['ppic'])
def update_detail_pemesanan_bahan(request, id_detail):
    detail = get_object_or_404(models.detail_pemesanan_bahan, id_detail_pemesanan=id_detail)
    bahanobj = models.bahan.objects.all().order_by('nama_bahan')

    if request.method == 'POST':
        bahan_id = request.POST.get("nama_bahan")
        qty_str  = request.POST.get("jumlah_bahan_masuk")
        # validasi...
        detail.id_bahan = models.bahan.objects.get(id_bahan=bahan_id)
        detail.jumlah_bahan_masuk = int(qty_str)
        detail.save()
        messages.success(request, "Detail bahan diperbarui.")
        return redirect('read_detail_pemesanan_bahan', id_pemesanan=detail.id_pemesanan.id_pemesanan)

    return render(request, 'pemesanan/update_detail_pemesanan_bahan.html', {
        'detail': detail, 'bahanobj': bahanobj
    })


@login_required(login_url='login')
@role_required(['ppic'])
def update_detail_pemesanan_produk(request, id_detail):
    detail = get_object_or_404(models.detail_pemesanan_produk, id_detail_pemesanan=id_detail)
    parent = detail.id_pemesanan
    
    # ❗ hanya produk EOE & Bottom End
    eoe_q = (
        Q(nama_produk__iregex=r'(^|[^A-Za-z0-9])EOE([^A-Za-z0-9]|$)') |
        Q(nama_produk__iregex=r'\bBottom\s+End\b')
    )
    produkobj   = models.produk.objects.filter(eoe_q).order_by('nama_produk')

    if request.method == 'POST':
        produk_id = request.POST.get("nama_produk")
        qty_str   = request.POST.get("jumlah_produk_masuk")

        if not (produk_id and qty_str):
            messages.error(request, "Semua field wajib diisi.")
            return render(request, 'pemesanan/update_detail_pemesanan_produk.html', {
                'detail': detail, 'produkobj': produkobj
            })
        try:
            qty = int(qty_str)
            if qty <= 0: raise ValueError
        except ValueError:
            messages.error(request, "Kuantitas harus berupa angka > 0.")
            return render(request, 'pemesanan/update_detail_pemesanan_produk.html', {
                'detail': detail, 'produkobj': produkobj
            })
        try:
            produk = models.produk.objects.get(id_produk=produk_id)
        except models.produk.DoesNotExist:
            messages.error(request, "Produk tidak ditemukan.")
            return render(request, 'pemesanan/update_detail_pemesanan_produk.html', {
                'detail': detail, 'produkobj': produkobj
            })

        detail.id_produk = produk
        detail.jumlah_produk_masuk = qty
        detail.save()
        
        # Hanya untuk produk EOE/Bottom End, cek sama seperti di _wrap_eoe_from_pemesanan
        if models.pallet_penuh.objects.filter(id_detail_pemesanan_produk=detail).exists():
            models.pallet_penuh.objects.filter(id_detail_pemesanan_produk=detail).delete()
        # buat ulang mengacu qty terbaru
        _wrap_eoe_from_pemesanan(detail)

        messages.success(request, "Detail produk diperbarui.")
        return redirect('read_detail_pemesanan_produk', id_pemesanan=parent.id_pemesanan)

    return render(request, 'pemesanan/update_detail_pemesanan_produk.html', {
        'detail': detail, 'produkobj': produkobj
    })


#DELETE PEMESANAN
# Hapus seluruh dokumen PEMESANAN (parent + semua detail)
@login_required(login_url='login')
@role_required(['ppic'])
def delete_pemesanan(request, id_pemesanan):
    if request.method != 'POST':
        messages.error(request, "Metode tidak diizinkan.")
        return redirect('read_pemesanan')

    p = get_object_or_404(models.pemesanan, id_pemesanan=id_pemesanan)
    p.delete()  # CASCADE ke detail
    messages.success(request, "Pemesanan beserta seluruh detail berhasil dihapus.")
    return redirect('read_pemesanan')

# Hapus satu DETAIL BAHAN; kalau habis semua detail (bahan+produk), hapus parent
@login_required(login_url='login')
@role_required(['ppic'])
def delete_detail_pemesanan_bahan(request, id_detail):
    if request.method != 'POST':
        messages.error(request, "Metode tidak diizinkan.")
        return redirect('read_pemesanan')

    d = get_object_or_404(models.detail_pemesanan_bahan, id_detail_pemesanan=id_detail)
    parent = d.id_pemesanan

    with transaction.atomic():
        d.delete()
        if parent.detail_pemesanan_bahan_set.count() + parent.detail_pemesanan_produk_set.count() == 0:
            parent.delete()
            messages.success(request, "Detail terakhir dihapus; pemesanan ikut dihapus.")
            return redirect('read_pemesanan')

    messages.success(request, "Detail bahan berhasil dihapus.")
    return redirect('read_pemesanan')  # atau arahkan ke halaman detail dokumen jika mau


# Hapus satu DETAIL PRODUK; kalau habis semua detail (bahan+produk), hapus parent
@login_required(login_url='login')
@role_required(['ppic'])
def delete_detail_pemesanan_produk(request, id_detail):
    if request.method != 'POST':
        messages.error(request, "Metode tidak diizinkan.")
        return redirect('read_pemesanan')

    d = get_object_or_404(models.detail_pemesanan_produk, id_detail_pemesanan=id_detail)
    parent = d.id_pemesanan

    with transaction.atomic():
        d.delete()
        if parent.detail_pemesanan_bahan_set.count() + parent.detail_pemesanan_produk_set.count() == 0:
            parent.delete()
            messages.success(request, "Detail terakhir dihapus; pemesanan ikut dihapus.")
            return redirect('read_pemesanan')

    messages.success(request, "Detail produk berhasil dihapus.")
    return redirect('read_pemesanan')  # atau ke halaman detail dokumen


'''PRODUKSI''' 
@login_required(login_url="login")
@role_required(['ppic', 'finance', 'produksi','qc'])
def read_produksi(request):
  
    tmin = request.GET.get('tmin')
    tmax = request.GET.get('tmax')
    produk_sel = request.GET.get('produk') 

    qs_parent = models.produksi.objects.all()

    if tmin:
        qs_parent = qs_parent.filter(tanggal_produksi__gte=tmin)
    if tmax:
        qs_parent = qs_parent.filter(tanggal_produksi__lte=tmax)

    detail_qs = (
        models.detail_produksi.objects
        .select_related('id_produk', 'id_bahan')
        .order_by('id_produk__nama_produk', 'id_bahan__nama_bahan')
    )

    if produk_sel:
        qs_parent = qs_parent.filter(
            detail_produksi__id_produk__id_produk=produk_sel
        ).distinct()
        detail_qs = detail_qs.filter(id_produk__id_produk=produk_sel)

    produksiobj = (
        qs_parent
        .prefetch_related(Prefetch('detail_produksi_set', queryset=detail_qs))
        .order_by('tanggal_produksi', 'id_produksi')
    )

    is_ppic = request.user.is_superuser or _in_group(request.user, 'ppic')
    is_produksi = _in_group(request.user, 'produksi')
    is_qc = _in_group(request.user, 'qc')

    return render(request, 'produksi/read_produksi.html', {
        'produksiobj': produksiobj,
        'is_ppic': is_ppic,
        'is_produksi': is_produksi,
        'is_qc': is_qc,
        # form filter
        'produkobj': models.produk.objects.all().order_by('nama_produk'),
        'tmin': tmin, 'tmax': tmax, 'produk_sel': produk_sel,
    })

#CREATE PRODUKSI
@login_required(login_url='login')
@role_required(['produksi', 'ppic'])
def create_produksi(request):
    produkobj = models.produk.objects.all()
    bahanobj = models.bahan.objects.all()

    # hanya produk non-EOE & non-Bottom End
    eoe_q = (
        Q(nama_produk__iregex=r'(^|[^A-Za-z0-9])EOE([^A-Za-z0-9]|$)') |
        Q(nama_produk__iregex=r'\bBottom\s+End\b')
    )
    
    produkobj = models.produk.objects.exclude(eoe_q).order_by('nama_produk')
    bahanobj = models.bahan.objects.filter(jenis_bahan='Bahan Baku').order_by('nama_bahan')

    if request.method == 'GET':
        return render(request, 'produksi/create_produksi.html', {
            'produkobj': produkobj,
            'bahanobj': bahanobj,
        })

    # POST
    is_ppic = request.user.is_superuser or _in_group(request.user, 'ppic')
    is_qc = _in_group(request.user, 'qc')

    tanggal_produksi = request.POST.get('tanggal_produksi')

    nama_produk_list = request.POST.getlist('nama_produk')
    nama_bahan_list = request.POST.getlist('nama_bahan')
    jumlah_produk_list = request.POST.getlist('jumlah_produk')
    jumlah_reject_list = request.POST.getlist('jumlah_reject')
    jumlah_fg_list = request.POST.getlist('jumlah_fg')
    jumlah_bahan_keluar_list = request.POST.getlist('jumlah_bahan_keluar')

    with transaction.atomic():
        produksi = models.produksi.objects.create(tanggal_produksi=tanggal_produksi)

    for prod_id, bahan_id, qty_prod, qty_reject, qty_fg, qty_bhn in zip(
        nama_produk_list, nama_bahan_list,
        jumlah_produk_list, jumlah_reject_list, jumlah_fg_list,
        jumlah_bahan_keluar_list,
    ):
        # Produksi tidak boleh set reject/FG saat create; ppic qc boleh
        if is_ppic or is_qc:
            jr = int(qty_reject or 0)
            fg = int(qty_fg     or 0)
        else:
            jr = 0
            fg = 0

        detail = models.detail_produksi.objects.create(
            id_produksi=produksi,
            id_produk=models.produk.objects.get(id_produk=prod_id),
            id_bahan=models.bahan.objects.get(id_bahan=bahan_id),
            jumlah_produk=int(qty_prod or 0),
            jumlah_reject=jr,
            jumlah_fg=fg,
            jumlah_bahan_keluar=int(qty_bhn or 0),
        )

        # === AUTO WRAP berdasarkan kapasitas pallet ===
        _auto_wrap_dari_produksi(detail)

    messages.success(request, "Data Produksi Berhasil Ditambahkan.")
    return redirect('read_produksi')

    
#UPDATE PRODUKSI
@login_required(login_url='login')
@role_required(['produksi', 'ppic'])
def update_produksi(request, id):
    getdetailobj = get_object_or_404(models.detail_produksi, id_detail_produksi=id)
    produkobj = models.produk.objects.all()
    bahanobj = models.bahan.objects.all()

    if request.method == "GET":
        tanggal_produksi = getdetailobj.id_produksi.tanggal_produksi.strftime('%Y-%m-%d')
        return render(request, 'produksi/update_produksi.html', {
            'getdetailobj': getdetailobj,
            'bahanobj': bahanobj,
            'produkobj': produkobj,
            'tanggal_produksi': tanggal_produksi,
        })

    # POST (hanya field produksi)
    getdetailobj.id_produksi.tanggal_produksi = request.POST.get("tanggal_produksi")
    getdetailobj.id_produk = models.produk.objects.get(id_produk=request.POST.get('nama_produk'))
    getdetailobj.id_bahan = models.bahan.objects.get(id_bahan=request.POST.get("nama_bahan"))
    getdetailobj.jumlah_produk = int(request.POST.get("jumlah_produk") or 0)
    getdetailobj.jumlah_bahan_keluar = int(request.POST.get("jumlah_bahan_keluar") or 0)

    # Catatan: reject & FG TIDAK disentuh di sini
    with transaction.atomic():
        getdetailobj.id_produksi.save()
        getdetailobj.save()

    messages.success(request, "Data produksi berhasil diperbarui.")
    return redirect('read_produksi')

@login_required(login_url='login')
@role_required(['qc', 'ppic'])
def update_qc_produksi(request, id):
    d = get_object_or_404(models.detail_produksi, id_detail_produksi=id)

    if request.method == "GET":
        return render(request, 'produksi/update_qc_produksi.html', {'getdetailobj': d})

    # POST
    try:
        jr = int(request.POST.get("jumlah_reject") or 0)
        fg = int(request.POST.get("jumlah_fg") or 0)
    except (TypeError, ValueError):
        messages.error(request, "Input tidak valid. Gunakan angka bulat ≥ 0.")
        d.jumlah_reject = request.POST.get("jumlah_reject") or 0
        d.jumlah_fg = request.POST.get("jumlah_fg") or 0
        return render(request, 'produksi/update_qc_produksi.html', {'getdetailobj': d})

    if jr < 0 or fg < 0:
        messages.error(request, "Jumlah reject/FG tidak boleh negatif.")
        d.jumlah_reject = jr
        d.jumlah_fg = fg
        return render(request, 'produksi/update_qc_produksi.html', {'getdetailobj': d})

    d.jumlah_reject = jr
    d.jumlah_fg = fg
    d.save()

    messages.success(request, "Data QC (reject & finished goods) berhasil diperbarui.")
    return redirect('read_produksi')
    
@login_required(login_url='login')
@role_required(['qc', 'ppic'])
@require_POST
def set_qc_status(request, id_detail):
    d = get_object_or_404(models.detail_produksi, id_detail_produksi=id_detail)
    status = (request.POST.get('status') or '').strip().lower()

    valid_values = {'belum', 'sedang', 'sudah'}
    if status not in valid_values:
        messages.error(request, "Status QC tidak dikenal.")
        return redirect('read_produksi')

    # Jika mau set ke "sudah", pastikan equality terpenuhi
    if status == 'sudah':
        jr = int(d.jumlah_reject or 0)
        fg = int(d.jumlah_fg or 0)
        target = int(d.jumlah_produk or 0)
        if (jr + fg) != target:
            messages.error(
                request,
                f"Gagal set status 'Sudah diperiksa'. "
                f"Total Reject + FG = {jr + fg} tidak sama dengan Jumlah Produk ({target})."
            )
            return redirect('read_produksi')

    # Lolos: update status + (opsional) audit
    d.status_qc = status
    if hasattr(d, 'qc_updated_at'):
        d.qc_updated_at = timezone.now()
    if hasattr(d, 'qc_updated_by'):
        d.qc_updated_by = request.user
    d.save()

    label = dict(models.detail_produksi.STATUS_QC_CHOICES).get(status, status.title())
    messages.success(request, f"Status QC diperbarui menjadi: {label}.")
    return redirect('read_produksi')    


#DELETE PRODUKSI
@login_required(login_url='login')
@role_required(['produksi', 'ppic'])
def delete_produksi(request, id_produksi=None, id_detail=None):
    # A) Hapus seluruh PRODUKSI (cascade detail)
    if id_produksi is not None:
        obj = get_object_or_404(models.produksi, id_produksi=id_produksi)
        obj.delete()
        messages.success(request, "Produksi beserta seluruh detail berhasil dihapus.")
        return redirect('read_produksi')

    # B) Hapus satu DETAIL; jika itu terakhir, parent ikut terhapus
    if id_detail is not None:
        detail = get_object_or_404(models.detail_produksi, id_detail_produksi=id_detail)
        parent = detail.id_produksi

        with transaction.atomic():
            if parent.detail_produksi_set.count() <= 1:
                parent.delete()
                messages.success(request, "Detail terakhir dihapus; produksi ikut dihapus.")
            else:
                detail.delete()
                messages.success(request, "Detail produksi berhasil dihapus.")
        return redirect('read_produksi')

    messages.error(request, "Parameter hapus tidak valid.")
    return redirect('read_produksi')


'''PENGIRIMAN'''
#READ PENGIRIMAN
def read_pengiriman(request):
    # --- ambil parameter filter ---
    tmin = request.GET.get('tmin')
    tmax = request.GET.get('tmax')
    produk_sel = request.GET.get('produk')    
    customer_sel = request.GET.get('customer')  

    # --- base queryset parent ---
    qs_parent = models.pengiriman.objects.all().select_related('id_customer')

    # filter tanggal (opsional)
    if tmin:
        qs_parent = qs_parent.filter(tanggal_pengiriman__gte=tmin)
    if tmax:
        qs_parent = qs_parent.filter(tanggal_pengiriman__lte=tmax)

    # --- queryset detail untuk prefetch (bisa ikut difilter) ---
    detail_qs = (
        models.detail_pengiriman.objects
        .select_related('id_produk', 'id_pengiriman__id_customer')
        .order_by('id_produk__nama_produk')
    )

    # filter parent by produk
    if produk_sel:
        qs_parent = qs_parent.filter(
            detail_pengiriman__id_produk__id_produk=produk_sel
        ).distinct()

    # filter parent by customer
    if customer_sel:
        qs_parent = qs_parent.filter(id_customer__id_customer=customer_sel)
   
    detail_qs = (
        models.detail_pengiriman.objects
        .select_related('id_produk')
        .order_by('id_produk__nama_produk')
    )

    # prefetch detail yang sudah terfilter
    pengirimanobj = (
        qs_parent
        .prefetch_related(Prefetch('detail_pengiriman_set', queryset=detail_qs))
        .order_by('tanggal_pengiriman', 'id_pengiriman')
    )


    return render(request, 'pengiriman/read_pengiriman.html', {
        'pengirimanobj': pengirimanobj,
        # untuk form filter
        'produkobj': models.produk.objects.all().order_by('nama_produk'),
        'customerobj': models.customer.objects.all().order_by('nama_customer'),
        'tmin': tmin, 'tmax': tmax, 'produk_sel': produk_sel, 'customer_sel': customer_sel,
    })


#CREATE PENGIRIMAN
@login_required(login_url='login')
@role_required(['ppic'])
def create_pengiriman(request):
    produkobj = models.produk.objects.all().order_by('nama_produk')
    customerobj = models.customer.objects.all().order_by('nama_customer')

    if request.method == 'GET':
        return render(request, 'pengiriman/create_pengiriman.html', {
            'produkobj': produkobj,
            'customerobj': customerobj,
        })

    if request.method == 'POST':
        tanggal_pengiriman = request.POST.get('tanggal_pengiriman')
        customer_id = request.POST.get('nama_customer')
        nomor_sj = (request.POST.get('nomor_sj') or '').strip()

        # list detail dari form
        produk_list = request.POST.getlist('nama_produk[]')
        jumlah_list = request.POST.getlist('jumlah_produk_dikirim[]')

        with transaction.atomic():
            # simpan header pengiriman
            pengiriman = models.pengiriman.objects.create(
                tanggal_pengiriman=tanggal_pengiriman,
                id_customer_id=customer_id,
                nomor_sj=nomor_sj
            )

            # simpan detail (loop semua baris)
            for prod_id, qty in zip(produk_list, jumlah_list):
                if prod_id and qty:
                    models.detail_pengiriman.objects.create(
                        id_pengiriman=pengiriman,
                        id_produk_id=prod_id,
                        jumlah_produk_dikirim=qty
                    )

        messages.success(request, "Data Pengiriman berhasil ditambahkan.")
        return redirect('read_pengiriman')


#UPDATE PENGIRIMAN
@login_required(login_url='login')
@role_required(['ppic'])
def update_pengiriman(request, id):
    detail = get_object_or_404(models.detail_pengiriman, id_detail_pengiriman=id)
    produkobj = models.produk.objects.all()
    customerobj = models.customer.objects.all()

    if request.method == "GET":
        tanggal_pengiriman = detail.id_pengiriman.tanggal_pengiriman.strftime('%Y-%m-%d')
        return render(request, 'pengiriman/update_pengiriman.html', {
            'getdetailobj': detail,
            'produkobj': produkobj,
            'customerobj': customerobj,
            'tanggal_pengiriman': tanggal_pengiriman,
        })

    # POST
    parent = detail.id_pengiriman
    new_produk = models.produk.objects.get(id_produk=request.POST["nama_produk"])
    new_customer = models.customer.objects.get(id_customer=request.POST["nama_customer"])

    parent.tanggal_pengiriman = request.POST["tanggal_pengiriman"]
    parent.id_customer = new_customer
    parent.nomor_sj = request.POST["nomor_sj"]

    detail.id_produk = new_produk
    detail.jumlah_produk_dikirim = int(request.POST["jumlah_produk_dikirim"] or 0)

    with transaction.atomic():
        parent.save()
        detail.save()

    messages.success(request, "Data pengiriman berhasil diperbarui!")
    return redirect('read_pengiriman')


# DELETE (bisa hapus seluruh pengiriman ATAU 1 detail)

@login_required(login_url='login')
@role_required(['ppic'])
def delete_pengiriman(request, id_pengiriman=None, id_detail=None):
    """
    - Jika id_pengiriman ada  -> hapus parent + seluruh detail (aman untuk DB tanpa CASCADE)
    - Jika id_detail ada      -> hapus satu detail; jika itu terakhir, hapus parent juga
    """
    if request.method != 'POST':
        messages.error(request, "Gunakan tombol hapus (POST).")
        return redirect('read_pengiriman')

    # A) Hapus seluruh PENGIRIMAN
    if id_pengiriman is not None:
        parent = get_object_or_404(models.pengiriman, id_pengiriman=id_pengiriman)
        with transaction.atomic():
            # aman untuk DB yang tidak CASCADE
            models.detail_pengiriman.objects.filter(id_pengiriman=parent).delete()
            parent.delete()
        messages.success(request, "Pengiriman beserta seluruh detail berhasil dihapus.")
        return redirect('read_pengiriman')

    # B) Hapus satu DETAIL
    if id_detail is not None:
        detail = get_object_or_404(models.detail_pengiriman, id_detail_pengiriman=id_detail)
        parent = detail.id_pengiriman
        with transaction.atomic():
            # hapus detail
            detail.delete()
            # jika tidak ada detail tersisa, hapus parent juga
            if not parent.detail_pengiriman_set.exists():
                parent.delete()
                messages.success(request, "Detail terakhir dihapus; pengiriman ikut terhapus.")
            else:
                messages.success(request, "Detail pengiriman berhasil dihapus.")
        return redirect('read_pengiriman')

    messages.error(request, "Parameter hapus tidak valid.")
    return redirect('read_pengiriman')


'''STOK OPNAME'''
#READ STOK OPNAME
@login_required(login_url='login')
@role_required(['ppic','finance'])
def read_stok_opname(request):
    qs = (models.stok_opname.objects
          .prefetch_related('detail_so_bahan_set','detail_so_produk_set')
          .order_by('-tanggal_stok_opname','id_stok_opname'))
    rows = [{
        'id': s.id_stok_opname,
        'tanggal': s.tanggal_stok_opname,
        'n_bahan': s.detail_so_bahan_set.count(),
        'n_produk': s.detail_so_produk_set.count(),
    } for s in qs]

    return render(request, 'stok_opname/read_stok_opname.html', {
        'rows': rows
    })

#detail stok opname bahan per tanggal
@login_required(login_url='login')
@role_required(['ppic','finance'])
def read_detail_so_bahan(request, id_stok_opname):
    so = get_object_or_404(
        models.stok_opname.objects.prefetch_related('detail_so_bahan_set__id_bahan'),
        id_stok_opname=id_stok_opname
    )
    
    return render(request, 'stok_opname/read_detail_so_bahan.html', {
        'so': so, 'details': so.detail_so_bahan_set.all()
    })

#detail stok opname produk per tanggal
@login_required(login_url='login')
@role_required(['ppic','finance'])
def read_detail_so_produk(request, id_stok_opname):
    so = get_object_or_404(
        models.stok_opname.objects.prefetch_related('detail_so_produk_set__id_produk'),
        id_stok_opname=id_stok_opname
    )
   
    return render(request, 'stok_opname/read_detail_so_produk.html', {
        'so': so, 'details': so.detail_so_produk_set.all()
    })

#kumpulan daftar stok opname bahan
def get_stok_sistem_bahan_until(bahan_id, sampai_tanggal):
    """
    Hitung stok sistem bahan per TANGGAL (<= sampai_tanggal).
    Rumus umum:
      stok_awal(opsional) + total_masuk - total_keluar

    — Map-kan bagian 'MASUK' & 'KELUAR' ke model & field kamu —
    """
    total_masuk = 0
    total_keluar = 0

    # === MASUK: dari detail pemesanan bahan (atau penerimaan bahan)
    masuk_qs = getattr(models, 'detail_pemesanan_bahan', None)
    if masuk_qs:
        total_masuk = models.detail_pemesanan_bahan.objects.filter(
            id_bahan_id=bahan_id,
            id_pemesanan__tanggal_pemesanan__lte=sampai_tanggal
        ).aggregate(x=Sum('jumlah_bahan_masuk'))['x'] or 0

    # === KELUAR: dipakai di produksi (detail_produksi.jumlah_bahan_keluar)
    if hasattr(models, 'detail_produksi'):
        total_keluar = models.detail_produksi.objects.filter(
            id_bahan_id=bahan_id,
            id_produksi__tanggal_produksi__lte=sampai_tanggal
        ).aggregate(x=Sum('jumlah_bahan_keluar'))['x'] or 0

    # Jika kamu menyimpan stok awal per bahan per tanggal, tambahkan di sini.
    stok_awal = 0

    return int(stok_awal + total_masuk - total_keluar)

@login_required(login_url='login')
@role_required(['ppic','finance'])
def read_so_bahan(request):
    # --- filter basic ---
    tmin = request.GET.get('tmin')
    tmax = request.GET.get('tmax')
    bahan_sel = request.GET.get('bahan')

    qs = models.detail_so_bahan.objects.select_related('id_stok_opname','id_bahan')

    if tmin:
        qs = qs.filter(id_stok_opname__tanggal_stok_opname__gte=tmin)
    if tmax:
        qs = qs.filter(id_stok_opname__tanggal_stok_opname__lte=tmax)
    if bahan_sel:
        qs = qs.filter(id_bahan_id=bahan_sel)

    qs = qs.order_by('-id_stok_opname__tanggal_stok_opname','id_bahan__nama_bahan')

    # --- paginate ---
    paginator = Paginator(qs, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    # --- hitung stok sistem & penyesuaian per baris ---
    for d in page_obj.object_list:
        tgl = d.id_stok_opname.tanggal_stok_opname
        d.stok_sistem = get_stok_sistem_bahan_until(d.id_bahan_id, tgl)
        d.penyesuaian = int(d.stok_fisik_bahan or 0) - int(d.stok_sistem or 0)
        try:
            fisik = int(d.stok_fisik_bahan or 0)
            sistem = int(d.stok_sistem or 0)
        except (TypeError, ValueError):
            fisik, sistem = 0, 0

        d.penyesuaian = fisik - sistem
        d.penyesuaian_abs = abs(d.penyesuaian) 

    # --- data dropdown filter bahan ---
    bahanobj = models.bahan.objects.all().order_by('nama_bahan')

    return render(request, 'stok_opname/read_so_bahan.html', {
        'page_obj': page_obj,
        'bahanobj': bahanobj,
        'bahan_sel': str(bahan_sel) if bahan_sel else '',
        'tmin': tmin, 'tmax': tmax,
        'is_ppic': request.user.groups.filter(name='ppic').exists(),
    })



#kumpulan daftar stok opname produk
def get_stok_sistem_produk_until(produk_id, sampai_tanggal):
    """
    Rumus umum:
      total_produksi_jadi (FG) - total_pengiriman
    (Jika kamu menyimpan stok awal produk, tambahkan)
    """
    fg = 0
    kirim = 0

    # === FG dari detail_produksi.jumlah_produk
    if hasattr(models, 'detail_produksi'):
        fg = models.detail_produksi.objects.filter(
            id_produk_id=produk_id,
            id_produksi__tanggal_produksi__lte=sampai_tanggal
        ).aggregate(x=Sum('jumlah_produk'))['x'] or 0

    # === Keluar karena pengiriman (detail_pengiriman.jumlah_produk_dikirim)
    if hasattr(models, 'detail_pengiriman'):
        kirim = models.detail_pengiriman.objects.filter(
            id_produk_id=produk_id,
            id_pengiriman__tanggal_pengiriman__lte=sampai_tanggal
        ).aggregate(x=Sum('jumlah_produk_dikirim'))['x'] or 0

    stok_awal = 0
    return int(stok_awal + fg - kirim)

@login_required(login_url='login')
@role_required(['ppic','finance'])
def read_so_produk(request):
    tmin = request.GET.get('tmin')
    tmax = request.GET.get('tmax')
    produk_sel = request.GET.get('produk')

    qs = models.detail_so_produk.objects.select_related('id_stok_opname','id_produk')

    if tmin:
        qs = qs.filter(id_stok_opname__tanggal_stok_opname__gte=tmin)
    if tmax:
        qs = qs.filter(id_stok_opname__tanggal_stok_opname__lte=tmax)
    if produk_sel:
        qs = qs.filter(id_produk_id=produk_sel)

    qs = qs.order_by('-id_stok_opname__tanggal_stok_opname','id_produk__nama_produk')

    paginator = Paginator(qs, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    for d in page_obj.object_list:
        tgl = d.id_stok_opname.tanggal_stok_opname
        d.stok_sistem = get_stok_sistem_produk_until(d.id_produk_id, tgl)
        d.penyesuaian = int(d.stok_fisik_produk or 0) - int(d.stok_sistem or 0)

    produkobj = models.produk.objects.all().order_by('nama_produk')

    return render(request, 'stok_opname/read_so_produk.html', {
        'page_obj': page_obj,
        'produkobj': produkobj,
        'produk_sel': str(produk_sel) if produk_sel else '',
        'tmin': tmin, 'tmax': tmax,
        'is_ppic': request.user.groups.filter(name='ppic').exists(),
    })




#CREATE STOK OPNAME
@login_required(login_url='login')
@role_required(['ppic'])
def create_stok_opname(request):
    bahanobj  = models.bahan.objects.all().order_by('nama_bahan')
    produkobj = models.produk.objects.all().order_by('nama_produk')

    if request.method == 'GET':
        return render(request, 'stok_opname/create_stok_opname.html', {
            'bahanobj': bahanobj, 'produkobj': produkobj
        })

    tanggal = request.POST.get('tanggal_stok_opname')
    if not tanggal:
        messages.error(request, "Tanggal wajib diisi.")
        return render(request, 'stok_opname/create_stok_opname.html', {
            'bahanobj': bahanobj, 'produkobj': produkobj
        })

    if models.stok_opname.objects.filter(tanggal_stok_opname=tanggal).exists():
        messages.error(request,'Tanggal Stok Opname sudah ada.')
        return render(request, 'stok_opname/create_stok_opname.html', {
            'bahanobj': bahanobj, 'produkobj': produkobj
        })

    b_ids  = request.POST.getlist('bahan_id[]')
    b_qtys = request.POST.getlist('bahan_fisik[]')
    p_ids  = request.POST.getlist('produk_id[]')
    p_qtys = request.POST.getlist('produk_fisik[]')

    if not any(b_ids) and not any(p_ids):
        messages.error(request, "Minimal isi salah satu detail (bahan/prodak).")
        return render(request, 'stok_opname/create_stok_opname.html', {
            'bahanobj': bahanobj, 'produkobj': produkobj
        })

    with transaction.atomic():
        so = models.stok_opname.objects.create(tanggal_stok_opname=tanggal)

        for bid, q in zip(b_ids, b_qtys):
            if not bid or not q: continue
            try:
                qty = int(q); 
                if qty < 0: continue
                b = models.bahan.objects.get(id_bahan=bid)
                models.detail_so_bahan.objects.create(
                    id_stok_opname=so, id_bahan=b, stok_fisik_bahan=qty
                )
            except: 
                continue

        for pid, q in zip(p_ids, p_qtys):
            if not pid or not q: continue
            try:
                qty = int(q); 
                if qty < 0: continue
                pr = models.produk.objects.get(id_produk=pid)
                models.detail_so_produk.objects.create(
                    id_stok_opname=so, id_produk=pr, stok_fisik_produk=qty
                )
            except:
                continue

    messages.success(request, "Data Stok Opname Berhasil Ditambahkan")
    return redirect('read_stok_opname')

#UPDATE STOK OPNAME
@login_required(login_url='login')
@role_required(['ppic'])
def update_stok_opname(request, id):
    so = get_object_or_404(models.stok_opname, id_stok_opname=id)

    if request.method == 'GET':
        return render(request, 'stok_opname/update_stok_opname.html', {'so': so})

    tanggal = request.POST.get('tanggal_stok_opname')
    if not tanggal:
        messages.error(request, "Tanggal wajib diisi.")
        return render(request, 'stok_opname/update_stok_opname.html', {'so': so})

    if models.stok_opname.objects.filter(tanggal_stok_opname=tanggal).exclude(id_stok_opname=id).exists():
        messages.error(request, "Tanggal Stok Opname sudah ada!")
        return render(request, 'stok_opname/update_stok_opname.html', {'so': so})

    so.tanggal_stok_opname = tanggal
    so.save()
    messages.success(request, "Data Stok Opname Berhasil Diperbarui")
    return redirect('read_stok_opname')

@login_required(login_url='login')
@role_required(['ppic'])
def update_detail_so_bahan(request, id_detail):
    d = get_object_or_404(models.detail_so_bahan, id_detail_so_bahan=id_detail)
    bahanobj = models.bahan.objects.all().order_by('nama_bahan')

    if request.method == 'GET':
        return render(request, 'stok_opname/update_detail_so_bahan.html', {'d': d, 'bahanobj': bahanobj})

    bahan_id = request.POST.get('id_bahan')
    qty_str  = request.POST.get('stok_fisik_bahan')
    try:
        d.id_bahan = models.bahan.objects.get(id_bahan=bahan_id)
        d.stok_fisik_bahan = int(qty_str)
        d.save()
        messages.success(request, "Detail SO Bahan diperbarui.")
    except:
        messages.error(request, "Gagal menyimpan detail.")
    return redirect('read_detail_so_bahan', id_stok_opname=d.id_stok_opname.id_stok_opname)

@login_required(login_url='login')
@role_required(['ppic'])
def update_detail_so_produk(request, id_detail):
    d = get_object_or_404(models.detail_so_produk, id_detail_so_produk=id_detail)
    produkobj = models.produk.objects.all().order_by('nama_produk')

    if request.method == 'GET':
        return render(request, 'stok_opname/update_detail_so_produk.html', {'d': d, 'produkobj': produkobj})

    produk_id = request.POST.get('id_produk')
    qty_str   = request.POST.get('stok_fisik_produk')
    try:
        d.id_produk = models.produk.objects.get(id_produk=produk_id)
        d.stok_fisik_produk = int(qty_str)
        d.save()
        messages.success(request, "Detail SO Produk diperbarui.")
    except:
        messages.error(request, "Gagal menyimpan detail.")
    return redirect('read_detail_so_produk', id_stok_opname=d.id_stok_opname.id_stok_opname)

#DELETE STOK OPNAME
@login_required(login_url="login")
@role_required(['ppic'])
def delete_stok_opname(request, id):
    if request.method != 'POST':
        messages.error(request, "Metode tidak diizinkan.")
        return redirect('read_stok_opname')
    so = get_object_or_404(models.stok_opname, id_stok_opname=id)
    so.delete()  # cascade ke detail
    messages.success(request, "Data Stok Opname Berhasil Dihapus")

    return redirect('read_stok_opname')

@login_required(login_url='login')
@role_required(['ppic'])
def delete_detail_so_bahan(request, id_detail):
    if request.method != 'POST':
        messages.error(request, "Metode tidak diizinkan.")
        return redirect('read_stok_opname')
    
    d = get_object_or_404(models.detail_so_bahan, id_detail_so_bahan=id_detail)
    parent = d.id_stok_opname
    d.delete()
    messages.success(request, "Detail bahan berhasil dihapus.")

    return redirect('read_detail_so_bahan', id_stok_opname=parent.id_stok_opname)

@login_required(login_url='login')
@role_required(['ppic'])
def delete_detail_so_produk(request, id_detail):
    if request.method != 'POST':
        messages.error(request, "Metode tidak diizinkan.")
        return redirect('read_stok_opname')
    d = get_object_or_404(models.detail_so_produk, id_detail_so_produk=id_detail)
    parent = d.id_stok_opname
    d.delete()
    messages.success(request, "Detail produk berhasil dihapus.")
  
    return redirect('read_detail_so_produk', id_stok_opname=parent.id_stok_opname)


'''PALLET BISMILLAH'''
#Tarik kebutuhan pallet
def _baca_kebutuhan_global():
    """
    Tarik aturan global dari tabel kebutuhan_pallet (global per bahan).
    Return dict {id_bahan: kebutuhan_mm_per_pallet}
    """
    rows = models.kebutuhan_pallet.objects.all().values('id_bahan', 'kebutuhan')
    return {r['id_bahan']: r['kebutuhan'] for r in rows}

#Perhitungan Auto Wrap dari Produksi
def _auto_wrap_dari_produksi(detail_obj):
    """
    Diberi satu baris detail_produksi -> update pallet_terbuka,
    hitung berapa pallet penuh (AUTO), buat event pallet_penuh, dan sisa_item (modulo).
    """
    produk = detail_obj.id_produk
    qty = int(detail_obj.jumlah_produk or 0)
    if qty <= 0:
        return

    kapasitas = int(produk.kapasitas_pallet or 0)
    if kapasitas <= 0:
        return

    # buffer per produk (1 baris per produk)
    buffer, _ = models.pallet_terbuka.objects.get_or_create(
        id_produk=produk,
        defaults={'sisa_item': 0, 'tanggal_update': detail_obj.id_produksi.tanggal_produksi}
    )

    sisa_awal = int(buffer.sisa_item or 0)
    total = sisa_awal + qty

    pallet_full = total // kapasitas
    sisa_baru  = total % kapasitas

    # update buffer
    buffer.sisa_item = sisa_baru
    buffer.tanggal_update = detail_obj.id_produksi.tanggal_produksi
    buffer.save(update_fields=['sisa_item', 'tanggal_update'])

    # buat event pallet_penuh kalau ada yang terbentuk
    if pallet_full > 0:
        models.pallet_penuh.objects.create(
            id_produk=produk,
            id_detail_produksi=detail_obj,
            jumlah_pallet_penuh=pallet_full,
            tanggal_event=detail_obj.id_produksi.tanggal_produksi,
            event_type=models.pallet_penuh.AUTO
        )
        # konsumsi bahan pembantu → dihitung dari query saat laporan

#Perhitungan Auto Wrap dari Pemesanan EOE
def _wrap_eoe_from_pemesanan(detail_obj, *, default_capacity=55200):
    eoe_q = (
    Q(nama_produk__iregex=r'(^|[^A-Za-z0-9])EOE([^A-Za-z0-9]|$)') |
    Q(nama_produk__iregex=r'\bBottom\s+End\b')
    )
    eoe_ids = set(
        models.produk.objects
        .filter(eoe_q)
        .values_list('id_produk', flat=True)
    )

    produk = detail_obj.id_produk
    if produk.id_produk not in eoe_ids:
        return  # hanya EOE/Bottom End

    if models.pallet_penuh.objects.filter(id_detail_pemesanan_produk=detail_obj).exists():
        return
    
    qty = int(detail_obj.jumlah_produk_masuk or 0)
    if qty <= 0:
        return

    kapasitas = int(getattr(produk, 'kapasitas_pallet', 0) or default_capacity)
    if kapasitas <= 0:
        kapasitas = default_capacity  

    pallets = max(1, math.ceil(qty / kapasitas))
    tanggal_evt = getattr(detail_obj.id_pemesanan, 'tanggal_pemesanan', None) or getattr(detail_obj, 'tanggal', None)

    models.pallet_penuh.objects.create(
        id_produk=produk,
        id_detail_produksi=None,
        id_detail_pemesanan_produk=detail_obj,
        jumlah_pallet_penuh=pallets,
        tanggal_event=tanggal_evt,
        event_type=models.pallet_penuh.AUTO
    )

'''PALLET'''
#READ PALLET (daftar manual & auto wrap)
@login_required(login_url='login')
@role_required(['ppic','produksi'])
def read_pallet(request):
    tmin = request.GET.get('tmin')
    tmax = request.GET.get('tmax')
    produk_sel = request.GET.get('produk')

    pallet_open_qs = models.pallet_terbuka.objects.select_related('id_produk').order_by('id_produk__nama_produk')
    if produk_sel:
        pallet_open_qs = pallet_open_qs.filter(id_produk__id_produk=produk_sel)

    penuh_qs = models.pallet_penuh.objects.select_related('id_produk').order_by('-tanggal_event','-id_pallet_penuh')
    if tmin: penuh_qs = penuh_qs.filter(tanggal_event__gte=tmin)
    if tmax: penuh_qs = penuh_qs.filter(tanggal_event__lte=tmax)
    if produk_sel: penuh_qs = penuh_qs.filter(id_produk__id_produk=produk_sel)

    # Ambil aturan global kebutuhan (mm per pallet) untuk tiap bahan pembantu
    kebutuhan_qs = models.kebutuhan_pallet.objects.select_related('id_bahan') \
                    .order_by('id_bahan__nama_bahan')
    kebutuhan_map = {
        row.id_bahan_id: (int(row.kebutuhan or 0), int(row.mm_per_roll or 0))
        for row in kebutuhan_qs
    }
    bahan_list = [row.id_bahan for row in kebutuhan_qs]

    riwayat_data = []
    for e in penuh_qs:
        consum = []
        pallets = int(e.jumlah_pallet_penuh or 0)
        for bhn in bahan_list:
            per_pallet, mm_roll = kebutuhan_map.get(bhn.id_bahan, (0, 0))
            total_mm = per_pallet * pallets
            rolls    = (total_mm // mm_roll) if (mm_roll and total_mm) else 0
            sisa_mm  = (total_mm %  mm_roll) if mm_roll else 0
            consum.append({
                "bahan": bhn,
                "per_pallet_mm": per_pallet,
                "mm_per_roll": mm_roll,
                "total_mm": total_mm,
                "rolls": rolls,
                "sisa_mm": sisa_mm,
            })
        riwayat_data.append({"event": e, "consum": consum})
        
    # --- RIWAYAT EOE: event pallet yang sumbernya dari pemesanan EOE ---
    eoe_qs = (models.pallet_penuh.objects.select_related('id_produk', 'id_detail_pemesanan_produk__id_pemesanan') 
            .filter(id_detail_pemesanan_produk__isnull=False)  
            .order_by('-tanggal_event', '-id_pallet_penuh'))

    # ikutkan filter tmin/tmax/produk_sel jika ada
    if tmin:
        eoe_qs = eoe_qs.filter(tanggal_event__gte=tmin)
    if tmax:
        eoe_qs = eoe_qs.filter(tanggal_event__lte=tmax)
    if produk_sel:
        eoe_qs = eoe_qs.filter(id_produk__id_produk=produk_sel)

    # siapkan baris yang enak dipakai template
    eoe_rows = []
    for e in eoe_qs:
        pr = e.id_produk
        dp = e.id_detail_pemesanan_produk  # bisa None kalau FK di-set null
        kapasitas = int(getattr(pr, 'kapasitas_pallet', 0) or 55200)
        qty_masuk = int(getattr(dp, 'jumlah_produk_masuk', 0) or 0)
        eoe_rows.append({
            "event": e,                  # punya: tanggal_event, jumlah_pallet_penuh, dll.
            "produk": pr,
            "qty_masuk": qty_masuk,      # dari detail pemesanan
            "kapasitas": kapasitas,      # kapasitas pallet (fallback 55200)
            "pemesanan": getattr(dp, 'id_pemesanan', None),
        })

    riwayat_eoe = []
    for e in eoe_qs:
        pallets = int(e.jumlah_pallet_penuh or 0)
        consum = []
        for bhn in bahan_list:
            per_pallet, mm_roll = kebutuhan_map.get(bhn.id_bahan, (0, 0))
            total_mm = per_pallet * pallets
            rolls    = (total_mm // mm_roll) if (mm_roll and total_mm) else 0
            sisa_mm  = (total_mm %  mm_roll) if mm_roll else 0
            consum.append({
                "bahan": bhn,
                "per_pallet_mm": per_pallet,
                "mm_per_roll": mm_roll,
                "total_mm": total_mm,
                "rolls": rolls,
                "sisa_mm": sisa_mm,
            })
        riwayat_eoe.append({"event": e, "consum": consum})

    return render(request, 'pallet/read_pallet.html', {
        'pallet_open': pallet_open_qs,
        'riwayat_data': riwayat_data,           
        'produkobj': models.produk.objects.all().order_by('nama_produk'),
        'tmin': tmin, 'tmax': tmax, 'produk_sel': produk_sel,
        'bahan_list': bahan_list,    
        'riwayat_eoe': riwayat_eoe,
    })


#Logika Manual Wrap
@login_required(login_url='login')
@role_required(['ppic','produksi'])
@require_POST
def wrap_manual(request, id_produk):
    """
    Manual wrap 1 pallet untuk produk tertentu dari buffer yang ada.
    Aturan: hanya boleh jika sisa_item > 0.
    tanggal_event = today (kebijakanmu real-time).
    """
    produk = get_object_or_404(models.produk, id_produk=id_produk)
    buffer = models.pallet_terbuka.objects.filter(id_produk=produk).first()
    if not buffer or (buffer.sisa_item or 0) <= 0:
        messages.error(request, "Tidak ada pallet terbuka untuk produk ini.")
        return redirect('read_pallet')

    # buat event manual (1 pallet)
    models.pallet_penuh.objects.create(
        id_produk=produk,
        id_detail_produksi=None,
        jumlah_pallet_penuh=1,
        tanggal_event=now().date(),  # real-time no backdate
        event_type=models.pallet_penuh.MANUAL
    )

    # reset buffer
    buffer.sisa_item = 0
    buffer.tanggal_update = now().date()
    buffer.save(update_fields=['sisa_item', 'tanggal_update'])

    messages.success(request, f"Pallet manual untuk {produk.nama_produk} berhasil ditutup.")
    return redirect('read_pallet')


'''KEBUTUHAN PALLET'''
@login_required(login_url='login')
@role_required(['ppic'])
def read_kebutuhan_pallet(request):
    rows = (models.kebutuhan_pallet.objects
            .select_related('id_bahan')
            .order_by('id_bahan__nama_bahan'))
    return render(request, 'pallet/read_kebutuhan_pallet.html', {'rows': rows})

@login_required(login_url='login')
@role_required(['ppic'])
def create_kebutuhan_pallet(request):
    bahanobj = models.bahan.objects.filter(jenis_bahan__icontains='pembantu').order_by('nama_bahan')
    if request.method == 'GET':
        return render(request, 'pallet/create_kebutuhan_pallet.html', {'bahanobj': bahanobj})
    id_bahan = request.POST.get('nama_bahan')
    kebutuhan = int(request.POST.get('kebutuhan') or 0)
   
    if not id_bahan or kebutuhan <= 0:
        messages.error(request, "Pilih bahan & isi kebutuhan (mm) > 0.")
        return render(request, 'pallet/create_kebutuhan_pallet.html', {'bahanobj': bahanobj})
    if models.kebutuhan_pallet.objects.filter(id_bahan_id=id_bahan).exists():
        messages.error(request, "Aturan kebutuhan untuk bahan ini sudah ada.")
        return render(request, 'pallet/create_kebutuhan_pallet.html', {'bahanobj': bahanobj})
   
    mm_per_roll = request.POST.get('mm_per_roll')
    models.kebutuhan_pallet.objects.create(id_bahan_id=id_bahan, kebutuhan=kebutuhan, mm_per_roll=mm_per_roll)
  
    messages.success(request, "Aturan kebutuhan berhasil ditambahkan.")
    return redirect('read_kebutuhan_pallet')

@login_required(login_url='login')
@role_required(['ppic'])
def update_kebutuhan_pallet(request, id):
    row = get_object_or_404(models.kebutuhan_pallet, id_kebutuhan=id)
    bahanobj = models.bahan.objects.filter(jenis_bahan__icontains='pembantu').order_by('nama_bahan')
    if request.method == 'GET':
        return render(request, 'pallet/update_kebutuhan_pallet.html', {'row': row, 'bahanobj': bahanobj})
    id_bahan = request.POST.get('nama_bahan')
    kebutuhan = int(request.POST.get('kebutuhan') or 0)
    if not id_bahan or kebutuhan <= 0:
        messages.error(request, "Pilih bahan & isi kebutuhan (mm) > 0.")
        return render(request, 'pallet/update_kebutuhan_pallet.html', {'row': row, 'bahanobj': bahanobj})
    # pastikan unique per bahan
    if models.kebutuhan_pallet.objects.filter(id_bahan_id=id_bahan).exclude(id_kebutuhan=row.id_kebutuhan).exists():
        messages.error(request, "Aturan untuk bahan ini sudah ada.")
        return render(request, 'pallet/update_kebutuhan_pallet.html', {'row': row, 'bahanobj': bahanobj})
    mm_per_roll = request.POST.get('mm_per_roll')
        
    row.id_bahan_id = id_bahan
    row.kebutuhan = kebutuhan
    row.mm_per_roll = mm_per_roll
    row.save()
    messages.success(request, "Aturan kebutuhan diperbarui.")
    return redirect('read_kebutuhan_pallet')

@login_required(login_url='login')
@role_required(['ppic'])
@require_POST
def delete_kebutuhan_pallet(request, id):
    row = get_object_or_404(models.kebutuhan_pallet, id_kebutuhan=id)
    row.delete()
    messages.success(request, "Aturan kebutuhan dihapus.")
    return redirect('read_kebutuhan_pallet')


'''sebelum laporan'''
#hitung stok awal based on stok fisik stok opname terakhir
from datetime import timedelta
from django.db.models import Sum

# --- cari SO terakhir sebelum/hingga tgl tertentu ---
def _last_so_produk_before(date_, produk):
    row = (
        models.detail_so_produk.objects
        .filter(id_stok_opname__tanggal_stok_opname__lte=date_, id_produk=produk)
        .order_by('-id_stok_opname__tanggal_stok_opname')
        .values('id_stok_opname__tanggal_stok_opname', 'stok_fisik_produk')
        .first()
    )
    if not row:
        return None, None
    return row['id_stok_opname__tanggal_stok_opname'], int(row['stok_fisik_produk'] or 0)

def _last_so_bahan_before(date_, bahan):
    row = (
        models.detail_so_bahan.objects
        .filter(id_stok_opname__tanggal_stok_opname__lte=date_, id_bahan=bahan)
        .order_by('-id_stok_opname__tanggal_stok_opname')
        .values('id_stok_opname__tanggal_stok_opname', 'stok_fisik_bahan')
        .first()
    )
    if not row:
        return None, None
    return row['id_stok_opname__tanggal_stok_opname'], int(row['stok_fisik_bahan'] or 0)

# --- net movement PRODUK (masuk-keluar) di [d1, d2] ---
def _net_mov_produk_in_range(produk, d1, d2):
    if d1 > d2:
        return 0
    # MASUK: EOE dari pemesanan produk, non-EOE dari produksi
    if models.produk.objects.filter(_eoe_q(), id_produk=produk.id_produk).exists():
        masuk = (
            models.detail_pemesanan_produk.objects
            .filter(id_produk=produk, id_pemesanan__tanggal_pemesanan__range=[d1, d2])
            .aggregate(x=Sum('jumlah_produk_masuk'))['x'] or 0
        )
    else:
        masuk = (
            models.detail_produksi.objects
            .filter(id_produk=produk, id_produksi__tanggal_produksi__range=[d1, d2])
            .aggregate(x=Sum('jumlah_produk'))['x'] or 0
        )
    # KELUAR: pengiriman
    keluar = (
        models.detail_pengiriman.objects
        .filter(id_produk=produk, id_pengiriman__tanggal_pengiriman__range=[d1, d2])
        .aggregate(x=Sum('jumlah_produk_dikirim'))['x'] or 0
    )
    return int(masuk) - int(keluar)

# --- net movement BAHAN (masuk-keluar) di [d1, d2] ---
def _net_mov_bahan_in_range(bahan, d1, d2):
    if d1 > d2:
        return 0
    # MASUK: pemesanan bahan
    masuk = (
        models.detail_pemesanan_bahan.objects
        .filter(id_bahan=bahan, id_pemesanan__tanggal_pemesanan__range=[d1, d2])
        .aggregate(x=Sum('jumlah_bahan_masuk'))['x'] or 0
    )

    # KELUAR: beda perlakuan (pallet vs wrapping vs baku ke produksi)
    nama = (bahan.nama_bahan or '').lower()
    jenis = (bahan.jenis_bahan or '').lower()

    if _is_pallet_name(bahan.nama_bahan):
        # keluar = jumlah pallet penuh di rentang
        keluar = _total_pallet_penuh_dalam(d1, d2)
    elif 'pembantu' in jenis and bahan.id_bahan in _kebutuhan_map():
        per_mm, mm_per_roll = _kebutuhan_map()[bahan.id_bahan]
        if per_mm > 0 and mm_per_roll > 0:
            pallet = int(_total_pallet_penuh_dalam(d1, d2))
            keluar = (per_mm * pallet) // mm_per_roll  # roll terpakai
        else:
            keluar = 0
    else:
        # asumsi selain itu = bahan baku → keluar di produksi
        keluar = (
            models.detail_produksi.objects
            .filter(id_bahan=bahan, id_produksi__tanggal_produksi__range=[d1, d2])
            .aggregate(x=Sum('jumlah_bahan_keluar'))['x'] or 0
        )
    return int(masuk) - int(keluar)

# --- stok awal PRODUK yang menghormati SO ---
def _stok_awal_produk_dengan_so(start_date, produk):
    h_1 = start_date - timedelta(days=1)
    so_date, so_fisik = _last_so_produk_before(h_1, produk)
    if not so_date:
        # fallback: saldo sistem s.d. H-1 (jika belum pernah SO)
        return _stok_sistem_produk_sampai(h_1, produk)
    mov = _net_mov_produk_in_range(produk, so_date + timedelta(days=1), h_1)
    return int(so_fisik) + int(mov)

# --- stok awal BAHAN yang menghormati SO ---
def _stok_awal_bahan_dengan_so(start_date, bahan):
    h_1 = start_date - timedelta(days=1)
    so_date, so_fisik = _last_so_bahan_before(h_1, bahan)
    if not so_date:
        return _stok_sistem_bahan_sampai(h_1, bahan)
    mov = _net_mov_bahan_in_range(bahan, so_date + timedelta(days=1), h_1)
    return int(so_fisik) + int(mov)


'''LAPORAN REKAPITULASI STOK'''
# =========================
# HELPER: saldo sistem sampai tanggal (inklusif)
# =========================

# FILTER EOE & produk biasa
def _eoe_q():
    return (
        Q(nama_produk__iregex=r'(^|[^A-Za-z0-9])EOE([^A-Za-z0-9]|$)') |
        Q(nama_produk__iregex=r'\bBottom\s+End\b')
    )
    
# Hitung Stok Produk
def _stok_sistem_produk_sampai(tanggal, produk):
    # bedakan EOE/Bottom End vs non-EOE
    if models.produk.objects.filter(_eoe_q(), id_produk=produk.id_produk).exists():
        masuk = (
            models.detail_pemesanan_produk.objects
            .filter(id_produk=produk, id_pemesanan__tanggal_pemesanan__lte=tanggal)
            .aggregate(total=Sum('jumlah_produk_masuk'))['total'] or 0
        )
    else:
        masuk = (
            models.detail_produksi.objects
            .filter(id_produk=produk, id_produksi__tanggal_produksi__lte=tanggal)
            .aggregate(total=Sum('jumlah_produk'))['total'] or 0
        )

    keluar = (
        models.detail_pengiriman.objects
        .filter(id_produk=produk, id_pengiriman__tanggal_pengiriman__lte=tanggal)
        .aggregate(total=Sum('jumlah_produk_dikirim'))['total'] or 0
    )
    return int(masuk) - int(keluar)


# FILTER Pallet & Bahan Pembantu Lain
def _is_pallet_name(nama):
    s = (nama or '').lower()
    return ('pallet' in s) or ('palet' in s)

def _kebutuhan_map():
    # { id_bahan: (kebutuhan_mm_per_pallet, mm_per_roll) }
    rows = models.kebutuhan_pallet.objects.values('id_bahan', 'kebutuhan', 'mm_per_roll')
    return { r['id_bahan']: (int(r['kebutuhan'] or 0), int(r['mm_per_roll'] or 0)) for r in rows }

def _total_pallet_penuh_sampai(tanggal):
    return models.pallet_penuh.objects.filter(tanggal_event__lte=tanggal)\
        .aggregate(total=Sum('jumlah_pallet_penuh'))['total'] or 0

def _total_pallet_penuh_dalam(start_date, end_date):
    return models.pallet_penuh.objects.filter(tanggal_event__range=[start_date, end_date])\
        .aggregate(total=Sum('jumlah_pallet_penuh'))['total'] or 0

# Hitung Stok Bahan Pembantu
def _stok_sistem_bahan_sampai(tanggal, bahan):
    # MASUK: pemesanan bahan s.d. tanggal
    masuk = (
        models.detail_pemesanan_bahan.objects
        .filter(id_bahan=bahan, id_pemesanan__tanggal_pemesanan__lte=tanggal)
        .aggregate(total=Sum('jumlah_bahan_masuk'))['total'] or 0
    )

    # KELUAR: beda perlakuan
    if _is_pallet_name(bahan.nama_bahan):
        # keluar = jumlah pallet penuh (unit pallet)
        keluar = _total_pallet_penuh_sampai(tanggal)
    else:
        # cek apakah bahan ini bahan pembantu wrapping (punya kebutuhan per pallet)
        keb_map = _kebutuhan_map()
        if bahan.id_bahan in keb_map and 'pembantu' in (bahan.jenis_bahan or '').lower():
            per_pallet_mm, mm_per_roll = keb_map[bahan.id_bahan]
            if per_pallet_mm > 0 and mm_per_roll > 0:
                total_pallet = _total_pallet_penuh_sampai(tanggal)
                total_mm = per_pallet_mm * total_pallet
                keluar = total_mm // mm_per_roll  # jumlah roll terpakai
            else:
                keluar = 0
        else:
            # default: bahan baku dipakai di produksi
            keluar = (
                models.detail_produksi.objects
                .filter(id_bahan=bahan, id_produksi__tanggal_produksi__lte=tanggal)
                .aggregate(total=Sum('jumlah_bahan_keluar'))['total'] or 0
            )

    return int(masuk) - int(keluar)


# =========================
# HELPER: penyesuaian kumulatif di dalam periode (berurutan per tanggal SO)
# =========================
def _penyesuaian_produk_dalam_periode(start_date, end_date, produk):
    total_adj = 0
    so_list = (
        models.stok_opname.objects
        .filter(tanggal_stok_opname__range=[start_date, end_date])
        .order_by('tanggal_stok_opname')
    )  # stok_opname.tanggal_stok_opname :contentReference[oaicite:7]{index=7}
    for so in so_list:
        det = models.detail_so_produk.objects.filter(id_stok_opname=so, id_produk=produk).first()
        if not det:
            continue
        sistem_sampai_t = _stok_sistem_produk_sampai(so.tanggal_stok_opname, produk)
        fisik_t = int(getattr(det, 'stok_fisik_produk', 0) or 0)  # stok_fisik_produk :contentReference[oaicite:8]{index=8}
        adj_t = fisik_t - (sistem_sampai_t + total_adj)
        total_adj += adj_t
    return total_adj

def _penyesuaian_bahan_dalam_periode(start_date, end_date, bahan):
    total_adj = 0
    so_list = (
        models.stok_opname.objects
        .filter(tanggal_stok_opname__range=[start_date, end_date])
        .order_by('tanggal_stok_opname')
    )  # stok_opname.tanggal_stok_opname :contentReference[oaicite:9]{index=9}
    for so in so_list:
        det = models.detail_so_bahan.objects.filter(id_stok_opname=so, id_bahan=bahan).first()
        if not det:
            continue
        sistem_sampai_t = _stok_sistem_bahan_sampai(so.tanggal_stok_opname, bahan)
        fisik_t = int(getattr(det, 'stok_fisik_bahan', 0) or 0)  # stok_fisik_bahan :contentReference[oaicite:10]{index=10}
        adj_t = fisik_t - (sistem_sampai_t + total_adj)
        total_adj += adj_t
    return total_adj
        


# ========================= #
# LAPORAN REKAPITULASI STOK #
# ========================= #

@login_required(login_url='login')
@role_required(['ppic', 'manajer'])
def laporan_rekapitulasi_stok(request):
    # baca rentang tanggal (GET)
    start_str = request.GET.get('start')
    end_str   = request.GET.get('end')

    start_date = end_date = None
    if start_str and end_str:
        try:
            start_date = datetime.strptime(start_str, '%Y-%m-%d').date()
            end_date   = datetime.strptime(end_str,   '%Y-%m-%d').date()
        except ValueError:
            start_date = end_date = None

    produk_data, bahan_data, bahan_baku_data = [], [], []

    if start_date and end_date:
        h_minus_1 = start_date - timedelta(days=1)

        # ------- PRODUK (tampil dulu) -------
        eoe_ids = set(
                    models.produk.objects.filter(_eoe_q()).values_list('id_produk', flat=True)
                )
        
        produk_qs = models.produk.objects.all().order_by('nama_produk')  
        no = 1
        for p in produk_qs:
            stok_awal = _stok_awal_produk_dengan_so(start_date, p)


            if p.id_produk in eoe_ids:
                masuk = (
                    models.detail_pemesanan_produk.objects
                    .filter(id_produk=p, id_pemesanan__tanggal_pemesanan__range=[start_date, end_date])
                    .aggregate(total=Sum('jumlah_produk_masuk'))['total'] or 0
                )
            else:
                masuk = (
                    models.detail_produksi.objects
                    .filter(id_produk=p, id_produksi__tanggal_produksi__range=[start_date, end_date])
                    .aggregate(total=Sum('jumlah_produk'))['total'] or 0
                )

            keluar = (
                models.detail_pengiriman.objects
                .filter(id_produk=p, id_pengiriman__tanggal_pengiriman__range=[start_date, end_date])
                .aggregate(total=Sum('jumlah_produk_dikirim'))['total'] or 0
            ) 

            penyesuaian = _penyesuaian_produk_dalam_periode(start_date, end_date, p)
            stok_akhir = stok_awal + masuk - keluar + penyesuaian

            produk_data.append({
                'no': no,
                'nama': p.nama_produk,
                'stok_awal': stok_awal,
                'masuk': masuk,
                'keluar': keluar,
                'penyesuaian': penyesuaian,
                'stok_akhir': stok_akhir,
            })
            no += 1

        # ------- BAHAN PEMBANTU -------
        bahan_qs = (
            models.bahan.objects
            .filter(jenis_bahan__icontains='pembantu')
            .order_by('nama_bahan')
        )

        keb_map = _kebutuhan_map()  # 1x untuk efisiensi
        total_pallet_period = _total_pallet_penuh_dalam(start_date, end_date)

        no = 1
        for b in bahan_qs:
            h_minus_1 = start_date - timedelta(days=1)

            stok_awal = _stok_awal_bahan_dengan_so(start_date, b)

            # masuk periode (pemesanan)
            masuk = (
                models.detail_pemesanan_bahan.objects
                .filter(id_bahan=b, id_pemesanan__tanggal_pemesanan__range=[start_date, end_date])
                .aggregate(total=Sum('jumlah_bahan_masuk'))['total'] or 0
            )

            # keluar periode (dibedakan)
            if _is_pallet_name(b.nama_bahan):
                keluar = int(total_pallet_period)
            elif b.id_bahan in keb_map:
                per_pallet_mm, mm_per_roll = keb_map[b.id_bahan]
                if per_pallet_mm > 0 and mm_per_roll > 0 and total_pallet_period > 0:
                    total_mm = per_pallet_mm * total_pallet_period
                    keluar = total_mm // mm_per_roll
                else:
                    keluar = 0
            else:
                keluar = (
                    models.detail_produksi.objects
                    .filter(id_bahan=b, id_produksi__tanggal_produksi__range=[start_date, end_date])
                    .aggregate(total=Sum('jumlah_bahan_keluar'))['total'] or 0
                )

            penyesuaian = _penyesuaian_bahan_dalam_periode(start_date, end_date, b)
            stok_akhir = int(stok_awal) + int(masuk) - int(keluar) + int(penyesuaian)

            bahan_data.append({
                'no': no,
                'nama': b.nama_bahan,
                'stok_awal': stok_awal,
                'masuk': masuk,
                'keluar': keluar,
                'penyesuaian': penyesuaian,
                'stok_akhir': stok_akhir,
            })
            no += 1

        # ------- BAHAN BAKU -------
        bahan_baku_data = []
        bahan_baku_qs = (
            models.bahan.objects
            .filter(jenis_bahan__icontains='baku')   # kategori bahan baku
            .order_by('nama_bahan')
        )

        no = 1
        for b in bahan_baku_qs:
            h_minus_1 = start_date - timedelta(days=1)

            # stok awal (akumulasi s.d. H-1 so)
            stok_awal = _stok_awal_bahan_dengan_so(start_date, b)

            # masuk (pemesanan bahan di periode)
            masuk = (
                models.detail_pemesanan_bahan.objects
                .filter(id_bahan=b, id_pemesanan__tanggal_pemesanan__range=[start_date, end_date])
                .aggregate(total=Sum('jumlah_bahan_masuk'))['total'] or 0
            )

            # keluar (dipakai di produksi di periode)
            keluar = (
                models.detail_produksi.objects
                .filter(id_bahan=b, id_produksi__tanggal_produksi__range=[start_date, end_date])
                .aggregate(total=Sum('jumlah_bahan_keluar'))['total'] or 0
            )

            # penyesuaian (SO di periode)
            penyesuaian = _penyesuaian_bahan_dalam_periode(start_date, end_date, b)

            stok_akhir = int(stok_awal) + int(masuk) - int(keluar) + int(penyesuaian)

            bahan_baku_data.append({
                'no': no,
                'nama': b.nama_bahan,
                'stok_awal': stok_awal,
                'masuk': masuk,
                'keluar': keluar,
                'penyesuaian': penyesuaian,
                'stok_akhir': stok_akhir,
            })
            no += 1


    # build querystring untuk tombol PDF
    qs = {}
    if start_date and end_date:
        qs = {'start': start_date.strftime('%Y-%m-%d'), 'end': end_date.strftime('%Y-%m-%d')}
    pdf_url = reverse('laporan_rekapitulasi_stok_pdf') + (f"?{urlencode(qs)}" if qs else "")

    context = {
        'produk_data': produk_data,
        'bahan_data': bahan_data,
        'bahan_baku_data': bahan_baku_data,
        'start_date': start_date,
        'end_date': end_date,
        'pdf_url': pdf_url,
    }
    return render(request, 'laporan/laporan_rekapitulasi_stok.html', context)

# =========================
# LAPORAN REKAPITULASI: PDF
# =========================
@login_required(login_url='login')
@role_required(['ppic', 'manajer'])
def laporan_rekapitulasi_stok_pdf(request):
    # ambil parameter
    start_str = request.GET.get('start')
    end_str   = request.GET.get('end')

    start_date = end_date = None
    if start_str and end_str:
        try:
            start_date = datetime.strptime(start_str, '%Y-%m-%d').date()
            end_date   = datetime.strptime(end_str,   '%Y-%m-%d').date()
        except ValueError:
            start_date = end_date = None

    produk_data, bahan_data = [], []

    if start_date and end_date:
        h_minus_1 = start_date - timedelta(days=1)

        # PRODUK
        eoe_ids = set(
                    models.produk.objects.filter(_eoe_q()).values_list('id_produk', flat=True)
                )
       
        produk_qs = models.produk.objects.all().order_by('nama_produk')  # :contentReference[oaicite:17]{index=17}
        no = 1
        for p in produk_qs:
            stok_awal = _stok_awal_produk_dengan_so(start_date, p)



            if p.id_produk in eoe_ids:
                masuk = (
                    models.detail_pemesanan_produk.objects
                    .filter(id_produk=p, id_pemesanan__tanggal_pemesanan__range=[start_date, end_date])
                    .aggregate(total=Sum('jumlah_produk_masuk'))['total'] or 0
                )
            else:
                masuk = (
                    models.detail_produksi.objects
                    .filter(id_produk=p, id_produksi__tanggal_produksi__range=[start_date, end_date])
                    .aggregate(total=Sum('jumlah_produk'))['total'] or 0
                )

            keluar = (
                models.detail_pengiriman.objects
                .filter(id_produk=p, id_pengiriman__tanggal_pengiriman__range=[start_date, end_date])
                .aggregate(total=Sum('jumlah_produk_dikirim'))['total'] or 0
            ) 

            penyesuaian = _penyesuaian_produk_dalam_periode(start_date, end_date, p)
            stok_akhir = stok_awal + masuk - keluar + penyesuaian

            produk_data.append({
                'no': no,
                'nama': p.nama_produk,
                'stok_awal': stok_awal,
                'masuk': masuk,
                'keluar': keluar,
                'penyesuaian': penyesuaian,
                'stok_akhir': stok_akhir,
            })
            no += 1

        # BAHAN PEMBANTU
        bahan_qs = (
            models.bahan.objects
            .filter(jenis_bahan__icontains='pembantu')
            .order_by('nama_bahan')
        )  # :contentReference[oaicite:20]{index=20}
        no = 1
        for b in bahan_qs:
            stok_awal = _stok_awal_bahan_dengan_so(start_date, b)

            masuk = (
                models.detail_pemesanan_bahan.objects
                .filter(id_bahan=b, id_pemesanan__tanggal_pemesanan__range=[start_date, end_date])
                .aggregate(total=Sum('jumlah_bahan_masuk'))['total'] or 0
            )  # :contentReference[oaicite:21]{index=21}

            keluar = (
                models.detail_produksi.objects
                .filter(id_bahan=b, id_produksi__tanggal_produksi__range=[start_date, end_date])
                .aggregate(total=Sum('jumlah_bahan_keluar'))['total'] or 0
            )  # :contentReference[oaicite:22]{index=22}

            penyesuaian = _penyesuaian_bahan_dalam_periode(start_date, end_date, b)
            stok_akhir = stok_awal + masuk - keluar + penyesuaian

            bahan_data.append({
                'no': no,
                'nama': b.nama_bahan,
                'stok_awal': stok_awal,
                'masuk': masuk,
                'keluar': keluar,
                'penyesuaian': penyesuaian,
                'stok_akhir': stok_akhir,
            })
            no += 1

        # BAHAN BAKU 
        bahan_baku_data = []
        bahan_baku_qs = (
            models.bahan.objects
            .filter(jenis_bahan__icontains='baku')   # kategori bahan baku
            .order_by('nama_bahan')
        )

        no = 1
        for b in bahan_baku_qs:
            h_minus_1 = start_date - timedelta(days=1)

            # stok awal (akumulasi s.d. H-1)
            stok_awal = _stok_awal_bahan_dengan_so(start_date, b)

            # masuk (pemesanan bahan di periode)
            masuk = (
                models.detail_pemesanan_bahan.objects
                .filter(id_bahan=b, id_pemesanan__tanggal_pemesanan__range=[start_date, end_date])
                .aggregate(total=Sum('jumlah_bahan_masuk'))['total'] or 0
            )

            # keluar (dipakai di produksi di periode)
            keluar = (
                models.detail_produksi.objects
                .filter(id_bahan=b, id_produksi__tanggal_produksi__range=[start_date, end_date])
                .aggregate(total=Sum('jumlah_bahan_keluar'))['total'] or 0
            )

            # penyesuaian (SO di periode)
            penyesuaian = _penyesuaian_bahan_dalam_periode(start_date, end_date, b)

            stok_akhir = int(stok_awal) + int(masuk) - int(keluar) + int(penyesuaian)

            bahan_baku_data.append({
                'no': no,
                'nama': b.nama_bahan,
                'stok_awal': stok_awal,
                'masuk': masuk,
                'keluar': keluar,
                'penyesuaian': penyesuaian,
                'stok_akhir': stok_akhir,
            })
            no += 1


    context = {
        'produk_data': produk_data,
        'bahan_baku_data': bahan_baku_data,
        'bahan_data': bahan_data,
        'start_date': start_date,
        'end_date': end_date,
    }
    from weasyprint import HTML
    html_string = render_to_string('laporan/laporan_rekapitulasi_stok_pdf.html', context)
    pdf_bytes = HTML(string=html_string).write_pdf()

    filename = f"rekapitulasi_stok_{(start_date or '')}_{(end_date or '')}.pdf"
    resp = HttpResponse(pdf_bytes, content_type='application/pdf')
    resp['Content-Disposition'] = f'attachment; filename="{filename}"'
    return resp


'''LAPORAN ALIRAN BARANG'''
# ==== HELPER LAPORAN ALIRAN BARANG ====
def _is_pallet_name(nama):
    s = (nama or '').lower()
    return ('pallet' in s) or ('palet' in s)

def _eoe_q():
    return (
        Q(nama_produk__iregex=r'(^|[^A-Za-z0-9])EOE([^A-Za-z0-9]|$)') |
        Q(nama_produk__iregex=r'\bBottom\s+End\b')
    )

def _kebutuhan_map():
    # { id_bahan: (kebutuhan_mm_per_pallet, mm_per_roll) }
    rows = models.kebutuhan_pallet.objects.values('id_bahan', 'kebutuhan', 'mm_per_roll')
    return { r['id_bahan']: (int(r['kebutuhan'] or 0), int(r['mm_per_roll'] or 0)) for r in rows }

def _total_pallet_penuh_dalam(start_date, end_date):
    return (
        models.pallet_penuh.objects
        .filter(tanggal_event__range=[start_date, end_date])
        .aggregate(x=Sum('jumlah_pallet_penuh'))['x'] or 0
    )

def _total_pallet_penuh_per_tanggal(start_date, end_date):
    # return dict: {date: total_pallet_penuh_on_that_date}
    qs = (
        models.pallet_penuh.objects
        .filter(tanggal_event__range=[start_date, end_date])
        .values('tanggal_event')
        .annotate(x=Sum('jumlah_pallet_penuh'))
        .order_by('tanggal_event')
    )
    return { r['tanggal_event']: int(r['x'] or 0) for r in qs }

def _stok_sistem_produk_sampai(tanggal, produk):
    # Produk EOE/Bottom End: masuk dari pemesanan produk
    if models.produk.objects.filter(_eoe_q(), id_produk=produk.id_produk).exists():
        masuk = (
            models.detail_pemesanan_produk.objects
            .filter(id_produk=produk, id_pemesanan__tanggal_pemesanan__lte=tanggal)
            .aggregate(total=Sum('jumlah_produk_masuk'))['total'] or 0
        )
    else:
        masuk = (
            models.detail_produksi.objects
            .filter(id_produk=produk, id_produksi__tanggal_produksi__lte=tanggal)
            .aggregate(total=Sum('jumlah_produk'))['total'] or 0
        )

    keluar = (
        models.detail_pengiriman.objects
        .filter(id_produk=produk, id_pengiriman__tanggal_pengiriman__lte=tanggal)
        .aggregate(total=Sum('jumlah_produk_dikirim'))['total'] or 0
    )
    return int(masuk) - int(keluar)

def _stok_sistem_bahan_sampai(tanggal, bahan):
    # Masuk: pemesanan bahan
    masuk = (
        models.detail_pemesanan_bahan.objects
        .filter(id_bahan=bahan, id_pemesanan__tanggal_pemesanan__lte=tanggal)
        .aggregate(total=Sum('jumlah_bahan_masuk'))['total'] or 0
    )

    # Keluar:
    if _is_pallet_name(bahan.nama_bahan):
        # keluar = total pallet penuh s.d. tgl
        keluar = (
            models.pallet_penuh.objects
            .filter(tanggal_event__lte=tanggal)
            .aggregate(x=Sum('jumlah_pallet_penuh'))['x'] or 0
        )
    else:
        keb_map = _kebutuhan_map()
        if bahan.id_bahan in keb_map and 'pembantu' in (bahan.jenis_bahan or '').lower():
            per_pallet_mm, mm_per_roll = keb_map[bahan.id_bahan]
            if per_pallet_mm > 0 and mm_per_roll > 0:
                total_pallet = (
                    models.pallet_penuh.objects
                    .filter(tanggal_event__lte=tanggal)
                    .aggregate(x=Sum('jumlah_pallet_penuh'))['x'] or 0
                )
                total_mm = per_pallet_mm * int(total_pallet)
                keluar = total_mm // mm_per_roll  # roll terpakai
            else:
                keluar = 0
        else:
            # bahan baku → keluar dari produksi
            keluar = (
                models.detail_produksi.objects
                .filter(id_bahan=bahan, id_produksi__tanggal_produksi__lte=tanggal)
                .aggregate(total=Sum('jumlah_bahan_keluar'))['total'] or 0
            )

    return int(masuk) - int(keluar)

def _satuan_guess_bahan(bahan):
    nb = (bahan.nama_bahan or '').lower()
    jb = (bahan.jenis_bahan or '').lower()
    if _is_pallet_name(bahan.nama_bahan):
        return 'pcs'
    if 'band' in nb or 'film' in nb or 'roll' in nb:
        return 'roll'
    if 'baku' in jb:
        return 'sheets'
    if 'pembantu' in jb:
        return 'roll'  # default pembantu selain pallet
    return 'pcs'       # default baku

def _satuan_guess_produk(produk):
    np = (produk.nama_produk or '').lower()
    if 'sheet' in np or 'sheets' in np:
        return 'sheets'
    return 'pcs'

# ============================
# LAPORAN ALIRAN BARANG : HTML 
# ============================
from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils.dateparse import parse_date

def laporan_aliran_barang(request):
    start_date_str = request.GET.get('start_date')
    end_date_str   = request.GET.get('end_date')
    start_date = parse_date(start_date_str) if start_date_str else None
    end_date   = parse_date(end_date_str) if end_date_str else None

    # data untuk tabel (group by tanggal, merge No & Tanggal)
    groups = []   # [{ 'tanggal': date, 'rows': [ ... ] }]
    pdf_url = None

    if start_date and end_date:
        pdf_url = f"{reverse('laporan_aliran_barang_pdf')}?start_date={start_date}&end_date={end_date}"
        # Running balance per item (keyed by ('produk', id) atau ('bahan', id))
        balance = {}

        # 1) AWAL: siapkan saldo awal s.d. H-1 untuk semua entitas yang mungkin muncul
        h_minus_1 = start_date - timedelta(days=1)

        # Produk
        for p in models.produk.objects.all():
            balance[('produk', p.id_produk)] = _stok_sistem_produk_sampai(h_minus_1, p)

        # Bahan
        for b in models.bahan.objects.all():
            balance[('bahan', b.id_bahan)] = _stok_sistem_bahan_sampai(h_minus_1, b)

        # 2) Kumpulkan event movement (tanggal di range) -> list of dict
        events = []

        # 2a) Produk MASUK:
        #   - Non EOE: dari produksi
        non_eoe_ids = set(models.produk.objects.exclude(_eoe_q()).values_list('id_produk', flat=True))
        for r in (
            models.detail_produksi.objects
            .filter(id_produksi__tanggal_produksi__range=[start_date, end_date],
                    id_produk_id__in=non_eoe_ids)
            .values('id_produksi__tanggal_produksi', 'id_produk', 'id_produk__nama_produk')
            .annotate(q=Sum('jumlah_produk'))
            .order_by('id_produksi__tanggal_produksi', 'id_produk__nama_produk')
        ):
            tgl = r['id_produksi__tanggal_produksi']
            pid = r['id_produk']
            nama = r['id_produk__nama_produk']
            satuan = _satuan_guess_produk(models.produk(id_produk=pid, nama_produk=nama))
            key = ('produk', pid)
            masuk = int(r['q'] or 0)
            sisa = balance.get(key, 0) + masuk
            events.append({
                'tanggal': tgl, 'nama': nama, 'jenis': 'Produk', 'satuan': satuan,
                'masuk': masuk, 'keluar': 0, 'sisa': sisa,
                'ket': f"Masuk: Produksi {tgl}"
            })
            balance[key] = sisa

        #   - EOE/Bottom End: dari pemesanan produk
        eoe_ids = set(models.produk.objects.filter(_eoe_q()).values_list('id_produk', flat=True))
        for r in (
            models.detail_pemesanan_produk.objects
            .filter(id_pemesanan__tanggal_pemesanan__range=[start_date, end_date],
                    id_produk_id__in=eoe_ids)
            .values('id_pemesanan__tanggal_pemesanan', 'id_produk', 'id_produk__nama_produk')
            .annotate(q=Sum('jumlah_produk_masuk'))
            .order_by('id_pemesanan__tanggal_pemesanan', 'id_produk__nama_produk')
        ):
            tgl = r['id_pemesanan__tanggal_pemesanan']
            pid = r['id_produk']
            nama = r['id_produk__nama_produk']
            satuan = _satuan_guess_produk(models.produk(id_produk=pid, nama_produk=nama))
            key = ('produk', pid)
            masuk = int(r['q'] or 0)
            sisa = balance.get(key, 0) + masuk
            events.append({
                'tanggal': tgl, 'nama': nama, 'jenis': 'Produk', 'satuan': satuan,
                'masuk': masuk, 'keluar': 0, 'sisa': sisa,
                'ket': f"Masuk: Pemesanan Produk {tgl}"
            })
            balance[key] = sisa

        # 2b) Produk KELUAR: dari pengiriman
        for r in (
            models.detail_pengiriman.objects
            .filter(id_pengiriman__tanggal_pengiriman__range=[start_date, end_date])
            .values('id_pengiriman__tanggal_pengiriman', 'id_produk', 'id_produk__nama_produk')
            .annotate(q=Sum('jumlah_produk_dikirim'))
            .order_by('id_pengiriman__tanggal_pengiriman', 'id_produk__nama_produk')
        ):
            tgl = r['id_pengiriman__tanggal_pengiriman']
            pid = r['id_produk']
            nama = r['id_produk__nama_produk']
            satuan = _satuan_guess_produk(models.produk(id_produk=pid, nama_produk=nama))
            key = ('produk', pid)
            keluar = int(r['q'] or 0)
            sisa = balance.get(key, 0) - keluar
            events.append({
                'tanggal': tgl, 'nama': nama, 'jenis': 'Produk', 'satuan': satuan,
                'masuk': 0, 'keluar': keluar, 'sisa': sisa,
                'ket': f"Keluar: Pengiriman {tgl}"
            })
            balance[key] = sisa

        # 2c) Bahan MASUK: dari pemesanan bahan
        for r in (
            models.detail_pemesanan_bahan.objects
            .filter(id_pemesanan__tanggal_pemesanan__range=[start_date, end_date])
            .values('id_pemesanan__tanggal_pemesanan', 'id_bahan', 'id_bahan__nama_bahan', 'id_bahan__jenis_bahan')
            .annotate(q=Sum('jumlah_bahan_masuk'))
            .order_by('id_pemesanan__tanggal_pemesanan', 'id_bahan__nama_bahan')
        ):
            tgl = r['id_pemesanan__tanggal_pemesanan']
            bid = r['id_bahan']
            nama = r['id_bahan__nama_bahan']
            jenis = r['id_bahan__jenis_bahan'] or ''
            satuan = _satuan_guess_bahan(models.bahan(id_bahan=bid, nama_bahan=nama, jenis_bahan=jenis))
            key = ('bahan', bid)
            masuk = int(r['q'] or 0)
            sisa = balance.get(key, 0) + masuk
            jenis_disp = 'Bahan Baku' if 'baku' in jenis.lower() else 'Bahan Pembantu'
            events.append({
                'tanggal': tgl, 'nama': nama, 'jenis': jenis_disp, 'satuan': satuan,
                'masuk': masuk, 'keluar': 0, 'sisa': sisa,
                'ket': f"Masuk: Pemesanan Bahan {tgl}"
            })
            balance[key] = sisa

        # 2d) Bahan KELUAR:
        #    - Bahan baku: dari produksi
        for r in (
            models.detail_produksi.objects
            .filter(id_produksi__tanggal_produksi__range=[start_date, end_date], id_bahan__jenis_bahan__icontains='baku')
            .values('id_produksi__tanggal_produksi', 'id_bahan', 'id_bahan__nama_bahan', 'id_bahan__jenis_bahan')
            .annotate(q=Sum('jumlah_bahan_keluar'))
            .order_by('id_produksi__tanggal_produksi', 'id_bahan__nama_bahan')
        ):
            tgl = r['id_produksi__tanggal_produksi']
            bid = r['id_bahan']
            nama = r['id_bahan__nama_bahan']
            jenis = r['id_bahan__jenis_bahan'] or ''
            satuan = _satuan_guess_bahan(models.bahan(id_bahan=bid, nama_bahan=nama, jenis_bahan=jenis))
            key = ('bahan', bid)
            keluar = int(r['q'] or 0)
            sisa = balance.get(key, 0) - keluar
            events.append({
                'tanggal': tgl, 'nama': nama, 'jenis': 'Bahan Baku', 'satuan': satuan,
                'masuk': 0, 'keluar': keluar, 'sisa': sisa,
                'ket': f"Keluar: Produksi {tgl}"
            })
            balance[key] = sisa

        #    - Pallet (pembantu – pallet): dari pallet_penuh per tanggal
        pallet_per_tgl = _total_pallet_penuh_per_tanggal(start_date, end_date)
        for b in models.bahan.objects.filter(jenis_bahan__icontains='pembantu'):
            if _is_pallet_name(b.nama_bahan):
                key = ('bahan', b.id_bahan)
                for tgl, jml in pallet_per_tgl.items():
                    if jml <= 0: 
                        continue
                    satuan = _satuan_guess_bahan(b)
                    sisa = balance.get(key, 0) - int(jml)
                    events.append({
                        'tanggal': tgl, 'nama': b.nama_bahan, 'jenis': 'Bahan Pembantu - Pallet', 'satuan': satuan,
                        'masuk': 0, 'keluar': int(jml), 'sisa': sisa,
                        'ket': f"Keluar: Pallet Penuh {tgl}"
                    })
                    balance[key] = sisa

        #    - Wrapping (pembantu – roll): kebutuhan per pallet → roll terpakai per tanggal
        keb_map = _kebutuhan_map()
        for b in models.bahan.objects.filter(jenis_bahan__icontains='pembantu'):
            if b.id_bahan in keb_map and not _is_pallet_name(b.nama_bahan):
                per_mm, per_roll = keb_map[b.id_bahan]
                if per_mm > 0 and per_roll > 0:
                    key = ('bahan', b.id_bahan)
                    for tgl, pallet_hari_ini in pallet_per_tgl.items():
                        if pallet_hari_ini <= 0:
                            continue
                        roll_terpakai = (per_mm * int(pallet_hari_ini)) // per_roll
                        if roll_terpakai <= 0:
                            continue
                        satuan = _satuan_guess_bahan(b)
                        sisa = balance.get(key, 0) - roll_terpakai
                        events.append({
                            'tanggal': tgl, 'nama': b.nama_bahan, 'jenis': 'Bahan Pembantu - Wrap', 'satuan': satuan,
                            'masuk': 0, 'keluar': roll_terpakai, 'sisa': sisa,
                            'ket': f"Keluar: Wrapping (berdasar Pallet Penuh) {tgl}"
                        })
                        balance[key] = sisa

        # 3) Sort semua events (tgl, nama)
        events.sort(key=lambda x: (x['tanggal'], x['nama']))

        # 4) Group by tanggal untuk kebutuhan merge No & Tanggal
        from itertools import groupby
        for tgl, rows_iter in groupby(events, key=lambda x: x['tanggal']):
            rows = list(rows_iter)
            groups.append({'tanggal': tgl, 'rows': rows})

    context = {
        'groups': groups,
        'start_date': start_date,
        'end_date': end_date,
        'pdf_url': pdf_url,
    }
    return render(request, 'laporan/laporan_aliran_barang.html', context)

# ===========================
# LAPORAN ALIRAN BARANG : PDF
# ===========================
def laporan_aliran_barang_pdf(request):
    start_date_str = request.GET.get('start_date')
    end_date_str   = request.GET.get('end_date')
    start_date = parse_date(start_date_str) if start_date_str else None
    end_date   = parse_date(end_date_str) if end_date_str else None
    if not (start_date and end_date):
        return redirect('laporan_aliran_barang')

    # Reuse logic dari HTML (kita panggil fungsi helper grouping di atas)
    # Untuk menghindari duplikasi, kita panggil lagi laporan_aliran_barang() logic ringkas:
    # — atau copy blok kalkulasi di atas. Di sini aku copy ringkas:

    balance = {}
    h_minus_1 = start_date - timedelta(days=1)

    for p in models.produk.objects.all():
        balance[('produk', p.id_produk)] = _stok_sistem_produk_sampai(h_minus_1, p)
    for b in models.bahan.objects.all():
        balance[('bahan', b.id_bahan)] = _stok_sistem_bahan_sampai(h_minus_1, b)

    events = []
    # (SALIN blok 2a s.d. 2d dari view HTML di atas – isinya sama persis)
    # ---- mulai salin ----
    non_eoe_ids = set(models.produk.objects.exclude(_eoe_q()).values_list('id_produk', flat=True))
    for r in (
        models.detail_produksi.objects
        .filter(id_produksi__tanggal_produksi__range=[start_date, end_date],
                id_produk_id__in=non_eoe_ids)
        .values('id_produksi__tanggal_produksi', 'id_produk', 'id_produk__nama_produk')
        .annotate(q=Sum('jumlah_produk'))
        .order_by('id_produksi__tanggal_produksi', 'id_produk__nama_produk')
    ):
        tgl = r['id_produksi__tanggal_produksi']
        pid = r['id_produk']; nama = r['id_produk__nama_produk']
        satuan = _satuan_guess_produk(models.produk(id_produk=pid, nama_produk=nama))
        key = ('produk', pid); masuk = int(r['q'] or 0)
        sisa = balance.get(key, 0) + masuk
        events.append({'tanggal': tgl, 'nama': nama, 'jenis': 'Produk', 'satuan': satuan,
                       'masuk': masuk, 'keluar': 0, 'sisa': sisa,
                       'ket': f"Masuk: Produksi {tgl}"})
        balance[key] = sisa

    eoe_ids = set(models.produk.objects.filter(_eoe_q()).values_list('id_produk', flat=True))
    for r in (
        models.detail_pemesanan_produk.objects
        .filter(id_pemesanan__tanggal_pemesanan__range=[start_date, end_date],
                id_produk_id__in=eoe_ids)
        .values('id_pemesanan__tanggal_pemesanan', 'id_produk', 'id_produk__nama_produk')
        .annotate(q=Sum('jumlah_produk_masuk'))
        .order_by('id_pemesanan__tanggal_pemesanan', 'id_produk__nama_produk')
    ):
        tgl = r['id_pemesanan__tanggal_pemesanan']
        pid = r['id_produk']; nama = r['id_produk__nama_produk']
        satuan = _satuan_guess_produk(models.produk(id_produk=pid, nama_produk=nama))
        key = ('produk', pid); masuk = int(r['q'] or 0)
        sisa = balance.get(key, 0) + masuk
        events.append({'tanggal': tgl, 'nama': nama, 'jenis': 'Produk', 'satuan': satuan,
                       'masuk': masuk, 'keluar': 0, 'sisa': sisa,
                       'ket': f"Masuk: Pemesanan Produk {tgl}"})
        balance[key] = sisa

    for r in (
        models.detail_pengiriman.objects
        .filter(id_pengiriman__tanggal_pengiriman__range=[start_date, end_date])
        .values('id_pengiriman__tanggal_pengiriman', 'id_produk', 'id_produk__nama_produk')
        .annotate(q=Sum('jumlah_produk_dikirim'))
        .order_by('id_pengiriman__tanggal_pengiriman', 'id_produk__nama_produk')
    ):
        tgl = r['id_pengiriman__tanggal_pengiriman']
        pid = r['id_produk']; nama = r['id_produk__nama_produk']
        satuan = _satuan_guess_produk(models.produk(id_produk=pid, nama_produk=nama))
        key = ('produk', pid); keluar = int(r['q'] or 0)
        sisa = balance.get(key, 0) - keluar
        events.append({'tanggal': tgl, 'nama': nama, 'jenis': 'Produk', 'satuan': satuan,
                       'masuk': 0, 'keluar': keluar, 'sisa': sisa,
                       'ket': f"Keluar: Pengiriman {tgl}"})
        balance[key] = sisa

    for r in (
        models.detail_pemesanan_bahan.objects
        .filter(id_pemesanan__tanggal_pemesanan__range=[start_date, end_date])
        .values('id_pemesanan__tanggal_pemesanan', 'id_bahan', 'id_bahan__nama_bahan', 'id_bahan__jenis_bahan')
        .annotate(q=Sum('jumlah_bahan_masuk'))
        .order_by('id_pemesanan__tanggal_pemesanan', 'id_bahan__nama_bahan')
    ):
        tgl = r['id_pemesanan__tanggal_pemesanan']
        bid = r['id_bahan']; nama = r['id_bahan__nama_bahan']; jenis = r['id_bahan__jenis_bahan'] or ''
        satuan = _satuan_guess_bahan(models.bahan(id_bahan=bid, nama_bahan=nama, jenis_bahan=jenis))
        key = ('bahan', bid); masuk = int(r['q'] or 0)
        sisa = balance.get(key, 0) + masuk
        jenis_disp = 'Bahan Baku' if 'baku' in jenis.lower() else 'Bahan Pembantu'
        events.append({'tanggal': tgl, 'nama': nama, 'jenis': jenis_disp, 'satuan': satuan,
                       'masuk': masuk, 'keluar': 0, 'sisa': sisa,
                       'ket': f"Masuk: Pemesanan Bahan {tgl}"})
        balance[key] = sisa

    for r in (
        models.detail_produksi.objects
        .filter(id_produksi__tanggal_produksi__range=[start_date, end_date], id_bahan__jenis_bahan__icontains='baku')
        .values('id_produksi__tanggal_produksi', 'id_bahan', 'id_bahan__nama_bahan', 'id_bahan__jenis_bahan')
        .annotate(q=Sum('jumlah_bahan_keluar'))
        .order_by('id_produksi__tanggal_produksi', 'id_bahan__nama_bahan')
    ):
        tgl = r['id_produksi__tanggal_produksi']
        bid = r['id_bahan']; nama = r['id_bahan__nama_bahan']; jenis = r['id_bahan__jenis_bahan'] or ''
        satuan = _satuan_guess_bahan(models.bahan(id_bahan=bid, nama_bahan=nama, jenis_bahan=jenis))
        key = ('bahan', bid); keluar = int(r['q'] or 0)
        sisa = balance.get(key, 0) - keluar
        events.append({'tanggal': tgl, 'nama': nama, 'jenis': 'Bahan Baku', 'satuan': satuan,
                       'masuk': 0, 'keluar': keluar, 'sisa': sisa,
                       'ket': f"Keluar: Produksi {tgl}"})
        balance[key] = sisa

    pallet_per_tgl = _total_pallet_penuh_per_tanggal(start_date, end_date)
    for b in models.bahan.objects.filter(jenis_bahan__icontains='pembantu'):
        if _is_pallet_name(b.nama_bahan):
            key = ('bahan', b.id_bahan)
            for tgl, jml in pallet_per_tgl.items():
                if jml <= 0: 
                    continue
                satuan = _satuan_guess_bahan(b)
                sisa = balance.get(key, 0) - int(jml)
                events.append({'tanggal': tgl, 'nama': b.nama_bahan, 'jenis': 'Bahan Pembantu', 'satuan': satuan,
                               'masuk': 0, 'keluar': int(jml), 'sisa': sisa,
                               'ket': f"Keluar: Pallet Penuh {tgl}"})
                balance[key] = sisa

    keb_map = _kebutuhan_map()
    for b in models.bahan.objects.filter(jenis_bahan__icontains='pembantu'):
        if b.id_bahan in keb_map and not _is_pallet_name(b.nama_bahan):
            per_mm, per_roll = keb_map[b.id_bahan]
            if per_mm > 0 and per_roll > 0:
                key = ('bahan', b.id_bahan)
                for tgl, pallet_hari_ini in pallet_per_tgl.items():
                    if pallet_hari_ini <= 0:
                        continue
                    roll_terpakai = (per_mm * int(pallet_hari_ini)) // per_roll
                    if roll_terpakai <= 0:
                        continue
                    satuan = _satuan_guess_bahan(b)
                    sisa = balance.get(key, 0) - roll_terpakai
                    events.append({'tanggal': tgl, 'nama': b.nama_bahan, 'jenis': 'Bahan Pembantu', 'satuan': satuan,
                                   'masuk': 0, 'keluar': roll_terpakai, 'sisa': sisa,
                                   'ket': f"Keluar: Wrapping (berdasarkan Pallet Penuh) {tgl}"})
                    balance[key] = sisa
    # ---- selesai salin ----

    events.sort(key=lambda x: (x['tanggal'], x['nama']))
    from itertools import groupby
    groups = []
    for tgl, rows_iter in groupby(events, key=lambda x: x['tanggal']):
        rows = list(rows_iter)
        groups.append({'tanggal': tgl, 'rows': rows})

    context = {'groups': groups, 'start_date': start_date, 'end_date': end_date}

    # Render PDF
    html = render(request, 'laporan/laporan_aliran_barang_pdf.html', context)
    from weasyprint import HTML
    pdf = HTML(string=html.content.decode('utf-8')).write_pdf()
    from django.http import HttpResponse
    resp = HttpResponse(pdf, content_type='application/pdf')
    resp['Content-Disposition'] = f'attachment; filename="laporan_aliran_barang_{start_date}_{end_date}.pdf"'
    return resp


'''LAPORAN PENGIRIMAN'''
# =========================
# LAPORAN PENGIRIMAN : HTML
# =========================
def _get_no_sj(h):
    candidates = [
        'nomor_surat_jalan', 'no_surat_jalan',
        'nomor_sj', 'no_sj',
        'nomor_surat', 'no_surat',
        'kode_sj', 'kode_surat_jalan',
    ]
    for name in candidates:
        val = getattr(h, name, None)
        if val:
            return str(val)
    return str(getattr(h, 'id_pengiriman', h.pk))


def _pallet_per_tanggal(start_date, end_date):
    qs = (
        models.pallet_penuh.objects
        .filter(tanggal_event__range=[start_date, end_date])
        .values('tanggal_event')
        .annotate(x=Sum('jumlah_pallet_penuh'))
    )
    return { r['tanggal_event']: int(r['x'] or 0) for r in qs }

CAN_TARGETS = {'307_211': 1_500_000, '311': 2_300_000, '202': 2_000_000}

def _fmt_pct(num, den): return 0.0 if not den else round((float(num)/float(den))*100.0, 2)

def _build_pengiriman_context(start_date, end_date):
    mini = {
        'qty_307':0,'qty_211':0,'qty_311':0,'qty_202':0,
        'qty_307_211':0,'qty_total_4':0,
        'target_307_211':CAN_TARGETS['307_211'],
        'target_311':CAN_TARGETS['311'],
        'target_202':CAN_TARGETS['202'],
        'pct_307_211':0.0,'pct_311':0.0,'pct_202':0.0,
    }
    rows = []

    base_qs = (models.detail_pengiriman.objects
               .filter(id_pengiriman__tanggal_pengiriman__range=[start_date, end_date])
               .select_related('id_produk','id_pengiriman','id_pengiriman__id_customer'))

    agg = base_qs.values('id_produk__jenis_produk').annotate(q=Sum('jumlah_produk_dikirim'))
    bucket = { (r['id_produk__jenis_produk'] or '').strip().upper(): int(r['q'] or 0) for r in agg }
    mini['qty_307'] = bucket.get('CAN 307',0)
    mini['qty_211'] = bucket.get('CAN 211',0)
    mini['qty_311'] = bucket.get('CAN 311',0)
    mini['qty_202'] = bucket.get('CAN 202',0)
    mini['qty_307_211'] = mini['qty_307'] + mini['qty_211']
    mini['qty_total_4'] = mini['qty_307'] + mini['qty_211'] + mini['qty_311'] + mini['qty_202']
    mini['pct_307_211'] = _fmt_pct(mini['qty_307_211'], CAN_TARGETS['307_211'])
    mini['pct_311']     = _fmt_pct(mini['qty_311'],     CAN_TARGETS['311'])
    mini['pct_202']     = _fmt_pct(mini['qty_202'],     CAN_TARGETS['202'])

   
    # Pallet per tanggal
    pallet_map = _pallet_per_tanggal(start_date, end_date)

    # Kumpulkan detail per tanggal
    buckets = defaultdict(list)
    headers = (models.pengiriman.objects
               .filter(tanggal_pengiriman__range=[start_date, end_date])
               .select_related('id_customer')
               .order_by('tanggal_pengiriman','id_pengiriman'))
    for h in headers:
        dets = (models.detail_pengiriman.objects
                .filter(id_pengiriman=h)
                .select_related('id_produk')
                .order_by('id_produk__nama_produk'))
        for d in dets:
            buckets[h.tanggal_pengiriman].append({
                'tanggal':  h.tanggal_pengiriman,
                'no_sj': _get_no_sj(h),

                'customer': getattr(h.id_customer,'nama_customer',str(h.id_customer)) if getattr(h,'id_customer',None) else '-',
                'produk':   getattr(d.id_produk,'nama_produk',str(d.id_produk)),
                'jenis':    (getattr(d.id_produk,'jenis_produk','') or '').upper(),
                'qty':      int(getattr(d,'jumlah_produk_dikirim',0) or 0),
                'satuan':   'pcs',
            })

    # Flatten: sisipkan kolom pallet dengan rowspan di baris pertama per tanggal
    for tgl in sorted(buckets.keys()):
        lst = buckets[tgl]
        rowspan = len(lst)
        pallet_used = pallet_map.get(tgl, 0)
        for idx, r in enumerate(lst):
            r['pallet']  = pallet_used if idx == 0 else None
            
            rows.append(r)

    return mini, rows

def laporan_pengiriman(request):
    # filters
    start_date_str = request.GET.get('start_date')
    end_date_str   = request.GET.get('end_date')
    start_date = parse_date(start_date_str) if start_date_str else None
    end_date   = parse_date(end_date_str) if end_date_str else None

    # default context
    mini = {
        'qty_307': 0, 'qty_211': 0, 'qty_311': 0, 'qty_202': 0,
        'qty_307_211': 0, 'qty_total_4': 0,
        'pct_307_211': 0.0, 'pct_311': 0.0, 'pct_202': 0.0,
        'target_307_211': CAN_TARGETS['307_211'],
        'target_311': CAN_TARGETS['311'],
        'target_202': CAN_TARGETS['202'],
    }
    rows = []
    pdf_url = None

    if start_date and end_date:
        pdf_url = f"{reverse('laporan_pengiriman_pdf')}?start_date={start_date}&end_date={end_date}"

        # ==== RINGKASAN CAN ====
        base_qs = models.detail_pengiriman.objects.filter(
            id_pengiriman__tanggal_pengiriman__range=[start_date, end_date]
        ).select_related('id_produk', 'id_pengiriman', 'id_pengiriman__id_customer')

        # ambil total per jenis dari master produk.jenis_produk
        agg = (
            base_qs.values('id_produk__jenis_produk')
            .annotate(q=Sum('jumlah_produk_dikirim'))
        )
        # normalize nama jenis ke upper (biar aman)
        by_jenis = { (r['id_produk__jenis_produk'] or '').strip().upper(): int(r['q'] or 0) for r in agg }

        mini['qty_307'] = by_jenis.get('CAN 307', 0)
        mini['qty_211'] = by_jenis.get('CAN 211', 0)
        mini['qty_311'] = by_jenis.get('CAN 311', 0)
        mini['qty_202'] = by_jenis.get('CAN 202', 0)
        mini['qty_307_211'] = mini['qty_307'] + mini['qty_211']
        mini['qty_total_4'] = mini['qty_307'] + mini['qty_211'] + mini['qty_311'] + mini['qty_202']

        mini['pct_307_211'] = _fmt_pct(mini['qty_307_211'], CAN_TARGETS['307_211'])
        mini['pct_311']     = _fmt_pct(mini['qty_311'],     CAN_TARGETS['311'])
        mini['pct_202']     = _fmt_pct(mini['qty_202'],     CAN_TARGETS['202'])

        # ==== TABEL DETAIL (mirip read_pengiriman) ====
        # ambil daftar header pengiriman dalam periode, lalu join details
        headers = (
            models.pengiriman.objects
            .filter(tanggal_pengiriman__range=[start_date, end_date])
            .select_related('id_customer')
            .order_by('tanggal_pengiriman', 'id_pengiriman')
        )

        # bentuk rows: satu baris per detail (tanggal, no, customer, produk, qty, ket)
        for h in headers:
            details = (
                models.detail_pengiriman.objects
                .filter(id_pengiriman=h)
                .select_related('id_produk')
                .order_by('id_produk__nama_produk')
            )
            for d in details:
                rows.append({
                    'tanggal': h.tanggal_pengiriman,
                    'no_sj':   _get_no_sj(h),
                    'customer': getattr(h.id_customer, 'nama_customer', str(h.id_customer)) if getattr(h, 'id_customer', None) else '-',
                    'produk':  getattr(d.id_produk, 'nama_produk', str(d.id_produk)),
                    'jenis':   (getattr(d.id_produk, 'jenis_produk', '') or '').upper(),
                    'qty':     int(getattr(d, 'jumlah_produk_dikirim', 0) or 0),
                    'satuan':  'pcs',
                })

    context = {
        'start_date': start_date,
        'end_date': end_date,
        'mini': mini,
        'rows': rows,
        'pdf_url': pdf_url,
    }
    return render(request, 'laporan/laporan_pengiriman.html', context)

# ========================
# LAPORAN PENGIRIMAN : PDF
# ========================
def laporan_pengiriman_pdf(request):
    start_date = parse_date(request.GET.get('start_date') or '')
    end_date   = parse_date(request.GET.get('end_date') or '')
    if not (start_date and end_date):
        return redirect('laporan_pengiriman')

    mini, rows = _build_pengiriman_context(start_date, end_date)
    context = {'start_date': start_date, 'end_date': end_date, 'mini': mini, 'rows': rows}

    html = render(request, 'laporan/laporan_pengiriman_pdf.html', context)  # << template PDF khusus
    from weasyprint import HTML
    pdf = HTML(string=html.content.decode('utf-8')).write_pdf()
    from django.http import HttpResponse
    resp = HttpResponse(pdf, content_type='application/pdf')
    resp['Content-Disposition'] = f'attachment; filename="laporan_pengiriman_{start_date}_{end_date}.pdf"'
    return resp


'''LAPORAN STOK OPNAME'''
# =========================
# LAPORAN STOK OPNAME (HELPERS)
# =========================
from django.db.models import Sum, Q

def _eoe_q():
    return (
        Q(nama_produk__iregex=r'(^|[^A-Za-z0-9])EOE([^A-Za-z0-9]|$)') |
        Q(nama_produk__iregex=r'\bBottom\s+End\b')
    )

def _total_pallet_penuh_dalam(start_date, end_date):
    return (
        models.pallet_penuh.objects
        .filter(tanggal_event__range=[start_date, end_date])
        .aggregate(x=Sum('jumlah_pallet_penuh'))['x'] or 0
    )

def _is_pallet_name(nama):
    s = (nama or '').lower()
    return ('pallet' in s) or ('palet' in s)

def _kebutuhan_map():
    rows = models.kebutuhan_pallet.objects.values('id_bahan', 'kebutuhan', 'mm_per_roll')
    return { r['id_bahan']: (int(r['kebutuhan'] or 0), int(r['mm_per_roll'] or 0)) for r in rows }

# SO fisik di tgl (pakai __date biar aman kalau field DateTimeField)
def _so_fisik_produk(tgl, produk):
    return (
        models.detail_so_produk.objects
        .filter(id_stok_opname__tanggal_stok_opname=tgl, id_produk=produk)
        .aggregate(x=Sum('stok_fisik_produk'))['x'] or 0
    )

def _so_fisik_bahan(tgl, bahan):
    return (
        models.detail_so_bahan.objects
        .filter(id_stok_opname__tanggal_stok_opname=tgl, id_bahan=bahan)
        .aggregate(x=Sum('stok_fisik_bahan'))['x'] or 0
    )

# Keluar bahan pembantu kumulatif [start..tgl] (logika pallet/kebutuhan)
def _keluar_bahan_pembantu_dalam(start_date, tgl, bahan, keb_map):
    if _is_pallet_name(bahan.nama_bahan):
        return int(_total_pallet_penuh_dalam(start_date, tgl))
    if bahan.id_bahan in keb_map and 'pembantu' in (bahan.jenis_bahan or '').lower():
        per_pallet_mm, mm_per_roll = keb_map[bahan.id_bahan]
        if per_pallet_mm > 0 and mm_per_roll > 0:
            total_pallet_period = _total_pallet_penuh_dalam(start_date, tgl)
            total_mm = per_pallet_mm * total_pallet_period
            return total_mm // mm_per_roll
        return 0
    return (
        models.detail_produksi.objects
        .filter(id_bahan=bahan, id_produksi__tanggal_produksi__range=[start_date, tgl])
        .aggregate(x=Sum('jumlah_bahan_keluar'))['x'] or 0
    )

# ================================================
# BUILDER: SISTEM (tanpa penyesuaian) + FISIK + SELISIH, per tanggal SO
# ================================================
def _build_so_rows_for_date_like_rekap_sistem(start_date, tgl):
    """
    Untuk tgl SO:
      stok_awal    = _stok_awal_*_dengan_so(start_date)
      masuk        = kumulatif [start_date..tgl]
      keluar       = kumulatif [start_date..tgl]
      stok_akhir   = stok_awal + masuk - keluar   (TANPA penyesuaian)
      stok_fisik   = total fisik di tgl
      selisih      = stok_fisik - stok_akhir
    Item hanya yang di-SO pada tanggal tsb (ringkas & relevan).
    """
    eoe_ids = set(models.produk.objects.filter(_eoe_q()).values_list('id_produk', flat=True))
    keb_map = _kebutuhan_map()

    # --- ambil item yang di-SO pada tgl
    produk_ids = (
        models.detail_so_produk.objects
        .filter(id_stok_opname__tanggal_stok_opname=tgl, id_produk__isnull=False)
        .values_list('id_produk', flat=True).distinct()
    )
    baku_ids = (
        models.detail_so_bahan.objects
        .filter(id_stok_opname__tanggal_stok_opname=tgl, id_bahan__jenis_bahan__icontains='baku')
        .values_list('id_bahan', flat=True).distinct()
    )
    pembantu_ids = (
        models.detail_so_bahan.objects
        .filter(id_stok_opname__tanggal_stok_opname=tgl, id_bahan__jenis_bahan__icontains='pembantu')
        .values_list('id_bahan', flat=True).distinct()
    )

    # ===== PRODUK =====
    produk_rows = []
    for pid in produk_ids:
        p = models.produk.objects.get(pk=pid)

        stok_awal = _stok_awal_produk_dengan_so(start_date, p)

        if p.id_produk in eoe_ids:
            masuk = (
                models.detail_pemesanan_produk.objects
                .filter(id_produk=p, id_pemesanan__tanggal_pemesanan__range=[start_date, tgl])
                .aggregate(x=Sum('jumlah_produk_masuk'))['x'] or 0
            )
        else:
            masuk = (
                models.detail_produksi.objects
                .filter(id_produk=p, id_produksi__tanggal_produksi__range=[start_date, tgl])
                .aggregate(x=Sum('jumlah_produk'))['x'] or 0
            )

        keluar = (
            models.detail_pengiriman.objects
            .filter(id_produk=p, id_pengiriman__tanggal_pengiriman__range=[start_date, tgl])
            .aggregate(x=Sum('jumlah_produk_dikirim'))['x'] or 0
        )

        stok_akhir = int(stok_awal or 0) + int(masuk or 0) - int(keluar or 0)  # TANPA penyesuaian
        stok_fisik = _so_fisik_produk(tgl, p)
        selisih = int(stok_fisik) - int(stok_akhir)

        produk_rows.append({
            'nama': p.nama_produk,
            'stok_awal': int(stok_awal or 0),
            'masuk': int(masuk or 0),
            'keluar': int(keluar or 0),
            'stok_akhir': int(stok_akhir or 0),
            'stok_fisik': int(stok_fisik or 0),
            'selisih': int(selisih or 0),
        })

    # ===== BAHAN BAKU =====
    baku_rows = []
    for bid in baku_ids:
        b = models.bahan.objects.get(pk=bid)

        stok_awal = _stok_awal_bahan_dengan_so(start_date, b)

        masuk = (
            models.detail_pemesanan_bahan.objects
            .filter(id_bahan=b, id_pemesanan__tanggal_pemesanan__range=[start_date, tgl])
            .aggregate(x=Sum('jumlah_bahan_masuk'))['x'] or 0
        )
        keluar = (
            models.detail_produksi.objects
            .filter(id_bahan=b, id_produksi__tanggal_produksi__range=[start_date, tgl])
            .aggregate(x=Sum('jumlah_bahan_keluar'))['x'] or 0
        )

        stok_akhir = int(stok_awal or 0) + int(masuk or 0) - int(keluar or 0)  # TANPA penyesuaian
        stok_fisik = _so_fisik_bahan(tgl, b)
        selisih = int(stok_fisik) - int(stok_akhir)

        baku_rows.append({
            'nama': b.nama_bahan,
            'stok_awal': int(stok_awal or 0),
            'masuk': int(masuk or 0),
            'keluar': int(keluar or 0),
            'stok_akhir': int(stok_akhir or 0),
            'stok_fisik': int(stok_fisik or 0),
            'selisih': int(selisih or 0),
        })

    # ===== BAHAN PEMBANTU =====
    pembantu_rows = []
    for bid in pembantu_ids:
        b = models.bahan.objects.get(pk=bid)

        stok_awal = _stok_awal_bahan_dengan_so(start_date, b)

        masuk = (
            models.detail_pemesanan_bahan.objects
            .filter(id_bahan=b, id_pemesanan__tanggal_pemesanan__range=[start_date, tgl])
            .aggregate(x=Sum('jumlah_bahan_masuk'))['x'] or 0
        )
        keluar = _keluar_bahan_pembantu_dalam(start_date, tgl, b, keb_map)

        stok_akhir = int(stok_awal or 0) + int(masuk or 0) - int(keluar or 0)  # TANPA penyesuaian
        stok_fisik = _so_fisik_bahan(tgl, b)
        selisih = int(stok_fisik) - int(stok_akhir)

        pembantu_rows.append({
            'nama': b.nama_bahan,
            'stok_awal': int(stok_awal or 0),
            'masuk': int(masuk or 0),
            'keluar': int(keluar or 0),
            'stok_akhir': int(stok_akhir or 0),
            'stok_fisik': int(stok_fisik or 0),
            'selisih': int(selisih or 0),
        })

    return produk_rows, baku_rows, pembantu_rows



# =========================
# LAPORAN STOK OPNAME : HTML
# =========================
@login_required(login_url='login')
@role_required(['ppic', 'manajer'])
def laporan_stok_opname(request):
    start_date = parse_date(request.GET.get('start_date') or '')
    end_date   = parse_date(request.GET.get('end_date') or '')
    pdf_url = None
    groups = []

    if start_date and end_date:
        if start_date > end_date:
            start_date, end_date = end_date, start_date
        pdf_url = f"{reverse('laporan_stok_opname_pdf')}?start_date={start_date}&end_date={end_date}"

        tanggal_list = (
            models.stok_opname.objects
            .filter(tanggal_stok_opname__range=[start_date, end_date])   # aman utk DateTimeField
            .order_by('tanggal_stok_opname')
            .values_list('tanggal_stok_opname', flat=True)
            .distinct()
        )

        for tgl_dt in tanggal_list:
            tgl = getattr(tgl_dt, 'date', lambda: tgl_dt)()   # normalize ke date
            produk_rows, baku_rows, pembantu_rows = _build_so_rows_for_date_like_rekap_sistem(start_date, tgl)
            groups.append({
                'tanggal': tgl,
                'produk_rows': produk_rows,
                'baku_rows': baku_rows,
                'pembantu_rows': pembantu_rows,
            })

    return render(request, 'laporan/laporan_stok_opname.html', {
        'start_date': start_date, 'end_date': end_date,
        'groups': groups, 'pdf_url': pdf_url,
    })


# =========================
# LAPORAN STOK OPNAME : PDF
# =========================
@login_required(login_url='login')
@role_required(['ppic', 'manajer'])
def laporan_stok_opname_pdf(request):
    start_date = parse_date(request.GET.get('start_date') or '')
    end_date   = parse_date(request.GET.get('end_date') or '')
    if not (start_date and end_date):
        return redirect('laporan_stok_opname')
    if start_date > end_date:
        start_date, end_date = end_date, start_date

    groups = []
    tanggal_list = (
        models.stok_opname.objects
        .filter(tanggal_stok_opname__range=[start_date, end_date])
        .order_by('tanggal_stok_opname')
        .values_list('tanggal_stok_opname', flat=True)
        .distinct()
    )
    for tgl_dt in tanggal_list:
        tgl = getattr(tgl_dt, 'date', lambda: tgl_dt)()
        produk_rows, baku_rows, pembantu_rows = _build_so_rows_for_date_like_rekap_sistem(start_date, tgl)
        groups.append({
            'tanggal': tgl,
            'produk_rows': produk_rows,
            'baku_rows': baku_rows,
            'pembantu_rows': pembantu_rows,
        })

    html = render(request, 'laporan/laporan_stok_opname_pdf.html', {
        'start_date': start_date, 'end_date': end_date, 'groups': groups,
    })
    from weasyprint import HTML
    pdf = HTML(string=html.content.decode('utf-8')).write_pdf()
    from django.http import HttpResponse
    resp = HttpResponse(pdf, content_type='application/pdf')
    resp['Content-Disposition'] = f'attachment; filename="laporan_stok_opname_{start_date}_{end_date}.pdf"'
    return resp


