import secrets


CREDENTIAL_ID_BYTE_LENGTH = 32
CREDENTIAL_ID_PREFIX = "gc"


def generate_credential_id() -> str:
    """
    Generate a cryptographically secure 256-bit credential identifier.
    """

    random_value = secrets.token_hex(CREDENTIAL_ID_BYTE_LENGTH)
    return f"{CREDENTIAL_ID_PREFIX}_{random_value}"


def is_valid_credential_id(credential_id: str) -> bool:
    """
    Validate the structural format of a credential identifier.
    """

    prefix = f"{CREDENTIAL_ID_PREFIX}_"

    if not credential_id.startswith(prefix):
        return False

    hexadecimal_part = credential_id.removeprefix(prefix)

    if len(hexadecimal_part) != CREDENTIAL_ID_BYTE_LENGTH * 2:
        return False

    try:
        int(hexadecimal_part, 16)
    except ValueError:
        return False

    return True
