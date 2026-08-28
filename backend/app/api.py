from fastapi import APIRouter, HTTPException

from app.schemas.analysis import (
    AnalysisResponse,
    MapTile,
    SelectedZoneAnalysis,
)
from app.schemas.hotspot import HotspotResult

from app.services.fortyguard_service import fortyguard_service
from app.services.risk_service import risk_service
from app.services.recommendation_service import recommendation_service
from app.services.intervention_service import intervention_service
from app.services.forecast_service import forecast_service
from app.services.historical_service import historical_service
from app.services.vulnerability_service import vulnerability_service


router = APIRouter(
    prefix="/api",
    tags=["AI HeatShield"],
)


# ================================================================
# HEALTH CHECK
# ================================================================

@router.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "AI HeatShield API",
        "data_source": fortyguard_service.get_source(),
    }


# ================================================================
# MAIN ANALYSIS ENDPOINT
# ================================================================

@router.get(
    "/analyze",
    response_model=AnalysisResponse,
)
async def analyze(
    tile_id: str | None = None,
):
    """
    Complete AI HeatShield analysis.

    Returns:
    - heat map
    - heat risk
    - hotspots
    - explainable risk factors
    - recommendations
    - intervention simulations
    - 12-hour forecast
    - historical comparison
    - persona vulnerability analysis

    Data source:
    LIVE
    DEMO
    DEMO_FALLBACK
    """

    # ============================================================
    # LOAD HEATMAP
    # ============================================================

    try:
        heatmap = await fortyguard_service.get_heatmap()

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to load heatmap data: "
                f"{exc}"
            ),
        ) from exc

    if not heatmap.tiles:
        raise HTTPException(
            status_code=500,
            detail="Heatmap contains no tiles.",
        )

    # ============================================================
    # ANALYZE EVERY TILE
    # ============================================================

    analyzed_tiles: list[MapTile] = []

    tile_lookup: dict[str, dict] = {}

    for tile in heatmap.tiles:

        risk = risk_service.calculate_risk(
            tile
        )

        map_tile = MapTile(
            tile_id=tile.id,
            latitude=tile.latitude,
            longitude=tile.longitude,
            temperature=tile.temperature,
            humidity=tile.humidity,
            heat_index=tile.heat_index,
            wet_bulb=tile.wet_bulb,
            solar_radiation=tile.solar_radiation,
            risk_score=risk.risk_score,
            risk_level=risk.risk_level,
        )

        analyzed_tiles.append(
            map_tile
        )

        tile_lookup[
            tile.id
        ] = {
            "tile": tile,
            "risk": risk,
            "map_tile": map_tile,
        }

    # ============================================================
    # SELECT ACTIVE TILE
    # ============================================================

    selected_id = tile_id

    if (
        not selected_id
        or selected_id not in tile_lookup
    ):
        highest_risk_tile = max(
            analyzed_tiles,
            key=lambda item: item.risk_score,
        )

        selected_id = (
            highest_risk_tile.tile_id
        )

    selected_entry = (
        tile_lookup[selected_id]
    )

    selected_tile = (
        selected_entry["tile"]
    )

    selected_risk = (
        selected_entry["risk"]
    )

    # ============================================================
    # RISK DRIVERS
    # ============================================================

    sorted_factors = sorted(
        selected_risk.factors,
        key=lambda factor: factor.contribution,
        reverse=True,
    )

    primary_driver = (
        sorted_factors[0].name
        if len(sorted_factors) >= 1
        else "Unknown"
    )

    secondary_driver = (
        sorted_factors[1].name
        if len(sorted_factors) >= 2
        else "Unknown"
    )

    # ============================================================
    # HOTSPOTS
    # ============================================================

    sorted_entries = sorted(
        tile_lookup.values(),
        key=lambda entry: (
            entry["risk"].risk_score
        ),
        reverse=True,
    )

    top_entries = (
        sorted_entries[:3]
    )

    hotspots: list[
        HotspotResult
    ] = []

    for index, entry in enumerate(
        top_entries
    ):

        hotspot_tile = (
            entry["tile"]
        )

        hotspot_risk = (
            entry["risk"]
        )

        hotspots.append(
            HotspotResult(
                rank=index + 1,

                tile_id=hotspot_tile.id,

                latitude=hotspot_tile.latitude,

                longitude=hotspot_tile.longitude,

                temperature=hotspot_tile.temperature,

                risk_score=hotspot_risk.risk_score,

                risk_level=hotspot_risk.risk_level,

                factors=hotspot_risk.factors,
            )
        )

    # ============================================================
    # RECOMMENDATIONS
    # ============================================================

    recommendation_response = (
        recommendation_service.generate(
            selected_tile
        )
    )

    recommendations = (
        recommendation_response.recommendations
    )

    # ============================================================
    # INTERVENTION SIMULATION
    # ============================================================

    intervention_response = (
        intervention_service.simulate(
            selected_tile
        )
    )

    interventions = (
        intervention_response.simulations
    )

    # ============================================================
    # FORECAST
    # ============================================================

    forecast_response = (
        forecast_service.generate_forecast(
            selected_tile
        )
    )

    forecast = (
        forecast_response.forecast
    )

    # ============================================================
    # HISTORICAL COMPARISON
    # ============================================================

    historical = (
        historical_service.compare(
            selected_tile
        )
    )

    # ============================================================
    # PERSONA / VULNERABILITY INTELLIGENCE
    # ============================================================

    vulnerability = (
        vulnerability_service.analyze(
            selected_tile
        )
    )

    # ============================================================
    # BUILD SELECTED ZONE RESPONSE
    # ============================================================

    selected_zone = (
        SelectedZoneAnalysis(
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

            primary_driver=primary_driver,

            secondary_driver=secondary_driver,

            factors=selected_risk.factors,

            recommendations=recommendations,

            interventions=interventions,

            forecast=forecast,

            historical=historical,

            vulnerability=vulnerability,
        )
    )

    # ============================================================
    # ACTUAL DATA SOURCE
    # ============================================================

    actual_source = (
        fortyguard_service.get_source()
    )

    # ============================================================
    # FINAL RESPONSE
    # ============================================================

    return AnalysisResponse(
        project="AI HeatShield",

        mode=actual_source,

        location=heatmap.location,

        statistics=(
            heatmap.statistics.model_dump()
        ),

        selected_zone=selected_zone,

        map_tiles=analyzed_tiles,

        hotspots=hotspots,
    )