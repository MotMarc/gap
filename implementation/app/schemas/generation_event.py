from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CreateGenerationEventRequest(BaseModel):
    provider_id: str = Field(
        min_length=1,
        max_length=100,
        examples=["gap-demo-provider"],
    )

    model_id: str = Field(
        min_length=1,
        max_length=200,
        examples=["demo-image-model-v1"],
    )


class GenerationEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    generation_id: str
    provider_id: str
    model_id: str
    created_at: datetime
    gap_version: str
