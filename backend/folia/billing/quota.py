from django.db.models import Sum
from rest_framework.exceptions import PermissionDenied

from .models import Plan, Subscription


def get_site_plan(site) -> Plan:
    try:
        sub = Subscription.objects.select_related("plan").get(site=site)
        if sub.is_active:
            return sub.plan
    except Subscription.DoesNotExist:
        pass
    return Plan.objects.filter(name="free").first()


def check_page_limit(site):
    from folia.wiki.models import Page
    plan = get_site_plan(site)
    if not plan or plan.max_pages <= 0:
        return
    count = Page.objects.filter(site=site).count()
    if count >= plan.max_pages:
        raise PermissionDenied(f"已达页面上限（{plan.max_pages}），请升级套餐")


def check_storage_limit(site, additional_bytes=0):
    from folia.wiki.models import File
    plan = get_site_plan(site)
    if not plan or plan.max_storage <= 0:
        return
    used = File.objects.filter(site=site).aggregate(total=Sum("size"))["total"] or 0
    if used + additional_bytes > plan.max_storage:
        limit_mb = plan.max_storage / (1024 * 1024)
        raise PermissionDenied(f"存储空间已满（限制 {limit_mb:.0f}MB），请升级套餐")


def check_upload_size(site, file_size):
    plan = get_site_plan(site)
    if not plan:
        return
    if file_size > plan.max_upload_size:
        limit_mb = plan.max_upload_size / (1024 * 1024)
        raise PermissionDenied(f"文件超过大小限制（{limit_mb:.0f}MB），请升级套餐")


def check_member_limit(site):
    from folia.sites.models import Member
    plan = get_site_plan(site)
    if not plan or plan.max_members <= 0:
        return
    count = Member.objects.filter(site=site).count()
    if count >= plan.max_members:
        raise PermissionDenied(f"已达成员上限（{plan.max_members}），请升级套餐")


def can_use_feature(site, feature: str) -> bool:
    plan = get_site_plan(site)
    if not plan:
        return False
    feature_map = {
        "custom_domain": plan.allow_custom_domain,
        "private": plan.allow_private,
        "remove_branding": plan.remove_branding,
    }
    return feature_map.get(feature, False)
