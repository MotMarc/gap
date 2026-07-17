import math
import random

from PIL import ImageDraw

from app.procedural.palette import RGBColour


IMAGE_WIDTH = 1024
IMAGE_HEIGHT = 1024


def draw_city(
    draw: ImageDraw.ImageDraw,
    palette: list[RGBColour],
    random_generator: random.Random,
) -> None:
    horizon = random_generator.randint(500, 680)
    current_x = -20

    while current_x < IMAGE_WIDTH:
        building_width = random_generator.randint(55, 135)
        building_height = random_generator.randint(150, 480)
        building_top = horizon - building_height

        colour = random_generator.choice(palette[:3])

        draw.rectangle(
            xy=(
                current_x,
                building_top,
                current_x + building_width,
                IMAGE_HEIGHT,
            ),
            fill=(*colour, 220),
            outline=(230, 235, 245, 120),
            width=2,
        )

        window_width = random_generator.randint(6, 12)
        window_height = random_generator.randint(9, 16)

        for window_y in range(
            building_top + 22,
            horizon - 20,
            window_height + 16,
        ):
            for window_x in range(
                current_x + 14,
                current_x + building_width - 12,
                window_width + 15,
            ):
                if random_generator.random() < 0.68:
                    window_colour = random_generator.choice(
                        (
                            (255, 219, 126, 185),
                            (120, 220, 255, 175),
                            (245, 245, 255, 145),
                        )
                    )

                    draw.rectangle(
                        xy=(
                            window_x,
                            window_y,
                            window_x + window_width,
                            window_y + window_height,
                        ),
                        fill=window_colour,
                    )

        current_x += building_width + random_generator.randint(8, 25)


def draw_ocean(
    draw: ImageDraw.ImageDraw,
    palette: list[RGBColour],
    random_generator: random.Random,
) -> None:
    start_y = random_generator.randint(570, 700)

    for layer_index in range(9):
        base_y = start_y + layer_index * 34
        amplitude = random_generator.randint(8, 28)
        frequency = random_generator.uniform(0.012, 0.025)
        phase = random_generator.uniform(0, math.tau)

        points = []

        for horizontal_position in range(-20, IMAGE_WIDTH + 21, 12):
            vertical_position = (
                base_y
                + math.sin(
                    horizontal_position * frequency + phase,
                )
                * amplitude
            )

            points.append(
                (
                    horizontal_position,
                    round(vertical_position),
                )
            )

        colour = palette[(layer_index + 1) % len(palette)]

        draw.line(
            xy=points,
            fill=(*colour, 175),
            width=random_generator.randint(4, 12),
            joint="curve",
        )


def draw_forest(
    draw: ImageDraw.ImageDraw,
    palette: list[RGBColour],
    random_generator: random.Random,
) -> None:
    tree_count = random_generator.randint(18, 30)

    for _ in range(tree_count):
        base_x = random_generator.randint(-20, IMAGE_WIDTH + 20)
        base_y = random_generator.randint(650, 960)
        height = random_generator.randint(180, 430)
        trunk_width = random_generator.randint(8, 24)

        trunk_colour = random_generator.choice(
            (
                (57, 39, 30, 225),
                (73, 48, 33, 220),
                (40, 45, 35, 225),
            )
        )

        draw.line(
            xy=(
                base_x,
                base_y,
                base_x,
                base_y - height,
            ),
            fill=trunk_colour,
            width=trunk_width,
        )

        branch_count = random_generator.randint(5, 10)

        for branch_index in range(branch_count):
            branch_y = base_y - int(
                height * (0.35 + branch_index / (branch_count * 1.7))
            )

            branch_length = random_generator.randint(30, 100)
            direction = -1 if branch_index % 2 == 0 else 1

            draw.line(
                xy=(
                    base_x,
                    branch_y,
                    base_x + branch_length * direction,
                    branch_y - random_generator.randint(15, 70),
                ),
                fill=trunk_colour,
                width=max(3, trunk_width // 3),
            )

        canopy_colour = random_generator.choice(palette)
        canopy_radius = random_generator.randint(45, 110)

        draw.ellipse(
            xy=(
                base_x - canopy_radius,
                base_y - height - canopy_radius,
                base_x + canopy_radius,
                base_y - height + canopy_radius,
            ),
            fill=(*canopy_colour, 150),
            outline=(235, 255, 235, 85),
            width=2,
        )


def draw_mountains(
    draw: ImageDraw.ImageDraw,
    palette: list[RGBColour],
    random_generator: random.Random,
) -> None:
    for layer_index in range(4):
        baseline = 600 + layer_index * 85
        points = [(-50, IMAGE_HEIGHT)]

        current_x = -50

        while current_x < IMAGE_WIDTH + 50:
            peak_width = random_generator.randint(170, 320)
            peak_height = random_generator.randint(130, 350)

            points.append(
                (
                    current_x + peak_width // 2,
                    baseline - peak_height,
                )
            )

            current_x += peak_width
            points.append((current_x, baseline))

        points.append((IMAGE_WIDTH + 50, IMAGE_HEIGHT))

        colour = palette[layer_index % len(palette)]

        draw.polygon(
            xy=points,
            fill=(
                colour[0],
                colour[1],
                colour[2],
                115 + layer_index * 25,
            ),
        )


def draw_galaxy(
    draw: ImageDraw.ImageDraw,
    palette: list[RGBColour],
    random_generator: random.Random,
) -> None:
    centre_x = random_generator.randint(380, 650)
    centre_y = random_generator.randint(280, 520)

    for _ in range(220):
        angle = random_generator.uniform(0, math.tau * 4)
        radius = random_generator.uniform(5, 430)

        spiral_offset = angle * 18

        x_position = centre_x + math.cos(angle) * (radius + spiral_offset)
        y_position = centre_y + math.sin(angle) * radius * 0.42

        star_radius = random_generator.choice((1, 1, 1, 2, 2, 3))
        colour = random_generator.choice(palette + [(245, 245, 255)])

        draw.ellipse(
            xy=(
                x_position - star_radius,
                y_position - star_radius,
                x_position + star_radius,
                y_position + star_radius,
            ),
            fill=(*colour, random_generator.randint(120, 245)),
        )


def draw_fire(
    draw: ImageDraw.ImageDraw,
    palette: list[RGBColour],
    random_generator: random.Random,
) -> None:
    flame_count = random_generator.randint(20, 35)

    for _ in range(flame_count):
        base_x = random_generator.randint(0, IMAGE_WIDTH)
        base_y = random_generator.randint(700, 1050)
        flame_height = random_generator.randint(130, 430)
        flame_width = random_generator.randint(35, 110)

        colour = random_generator.choice(
            (
                (255, 65, 15),
                (255, 128, 18),
                (255, 205, 40),
                random_generator.choice(palette),
            )
        )

        points = (
            (base_x - flame_width, base_y),
            (
                base_x - flame_width // 3,
                base_y - flame_height // 2,
            ),
            (base_x, base_y - flame_height),
            (
                base_x + flame_width // 3,
                base_y - flame_height // 2,
            ),
            (base_x + flame_width, base_y),
        )

        draw.polygon(
            xy=points,
            fill=(*colour, random_generator.randint(100, 190)),
        )


def draw_snow(
    draw: ImageDraw.ImageDraw,
    palette: list[RGBColour],
    random_generator: random.Random,
) -> None:
    for _ in range(95):
        centre_x = random_generator.randint(0, IMAGE_WIDTH)
        centre_y = random_generator.randint(0, IMAGE_HEIGHT)
        radius = random_generator.randint(3, 15)

        colour = random_generator.choice(
            (
                (245, 250, 255),
                (196, 230, 255),
                random_generator.choice(palette),
            )
        )

        for angle_index in range(0, 360, 60):
            angle = math.radians(angle_index)

            end_x = centre_x + math.cos(angle) * radius
            end_y = centre_y + math.sin(angle) * radius

            draw.line(
                xy=(centre_x, centre_y, end_x, end_y),
                fill=(*colour, random_generator.randint(130, 230)),
                width=1,
            )


def draw_sunset(
    draw: ImageDraw.ImageDraw,
    palette: list[RGBColour],
    random_generator: random.Random,
) -> None:
    centre_x = random_generator.randint(280, 740)
    centre_y = random_generator.randint(390, 620)
    radius = random_generator.randint(75, 145)

    draw.ellipse(
        xy=(
            centre_x - radius,
            centre_y - radius,
            centre_x + radius,
            centre_y + radius,
        ),
        fill=(255, 191, 70, 205),
        outline=(255, 236, 170, 180),
        width=5,
    )

    for ring_index in range(1, 5):
        ring_radius = radius + ring_index * 22

        draw.ellipse(
            xy=(
                centre_x - ring_radius,
                centre_y - ring_radius,
                centre_x + ring_radius,
                centre_y + ring_radius,
            ),
            outline=(*palette[ring_index % len(palette)], 50),
            width=5,
        )


def draw_cyber(
    draw: ImageDraw.ImageDraw,
    palette: list[RGBColour],
    random_generator: random.Random,
) -> None:
    horizon = random_generator.randint(580, 730)
    grid_colour = random_generator.choice(palette[1:])

    for vertical_line in range(-10, 11):
        destination_x = IMAGE_WIDTH // 2 + vertical_line * 130

        draw.line(
            xy=(
                IMAGE_WIDTH // 2,
                horizon,
                destination_x,
                IMAGE_HEIGHT,
            ),
            fill=(*grid_colour, 110),
            width=2,
        )

    for line_index in range(12):
        progress = line_index / 11
        vertical_position = horizon + int((progress**2) * (IMAGE_HEIGHT - horizon))

        draw.line(
            xy=(0, vertical_position, IMAGE_WIDTH, vertical_position),
            fill=(*grid_colour, 100),
            width=2,
        )

    for _ in range(25):
        start_x = random_generator.randint(20, IMAGE_WIDTH - 20)
        start_y = random_generator.randint(40, IMAGE_HEIGHT - 80)
        length = random_generator.randint(35, 150)

        colour = random_generator.choice(palette)

        draw.line(
            xy=(
                start_x,
                start_y,
                start_x + length,
                start_y,
            ),
            fill=(*colour, 150),
            width=random_generator.randint(2, 5),
        )

        draw.line(
            xy=(
                start_x + length,
                start_y,
                start_x + length,
                start_y + random_generator.randint(15, 70),
            ),
            fill=(*colour, 150),
            width=random_generator.randint(2, 5),
        )


def draw_abstract(
    draw: ImageDraw.ImageDraw,
    palette: list[RGBColour],
    random_generator: random.Random,
) -> None:
    for _ in range(random_generator.randint(22, 38)):
        centre_x = random_generator.randint(-50, IMAGE_WIDTH + 50)
        centre_y = random_generator.randint(-50, IMAGE_HEIGHT + 50)
        width = random_generator.randint(60, 310)
        height = random_generator.randint(60, 310)
        colour = random_generator.choice(palette)

        bounding_box = (
            centre_x - width // 2,
            centre_y - height // 2,
            centre_x + width // 2,
            centre_y + height // 2,
        )

        if random_generator.random() < 0.5:
            draw.ellipse(
                xy=bounding_box,
                fill=(*colour, random_generator.randint(45, 145)),
                outline=(255, 255, 255, 80),
                width=2,
            )
        else:
            draw.rounded_rectangle(
                xy=bounding_box,
                radius=random_generator.randint(10, 65),
                fill=(*colour, random_generator.randint(45, 145)),
                outline=(255, 255, 255, 80),
                width=2,
            )
