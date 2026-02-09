# COHEZION: CLOUD RUN DOCKERFILE
# "The Ship that carries the Universe"

FROM python:3.11-slim

# 1. Setup Environment
WORKDIR /app
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# 2. Install System Dependencies (Rust/Cargo needed for FlumePhysics?)
# For the demo, we fall back to Python physics to minimize build complexity/time.
# If we need Rust, we would use a multi-stage build.
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 3. Install Python Dependencies
COPY pyproject.toml .
# Generate requirements.txt from pyproject or just install manually for now
# We assume uv or pip. Let's use pip for simplicity in Cloud Run standard image.
# We need to extract dependencies. For now, manual:
RUN pip install flask gunicorn numpy surrealdb cohezion-core-mock

# 4. Copy Codebase
COPY src/ src/

# 5. Entrypoint
# We run the Diplomat App (which spawns the UniverseSim thread)
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "cohezion.system.diplomat:app"]
