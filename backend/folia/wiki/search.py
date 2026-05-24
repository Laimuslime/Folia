"""
Search integration with Meilisearch.
Indexes pages for full-text search within each site.
"""
import meilisearch
from django.conf import settings


def get_client():
    return meilisearch.Client(settings.MEILI_URL, settings.MEILI_KEY)


def get_index_name(site):
    return f"pages_{site.slug}"


def ensure_index(site):
    client = get_client()
    index_name = get_index_name(site)
    try:
        client.get_index(index_name)
    except meilisearch.errors.MeilisearchApiError:
        client.create_index(index_name, {"primaryKey": "id"})
        index = client.index(index_name)
        index.update_searchable_attributes(["title", "source", "tags", "unix_name"])
        index.update_filterable_attributes(["category", "tags"])
        index.update_sortable_attributes(["date_created", "date_last_edited", "rate"])
    return client.index(index_name)


def index_page(page):
    try:
        index = ensure_index(page.site)
        doc = {
            "id": page.pk,
            "unix_name": page.unix_name,
            "title": page.title,
            "source": page.current_source,
            "category": page.category.name if page.category else "_default",
            "tags": list(page.tags.values_list("tag", flat=True)),
            "rate": page.rate,
            "date_created": page.date_created.isoformat() if page.date_created else None,
            "date_last_edited": page.date_last_edited.isoformat() if page.date_last_edited else None,
        }
        index.add_documents([doc])
    except Exception:
        pass


def remove_page(page_id, site):
    try:
        index = ensure_index(site)
        index.delete_document(page_id)
    except Exception:
        pass


def search_pages(site, query, filters=None, sort=None, limit=20, offset=0):
    try:
        index = ensure_index(site)
        params = {"limit": limit, "offset": offset}
        if filters:
            params["filter"] = filters
        if sort:
            params["sort"] = sort
        result = index.search(query, params)
        return {
            "hits": result.get("hits", []),
            "total": result.get("estimatedTotalHits", 0),
            "query": query,
        }
    except Exception:
        return {"hits": [], "total": 0, "query": query}


def reindex_site(site):
    from folia.wiki.models import Page
    pages = Page.objects.filter(site=site).select_related("category").prefetch_related("tags")
    for page in pages:
        index_page(page)
