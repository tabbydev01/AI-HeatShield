from copy import deepcopy

from app.schemas.heatmap import HeatTile
from app.schemas.historical import (
    HistoricalComparison,
    HistoricalPoint,
)
from app.services.risk_service import risk_service


class HistoricalService:
    def compare(self, tile: HeatTile) -> HistoricalComparison:
        current_risk = risk_service.calculate_risk(tile)

        baseline_tile = self._build_baseline_tile(tile)
        baseline_risk = risk_service.calculate_risk(baseline_tile)

        history = self._build_history(tile)

        temperature_difference = round(
            tile.temperature - baseline_tile.temperature,
            1,
        )

        heat_index_difference = round(
            tile.heat_index - baseline_tile.heat_index,
            1,
        )

        risk_difference = round(
            current_risk.risk_score - baseline_risk.risk_score,
            1,
        )

        return HistoricalComparison(
            tile_id=tile.id,

            current_temperature=tile.temperature,
            baseline_temperature=baseline_tile.temperature,
            temperature_difference=temperature_difference,

            current_heat_index=tile.heat_index,
            baseline_heat_index=baseline_tile.heat_index,
            heat_index_difference=heat_index_difference,

            current_risk_score=current_risk.risk_score,
            baseline_risk_score=baseline_risk.risk_score,
            risk_difference=risk_difference,

            trend=self._get_trend(
                temperature_difference,
                heat_index_difference,
                risk_difference,
            ),

            history=history,
        )

    def _build_baseline_tile(
        self,
        tile: HeatTile,
    ) -> HeatTile:
        baseline = deepcopy(tile)

        baseline.temperature = round(
            max(tile.temperature - 2.4, 0),
            1,
        )

        baseline.heat_index = round(
            max(tile.heat_index - 2.8, 0),
            1,
        )

        baseline.wet_bulb = round(
            max(tile.wet_bulb - 0.7, 0),
            1,
        )

        baseline.solar_radiation = round(
            max(tile.solar_radiation * 0.88, 0),
            1,
        )

        baseline.humidity = round(
            min(tile.humidity + 1.5, 100),
            1,
        )

        return baseline

    def _build_history(
        self,
        tile: HeatTile,
    ) -> list[HistoricalPoint]:
        history_config = [
            {
                "label": "4 weeks ago",
                "temperature_delta": -3.1,
                "heat_index_delta": -3.5,
                "solar_multiplier": 0.82,
            },
            {
                "label": "3 weeks ago",
                "temperature_delta": -2.7,
                "heat_index_delta": -3.0,
                "solar_multiplier": 0.85,
            },
            {
                "label": "2 weeks ago",
                "temperature_delta": -2.0,
                "heat_index_delta": -2.3,
                "solar_multiplier": 0.89,
            },
            {
                "label": "1 week ago",
                "temperature_delta": -1.3,
                "heat_index_delta": -1.5,
                "solar_multiplier": 0.93,
            },
            {
                "label": "Current",
                "temperature_delta": 0.0,
                "heat_index_delta": 0.0,
                "solar_multiplier": 1.0,
            },
        ]

        history: list[HistoricalPoint] = []

        for config in history_config:
            historical_tile = deepcopy(tile)

            historical_tile.temperature = round(
                max(
                    tile.temperature
                    + config["temperature_delta"],
                    0,
                ),
                1,
            )

            historical_tile.heat_index = round(
                max(
                    tile.heat_index
                    + config["heat_index_delta"],
                    0,
                ),
                1,
            )

            historical_tile.solar_radiation = round(
                max(
                    tile.solar_radiation
                    * config["solar_multiplier"],
                    0,
                ),
                1,
            )

            risk = risk_service.calculate_risk(
                historical_tile,
            )

            history.append(
                HistoricalPoint(
                    label=config["label"],
                    temperature=historical_tile.temperature,
                    heat_index=historical_tile.heat_index,
                    risk_score=risk.risk_score,
                )
            )

        return history

    @staticmethod
    def _get_trend(
        temperature_difference: float,
        heat_index_difference: float,
        risk_difference: float,
    ) -> str:
        if (
            temperature_difference >= 2
            or heat_index_difference >= 2
            or risk_difference >= 8
        ):
            return "WARMING"

        if (
            temperature_difference <= -2
            or heat_index_difference <= -2
            or risk_difference <= -8
        ):
            return "COOLING"

        return "STABLE"


historical_service = HistoricalService()