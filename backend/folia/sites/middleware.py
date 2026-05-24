from django.conf import settings


class SiteMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        site_slug = self._extract_site_slug(request)
        request.site_slug = site_slug
        request.current_site = None

        if site_slug:
            from .models import Site
            try:
                site = Site.objects.get(slug=site_slug)
                request.current_site = site
                if site.suspended and not (request.user and request.user.is_superuser):
                    from django.http import JsonResponse
                    return JsonResponse({"detail": "This site has been suspended."}, status=403)
            except Site.DoesNotExist:
                pass

        return self.get_response(request)

    def _extract_site_slug(self, request):
        slug = request.META.get("HTTP_X_SITE_SLUG")
        if slug:
            return slug

        host = request.get_host().split(":")[0]
        domain = settings.FOLIA_DOMAIN
        if host.endswith(f".{domain}"):
            return host[: -(len(domain) + 1)]

        return None
