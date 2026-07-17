from app.adapters.demo_image_adapter import DemoImageAdapter
from app.services.provider_adapter_repository import (
    ProviderAdapterRepository,
)


provider_adapter_repository = ProviderAdapterRepository(
    adapters=[
        DemoImageAdapter(),
    ]
)
