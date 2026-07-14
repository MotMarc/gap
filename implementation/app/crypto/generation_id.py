import secrets


GID_BYTE_LENGTH = 32
GID_PREFIX = "gid"


def generate_generation_id() -> str:
    """
    Generate a cryptographically secure 256-bit Generation Identifier.

    The identifier contains no user, provider, device, prompt, or timestamp
    information. It is an opaque identifier for a single generation event.
    """

    random_value = secrets.token_hex(GID_BYTE_LENGTH)
    return f"{GID_PREFIX}_{random_value}"


def is_valid_generation_id(generation_id: str) -> bool:
    """
    Validate the structural format of a Generation Identifier.

    This only validates the format. It does not prove that the GID was issued
    by a legitimate provider.
    """

    expected_hex_length = GID_BYTE_LENGTH * 2

    if not generation_id.startswith(f"{GID_PREFIX}_"):
        return False

    hexadecimal_part = generation_id.removeprefix(f"{GID_PREFIX}_")

    if len(hexadecimal_part) != expected_hex_length:
        return False

    try:
        int(hexadecimal_part, 16)
    except ValueError:
        return False

    return True