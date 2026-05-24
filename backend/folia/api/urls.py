from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from folia.users.views import (
    RegisterView, ProfileView, UserDetailView,
    ChangePasswordView, ChangeEmailView, AvatarUploadView, UserSitesView,
    UserActivityView, MessageListCreateView,
)
from folia.sites.views import SiteViewSet
from folia.wiki.views import PageViewSet, CategoryViewSet, NotificationViewSet
from folia.wiki.ajax import AjaxModuleConnectorView
from folia.wiki.system_pages import SystemPageView
from folia.wiki.search_views import SearchView
from folia.forums.views import ForumGroupViewSet, ForumThreadViewSet, ForumPostViewSet
from folia.sites.platform_views import (
    PlatformSiteListView, PlatformSiteSuspendView, PlatformSiteDeleteView,
    PlatformUserListView, PlatformUserBanView, PlatformUserUnbanView, PlatformStatsView,
)

router = DefaultRouter()
router.register(r"sites", SiteViewSet, basename="site")
router.register(r"pages", PageViewSet, basename="page")
router.register(r"categories", CategoryViewSet, basename="category")
router.register(r"forum/groups", ForumGroupViewSet, basename="forum-group")
router.register(r"forum/threads", ForumThreadViewSet, basename="forum-thread")
router.register(r"forum/posts", ForumPostViewSet, basename="forum-post")
router.register(r"notifications", NotificationViewSet, basename="notification")

urlpatterns = [
    path("", include(router.urls)),
    # Auth
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("auth/token/", TokenObtainPairView.as_view(), name="token_obtain"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("auth/profile/", ProfileView.as_view(), name="profile"),
    path("auth/change-password/", ChangePasswordView.as_view(), name="change-password"),
    path("auth/change-email/", ChangeEmailView.as_view(), name="change-email"),
    path("auth/avatar/", AvatarUploadView.as_view(), name="avatar-upload"),
    # Users
    path("users/<str:username>/", UserDetailView.as_view(), name="user-detail"),
    path("users/<str:username>/sites/", UserSitesView.as_view(), name="user-sites"),
    path("users/<str:username>/activity/", UserActivityView.as_view(), name="user-activity"),
    # Messages
    path("messages/", MessageListCreateView.as_view(), name="messages"),
    # AJAX Module Connector (Wikidot compatibility)
    path("ajax-module-connector/", AjaxModuleConnectorView.as_view(), name="ajax-module-connector"),
    # System pages
    path("system/<str:page_name>/", SystemPageView.as_view(), name="system-page"),
    # Search
    path("search/", SearchView.as_view(), name="search"),
    # Platform admin
    path("platform/sites/", PlatformSiteListView.as_view(), name="platform-sites"),
    path("platform/sites/<int:site_id>/suspend/", PlatformSiteSuspendView.as_view(), name="platform-site-suspend"),
    path("platform/sites/<int:site_id>/", PlatformSiteDeleteView.as_view(), name="platform-site-delete"),
    path("platform/users/", PlatformUserListView.as_view(), name="platform-users"),
    path("platform/users/<int:user_id>/ban/", PlatformUserBanView.as_view(), name="platform-user-ban"),
    path("platform/users/<int:user_id>/unban/", PlatformUserUnbanView.as_view(), name="platform-user-unban"),
    path("platform/stats/", PlatformStatsView.as_view(), name="platform-stats"),
]
