from app.procedural.parser import SceneTheme, parse_prompt


def test_city_sunset_and_cyber_themes_are_detected() -> None:
    parsed_prompt = parse_prompt("A cyberpunk city at sunset.")

    assert SceneTheme.CITY in parsed_prompt.themes
    assert SceneTheme.SUNSET in parsed_prompt.themes
    assert SceneTheme.CYBER in parsed_prompt.themes


def test_ocean_mountain_and_snow_themes_are_detected() -> None:
    parsed_prompt = parse_prompt("Snow-covered mountains beside the ocean.")

    assert SceneTheme.SNOW in parsed_prompt.themes
    assert SceneTheme.MOUNTAIN in parsed_prompt.themes
    assert SceneTheme.OCEAN in parsed_prompt.themes


def test_unknown_prompt_uses_abstract_theme() -> None:
    parsed_prompt = parse_prompt("An unusual composition of memory and silence.")

    assert parsed_prompt.themes == (SceneTheme.ABSTRACT,)


def test_prompt_whitespace_is_normalised() -> None:
    parsed_prompt = parse_prompt("   A   city    beside   the ocean.   ")

    assert parsed_prompt.prompt == "A city beside the ocean."


def test_empty_prompt_is_rejected() -> None:
    try:
        parse_prompt("   ")
    except ValueError as error:
        assert str(error) == "A non-empty prompt is required."
    else:
        raise AssertionError("Expected an empty prompt to be rejected.")
