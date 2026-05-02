"""HTTP client for the GoogleSQL Analyzer service."""

import json
import logging
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any


logger = logging.getLogger(__name__)


@dataclass
class GoogleSqlConfig:
    """Configuration for the GoogleSQL Analyzer service connection."""

    base_url: str = "http://localhost:8370"
    timeout: int = 30


@dataclass
class ParseResult:
    success: bool
    error: str | None = None
    statement_type: str | None = None
    ast: str | None = None


@dataclass
class AnalyzeResult:
    success: bool
    error: str | None = None
    resolved_type: str | None = None
    resolved_ast: str | None = None
    referenced_tables: list[str] = field(default_factory=list)
    referenced_columns: list[str] = field(default_factory=list)


@dataclass
class ValidationResult:
    valid: bool
    issues: list[dict] = field(default_factory=list)


@dataclass
class TableExtractionResult:
    success: bool
    error: str | None = None
    tables: list[str] = field(default_factory=list)


@dataclass
class ColumnExtractionResult:
    success: bool
    error: str | None = None
    columns: list[str] = field(default_factory=list)


@dataclass
class FormatResult:
    success: bool
    error: str | None = None
    formatted: str | None = None


class GoogleSqlClient:
    """Client for the GoogleSQL Analyzer REST service.

    Uses stdlib urllib to avoid adding external HTTP dependencies.
    """

    def __init__(self, config: GoogleSqlConfig | None = None):
        self.config = config or GoogleSqlConfig()
        self._base = self.config.base_url.rstrip("/")

    def _post(self, path: str, payload: dict) -> dict:
        """Send a POST request to the analyzer service."""
        url = f"{self._base}{path}"
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.config.timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.URLError as e:
            logger.error("GoogleSQL service request failed: %s", e)
            raise ConnectionError(
                f"GoogleSQL Analyzer service unavailable at {self._base}: {e}"
            ) from e

    def _get(self, path: str) -> dict:
        """Send a GET request to the analyzer service."""
        url = f"{self._base}{path}"
        req = urllib.request.Request(url, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=self.config.timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.URLError as e:
            logger.error("GoogleSQL service request failed: %s", e)
            raise ConnectionError(
                f"GoogleSQL Analyzer service unavailable at {self._base}: {e}"
            ) from e

    def health(self) -> bool:
        """Check if the GoogleSQL Analyzer service is healthy."""
        try:
            result = self._get("/health")
            return result.get("status") == "ok"
        except ConnectionError:
            return False

    def parse(self, sql: str) -> ParseResult:
        """Parse SQL into an AST representation."""
        result = self._post("/parse", {"sql": sql})
        return ParseResult(
            success=result.get("success", False),
            error=result.get("error"),
            statement_type=result.get("statementType"),
            ast=result.get("ast"),
        )

    def analyze(
        self,
        sql: str,
        tables: list[dict] | None = None,
    ) -> AnalyzeResult:
        """Perform full semantic analysis of SQL.

        Args:
            sql: The SQL statement to analyze.
            tables: Optional catalog context as a list of table specs:
                    [{"name": "users", "columns": [{"name": "id", "type": "INT64"}]}]
        """
        payload: dict[str, Any] = {"sql": sql}
        if tables:
            payload["catalog"] = {"tables": tables}

        result = self._post("/analyze", payload)
        return AnalyzeResult(
            success=result.get("success", False),
            error=result.get("error"),
            resolved_type=result.get("resolvedType"),
            resolved_ast=result.get("resolvedAst"),
            referenced_tables=result.get("referencedTables") or [],
            referenced_columns=result.get("referencedColumns") or [],
        )

    def validate(self, sql: str) -> ValidationResult:
        """Validate SQL syntax."""
        result = self._post("/validate", {"sql": sql})
        return ValidationResult(
            valid=result.get("valid", False),
            issues=result.get("issues", []),
        )

    def extract_tables(self, sql: str) -> TableExtractionResult:
        """Extract table references from SQL."""
        result = self._post("/extract-tables", {"sql": sql})
        return TableExtractionResult(
            success=result.get("success", False),
            error=result.get("error"),
            tables=result.get("tables", []),
        )

    def extract_columns(self, sql: str) -> ColumnExtractionResult:
        """Extract column references from SQL."""
        result = self._post("/extract-columns", {"sql": sql})
        return ColumnExtractionResult(
            success=result.get("success", False),
            error=result.get("error"),
            columns=result.get("columns", []),
        )

    def format_sql(self, sql: str) -> FormatResult:
        """Format a SQL statement."""
        result = self._post("/format", {"sql": sql})
        return FormatResult(
            success=result.get("success", False),
            error=result.get("error"),
            formatted=result.get("formatted"),
        )
