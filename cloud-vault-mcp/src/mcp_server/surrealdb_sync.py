"""SurrealDB synchronization layer for vault data.

Bidirectional sync between Obsidian vault files and SurrealDB graph database.
Supports real-time file watching and dimensional metadata.
"""

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
import yaml
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer


logger = logging.getLogger(__name__)


class SurrealDBSync:
    """Bidirectional sync between vault files and SurrealDB."""

    def __init__(
        self,
        vault_path: str,
        surrealdb_url: str = "http://localhost:8000",
        namespace: str = "cohezion",
        database: str = "vault",
        username: str = "root",
        password: str = "root",
    ):
        """Initialize SurrealDB sync.

        Args:
            vault_path: Path to Obsidian vault root
            surrealdb_url: SurrealDB HTTP endpoint
            namespace: SurrealDB namespace
            database: SurrealDB database name
            username: Auth username
            password: Auth password
        """
        self.vault_path = Path(vault_path).resolve()
        self.surrealdb_url = surrealdb_url.rstrip("/")
        self.namespace = namespace
        self.database = database
        self.auth = (username, password)
        self.client = httpx.Client(timeout=30.0)
        self.observer: Observer | None = None

        logger.info(
            f"Initialized SurrealDB sync: {vault_path} -> {surrealdb_url}/{namespace}/{database}"
        )

    def _execute_query(self, query: str) -> list[dict[str, Any]]:
        """Execute SurrealDB SQL query.

        Args:
            query: SurrealQL query string

        Returns:
            List of result objects from SurrealDB
        """
        headers = {
            "Content-Type": "text/plain",
            "Accept": "application/json",
            "NS": self.namespace,
            "DB": self.database,
        }

        response = self.client.post(
            f"{self.surrealdb_url}/sql",
            headers=headers,
            auth=self.auth,
            content=query,
        )
        response.raise_for_status()
        return response.json()

    def _parse_frontmatter(self, content: str) -> tuple[dict[str, Any], str]:
        """Extract YAML frontmatter and body from markdown.

        Args:
            content: Full markdown content

        Returns:
            Tuple of (frontmatter_dict, body_content)
        """
        if not content.startswith("---"):
            return {}, content

        # Match frontmatter block
        match = re.match(r"^---\n(.*?)\n---\n(.*)", content, re.DOTALL)
        if not match:
            return {}, content

        try:
            frontmatter = yaml.safe_load(match.group(1)) or {}
            body = match.group(2)
            return frontmatter, body
        except yaml.YAMLError:
            logger.warning("Failed to parse frontmatter, treating as plain markdown")
            return {}, content

    def _extract_wikilinks(self, content: str) -> list[str]:
        """Extract all [[wiki-links]] from content.

        Args:
            content: Markdown content

        Returns:
            List of wiki-link targets (without brackets)
        """
        return re.findall(r"\[\[([^\]]+)\]\]", content)

    def sync_paper(self, paper_path: Path) -> None:
        """Sync a single paper file to SurrealDB.

        Args:
            paper_path: Path to paper markdown file
        """
        if not paper_path.suffix == ".md":
            return

        try:
            content = paper_path.read_text(encoding="utf-8")
            frontmatter, body = self._parse_frontmatter(content)

            # Extract metadata
            relative_path = str(paper_path.relative_to(self.vault_path))
            title = frontmatter.get("title", paper_path.stem)
            tags = frontmatter.get("tags", [])
            date_str = frontmatter.get("date")

            # Parse date
            date_iso = None
            if date_str:
                try:
                    if isinstance(date_str, datetime):
                        date_iso = date_str.isoformat()
                    else:
                        # Try parsing common formats
                        dt = datetime.fromisoformat(str(date_str).replace("Z", "+00:00"))
                        date_iso = dt.isoformat()
                except (ValueError, AttributeError):
                    logger.warning(f"Could not parse date: {date_str}")

            # Extract wiki-links
            wikilinks = self._extract_wikilinks(content)

            # Build UPSERT query (insert or update)
            paper_id = relative_path.replace("/", "_").replace(".md", "")

            # Build date clause - use NONE for null, cast string to datetime
            if date_iso:
                date_clause = f"<datetime> {json.dumps(date_iso)}"
            else:
                date_clause = "NONE"

            # Truncate content to avoid huge queries
            content_truncated = body[:5000] if body else ""

            query = f"""
            USE NS {self.namespace};
            USE DB {self.database};

            -- Upsert: UPDATE if exists, CREATE if not (only set fields once in CREATE)
            UPDATE paper:{json.dumps(paper_id)} SET
                path = {json.dumps(relative_path)},
                title = {json.dumps(title)},
                tags = {json.dumps(tags)},
                content = {json.dumps(content_truncated)},
                date = {date_clause},
                updated_at = time::now()
            OR CREATE (
                path: {json.dumps(relative_path)},
                title: {json.dumps(title)},
                tags: {json.dumps(tags)},
                content: {json.dumps(content_truncated)},
                date: {date_clause}
            );
            """

            results = self._execute_query(query)
            logger.info(f"Synced paper: {relative_path}")

            # Sync wiki-links to concepts (create edges)
            self._sync_paper_links(paper_id, wikilinks)

        except Exception as e:
            logger.error(f"Failed to sync paper {paper_path}: {e}")

    def _sync_paper_links(self, paper_id: str, wikilinks: list[str]) -> None:
        """Create link relationships from paper to concepts.

        Args:
            paper_id: Paper record ID
            wikilinks: List of concept names
        """
        # Filter for concept links (typically in concepts/ directory)
        concept_links = [
            link for link in wikilinks if not link.startswith(("papers/", "patterns/", "decisions/"))
        ]

        if not concept_links:
            return

        # Delete existing links first (to handle removed links)
        delete_query = f"""
        USE NS {self.namespace};
        USE DB {self.database};
        DELETE links WHERE in = paper:{json.dumps(paper_id)};
        """
        self._execute_query(delete_query)

        # Create new links
        for concept_name in concept_links:
            concept_id = concept_name.replace("/", "_")
            link_query = f"""
            USE NS {self.namespace};
            USE DB {self.database};

            -- Create concept if doesn't exist
            UPDATE concept:{json.dumps(concept_id)} SET updated_at = time::now()
            OR CREATE (
                path: {json.dumps(f"concepts/{concept_name}.md")},
                title: {json.dumps(concept_name)},
                content: ""
            );

            -- Create link relationship (RELATE is idempotent)
            RELATE paper:{json.dumps(paper_id)}->links->concept:{json.dumps(concept_id)} SET
                strength = 1.0;
            """
            try:
                self._execute_query(link_query)
            except Exception as e:
                logger.warning(f"Failed to create link {paper_id} -> {concept_name}: {e}")

    def bulk_import_papers(self) -> int:
        """Import all papers from vault/papers/ directory.

        Returns:
            Count of papers imported
        """
        papers_dir = self.vault_path / "papers"
        if not papers_dir.exists():
            logger.warning(f"Papers directory not found: {papers_dir}")
            return 0

        paper_files = list(papers_dir.glob("*.md"))
        logger.info(f"Starting bulk import of {len(paper_files)} papers...")

        count = 0
        for paper_path in paper_files:
            try:
                self.sync_paper(paper_path)
                count += 1
            except Exception as e:
                logger.error(f"Failed to import {paper_path.name}: {e}")

        logger.info(f"Bulk import complete: {count}/{len(paper_files)} papers")
        return count

    def sync_concept(self, concept_path: Path) -> None:
        """Sync a single concept file to SurrealDB.

        Args:
            concept_path: Path to concept markdown file
        """
        if not concept_path.suffix == ".md":
            return

        try:
            content = concept_path.read_text(encoding="utf-8")
            frontmatter, body = self._parse_frontmatter(content)

            relative_path = str(concept_path.relative_to(self.vault_path))
            title = frontmatter.get("title", concept_path.stem)
            tags = frontmatter.get("tags", [])

            concept_id = concept_path.stem.replace("/", "_")

            # Truncate content to avoid huge queries
            content_truncated = body[:5000] if body else ""

            query = f"""
            USE NS {self.namespace};
            USE DB {self.database};

            UPDATE concept:{json.dumps(concept_id)} SET
                path = {json.dumps(relative_path)},
                title = {json.dumps(title)},
                tags = {json.dumps(tags)},
                content = {json.dumps(content_truncated)},
                updated_at = time::now()
            OR CREATE (
                path: {json.dumps(relative_path)},
                title: {json.dumps(title)},
                tags: {json.dumps(tags)},
                content: {json.dumps(content_truncated)}
            );
            """

            self._execute_query(query)
            logger.info(f"Synced concept: {relative_path}")

        except Exception as e:
            logger.error(f"Failed to sync concept {concept_path}: {e}")

    def bulk_import_concepts(self) -> int:
        """Import all concepts from vault/concepts/ directory.

        Returns:
            Count of concepts imported
        """
        concepts_dir = self.vault_path / "concepts"
        if not concepts_dir.exists():
            logger.warning(f"Concepts directory not found: {concepts_dir}")
            return 0

        concept_files = list(concepts_dir.glob("*.md"))
        logger.info(f"Starting bulk import of {len(concept_files)} concepts...")

        count = 0
        for concept_path in concept_files:
            try:
                self.sync_concept(concept_path)
                count += 1
            except Exception as e:
                logger.error(f"Failed to import {concept_path.name}: {e}")

        logger.info(f"Bulk import complete: {count}/{len(concept_files)} concepts")
        return count

    def start_watching(self) -> None:
        """Start watching vault for file changes (real-time sync)."""
        if self.observer is not None:
            logger.warning("File watcher already running")
            return

        event_handler = VaultFileHandler(self)
        self.observer = Observer()

        # Watch papers and concepts directories
        for subdir in ["papers", "concepts", "patterns", "decisions"]:
            watch_path = self.vault_path / subdir
            if watch_path.exists():
                self.observer.schedule(event_handler, str(watch_path), recursive=False)
                logger.info(f"Watching: {watch_path}")

        self.observer.start()
        logger.info("File watcher started")

    def stop_watching(self) -> None:
        """Stop watching vault for file changes."""
        if self.observer is not None:
            self.observer.stop()
            self.observer.join()
            self.observer = None
            logger.info("File watcher stopped")

    def close(self) -> None:
        """Clean up resources."""
        self.stop_watching()
        self.client.close()


class VaultFileHandler(FileSystemEventHandler):
    """Watchdog event handler for vault file changes."""

    def __init__(self, sync: SurrealDBSync):
        self.sync = sync

    def on_modified(self, event: FileSystemEvent) -> None:
        """Handle file modification events."""
        if event.is_directory or not event.src_path.endswith(".md"):
            return

        path = Path(event.src_path)

        # Determine file type and sync
        if "papers" in path.parts:
            self.sync.sync_paper(path)
        elif "concepts" in path.parts:
            self.sync.sync_concept(path)

    def on_created(self, event: FileSystemEvent) -> None:
        """Handle file creation events."""
        self.on_modified(event)  # Same logic as modification
