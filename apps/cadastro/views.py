from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .models import Loja
from .forms import LojaForm, FuncionarioForm, ServicoForm

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

@login_required
def owner_shops(request):
    if not getattr(request.user, 'is_owner', False):
        return redirect('accounts:owner_login')

    target = request.headers.get('HX-Target')
    if request.method == 'POST':
        form = LojaForm(request.POST)
        if form.is_valid():
            loja = form.save(commit=False)
            loja.owner = request.user
            loja.save()
            messages.success(request, 'Loja criada com sucesso!')

            # Após criar, reconsulta para incluir a nova loja
            lojas = request.user.lojas.all().order_by('-criada_em')

            if request.headers.get('HX-Request') and target != 'content':
                # Limpa o form e devolve o parcial atualizado
                form = LojaForm()
                return render(request, 'cadastro/partials/owner_shops.html',
                              {'form': form, 'lojas': lojas})

            return redirect('cadastro:owner_shops')
        else:
            # Form inválido → se for HTMX, devolve parcial com erros
            if request.headers.get('HX-Request') and target != 'content':
                lojas = request.user.lojas.all().order_by('-criada_em')
                return render(request, 'cadastro/partials/owner_shops.html',
                              {'form': form, 'lojas': lojas}, status=422)

    # GET
    form = LojaForm()
    lojas = request.user.lojas.all().order_by('-criada_em')

    if request.headers.get('HX-Request') and target != 'content':
        return render(request, 'cadastro/partials/owner_shops.html', {'form': form, 'lojas': lojas})

    return render(request, 'cadastro/owner_shops.html', {'form': form, 'lojas': lojas})

@login_required
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
            'funcionarios': []
        }
        if request.headers.get('HX-Request') and target != 'content':
            return render(request, 'cadastro/partials/funcionarios.html', ctx)
        return render(request, 'cadastro/funcionarios.html', ctx)

    if request.method == 'POST':
        form = FuncionarioForm(request.POST, lojas=lojas_qs)
        if form.is_valid():
            obj = form.save()
            messages.success(request, 'Funcionário salvo!')
            # reconsulta lista e limpa form
            qs = loja.funcionarios.order_by('nome')
            form = FuncionarioForm(lojas=lojas_qs, initial={'loja': loja})
            ctx = {'lojas': lojas_qs, 'loja': loja, 'form': form, 'funcionarios': qs}
            if request.headers.get('HX-Request') and target != 'content':
                return render(request, 'cadastro/partials/funcionarios.html', ctx)
            return redirect(f"{request.path}?loja_filtro={loja.id}")
        # inválido
        qs = loja.funcionarios.order_by('nome')
        ctx = {'lojas': lojas_qs, 'loja': loja, 'form': form, 'funcionarios': qs}
        if request.headers.get('HX-Request') and target != 'content':
            return render(request, 'cadastro/partials/funcionarios.html', ctx, status=422)
        return render(request, 'cadastro/funcionarios.html', ctx, status=422)

    # GET
    form = FuncionarioForm(lojas=lojas_qs, initial={'loja': loja})
    qs = loja.funcionarios.order_by('nome')
    ctx = {'lojas': lojas_qs, 'loja': loja, 'form': form, 'funcionarios': qs}
    if request.headers.get('HX-Request') and target != 'content':
        return render(request, 'cadastro/partials/funcionarios.html', ctx)
    return render(request, 'cadastro/funcionarios.html', ctx)

@login_required
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
            obj = form.save()
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
def servico_form(request):
    """Recarrega o formulário de serviço para atualizar profissionais conforme a loja."""
    if not getattr(request.user, 'is_owner', False):
        return redirect('accounts:owner_login')

    lojas_qs = request.user.lojas.order_by('nome')
    form = ServicoForm(request.GET or None, lojas=lojas_qs)
    return render(request, 'cadastro/partials/servico_form.html', {'form': form})
