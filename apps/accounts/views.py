import random
from datetime import timedelta
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.http import HttpResponse
from django.db.models import Q, Sum

from .forms import OwnerLoginForm, ClientStartForm, ClientVerifyForm
from .models import User, ClientOTP, Subscription, Plan
from apps.cadastro.models import Loja
from apps.accounts.decorators import subscription_required
from apps.appointments.models import Agendamento

# ========== OWNER ==========

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
def owner_home_agendamentos(request):
    if not getattr(request.user, 'is_owner', False):
        return redirect('accounts:owner_login')

    lojas = request.user.lojas.order_by('nome')
    loja_id = request.GET.get('loja_filtro') or request.GET.get('loja')
    loja_sel = get_object_or_404(lojas, pk=loja_id) if loja_id else (lojas.first() if lojas.exists() else None)

    base = Agendamento.objects.filter(loja__owner=request.user)
    if loja_sel:
        base = base.filter(loja=loja_sel)

    # Tentamos cobrir 2 cenários: por status OU por booleano realizado
    pendentes = base.filter(confirmado=False).order_by('criado_em')[:20]
    realizados = base.filter(confirmado=True).order_by('-criado_em')[:20]

    ctx = {
        'lojas': lojas,
        'loja': loja_sel,
        'pendentes': pendentes,
        'realizados': realizados,
        'total_pendentes': base.filter(confirmado=False).count(),
        'total_realizados': base.filter(confirmado=True).count(),
    }
    return render(request, 'accounts/partials/owner_home_agendamentos.html', ctx)

@login_required
@subscription_required
def owner_logout(request):
    logout(request)
    return redirect('accounts:owner_login')

# ========== CLIENTE (OTP por telefone) ==========

def client_start_loja(request, slug):

    loja = get_object_or_404(Loja, slug=slug, ativa=True)

    if request.method == 'POST':
        form = ClientStartForm(request.POST)
        if form.is_valid():
            full_name = (form.cleaned_data['full_name'] or '').strip()
            phone     = form.cleaned_data['phone']

            # contexto para o verify
            request.session['pending_full_name'] = full_name
            request.session['shop_slug'] = loja.slug

            # GERA OTP AQUI
            code = f"{random.randint(0, 999999):06d}"
            ClientOTP.objects.create(
                phone=phone,
                code=code,
                created_at=timezone.now(),
                expires_at=timezone.now() + timedelta(minutes=5),
            )

            print(f"[DEBUG OTP] Enviar {code} para {phone}", flush=True)

            messages.success(request, "Código de verificação enviado (ver console do servidor).")
            url = reverse('accounts:client_verify')
            return redirect(f"{url}?phone={phone}&shop={loja.slug}")
    else:
        form = ClientStartForm()

    return render(request, 'accounts/client_start.html', {'form': form, 'shop': loja})

def client_verify(request):

    phone = request.GET.get('phone') or request.POST.get('phone')
    shop_slug = (
        request.GET.get('shop')
        or request.POST.get('shop')
        or request.session.get('shop_slug')
    )

    if request.method == 'POST':
        form = ClientVerifyForm(request.POST)
        if form.is_valid():
            phone = form.cleaned_data['phone']
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

                if not user.is_client:
                    user.is_client = True
                    user.save(update_fields=['is_client'])

                # invalida o OTP para não reutilizar
                otp.delete()

                login(request, user)
                return redirect('accounts:client_dashboard')
    else:
        form = ClientVerifyForm(initial={'phone': phone})

    return render(request, 'accounts/client_verify.html', {
        'form': form,
        'phone': phone,
    })

@login_required
def client_dashboard(request):
    loja = None
    shop_slug = request.session.get('shop_slug') or request.GET.get('shop')

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

