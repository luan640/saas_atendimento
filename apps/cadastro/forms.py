from django import forms
from .models import Loja

class LojaForm(forms.ModelForm):
    class Meta:
        model = Loja
        fields = ['nome', 'telefone', 'endereco', 'ativa']