"""Tests for the GoogleSQL client and operations layer.

These tests mock the HTTP calls to the GoogleSQL Analyzer service,
so they run without requiring the Java service to be running.
"""

import json
from unittest.mock import patch

import pytest

from mcp_server.googlesql_client import (
    AnalyzeResult,
    ColumnExtractionResult,
    FormatResult,
    GoogleSqlClient,
    GoogleSqlConfig,
    ParseResult,
    TableExtractionResult,
    ValidationResult,
)
from mcp_server.googlesql_ops import GoogleSqlOps


# ── Client Unit Tests ─────────────────────────────────────────────────


class TestGoogleSqlClientHealth:
    def test_healthy_service(self):
        client = GoogleSqlClient(GoogleSqlConfig(base_url="http://fake:8370"))
        with patch.object(client, "_get", return_value={"status": "ok"}):
            assert client.health() is True

    def test_unhealthy_service(self):
        client = GoogleSqlClient(GoogleSqlConfig(base_url="http://fake:8370"))
        with patch.object(client, "_get", side_effect=ConnectionError("down")):
            assert client.health() is False


class TestGoogleSqlClientParse:
    def test_parse_success(self):
        client = GoogleSqlClient(GoogleSqlConfig(base_url="http://fake:8370"))
        mock_response = {
            "success": True,
            "statementType": "ASTQueryStatement",
            "ast": "QueryStatement\n  Select\n    ...",
        }
        with patch.object(client, "_post", return_value=mock_response):
            result = client.parse("SELECT 1")
            assert result.success is True
            assert result.statement_type == "ASTQueryStatement"
            assert result.ast is not None

    def test_parse_failure(self):
        client = GoogleSqlClient(GoogleSqlConfig(base_url="http://fake:8370"))
        mock_response = {
            "success": False,
            "error": "Syntax error at position 7",
        }
        with patch.object(client, "_post", return_value=mock_response):
            result = client.parse("SELEC 1")
            assert result.success is False
            assert "Syntax error" in result.error


class TestGoogleSqlClientValidate:
    def test_valid_sql(self):
        client = GoogleSqlClient(GoogleSqlConfig(base_url="http://fake:8370"))
        mock_response = {"valid": True, "issues": []}
        with patch.object(client, "_post", return_value=mock_response):
            result = client.validate("SELECT * FROM users")
            assert result.valid is True
            assert result.issues == []

    def test_invalid_sql(self):
        client = GoogleSqlClient(GoogleSqlConfig(base_url="http://fake:8370"))
        mock_response = {
            "valid": False,
            "issues": [
                {
                    "severity": "error",
                    "category": "syntax",
                    "message": "Expected keyword SELECT",
                }
            ],
        }
        with patch.object(client, "_post", return_value=mock_response):
            result = client.validate("INVALID SQL")
            assert result.valid is False
            assert len(result.issues) == 1
            assert result.issues[0]["severity"] == "error"


class TestGoogleSqlClientAnalyze:
    def test_analyze_with_catalog(self):
        client = GoogleSqlClient(GoogleSqlConfig(base_url="http://fake:8370"))
        mock_response = {
            "success": True,
            "resolvedType": "ResolvedQueryStmt",
            "resolvedAst": "QueryStmt\n  ...",
            "referencedTables": ["users"],
            "referencedColumns": ["id", "email"],
        }
        with patch.object(client, "_post", return_value=mock_response) as mock_post:
            tables = [
                {
                    "name": "users",
                    "columns": [
                        {"name": "id", "type": "INT64"},
                        {"name": "email", "type": "STRING"},
                    ],
                }
            ]
            result = client.analyze("SELECT id, email FROM users", tables=tables)
            assert result.success is True
            assert result.resolved_type == "ResolvedQueryStmt"
            assert "users" in result.referenced_tables
            assert "id" in result.referenced_columns

            # Verify catalog was sent
            call_payload = mock_post.call_args[0][1]
            assert "catalog" in call_payload

    def test_analyze_without_catalog(self):
        client = GoogleSqlClient(GoogleSqlConfig(base_url="http://fake:8370"))
        mock_response = {
            "success": False,
            "error": "Table not found: users",
        }
        with patch.object(client, "_post", return_value=mock_response) as mock_post:
            result = client.analyze("SELECT id FROM users")
            assert result.success is False

            # Verify no catalog was sent
            call_payload = mock_post.call_args[0][1]
            assert "catalog" not in call_payload


class TestGoogleSqlClientExtractTables:
    def test_extract_tables(self):
        client = GoogleSqlClient(GoogleSqlConfig(base_url="http://fake:8370"))
        mock_response = {
            "success": True,
            "tables": ["users", "orders"],
        }
        with patch.object(client, "_post", return_value=mock_response):
            result = client.extract_tables(
                "SELECT * FROM users JOIN orders ON users.id = orders.user_id"
            )
            assert result.success is True
            assert "users" in result.tables
            assert "orders" in result.tables


class TestGoogleSqlClientExtractColumns:
    def test_extract_columns(self):
        client = GoogleSqlClient(GoogleSqlConfig(base_url="http://fake:8370"))
        mock_response = {
            "success": True,
            "columns": ["id", "email", "name"],
        }
        with patch.object(client, "_post", return_value=mock_response):
            result = client.extract_columns("SELECT id, email, name FROM users")
            assert result.success is True
            assert len(result.columns) == 3


class TestGoogleSqlClientFormat:
    def test_format_sql(self):
        client = GoogleSqlClient(GoogleSqlConfig(base_url="http://fake:8370"))
        mock_response = {
            "success": True,
            "formatted": "SELECT\n  id,\n  email\nFROM\n  users",
        }
        with patch.object(client, "_post", return_value=mock_response):
            result = client.format_sql("SELECT id, email FROM users")
            assert result.success is True
            assert "SELECT" in result.formatted


class TestGoogleSqlClientConnectionError:
    def test_service_unavailable(self):
        client = GoogleSqlClient(GoogleSqlConfig(base_url="http://fake:8370"))
        with pytest.raises(ConnectionError, match="unavailable"):
            client.parse("SELECT 1")


# ── Operations Layer Tests ────────────────────────────────────────────


class TestGoogleSqlOps:
    @pytest.fixture
    def ops(self):
        config = GoogleSqlConfig(base_url="http://fake:8370")
        return GoogleSqlOps(config)

    def test_parse_returns_json(self, ops):
        mock_result = ParseResult(
            success=True,
            statement_type="ASTQueryStatement",
            ast="QueryStatement...",
        )
        with patch.object(ops.client, "parse", return_value=mock_result):
            result = ops.parse("SELECT 1")
            parsed = json.loads(result)
            assert parsed["success"] is True
            assert parsed["statement_type"] == "ASTQueryStatement"

    def test_parse_error_returns_json(self, ops):
        mock_result = ParseResult(success=False, error="Syntax error")
        with patch.object(ops.client, "parse", return_value=mock_result):
            result = ops.parse("BAD SQL")
            parsed = json.loads(result)
            assert parsed["success"] is False
            assert "Syntax error" in parsed["error"]

    def test_validate_returns_json(self, ops):
        mock_result = ValidationResult(valid=True, issues=[])
        with patch.object(ops.client, "validate", return_value=mock_result):
            result = ops.validate("SELECT 1")
            parsed = json.loads(result)
            assert parsed["valid"] is True

    def test_analyze_with_catalog_json(self, ops):
        mock_result = AnalyzeResult(
            success=True,
            resolved_type="ResolvedQueryStmt",
            resolved_ast="...",
            referenced_tables=["users"],
            referenced_columns=["id"],
        )
        with patch.object(ops.client, "analyze", return_value=mock_result):
            catalog = json.dumps(
                [{"name": "users", "columns": [{"name": "id", "type": "INT64"}]}]
            )
            result = ops.analyze("SELECT id FROM users", catalog_json=catalog)
            parsed = json.loads(result)
            assert parsed["success"] is True
            assert "users" in parsed["referenced_tables"]

    def test_analyze_bad_catalog_json(self, ops):
        result = ops.analyze("SELECT 1", catalog_json="not valid json")
        parsed = json.loads(result)
        assert parsed["success"] is False
        assert "Invalid catalog JSON" in parsed["error"]

    def test_extract_tables_returns_json(self, ops):
        mock_result = TableExtractionResult(success=True, tables=["users", "orders"])
        with patch.object(ops.client, "extract_tables", return_value=mock_result):
            result = ops.extract_tables("SELECT * FROM users, orders")
            parsed = json.loads(result)
            assert parsed["success"] is True
            assert len(parsed["tables"]) == 2

    def test_extract_columns_returns_json(self, ops):
        mock_result = ColumnExtractionResult(success=True, columns=["id", "name"])
        with patch.object(ops.client, "extract_columns", return_value=mock_result):
            result = ops.extract_columns("SELECT id, name FROM users")
            parsed = json.loads(result)
            assert parsed["success"] is True
            assert len(parsed["columns"]) == 2

    def test_format_sql_returns_formatted(self, ops):
        mock_result = FormatResult(
            success=True,
            formatted="SELECT\n  id\nFROM\n  users",
        )
        with patch.object(ops.client, "format_sql", return_value=mock_result):
            result = ops.format_sql("SELECT id FROM users")
            assert "SELECT" in result
            assert "FROM" in result

    def test_format_sql_error_returns_json(self, ops):
        mock_result = FormatResult(success=False, error="Cannot format")
        with patch.object(ops.client, "format_sql", return_value=mock_result):
            result = ops.format_sql("BAD")
            parsed = json.loads(result)
            assert parsed["success"] is False

    def test_is_available_true(self, ops):
        with patch.object(ops.client, "health", return_value=True):
            assert ops.is_available() is True

    def test_is_available_false(self, ops):
        with patch.object(ops.client, "health", return_value=False):
            assert ops.is_available() is False
