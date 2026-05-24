"""
Folia Migration Tool — Migrate from Wikidot to Folia.

Supports:
- Wikidot XML-RPC API scraping
- Wikidot backup file (XML) import
- Web scraping fallback for data not available via API
"""
import click
from .config import MigrationConfig


@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.pass_context
def cli(ctx, verbose):
    """Folia Migration Tool — Migrate Wikidot sites to Folia."""
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose


@cli.command()
@click.option("--site", required=True, help="Wikidot site slug (e.g., scp-wiki)")
@click.option("--api-key", required=True, help="Wikidot API key")
@click.option("--target", default="http://localhost:8000", help="Folia API URL")
@click.option("--target-token", help="Folia API auth token")
@click.option("--include-forum", is_flag=True, help="Also migrate forum posts")
@click.option("--include-files", is_flag=True, help="Also download and migrate files")
@click.option("--workers", default=4, help="Number of concurrent workers")
@click.pass_context
def api(ctx, site, api_key, target, target_token, include_forum, include_files, workers):
    """Migrate a site using the Wikidot XML-RPC API."""
    from .wikidot_api.client import WikidotApiClient
    from .importer.bulk import BulkImporter

    config = MigrationConfig(
        source_site=site,
        api_key=api_key,
        target_url=target,
        target_token=target_token,
        include_forum=include_forum,
        include_files=include_files,
        workers=workers,
        verbose=ctx.obj["verbose"],
    )

    click.echo(f"Starting API migration from Wikidot site: {site}")
    client = WikidotApiClient(config)
    data = client.export_all()

    click.echo(f"Exported {len(data['pages'])} pages, {len(data.get('files', []))} files")

    importer = BulkImporter(config)
    result = importer.import_data(data)

    click.echo(f"Migration complete: {result['pages_imported']} pages imported, {result['errors']} errors")


@cli.command()
@click.option("--file", "backup_file", required=True, type=click.Path(exists=True), help="Path to Wikidot backup XML file")
@click.option("--target", default="http://localhost:8000", help="Folia API URL")
@click.option("--target-token", help="Folia API auth token")
@click.option("--site-slug", help="Target site slug in Folia")
@click.pass_context
def backup(ctx, backup_file, target, target_token, site_slug):
    """Import from a Wikidot backup XML file."""
    from .backup_parser.xml_parser import WikidotBackupParser
    from .importer.bulk import BulkImporter

    config = MigrationConfig(
        source_file=backup_file,
        target_url=target,
        target_token=target_token,
        target_site_slug=site_slug,
        verbose=ctx.obj["verbose"],
    )

    click.echo(f"Parsing backup file: {backup_file}")
    parser = WikidotBackupParser(config)
    data = parser.parse()

    click.echo(f"Found {len(data['pages'])} pages in backup")

    importer = BulkImporter(config)
    result = importer.import_data(data)

    click.echo(f"Import complete: {result['pages_imported']} pages imported, {result['errors']} errors")


@cli.command()
@click.option("--site", required=True, help="Site slug to verify")
@click.option("--target", default="http://localhost:8000", help="Folia API URL")
@click.option("--target-token", help="Folia API auth token")
@click.option("--source-site", help="Original Wikidot site slug for comparison")
@click.option("--api-key", help="Wikidot API key for comparison")
@click.pass_context
def verify(ctx, site, target, target_token, source_site, api_key):
    """Verify migration results by comparing source and target."""
    from .importer.validator import MigrationValidator

    config = MigrationConfig(
        source_site=source_site,
        api_key=api_key,
        target_url=target,
        target_token=target_token,
        target_site_slug=site,
        verbose=ctx.obj["verbose"],
    )

    validator = MigrationValidator(config)
    report = validator.validate()

    click.echo("\n=== Migration Verification Report ===")
    click.echo(f"Pages in target: {report['target_pages']}")
    click.echo(f"Pages with content: {report['pages_with_content']}")
    click.echo(f"Empty pages: {report['empty_pages']}")
    if report.get("source_pages"):
        click.echo(f"Pages in source: {report['source_pages']}")
        click.echo(f"Missing pages: {report['missing_pages']}")
    click.echo(f"Status: {'PASS' if report['status'] == 'ok' else 'ISSUES FOUND'}")


def main():
    cli()


if __name__ == "__main__":
    main()
