from pydantic import BaseModel, Field


class ArtifactDigest(BaseModel):
    algorithm: str = Field(
        default="sha-256",
        pattern=r"^sha-256$",
    )
    value: str = Field(
        min_length=64,
        max_length=64,
        pattern=r"^[0-9a-f]{64}$",
    )


class ArtifactDescriptor(BaseModel):
    media_type: str = Field(
        min_length=1,
        max_length=255,
        examples=["image/png"],
    )
    digest: ArtifactDigest
