from django import forms
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
