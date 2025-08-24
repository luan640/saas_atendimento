from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from apps.cadastro.models import Loja, Funcionario, Servico
from .models import Agendamento
from .forms import AgendamentoDataHoraForm


@login_required
def agendamento_start(request):
    """Página inicial que carrega os passos via HTMX."""
    request.session.pop("agendamento_funcionario", None)
    request.session.pop("agendamento_servicos", None)
    return render(request, "appointments/agendamento_base.html")


@login_required
def agendamento_profissionais(request):
    shop_slug = request.session.get("shop_slug")
    loja = get_object_or_404(Loja, slug=shop_slug, ativa=True)
    funcionarios = loja.funcionarios.filter(ativo=True).order_by("nome")
    return render(request, "appointments/partials/profissionais.html", {"funcionarios": funcionarios})


@login_required
def agendamento_servicos(request, funcionario_id):
    funcionario = get_object_or_404(Funcionario, id=funcionario_id, ativo=True)
    request.session["agendamento_funcionario"] = funcionario.id
    servicos = funcionario.servicos.filter(ativo=True).order_by("nome")

    if request.method == "POST":
        selecionados = request.POST.getlist("servicos")
        request.session["agendamento_servicos"] = selecionados
        response = render(
            request,
            "appointments/partials/datahora.html",
            {
                "funcionario": funcionario,
                "servicos": Servico.objects.filter(id__in=selecionados),
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
    funcionario = get_object_or_404(Funcionario, id=funcionario_id, ativo=True)
    servicos = Servico.objects.filter(id__in=servico_ids, profissionais=funcionario, ativo=True)

    if request.method == "POST":
        form = AgendamentoDataHoraForm(request.POST)
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
        form = AgendamentoDataHoraForm()

    return render(
        request,
        "appointments/partials/datahora.html",
        {"funcionario": funcionario, "servicos": servicos, "form": form},
    )


@login_required
def agendamento_confirmacao(request, agendamento_id):
    agendamento = get_object_or_404(Agendamento, id=agendamento_id, cliente=request.user)
    return render(
        request,
        "appointments/partials/confirmacao.html",
        {"agendamento": agendamento},
    )
