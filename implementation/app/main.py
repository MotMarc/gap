from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.protocol import router as protocol_router


APPLICATION_DIRECTORY = Path(__file__).resolve().parent
WEB_DIRECTORY = APPLICATION_DIRECTORY / "web"


app = FastAPI(
    title="Generation Attribution Protocol",
    description=(
        "Reference implementation and browser demonstrator for the "
        "Generation Attribution Protocol."
    ),
    version="0.5.0",
)


app.include_router(protocol_router)


app.mount(
    "/static",
    StaticFiles(directory=WEB_DIRECTORY),
    name="static",
)


@app.get(
    "/",
    include_in_schema=False,
    response_class=FileResponse,
)
def read_demonstrator() -> FileResponse:
    """
    Serve the GAP browser demonstrator.
    """

    return FileResponse(
        WEB_DIRECTORY / "index.html",
        media_type="text/html",
    )


@app.get(
    "/health",
    tags=["System"],
)
def read_health() -> dict[str, str]:
    """
    Return the current service status.
    """

    return {
        "status": "healthy",
        "service": "gap-reference-implementation",
        "version": "0.5.0",
    }
