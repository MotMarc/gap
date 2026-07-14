from fastapi import APIRouter, status

from app.schemas.generation_event import (
    CreateGenerationEventRequest,
    GenerationEventResponse,
)
from app.services.generation_event_service import create_generation_event


router = APIRouter(
    prefix="/generation-events",
    tags=["Generation Events"],
)


@router.post(
    "",
    response_model=GenerationEventResponse,
    status_code=status.HTTP_201_CREATED,
)
def issue_generation_event(
    request: CreateGenerationEventRequest,
) -> GenerationEventResponse:
    event = create_generation_event(
        provider_id=request.provider_id,
        model_id=request.model_id,
    )

    return GenerationEventResponse.model_validate(event)