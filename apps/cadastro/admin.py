from django.contrib import admin
from .models import Loja, Funcionario, Servico

@admin.register(Loja)
class LojaAdmin(admin.ModelAdmin):
    list_display = ("nome", "owner", "slug", "ativa", "criada_em")
    list_filter = ("ativa",)
    search_fields = ("nome", "slug", "owner__email")

@admin.register(Servico)
class ServicoAdmin(admin.ModelAdmin):
    list_display = ("nome", "loja", "preco", "duracao_minutos", "ativo", "atualizado_em")
    list_filter = ("ativo", "loja")
    search_fields = ("nome", "slug", "descricao", "loja__nome")
    filter_horizontal = ("profissionais",)
