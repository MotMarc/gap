from fastapi import FastAPI

from app.api.generation_events import router as generation_events_router
from app.api.protocol import router as protocol_router


app = FastAPI(
    title="Generation Attribution Protocol",
    description="Reference implementation of GAP",
    version="0.0.1",
)

app.include_router(generation_events_router)
app.include_router(protocol_router)


@app.get("/")
def root() -> dict[str, str]:
    return {
        "project": "Generation Attribution Protocol",
        "status": "running",
        "version": "0.0.1",
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "healthy"}
