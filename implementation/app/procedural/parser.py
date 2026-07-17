from dataclasses import dataclass
from enum import Enum


class SceneTheme(str, Enum):
    ABSTRACT = "abstract"
    CITY = "city"
    FOREST = "forest"
    OCEAN = "ocean"
    GALAXY = "galaxy"
    FIRE = "fire"
    SNOW = "snow"
    MOUNTAIN = "mountain"
    SUNSET = "sunset"
    CYBER = "cyber"


@dataclass(frozen=True)
class ParsedPrompt:
    prompt: str
    themes: tuple[SceneTheme, ...]


_THEME_KEYWORDS: dict[SceneTheme, tuple[str, ...]] = {
    SceneTheme.CITY: (
        "city",
        "cities",
        "building",
        "buildings",
        "skyline",
        "urban",
        "metropolis",
        "skyscraper",
        "skyscrapers",
        "street",
    ),
    SceneTheme.FOREST: (
        "forest",
        "tree",
        "trees",
        "woods",
        "woodland",
        "jungle",
        "nature",
    ),
    SceneTheme.OCEAN: (
        "ocean",
        "sea",
        "water",
        "wave",
        "waves",
        "river",
        "lake",
        "coast",
        "beach",
    ),
    SceneTheme.GALAXY: (
        "galaxy",
        "space",
        "star",
        "stars",
        "cosmos",
        "nebula",
        "planet",
        "planets",
        "universe",
    ),
    SceneTheme.FIRE: (
        "fire",
        "flame",
        "flames",
        "lava",
        "burning",
        "inferno",
        "ember",
        "embers",
    ),
    SceneTheme.SNOW: (
        "snow",
        "snowy",
        "ice",
        "icy",
        "frozen",
        "winter",
        "glacier",
        "crystal",
        "crystals",
    ),
    SceneTheme.MOUNTAIN: (
        "mountain",
        "mountains",
        "peak",
        "peaks",
        "cliff",
        "valley",
        "alpine",
        "hill",
        "hills",
    ),
    SceneTheme.SUNSET: (
        "sunset",
        "sunrise",
        "dusk",
        "dawn",
        "evening",
        "golden hour",
    ),
    SceneTheme.CYBER: (
        "cyber",
        "cyberpunk",
        "digital",
        "neon",
        "futuristic",
        "technology",
        "circuit",
        "circuits",
        "matrix",
    ),
}


def parse_prompt(prompt: str) -> ParsedPrompt:
    cleaned_prompt = " ".join(prompt.strip().split())

    if not cleaned_prompt:
        raise ValueError("A non-empty prompt is required.")

    lowercase_prompt = cleaned_prompt.lower()
    detected_themes: list[SceneTheme] = []

    for theme, keywords in _THEME_KEYWORDS.items():
        if any(keyword in lowercase_prompt for keyword in keywords):
            detected_themes.append(theme)

    if not detected_themes:
        detected_themes.append(SceneTheme.ABSTRACT)

    return ParsedPrompt(
        prompt=cleaned_prompt,
        themes=tuple(detected_themes),
    )
