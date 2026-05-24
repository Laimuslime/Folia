from rest_framework import serializers
from .models import Plan, Subscription, Payment


class PlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plan
        fields = [
            "id", "name", "display_name",
            "price_monthly", "price_yearly",
            "max_pages", "max_storage", "max_upload_size", "max_members",
            "allow_custom_domain", "allow_private", "remove_branding",
        ]


class SubscriptionSerializer(serializers.ModelSerializer):
    plan = PlanSerializer(read_only=True)

    class Meta:
        model = Subscription
        fields = [
            "id", "plan", "status", "period",
            "current_period_start", "current_period_end",
            "created_at",
        ]


class CreateOrderSerializer(serializers.Serializer):
    plan_id = serializers.IntegerField()
    period = serializers.ChoiceField(choices=["monthly", "yearly"])
    channel = serializers.ChoiceField(choices=["wechat", "alipay"])


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ["id", "out_trade_no", "amount", "channel", "status", "created_at", "paid_at"]
