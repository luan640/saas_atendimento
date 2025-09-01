from django import forms
from apps.cadastro.models import Servico
from .models import Agendamento


class AgendamentoDataHoraForm(forms.ModelForm):
    hora = forms.ChoiceField(choices=[])

    class Meta:
        model = Agendamento
        fields = ["data", "hora"]
        widgets = {
            "data": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, slots=None, **kwargs):
        super().__init__(*args, **kwargs)
        if slots:
            self.fields["hora"].choices = [
                (s.strftime("%H:%M"), s.strftime("%H:%M")) for s in slots
            ]


class FinalizarAtendimentoForm(forms.ModelForm):
    servicos = forms.ModelMultipleChoiceField(
        queryset=Servico.objects.none(), widget=forms.CheckboxSelectMultiple
    )

    class Meta:
        model = Agendamento
        fields = [
            "funcionario",
            "servicos",
            "valor_final",
            "teve_desconto",
            "forma_pagamento",
            "observacao",
        ]
        widgets = {
            "valor_final": forms.NumberInput(attrs={"readonly": "readonly"}),
            "observacao": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, loja=None, **kwargs):
        super().__init__(*args, **kwargs)
        if loja is not None:
            self.fields["funcionario"].queryset = loja.funcionarios.all()
            self.fields["servicos"].queryset = loja.servicos.all()
        if self.instance.pk:
            self.fields["servicos"].initial = [
                str(pk)
                for pk in self.instance.servicos.values_list("pk", flat=True)
            ]
