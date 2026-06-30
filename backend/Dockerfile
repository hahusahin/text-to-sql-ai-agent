# Runtime image for the FastAPI AI service, built for a Hugging Face Spaces
# Docker SDK Space. HF routes external traffic to the container's port 7860, so
# the app must listen on 0.0.0.0:7860.

FROM python:3.13-slim

# POETRY_VIRTUALENVS_CREATE=false: install deps straight into the image's system
# site-packages. The container is already an isolated environment; a venv inside
# it would only add a layer of indirection.
ENV POETRY_VIRTUALENVS_CREATE=false \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN pip install --no-cache-dir "poetry>=2.0,<3.0"

WORKDIR /app

# Copy only the dependency manifests first. Docker caches this layer and re-runs
# the install only when deps change — not on every code edit (which would be slow).
COPY pyproject.toml poetry.lock ./
RUN poetry install --only main --no-cache

# Only the runtime package ships. Migrations, seed, and eval are dev-time tooling
# and deliberately left out of the production image.
COPY app ./app

# Run as a non-root user (HF Spaces convention; smaller blast radius if the
# process is ever compromised).
RUN useradd --create-home --uid 1000 appuser
USER appuser

EXPOSE 7860

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
