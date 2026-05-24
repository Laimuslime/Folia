from django.contrib import admin
from .models import Plan, Subscription, Payment


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ["name", "display_name", "price_monthly", "price_yearly", "active", "sort_order"]
    list_editable = ["sort_order", "active"]


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ["site", "plan", "status", "period", "current_period_end"]
    list_filter = ["status", "plan"]
    raw_id_fields = ["site"]


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ["out_trade_no", "site", "user", "plan", "amount", "channel", "status", "created_at"]
    list_filter = ["status", "channel"]
    raw_id_fields = ["site", "user", "subscription"]
    readonly_fields = ["out_trade_no", "trade_no", "paid_at"]
