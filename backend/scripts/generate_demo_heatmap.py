import json
import math
import random
from pathlib import Path
from statistics import mean


# Reproducible demo data
random.seed(42)

# Phoenix city-center demo coordinates
CENTER_LAT = 33.4484
CENTER_LON = -112.0740

ROWS = 14
COLS = 15

# Approximately 80–100 meter spacing
LAT_STEP = 0.0008
LON_STEP = 0.0009


def clamp(value, minimum, maximum):
    return max(minimum, min(value, maximum))


def generate_tile(row, col, tile_number):
    """
    Generate one synthetic urban heat cell.

    The model creates:
    - hotter urban core
    - cooler pockets
    - local random variation
    - correlated heat index
    - humidity variation
    - solar radiation variation
    """

    row_offset = row - (ROWS - 1) / 2
    col_offset = col - (COLS - 1) / 2

    latitude = CENTER_LAT + row_offset * LAT_STEP
    longitude = CENTER_LON + col_offset * LON_STEP

    # Normalized distance from center
    distance = math.sqrt(
        (row_offset / ROWS) ** 2
        + (col_offset / COLS) ** 2
    )

    # Urban heat-island effect:
    # central locations tend to be hotter
    urban_heat = max(
        0,
        1 - distance * 2.2
    )

    # Create a few cooler pockets
    cool_pocket_1 = math.exp(
        -(
            ((row - 3) ** 2)
            + ((col - 4) ** 2)
        )
        / 8
    )

    cool_pocket_2 = math.exp(
        -(
            ((row - 10) ** 2)
            + ((col - 11) ** 2)
        )
        / 10
    )

    cooling_effect = (
        cool_pocket_1 * 2.2
        + cool_pocket_2 * 1.8
    )

    # Local spatial variation
    wave_effect = (
        math.sin(row * 0.8)
        + math.cos(col * 0.65)
    ) * 0.45

    random_noise = random.uniform(
        -0.45,
        0.45,
    )

    temperature = (
        38.2
        + urban_heat * 5.6
        - cooling_effect
        + wave_effect
        + random_noise
    )

    temperature = clamp(
        temperature,
        36.5,
        45.5,
    )

    # Phoenix-style dry conditions
    humidity = (
        39
        - urban_heat * 10
        + cooling_effect * 1.8
        + random.uniform(-2.5, 2.5)
    )

    humidity = clamp(
        humidity,
        22,
        45,
    )

    # Solar exposure
    solar_radiation = (
        690
        + urban_heat * 220
        - cooling_effect * 35
        + random.uniform(-35, 35)
    )

    solar_radiation = clamp(
        solar_radiation,
        580,
        960,
    )

    # Synthetic perceived heat
    heat_index = (
        temperature
        + max(0, temperature - 37) * 0.35
        + max(0, humidity - 30) * 0.035
    )

    # Synthetic wet bulb approximation
    wet_bulb = (
        22.8
        + humidity * 0.07
        + max(0, temperature - 35) * 0.10
    )

    return {
        "id": f"tile_{tile_number:03d}",
        "latitude": round(latitude, 6),
        "longitude": round(longitude, 6),
        "temperature": round(
            temperature,
            1,
        ),
        "humidity": round(
            humidity,
            1,
        ),
        "heat_index": round(
            heat_index,
            1,
        ),
        "wet_bulb": round(
            wet_bulb,
            1,
        ),
        "solar_radiation": round(
            solar_radiation,
            1,
        ),
    }


def main():
    tiles = []

    tile_number = 1

    for row in range(ROWS):
        for col in range(COLS):

            tile = generate_tile(
                row,
                col,
                tile_number,
            )

            tiles.append(tile)

            tile_number += 1

    temperatures = [
        tile["temperature"]
        for tile in tiles
    ]

    heatmap = {
        "location": {
            "city": "Phoenix",
            "state": "Arizona",
            "country": "USA",
        },

        "generated_at":
            "2026-08-28T13:00:00Z",

        "statistics": {
            "temperature_min": round(
                min(temperatures),
                1,
            ),

            "temperature_max": round(
                max(temperatures),
                1,
            ),

            "temperature_mean": round(
                mean(temperatures),
                1,
            ),
        },

        "tiles": tiles,
    }

    output_path = (
        Path(__file__).resolve().parents[1]
        / "demo_data"
        / "phoenix_heatmap.json"
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with open(
        output_path,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            heatmap,
            file,
            indent=2,
        )

    print(
        f"Generated {len(tiles)} heat tiles."
    )

    print(
        f"Temperature range: "
        f"{min(temperatures):.1f}°C "
        f"to {max(temperatures):.1f}°C"
    )

    print(
        f"Mean temperature: "
        f"{mean(temperatures):.1f}°C"
    )

    print(
        f"Saved to: {output_path}"
    )


if __name__ == "__main__":
    main()