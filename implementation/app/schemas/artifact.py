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
    # Optional for backwards compatibility with credentials issued before 0.16.
    # A missing value has the historical raw-byte meaning.
    binding_profile: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
        pattern=r"^gap-[a-z0-9-]+-v[0-9]+$",
    )
