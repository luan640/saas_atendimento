from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .models import Loja
from .forms import LojaForm

@login_required
def owner_shops(request):
    # Apenas Dono
    if not getattr(request.user, 'is_owner', False):
        return redirect('accounts:owner_login')

    if request.method == 'POST':
        form = LojaForm(request.POST)
        if form.is_valid():
            loja = form.save(commit=False)
            loja.owner = request.user
            loja.save()
            messages.success(request, 'Loja criada com sucesso!')
            return redirect('cadastro:owner_shops')
    else:
        form = LojaForm()

    lojas = request.user.lojas.all().order_by('-criada_em')

    template = 'loja/owner_shops.html'
    if request.headers.get('HX-Request'):
        template = 'loja/partials/owner_shops.html'
    return render(request, template, {
        'form': form,
        'lojas': lojas,
    })