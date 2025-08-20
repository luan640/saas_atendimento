from django import forms
from .models import Loja, Funcionario, Servico

class LojaForm(forms.ModelForm):
    class Meta:
        model = Loja
        fields = ['nome', 'telefone', 'endereco', 'ativa']

class FuncionarioForm(forms.ModelForm):
    class Meta:
        model = Funcionario
        fields = ["nome", "cargo", "email", "telefone", "ativo"]
        labels = {
            "nome": "Nome",
            "cargo": "Cargo",
            "email": "E-mail",
            "telefone": "Telefone",
            "ativo": "Ativo?",
        }
        widgets = {
            "nome": forms.TextInput(attrs={"placeholder": "Ex.: Pedro Alves"}),
            "email": forms.EmailInput(attrs={"placeholder": "exemplo@dominio.com"}),
            "telefone": forms.TextInput(attrs={"placeholder": "+5585..."}),
        }


class ServicoForm(forms.ModelForm):
    profissionais = forms.ModelMultipleChoiceField(
        queryset=Funcionario.objects.none(),
        required=False,
        label="Profissionais",
        widget=forms.CheckboxSelectMultiple
    )

    class Meta:
        model = Servico
        fields = ["nome", "descricao", "duracao_minutos", "preco", "profissionais", "ativo"]
        labels = {
            "nome": "Nome do serviço",
            "descricao": "Descrição",
            "duracao_minutos": "Duração (minutos)",
            "preco": "Preço (R$)",
            "profissionais": "Profissionais",
            "ativo": "Ativo?",
        }
        widgets = {
            "descricao": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        self.loja = kwargs.pop("loja", None)
        super().__init__(*args, **kwargs)
        if self.loja is not None:
            self.fields["profissionais"].queryset = self.loja.funcionarios.filter(ativo=True).order_by("nome")
        else:
            self.fields["profissionais"].queryset = Funcionario.objects.none()
