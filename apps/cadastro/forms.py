from django import forms
from django.urls import reverse
from django.forms import inlineformset_factory

from .models import Loja, Funcionario, Servico, FuncionarioAgendaSemanal, LojaHorario, FormaPagamento, Semana
from apps.accounts.models import Plan, PlanInfo, User

import re

HEX_RE = re.compile(r'^#([0-9A-Fa-f]{6})$')

# ====== Loja =======

class LojaForm(forms.ModelForm):

    pagamentos_aceitos = forms.ModelMultipleChoiceField(
        queryset=FormaPagamento.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Formas de pagamento aceitas",
    )

    class Meta:
        model = Loja
        fields = ["nome", "telefone", "endereco", "ativa", "pagamentos_aceitos"]
        labels = {
            "nome": "Nome da loja",
            "telefone": "Telefone",
            "endereco": "Endereço",
            "ativa": "Ativa?",
        }

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

class LojaHorarioForm(forms.ModelForm):
    inicio = forms.TimeField(required=False, widget=forms.TimeInput(attrs={"type": "time"}))
    fim = forms.TimeField(required=False, widget=forms.TimeInput(attrs={"type": "time"}))
    almoco_inicio = forms.TimeField(required=False, widget=forms.TimeInput(attrs={"type": "time"}))
    almoco_fim = forms.TimeField(required=False, widget=forms.TimeInput(attrs={"type": "time"}))

    class Meta:
        model = LojaHorario
        fields = ["weekday", "aberto", "inicio", "fim", "almoco_inicio", "almoco_fim"]
        labels = {
            "weekday": "Dia",
            "aberto": "Aberto?",
            "inicio": "Início",
            "fim": "Fim",
            "almoco_inicio": "Almoço início",
            "almoco_fim": "Almoço fim",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Deixa o dia fixo na UI (somente leitura) e mantém o valor via hidden
        self.fields["weekday"].widget = forms.HiddenInput()

LojaHorarioFormSet = inlineformset_factory(
    Loja,
    LojaHorario,
    form=LojaHorarioForm,
    extra=0,
    can_delete=False,
    min_num=7,
    validate_min=True,
    max_num=7,
)

# ====== Cliente =======

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


# ====== Serviço =======

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

        editing = bool(self.instance and self.instance.pk)

        if editing:
            # 👉 edição: não permitir trocar loja nem exigir no POST
            self.fields["loja"].required = False
            self.fields["loja"].disabled = True
            self.fields["loja"].initial = self.instance.loja
            # (opcional) remova htmx do campo, caso ele ainda seja renderizado em algum lugar
            for attr in ("hx-get","hx-target","hx-select","hx-trigger","hx-swap","hx-include","hx-params"):
                self.fields["loja"].widget.attrs.pop(attr, None)

            loja_obj = self.instance.loja
        else:
            # 👉 criação: loja vem do POST/initial; mantém HTMX se quiser filtrar profissionais
            self.fields["loja"].widget.attrs.update({
                "hx-get": reverse("cadastro:servico_form"),
                "hx-target": "#modal-servico-body",
                "hx-select": "#modal-servico-body",
                "hx-trigger": "change",
                "hx-swap": "outerHTML",
                "hx-include": "this",
                "hx-params": "loja",
            })

            loja_valor = self.data.get("loja") or self.initial.get("loja")
            if isinstance(loja_valor, Loja):
                loja_obj = loja_valor
            elif loja_valor:
                try:
                    loja_obj = lojas.get(id=int(loja_valor))
                except (ValueError, Loja.DoesNotExist):
                    loja_obj = None
            else:
                loja_obj = None

        # queryset dos profissionais conforme loja (edição: sempre da loja do instance)
        if loja_obj is not None:
            self.fields["profissionais"].queryset = (
                loja_obj.funcionarios.filter(ativo=True).order_by("nome")
            )
        else:
            self.fields["profissionais"].queryset = Funcionario.objects.none()

# ====== Funcionário =======

class FuncionarioForm(forms.ModelForm):
    loja = forms.ModelChoiceField(queryset=Loja.objects.none(), label="Loja")

    class Meta:
        model = Funcionario
        fields = ["loja", "nome", "cargo", "email", "telefone", "cor_hex", "ativo"]
        labels = {
            "nome": "Nome",
            "cargo": "Cargo",
            "email": "E-mail",
            "telefone": "Telefone",
            "cor_hex": "Cor no calendário",
            "ativo": "Ativo?",
            "loja": "Loja",
        }
        widgets = {
            "nome": forms.TextInput(attrs={"placeholder": "Ex.: Pedro Alves"}),
            "email": forms.EmailInput(attrs={"placeholder": "exemplo@dominio.com"}),
            "telefone": forms.TextInput(attrs={"placeholder": "+5585..."}),
            # Bootstrap 5: form-control-color + type=color
            "cor_hex": forms.TextInput(attrs={
                "type": "color",
                "class": "form-control form-control-color",
                "title": "Escolha uma cor",
                "style": "width:3rem; padding:0;"
            }),

        }

    def __init__(self, *args, **kwargs):
        lojas = kwargs.pop("lojas", Loja.objects.none())
        super().__init__(*args, **kwargs)
        self.fields["loja"].queryset = lojas
        # default se vier vazio na criação
        if not self.initial.get("cor_hex"):
            self.initial["cor_hex"] = self.instance.cor_hex or "#1E90FF"

    def clean_cor_hex(self):
        value = (self.cleaned_data.get("cor_hex") or "").strip()
        # aceita sem # e corrige
        if value and not value.startswith("#"):
            value = f"#{value}"
        if not HEX_RE.match(value or ""):
            raise forms.ValidationError("Informe uma cor em hexadecimal no formato #RRGGBB.")
        return value

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
    can_delete=False,
)