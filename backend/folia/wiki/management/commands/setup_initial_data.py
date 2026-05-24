from django.core.management.base import BaseCommand
from folia.sites.models import Site, SiteSettings, Admin, Member, License, Theme
from folia.wiki.models import Category, Page, PageSource, PageCompiled
from folia.forums.models import ForumGroup, ForumCategory
from folia.wiki.parser import render_wikidot_markup
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = "Set up initial data: licenses, themes, and optionally a demo site"

    def add_arguments(self, parser):
        parser.add_argument("--demo", action="store_true", help="Create a demo site")

    def handle(self, *args, **options):
        self._create_licenses()
        self._create_themes()

        if options["demo"]:
            self._create_demo_site()

        self.stdout.write(self.style.SUCCESS("Initial data created."))

    def _create_licenses(self):
        licenses = [
            ("Creative Commons Attribution-ShareAlike 3.0", "https://creativecommons.org/licenses/by-sa/3.0/", 1),
            ("Creative Commons Attribution 3.0", "https://creativecommons.org/licenses/by/3.0/", 2),
            ("Creative Commons Attribution-NonCommercial-ShareAlike 3.0", "https://creativecommons.org/licenses/by-nc-sa/3.0/", 3),
            ("GNU Free Documentation License 1.3", "https://www.gnu.org/licenses/fdl-1.3.html", 4),
            ("Public Domain", "", 5),
            ("Other (see site for details)", "", 10),
        ]
        for name, url, sort in licenses:
            License.objects.get_or_create(name=name, defaults={"url": url, "sort": sort})
        self.stdout.write(f"  Created {len(licenses)} licenses.")

    def _create_themes(self):
        themes = [
            ("Base", "base", False),
            ("Sigma-9", "sigma-9", False),
            ("Black Highlighter", "black-highlighter", False),
            ("Minimal", "minimal", False),
        ]
        for name, unix_name, abstract in themes:
            Theme.objects.get_or_create(unix_name=unix_name, defaults={"name": name, "abstract": abstract})
        self.stdout.write(f"  Created {len(themes)} themes.")

    def _create_demo_site(self):
        if Site.objects.filter(slug="demo").exists():
            self.stdout.write("  Demo site already exists.")
            return

        admin_user = User.objects.filter(is_superuser=True).first()
        if not admin_user:
            self.stdout.write(self.style.WARNING("  No superuser found. Create one first."))
            return

        site = Site.objects.create(
            unix_name="demo", slug="demo", name="Demo Wiki",
            subtitle="A demonstration wiki", description="This is a demo wiki for testing Folia.",
        )
        SiteSettings.objects.create(site=site)
        Admin.objects.create(site=site, user=admin_user, founder=True)
        Member.objects.create(site=site, user=admin_user)

        default_cat, _ = Category.objects.get_or_create(site=site, name="_default")
        nav_cat, _ = Category.objects.get_or_create(site=site, name="nav")

        pages_data = [
            ("start", "Welcome", default_cat, (
                "+ Welcome to the Demo Wiki\n\n"
                "This is a demonstration of the Folia wiki farm platform.\n\n"
                "++ Features\n\n"
                "* Full Wikidot syntax support\n"
                "* Module system (ListPages, Rate, TagCloud, etc.)\n"
                "* Forum system\n"
                "* File management\n"
                "* Version history\n\n"
                "[[collapsible show=\"+ Click to expand\" hide=\"- Click to collapse\"]]\n"
                "This is hidden content inside a collapsible block.\n"
                "[[/collapsible]]\n\n"
                "[[module Rate]]\n"
            )),
            ("side", "Side Navigation", nav_cat, (
                "* [/ Home]\n"
                "* [/system:list-all-pages All Pages]\n"
                "* [/system:recent-changes Recent Changes]\n"
                "* [/forum:start Forum]\n"
            )),
        ]

        for unix_name, title, category, source_text in pages_data:
            page = Page.objects.create(
                site=site, category=category, unix_name=unix_name,
                title=title, owner_user=admin_user, last_edit_user=admin_user,
            )
            PageSource.objects.create(page=page, text=source_text)
            PageCompiled.objects.create(page=page, text=render_wikidot_markup(source_text, site))

        # Forum
        group = ForumGroup.objects.create(site=site, name="General", description="General discussion")
        ForumCategory.objects.create(group=group, site=site, name="General Discussion", description="Talk about anything")
        ForumCategory.objects.create(group=group, site=site, name="Help & Questions", description="Ask for help")

        self.stdout.write(self.style.SUCCESS("  Demo site created at demo.folia.localhost"))
