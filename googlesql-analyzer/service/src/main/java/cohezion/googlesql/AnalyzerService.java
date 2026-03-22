package cohezion.googlesql;

import com.google.zetasql.AnalyzerOptions;
import com.google.zetasql.LanguageOptions;
import com.google.zetasql.Parser;
import com.google.zetasql.SimpleCatalog;
import com.google.zetasql.SimpleColumn;
import com.google.zetasql.SimpleTable;
import com.google.zetasql.SqlFormatter;
import com.google.zetasql.TypeFactory;
import com.google.zetasql.ZetaSQLType.TypeKind;
import com.google.zetasql.parser.ASTNodes.ASTStatement;
import com.google.zetasql.resolvedast.ResolvedNodes.ResolvedStatement;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Core GoogleSQL analysis logic wrapping the ZetaSQL Java API.
 */
public class AnalyzerService {

    private static final Logger log = LoggerFactory.getLogger(AnalyzerService.class);

    private final LanguageOptions languageOptions;

    public AnalyzerService() {
        this.languageOptions = new LanguageOptions();
        languageOptions.enableMaximumLanguageFeatures();
        log.info("GoogleSQL AnalyzerService initialized with maximum language features");
    }

    /**
     * Parse SQL into an AST representation.
     */
    public ParseResponse parse(SqlRequest request) {
        try {
            ASTStatement stmt = Parser.parseStatement(
                request.sql, languageOptions);

            return new ParseResponse(
                true,
                null,
                stmt.getClass().getSimpleName(),
                stmt.debugString()
            );
        } catch (Exception e) {
            return new ParseResponse(false, e.getMessage(), null, null);
        }
    }

    /**
     * Full semantic analysis of SQL with catalog context.
     */
    public AnalyzeResponse analyze(AnalyzeRequest request) {
        try {
            SimpleCatalog catalog = buildCatalog(request.catalog);
            AnalyzerOptions options = new AnalyzerOptions();
            options.setLanguageOptions(languageOptions);

            ResolvedStatement resolved = com.google.zetasql.Analyzer.analyzeStatement(
                request.sql, options, catalog);

            List<String> referencedTables = new ArrayList<>();
            List<String> referencedColumns = new ArrayList<>();
            extractReferences(resolved, referencedTables, referencedColumns);

            return new AnalyzeResponse(
                true,
                null,
                resolved.getClass().getSimpleName(),
                resolved.debugString(),
                referencedTables,
                referencedColumns
            );
        } catch (Exception e) {
            return new AnalyzeResponse(false, e.getMessage(), null, null, null, null);
        }
    }

    /**
     * Validate SQL syntax without full semantic analysis.
     */
    public ValidationResponse validate(SqlRequest request) {
        List<ValidationIssue> issues = new ArrayList<>();
        boolean valid = true;

        try {
            Parser.parseStatement(request.sql, languageOptions);
        } catch (Exception e) {
            valid = false;
            issues.add(new ValidationIssue("error", "syntax", e.getMessage()));
        }

        return new ValidationResponse(valid, issues);
    }

    /**
     * Extract table references from SQL.
     */
    public TableExtractionResponse extractTables(SqlRequest request) {
        try {
            ASTStatement stmt = Parser.parseStatement(
                request.sql, languageOptions);
            List<String> tables = extractTableNames(stmt);
            return new TableExtractionResponse(true, null, tables);
        } catch (Exception e) {
            return new TableExtractionResponse(false, e.getMessage(), null);
        }
    }

    /**
     * Extract column references from SQL.
     */
    public ColumnExtractionResponse extractColumns(SqlRequest request) {
        try {
            ASTStatement stmt = Parser.parseStatement(
                request.sql, languageOptions);
            List<String> columns = extractColumnNames(stmt);
            return new ColumnExtractionResponse(true, null, columns);
        } catch (Exception e) {
            return new ColumnExtractionResponse(false, e.getMessage(), null);
        }
    }

    /**
     * Format SQL statement.
     */
    public FormatResponse format(SqlRequest request) {
        try {
            String formatted = SqlFormatter.formatSql(request.sql);
            return new FormatResponse(true, null, formatted);
        } catch (Exception e) {
            return new FormatResponse(false, e.getMessage(), null);
        }
    }

    /**
     * Build a SimpleCatalog from the request's catalog specification.
     */
    private SimpleCatalog buildCatalog(CatalogSpec spec) {
        SimpleCatalog catalog = new SimpleCatalog("cohezion_catalog");

        if (spec != null && spec.tables != null) {
            for (TableSpec tableSpec : spec.tables) {
                SimpleTable table = new SimpleTable(tableSpec.name);
                if (tableSpec.columns != null) {
                    for (ColumnSpec colSpec : tableSpec.columns) {
                        TypeKind typeKind = mapTypeKind(colSpec.type);
                        table.addSimpleColumn(
                            colSpec.name,
                            TypeFactory.createSimpleType(typeKind)
                        );
                    }
                }
                catalog.addSimpleTable(table);
            }
        }

        // Add built-in functions for analysis
        catalog.addZetaSQLFunctions(new AnalyzerOptions());

        return catalog;
    }

    private TypeKind mapTypeKind(String typeName) {
        if (typeName == null) return TypeKind.TYPE_STRING;
        switch (typeName.toUpperCase()) {
            case "INT64":
            case "INTEGER":
            case "BIGINT":
                return TypeKind.TYPE_INT64;
            case "INT32":
            case "INT":
                return TypeKind.TYPE_INT32;
            case "FLOAT64":
            case "DOUBLE":
            case "FLOAT":
                return TypeKind.TYPE_DOUBLE;
            case "BOOL":
            case "BOOLEAN":
                return TypeKind.TYPE_BOOL;
            case "STRING":
            case "TEXT":
            case "VARCHAR":
                return TypeKind.TYPE_STRING;
            case "BYTES":
            case "BYTEA":
                return TypeKind.TYPE_BYTES;
            case "DATE":
                return TypeKind.TYPE_DATE;
            case "TIMESTAMP":
            case "TIMESTAMPTZ":
                return TypeKind.TYPE_TIMESTAMP;
            case "JSON":
            case "JSONB":
                return TypeKind.TYPE_JSON;
            case "NUMERIC":
            case "DECIMAL":
                return TypeKind.TYPE_NUMERIC;
            case "UUID":
                return TypeKind.TYPE_STRING; // Map UUID to STRING
            default:
                return TypeKind.TYPE_STRING;
        }
    }

    private List<String> extractTableNames(ASTStatement stmt) {
        List<String> tables = new ArrayList<>();
        extractTableNamesFromDebug(stmt.debugString(), tables);
        return tables;
    }

    private List<String> extractColumnNames(ASTStatement stmt) {
        List<String> columns = new ArrayList<>();
        extractColumnNamesFromDebug(stmt.debugString(), columns);
        return columns;
    }

    private void extractReferences(
            ResolvedStatement stmt,
            List<String> tables,
            List<String> columns) {
        String debug = stmt.debugString();
        extractTableNamesFromDebug(debug, tables);
        extractColumnNamesFromDebug(debug, columns);
    }

    private void extractTableNamesFromDebug(String debug, List<String> tables) {
        // Parse table references from the AST debug string
        for (String line : debug.split("\n")) {
            String trimmed = line.trim();
            if (trimmed.startsWith("TablePathExpression") ||
                trimmed.contains("table=")) {
                String name = trimmed.replaceAll(".*\\b(\\w+\\.?\\w+)\\s*$", "$1");
                if (!name.isEmpty() && !tables.contains(name)) {
                    tables.add(name);
                }
            }
        }
    }

    private void extractColumnNamesFromDebug(String debug, List<String> columns) {
        // Parse column references from the AST debug string
        for (String line : debug.split("\n")) {
            String trimmed = line.trim();
            if (trimmed.startsWith("Identifier") ||
                trimmed.contains("column=")) {
                String name = trimmed.replaceAll(".*\\b(\\w+)\\s*$", "$1");
                if (!name.isEmpty() && !columns.contains(name)) {
                    columns.add(name);
                }
            }
        }
    }
}
