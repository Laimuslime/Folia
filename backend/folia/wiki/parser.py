"""
Wikidot markup parser for Folia.

This is a Python implementation of the core Wikidot syntax.
For production use, this should be replaced with FTML (Rust/WASM) bindings
for full compatibility. This implementation covers the most common syntax elements.
"""
import re
import html


def render_wikidot_markup(source: str, site=None, page=None, user=None) -> str:
    parser = WikidotParser(site, page, user)
    return parser.render(source)


def extract_wiki_links(source: str) -> list[str]:
    """Extract all wiki link targets from Wikidot markup source."""
    links = set()
    for match in re.finditer(r'\[\[\[([^\]|#]+)', source):
        target = match.group(1).strip().lower()
        target = re.sub(r'[^a-z0-9:_/-]', '-', target)
        if target:
            links.add(target)
    return list(links)


class WikidotParser:
    def __init__(self, site=None, page=None, user=None):
        self.site = site
        self.page = page
        self.user = user
        self.footnotes = []
        self.toc_entries = []

    def render(self, source: str) -> str:
        # Process includes first
        source = self._process_includes(source)

        lines = source.split("\n")
        output = []
        i = 0

        while i < len(lines):
            line = lines[i]

            # Code blocks
            if line.strip().startswith("[[code"):
                block, i = self._parse_code_block(lines, i)
                output.append(block)
                continue

            # Module blocks
            if line.strip().startswith("[[module"):
                block, i = self._parse_module_block(lines, i)
                output.append(block)
                continue

            # Collapsible blocks
            if line.strip().startswith("[[collapsible"):
                block, i = self._parse_collapsible(lines, i)
                output.append(block)
                continue

            # Div blocks
            if line.strip().startswith("[[div"):
                block, i = self._parse_div(lines, i)
                output.append(block)
                continue

            # Tabview
            if line.strip() == "[[tabview]]":
                block, i = self._parse_tabview(lines, i)
                output.append(block)
                continue

            # Horizontal rule
            if line.strip().startswith("----"):
                output.append("<hr>")
                i += 1
                continue

            # Headings
            heading_match = re.match(r"^(\+{1,6})\s+(.+)$", line)
            if heading_match:
                level = len(heading_match.group(1))
                text = self._inline(heading_match.group(2))
                anchor = re.sub(r"[^a-z0-9]+", "-", heading_match.group(2).lower()).strip("-")
                self.toc_entries.append((level, text, anchor))
                output.append(f'<h{level} id="{anchor}">{text}</h{level}>')
                i += 1
                continue

            # Blockquote
            if line.startswith(">"):
                block, i = self._parse_blockquote(lines, i)
                output.append(block)
                continue

            # Unordered list
            if re.match(r"^\s*\*\s", line):
                block, i = self._parse_list(lines, i, "ul")
                output.append(block)
                continue

            # Ordered list
            if re.match(r"^\s*#\s", line):
                block, i = self._parse_list(lines, i, "ol")
                output.append(block)
                continue

            # Table
            if line.startswith("||"):
                block, i = self._parse_table(lines, i)
                output.append(block)
                continue

            # Empty line = paragraph break
            if not line.strip():
                output.append("")
                i += 1
                continue

            # Normal paragraph
            para, i = self._parse_paragraph(lines, i)
            output.append(f"<p>{para}</p>")

        result = "\n".join(output)

        # Insert TOC if requested
        if "[[toc]]" in source.lower():
            toc_html = self._build_toc()
            result = re.sub(r"\[\[toc\]\]", toc_html, result, flags=re.IGNORECASE)

        # Insert footnotes
        if self.footnotes:
            result += self._build_footnotes()

        return result

    def _process_includes(self, source: str, depth: int = 0) -> str:
        if depth > 5:
            return source

        def replace_include(match):
            page_name = match.group(1).strip()
            params_str = match.group(2) if match.group(2) else ""
            params = {}
            for m in re.finditer(r'\|?\s*(\w+)\s*=\s*([^|]+)', params_str):
                params[m.group(1).strip()] = m.group(2).strip()

            if self.site:
                from folia.wiki.models import Page
                included = Page.objects.filter(site=self.site, unix_name=page_name).first()
                if not included and ":" in page_name:
                    cat, name = page_name.split(":", 1)
                    included = Page.objects.filter(site=self.site, unix_name=name, category__name=cat).first()
                if included:
                    text = included.current_source
                    for key, value in params.items():
                        text = text.replace(f"{{${key}}}", value)
                    return self._process_includes(text, depth + 1)
            return f'<div class="error-block">Include: page "{page_name}" not found.</div>'

        return re.sub(r'\[\[include\s+([^\]|]+)((?:\|[^\]]*)?)\]\]', replace_include, source, flags=re.IGNORECASE)

    def _inline(self, text: str) -> str:
        # Escape HTML first
        text = html.escape(text, quote=False)

        # Bold
        text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
        # Italic
        text = re.sub(r"//(.+?)//", r"<em>\1</em>", text)
        # Underline
        text = re.sub(r"__(.+?)__", r"<u>\1</u>", text)
        # Strikethrough
        text = re.sub(r"--(.+?)--", r"<s>\1</s>", text)
        # Superscript
        text = re.sub(r"\^\^(.+?)\^\^", r"<sup>\1</sup>", text)
        # Subscript
        text = re.sub(r",,(.+?),,", r"<sub>\1</sub>", text)
        # Monospace
        text = re.sub(r"\{\{(.+?)\}\}", r"<code>\1</code>", text)

        # Links: [[[page-name]]] or [[[page-name | display text]]]
        text = re.sub(r"\[\[\[([^\]|]+)\|([^\]]+)\]\]\]", self._wiki_link, text)
        text = re.sub(r"\[\[\[([^\]]+)\]\]\]", self._wiki_link_simple, text)

        # External links: [url text]
        text = re.sub(r"\[(https?://[^\s\]]+)\s+([^\]]+)\]", r'<a href="\1" class="external">\2</a>', text)
        text = re.sub(r"\[(https?://[^\s\]]+)\]", r'<a href="\1" class="external">\1</a>', text)

        # Images
        text = self._parse_images(text)

        # Footnotes
        text = re.sub(r"\[\[footnote\]\](.+?)\[\[/footnote\]\]", self._add_footnote, text)

        # Span with CSS
        text = re.sub(r'\[\[span\s+([^\]]*)\]\](.+?)\[\[/span\]\]', self._parse_span, text)

        # Line break
        text = text.replace("_\n", "<br>")

        return text

    def _wiki_link(self, match):
        page = match.group(1).strip()
        display = match.group(2).strip()
        slug = page.lower().replace(" ", "-")
        return f'<a href="/{slug}">{display}</a>'

    def _wiki_link_simple(self, match):
        page = match.group(1).strip()
        slug = page.lower().replace(" ", "-")
        display = page.replace("-", " ").title()
        return f'<a href="/{slug}">{display}</a>'

    def _parse_images(self, text):
        def replace_image(m):
            attrs = m.group(1)
            src_match = re.search(r'source="([^"]+)"', attrs)
            if not src_match:
                parts = attrs.strip().split()
                if parts:
                    src = parts[0]
                else:
                    return m.group(0)
            else:
                src = src_match.group(1)

            css_classes = []
            if "f<" in attrs:
                css_classes.append("image-left")
            elif "f>" in attrs:
                css_classes.append("image-right")

            cls = f' class="{" ".join(css_classes)}"' if css_classes else ""
            return f'<img src="{src}"{cls} alt="">'

        text = re.sub(r"\[\[image\s+([^\]]+)\]\]", replace_image, text, flags=re.IGNORECASE)
        return text

    def _parse_span(self, match):
        attrs = match.group(1)
        content = match.group(2)
        style_match = re.search(r'style="([^"]+)"', attrs)
        class_match = re.search(r'class="([^"]+)"', attrs)
        parts = []
        if style_match:
            style_val = re.sub(r'(javascript|expression|url\s*\()', '', style_match.group(1), flags=re.IGNORECASE)
            parts.append(f'style="{html.escape(style_val, quote=True)}"')
        if class_match:
            class_val = re.sub(r'[^a-zA-Z0-9_ -]', '', class_match.group(1))
            parts.append(f'class="{class_val}"')
        attr_str = " " + " ".join(parts) if parts else ""
        return f"<span{attr_str}>{content}</span>"

    def _add_footnote(self, match):
        self.footnotes.append(html.escape(match.group(1)))
        idx = len(self.footnotes)
        return f'<sup class="footnoteref"><a href="#footnote-{idx}">{idx}</a></sup>'

    def _build_footnotes(self):
        items = []
        for i, note in enumerate(self.footnotes, 1):
            items.append(f'<li id="footnote-{i}">{note}</li>')
        return f'<div class="footnotes"><ol>{"".join(items)}</ol></div>'

    def _build_toc(self):
        if not self.toc_entries:
            return ""
        items = []
        for level, text, anchor in self.toc_entries:
            indent = "  " * (level - 1)
            items.append(f'{indent}<li><a href="#{anchor}">{text}</a></li>')
        return f'<div id="toc"><div class="toc-title">Table of Contents</div><ul>{"".join(items)}</ul></div>'

    def _parse_code_block(self, lines, start):
        attrs = lines[start].strip()
        lang_match = re.search(r'type="([^"]+)"', attrs)
        lang = lang_match.group(1) if lang_match else ""

        content_lines = []
        i = start + 1
        while i < len(lines) and lines[i].strip() != "[[/code]]":
            content_lines.append(lines[i])
            i += 1
        i += 1

        code = html.escape("\n".join(content_lines))
        lang_attr = f' class="language-{lang}"' if lang else ""
        return f"<pre><code{lang_attr}>{code}</code></pre>", i

    def _parse_module_block(self, lines, start):
        header = lines[start].strip()
        module_match = re.match(r"\[\[module\s+(\w+)(.*?)\]\]", header, re.IGNORECASE)
        module_name = module_match.group(1) if module_match else "Unknown"
        module_attrs_str = module_match.group(2).strip() if module_match else ""

        # Parse module params
        params = {}
        for m in re.finditer(r'(\w+)\s*=\s*"([^"]*)"', module_attrs_str):
            params[m.group(1)] = m.group(2)

        content_lines = []
        i = start + 1
        while i < len(lines) and not lines[i].strip().startswith("[[/module"):
            content_lines.append(lines[i])
            i += 1
        i += 1

        # Store body content as _body param
        if content_lines:
            params["_body"] = "\n".join(content_lines)

        # Try to render via module system
        from folia.wiki.modules import ModuleRegistry
        context = {"site": self.site, "page": self.page, "user": self.user}
        return ModuleRegistry.render(module_name, params, context), i

    def _parse_collapsible(self, lines, start):
        header = lines[start].strip()
        show_match = re.search(r'show="([^"]+)"', header)
        hide_match = re.search(r'hide="([^"]+)"', header)
        show_text = show_match.group(1) if show_match else "+ show block"
        hide_text = hide_match.group(1) if hide_match else "- hide block"

        content_lines = []
        i = start + 1
        while i < len(lines) and lines[i].strip() != "[[/collapsible]]":
            content_lines.append(lines[i])
            i += 1
        i += 1

        inner = self.render("\n".join(content_lines)) if content_lines else ""
        return (
            f'<div class="collapsible-block">'
            f'<div class="collapsible-block-folded"><a class="collapsible-block-link">{show_text}</a></div>'
            f'<div class="collapsible-block-unfolded" style="display:none">'
            f'<a class="collapsible-block-link">{hide_text}</a>'
            f'<div class="collapsible-block-content">{inner}</div></div></div>'
        ), i

    def _parse_div(self, lines, start):
        header = lines[start].strip()
        attrs_match = re.match(r"\[\[div\s*(.*?)\]\]", header, re.IGNORECASE)
        attrs_str = attrs_match.group(1) if attrs_match else ""

        style_match = re.search(r'style="([^"]+)"', attrs_str)
        class_match = re.search(r'class="([^"]+)"', attrs_str)
        id_match = re.search(r'id="([^"]+)"', attrs_str)

        parts = []
        if style_match:
            parts.append(f'style="{style_match.group(1)}"')
        if class_match:
            parts.append(f'class="{class_match.group(1)}"')
        if id_match:
            parts.append(f'id="{id_match.group(1)}"')
        attr_html = " " + " ".join(parts) if parts else ""

        content_lines = []
        i = start + 1
        while i < len(lines) and lines[i].strip() != "[[/div]]":
            content_lines.append(lines[i])
            i += 1
        i += 1

        inner = self.render("\n".join(content_lines)) if content_lines else ""
        return f"<div{attr_html}>{inner}</div>", i

    def _parse_tabview(self, lines, start):
        tabs = []
        current_tab = None
        current_content = []
        i = start + 1

        while i < len(lines) and lines[i].strip() != "[[/tabview]]":
            tab_match = re.match(r"\[\[tab\s+(.+?)\]\]", lines[i].strip())
            if tab_match:
                if current_tab:
                    tabs.append((current_tab, "\n".join(current_content)))
                current_tab = tab_match.group(1)
                current_content = []
            elif lines[i].strip() == "[[/tab]]":
                if current_tab:
                    tabs.append((current_tab, "\n".join(current_content)))
                    current_tab = None
                    current_content = []
            else:
                current_content.append(lines[i])
            i += 1
        i += 1

        if current_tab:
            tabs.append((current_tab, "\n".join(current_content)))

        tab_headers = []
        tab_bodies = []
        for idx, (name, content) in enumerate(tabs):
            active = " active" if idx == 0 else ""
            display = "" if idx == 0 else ' style="display:none"'
            tab_headers.append(f'<li class="tab-header{active}" data-tab="{idx}">{html.escape(name)}</li>')
            tab_bodies.append(f'<div class="tab-content{active}"{display}>{self.render(content)}</div>')

        return (
            f'<div class="yui-navset">'
            f'<ul class="yui-nav">{"".join(tab_headers)}</ul>'
            f'<div class="yui-content">{"".join(tab_bodies)}</div></div>'
        ), i

    def _parse_blockquote(self, lines, start):
        quote_lines = []
        i = start
        while i < len(lines) and lines[i].startswith(">"):
            quote_lines.append(lines[i][1:].lstrip() if len(lines[i]) > 1 else "")
            i += 1
        inner = self.render("\n".join(quote_lines))
        return f"<blockquote>{inner}</blockquote>", i

    def _parse_list(self, lines, start, list_type):
        marker = r"^\s*\*\s" if list_type == "ul" else r"^\s*#\s"
        items = []
        i = start
        while i < len(lines) and re.match(marker, lines[i]):
            item_text = re.sub(marker, "", lines[i]).strip()
            items.append(f"<li>{self._inline(item_text)}</li>")
            i += 1
        return f"<{list_type}>{''.join(items)}</{list_type}>", i

    def _parse_table(self, lines, start):
        rows = []
        i = start
        while i < len(lines) and lines[i].startswith("||"):
            cells = lines[i].split("||")[1:-1]
            row_cells = []
            for cell in cells:
                cell = cell.strip()
                if cell.startswith("~"):
                    row_cells.append(f"<th>{self._inline(cell[1:].strip())}</th>")
                else:
                    row_cells.append(f"<td>{self._inline(cell)}</td>")
            rows.append(f"<tr>{''.join(row_cells)}</tr>")
            i += 1
        return f'<table class="wiki-table">{"".join(rows)}</table>', i

    def _parse_paragraph(self, lines, start):
        para_lines = []
        i = start
        while i < len(lines) and lines[i].strip() and not self._is_block_start(lines[i]):
            para_lines.append(lines[i])
            i += 1
        return self._inline(" ".join(para_lines)), i

    def _is_block_start(self, line):
        if line.startswith("||"):
            return True
        if re.match(r"^(\+{1,6})\s", line):
            return True
        if line.startswith(">"):
            return True
        if re.match(r"^\s*[\*#]\s", line):
            return True
        if line.strip().startswith("[["):
            return True
        if line.strip().startswith("----"):
            return True
        return False
