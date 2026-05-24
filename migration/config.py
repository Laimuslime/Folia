from dataclasses import dataclass, field
from typing import Optional


@dataclass
class MigrationConfig:
    source_site: Optional[str] = None
    source_file: Optional[str] = None
    api_key: Optional[str] = None
    target_url: str = "http://localhost:8000"
    target_token: Optional[str] = None
    target_site_slug: Optional[str] = None
    include_forum: bool = False
    include_files: bool = False
    workers: int = 4
    verbose: bool = False
    batch_size: int = 50
    retry_count: int = 3
    retry_delay: float = 1.0
