from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render, redirect
from apps.cadastro.models import Loja, Funcionario, Servico
from .models import Agendamento
from .forms import AgendamentoDataHoraForm

@login_required
def agendamento_start(request):
    """Etapa 1: escolher funcionário"""
    shop_slug = request.session.get("shop_slug")
    loja = get_object_or_404(Loja, slug=shop_slug, ativa=True)
    funcionarios = loja.funcionarios.filter(ativo=True).order_by("nome")
    return render(request, "appointments/agendamento_step1.html", {"loja": loja, "funcionarios": funcionarios})

@login_required
def agendamento_servicos(request, funcionario_id):
    """Etapa 2: escolher serviço vinculado ao funcionário"""
    funcionario = get_object_or_404(Funcionario, id=funcionario_id, ativo=True)
    servicos = funcionario.servicos.filter(ativo=True).order_by("nome")
    return render(request, "appointments/agendamento_step2.html", {"funcionario": funcionario, "servicos": servicos})

@login_required
def agendamento_datahora(request, funcionario_id, servico_id):
    """Etapa 3: escolher data e horário"""
    funcionario = get_object_or_404(Funcionario, id=funcionario_id, ativo=True)
    servico = get_object_or_404(Servico, id=servico_id, profissionais=funcionario, ativo=True)

    if request.method == "POST":
        form = AgendamentoDataHoraForm(request.POST)
        if form.is_valid():
            ag = form.save(commit=False)
            ag.cliente = request.user
            ag.loja = funcionario.loja
            ag.funcionario = funcionario
            ag.servico = servico
            ag.save()
            return redirect("appointments:agendamento_confirmacao", agendamento_id=ag.id)
    else:
        form = AgendamentoDataHoraForm()

    return render(request, "appointments/agendamento_step3.html", {
        "funcionario": funcionario,
        "servico": servico,
        "form": form,
    })

@login_required
def agendamento_confirmacao(request, agendamento_id):
    """Tela final de confirmação"""
    agendamento = get_object_or_404(Agendamento, id=agendamento_id, cliente=request.user)
    return render(request, "appointments/agendamento_confirm.html", {"agendamento": agendamento})
