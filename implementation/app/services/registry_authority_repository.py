from app.domain.registry_authority import RegistryAuthority


class RegistryAuthorityNotFoundError(LookupError):
    pass


class DuplicateRegistryAuthorityError(ValueError):
    pass


class RegistryAuthorityRepository:
    def __init__(self, authorities: list[RegistryAuthority] | None = None) -> None:
        self._authorities: dict[str, RegistryAuthority] = {}
        for authority in authorities or []:
            self.add(authority)

    def add(self, authority: RegistryAuthority) -> None:
        if authority.authority_id in self._authorities:
            raise DuplicateRegistryAuthorityError(
                f"Registry authority already exists: {authority.authority_id}"
            )
        self._authorities[authority.authority_id] = authority

    def get(self, authority_id: str) -> RegistryAuthority:
        try:
            return self._authorities[authority_id]
        except KeyError as error:
            raise RegistryAuthorityNotFoundError(
                f"Unknown registry authority: {authority_id}"
            ) from error

    def list_all(self) -> list[RegistryAuthority]:
        return list(self._authorities.values())
