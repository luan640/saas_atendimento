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
    """
    Passe 'loja' no __init__ para limitar a lista de profissionais dessa loja:
        form = ServicoForm(request.POST or None, loja=loja)
    """
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
            "nome": forms.TextInput(attrs={"placeholder": "Ex.: Corte masculino"}),
            "descricao": forms.Textarea(attrs={"rows": 3, "placeholder": "Detalhes do serviço"}),
        }

    def __init__(self, *args, **kwargs):
        self.loja = kwargs.pop("loja", None)
        super().__init__(*args, **kwargs)
        # Limita M2M aos funcionários da loja (de preferência ativos)
        if self.loja is not None:
            self.fields["profissionais"].queryset = self.loja.funcionarios.filter(ativo=True).order_by("nome")
        else:
            self.fields["profissionais"].queryset = Funcionario.objects.none()

    def clean(self):
        cleaned = super().clean()
        # Regras extras (opcionais; já há validators no model)
        dur = cleaned.get("duracao_minutos")
        preco = cleaned.get("preco")
        if dur is not None and dur <= 0:
            self.add_error("duracao_minutos", "Informe uma duração maior que zero.")
        if preco is not None and preco < 0:
            self.add_error("preco", "O preço não pode ser negativo.")
        return cleaned
