from fastapi import FastAPI

app = FastAPI(title="Manufacturing Text-to-SQL AI Service")


@app.get("/health")
async def health() -> dict[str, str]:
    """Liveness probe: confirms the service is up. No DB or LLM wired yet."""
    return {"status": "ok"}
