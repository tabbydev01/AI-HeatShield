from fastapi import APIRouter, Query

from app.schemas.analysis import AnalysisResponse, MapTile, SelectedZoneAnalysis
from app.schemas.hotspot import HotspotResult
from app.services.forecast_service import forecast_service
from app.services.fortyguard_service import fortyguard_service
from app.services.historical_service import historical_service
from app.services.intervention_service import intervention_service
from app.services.recommendation_service import recommendation_service
from app.services.risk_service import risk_service
from app.services.vulnerability_service import vulnerability_service


router = APIRouter(prefix="/api")


@router.get("/health")
def health() -> dict:
    return {
        "status": "healthy",
        "source": fortyguard_service.get_source(),
        "refreshing": fortyguard_service.is_refreshing(),
        "needs_refresh": fortyguard_service.needs_refresh(),
    }


@router.get("/analyze", response_model=AnalysisResponse)
async def analyze(
    tile_id: str | None = Query(default=None),
) -> AnalysisResponse:
    """
    Fast read endpoint.

    This endpoint never starts a new FortyGuard or Open-Meteo network request.
    It analyzes the newest RAM/persisted snapshot, so initial dashboard reads,
    heat-cell selection and hotspot selection remain fast.
    """
    heatmap = fortyguard_service.get_cached_heatmap()

    if not heatmap.tiles:
        raise RuntimeError("No heatmap tiles are available for analysis.")

    risk_by_tile = {
        tile.id: risk_service.calculate_risk(tile)
        for tile in heatmap.tiles
    }

    selected_tile = None

    if tile_id:
        selected_tile = next(
            (
                tile
                for tile in heatmap.tiles
                if tile.id == tile_id
            ),
            None,
        )

    if selected_tile is None:
        selected_tile = max(
            heatmap.tiles,
            key=lambda tile: risk_by_tile[tile.id].risk_score,
        )

    selected_risk = risk_by_tile[selected_tile.id]

    recommendation_result = recommendation_service.generate(
        selected_tile
    )
    intervention_result = intervention_service.simulate(
        selected_tile
    )
    historical_result = historical_service.compare(
        selected_tile
    )
    vulnerability_result = vulnerability_service.analyze(
        selected_tile
    )
    forecast_result = await forecast_service.generate_forecast(
        selected_tile
    )

    ranked_tiles = sorted(
        heatmap.tiles,
        key=lambda tile: risk_by_tile[tile.id].risk_score,
        reverse=True,
    )

    hotspots = [
        HotspotResult(
            rank=index,
            tile_id=tile.id,
            latitude=tile.latitude,
            longitude=tile.longitude,
            temperature=tile.temperature,
            risk_score=risk_by_tile[tile.id].risk_score,
            risk_level=risk_by_tile[tile.id].risk_level,
            factors=risk_by_tile[tile.id].factors,
        )
        for index, tile in enumerate(
            ranked_tiles[:3],
            start=1,
        )
    ]

    map_tiles = [
        MapTile(
            tile_id=tile.id,
            latitude=tile.latitude,
            longitude=tile.longitude,
            temperature=tile.temperature,
            humidity=tile.humidity,
            heat_index=tile.heat_index,
            wet_bulb=tile.wet_bulb,
            solar_radiation=tile.solar_radiation,
            risk_score=risk_by_tile[tile.id].risk_score,
            risk_level=risk_by_tile[tile.id].risk_level,
        )
        for tile in heatmap.tiles
    ]

    return AnalysisResponse(
        project="AI HeatShield",
        mode=fortyguard_service.get_source(),
        location=heatmap.location,
        statistics=heatmap.statistics.model_dump(),
        refreshing=fortyguard_service.is_refreshing(),
        needs_refresh=fortyguard_service.needs_refresh(),
        data_generated_at=fortyguard_service.get_data_generated_at(),
        forecast_status=fortyguard_service.get_forecast_status(),
        selected_zone=SelectedZoneAnalysis(
            tile_id=selected_tile.id,
            latitude=selected_tile.latitude,
            longitude=selected_tile.longitude,
            temperature=selected_tile.temperature,
            humidity=selected_tile.humidity,
            heat_index=selected_tile.heat_index,
            wet_bulb=selected_tile.wet_bulb,
            solar_radiation=selected_tile.solar_radiation,
            risk_score=selected_risk.risk_score,
            risk_level=selected_risk.risk_level,
            primary_driver=recommendation_result.primary_driver,
            secondary_driver=recommendation_result.secondary_driver,
            factors=selected_risk.factors,
            recommendations=recommendation_result.recommendations,
            interventions=intervention_result.simulations,
            forecast=forecast_result.forecast,
            historical=historical_result,
            vulnerability=vulnerability_result,
        ),
        map_tiles=map_tiles,
        hotspots=hotspots,
    )


@router.post("/refresh")
async def refresh(
    force: bool = Query(default=False),
) -> dict:
    """
    Refresh only the current FortyGuard heatmap.

    Forecast generation is intentionally handled by /refresh-forecasts so the
    production deployment does not depend on detached asyncio background tasks.
    """
    result = await fortyguard_service.refresh_all(
        force=force
    )

    return {
        **result,
        "needs_refresh": fortyguard_service.needs_refresh(),
        "forecast_status": fortyguard_service.get_forecast_status(),
        "data_generated_at": fortyguard_service.get_data_generated_at(),
    }


@router.post("/refresh-forecasts")
async def refresh_forecasts(
    force: bool = Query(default=False),
) -> dict:
    """
    Explicitly refresh +3h/+6h/+9h/+12h FortyGuard forecast heatmaps.

    This request stays alive until the forecast batch completes. That makes the
    flow reliable on production/serverless-style deployments where detached
    asyncio tasks may be cancelled after the original request finishes.
    """
    result = await fortyguard_service.refresh_forecasts(
        force=force
    )

    return {
        **result,
        "needs_refresh": fortyguard_service.needs_refresh(),
        "forecast_status": fortyguard_service.get_forecast_status(),
        "data_generated_at": fortyguard_service.get_data_generated_at(),
    }
