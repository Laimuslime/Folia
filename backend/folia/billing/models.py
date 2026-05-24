from django.db import models
from django.conf import settings


class Plan(models.Model):
    name = models.CharField(max_length=50, unique=True)
    display_name = models.CharField(max_length=100)
    price_monthly = models.IntegerField(default=0, help_text="月费，单位：分")
    price_yearly = models.IntegerField(default=0, help_text="年费，单位：分")

    max_pages = models.IntegerField(default=200)
    max_storage = models.BigIntegerField(default=314572800, help_text="最大存储，字节")
    max_upload_size = models.IntegerField(default=5242880, help_text="单文件上传限制，字节")
    max_members = models.IntegerField(default=50)

    allow_custom_domain = models.BooleanField(default=False)
    allow_private = models.BooleanField(default=False)
    remove_branding = models.BooleanField(default=False)

    sort_order = models.IntegerField(default=0)
    active = models.BooleanField(default=True)

    class Meta:
        db_table = "billing_plan"
        ordering = ["sort_order"]

    def __str__(self):
        return self.display_name


class Subscription(models.Model):
    PERIOD_CHOICES = [("monthly", "月付"), ("yearly", "年付")]
    STATUS_CHOICES = [
        ("active", "生效中"),
        ("expired", "已过期"),
        ("cancelled", "已取消"),
    ]

    site = models.OneToOneField("sites.Site", on_delete=models.CASCADE, related_name="subscription")
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name="subscriptions")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")
    period = models.CharField(max_length=20, choices=PERIOD_CHOICES, default="monthly")
    current_period_start = models.DateTimeField(null=True, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "billing_subscription"

    def __str__(self):
        return f"{self.site.slug} — {self.plan.name} ({self.status})"

    @property
    def is_active(self):
        from django.utils import timezone
        if self.status != "active":
            return False
        if self.current_period_end and self.current_period_end < timezone.now():
            return False
        return True


class Payment(models.Model):
    CHANNEL_CHOICES = [("wechat", "微信"), ("alipay", "支付宝")]
    STATUS_CHOICES = [
        ("pending", "待支付"),
        ("paid", "已支付"),
        ("failed", "失败"),
        ("refunded", "已退款"),
    ]

    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name="payments", null=True, blank=True)
    site = models.ForeignKey("sites.Site", on_delete=models.CASCADE, related_name="payments")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="payments")
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT)
    period = models.CharField(max_length=20, default="monthly")
    amount = models.IntegerField(help_text="金额，单位：分")
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES, default="wechat")
    out_trade_no = models.CharField(max_length=64, unique=True, help_text="我方订单号")
    trade_no = models.CharField(max_length=64, blank=True, help_text="支付平台订单号")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "billing_payment"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.out_trade_no} — ¥{self.amount / 100:.2f} ({self.status})"
