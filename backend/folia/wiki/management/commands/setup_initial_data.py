from django.core.management.base import BaseCommand
from folia.sites.models import Site, SiteSettings, Admin, Member, License, Theme
from folia.wiki.models import Category, Page, PageSource, PageCompiled
from folia.forums.models import ForumGroup, ForumCategory
from folia.wiki.parser import render_wikidot_markup
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = "初始化数据：许可证、主题，可选创建演示站点"

    def add_arguments(self, parser):
        parser.add_argument("--demo", action="store_true", help="创建演示站点")

    def handle(self, *args, **options):
        self._create_licenses()
        self._create_themes()

        if options["demo"]:
            self._create_demo_site()

        self.stdout.write(self.style.SUCCESS("初始数据已创建。"))

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
            unix_name="demo", slug="demo", name="演示 Wiki",
            subtitle="演示站点", description="这是 Folia Wiki 农场的演示站点。",
        )
        SiteSettings.objects.create(site=site)
        Admin.objects.create(site=site, user=admin_user, founder=True)
        Member.objects.create(site=site, user=admin_user)

        default_cat, _ = Category.objects.get_or_create(site=site, name="_default")
        nav_cat, _ = Category.objects.get_or_create(site=site, name="nav")

        pages_data = [
            ("start", "欢迎", default_cat, (
                "+ 欢迎来到演示 Wiki\n\n"
                "这是 Folia Wiki 农场平台的演示站点。\n\n"
                "++ 功能\n\n"
                "* 完整的 Wikidot 语法支持\n"
                "* 模块系统（ListPages、Rate、TagCloud 等）\n"
                "* 论坛系统\n"
                "* 文件管理\n"
                "* 版本历史\n\n"
                "[[collapsible show=\"+ 点击展开\" hide=\"- 点击收起\"]]\n"
                "这是折叠块中的隐藏内容。\n"
                "[[/collapsible]]\n\n"
                "[[module Rate]]\n"
            )),
            ("side", "侧边导航", nav_cat, (
                "* [/ 首页]\n"
                "* [/system:list-all-pages 所有页面]\n"
                "* [/system:recent-changes 最近更改]\n"
                "* [/forum:start 论坛]\n"
            )),
        ]

        for unix_name, title, category, source_text in pages_data:
            page = Page.objects.create(
                site=site, category=category, unix_name=unix_name,
                title=title, owner_user=admin_user, last_edit_user=admin_user,
            )
            PageSource.objects.create(page=page, text=source_text)
            PageCompiled.objects.create(page=page, text=render_wikidot_markup(source_text, site))

        # 论坛
        group = ForumGroup.objects.create(site=site, name="综合", description="综合讨论")
        ForumCategory.objects.create(group=group, site=site, name="综合讨论", description="随便聊聊")
        ForumCategory.objects.create(group=group, site=site, name="帮助与提问", description="寻求帮助")

        self.stdout.write(self.style.SUCCESS("  演示站点已创建：demo.brcnwiki.com"))
