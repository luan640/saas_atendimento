from django import forms
from .models import Loja, Funcionario, Servico

class LojaForm(forms.ModelForm):
    class Meta:
        model = Loja
        fields = ['nome', 'telefone', 'endereco', 'ativa']

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
