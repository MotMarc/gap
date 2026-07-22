from app.adapters.configurable_svg_adapter import ConfigurableSvgAdapter
from app.adapters.demo_image_adapter import DemoImageAdapter
from app.services.provider_adapter_repository import (
    ProviderAdapterRepository,
)


AURORA_ADAPTER = ConfigurableSvgAdapter(
    provider_id="aurora-ai",
    provider_name="Aurora AI",
    model_id="aurora-spectrum-v1",
    primary_colour="#24105f",
    secondary_colour="#d946ef",
    visual_style="Luminous gradient synthesis",
)

MERIDIAN_ADAPTER = ConfigurableSvgAdapter(
    provider_id="meridian-ai",
    provider_name="Meridian AI",
    model_id="meridian-geometry-v1",
    primary_colour="#082f49",
    secondary_colour="#0891b2",
    visual_style="Geometric procedural synthesis",
)


provider_adapter_repository = ProviderAdapterRepository(
    adapters=[
        DemoImageAdapter(),
        AURORA_ADAPTER,
        MERIDIAN_ADAPTER,
    ],
)
