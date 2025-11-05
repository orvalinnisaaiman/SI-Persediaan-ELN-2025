def is_ppic(request):
    return{'is_ppic': request.user.groups.filter(name='ppic').exists()}
def is_produksi(request):
    return{'is_produksi': request.user.groups.filter(name='produksi').exists()}
def is_qc(request):
    return{'is_qc': request.user.groups.filter(name='qc').exists()}
def is_finance(request):
    return{'is_finance': request.user.groups.filter(name='finance').exists()}
def is_manajer(request):
    return{'is_manajer': request.user.groups.filter(name='manajer').exists()}

