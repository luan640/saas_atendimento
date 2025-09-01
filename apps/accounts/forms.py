from django import forms
from django.contrib.auth import authenticate

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
    phone = forms.CharField(label="Telefone (ex.: +5585...)")
    username = f'{full_name}_{phone}'

class ClientVerifyForm(forms.Form):
    phone = forms.CharField(widget=forms.HiddenInput())
    code = forms.CharField(label="Código recebido", max_length=6)