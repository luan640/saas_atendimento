from django.contrib import admin
from .models import User, Subscription, PlanInfo

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("email", "is_owner", "is_client", "phone", "full_name")
    search_fields = ("email", "phone", "full_name")
    list_filter = ("is_owner", "is_client")

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("owner", "plan", "start_date", "end_date")
    list_filter = ("plan",)

@admin.register(PlanInfo)
class PlanInfoAdmin(admin.ModelAdmin):
    list_display = ("plan", "max_lojas", "max_funcionarios")
    list_editable = ("max_lojas", "max_funcionarios")
    ordering = ("plan",)
