from django.contrib import admin
from .models import Agendamento
from apps.cadastro.models import Funcionario

@admin.register(Agendamento)
class AgendamentoAdmin(admin.ModelAdmin):
    list_display = (
        "cliente",
        "loja",
        "funcionario",
        "lista_servicos",
        "data",
        "hora",
        "confirmado",
        "no_show",
        "criado_em",
    )
    list_filter = ("loja", "funcionario", "servicos", "confirmado", "no_show", "data")
    search_fields = (
        "cliente__full_name",
        "cliente__email",
        "cliente__phone",
        "funcionario__nome",
        "servicos__nome",
        "loja__nome",
    )
    ordering = ("-data", "-hora")
    date_hierarchy = "data"
    autocomplete_fields = ("cliente", "loja", "servicos")
    list_editable = ("confirmado", "no_show")

    def lista_servicos(self, obj):
        return ", ".join(s.nome for s in obj.servicos.all()[:3]) + (
            "..." if obj.servicos.count() > 3 else ""
        )
    lista_servicos.short_description = "Serviços"
