from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser
from .models import User
from .serializers import (
    UserSerializer, UserRegistrationSerializer,
    ProfileUpdateSerializer, ChangePasswordSerializer, ChangeEmailSerializer,
)


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]


class ProfileView(generics.RetrieveUpdateAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method in ("PUT", "PATCH"):
            return ProfileUpdateSerializer
        return UserSerializer

    def get_object(self):
        return self.request.user

    def retrieve(self, request, *args, **kwargs):
        user = self.get_object()
        data = UserSerializer(user).data
        data["email"] = user.email
        data["language"] = user.language
        data["receive_pm"] = user.receive_pm
        return Response(data)


class UserDetailView(generics.RetrieveAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    lookup_field = "username"


class ChangePasswordView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        if not user.check_password(serializer.validated_data["old_password"]):
            return Response({"detail": "旧密码不正确。"}, status=status.HTTP_400_BAD_REQUEST)
        user.set_password(serializer.validated_data["new_password"])
        user.save()
        return Response({"detail": "密码已修改。"})


class ChangeEmailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def put(self, request):
        serializer = ChangeEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        request.user.email = serializer.validated_data["email"]
        request.user.save(update_fields=["email"])
        return Response({"detail": "邮箱已修改。"})


class AvatarUploadView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser]

    def post(self, request):
        avatar = request.FILES.get("avatar")
        if not avatar:
            return Response({"detail": "请选择头像文件。"}, status=status.HTTP_400_BAD_REQUEST)
        if avatar.size > 2 * 1024 * 1024:
            return Response({"detail": "头像文件不能超过 2MB。"}, status=status.HTTP_400_BAD_REQUEST)
        request.user.avatar = avatar
        request.user.save(update_fields=["avatar"])
        return Response({"avatar": request.user.avatar.url if request.user.avatar else None})


class UserSitesView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, username):
        from folia.sites.models import Member, Site
        from folia.sites.serializers import SiteSerializer
        user = generics.get_object_or_404(User, username=username)
        site_ids = Member.objects.filter(user=user).values_list("site_id", flat=True)
        sites = Site.objects.filter(id__in=site_ids, visible=True)
        return Response(SiteSerializer(sites, many=True).data)


class UserActivityView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, username):
        from folia.wiki.models import PageRevision
        user = generics.get_object_or_404(User, username=username)
        revisions = PageRevision.objects.filter(user=user).select_related("page", "site").order_by("-date_last_edited")[:20]
        activity = []
        for rev in revisions:
            act_type = "create" if rev.flag_new else "edit"
            activity.append({
                "type": act_type,
                "date": rev.date_last_edited.isoformat() if rev.date_last_edited else "",
                "page_slug": rev.page.unix_name if rev.page else "",
                "page_title": rev.page.title if rev.page else "",
                "site_name": rev.site.name if rev.site else "",
            })
        return Response(activity)


class MessageListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from .models import UserMessage
        folder = request.query_params.get("folder", "inbox")
        if folder == "sent":
            messages = UserMessage.objects.filter(sender=request.user).order_by("-created_at")[:50]
        else:
            messages = UserMessage.objects.filter(recipient=request.user).order_by("-created_at")[:50]
        data = []
        for m in messages:
            data.append({
                "id": m.id,
                "sender": m.sender.username,
                "recipient": m.recipient.username,
                "subject": m.subject,
                "body": m.body,
                "read": m.read,
                "created_at": m.created_at.isoformat(),
            })
        return Response(data)

    def post(self, request):
        from .models import UserMessage
        recipient_name = request.data.get("recipient")
        subject = request.data.get("subject", "")
        body = request.data.get("body", "")
        if not recipient_name or not subject or not body:
            return Response({"detail": "请填写收件人、主题和内容。"}, status=status.HTTP_400_BAD_REQUEST)
        recipient = User.objects.filter(username=recipient_name).first()
        if not recipient:
            return Response({"detail": "收件人不存在。"}, status=status.HTTP_404_NOT_FOUND)
        if not recipient.receive_pm:
            return Response({"detail": "该用户不接受私信。"}, status=status.HTTP_403_FORBIDDEN)
        UserMessage.objects.create(sender=request.user, recipient=recipient, subject=subject, body=body)
        return Response({"detail": "私信已发送。"}, status=status.HTTP_201_CREATED)
