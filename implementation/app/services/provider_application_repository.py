from dataclasses import replace

from app.domain.provider_application import (
    ProviderApplicationStatus,
    ProviderOnboardingApplication,
)


class ProviderApplicationNotFoundError(LookupError):
    """
    Raised when an onboarding application does not exist.
    """


class DuplicateProviderApplicationError(ValueError):
    """
    Raised when an application ID or active provider application is duplicated.
    """


class ProviderApplicationRepository:
    """
    In-memory repository of private provider onboarding applications.
    """

    def __init__(
        self,
        applications: list[ProviderOnboardingApplication] | None = None,
    ) -> None:
        self._applications: dict[str, ProviderOnboardingApplication] = {}

        for application in applications or []:
            self.add(application)

    def add(
        self,
        application: ProviderOnboardingApplication,
    ) -> None:
        if application.application_id in self._applications:
            raise DuplicateProviderApplicationError(
                f"Provider application already exists: {application.application_id}"
            )

        if (
            application.is_active
            and self.active_for_provider(application.provider_id) is not None
        ):
            raise DuplicateProviderApplicationError(
                "An active onboarding application already exists for provider: "
                f"{application.provider_id}"
            )

        self._applications[application.application_id] = application

    def get(
        self,
        application_id: str,
    ) -> ProviderOnboardingApplication:
        application = self._applications.get(application_id)

        if application is None:
            raise ProviderApplicationNotFoundError(
                f"Unknown provider application: {application_id}"
            )

        return application

    def list_all(self) -> list[ProviderOnboardingApplication]:
        return list(self._applications.values())

    def list_for_provider(
        self,
        provider_id: str,
    ) -> list[ProviderOnboardingApplication]:
        return [
            application
            for application in self._applications.values()
            if application.provider_id == provider_id
        ]

    def active_for_provider(
        self,
        provider_id: str,
    ) -> ProviderOnboardingApplication | None:
        return next(
            (
                application
                for application in self._applications.values()
                if application.provider_id == provider_id and application.is_active
            ),
            None,
        )

    def update_status(
        self,
        application_id: str,
        status: ProviderApplicationStatus,
    ) -> ProviderOnboardingApplication:
        application = self.get(application_id)
        updated_application = replace(
            application,
            status=status,
        )
        self._applications[application_id] = updated_application
        return updated_application
