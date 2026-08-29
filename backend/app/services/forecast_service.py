from __future__ import annotations

from math import cos, radians

from app.schemas.forecast import ForecastPoint, ForecastResponse
from app.schemas.heatmap import HeatTile, HeatmapResponse
from app.services.fortyguard_service import fortyguard_service
from app.services.risk_service import risk_service


class ForecastService:
    """
    Builds the selected-zone outlook from already-cached FortyGuard forecasts.

    This service intentionally performs no external network I/O. Forecast
    refreshes are handled by FortyGuardService.refresh_all(), so `/api/analyze`
    remains fast for first paint and every tile selection.
    """

    FORECAST_HORIZONS = (3, 6, 9, 12)

    async def generate_forecast(self, tile: HeatTile) -> ForecastResponse:
        points: list[ForecastPoint] = []

        current_risk = risk_service.calculate_risk(tile)
        points.append(
            ForecastPoint(
                hours_ahead=0,
                temperature=round(tile.temperature, 1),
                heat_index=round(tile.heat_index, 1),
                solar_radiation=round(tile.solar_radiation, 1),
                risk_score=current_risk.risk_score,
                risk_level=current_risk.risk_level,
            )
        )

        forecast_heatmaps = fortyguard_service.get_cached_forecast_heatmaps()

        for hours in self.FORECAST_HORIZONS:
            heatmap = forecast_heatmaps.get(hours)
            if heatmap is None:
                continue

            future_tile = self._find_nearest_tile(
                heatmap,
                tile.latitude,
                tile.longitude,
            )
            if future_tile is None:
                continue

            future_risk = risk_service.calculate_risk(future_tile)
            points.append(
                ForecastPoint(
                    hours_ahead=hours,
                    temperature=round(future_tile.temperature, 1),
                    heat_index=round(future_tile.heat_index, 1),
                    solar_radiation=round(future_tile.solar_radiation, 1),
                    risk_score=future_risk.risk_score,
                    risk_level=future_risk.risk_level,
                )
            )

        return ForecastResponse(tile_id=tile.id, forecast=points)

    def _find_nearest_tile(
        self,
        heatmap: HeatmapResponse,
        latitude: float,
        longitude: float,
    ) -> HeatTile | None:
        if not heatmap.tiles:
            return None

        return min(
            heatmap.tiles,
            key=lambda candidate: self._distance_squared(
                latitude,
                longitude,
                candidate.latitude,
                candidate.longitude,
            ),
        )

    @staticmethod
    def _distance_squared(
        latitude_1: float,
        longitude_1: float,
        latitude_2: float,
        longitude_2: float,
    ) -> float:
        mean_latitude = radians((latitude_1 + latitude_2) / 2)
        latitude_delta = latitude_2 - latitude_1
        longitude_delta = (longitude_2 - longitude_1) * cos(mean_latitude)
        return latitude_delta**2 + longitude_delta**2


forecast_service = ForecastService()
