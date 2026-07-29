class GapError(Exception):
    """Base class for safe, public SDK errors."""

    code = "gap-error"


class CredentialError(GapError):
    code = "credential-error"


class KeyError(GapError):
    code = "key-error"


class TrustMaterialError(GapError):
    code = "trust-material-error"


class ServiceError(GapError):
    code = "service-error"


class NetworkError(ServiceError):
    code = "network-error"
