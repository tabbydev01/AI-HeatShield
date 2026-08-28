from copy import deepcopy

from app.schemas.forecast import ForecastPoint, ForecastResponse
from app.schemas.heatmap import HeatTile
from app.services.risk_service import risk_service


class ForecastService:
    def generate_forecast(self, tile: HeatTile) -> ForecastResponse:
        forecast_config = [
            {
                "hours": 0,
                "temp_delta": 0.0,
                "heat_index_delta": 0.0,
                "solar_multiplier": 1.00,
            },
            {
                "hours": 3,
                "temp_delta": 1.1,
                "heat_index_delta": 1.4,
                "solar_multiplier": 1.05,
            },
            {
                "hours": 6,
                "temp_delta": 0.6,
                "heat_index_delta": 0.9,
                "solar_multiplier": 0.90,
            },
            {
                "hours": 9,
                "temp_delta": -1.5,
                "heat_index_delta": -1.3,
                "solar_multiplier": 0.55,
            },
            {
                "hours": 12,
                "temp_delta": -3.2,
                "heat_index_delta": -2.8,
                "solar_multiplier": 0.20,
            },
        ]

        points = []

        for config in forecast_config:
            modified = deepcopy(tile)

            modified.temperature = max(
                modified.temperature + config["temp_delta"],
                0,
            )

            modified.heat_index = max(
                modified.heat_index + config["heat_index_delta"],
                0,
            )

            modified.solar_radiation = max(
                modified.solar_radiation
                * config["solar_multiplier"],
                0,
            )

            risk = risk_service.calculate_risk(modified)

            points.append(
                ForecastPoint(
                    hours_ahead=config["hours"],
                    temperature=round(modified.temperature, 1),
                    heat_index=round(modified.heat_index, 1),
                    solar_radiation=round(modified.solar_radiation, 1),
                    risk_score=risk.risk_score,
                    risk_level=risk.risk_level,
                )
            )

        return ForecastResponse(
            tile_id=tile.id,
            forecast=points,
        )


forecast_service = ForecastService()