from django import forms
from django.urls import reverse
from .models import Loja, Funcionario, Servico, FuncionarioAgendaSemanal
from apps.accounts.models import Plan, PlanInfo
from django.forms import inlineformset_factory


class LojaForm(forms.ModelForm):
    class Meta:
        model = Loja
        fields = ['nome', 'telefone', 'endereco', 'ativa']

    def __init__(self, *args, **kwargs):
        # receba o usuário que está criando
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned = super().clean()

        # Só checa em criação (não em edição)
        if not self.instance.pk:
            user = self.user or getattr(self.instance, 'owner', None)
            if user:
                # plano atual (se não houver subscription, trate como FREE)
                sub = getattr(user, 'subscription', None)
                plan_key = sub.plan if sub else Plan.FREE

                # carrega limites; se não houver registro, aplica fallback seguro
                try:
                    limites = PlanInfo.objects.get(plan=plan_key)
                except PlanInfo.DoesNotExist:
                    # defaults: 1 loja / 1 funcionário
                    class _Default: 
                        max_lojas = 1
                        max_funcionarios = 1
                    limites = _Default()

                # quer contar só ativas? use: user.lojas.filter(ativa=True).count()
                qtd_lojas = user.lojas.count()
                if qtd_lojas >= limites.max_lojas:
                    # nome bonitinho do plano
                    try:
                        plano_label = Plan(plan_key).label
                    except Exception:
                        plano_label = str(plan_key)
                    raise forms.ValidationError(
                        f"Seu plano atual ({plano_label}) permite no máximo {limites.max_lojas} loja(s)."
                    )

        return cleaned


class FuncionarioForm(forms.ModelForm):
    loja = forms.ModelChoiceField(queryset=Loja.objects.none(), label="Loja")
    slot_interval_minutes = forms.IntegerField(min_value=1, label="Tempo do slot (minutos)")

    class Meta:
        model = Funcionario
        fields = ["loja", "nome", "cargo", "email", "telefone", "ativo", "slot_interval_minutes"]
        widgets = {
            "nome": forms.TextInput(attrs={"placeholder": "Ex.: Pedro Alves"}),
            "email": forms.EmailInput(attrs={"placeholder": "exemplo@dominio.com"}),
            "telefone": forms.TextInput(attrs={"placeholder": "+5585..."}),
        }

    def __init__(self, *args, **kwargs):
        lojas = kwargs.pop("lojas", Loja.objects.none())
        super().__init__(*args, **kwargs)
        self.fields["loja"].queryset = lojas

    def clean(self):
        cleaned = super().clean()
        loja = cleaned.get("loja")
        if not self.instance.pk and loja and hasattr(loja, "owner") and hasattr(loja.owner, "subscription"):
            limites = PlanInfo.objects.get(plan=loja.owner.subscription.plan)
            if loja.funcionarios.count() >= limites.max_funcionarios:
                raise forms.ValidationError(
                    f"O plano atual permite no máximo {limites.max_funcionarios} funcionário(s) por loja."
                )
        return cleaned


class FuncionarioAgendaSemanalForm(forms.ModelForm):
    class Meta:
        model = FuncionarioAgendaSemanal
        fields = ["weekday", "ativo", "inicio", "fim", "almoco_inicio", "almoco_fim", "slot_interval_minutes"]
        widgets = {
            "inicio": forms.TimeInput(attrs={"type": "time"}),
            "fim": forms.TimeInput(attrs={"type": "time"}),
            "almoco_inicio": forms.TimeInput(attrs={"type": "time"}),
            "almoco_fim": forms.TimeInput(attrs={"type": "time"}),
        }

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("ativo"):
            ini, fim = cleaned.get("inicio"), cleaned.get("fim")
            ai, af = cleaned.get("almoco_inicio"), cleaned.get("almoco_fim")
            if not ini or not fim or ini >= fim:
                raise forms.ValidationError("Defina início < fim para dias ativos.")
            if (ai and not af) or (af and not ai):
                raise forms.ValidationError("Preencha os dois horários de almoço ou deixe ambos vazios.")
            if ai and af and not (ini < ai < af < fim):
                raise forms.ValidationError("Almoço deve estar dentro do expediente.")
        return cleaned

FuncionarioAgendaSemanalFormSet = inlineformset_factory(
    Funcionario,
    FuncionarioAgendaSemanal,
    form=FuncionarioAgendaSemanalForm,
    extra=0,
    can_delete=False,
    max_num=7,
)

class ServicoForm(forms.ModelForm):
    loja = forms.ModelChoiceField(queryset=Loja.objects.none(), label="Loja")
    profissionais = forms.ModelMultipleChoiceField(
        queryset=Funcionario.objects.none(),
        required=False,
        label="Profissionais",
        widget=forms.CheckboxSelectMultiple
    )

    class Meta:
        model = Servico
        fields = ["loja", "nome", "descricao", "duracao_minutos", "preco", "profissionais", "ativo"]
        labels = {
            "nome": "Nome do serviço",
            "descricao": "Descrição",
            "duracao_minutos": "Duração (minutos)",
            "preco": "Preço (R$)",
            "profissionais": "Profissionais",
            "ativo": "Ativo?",
            "loja": "Loja",
        }
        widgets = {
            "descricao": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        lojas = kwargs.pop("lojas", Loja.objects.none())
        super().__init__(*args, **kwargs)
        self.fields["loja"].queryset = lojas
        self.fields["loja"].widget.attrs.update({
            "hx-get": reverse("cadastro:servico_form"),
            "hx-target": "#modal-servico-body",
            "hx-select": "#modal-servico-body",
            "hx-include": "#form-servico",
            "hx-trigger": "change",
            "hx-swap": "outerHTML",
        })

        loja_valor = self.data.get("loja") or self.initial.get("loja")
        loja_obj = None
        if isinstance(loja_valor, Loja):
            loja_obj = loja_valor
        elif loja_valor:
            try:
                loja_obj = lojas.get(id=int(loja_valor))
            except (ValueError, Loja.DoesNotExist):
                loja_obj = None
        elif self.instance.pk:
            loja_obj = self.instance.loja

        if loja_obj is not None:
            self.fields["profissionais"].queryset = loja_obj.funcionarios.filter(ativo=True).order_by("nome")
        else:
            self.fields["profissionais"].queryset = Funcionario.objects.none()
