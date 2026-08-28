from app.schemas.heatmap import HeatmapResponse
from app.schemas.hotspot import HotspotResult
from app.services.risk_service import risk_service


class HotspotService:
    def detect_hotspots(
        self,
        heatmap: HeatmapResponse,
        limit: int = 3,
    ) -> list[HotspotResult]:

        ranked_tiles = []

        for tile in heatmap.tiles:
            risk = risk_service.calculate_risk(tile)

            ranked_tiles.append(
                {
                    "tile": tile,
                    "risk": risk,
                }
            )

        ranked_tiles.sort(
            key=lambda item: item["risk"].risk_score,
            reverse=True,
        )

        hotspots = []

        for rank, item in enumerate(ranked_tiles[:limit], start=1):
            tile = item["tile"]
            risk = item["risk"]

            hotspots.append(
                HotspotResult(
                    rank=rank,
                    tile_id=tile.id,
                    latitude=tile.latitude,
                    longitude=tile.longitude,
                    temperature=tile.temperature,
                    risk_score=risk.risk_score,
                    risk_level=risk.risk_level,
                    factors=risk.factors,
                )
            )

        return hotspots


hotspot_service = HotspotService()