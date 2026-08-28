from app.schemas.heatmap import HeatTile
from app.schemas.recommendation import (
    Recommendation,
    RecommendationResponse,
)
from app.services.risk_service import risk_service


class RecommendationService:
    def generate(self, tile: HeatTile) -> RecommendationResponse:
        risk = risk_service.calculate_risk(tile)

        sorted_factors = sorted(
            risk.factors,
            key=lambda factor: factor.contribution,
            reverse=True,
        )

        primary_driver = sorted_factors[0].name
        secondary_driver = sorted_factors[1].name

        recommendations = []

        if risk.risk_score >= 86:
            recommendations.append(
                Recommendation(
                    priority=1,
                    category="Human Safety",
                    title="Restrict peak-hour outdoor exposure",
                    action="Reduce non-essential outdoor activity during the hottest hours.",
                    reason="The selected area is currently classified as CRITICAL heat risk.",
                )
            )

        if tile.solar_radiation >= 800:
            recommendations.append(
                Recommendation(
                    priority=2,
                    category="Urban Design",
                    title="Increase temporary or permanent shade",
                    action="Deploy shade structures or increase tree canopy in exposed pedestrian areas.",
                    reason="High solar radiation is significantly increasing local heat exposure.",
                )
            )

        if tile.temperature >= 40:
            recommendations.append(
                Recommendation(
                    priority=3,
                    category="Hydration",
                    title="Deploy hydration points",
                    action="Provide accessible drinking-water or hydration stations in the hotspot.",
                    reason="Extreme temperature increases dehydration and heat-stress risk.",
                )
            )

        if tile.wet_bulb >= 26:
            recommendations.append(
                Recommendation(
                    priority=4,
                    category="Health",
                    title="Protect vulnerable populations",
                    action="Prioritize elderly people, children, outdoor workers, and people with limited cooling access.",
                    reason="Elevated wet-bulb conditions increase physiological heat stress.",
                )
            )

        if risk.risk_score >= 70:
            recommendations.append(
                Recommendation(
                    priority=5,
                    category="Operations",
                    title="Adjust outdoor work schedules",
                    action="Move strenuous outdoor work to cooler morning or evening periods.",
                    reason="Sustained high heat risk can make prolonged outdoor exposure unsafe.",
                )
            )

        if not recommendations:
            recommendations.append(
                Recommendation(
                    priority=1,
                    category="Monitoring",
                    title="Continue monitoring",
                    action="Track temperature and risk conditions for meaningful changes.",
                    reason="Current conditions do not require major intervention.",
                )
            )

        recommendations.sort(key=lambda item: item.priority)

        return RecommendationResponse(
            tile_id=tile.id,
            risk_score=risk.risk_score,
            risk_level=risk.risk_level,
            primary_driver=primary_driver,
            secondary_driver=secondary_driver,
            recommendations=recommendations,
        )


recommendation_service = RecommendationService()