from fastapi import FastAPI

from app.api.generation_events import router as generation_events_router


app = FastAPI(
    title="Generation Attribution Protocol",
    description="Reference implementation of GAP",
    version="0.1.0",
)

app.include_router(generation_events_router)


@app.get("/")
def root() -> dict[str, str]:
    return {
        "project": "Generation Attribution Protocol",
        "status": "running",
        "version": "0.1.0",
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "healthy"}