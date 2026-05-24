from django.urls import path
from .views import PlanListView, SubscriptionView, CreateOrderView, PaymentCallbackView, OrderStatusView

urlpatterns = [
    path("plans/", PlanListView.as_view(), name="billing-plans"),
    path("subscription/", SubscriptionView.as_view(), name="billing-subscription"),
    path("create-order/", CreateOrderView.as_view(), name="billing-create-order"),
    path("callback/", PaymentCallbackView.as_view(), name="billing-callback"),
    path("order-status/<int:order_id>/", OrderStatusView.as_view(), name="billing-order-status"),
]
