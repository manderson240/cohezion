"""GoogleSQL analysis operations for MCP tool integration."""

import json
import logging

from .googlesql_client import (
    GoogleSqlClient,
    GoogleSqlConfig,
)


logger = logging.getLogger(__name__)


class GoogleSqlOps:
    """High-level operations wrapping the GoogleSQL Analyzer client.

    Provides formatted, human-readable output suitable for MCP tool responses.
    """

    def __init__(self, config: GoogleSqlConfig | None = None):
        self.client = GoogleSqlClient(config)

    def is_available(self) -> bool:
        """Check if the GoogleSQL Analyzer service is reachable."""
        return self.client.health()

    def parse(self, sql: str) -> str:
        """Parse SQL and return AST information.

        Args:
            sql: SQL statement to parse.

        Returns:
            JSON string with parse results.
        """
        result = self.client.parse(sql)
        if not result.success:
            return json.dumps(
                {"success": False, "error": result.error},
                indent=2,
            )

        return json.dumps(
            {
                "success": True,
                "statement_type": result.statement_type,
                "ast": result.ast,
            },
            indent=2,
        )

    def analyze(
        self,
        sql: str,
        catalog_json: str = "",
    ) -> str:
        """Perform full semantic analysis of SQL.

        Args:
            sql: SQL statement to analyze.
            catalog_json: Optional JSON string defining the catalog
                context. Example: [{"name": "t", "columns": [...]}]

        Returns:
            JSON string with analysis results.
        """
        tables = None
        if catalog_json:
            try:
                tables = json.loads(catalog_json)
            except json.JSONDecodeError as e:
                return json.dumps(
                    {"success": False, "error": f"Invalid catalog JSON: {e}"},
                    indent=2,
                )

        result = self.client.analyze(sql, tables=tables)
        if not result.success:
            return json.dumps(
                {"success": False, "error": result.error},
                indent=2,
            )

        return json.dumps(
            {
                "success": True,
                "resolved_type": result.resolved_type,
                "referenced_tables": result.referenced_tables,
                "referenced_columns": result.referenced_columns,
                "resolved_ast": result.resolved_ast,
            },
            indent=2,
        )

    def validate(self, sql: str) -> str:
        """Validate SQL syntax.

        Args:
            sql: SQL statement to validate.

        Returns:
            JSON string with validation results.
        """
        result = self.client.validate(sql)
        output: dict = {"valid": result.valid}
        if result.issues:
            output["issues"] = result.issues
        return json.dumps(output, indent=2)

    def extract_tables(self, sql: str) -> str:
        """Extract table references from SQL.

        Args:
            sql: SQL statement to extract tables from.

        Returns:
            JSON string with extracted table names.
        """
        result = self.client.extract_tables(sql)
        if not result.success:
            return json.dumps(
                {"success": False, "error": result.error},
                indent=2,
            )

        return json.dumps(
            {"success": True, "tables": result.tables},
            indent=2,
        )

    def extract_columns(self, sql: str) -> str:
        """Extract column references from SQL.

        Args:
            sql: SQL statement to extract columns from.

        Returns:
            JSON string with extracted column names.
        """
        result = self.client.extract_columns(sql)
        if not result.success:
            return json.dumps(
                {"success": False, "error": result.error},
                indent=2,
            )

        return json.dumps(
            {"success": True, "columns": result.columns},
            indent=2,
        )

    def format_sql(self, sql: str) -> str:
        """Format a SQL statement.

        Args:
            sql: SQL statement to format.

        Returns:
            Formatted SQL string or JSON error.
        """
        result = self.client.format_sql(sql)
        if not result.success:
            return json.dumps(
                {"success": False, "error": result.error},
                indent=2,
            )

        return result.formatted or sql
