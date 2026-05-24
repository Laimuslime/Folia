from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from .search import search_pages


class SearchView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        site = getattr(request, "current_site", None)
        if not site:
            return Response({"detail": "需要站点上下文。"}, status=400)

        query = request.query_params.get("q", "")
        if not query:
            return Response({"hits": [], "total": 0, "query": ""})

        category = request.query_params.get("category")
        tags = request.query_params.get("tags")
        sort = request.query_params.get("sort")
        limit = int(request.query_params.get("limit", 20))
        offset = int(request.query_params.get("offset", 0))

        filters = []
        if category:
            filters.append(f'category = "{category}"')
        if tags:
            for tag in tags.split(","):
                filters.append(f'tags = "{tag.strip()}"')

        filter_str = " AND ".join(filters) if filters else None
        sort_list = [sort] if sort else None

        result = search_pages(site, query, filters=filter_str, sort=sort_list, limit=limit, offset=offset)
        return Response(result)
