from django.core.management.base import BaseCommand
from folia.sites.models import Site
from folia.wiki.search import reindex_site


class Command(BaseCommand):
    help = "Reindex all pages in Meilisearch for one or all sites"

    def add_arguments(self, parser):
        parser.add_argument("--site", type=str, help="Site slug to reindex (default: all)")

    def handle(self, *args, **options):
        site_slug = options.get("site")
        if site_slug:
            sites = Site.objects.filter(slug=site_slug)
        else:
            sites = Site.objects.all()

        for site in sites:
            self.stdout.write(f"Reindexing {site.slug}...")
            reindex_site(site)
            page_count = site.pages.count()
            self.stdout.write(self.style.SUCCESS(f"  Indexed {page_count} pages."))

        self.stdout.write(self.style.SUCCESS("Done."))
