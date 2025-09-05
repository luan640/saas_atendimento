from django import forms
from django.contrib.auth import authenticate

import re

class OwnerLoginForm(forms.Form):
    email = forms.EmailField(label="E-mail")
    password = forms.CharField(widget=forms.PasswordInput, label="Senha")

    def clean(self):
        cleaned = super().clean()
        email = cleaned.get("email")
        password = cleaned.get("password")
        user = authenticate(email=email, password=password)
        if not user:
            raise forms.ValidationError("Credenciais inválidas.")
        if not user.is_owner:
            raise forms.ValidationError("Esta conta não é de proprietário.")
        cleaned["user"] = user
        return cleaned

class ClientStartForm(forms.Form):
    full_name = forms.CharField(label="Seu nome", max_length=120)
    phone = forms.CharField(label="Telefone (ex.: +5585...)",
                            help_text="Use o formato internacional (E.164). Ex.: +5585...")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['full_name'].widget.attrs.update({
            'placeholder': 'Seu nome completo',
            'autocomplete': 'name',
        })
        self.fields['phone'].widget.attrs.update({
            'placeholder': '+5585XXXXXXXX',
            'inputmode': 'tel',
            'pattern': r'^\+?\d{10,15}$',
        })

    def clean_phone(self):
        phone = self.cleaned_data['phone'].strip()
        # mantém + e dígitos, remove o resto
        cleaned = re.sub(r'[^\d+]', '', phone)
        digits = re.sub(r'\D', '', cleaned)
        if len(digits) < 10 or len(digits) > 15:
            raise forms.ValidationError("Telefone inválido. Use o formato +5585...")
        # garante prefixo +
        if not cleaned.startswith('+'):
            cleaned = '+' + digits
        else:
            cleaned = '+' + digits  # normaliza removendo outros símbolos
        return cleaned

class ClientVerifyForm(forms.Form):
    phone = forms.CharField(widget=forms.HiddenInput())
    code = forms.CharField(label="Código recebido", max_length=6)