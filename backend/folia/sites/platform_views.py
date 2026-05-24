from django.db.models import Count, Sum
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination

from .permissions import IsPlatformSuperuser
from .models import Site, PlatformBan
from folia.users.models import User


class PlatformSiteListView(APIView):
    permission_classes = [IsPlatformSuperuser]

    def get(self, request):
        search = request.query_params.get("search", "")
        qs = Site.objects.all().order_by("-date_created")
        if search:
            qs = qs.filter(name__icontains=search)
        qs = qs.annotate(member_count=Count("members"))

        paginator = PageNumberPagination()
        paginator.page_size = 50
        page = paginator.paginate_queryset(qs, request)
        data = [{
            "id": s.id, "slug": s.slug, "name": s.name,
            "member_count": s.member_count, "suspended": s.suspended,
            "private": s.private, "date_created": s.date_created,
        } for s in page]
        return paginator.get_paginated_response(data)


class PlatformSiteSuspendView(APIView):
    permission_classes = [IsPlatformSuperuser]

    def post(self, request, site_id):
        site = Site.objects.filter(id=site_id).first()
        if not site:
            return Response(status=status.HTTP_404_NOT_FOUND)
        site.suspended = not site.suspended
        site.save(update_fields=["suspended"])
        return Response({"suspended": site.suspended})


class PlatformSiteDeleteView(APIView):
    permission_classes = [IsPlatformSuperuser]

    def delete(self, request, site_id):
        site = Site.objects.filter(id=site_id).first()
        if not site:
            return Response(status=status.HTTP_404_NOT_FOUND)
        site.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class PlatformUserListView(APIView):
    permission_classes = [IsPlatformSuperuser]

    def get(self, request):
        search = request.query_params.get("search", "")
        qs = User.objects.all().order_by("-date_joined")
        if search:
            qs = qs.filter(username__icontains=search)

        paginator = PageNumberPagination()
        paginator.page_size = 50
        page = paginator.paginate_queryset(qs, request)
        banned_ids = set(PlatformBan.objects.values_list("user_id", flat=True))
        data = [{
            "id": u.id, "username": u.username, "email": u.email,
            "is_superuser": u.is_superuser, "is_active": u.is_active,
            "banned": u.id in banned_ids, "date_joined": u.date_joined,
        } for u in page]
        return paginator.get_paginated_response(data)


class PlatformUserBanView(APIView):
    permission_classes = [IsPlatformSuperuser]

    def post(self, request, user_id):
        user = User.objects.filter(id=user_id).first()
        if not user:
            return Response(status=status.HTTP_404_NOT_FOUND)
        reason = request.data.get("reason", "")
        PlatformBan.objects.get_or_create(user=user, defaults={"reason": reason, "banned_by": request.user})
        user.is_active = False
        user.save(update_fields=["is_active"])
        return Response({"detail": "User banned."})


class PlatformUserUnbanView(APIView):
    permission_classes = [IsPlatformSuperuser]

    def post(self, request, user_id):
        user = User.objects.filter(id=user_id).first()
        if not user:
            return Response(status=status.HTTP_404_NOT_FOUND)
        PlatformBan.objects.filter(user=user).delete()
        user.is_active = True
        user.save(update_fields=["is_active"])
        return Response({"detail": "User unbanned."})


class PlatformStatsView(APIView):
    permission_classes = [IsPlatformSuperuser]

    def get(self, request):
        from folia.wiki.models import Page
        return Response({
            "total_sites": Site.objects.count(),
            "total_users": User.objects.count(),
            "total_pages": Page.objects.count(),
            "active_sites": Site.objects.filter(suspended=False).count(),
            "banned_users": PlatformBan.objects.count(),
        })
