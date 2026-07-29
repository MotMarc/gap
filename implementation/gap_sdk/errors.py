class GapError(Exception):
    """Base class for safe, public SDK errors."""

    code = "gap-error"


class CompatibilityError(GapError):
    code = "compatibility-error"


class PackageError(GapError):
    code = "package-error"


class MediaBindingError(GapError):
    code = "media-binding-error"


class ProviderAdapterError(GapError):
    code = "provider-adapter-error"


class ConformanceError(GapError):
    code = "conformance-error"


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
