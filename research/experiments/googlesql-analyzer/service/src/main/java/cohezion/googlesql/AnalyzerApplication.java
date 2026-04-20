package cohezion.googlesql;

import io.javalin.Javalin;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * GoogleSQL Analyzer REST service.
 *
 * Exposes GoogleSQL parsing, analysis, and validation capabilities
 * via a lightweight HTTP API for consumption by Cohezion's MCP server.
 */
public class AnalyzerApplication {

    private static final Logger log = LoggerFactory.getLogger(AnalyzerApplication.class);

    public static void main(String[] args) {
        int port = Integer.parseInt(System.getenv().getOrDefault("GOOGLESQL_PORT", "8370"));
        AnalyzerService analyzer = new AnalyzerService();

        Javalin app = Javalin.create(config -> {
            config.showJavalinBanner = false;
        }).start(port);

        // Health check
        app.get("/health", ctx -> ctx.json(new StatusResponse("ok", "googlesql-analyzer")));

        // Parse SQL into AST
        app.post("/parse", ctx -> {
            SqlRequest req = ctx.bodyAsClass(SqlRequest.class);
            ctx.json(analyzer.parse(req));
        });

        // Analyze SQL with full semantic analysis
        app.post("/analyze", ctx -> {
            AnalyzeRequest req = ctx.bodyAsClass(AnalyzeRequest.class);
            ctx.json(analyzer.analyze(req));
        });

        // Validate SQL syntax
        app.post("/validate", ctx -> {
            SqlRequest req = ctx.bodyAsClass(SqlRequest.class);
            ctx.json(analyzer.validate(req));
        });

        // Extract table references from SQL
        app.post("/extract-tables", ctx -> {
            SqlRequest req = ctx.bodyAsClass(SqlRequest.class);
            ctx.json(analyzer.extractTables(req));
        });

        // Extract column references from SQL
        app.post("/extract-columns", ctx -> {
            SqlRequest req = ctx.bodyAsClass(SqlRequest.class);
            ctx.json(analyzer.extractColumns(req));
        });

        // Format SQL
        app.post("/format", ctx -> {
            SqlRequest req = ctx.bodyAsClass(SqlRequest.class);
            ctx.json(analyzer.format(req));
        });

        log.info("GoogleSQL Analyzer service started on port {}", port);
    }
}
