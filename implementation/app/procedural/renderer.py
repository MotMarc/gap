import hashlib
import math
import random
import textwrap

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

from app.procedural.palette import blend_colours, create_palette
from app.procedural.parser import ParsedPrompt, SceneTheme, parse_prompt
from app.procedural.themes import (
    IMAGE_HEIGHT,
    IMAGE_WIDTH,
    draw_abstract,
    draw_city,
    draw_cyber,
    draw_fire,
    draw_forest,
    draw_galaxy,
    draw_mountains,
    draw_ocean,
    draw_snow,
    draw_sunset,
)


class ProceduralRenderer:
    def render(self, prompt: str) -> Image.Image:
        parsed_prompt = parse_prompt(prompt)
        prompt_digest = hashlib.sha256(parsed_prompt.prompt.encode("utf-8")).hexdigest()

        random_generator = random.Random(int(prompt_digest, 16))

        palette = create_palette(
            parsed_prompt.themes,
            random_generator,
        )

        image = self._create_background(
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

        self._draw_scene(
            draw=draw,
            parsed_prompt=parsed_prompt,
            palette=palette,
            random_generator=random_generator,
        )

        image = image.filter(ImageFilter.GaussianBlur(radius=0.35))

        image = ImageEnhance.Contrast(image).enhance(1.08)
        image = ImageEnhance.Color(image).enhance(1.12)

        self._draw_information_overlay(
            image=image,
            parsed_prompt=parsed_prompt,
            prompt_digest=prompt_digest,
            palette=palette,
        )

        return image

    def _create_background(
        self,
        palette: list[tuple[int, int, int]],
        random_generator: random.Random,
    ) -> Image.Image:
        image = Image.new(
            mode="RGB",
            size=(IMAGE_WIDTH, IMAGE_HEIGHT),
        )

        pixels = image.load()

        angle = random_generator.uniform(0, math.tau)
        direction_x = math.cos(angle)
        direction_y = math.sin(angle)

        first_colour = palette[0]
        second_colour = palette[2]

        for vertical_position in range(IMAGE_HEIGHT):
            for horizontal_position in range(IMAGE_WIDTH):
                normalised_x = horizontal_position / (IMAGE_WIDTH - 1)
                normalised_y = vertical_position / (IMAGE_HEIGHT - 1)

                gradient_position = (
                    normalised_x * direction_x + normalised_y * direction_y + 1
                ) / 2

                pixels[horizontal_position, vertical_position] = blend_colours(
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
                random_generator.randrange(70, 186)
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

        texture_rgb = Image.merge(
            "RGB",
            (
                texture,
                texture,
                texture,
            ),
        )

        return Image.blend(
            image,
            texture_rgb,
            alpha=0.07,
        )

    def _draw_scene(
        self,
        draw: ImageDraw.ImageDraw,
        parsed_prompt: ParsedPrompt,
        palette: list[tuple[int, int, int]],
        random_generator: random.Random,
    ) -> None:
        themes = parsed_prompt.themes

        if SceneTheme.SUNSET in themes:
            draw_sunset(draw, palette, random_generator)

        if SceneTheme.GALAXY in themes:
            draw_galaxy(draw, palette, random_generator)

        if SceneTheme.MOUNTAIN in themes:
            draw_mountains(draw, palette, random_generator)

        if SceneTheme.FOREST in themes:
            draw_forest(draw, palette, random_generator)

        if SceneTheme.CITY in themes:
            draw_city(draw, palette, random_generator)

        if SceneTheme.OCEAN in themes:
            draw_ocean(draw, palette, random_generator)

        if SceneTheme.FIRE in themes:
            draw_fire(draw, palette, random_generator)

        if SceneTheme.SNOW in themes:
            draw_snow(draw, palette, random_generator)

        if SceneTheme.CYBER in themes:
            draw_cyber(draw, palette, random_generator)

        if themes == (SceneTheme.ABSTRACT,):
            draw_abstract(draw, palette, random_generator)

    def _draw_information_overlay(
        self,
        image: Image.Image,
        parsed_prompt: ParsedPrompt,
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
            fill=(8, 10, 14, 210),
            outline=(*palette[1], 175),
            width=2,
        )

        draw.text(
            xy=(72, overlay_top + 26),
            text="GAP SEMANTIC PROCEDURAL ARTIFACT",
            fill=(245, 247, 250),
            font=font,
        )

        wrapped_prompt = textwrap.wrap(
            parsed_prompt.prompt,
            width=95,
        )

        prompt_preview = " ".join(wrapped_prompt[:2])

        if len(wrapped_prompt) > 2:
            prompt_preview = f"{prompt_preview}..."

        draw.text(
            xy=(72, overlay_top + 65),
            text=prompt_preview,
            fill=(218, 224, 231),
            font=font,
        )

        theme_text = ", ".join(theme.value for theme in parsed_prompt.themes)

        draw.text(
            xy=(72, overlay_top + 101),
            text=f"Themes: {theme_text}",
            fill=(*palette[1], 255),
            font=font,
        )

        draw.text(
            xy=(72, overlay_top + 132),
            text=f"Digest: {prompt_digest[:32]}",
            fill=(188, 198, 210),
            font=font,
        )
