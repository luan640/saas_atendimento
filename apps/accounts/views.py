from django.utils import timezone
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.http import HttpResponse
from django.db.models import Q, Sum, Count, Avg
from django.views.decorators.http import require_POST
from django.http import HttpRequest

from .forms import OwnerLoginForm, ClientStartForm, ClientVerifyForm
from .models import User, ClientOTP, Subscription, Plan
from apps.cadastro.forms import ClienteForm
from apps.cadastro.models import Loja, Cliente, Funcionario, Servico
from apps.accounts.decorators import subscription_required
from apps.appointments.models import Agendamento
from apps.appointments.utils import gerar_slots_disponiveis
from .utils import get_shop_slug_from_host

import random
import json
from datetime import date, timedelta, time
from calendar import Calendar

# ========== HELPERS ==========

def _issue_otp(phone: str) -> str:
    code = f"{random.randint(0, 999999):06d}"
    ClientOTP.objects.create(
        phone=phone,
        code=code,
        created_at=timezone.now(),
        expires_at=timezone.now() + timedelta(minutes=5),
    )
    print(f"[DEBUG OTP] Enviar {code} para {phone}", flush=True)
    return code

# ========== OWNER ==========

def home_redirect(request: HttpRequest):
    """
    - Subdomínio de loja válido -> vai para fluxo do cliente
    - Subdomínio malformado/indevido -> tela de erro 404 com sugestão do host correto, se possível
    - Sem subdomínio -> login do dono
    """
    slug = get_shop_slug_from_host(request)
    if slug:
        # host válido: atende fluxo cliente daquela loja
        # Se sua view client_start_loja recebe slug:
        return client_start_loja(request)
        # Se ela mesma resolve do host, troque pela chamada sem slug:
        # return client_start_loja(request)

    # Detecta “parece subdomínio” (>=3 labels) e não é IPv4
    host = request.get_host().split(':')[0]
    labels = host.split('.')
    is_ipv4 = (len(labels) == 4 and all(p.isdigit() for p in labels))
    looks_like_subdomain = (not is_ipv4 and len(labels) >= 3)

    if looks_like_subdomain:
        # Se o 1º label é um slug de loja existente, sugerimos a URL canônica correta
        loja = (Loja.objects
                .select_related('owner')
                .filter(slug=labels[0], ativa=True)
                .first())
        ctx = {}
        if loja:
            # Usa sua própria lógica para montar o host correto (com first_name do dono)
            ctx['loja'] = loja
            ctx['suggested_url'] = loja.get_public_url(request)
        return render(request, 'errors/invalid_shop_host.html', ctx, status=404)
        # Ou, se preferir:
        # raise Http404("Endereço de barbearia inválido.")

    # Base domain / sem subdomínio: manda pro login do dono
    return redirect('accounts:owner_login')

def owner_login(request):
    form = OwnerLoginForm(request.POST or None)

    if request.method == 'POST':
        if form.is_valid():
            user = form.cleaned_data['user']

            # garante assinatura (trial no 1º login)
            sub = getattr(user, 'subscription', None)
            if not sub:
                Subscription.objects.create(
                    owner=user,
                    plan=Plan.FREE,
                    start_date=timezone.now(),
                    end_date=timezone.now() + timedelta(days=7)
                )

            login(request, user)

            # pega o next da querystring ou do form hidden
            next_url = request.POST.get('next') or request.GET.get('next')

            # Se veio via HTMX, devolve HX-Redirect para a URL certa
            if request.headers.get('HX-Request'):
                resp = HttpResponse(status=204)
                resp['HX-Redirect'] = next_url or reverse('accounts:owner_home')
                return resp

            return redirect(next_url or 'accounts:owner_home')

        # Form inválido
        template = 'accounts/partials/owner_login.html' if request.headers.get('HX-Request') \
                   else 'accounts/owner_login.html'
        return render(request, template, {'form': form}, status=422)

    # GET
    context = {'form': form}
    if request.headers.get('HX-Request'):
        return render(request, 'accounts/partials/owner_login.html', context)
    return render(request, 'accounts/owner_login.html', context)

@login_required
@subscription_required
def owner_home(request):
    sub = getattr(request.user, 'subscription', None)
    today = timezone.now().date()
    base = Agendamento.objects.filter(loja__owner=request.user, data=today)
    faturado = base.filter(confirmado=True, valor_final__isnull=False).aggregate(total=Sum('valor_final'))['total'] or 0
    agendamentos = base.count()
    no_show = base.filter(no_show=True).count()
    ctx = {
        'subscription': sub,
        'faturado_hoje': faturado,
        'agendamentos_hoje': agendamentos,
        'no_show_hoje': no_show,
    }
    target = request.headers.get('HX-Target')
    if request.headers.get('HX-Request') and target != 'content':
        return render(request, 'accounts/partials/owner_home.html', ctx)
    return render(request, 'accounts/owner_home.html', ctx)

@login_required
@subscription_required
def owner_dashboard(request):
    if not getattr(request.user, 'is_owner', False):
        return redirect('accounts:owner_login')

    lojas_qs = request.user.lojas.order_by('nome')
    loja_ids = request.GET.getlist('lojas')
    if loja_ids:
        lojas = lojas_qs.filter(id__in=loja_ids)
    else:
        lojas = lojas_qs
        loja_ids = [str(l.id) for l in lojas]

    end_str = request.GET.get('end')
    start_str = request.GET.get('start')
    end_date = date.fromisoformat(end_str) if end_str else timezone.now().date()
    start_date = date.fromisoformat(start_str) if start_str else end_date - timedelta(days=30)

    base = Agendamento.objects.filter(
        loja__in=lojas,
        data__range=[start_date, end_date]
    )
    confirmados = base.filter(confirmado=True, valor_final__isnull=False)

    ticket_qs = confirmados.values('loja__nome').annotate(media=Avg('valor_final')).order_by('loja__nome')
    ticket_labels = [t['loja__nome'] for t in ticket_qs]
    ticket_values = [float(t['media']) for t in ticket_qs]

    dias = [start_date + timedelta(days=i) for i in range((end_date - start_date).days + 1)]
    dia_labels = [d.strftime('%d/%m') for d in dias]

    fat_series = []
    for loja in lojas:
        daily = confirmados.filter(loja=loja).values('data').annotate(total=Sum('valor_final'))
        mapping = {item['data']: float(item['total']) for item in daily}
        fat_series.append({'name': loja.nome, 'data': [mapping.get(d, 0) for d in dias]})

    ag_series = []
    for loja in lojas:
        daily = base.filter(loja=loja).values('data').annotate(total=Count('id'))
        mapping = {item['data']: item['total'] for item in daily}
        ag_series.append({'name': loja.nome, 'data': [mapping.get(d, 0) for d in dias]})

    servicos_por_loja = []
    for loja in lojas:
        serv_qs = (
            Servico.objects.filter(loja=loja, agendamentos__in=base)
            .annotate(total=Count('agendamentos'))
            .order_by('-total')
        )
        labels = [s.nome for s in serv_qs]
        values = [s.total for s in serv_qs]
        servicos_por_loja.append({'loja': loja.nome, 'labels': json.dumps(labels), 'values': json.dumps(values)})

    fat_func_qs = confirmados.values('funcionario__nome').annotate(total=Sum('valor_final')).order_by('funcionario__nome')
    fat_func_labels = [f['funcionario__nome'] for f in fat_func_qs]
    fat_func_values = [float(f['total']) for f in fat_func_qs]

    no_show_count = base.filter(no_show=True).count()
    total_count = base.count()
    no_show_percent = (no_show_count / total_count * 100) if total_count else 0

    ctx = {
        'lojas': lojas_qs,
        'lojas_ids': [int(i) for i in loja_ids],
        'start': start_date,
        'end': end_date,
        'ticket_medio_labels': json.dumps(ticket_labels),
        'ticket_medio_values': json.dumps(ticket_values),
        'fat_dia_series': json.dumps(fat_series),
        'ag_dia_series': json.dumps(ag_series),
        'dia_labels': json.dumps(dia_labels),
        'servicos_por_loja': servicos_por_loja,
        'fat_func_labels': json.dumps(fat_func_labels),
        'fat_func_values': json.dumps(fat_func_values),
        'no_show_count': no_show_count,
        'no_show_percent': no_show_percent,
    }
    target = request.headers.get('HX-Target')
    if request.headers.get('HX-Request') and target != 'content':
        return render(request, 'accounts/partials/owner_dashboard.html', ctx)
    return render(request, 'accounts/owner_dashboard.html', ctx)

@login_required
@subscription_required
def owner_sobre(request):
    sub = getattr(request.user, 'subscription', None)
    ctx = {
        'subscription': sub,
    }
    # target = request.headers.get('HX-Target')
    # if request.headers.get('HX-Request') and target != 'content':
    #     return render(request, 'accounts/partials/sobre.html', ctx)
    return render(request, 'accounts/sobre.html', ctx)

@login_required
@subscription_required
def owner_home_agendamentos(request):
    lojas = request.user.lojas.order_by('nome')

    # loja via GET/POST/sessão (mantém como já estava)
    loja_id = (request.GET.get('loja_filtro') or request.POST.get('loja_filtro') or request.session.get('loja_filtro'))
    loja = lojas.filter(id=loja_id).first() or lojas.first()
    if loja:
        request.session['loja_filtro'] = loja.id

    # --- preferências de visualização (persistência em sessão) ---
    view_mode = (request.GET.get('view') or request.POST.get('view') or request.session.get('ag_view_mode') or 'month').lower()
    request.session['ag_view_mode'] = view_mode

    if view_mode == 'day':
        # dia preferido: GET/POST/sessão -> fallback hoje
        d_str = request.GET.get('d') or request.POST.get('d') or request.session.get('ag_view_day')
        try:
            day = date.fromisoformat(d_str) if d_str else timezone.localdate()
        except Exception:
            day = timezone.localdate()
        request.session['ag_view_day'] = day.isoformat()

        qs = (Agendamento.objects
              .filter(loja=loja, data=day, confirmado=False, no_show=False)
              .select_related('funcionario','cliente')
              .prefetch_related('servicos')
              .order_by('hora','funcionario__nome'))

        ctx = {
            'lojas': lojas,
            'loja': loja,
            'view_mode': 'day',
            'day': day,
            'day_prev': day - timedelta(days=1),
            'day_next': day + timedelta(days=1),
            'day_items': qs,
            'today': timezone.localdate(),
            # para o botão "Mês" voltar ao mês do dia atual:
            'current': day.replace(day=1),
            'total_pendentes': qs.count(),
        }
        return render(request, 'accounts/partials/owner_home_agendamentos.html', ctx)

    # ---- modo mensal (default) ----
    try:
        y = int(request.GET.get('y') or request.POST.get('y') or request.session.get('ag_y') or 0)
        m = int(request.GET.get('m') or request.POST.get('m') or request.session.get('ag_m') or 0)
        current = date(y, m, 1) if (y and m) else timezone.localdate().replace(day=1)
    except Exception:
        current = timezone.localdate().replace(day=1)

    # salva mês na sessão (para F5)
    request.session['ag_y'] = current.year
    request.session['ag_m'] = current.month

    cal = Calendar(firstweekday=0)  # 0 = segunda
    weeks_dates = cal.monthdatescalendar(current.year, current.month)
    start, end = weeks_dates[0][0], weeks_dates[-1][-1]

    pendentes_qs = (Agendamento.objects
        .filter(loja=loja, data__range=[start, end], confirmado=False, no_show=False)
        .select_related('funcionario','cliente')
        .prefetch_related('servicos')
        .order_by('data','hora'))

    by_day = {}
    for a in pendentes_qs:
        by_day.setdefault(a.data, []).append(a)

    weeks = [[(d, by_day.get(d, [])) for d in week] for week in weeks_dates]

    prev_first = (current.replace(day=1) - timedelta(days=1)).replace(day=1)
    next_first = (current.replace(day=28) + timedelta(days=4)).replace(day=1)

    ctx = {
        'lojas': lojas,
        'loja': loja,
        'view_mode': 'month',
        'weeks': weeks,
        'current': current,
        'today': timezone.localdate(),
        'prev_y': prev_first.year, 'prev_m': prev_first.month,
        'next_y': next_first.year, 'next_m': next_first.month,
        'total_pendentes': pendentes_qs.count(),
    }
    return render(request, 'accounts/partials/owner_home_agendamentos.html', ctx)

@login_required
@subscription_required
def owner_criar_atendimento(request):
    if not getattr(request.user, 'is_owner', False):
        return redirect('accounts:owner_login')

    if request.method == 'POST':
        loja_id = request.POST.get('loja')                # <-- NOVO
        cliente_id = request.POST.get('cliente')
        funcionario_id = request.POST.get('funcionario')
        servicos_ids = request.POST.getlist('servicos')
        data_str = request.POST.get('data')
        hora_str = request.POST.get('slot')

        # Se faltar algo, re-renderiza o modal no estado correto (com base em loja/func/data passados)
        if not (cliente_id and funcionario_id and servicos_ids and data_str and hora_str):
            clientes = request.user.clientes.select_related('user').order_by('user__full_name')
            lojas = request.user.lojas.order_by('nome')    # <-- NOVO

            loja_sel = None
            funcionarios = None
            servicos = None
            slots = []

            # Se a loja foi escolhida, monta etapa 2 já filtrada
            if loja_id:
                loja_sel = get_object_or_404(Loja, pk=loja_id, owner=request.user)
                funcionarios = Funcionario.objects.filter(loja=loja_sel, ativo=True).order_by('nome')
                servicos = Servico.objects.filter(loja=loja_sel, ativo=True).order_by('nome')

            # Se já temos func + data, pré-carrega slots
            dia = date.fromisoformat(data_str) if data_str else timezone.now().date()
            if funcionario_id and data_str:
                funcionario = get_object_or_404(Funcionario, pk=funcionario_id, loja__owner=request.user, ativo=True)
                slots = gerar_slots_disponiveis(funcionario, dia)

            ctx = {
                'clientes': clientes,
                'lojas': lojas,               # <-- NOVO
                'loja_sel': loja_sel,         # <-- NOVO (para marcar selected)
                'funcionarios': funcionarios, # <-- pode ser None se loja não escolhida
                'servicos': servicos,         # <--
                'slots': slots,               # <--
                'dia': dia,
            }
            resp = render(request, 'accounts/partials/criar_atendimento_modal.html', ctx, status=422)
            resp['HX-Retarget'] = '#modalShellLarge .modal-content'
            resp['HX-Reselect'] = '#modalShellLarge .modal-content'
            resp['HX-Reswap'] = 'innerHTML'
            return resp

        # Validações finais (consistência loja x funcionario)
        cliente = get_object_or_404(User, pk=cliente_id, is_client=True)
        funcionario = get_object_or_404(Funcionario, pk=funcionario_id, loja__owner=request.user, ativo=True)
        if loja_id and str(funcionario.loja_id) != str(loja_id):
            return HttpResponse('Funcionário não pertence à loja selecionada.', status=422)

        servicos_qs = Servico.objects.filter(pk__in=servicos_ids, loja=funcionario.loja, ativo=True)
        dia = date.fromisoformat(data_str)
        hora = time.fromisoformat(hora_str)

        ag = Agendamento.objects.create(
            cliente=cliente,
            loja=funcionario.loja,
            funcionario=funcionario,
            data=dia,
            hora=hora,
        )
        ag.servicos.set(servicos_qs)

        resp = owner_home_agendamentos(request)  # mantém o fluxo atual

        # DISPARA O EVENTO PARA O TOAST (ouça em document.body 'show-toast')
        resp['HX-Trigger'] = json.dumps({
            "show-toast": {"text": "Agendamento realizado com sucesso!", "level": "success"}
        })

        return resp

    # GET: etapa 1 (Loja + Cliente)
    clientes = request.user.clientes.select_related('user').order_by('user__full_name')
    lojas = request.user.lojas.order_by('nome')

    ctx = {
        'clientes': clientes,
        'lojas': lojas,
        'loja_sel': None,
        'funcionarios': None,   # etapa 2 virá por AJAX
        'servicos': None,
        'slots': [],
        'dia': timezone.now().date(),
    }
    return render(request, 'accounts/partials/criar_atendimento_modal.html', ctx)

@login_required
@subscription_required
def owner_add_cliente(request):
    if not getattr(request.user, 'is_owner', False):
        return redirect('accounts:owner_login')
    if request.method == 'POST':
        form = ClienteForm(request.POST)
        for field in form.fields.values():
            field.widget.attrs.update({'class': 'form-control'})
        if form.is_valid():
            user = form.save()
            Cliente.objects.get_or_create(owner=request.user, user=user)
            resp = HttpResponse(f'<option value="{user.id}" selected>{user.full_name}</option>')
            resp['HX-Retarget'] = '#cliente'
            resp['HX-Reswap'] = 'beforeend'
            resp['HX-Reselect'] = f'#cliente option[value="{user.id}"]'
            return resp
        resp = render(request, 'accounts/partials/cliente_form_modal.html', {'cliente_form': form}, status=422)
        resp['HX-Retarget'] = '#modalShell .modal-content'
        resp['HX-Reselect'] = '#modalShell .modal-content'
        resp['HX-Reswap'] = 'innerHTML'
        return resp
    form = ClienteForm()
    for field in form.fields.values():
        field.widget.attrs.update({'class': 'form-control'})
    return render(request, 'accounts/partials/cliente_form_modal.html', {'cliente_form': form})

@login_required
@subscription_required
def owner_slots_disponiveis(request):
    if not getattr(request.user, 'is_owner', False):
        return redirect('accounts:owner_login')

    func_id = request.GET.get('funcionario')
    data_str = request.GET.get('data')
    if not func_id or not data_str:
        return HttpResponse('Dados insuficientes', status=400)

    dia = date.fromisoformat(data_str)
    funcionario = get_object_or_404(
        Funcionario, pk=func_id, loja__owner=request.user, ativo=True
    )
    slots = gerar_slots_disponiveis(funcionario, dia)
    return render(
        request, 'accounts/partials/slot_options.html', {'slots': slots}
    )

@login_required
@subscription_required
def owner_fields_by_loja(request):
    if not getattr(request.user, 'is_owner', False):
        return HttpResponse(status=403)

    loja_id = request.GET.get('loja')
    if not loja_id:
        return HttpResponse('Loja não informada', status=400)

    loja = get_object_or_404(Loja, pk=loja_id, owner=request.user)

    funcionarios = Funcionario.objects.filter(loja=loja, ativo=True).order_by('nome')
    servicos = Servico.objects.filter(loja=loja, ativo=True).order_by('nome')

    dia = timezone.now().date()

    return render(
        request,
        'accounts/partials/criar_atendimento_stage2.html',
        {'funcionarios': funcionarios, 'servicos': servicos, 'dia': dia}
    )

@login_required
@subscription_required
def owner_logout(request):
    logout(request)
    return redirect('accounts:owner_login')

# ========== CLIENTE (OTP por telefone) ==========

def client_start_loja(request):

    shop_slug = get_shop_slug_from_host(request)
    loja = get_object_or_404(Loja, slug=shop_slug, ativa=True)

    if request.method == 'POST':
        form = ClientStartForm(request.POST)
        if form.is_valid():
            full_name = (form.cleaned_data['full_name'] or '').strip()
            phone     = form.cleaned_data['phone']

            # contexto para o verify
            request.session['pending_full_name'] = full_name
            request.session['shop_slug'] = loja.slug
            request.session['pending_phone'] = phone

            _issue_otp(phone)

            messages.success(request, "Código de verificação enviado (ver console do servidor).")
            url = reverse('accounts:client_verify')
            return redirect(f"{url}?phone={phone}&name={full_name}")
    else:
        form = ClientStartForm()

    return render(request, 'accounts/client_start.html', {'form': form, 'shop': loja})

def client_verify(request):

    phone = request.GET.get('phone') or request.POST.get('phone')
    shop_slug = (
        request.GET.get('shop')
        or request.POST.get('shop')
        or request.session.get('shop_slug')
        or get_shop_slug_from_host(request)
    )
    full_name = request.GET.get('name')

    if request.method == 'POST':
        form = ClientVerifyForm(request.POST)

        if form.is_valid():
            phone = request.session.get('pending_phone')
            code  = form.cleaned_data['code']
            
            # guarda a loja na sessão (se veio por GET/POST)
            if shop_slug:
                request.session['shop_slug'] = shop_slug

            # valida o OTP pelo trio: telefone + código + não expirado
            now = timezone.now()
            otp = (ClientOTP.objects
                   .filter(phone=phone, code=code, expires_at__gte=now)
                   .order_by('-created_at')
                   .first())

            if not otp:
                messages.error(request, 'Código inválido ou expirado.')
            else:
                full_name = request.session.get('pending_full_name') or 'Cliente'

                user, _ = User.objects.get_or_create(
                    phone=phone,
                    defaults={
                        'email': f'cliente-{phone}@example.local',
                        'is_client': True,
                        'is_owner': False,
                        'full_name': full_name,
                        'grupo': 'cliente',
                        'username': f'{full_name}_{phone}',
                    }
                )

                owner = get_object_or_404(Loja, slug=shop_slug)

                Cliente.objects.get_or_create(owner=owner.owner, user=user)

                if not user.is_client:
                    user.is_client = True
                    user.save(update_fields=['is_client'])

                # invalida o OTP para não reutilizar
                otp.delete()

                login(request, user)
                return redirect('accounts:client_dashboard')
        else:
            print(form.errors)
    else:
        form = ClientVerifyForm(initial={'phone': phone})

    return render(request, 'accounts/client_verify.html', {
        'form': form,
        'phone': phone,
        'client_start': full_name,
    })

@login_required
def client_dashboard(request):
    loja = None
    shop_slug = (
        request.session.get('shop_slug')
        or request.GET.get('shop')
        or get_shop_slug_from_host(request)
    )

    if shop_slug:
        # Import local para evitar dependência circular
        from apps.cadastro.models import Loja
        loja = Loja.objects.filter(slug=shop_slug, ativa=True).first()

    agendamentos = Agendamento.objects.filter(cliente=request.user)
    if loja:
        agendamentos = agendamentos.filter(loja=loja)
    agendamentos = agendamentos.select_related("funcionario", "loja").prefetch_related("servicos").order_by("-data", "-hora")

    return render(
        request,
        "accounts/client_dashboard.html",
        {
            "loja": loja,
            "agendamentos": agendamentos,
        }
    )

@require_POST
def client_resend_code(request):
    """
    Reemite o OTP via HTMX (POST).
    Espera: phone (POST) ou session['pending_phone'].
    Retorna 204 + HX-Trigger (toast).
    """
    shop_slug = get_shop_slug_from_host(request)
    loja = get_object_or_404(Loja, slug=shop_slug, ativa=True)

    phone = request.POST.get('phone') or request.session.get('pending_phone')
    if not phone:
        resp = HttpResponse(status=400)
        resp['HX-Trigger'] = json.dumps({
            "show-toast": {"text": "Telefone ausente para reenviar código.", "level": "error"}
        })
        return resp

    # Throttle simples: evita spam de reenvio < 60s
    last = ClientOTP.objects.filter(phone=phone).order_by('-created_at').first()
    if last and (timezone.now() - last.created_at).total_seconds() < 60:
        resp = HttpResponse(status=429)
        resp['HX-Trigger'] = json.dumps({
            "show-toast": {"text": "Aguarde alguns segundos antes de reenviar.", "level": "error"}
        })
        return resp

    _issue_otp(phone)

    resp = HttpResponse(status=204)  # sem swap no HTMX
    resp['HX-Trigger'] = json.dumps({
        "show-toast": {"text": "Código reenviado!", "level": "success"}
    })
    return resp
