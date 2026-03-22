## GoogleSQL Analyzer Service
## Multi-stage build: compile Java service, then run in slim JRE container.

# ── Stage 1: Build ────────────────────────────────────────────────────
FROM gradle:8.12-jdk17 AS builder

WORKDIR /build
COPY service/ .
RUN gradle shadowJar --no-daemon

# ── Stage 2: Run ──────────────────────────────────────────────────────
FROM eclipse-temurin:17-jre-jammy

WORKDIR /app

# Copy the fat JAR from builder
COPY --from=builder /build/build/libs/googlesql-analyzer-0.1.0.jar app.jar

# Install curl for healthcheck (not included in eclipse-temurin JRE image)
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

# Non-root user
RUN useradd --create-home --shell /bin/bash analyzer
USER analyzer

ENV GOOGLESQL_PORT=8370

EXPOSE 8370

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -sf http://localhost:8370/health || exit 1

ENTRYPOINT ["java", "-jar", "app.jar"]
