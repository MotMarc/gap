import colorsys
import random

from app.procedural.parser import SceneTheme


RGBColour = tuple[int, int, int]


_THEME_HUES: dict[SceneTheme, int] = {
    SceneTheme.ABSTRACT: 265,
    SceneTheme.CITY: 215,
    SceneTheme.FOREST: 130,
    SceneTheme.OCEAN: 205,
    SceneTheme.GALAXY: 265,
    SceneTheme.FIRE: 12,
    SceneTheme.SNOW: 195,
    SceneTheme.MOUNTAIN: 220,
    SceneTheme.SUNSET: 22,
    SceneTheme.CYBER: 290,
}


def create_palette(
    themes: tuple[SceneTheme, ...],
    random_generator: random.Random,
) -> list[RGBColour]:
    primary_theme = themes[0]
    base_hue = _THEME_HUES[primary_theme]

    if SceneTheme.SUNSET in themes:
        base_hue = 20
    elif SceneTheme.FIRE in themes:
        base_hue = 8
    elif SceneTheme.OCEAN in themes:
        base_hue = 205
    elif SceneTheme.FOREST in themes:
        base_hue = 130
    elif SceneTheme.GALAXY in themes:
        base_hue = 265

    hue_offsets = (
        0,
        random_generator.choice((18, 24, 32)),
        random_generator.choice((70, 100, 130)),
        random_generator.choice((170, 190, 215)),
        random_generator.choice((285, 310, 335)),
    )

    palette: list[RGBColour] = []

    for index, offset in enumerate(hue_offsets):
        hue = ((base_hue + offset) % 360) / 360
        saturation = random_generator.uniform(0.55, 0.9)
        lightness = random_generator.uniform(
            0.22 if index < 2 else 0.36,
            0.7,
        )

        red, green, blue = colorsys.hls_to_rgb(
            hue,
            lightness,
            saturation,
        )

        palette.append(
            (
                round(red * 255),
                round(green * 255),
                round(blue * 255),
            )
        )

    return palette


def blend_colours(
    first_colour: RGBColour,
    second_colour: RGBColour,
    amount: float,
) -> RGBColour:
    clamped_amount = max(0.0, min(1.0, amount))

    return tuple(
        round(first_component + (second_component - first_component) * clamped_amount)
        for first_component, second_component in zip(
            first_colour,
            second_colour,
        )
    )
