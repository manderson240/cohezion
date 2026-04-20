package cohezion.googlesql;

import java.util.List;

// ── Request Models ───────────────────────────────────────────────────

/** Basic SQL request with a single statement. */
class SqlRequest {
    public String sql;
}

/** Analysis request with optional catalog context for semantic analysis. */
class AnalyzeRequest {
    public String sql;
    public CatalogSpec catalog;
}

/** Catalog specification for semantic analysis. */
class CatalogSpec {
    public List<TableSpec> tables;
}

/** Table definition for catalog. */
class TableSpec {
    public String name;
    public List<ColumnSpec> columns;
}

/** Column definition for table. */
class ColumnSpec {
    public String name;
    public String type;
}

// ── Response Models ──────────────────────────────────────────────────

/** Generic status response. */
class StatusResponse {
    public String status;
    public String service;

    StatusResponse(String status, String service) {
        this.status = status;
        this.service = service;
    }
}

/** Parse response with AST information. */
class ParseResponse {
    public boolean success;
    public String error;
    public String statementType;
    public String ast;

    ParseResponse(boolean success, String error, String statementType, String ast) {
        this.success = success;
        this.error = error;
        this.statementType = statementType;
        this.ast = ast;
    }
}

/** Full analysis response with resolved AST and references. */
class AnalyzeResponse {
    public boolean success;
    public String error;
    public String resolvedType;
    public String resolvedAst;
    public List<String> referencedTables;
    public List<String> referencedColumns;

    AnalyzeResponse(
            boolean success,
            String error,
            String resolvedType,
            String resolvedAst,
            List<String> referencedTables,
            List<String> referencedColumns) {
        this.success = success;
        this.error = error;
        this.resolvedType = resolvedType;
        this.resolvedAst = resolvedAst;
        this.referencedTables = referencedTables;
        this.referencedColumns = referencedColumns;
    }
}

/** Validation response with issues list. */
class ValidationResponse {
    public boolean valid;
    public List<ValidationIssue> issues;

    ValidationResponse(boolean valid, List<ValidationIssue> issues) {
        this.valid = valid;
        this.issues = issues;
    }
}

/** A single validation issue. */
class ValidationIssue {
    public String severity;
    public String category;
    public String message;

    ValidationIssue(String severity, String category, String message) {
        this.severity = severity;
        this.category = category;
        this.message = message;
    }
}

/** Table extraction response. */
class TableExtractionResponse {
    public boolean success;
    public String error;
    public List<String> tables;

    TableExtractionResponse(boolean success, String error, List<String> tables) {
        this.success = success;
        this.error = error;
        this.tables = tables;
    }
}

/** Column extraction response. */
class ColumnExtractionResponse {
    public boolean success;
    public String error;
    public List<String> columns;

    ColumnExtractionResponse(boolean success, String error, List<String> columns) {
        this.success = success;
        this.error = error;
        this.columns = columns;
    }
}

/** Format response. */
class FormatResponse {
    public boolean success;
    public String error;
    public String formatted;

    FormatResponse(boolean success, String error, String formatted) {
        this.success = success;
        this.error = error;
        this.formatted = formatted;
    }
}
