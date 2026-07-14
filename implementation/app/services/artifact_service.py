import hashlib

from app.schemas.artifact import ArtifactDescriptor, ArtifactDigest


def calculate_sha256(artifact: bytes) -> str:
    """
    Calculate the SHA-256 digest of an artifact.
    """

    return hashlib.sha256(artifact).hexdigest()


def create_artifact_descriptor(
    artifact: bytes,
    media_type: str,
) -> ArtifactDescriptor:
    """
    Create a GAP artifact descriptor from raw artifact bytes.
    """

    return ArtifactDescriptor(
        media_type=media_type,
        digest=ArtifactDigest(
            algorithm="sha-256",
            value=calculate_sha256(artifact),
        ),
    )
