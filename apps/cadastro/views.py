from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import LojaForm
from .models import Loja


@login_required
def owner_shops(request):
    """Lista e cria lojas do proprietário sem recarregar a página."""
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
            form = LojaForm()
    else:
        form = LojaForm()

    lojas = request.user.lojas.all().order_by('-criada_em')

    context = {'form': form, 'lojas': lojas}

    if request.headers.get('HX-Request'):
        return render(request, 'loja/partials/owner_shops.html', context)
    return render(request, 'loja/owner_shops.html', context)
