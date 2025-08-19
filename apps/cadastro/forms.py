from django import forms
from .models import Loja, Funcionario, Servico

class LojaForm(forms.ModelForm):
    class Meta:
        model = Loja
        fields = ['nome', 'telefone', 'endereco', 'ativa']


class FuncionarioForm(forms.ModelForm):
    class Meta:
        model = Funcionario
        fields = ['nome', 'cargo', 'email', 'telefone', 'ativo']


class ServicoForm(forms.ModelForm):
    class Meta:
        model = Servico
        fields = [
            'nome',
            'descricao',
            'duracao_minutos',
            'preco',
            'profissionais',
            'ativo',
        ]
