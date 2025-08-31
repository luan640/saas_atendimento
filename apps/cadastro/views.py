from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .models import Loja, Funcionario, Servico
from .forms import (
    LojaForm,
    FuncionarioForm,
    ServicoForm,
    FuncionarioAgendaSemanalFormSet,
)
from apps.accounts.decorators import subscription_required

# ========== UTILITÁRIAS ==========

def _get_loja_ativa(request, lojas_qs):
    """Obtém a loja selecionada pelo usuário via GET/POST; fallback = primeira do queryset."""
    data = request.GET if request.method == 'GET' else request.POST
    loja_id = data.get('loja_filtro') or data.get('loja')
    loja = None
    if loja_id:
        try:
            loja = lojas_qs.filter(id=int(loja_id)).first()
        except (ValueError, TypeError):
            loja = None
    return loja or lojas_qs.first()

def _parse_filtros(request):
    data = request.GET if request.method == 'GET' else request.POST
    return {
        'q': (data.get('q') or '').strip() or None,
        'status': (data.get('status') or '').strip() or None,
        'prof': (data.get('prof') or '').strip() or None,
        'preco_min': (data.get('preco_min') or '').strip() or None,
        'preco_max': (data.get('preco_max') or '').strip() or None,
        'dur_min': (data.get('dur_min') or '').strip() or None,
        'dur_max': (data.get('dur_max') or '').strip() or None,
    }

def _aplica_filtros(qs, filtros):
    if filtros['q']:
        qs = qs.filter(models.Q(nome__icontains=filtros['q']) | models.Q(descricao__icontains=filtros['q']))
    if filtros['status'] == 'ativos':
        qs = qs.filter(ativo=True)
    elif filtros['status'] == 'inativos':
        qs = qs.filter(ativo=False)
    if filtros['prof']:
        try:
            qs = qs.filter(profissionais__id=int(filtros['prof']))
        except ValueError:
            pass
    # preço
    if filtros['preco_min']:
        try:
            qs = qs.filter(preco__gte=float(filtros['preco_min']))
        except ValueError:
            pass
    if filtros['preco_max']:
        try:
            qs = qs.filter(preco__lte=float(filtros['preco_max']))
        except ValueError:
            pass
    # duração
    if filtros['dur_min']:
        try:
            qs = qs.filter(duracao_minutos__gte=int(filtros['dur_min']))
        except ValueError:
            pass
    if filtros['dur_max']:
        try:
            qs = qs.filter(duracao_minutos__lte=int(filtros['dur_max']))
        except ValueError:
            pass
    return qs.distinct()

# ========== SHOPS ==========

@login_required
@subscription_required
def owner_shops(request):
    if not getattr(request.user, 'is_owner', False):
        return redirect('accounts:owner_login')

    target = request.headers.get('HX-Target')
    if request.method == 'POST':
        form = LojaForm(request.POST, user=request.user)
        if form.is_valid():
            loja = form.save(commit=False)
            loja.owner = request.user
            loja.save()
            messages.success(request, 'Loja criada com sucesso!')

            # Após criar, reconsulta para incluir a nova loja
            lojas = request.user.lojas.all().order_by('-criada_em')

            if request.headers.get('HX-Request') and target != 'content':
                # Limpa o form e devolve o parcial atualizado
                form = LojaForm(user=request.user)
                return render(request, 'cadastro/partials/owner_shops.html',
                              {'form': form, 'lojas': lojas})

            return redirect('cadastro:owner_shops')
        else:
            # Form inválido → se for HTMX, devolve parcial com erros
            if request.headers.get('HX-Request') and target != 'content':
                lojas = request.user.lojas.all().order_by('-criada_em')
                # status 200 para evitar erro 422 no console do HTMX
                return render(
                    request,
                    'cadastro/partials/owner_shops.html',
                    {'form': form, 'lojas': lojas},
                )

    # GET
    form = LojaForm(user=request.user)
    lojas = request.user.lojas.all().order_by('-criada_em')

    if request.headers.get('HX-Request') and target != 'content':
        return render(request, 'cadastro/partials/owner_shops.html', {'form': form, 'lojas': lojas})

    return render(request, 'cadastro/owner_shops.html', {'form': form, 'lojas': lojas})

@login_required
@subscription_required
def owner_shop_edit(request, pk):
    """Edita uma loja do owner via HTMX (modal)."""
    loja = get_object_or_404(Loja, pk=pk, owner=request.user)

    if request.method == 'POST':
        form = LojaForm(request.POST, instance=loja, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Loja atualizada com sucesso!')
            lojas = request.user.lojas.all().order_by('-criada_em')
            return render(request, 'cadastro/partials/owner_shops.html', {'lojas': lojas})
        else:
            # Retorna o corpo do modal com erros e orienta o HTMX a retargetar para o modal
            response = render(request, 'cadastro/partials/loja_form.html', {'form': form, 'loja': loja, 'acao': 'Editar Loja'})
            response['HX-Retarget'] = '#modalShell .modal-content'
            return response

    # GET → carrega o formulário de edição dentro do modal
    form = LojaForm(instance=loja, user=request.user)
    return render(request, 'cadastro/partials/loja_form.html', {'form': form, 'loja': loja, 'acao': 'Editar Loja'})


@login_required
@subscription_required
def owner_shop_delete(request, pk):
    """Exclui uma loja do owner via HTMX (modal)."""
    loja = get_object_or_404(Loja, pk=pk, owner=request.user)

    if request.method == 'POST':
        loja.delete()
        messages.success(request, 'Loja excluída com sucesso!')
        lojas = request.user.lojas.all().order_by('-criada_em')
        return render(request, 'cadastro/partials/owner_shops.html', {'lojas': lojas})

    # GET → confirma a exclusão no modal
    return render(request, 'cadastro/partials/loja_confirm_delete.html', {'loja': loja})

# ========== FUNCIONÁRIOS ==========

@login_required
@subscription_required
def funcionarios(request):
    if not getattr(request.user, 'is_owner', False):
        return redirect('accounts:owner_login')

    lojas_qs = request.user.lojas.order_by('nome')
    loja = _get_loja_ativa(request, lojas_qs)
    target = request.headers.get('HX-Target')

    # Sem lojas ainda? oriente o dono a criar
    if not loja:
        ctx = {
            'lojas': lojas_qs,
            'loja': None,
            'form': FuncionarioForm(lojas=lojas_qs),
            'formset': FuncionarioAgendaSemanalFormSet(instance=Funcionario(), prefix='agenda'),
            'funcionarios': []
        }
        if request.headers.get('HX-Request') and target != 'content':
            return render(request, 'cadastro/partials/funcionarios.html', ctx)
        return render(request, 'cadastro/funcionarios.html', ctx)

    if request.method == 'POST':
        func_inst = Funcionario()
        form = FuncionarioForm(request.POST, lojas=lojas_qs, instance=func_inst)
        formset = FuncionarioAgendaSemanalFormSet(request.POST, instance=func_inst, prefix='agenda')
        if form.is_valid() and formset.is_valid():
            func = form.save()
            formset.instance = func
            formset.save()
            messages.success(request, 'Funcionário salvo!')
            # reconsulta lista e limpa form
            qs = loja.funcionarios.order_by('nome')
            form = FuncionarioForm(lojas=lojas_qs, initial={'loja': loja})
            novo_inst = Funcionario(loja=loja)
            formset = FuncionarioAgendaSemanalFormSet(
                instance=novo_inst,
                prefix='agenda',
                queryset=novo_inst.agendas_semanais.none(),
                initial=[{'weekday': i} for i in range(7)],
            )
            ctx = {'lojas': lojas_qs, 'loja': loja, 'form': form, 'formset': formset, 'funcionarios': qs}
            if request.headers.get('HX-Request') and target != 'content':
                return render(request, 'cadastro/partials/funcionarios.html', ctx)
            return redirect(f"{request.path}?loja_filtro={loja.id}")

        qs = loja.funcionarios.order_by('nome')
        ctx = {'lojas': lojas_qs, 'loja': loja, 'form': form, 'formset': formset, 'funcionarios': qs}
        if request.headers.get('HX-Request') and target != 'content':
            # Retorna o corpo do modal com os erros de validação
            resp = render(request, 'cadastro/funcionarios.html', ctx)
            resp['HX-Retarget'] = '#modal-funcionario-body'
            resp['HX-Reselect'] = '#modal-funcionario-body'
            resp['HX-Reswap'] = 'outerHTML'
            return resp
        return render(request, 'cadastro/funcionarios.html', ctx)

    # GET
    form = FuncionarioForm(lojas=lojas_qs, initial={'loja': loja})
    inst = Funcionario(loja=loja)
    formset = FuncionarioAgendaSemanalFormSet(
        instance=inst,
        prefix='agenda',
        queryset=inst.agendas_semanais.none(),
        initial=[{'weekday': i} for i in range(7)],
    )
    qs = loja.funcionarios.order_by('nome')
    ctx = {'lojas': lojas_qs, 'loja': loja, 'form': form, 'formset': formset, 'funcionarios': qs}
    if request.headers.get('HX-Request') and target != 'content':
        return render(request, 'cadastro/partials/funcionarios.html', ctx)
    return render(request, 'cadastro/funcionarios.html', ctx)

@login_required
@subscription_required
def funcionario_edit(request, pk):
    """
    Edita um funcionário do owner via HTMX, reutilizando o modal #modalFuncionario.
    Não altera a view `funcionarios`.
    """
    if not getattr(request.user, 'is_owner', False):
        return redirect('accounts:owner_login')

    # Lista de lojas do owner e loja ativa conforme filtro atual
    lojas_qs = request.user.lojas.order_by('nome')
    func = get_object_or_404(Funcionario, pk=pk, loja__owner=request.user)

    if request.method == 'POST':
        form = FuncionarioForm(request.POST, instance=func, lojas=lojas_qs)
        formset = FuncionarioAgendaSemanalFormSet(request.POST, instance=func, prefix='agenda')
        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            messages.success(request, 'Funcionário atualizado!')

            # Recarrega a lista para a loja atualmente filtrada
            loja = _get_loja_ativa(request, lojas_qs)
            funcionarios_qs = (loja.funcionarios.order_by('nome') if loja else [])
            ctx = {'lojas': lojas_qs, 'loja': loja, 'funcionarios': funcionarios_qs}

            # devolve apenas o <tbody> para substituir na tabela
            return render(request, 'cadastro/partials/funcionarios.html', ctx)

        # Erros de validação → atualizar APENAS o modal
        resp = render(
            request,
            'cadastro/partials/funcionario_form.html',
            {'form': form, 'formset': formset, 'funcionario': func, 'acao': 'Editar funcionário'},
        )
        resp['HX-Retarget'] = '#modalFuncionario .modal-content'
        return resp

    # GET → carregamos o conteúdo do modal de edição
    form = FuncionarioForm(instance=func, lojas=lojas_qs)
    formset = FuncionarioAgendaSemanalFormSet(instance=func, prefix='agenda')
    return render(
        request,
        'cadastro/partials/funcionario_form.html',
        {'form': form, 'formset': formset, 'funcionario': func, 'acao': 'Editar funcionário'},
    )

@login_required
@subscription_required
def funcionario_delete(request, pk):
    """
    Exclui um funcionário do owner via HTMX (confirmação em modal).
    """
    if not getattr(request.user, 'is_owner', False):
        return redirect('accounts:owner_login')

    lojas_qs = request.user.lojas.order_by('nome')
    func = get_object_or_404(Funcionario, pk=pk, loja__owner=request.user)

    if request.method == 'POST':
        func.delete()
        messages.success(request, 'Funcionário excluído!')

        loja = _get_loja_ativa(request, lojas_qs)
        funcionarios_qs = (loja.funcionarios.order_by('nome') if loja else [])
        ctx = {'lojas': lojas_qs, 'loja': loja, 'funcionarios': funcionarios_qs}
        return render(request, 'cadastro/partials/funcionarios.html', ctx)

    # GET → confirma a exclusão
    return render(request, 'cadastro/partials/funcionario_confirm_delete.html', {'funcionario': func})

# ========== SERVIÇOS ==========

@login_required
@subscription_required
def servicos(request):
    if not getattr(request.user, 'is_owner', False):
        return redirect('accounts:owner_login')

    lojas_qs = request.user.lojas.order_by('nome')


    # loja selecionada para filtragem da lista
    loja_id = (request.GET.get('loja_filtro') or request.POST.get('loja_filtro') or
               request.GET.get('loja') or request.POST.get('loja'))
    loja = None
    if loja_id:
        try:
            loja = lojas_qs.filter(id=int(loja_id)).first()
        except (TypeError, ValueError):
            loja = None
    loja = loja or lojas_qs.first()

    # se não há loja, renderiza vazio
    if not loja:
        ctx = {'lojas': lojas_qs, 'loja': None, 'form': None, 'servicos': [], 'filtros': {}, 'profissionais': []}
        tpl = 'cadastro/partials/servicos.html' if (request.headers.get('HX-Request') and request.headers.get('HX-Target') != 'content') else 'cadastro/servicos.html'
        return render(request, tpl, ctx)

    # filtros
    filtros = _parse_filtros(request)

    if request.method == 'POST':
        form = ServicoForm(request.POST, lojas=lojas_qs)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.save()
            form.save_m2m()
            messages.success(request, 'Serviço salvo!')
            # depois de salvar, recarrega a lista já com filtros
            qs = _aplica_filtros(loja.servicos.select_related('loja').prefetch_related('profissionais').order_by('nome'), filtros)
            ctx = {
                'lojas': lojas_qs,
                'loja': loja,
                'form': ServicoForm(lojas=lojas_qs, initial={'loja': loja}),
                'servicos': qs,
                'filtros': filtros,
                'profissionais': loja.funcionarios.filter(ativo=True).order_by('nome'),
                'form_salvo': True,
            }
            if request.headers.get('HX-Request') and request.headers.get('HX-Target') != 'content':
                # devolve só o tbody; a modal fecha via hx-on no template
                return render(request, 'cadastro/partials/servicos.html', ctx)
            return redirect(f"{request.path}?loja_filtro={loja.id}")
        else:
            # form inválido: renderiza página completa (não-HTMX) ou tbody (HTMX) sem quebrar o alvo
            qs = _aplica_filtros(loja.servicos.select_related('loja').prefetch_related('profissionais').order_by('nome'), filtros)
            ctx = {
                'lojas': lojas_qs,
                'loja': loja,
                'form': form,
                'servicos': qs,
                'filtros': filtros,
                'profissionais': loja.funcionarios.filter(ativo=True).order_by('nome'),
            }
            tpl = 'cadastro/partials/servicos.html' if (request.headers.get('HX-Request') and request.headers.get('HX-Target') != 'content') else 'cadastro/servicos.html'

            return render(request, tpl, ctx, status=422)

    # GET (lista com filtros)
    form = ServicoForm(lojas=lojas_qs, initial={'loja': loja})
    qs = _aplica_filtros(loja.servicos.select_related('loja').prefetch_related('profissionais').order_by('nome'), filtros)
    ctx = {
        'lojas': lojas_qs,
        'loja': loja,
        'form': form,
        'servicos': qs,
        'filtros': filtros,
        'profissionais': loja.funcionarios.filter(ativo=True).order_by('nome'),
    }
    if request.headers.get('HX-Request') and request.headers.get('HX-Target') != 'content':
        return render(request, 'cadastro/partials/servicos.html', ctx)
    return render(request, 'cadastro/servicos.html', ctx)

@login_required
@subscription_required
def servico_form(request):
    """Recarrega o formulário de serviço para atualizar profissionais conforme a loja."""
    if not getattr(request.user, 'is_owner', False):
        return redirect('accounts:owner_login')

    lojas_qs = request.user.lojas.order_by('nome')
    form = ServicoForm(request.GET or None, lojas=lojas_qs)
    return render(request, 'cadastro/partials/servico_form.html', {'form': form})

@login_required
@subscription_required
def servico_edit(request, pk):
    """Edita um serviço via HTMX (modal)."""
    if not getattr(request.user, 'is_owner', False):
        return redirect('accounts:owner_login')

    lojas_qs = request.user.lojas.order_by('nome')
    serv = get_object_or_404(Servico, pk=pk, loja__owner=request.user)

    if request.method == 'POST':
        form = ServicoForm(request.POST, instance=serv, lojas=lojas_qs)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.save()
            form.save_m2m()
            messages.success(request, 'Serviço atualizado!')

            # Recarrega lista com a loja/filtros atuais
            loja = _get_loja_ativa(request, lojas_qs)
            filtros = _parse_filtros(request)
            qs = _aplica_filtros(
                loja.servicos.select_related('loja')
                             .prefetch_related('profissionais')
                             .order_by('nome'),
                filtros
            )
            ctx = {
                'lojas': lojas_qs,
                'loja': loja,
                'servicos': qs,
                'filtros': filtros,
                'profissionais': loja.funcionarios.filter(ativo=True).order_by('nome'),
            }
            return render(request, 'cadastro/partials/servicos.html', ctx)

        # Erros de validação -> mantém no modal
        resp = render(request, 'cadastro/partials/servico_form_edit.html',
                      {'form': form, 'servico': serv, 'acao': 'Editar serviço'})
        resp['HX-Retarget'] = '#modalServicoOps .modal-content'
        return resp

    # GET -> carrega form no modal
    form = ServicoForm(instance=serv, lojas=lojas_qs)
    return render(request, 'cadastro/partials/servico_form_edit.html',
                  {'form': form, 'servico': serv, 'acao': 'Editar serviço'})


@login_required
@subscription_required
def servico_delete(request, pk):
    """Exclui um serviço via HTMX (confirmação em modal)."""
    if not getattr(request.user, 'is_owner', False):
        return redirect('accounts:owner_login')

    lojas_qs = request.user.lojas.order_by('nome')
    serv = get_object_or_404(Servico, pk=pk, loja__owner=request.user)

    if request.method == 'POST':
        serv.delete()
        messages.success(request, 'Serviço excluído!')

        loja = _get_loja_ativa(request, lojas_qs)
        filtros = _parse_filtros(request)
        qs = _aplica_filtros(
            loja.servicos.select_related('loja')
                         .prefetch_related('profissionais')
                         .order_by('nome'),
            filtros
        )
        ctx = {
            'lojas': lojas_qs,
            'loja': loja,
            'servicos': qs,
            'filtros': filtros,
            'profissionais': loja.funcionarios.filter(ativo=True).order_by('nome'),
        }
        return render(request, 'cadastro/partials/servicos.html', ctx)

    # GET -> confirma exclusão
    return render(request, 'cadastro/partials/servico_confirm_delete.html', {'servico': serv})
