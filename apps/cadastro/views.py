from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .models import Loja, Funcionario, Servico
from .forms import LojaForm, FuncionarioForm, ServicoForm

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


@login_required
def owner_shop_edit(request, pk):
    if not getattr(request.user, 'is_owner', False):
        return redirect('accounts:owner_login')

    loja = get_object_or_404(Loja, pk=pk, owner=request.user)

    if request.method == 'POST':
        form = LojaForm(request.POST, instance=loja)
        if form.is_valid():
            form.save()
            messages.success(request, 'Loja atualizada com sucesso!')
            return redirect('cadastro:owner_shops')
    else:
        form = LojaForm(instance=loja)

    template = 'loja/owner_shop_form.html'
    if request.headers.get('HX-Request'):
        template = 'loja/partials/owner_shop_form.html'
    return render(request, template, {'form': form, 'loja': loja})


@login_required
def owner_shop_delete(request, pk):
    if not getattr(request.user, 'is_owner', False):
        return redirect('accounts:owner_login')

    loja = get_object_or_404(Loja, pk=pk, owner=request.user)

    if request.method == 'POST':
        loja.delete()
        messages.success(request, 'Loja removida com sucesso!')
        return redirect('cadastro:owner_shops')

    template = 'loja/owner_shop_confirm_delete.html'
    if request.headers.get('HX-Request'):
        template = 'loja/partials/owner_shop_confirm_delete.html'
    return render(request, template, {'loja': loja})


@login_required
def owner_staff(request, loja_id):
    if not getattr(request.user, 'is_owner', False):
        return redirect('accounts:owner_login')

    loja = get_object_or_404(Loja, pk=loja_id, owner=request.user)

    if request.method == 'POST':
        form = FuncionarioForm(request.POST)
        if form.is_valid():
            funcionario = form.save(commit=False)
            funcionario.loja = loja
            funcionario.save()
            messages.success(request, 'Funcionário cadastrado com sucesso!')
            return redirect('cadastro:owner_staff', loja_id=loja.id)
    else:
        form = FuncionarioForm()

    funcionarios = loja.funcionarios.all().order_by('nome')

    template = 'funcionario/owner_staff.html'
    if request.headers.get('HX-Request'):
        template = 'funcionario/partials/owner_staff.html'
    return render(request, template, {
        'loja': loja,
        'form': form,
        'funcionarios': funcionarios,
    })


@login_required
def owner_staff_edit(request, loja_id, pk):
    if not getattr(request.user, 'is_owner', False):
        return redirect('accounts:owner_login')

    loja = get_object_or_404(Loja, pk=loja_id, owner=request.user)
    funcionario = get_object_or_404(Funcionario, pk=pk, loja=loja)

    if request.method == 'POST':
        form = FuncionarioForm(request.POST, instance=funcionario)
        if form.is_valid():
            form.save()
            messages.success(request, 'Funcionário atualizado com sucesso!')
            return redirect('cadastro:owner_staff', loja_id=loja.id)
    else:
        form = FuncionarioForm(instance=funcionario)

    template = 'funcionario/owner_staff_form.html'
    if request.headers.get('HX-Request'):
        template = 'funcionario/partials/owner_staff_form.html'
    return render(request, template, {'loja': loja, 'form': form, 'funcionario': funcionario})


@login_required
def owner_staff_delete(request, loja_id, pk):
    if not getattr(request.user, 'is_owner', False):
        return redirect('accounts:owner_login')

    loja = get_object_or_404(Loja, pk=loja_id, owner=request.user)
    funcionario = get_object_or_404(Funcionario, pk=pk, loja=loja)

    if request.method == 'POST':
        funcionario.delete()
        messages.success(request, 'Funcionário removido com sucesso!')
        return redirect('cadastro:owner_staff', loja_id=loja.id)

    template = 'funcionario/owner_staff_confirm_delete.html'
    if request.headers.get('HX-Request'):
        template = 'funcionario/partials/owner_staff_confirm_delete.html'
    return render(request, template, {'loja': loja, 'funcionario': funcionario})


@login_required
def owner_services(request, loja_id):
    if not getattr(request.user, 'is_owner', False):
        return redirect('accounts:owner_login')

    loja = get_object_or_404(Loja, pk=loja_id, owner=request.user)

    if request.method == 'POST':
        form = ServicoForm(request.POST)
        if form.is_valid():
            servico = form.save(commit=False)
            servico.loja = loja
            servico.save()
            form.save_m2m()
            messages.success(request, 'Serviço criado com sucesso!')
            return redirect('cadastro:owner_services', loja_id=loja.id)
    else:
        form = ServicoForm()

    servicos = loja.servicos.all().order_by('nome')

    template = 'servico/owner_services.html'
    if request.headers.get('HX-Request'):
        template = 'servico/partials/owner_services.html'
    return render(request, template, {
        'loja': loja,
        'form': form,
        'servicos': servicos,
    })


@login_required
def owner_service_edit(request, loja_id, pk):
    if not getattr(request.user, 'is_owner', False):
        return redirect('accounts:owner_login')

    loja = get_object_or_404(Loja, pk=loja_id, owner=request.user)
    servico = get_object_or_404(Servico, pk=pk, loja=loja)

    if request.method == 'POST':
        form = ServicoForm(request.POST, instance=servico)
        if form.is_valid():
            form.save()
            messages.success(request, 'Serviço atualizado com sucesso!')
            return redirect('cadastro:owner_services', loja_id=loja.id)
    else:
        form = ServicoForm(instance=servico)

    template = 'servico/owner_service_form.html'
    if request.headers.get('HX-Request'):
        template = 'servico/partials/owner_service_form.html'
    return render(request, template, {'loja': loja, 'form': form, 'servico': servico})


@login_required
def owner_service_delete(request, loja_id, pk):
    if not getattr(request.user, 'is_owner', False):
        return redirect('accounts:owner_login')

    loja = get_object_or_404(Loja, pk=loja_id, owner=request.user)
    servico = get_object_or_404(Servico, pk=pk, loja=loja)

    if request.method == 'POST':
        servico.delete()
        messages.success(request, 'Serviço removido com sucesso!')
        return redirect('cadastro:owner_services', loja_id=loja.id)

    template = 'servico/owner_service_confirm_delete.html'
    if request.headers.get('HX-Request'):
        template = 'servico/partials/owner_service_confirm_delete.html'
    return render(request, template, {'loja': loja, 'servico': servico})

