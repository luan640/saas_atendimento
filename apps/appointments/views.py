from datetime import datetime, date

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render
from django.urls import reverse

from apps.cadastro.models import Loja, Funcionario, Servico
from .models import Agendamento
from .forms import AgendamentoDataHoraForm
from .utils import gerar_slots_disponiveis

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
    shop_slug = request.session.get("shop_slug")
    funcionario = get_object_or_404(
        Funcionario, id=funcionario_id, loja__slug=shop_slug, ativo=True
    )
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

        response = render(
            request,
            "appointments/partials/datahora.html",
            {
                "funcionario": funcionario,
                "servicos": Servico.objects.filter(id__in=selecionados, profissionais=funcionario),
                "form": AgendamentoDataHoraForm(),
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
    shop_slug = request.session.get("shop_slug")
    funcionario = get_object_or_404(
        Funcionario, id=funcionario_id, loja__slug=shop_slug, ativo=True
    )
    servicos = Servico.objects.filter(id__in=servico_ids, profissionais=funcionario, ativo=True)
    duracao_total = sum(s.duracao_minutos for s in servicos)

    # Data selecionada (GET ?data=) ou dia atual
    if request.method == "POST":
        dia_str = request.POST.get("data")
    else:
        dia_str = request.GET.get("data")
    dia = date.fromisoformat(dia_str) if dia_str else date.today()

    slots_dt = gerar_slots_disponiveis(funcionario, dia, duracao_total)
    slot_choices = [(s.time().strftime("%H:%M"), s.time().strftime("%H:%M")) for s in slots_dt]

    if not request.headers.get("HX-Request") and request.method == "GET":
        return render(
            request,
            "appointments/agendamento_base.html",
            {"initial_url": reverse("appointments:agendamento_datahora")},
        )

    if request.method == "POST":
        form = AgendamentoDataHoraForm(request.POST, slot_choices=slot_choices)
        if form.is_valid():
            hora_escolhida = form.cleaned_data["hora"].strftime("%H:%M")
            if hora_escolhida not in [h for h, _ in slot_choices]:
                form.add_error("hora", "Horário não disponível.")
            else:
                ag = form.save(commit=False)
                ag.cliente = request.user
                ag.loja = funcionario.loja
                ag.funcionario = funcionario
                ag.duracao_total_minutos = duracao_total
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
        form = AgendamentoDataHoraForm(initial={"data": dia}, slot_choices=slot_choices)

    return render(
        request,
        "appointments/partials/datahora.html",
        {
            "funcionario": funcionario,
            "servicos": servicos,
            "form": form,
            "slots": slot_choices,
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
