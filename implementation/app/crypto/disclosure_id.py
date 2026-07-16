import secrets


DISCLOSURE_ID_BYTE_LENGTH = 16
DISCLOSURE_ID_PREFIX = "disclosure"


def generate_disclosure_id() -> str:
    """
    Generate an opaque identifier for a disclosure audit event.
    """

    random_value = secrets.token_hex(DISCLOSURE_ID_BYTE_LENGTH)
    return f"{DISCLOSURE_ID_PREFIX}_{random_value}"
