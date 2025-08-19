from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .models import Loja
from .forms import LojaForm, FuncionarioForm, ServicoForm

def _get_loja_ativa(request, lojas_qs):
    """Obtém a loja selecionada pelo usuário via GET/POST; fallback = primeira do queryset."""
    loja_id = request.GET.get('loja') or request.POST.get('loja')
    loja = None
    if loja_id:
        try:
            loja = lojas_qs.filter(id=int(loja_id)).first()
        except (ValueError, TypeError):
            loja = None
    return loja or lojas_qs.first()

@login_required
def owner_shops(request):
    if not getattr(request.user, 'is_owner', False):
        return redirect('accounts:owner_login')

    if request.method == 'POST':
        form = LojaForm(request.POST)
        if form.is_valid():
            loja = form.save(commit=False)
            loja.owner = request.user
            loja.save()
            messages.success(request, 'Loja criada com sucesso!')

            # Após criar, reconsulta para incluir a nova loja
            lojas = request.user.lojas.all().order_by('-criada_em')

            if request.headers.get('HX-Request'):
                # Limpa o form e devolve o parcial atualizado
                form = LojaForm()
                return render(request, 'cadastro/partials/owner_shops.html',
                              {'form': form, 'lojas': lojas})

            return redirect('cadastro:owner_shops')
        else:
            # Form inválido → se for HTMX, devolve parcial com erros
            if request.headers.get('HX-Request'):
                lojas = request.user.lojas.all().order_by('-criada_em')
                return render(request, 'cadastro/partials/owner_shops.html',
                              {'form': form, 'lojas': lojas}, status=422)

    # GET
    form = LojaForm()
    lojas = request.user.lojas.all().order_by('-criada_em')

    if request.headers.get('HX-Request'):
        return render(request, 'cadastro/partials/owner_shops.html', {'form': form, 'lojas': lojas})

    return render(request, 'cadastro/owner_shops.html', {'form': form, 'lojas': lojas})

@login_required
def funcionarios(request):
    if not getattr(request.user, 'is_owner', False):
        return redirect('accounts:owner_login')

    lojas_qs = request.user.lojas.order_by('nome')
    loja = _get_loja_ativa(request, lojas_qs)

    # Sem lojas ainda? oriente o dono a criar
    if not loja:
        ctx = {'lojas': lojas_qs, 'loja': None, 'form': None, 'funcionarios': []}
        tpl = 'cadastro/partials/funcionarios.html' if request.headers.get('HX-Request') else 'cadastro/funcionarios.html'
        return render(request, tpl, ctx)

    if request.method == 'POST':
        form = FuncionarioForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.loja = loja
            obj.save()
            messages.success(request, 'Funcionário salvo!')
            # reconsulta lista e limpa form
            qs = loja.funcionarios.order_by('nome')
            form = FuncionarioForm()
            ctx = {'lojas': lojas_qs, 'loja': loja, 'form': form, 'funcionarios': qs}
            if request.headers.get('HX-Request'):
                return render(request, 'cadastro/partials/funcionarios.html', ctx)
            return redirect(f"{request.path}?loja={loja.id}")
        # inválido
        qs = loja.funcionarios.order_by('nome')
        ctx = {'lojas': lojas_qs, 'loja': loja, 'form': form, 'funcionarios': qs}
        tpl = 'cadastro/partials/funcionarios.html' if request.headers.get('HX-Request') else 'cadastro/funcionarios.html'
        return render(request, tpl, ctx, status=422)

    # GET
    form = FuncionarioForm()
    qs = loja.funcionarios.order_by('nome')
    ctx = {'lojas': lojas_qs, 'loja': loja, 'form': form, 'funcionarios': qs}
    if request.headers.get('HX-Request'):
        return render(request, 'cadastro/partials/funcionarios.html', ctx)
    return render(request, 'cadastro/funcionarios.html', ctx)

@login_required
def servicos(request):
    if not getattr(request.user, 'is_owner', False):
        return redirect('accounts:owner_login')

    lojas_qs = request.user.lojas.order_by('nome')
    loja = _get_loja_ativa(request, lojas_qs)

    if not loja:
        ctx = {'lojas': lojas_qs, 'loja': None, 'form': None, 'servicos': []}
        tpl = 'cadastro/partials/servicos.html' if request.headers.get('HX-Request') else 'cadastro/servicos.html'
        return render(request, tpl, ctx)

    if request.method == 'POST':
        form = ServicoForm(request.POST, loja=loja)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.loja = loja
            obj.save()
            form.save_m2m()
            messages.success(request, 'Serviço salvo!')
            qs = loja.servicos.order_by('nome')
            form = ServicoForm(loja=loja)  # limpa após salvar
            ctx = {'lojas': lojas_qs, 'loja': loja, 'form': form, 'servicos': qs}
            if request.headers.get('HX-Request'):
                return render(request, 'cadastro/partials/servicos.html', ctx)
            return redirect(f"{request.path}?loja={loja.id}")
        qs = loja.servicos.order_by('nome')
        ctx = {'lojas': lojas_qs, 'loja': loja, 'form': form, 'servicos': qs}
        tpl = 'cadastro/partials/servicos.html' if request.headers.get('HX-Request') else 'cadastro/servicos.html'
        return render(request, tpl, ctx, status=422)

    # GET
    form = ServicoForm(loja=loja)
    qs = loja.servicos.order_by('nome')
    ctx = {'lojas': lojas_qs, 'loja': loja, 'form': form, 'servicos': qs}
    if request.headers.get('HX-Request'):
        return render(request, 'cadastro/partials/servicos.html', ctx)
    return render(request, 'cadastro/servicos.html', ctx)
