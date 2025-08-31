from django import forms
from .models import Agendamento

class AgendamentoDataHoraForm(forms.ModelForm):
    class Meta:
        model = Agendamento
        fields = ["data", "hora"]
        widgets = {
            "data": forms.DateInput(attrs={"type": "date"}),
            "hora": forms.TimeInput(attrs={"type": "time"}),
        }
