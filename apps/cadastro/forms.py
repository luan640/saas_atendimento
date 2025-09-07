from django import forms
from django.urls import reverse
from django.forms import inlineformset_factory
from .models import Loja, Funcionario, Servico, FuncionarioAgendaSemanal
from apps.accounts.models import Plan, PlanInfo, User


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


class ClienteForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["full_name", "email", "phone"]
        labels = {
            "full_name": "Nome",
            "email": "E-mail",
            "phone": "Telefone",
        }
        widgets = {
            "phone": forms.TextInput(attrs={"placeholder": "+5585..."}),
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        if not user.username:
            user.username = user.email
        user.is_client = True
        if commit:
            if not user.pk:
                user.set_unusable_password()
            user.save()
        return user

class FuncionarioForm(forms.ModelForm):
    loja = forms.ModelChoiceField(queryset=Loja.objects.none(), label="Loja")

    class Meta:
        model = Funcionario
        fields = ["loja", "nome", "cargo", "email", "telefone", "ativo"]
        labels = {
            "nome": "Nome",
            "cargo": "Cargo",
            "email": "E-mail",
            "telefone": "Telefone",
            "ativo": "Ativo?",
            "loja": "Loja",
        }
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
        cleaned_data = super().clean()

        loja = cleaned_data.get("loja")
        if not self.instance.pk and loja:
            owner = loja.owner
            if hasattr(owner, "subscription"):
                plano_atual = owner.subscription.plan
                limites = PlanInfo.objects.get(plan=plano_atual)

                qtd_funcionarios = loja.funcionarios.count()
                if qtd_funcionarios >= limites.max_funcionarios:
                    raise forms.ValidationError(
                        f"O plano atual permite no máximo {limites.max_funcionarios} funcionário(s) por loja."
                    )

        return cleaned_data

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

        url = reverse("cadastro:servico_form")
        if self.instance.pk:
            url = reverse("cadastro:servico_edit", args=[self.instance.pk])

        self.fields["loja"].widget.attrs.update({
            "hx-get": url,
            "hx-target": "#modal-servico-body",
            "hx-select": "#modal-servico-body",
            "hx-trigger": "change",
            "hx-swap": "outerHTML",
            "hx-include": "this",

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

class FuncionarioAgendaSemanalForm(forms.ModelForm):
    inicio = forms.TimeField(required=False, widget=forms.TimeInput(attrs={"type": "time"}))
    fim = forms.TimeField(required=False, widget=forms.TimeInput(attrs={"type": "time"}))
    almoco_inicio = forms.TimeField(required=False, widget=forms.TimeInput(attrs={"type": "time"}))
    almoco_fim = forms.TimeField(required=False, widget=forms.TimeInput(attrs={"type": "time"}))
    slot_interval_minutes = forms.IntegerField(required=False)

    class Meta:
        model = FuncionarioAgendaSemanal
        fields = [
            "weekday",
            "inicio",
            "fim",
            "almoco_inicio",
            "almoco_fim",
            "ativo",
            "slot_interval_minutes",
        ]


FuncionarioAgendaSemanalFormSet = inlineformset_factory(
    Funcionario,
    FuncionarioAgendaSemanal,
    form=FuncionarioAgendaSemanalForm,
    extra=7,
    max_num=7,
    can_delete=True,
)
