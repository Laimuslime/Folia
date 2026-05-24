"""
权限系统 — 基于分类的权限模型。

每个分类可设置以下操作的权限：
  edit, create, move, delete, attach, rename, options, rate

每个操作可设为：
  'a' = 所有人（含匿名）
  'r' = 注册用户
  'm' = 站点成员
  'o' = 管理员 + 版主
  '' = 继承站点默认
"""
from folia.sites.models import Site, Member, Admin, Moderator


PERMISSION_ACTIONS = ("edit", "create", "move", "delete", "attach", "rename", "options", "rate")

SITE_DEFAULTS = {
    "edit": "m",
    "create": "m",
    "move": "o",
    "delete": "o",
    "attach": "m",
    "rename": "o",
    "options": "o",
    "rate": "m",
}


def parse_category_permissions(permissions_str: str) -> dict:
    perms = {}
    if not permissions_str:
        return perms
    for part in permissions_str.split(";"):
        part = part.strip()
        if ":" in part:
            action, level = part.split(":", 1)
            perms[action.strip()] = level.strip()
    return perms


def get_effective_permission(category, action: str) -> str:
    if category and not category.permissions_default and category.permissions:
        cat_perms = parse_category_permissions(category.permissions)
        if action in cat_perms:
            return cat_perms[action]
    return SITE_DEFAULTS.get(action, "m")


def get_user_role(user, site) -> str:
    if not user or not user.is_authenticated:
        return "anonymous"
    if user.is_superuser:
        return "admin"
    if Admin.objects.filter(site=site, user=user).exists():
        return "admin"
    if Moderator.objects.filter(site=site, user=user).exists():
        return "moderator"
    if Member.objects.filter(site=site, user=user).exists():
        return "member"
    return "registered"


def check_permission(user, site, category, action: str) -> bool:
    if user and user.is_superuser:
        return True

    role = get_user_role(user, site)
    level = get_effective_permission(category, action)

    if level == "a":
        return True
    if level == "r":
        return role != "anonymous"
    if level == "m":
        return role in ("member", "moderator", "admin")
    if level == "o":
        return role in ("moderator", "admin")
    return False


def can_view_page(user, site, page) -> bool:
    if not site.private:
        return True
    if not user or not user.is_authenticated:
        return False
    return get_user_role(user, site) in ("member", "moderator", "admin")


def can_edit_page(user, site, page) -> bool:
    if page and page.blocked:
        return get_user_role(user, site) in ("moderator", "admin")
    return check_permission(user, site, page.category if page else None, "edit")


def can_create_page(user, site, category=None) -> bool:
    return check_permission(user, site, category, "create")


def can_delete_page(user, site, page) -> bool:
    return check_permission(user, site, page.category if page else None, "delete")


def can_rate_page(user, site, page) -> bool:
    return check_permission(user, site, page.category if page else None, "rate")


def can_attach_file(user, site, page) -> bool:
    return check_permission(user, site, page.category if page else None, "attach")


def can_rename_page(user, site, page) -> bool:
    return check_permission(user, site, page.category if page else None, "rename")
