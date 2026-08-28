from app.schemas.heatmap import HeatTile
from app.schemas.risk import HeatRiskResult, RiskFactor


class RiskService:
    def calculate_risk(self, tile: HeatTile) -> HeatRiskResult:
        temperature_score = self._scale(tile.temperature, 30, 46) * 30
        heat_index_score = self._scale(tile.heat_index, 30, 50) * 25
        wet_bulb_score = self._scale(tile.wet_bulb, 20, 32) * 15
        humidity_score = self._scale(tile.humidity, 20, 70) * 10
        solar_score = self._scale(tile.solar_radiation, 300, 1000) * 20

        factors = [
            RiskFactor(name="Temperature", contribution=temperature_score),
            RiskFactor(name="Heat Index", contribution=heat_index_score),
            RiskFactor(name="Wet Bulb", contribution=wet_bulb_score),
            RiskFactor(name="Humidity", contribution=humidity_score),
            RiskFactor(name="Solar Radiation", contribution=solar_score),
        ]

        total_score = sum(f.contribution for f in factors)
        total_score = round(min(max(total_score, 0), 100), 1)

        return HeatRiskResult(
            tile_id=tile.id,
            risk_score=total_score,
            risk_level=self._get_risk_level(total_score),
            factors=factors,
        )

    @staticmethod
    def _scale(value: float, minimum: float, maximum: float) -> float:
        if value <= minimum:
            return 0.0

        if value >= maximum:
            return 1.0

        return (value - minimum) / (maximum - minimum)

    @staticmethod
    def _get_risk_level(score: float) -> str:
        if score < 26:
            return "LOW"

        if score < 51:
            return "MODERATE"

        if score < 71:
            return "HIGH"

        if score < 86:
            return "VERY HIGH"

        return "CRITICAL"


risk_service = RiskService()