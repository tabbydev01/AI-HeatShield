from copy import deepcopy

from app.schemas.heatmap import HeatTile
from app.schemas.intervention import (
    InterventionResult,
    InterventionSimulationResponse,
)
from app.services.risk_service import risk_service


class InterventionService:
    def simulate(self, tile: HeatTile) -> InterventionSimulationResponse:
        original_risk = risk_service.calculate_risk(tile)

        simulations = [
            self._simulate_shade(tile, original_risk.risk_score),
            self._simulate_tree_canopy(tile, original_risk.risk_score),
            self._simulate_cool_surface(tile, original_risk.risk_score),
            self._simulate_combined(tile, original_risk.risk_score),
        ]

        simulations.sort(
            key=lambda item: item.reduction_points,
            reverse=True,
        )

        return InterventionSimulationResponse(
            tile_id=tile.id,
            original_risk_level=original_risk.risk_level,
            simulations=simulations,
        )

    def _simulate_shade(
        self,
        tile: HeatTile,
        before_score: float,
    ) -> InterventionResult:
        modified = deepcopy(tile)

        modified.solar_radiation = max(
            modified.solar_radiation * 0.65,
            0,
        )

        modified.temperature = max(
            modified.temperature - 1.2,
            0,
        )

        return self._build_result(
            "Shade Structures",
            before_score,
            risk_service.calculate_risk(modified).risk_score,
        )

    def _simulate_tree_canopy(
        self,
        tile: HeatTile,
        before_score: float,
    ) -> InterventionResult:
        modified = deepcopy(tile)

        modified.temperature = max(
            modified.temperature - 1.8,
            0,
        )

        modified.solar_radiation = max(
            modified.solar_radiation * 0.75,
            0,
        )

        modified.humidity = min(
            modified.humidity + 2,
            100,
        )

        return self._build_result(
            "Tree Canopy",
            before_score,
            risk_service.calculate_risk(modified).risk_score,
        )

    def _simulate_cool_surface(
        self,
        tile: HeatTile,
        before_score: float,
    ) -> InterventionResult:
        modified = deepcopy(tile)

        modified.temperature = max(
            modified.temperature - 1.4,
            0,
        )

        modified.heat_index = max(
            modified.heat_index - 1.0,
            0,
        )

        return self._build_result(
            "Cool / Reflective Surface",
            before_score,
            risk_service.calculate_risk(modified).risk_score,
        )

    def _simulate_combined(
        self,
        tile: HeatTile,
        before_score: float,
    ) -> InterventionResult:
        modified = deepcopy(tile)

        modified.temperature = max(
            modified.temperature - 2.5,
            0,
        )

        modified.heat_index = max(
            modified.heat_index - 1.5,
            0,
        )

        modified.solar_radiation = max(
            modified.solar_radiation * 0.55,
            0,
        )

        return self._build_result(
            "Combined Cooling Strategy",
            before_score,
            risk_service.calculate_risk(modified).risk_score,
        )

    @staticmethod
    def _build_result(
        name: str,
        before_score: float,
        after_score: float,
    ) -> InterventionResult:
        reduction_points = round(
            before_score - after_score,
            1,
        )

        reduction_percent = round(
            (reduction_points / before_score) * 100,
            1,
        ) if before_score > 0 else 0.0

        return InterventionResult(
            name=name,
            before_score=before_score,
            after_score=after_score,
            reduction_points=reduction_points,
            reduction_percent=reduction_percent,
        )


intervention_service = InterventionService()