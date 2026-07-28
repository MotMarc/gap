from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.protocol import router as protocol_router
from app.core.repositories import (
    FEDERATION_INVALID_FILE_COUNT,
    FEDERATION_LOADED_BUNDLE_COUNT,
    transparency_log_repository,
    witness_statement_repository,
    checkpoint_gossip_repository,
)


APPLICATION_DIRECTORY = Path(__file__).resolve().parent
WEB_DIRECTORY = APPLICATION_DIRECTORY / "web"
APPLICATION_VERSION = "0.13.0"


app = FastAPI(
    title="Generation Attribution Protocol",
    description=(
        "Reference implementation and browser demonstrator for the "
        "Generation Attribution Protocol."
    ),
    version=APPLICATION_VERSION,
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
def read_health() -> dict[str, str | int | bool]:
    """
    Return the current service status.
    """

    return {
        "status": "healthy",
        "service": "gap-reference-implementation",
        "version": APPLICATION_VERSION,
        "federation_loaded_bundle_count": FEDERATION_LOADED_BUNDLE_COUNT,
        "federation_invalid_file_count": FEDERATION_INVALID_FILE_COUNT,
        "transparency_log_loaded": True,
        "transparency_entry_count": transparency_log_repository.entry_count,
        "transparency_tree_size": transparency_log_repository.entry_count,
        "transparency_valid_tree_head_count": len(
            transparency_log_repository.list_tree_heads()
        ),
        "transparency_invalid_runtime_object_count": (
            transparency_log_repository.invalid_runtime_object_count
        ),
        "transparency_consistency_valid": True,
        "trusted_witness_count": 1,
        "witness_statement_count": len(witness_statement_repository.list_all()),
        "witness_invalid_runtime_object_count": (
            witness_statement_repository.invalid_runtime_object_count
        ),
        "gossip_observation_count": len(checkpoint_gossip_repository.list_all()),
        "gossip_invalid_runtime_object_count": (
            checkpoint_gossip_repository.invalid_runtime_object_count
        ),
    }
