import hashlib
import html
from dataclasses import dataclass

from app.domain.generated_artifact import GeneratedArtifact


@dataclass(frozen=True, slots=True)
class ConfigurableSvgAdapter:
    provider_id: str
    provider_name: str
    model_id: str
    primary_colour: str
    secondary_colour: str
    visual_style: str

    def generate(self, prompt: str) -> GeneratedArtifact:
        cleaned_prompt = prompt.strip()

        if not cleaned_prompt:
            raise ValueError("The generation prompt cannot be empty.")

        prompt_hash = hashlib.sha256(
            cleaned_prompt.encode("utf-8"),
        ).hexdigest()

        short_hash = prompt_hash[:12]
        rotation = int(prompt_hash[:2], 16) % 360
        offset_x = 110 + int(prompt_hash[2:4], 16) % 180
        offset_y = 90 + int(prompt_hash[4:6], 16) % 180

        safe_prompt = html.escape(cleaned_prompt)
        safe_provider = html.escape(self.provider_name)
        safe_style = html.escape(self.visual_style)

        svg = f"""<svg
    xmlns="http://www.w3.org/2000/svg"
    width="1024"
    height="1024"
    viewBox="0 0 1024 1024"
>
    <defs>
        <linearGradient
            id="background"
            x1="0%"
            y1="0%"
            x2="100%"
            y2="100%"
        >
            <stop
                offset="0%"
                stop-color="{self.primary_colour}"
            />
            <stop
                offset="100%"
                stop-color="{self.secondary_colour}"
            />
        </linearGradient>

        <filter id="shadow">
            <feDropShadow
                dx="0"
                dy="22"
                stdDeviation="24"
                flood-opacity="0.28"
            />
        </filter>
    </defs>

    <rect
        width="1024"
        height="1024"
        fill="url(#background)"
    />

    <circle
        cx="{offset_x}"
        cy="{offset_y}"
        r="190"
        fill="none"
        stroke="rgba(255,255,255,0.35)"
        stroke-width="4"
    />

    <circle
        cx="{1024 - offset_x}"
        cy="{1024 - offset_y}"
        r="260"
        fill="none"
        stroke="rgba(255,255,255,0.22)"
        stroke-width="3"
    />

    <g
        transform="translate(512 430) rotate({rotation})"
        filter="url(#shadow)"
    >
        <rect
            x="-190"
            y="-190"
            width="380"
            height="380"
            rx="72"
            fill="rgba(255,255,255,0.20)"
            stroke="rgba(255,255,255,0.74)"
            stroke-width="5"
        />

        <path
            d="M -115 50 L 0 -130 L 115 50 Z"
            fill="rgba(255,255,255,0.78)"
        />

        <circle
            cx="0"
            cy="55"
            r="58"
            fill="rgba(255,255,255,0.36)"
        />
    </g>

    <text
        x="64"
        y="760"
        fill="white"
        font-family="Arial, Helvetica, sans-serif"
        font-size="26"
        font-weight="700"
        letter-spacing="2"
    >
        {safe_provider}
    </text>

    <text
        x="64"
        y="810"
        fill="rgba(255,255,255,0.76)"
        font-family="Arial, Helvetica, sans-serif"
        font-size="20"
    >
        {safe_style}
    </text>

    <foreignObject
        x="64"
        y="840"
        width="896"
        height="90"
    >
        <div
            xmlns="http://www.w3.org/1999/xhtml"
            style="
                color: rgba(255,255,255,0.88);
                font-family: Arial, Helvetica, sans-serif;
                font-size: 18px;
                line-height: 1.45;
                overflow: hidden;
            "
        >
            {safe_prompt}
        </div>
    </foreignObject>

    <text
        x="64"
        y="970"
        fill="rgba(255,255,255,0.54)"
        font-family="monospace"
        font-size="15"
    >
        GAP generation reference: {short_hash}
    </text>
</svg>
"""

        filename = f"{self.provider_id}-{short_hash}.svg"

        return GeneratedArtifact(
            content=svg.encode("utf-8"),
            media_type="image/svg+xml",
            filename=filename,
            model_id=self.model_id,
        )
