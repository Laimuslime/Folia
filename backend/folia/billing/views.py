import uuid
from django.utils import timezone
from dateutil.relativedelta import relativedelta
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny

from .models import Plan, Subscription, Payment
from .serializers import PlanSerializer, SubscriptionSerializer, CreateOrderSerializer, PaymentSerializer
from . import xunhupay


class PlanListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        plans = Plan.objects.filter(active=True)
        return Response(PlanSerializer(plans, many=True).data)


class SubscriptionView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        site = getattr(request, "site", None)
        if not site:
            return Response({"detail": "站点未找到"}, status=status.HTTP_404_NOT_FOUND)
        try:
            sub = Subscription.objects.select_related("plan").get(site=site)
        except Subscription.DoesNotExist:
            free_plan = Plan.objects.filter(name="free").first()
            return Response({
                "plan": PlanSerializer(free_plan).data if free_plan else None,
                "status": "active",
                "period": None,
                "current_period_start": None,
                "current_period_end": None,
            })
        return Response(SubscriptionSerializer(sub).data)


class CreateOrderView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        site = getattr(request, "site", None)
        if not site:
            return Response({"detail": "站点未找到"}, status=status.HTTP_404_NOT_FOUND)

        serializer = CreateOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        plan = Plan.objects.filter(id=serializer.validated_data["plan_id"], active=True).first()
        if not plan:
            return Response({"detail": "套餐不存在"}, status=status.HTTP_400_BAD_REQUEST)

        period = serializer.validated_data["period"]
        channel = serializer.validated_data["channel"]
        amount = plan.price_yearly if period == "yearly" else plan.price_monthly

        if amount <= 0:
            return Response({"detail": "免费套餐无需支付"}, status=status.HTTP_400_BAD_REQUEST)

        trade_no = f"FOLIA-{uuid.uuid4().hex[:16].upper()}"

        payment = Payment.objects.create(
            site=site,
            user=request.user,
            plan=plan,
            period=period,
            amount=amount,
            channel=channel,
            out_trade_no=trade_no,
        )

        notify_url = request.build_absolute_uri("/api/v1/billing/callback/")
        result = xunhupay.create_order(
            trade_no=trade_no,
            amount=amount,
            title=f"Folia {plan.display_name} - {'年付' if period == 'yearly' else '月付'}",
            notify_url=notify_url,
            channel=channel,
        )

        if result.get("errcode") != 0:
            payment.status = "failed"
            payment.save(update_fields=["status"])
            return Response({"detail": result.get("errmsg", "创建订单失败")}, status=status.HTTP_502_BAD_GATEWAY)

        return Response({
            "order_id": payment.id,
            "out_trade_no": trade_no,
            "qr_url": result.get("url_qrcode", ""),
            "pay_url": result.get("url", ""),
        })


class PaymentCallbackView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        params = request.data.dict() if hasattr(request.data, "dict") else dict(request.data)

        if not xunhupay.verify_callback(params):
            return Response("fail", status=status.HTTP_400_BAD_REQUEST)

        trade_no = params.get("outTradeNo", "")
        code = params.get("code", "")

        try:
            payment = Payment.objects.get(out_trade_no=trade_no)
        except Payment.DoesNotExist:
            return Response("fail", status=status.HTTP_404_NOT_FOUND)

        if code == "1" and payment.status == "pending":
            payment.status = "paid"
            payment.trade_no = params.get("payNo", "")
            payment.paid_at = timezone.now()
            payment.save(update_fields=["status", "trade_no", "paid_at"])
            self._activate_subscription(payment)

        return Response("success")

    def _activate_subscription(self, payment):
        now = timezone.now()
        if payment.period == "yearly":
            end = now + relativedelta(years=1)
        else:
            end = now + relativedelta(months=1)

        sub, created = Subscription.objects.update_or_create(
            site=payment.site,
            defaults={
                "plan": payment.plan,
                "status": "active",
                "period": payment.period,
                "current_period_start": now,
                "current_period_end": end,
            },
        )
        payment.subscription = sub
        payment.save(update_fields=["subscription"])


class OrderStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, order_id):
        try:
            payment = Payment.objects.get(id=order_id, user=request.user)
        except Payment.DoesNotExist:
            return Response({"detail": "订单不存在"}, status=status.HTTP_404_NOT_FOUND)
        return Response(PaymentSerializer(payment).data)
