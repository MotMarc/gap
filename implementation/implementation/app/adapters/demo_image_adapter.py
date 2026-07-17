import hashlib
import math
import random
import textwrap
from io import BytesIO

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

from app.domain.generated_artifact import GeneratedArtifact


IMAGE_WIDTH = 1024
IMAGE_HEIGHT = 1024
MODEL_ID = "gap-procedural-image-v1"

MIN_SHAPE_COUNT = 18
MAX_SHAPE_COUNT = 32

LIGHT_TEXT_COLOUR = (245, 247, 250)
DARK_TEXT_COLOUR = (18, 22, 28)


class DemoImageAdapter:
    """
    Generate deterministic prompt-conditioned procedural PNG images.

    This adapter demonstrates GAP's generation and attribution workflow
    without requiring a GPU, generative AI model or external API.

    It is not presented as an artificial-intelligence image generator.
    """

    @property
    def provider_id(self) -> str:
        return "gap-demo-provider"

    def generate(self, prompt: str) -> GeneratedArtifact:
        cleaned_prompt = prompt.strip()

        if not cleaned_prompt:
            raise ValueError("A non-empty prompt is required.")

        prompt_digest = hashlib.sha256(cleaned_prompt.encode("utf-8")).hexdigest()

        seed = int(prompt_digest, 16)
        random_generator = random.Random(seed)

        palette = self._create_palette(
            prompt=cleaned_prompt,
            random_generator=random_generator,
        )

        image = self._create_gradient_background(
            palette=palette,
            random_generator=random_generator,
        )

        image = self._add_texture(
            image=image,
            random_generator=random_generator,
        )

        draw = ImageDraw.Draw(
            image,
            mode="RGBA",
        )

        composition_style = random_generator.choice(
            (
                "radial",
                "diagonal",
                "layered",
                "scattered",
            )
        )

        self._draw_composition(
            draw=draw,
            palette=palette,
            composition_style=composition_style,
            random_generator=random_generator,
        )

        self._draw_accent_lines(
            draw=draw,
            palette=palette,
            random_generator=random_generator,
        )

        image = image.filter(
            ImageFilter.GaussianBlur(radius=random_generator.uniform(0.15, 0.65))
        )

        image = ImageEnhance.Contrast(image).enhance(1.08)
        image = ImageEnhance.Color(image).enhance(1.12)

        self._draw_information_overlay(
            image=image,
            prompt=cleaned_prompt,
            prompt_digest=prompt_digest,
            palette=palette,
        )

        output = BytesIO()

        image.save(
            output,
            format="PNG",
            optimize=False,
        )

        return GeneratedArtifact(
            content=output.getvalue(),
            media_type="image/png",
            filename="gap-generated-artifact.png",
            model_id=MODEL_ID,
        )

    def _create_palette(
        self,
        prompt: str,
        random_generator: random.Random,
    ) -> list[tuple[int, int, int]]:
        base_hue = random_generator.randrange(0, 360)

        keyword_hues = {
            "red": 0,
            "orange": 28,
            "yellow": 52,
            "green": 125,
            "forest": 135,
            "blue": 215,
            "ocean": 205,
            "purple": 275,
            "pink": 325,
            "night": 235,
            "sunset": 18,
            "fire": 8,
            "ice": 190,
        }

        lowercase_prompt = prompt.lower()

        for keyword, keyword_hue in keyword_hues.items():
            if keyword in lowercase_prompt:
                base_hue = keyword_hue
                break

        hue_offsets = (
            0,
            random_generator.choice((22, 30, 45)),
            random_generator.choice((120, 145, 180)),
            random_generator.choice((200, 220, 240)),
            random_generator.choice((300, 320, 335)),
        )

        palette = []

        for index, hue_offset in enumerate(hue_offsets):
            hue = (base_hue + hue_offset) % 360

            saturation = random_generator.uniform(
                0.52,
                0.88,
            )

            lightness = random_generator.uniform(
                0.25 if index < 2 else 0.38,
                0.68,
            )

            palette.append(
                self._hsl_to_rgb(
                    hue=hue,
                    saturation=saturation,
                    lightness=lightness,
                )
            )

        return palette

    def _create_gradient_background(
        self,
        palette: list[tuple[int, int, int]],
        random_generator: random.Random,
    ) -> Image.Image:
        image = Image.new(
            mode="RGB",
            size=(IMAGE_WIDTH, IMAGE_HEIGHT),
        )

        pixels = image.load()

        first_colour = palette[0]
        second_colour = palette[2]

        angle = random_generator.uniform(
            0,
            math.tau,
        )

        direction_x = math.cos(angle)
        direction_y = math.sin(angle)

        for vertical_position in range(IMAGE_HEIGHT):
            for horizontal_position in range(IMAGE_WIDTH):
                normalised_x = horizontal_position / (IMAGE_WIDTH - 1)
                normalised_y = vertical_position / (IMAGE_HEIGHT - 1)

                gradient_position = (
                    normalised_x * direction_x + normalised_y * direction_y + 1
                ) / 2

                gradient_position = max(
                    0.0,
                    min(1.0, gradient_position),
                )

                pixels[horizontal_position, vertical_position] = self._blend_colours(
                    first_colour,
                    second_colour,
                    gradient_position,
                )

        return image

    def _add_texture(
        self,
        image: Image.Image,
        random_generator: random.Random,
    ) -> Image.Image:
        texture_size = 48

        texture = Image.new(
            mode="L",
            size=(texture_size, texture_size),
        )

        texture.putdata(
            [
                random_generator.randrange(65, 191)
                for _ in range(texture_size * texture_size)
            ]
        )

        resampling_module = getattr(
            Image,
            "Resampling",
            Image,
        )

        texture = texture.resize(
            (IMAGE_WIDTH, IMAGE_HEIGHT),
            resample=resampling_module.BICUBIC,
        )

        texture = texture.filter(ImageFilter.GaussianBlur(radius=5))

        texture_layer = Image.merge(
            "RGB",
            (
                texture,
                texture,
                texture,
            ),
        )

        return Image.blend(
            image,
            texture_layer,
            alpha=0.08,
        )

    def _draw_composition(
        self,
        draw: ImageDraw.ImageDraw,
        palette: list[tuple[int, int, int]],
        composition_style: str,
        random_generator: random.Random,
    ) -> None:
        shape_count = random_generator.randint(
            MIN_SHAPE_COUNT,
            MAX_SHAPE_COUNT,
        )

        centre_x = random_generator.randint(
            IMAGE_WIDTH // 3,
            IMAGE_WIDTH * 2 // 3,
        )

        centre_y = random_generator.randint(
            IMAGE_HEIGHT // 3,
            IMAGE_HEIGHT * 2 // 3,
        )

        for shape_index in range(shape_count):
            colour = random_generator.choice(palette)
            opacity = random_generator.randint(45, 175)

            if composition_style == "radial":
                angle = (shape_index / max(shape_count, 1)) * math.tau

                radius = random_generator.randint(
                    80,
                    390,
                )

                x_position = int(centre_x + math.cos(angle) * radius)

                y_position = int(centre_y + math.sin(angle) * radius)

            elif composition_style == "diagonal":
                progress = shape_index / max(
                    shape_count - 1,
                    1,
                )

                x_position = int(80 + progress * (IMAGE_WIDTH - 160))

                y_position = int(
                    IMAGE_HEIGHT - x_position + random_generator.randint(-170, 170)
                )

            elif composition_style == "layered":
                layer = shape_index % 6

                x_position = random_generator.randint(
                    50,
                    IMAGE_WIDTH - 50,
                )

                y_position = int(100 + layer * 145 + random_generator.randint(-50, 50))

            else:
                x_position = random_generator.randint(
                    30,
                    IMAGE_WIDTH - 30,
                )

                y_position = random_generator.randint(
                    30,
                    IMAGE_HEIGHT - 30,
                )

            width = random_generator.randint(
                55,
                300,
            )

            height = random_generator.randint(
                55,
                300,
            )

            shape_type = random_generator.choice(
                (
                    "ellipse",
                    "rectangle",
                    "polygon",
                    "arc",
                )
            )

            bounding_box = (
                x_position - width // 2,
                y_position - height // 2,
                x_position + width // 2,
                y_position + height // 2,
            )

            fill_colour = (
                colour[0],
                colour[1],
                colour[2],
                opacity,
            )

            outline_colour = (
                255,
                255,
                255,
                min(210, opacity + 30),
            )

            if shape_type == "ellipse":
                draw.ellipse(
                    xy=bounding_box,
                    fill=fill_colour,
                    outline=outline_colour,
                    width=random_generator.randint(1, 5),
                )

            elif shape_type == "rectangle":
                draw.rounded_rectangle(
                    xy=bounding_box,
                    radius=random_generator.randint(8, 65),
                    fill=fill_colour,
                    outline=outline_colour,
                    width=random_generator.randint(1, 5),
                )

            elif shape_type == "polygon":
                point_count = random_generator.randint(
                    3,
                    8,
                )

                points = []

                for point_index in range(point_count):
                    angle = (point_index / point_count) * math.tau

                    point_radius_x = random_generator.uniform(
                        width * 0.25,
                        width * 0.55,
                    )

                    point_radius_y = random_generator.uniform(
                        height * 0.25,
                        height * 0.55,
                    )

                    points.append(
                        (
                            int(x_position + math.cos(angle) * point_radius_x),
                            int(y_position + math.sin(angle) * point_radius_y),
                        )
                    )

                draw.polygon(
                    xy=points,
                    fill=fill_colour,
                    outline=outline_colour,
                )

            else:
                draw.arc(
                    xy=bounding_box,
                    start=random_generator.randint(0, 180),
                    end=random_generator.randint(200, 360),
                    fill=outline_colour,
                    width=random_generator.randint(3, 12),
                )

    def _draw_accent_lines(
        self,
        draw: ImageDraw.ImageDraw,
        palette: list[tuple[int, int, int]],
        random_generator: random.Random,
    ) -> None:
        line_count = random_generator.randint(
            8,
            18,
        )

        for _ in range(line_count):
            colour = random_generator.choice(palette)

            points = [
                (
                    random_generator.randint(
                        -100,
                        IMAGE_WIDTH + 100,
                    ),
                    random_generator.randint(
                        -100,
                        IMAGE_HEIGHT + 100,
                    ),
                )
                for _ in range(random_generator.randint(2, 5))
            ]

            draw.line(
                xy=points,
                fill=(
                    colour[0],
                    colour[1],
                    colour[2],
                    random_generator.randint(45, 145),
                ),
                width=random_generator.randint(2, 12),
                joint="curve",
            )

    def _draw_information_overlay(
        self,
        image: Image.Image,
        prompt: str,
        prompt_digest: str,
        palette: list[tuple[int, int, int]],
    ) -> None:
        draw = ImageDraw.Draw(
            image,
            mode="RGBA",
        )

        font = ImageFont.load_default()

        overlay_top = IMAGE_HEIGHT - 190

        draw.rounded_rectangle(
            xy=(
                40,
                overlay_top,
                IMAGE_WIDTH - 40,
                IMAGE_HEIGHT - 40,
            ),
            radius=24,
            fill=(8, 10, 14, 205),
            outline=(
                palette[1][0],
                palette[1][1],
                palette[1][2],
                175,
            ),
            width=2,
        )

        draw.text(
            xy=(72, overlay_top + 28),
            text="GAP PROMPT-CONDITIONED PROCEDURAL ARTIFACT",
            fill=LIGHT_TEXT_COLOUR,
            font=font,
        )

        wrapped_prompt = textwrap.wrap(
            prompt,
            width=95,
        )

        prompt_preview = " ".join(wrapped_prompt[:2])

        if len(wrapped_prompt) > 2:
            prompt_preview = f"{prompt_preview}..."

        draw.text(
            xy=(72, overlay_top + 67),
            text=prompt_preview,
            fill=(218, 224, 231),
            font=font,
        )

        draw.text(
            xy=(72, overlay_top + 108),
            text=(f"Digest: {prompt_digest[:32]}  Model: {MODEL_ID}"),
            fill=(
                palette[1][0],
                palette[1][1],
                palette[1][2],
            ),
            font=font,
        )

    def _hsl_to_rgb(
        self,
        hue: float,
        saturation: float,
        lightness: float,
    ) -> tuple[int, int, int]:
        chroma = (1 - abs(2 * lightness - 1)) * saturation

        hue_section = hue / 60
        secondary_component = chroma * (1 - abs(hue_section % 2 - 1))

        if 0 <= hue_section < 1:
            red, green, blue = (
                chroma,
                secondary_component,
                0,
            )
        elif 1 <= hue_section < 2:
            red, green, blue = (
                secondary_component,
                chroma,
                0,
            )
        elif 2 <= hue_section < 3:
            red, green, blue = (
                0,
                chroma,
                secondary_component,
            )
        elif 3 <= hue_section < 4:
            red, green, blue = (
                0,
                secondary_component,
                chroma,
            )
        elif 4 <= hue_section < 5:
            red, green, blue = (
                secondary_component,
                0,
                chroma,
            )
        else:
            red, green, blue = (
                chroma,
                0,
                secondary_component,
            )

        lightness_adjustment = lightness - chroma / 2

        return (
            round((red + lightness_adjustment) * 255),
            round((green + lightness_adjustment) * 255),
            round((blue + lightness_adjustment) * 255),
        )

    def _blend_colours(
        self,
        first_colour: tuple[int, int, int],
        second_colour: tuple[int, int, int],
        amount: float,
    ) -> tuple[int, int, int]:
        return tuple(
            round(first_component + (second_component - first_component) * amount)
            for first_component, second_component in zip(
                first_colour,
                second_colour,
            )
        )
