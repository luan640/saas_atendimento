from datetime import date, timedelta
from calendar import Calendar
import json 
from urllib.parse import urlparse, parse_qs

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone
from django.db.models import Sum

from apps.cadastro.models import Loja, Funcionario, Servico
from apps.accounts.views import owner_home_agendamentos
from .models import Agendamento
from .forms import AgendamentoDataHoraForm, FinalizarAtendimentoForm
from .utils import gerar_slots_disponiveis

def _inherit_htmx_query(request):
    """Copia view/d/y/m/loja_filtro do HX-Current-URL (se houver) para request.GET."""
    
    hx_url = request.headers.get('HX-Current-URL') or ''

    if not hx_url:
        return

    parsed = urlparse(hx_url)
    qs = parse_qs(parsed.query)
    if not qs:
        return

    # torne GET mutável e injete apenas chaves que nos interessam
    mutable = request.GET.copy()
    for key in ('view', 'd', 'y', 'm', 'loja_filtro'):
        if key in qs and qs[key]:
            mutable[key] = qs[key][0]

    request.GET = mutable

@login_required
def agendamento_start(request):
    """Página inicial que carrega os passos via HTMX."""
    request.session.pop("agendamento_funcionario", None)
    request.session.pop("agendamento_servicos", None)
    return render(
        request,
        "appointments/agendamento_base.html",
        {"initial_url": reverse("appointments:agendamento_profissionais")},
    )

@login_required
def agendamento_profissionais(request):
    shop_slug = request.session.get("shop_slug")
    loja = get_object_or_404(Loja, slug=shop_slug, ativa=True)
    funcionarios = loja.funcionarios.filter(ativo=True).order_by("nome")

    ctx = {"loja": loja, "funcionarios": funcionarios}

    if request.headers.get("HX-Request"):
        return render(request, "appointments/partials/profissionais.html", ctx)
    return render(
        request,
        "appointments/agendamento_base.html",
        {"initial_url": reverse("appointments:agendamento_profissionais")},
    )

@login_required
def agendamento_servicos(request, funcionario_id):
    funcionario = get_object_or_404(Funcionario, id=funcionario_id, ativo=True)
    request.session["agendamento_funcionario"] = funcionario.id
    servicos = funcionario.servicos.filter(ativo=True).order_by("nome")

    if not request.headers.get("HX-Request") and request.method == "GET":
        return render(
            request,
            "appointments/agendamento_base.html",
            {
                "initial_url": reverse(
                    "appointments:agendamento_servicos", args=[funcionario.id]
                )
            },
        )

    if request.method == "POST":
        selecionados = request.POST.getlist("servicos")

        if not selecionados:
            # nenhum serviço escolhido → volta para a etapa 2 com erro
            return render(
                request,
                "appointments/partials/servicos.html",
                {
                    "funcionario": funcionario,
                    "servicos": servicos,
                    "selecionados": [],
                    "erro": "Você deve selecionar pelo menos um serviço.",
                },
                status=422
            )

        # salva os IDs escolhidos na sessão
        request.session["agendamento_servicos"] = selecionados

        servicos_sel = Servico.objects.filter(id__in=selecionados)
        dia = date.today()
        slots = gerar_slots_disponiveis(funcionario, dia)
        response = render(
            request,
            "appointments/partials/datahora.html",
            {
                "funcionario": funcionario,
                "servicos": servicos_sel,
                "form": AgendamentoDataHoraForm(initial={"data": dia}, slots=slots),
                "dia": dia,
            },
        )
        response["HX-Push-Url"] = reverse("appointments:agendamento_datahora")
        return response

    selecionados = request.session.get("agendamento_servicos", [])
    return render(
        request,
        "appointments/partials/servicos.html",
        {
            "funcionario": funcionario,
            "servicos": servicos,
            "selecionados": [int(s) for s in selecionados],
        },
    )

@login_required
def agendamento_datahora(request):
    funcionario_id = request.session.get("agendamento_funcionario")
    servico_ids = request.session.get("agendamento_servicos", [])
    funcionario = get_object_or_404(Funcionario, id=funcionario_id, ativo=True)
    servicos = Servico.objects.filter(id__in=servico_ids, profissionais=funcionario, ativo=True)

    if not request.headers.get("HX-Request") and request.method == "GET":
        return render(
            request,
            "appointments/agendamento_base.html",
            {"initial_url": reverse("appointments:agendamento_datahora")},
        )

    if request.method == "POST":
        dia_str = request.POST.get("data")
        dia = date.fromisoformat(dia_str) if dia_str else date.today()
        slots = gerar_slots_disponiveis(funcionario, dia)
        form = AgendamentoDataHoraForm(request.POST, slots=slots)
        if form.is_valid():
            ag = form.save(commit=False)
            ag.cliente = request.user
            ag.loja = funcionario.loja
            ag.funcionario = funcionario
            ag.save()
            ag.servicos.set(servicos)
            response = render(
                request,
                "appointments/partials/confirmacao.html",
                {"agendamento": ag},
            )
            response["HX-Push-Url"] = reverse(
                "appointments:agendamento_confirmacao", args=[ag.id]
            )
            return response
    else:
        dia_str = request.GET.get("data")
        dia = date.fromisoformat(dia_str) if dia_str else date.today()
        slots = gerar_slots_disponiveis(funcionario, dia)
        
        form = AgendamentoDataHoraForm(initial={"data": dia}, slots=slots)

    return render(
        request,
        "appointments/partials/datahora.html",
        {
            "funcionario": funcionario,
            "servicos": servicos,
            "form": form,
            "dia": dia,
        },
    )

@login_required
def agendamento_confirmacao(request, agendamento_id):
    agendamento = get_object_or_404(Agendamento, id=agendamento_id, cliente=request.user)
    if request.headers.get("HX-Request"):
        return render(
            request,
            "appointments/partials/confirmacao.html",
            {"agendamento": agendamento},
        )
    return render(
        request,
        "appointments/agendamento_base.html",
        {
            "initial_url": reverse(
                "appointments:agendamento_confirmacao", args=[agendamento.id]
            )
        },
    )

@login_required
def finalizar_agendamento(request, pk):
    agendamento = get_object_or_404(Agendamento, pk=pk, loja__owner=request.user)

    if request.method == "POST":
        form = FinalizarAtendimentoForm(
            request.POST, instance=agendamento, loja=agendamento.loja
        )
        if form.is_valid():
            ag = form.save(commit=False)
            total = form.cleaned_data["servicos"].aggregate(total=Sum("preco"))["total"] or 0
            ag.valor_final = total
            ag.confirmado = True
            ag.finalizado_em = timezone.now()
            ag.save()
            form.save_m2m()

            # Re-renderiza o calendário preservando loja e mês/ano atuais
            lojas = request.user.lojas.order_by("nome")
            loja_id = request.POST.get("loja_filtro") or request.POST.get("loja")
            loja = (
                get_object_or_404(lojas, pk=loja_id)
                if loja_id
                else (lojas.first() if lojas.exists() else None)
            )

            # Determina mês/ano exibidos (enviados como hidden no filtro)
            try:
                y = int(request.POST.get("y") or request.POST.get("year") or 0)
                m = int(request.POST.get("m") or request.POST.get("month") or 0)
                current = date(y, m, 1)
            except Exception:
                today = date.today()
                current = today.replace(day=1)

            cal = Calendar(firstweekday=0)
            weeks_dates = cal.monthdatescalendar(current.year, current.month)
            start, end = weeks_dates[0][0], weeks_dates[-1][-1]

            pendentes_qs = (
                Agendamento.objects
                .filter(loja=loja, data__range=[start, end], confirmado=False, no_show=False)
                .select_related("funcionario", "cliente")
                .prefetch_related("servicos")
                .order_by("data", "hora")
            )

            by_day = {}
            for a in pendentes_qs:
                by_day.setdefault(a.data, []).append(a)

            weeks = [[(d, by_day.get(d, [])) for d in week] for week in weeks_dates]

            prev_first = (current.replace(day=1) - timedelta(days=1)).replace(day=1)
            next_first = (current.replace(day=28) + timedelta(days=4)).replace(day=1)

            ctx = {
                "lojas": lojas,
                "loja": loja,
                "weeks": weeks,
                "current": current,
                "today": date.today(),
                "prev_y": prev_first.year,
                "prev_m": prev_first.month,
                "next_y": next_first.year,
                "next_m": next_first.month,
                "total_pendentes": pendentes_qs.count(),
            }

            # >>> herda os parâmetros da tela atual (view=day/d=... ou month/y&m)
            _inherit_htmx_query(request)

            # >>> delega para a view que renderiza o calendário/lista respeitando o modo atual
            resp = owner_home_agendamentos(request)

            resp["HX-Retarget"] = "#agendamentos-section"
            resp["HX-Reswap"]   = "outerHTML"
            resp["HX-Trigger"]  = json.dumps({
                "show-toast": {"text": "Atendimento finalizado com sucesso!", "level": "success"},
                "reload-owner-home": None,
            })
            return resp

    else:
        total = agendamento.servicos.aggregate(total=Sum("preco"))["total"] or 0
        form = FinalizarAtendimentoForm(
            instance=agendamento, loja=agendamento.loja, initial={"valor_final": total}
        )

    return render(
        request,
        "appointments/partials/finalizar_agendamento.html",
        {"agendamento": agendamento, "form": form},
        status=400 if request.method == "POST" else 200,
    )

@login_required
def marcar_no_show(request, pk):
    agendamento = get_object_or_404(Agendamento, pk=pk, loja__owner=request.user)

    if request.method == "POST":
        agendamento.confirmado = True
        agendamento.no_show = True
        agendamento.finalizado_em = timezone.now()
        agendamento.valor_final = 0
        agendamento.save(update_fields=["confirmado", "no_show", "finalizado_em", "valor_final"])

        # Re-renderiza o calendário preservando loja e mês/ano atuais
        lojas = request.user.lojas.order_by("nome")
        loja_id = request.POST.get("loja_filtro") or request.POST.get("loja")
        loja = (
            get_object_or_404(lojas, pk=loja_id)
            if loja_id
            else (lojas.first() if lojas.exists() else None)
        )

        try:
            y = int(request.POST.get("y") or request.POST.get("year") or 0)
            m = int(request.POST.get("m") or request.POST.get("month") or 0)
            current = date(y, m, 1)
        except Exception:
            today = date.today()
            current = today.replace(day=1)

        cal = Calendar(firstweekday=0)
        weeks_dates = cal.monthdatescalendar(current.year, current.month)
        start, end = weeks_dates[0][0], weeks_dates[-1][-1]

        pendentes_qs = (
            Agendamento.objects
            .filter(loja=loja, data__range=[start, end], confirmado=False, no_show=False)
            .select_related("funcionario", "cliente")
            .prefetch_related("servicos")
            .order_by("data", "hora")
        )

        by_day = {}
        for a in pendentes_qs:
            by_day.setdefault(a.data, []).append(a)

        weeks = [[(d, by_day.get(d, [])) for d in week] for week in weeks_dates]

        prev_first = (current.replace(day=1) - timedelta(days=1)).replace(day=1)
        next_first = (current.replace(day=28) + timedelta(days=4)).replace(day=1)

        ctx = {
            "lojas": lojas,
            "loja": loja,
            "weeks": weeks,
            "current": current,
            "today": date.today(),
            "prev_y": prev_first.year,
            "prev_m": prev_first.month,
            "next_y": next_first.year,
            "next_m": next_first.month,
            "total_pendentes": pendentes_qs.count(),
        }
        response = render(request, "accounts/partials/owner_home_agendamentos.html", ctx)
        response["HX-Retarget"] = "#agendamentos-section"
        response["HX-Reswap"] = "outerHTML"
        response['HX-Trigger'] = json.dumps({
            "show-toast": {"text": "Não comparecimento salvo com sucesso!", "level": "success"},
            "reload-owner-home": None,
        })

        return response

    return render(
        request,
        "appointments/partials/no_show_confirm.html",
        {"agendamento": agendamento},
    )
