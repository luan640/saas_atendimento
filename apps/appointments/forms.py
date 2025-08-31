from django import forms
from .models import Agendamento

class AgendamentoDataHoraForm(forms.ModelForm):
    class Meta:
        model = Agendamento
        fields = ["data", "hora"]
        widgets = {
            "data": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, slot_choices=None, **kwargs):
        super().__init__(*args, **kwargs)
        if slot_choices is not None:
            self.fields["hora"].widget = forms.Select(choices=slot_choices)
        else:
            self.fields["hora"].widget = forms.Select(choices=[])
