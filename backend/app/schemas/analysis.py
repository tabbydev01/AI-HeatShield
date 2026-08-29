from pydantic import BaseModel

from app.schemas.forecast import ForecastPoint
from app.schemas.historical import HistoricalComparison
from app.schemas.hotspot import HotspotResult
from app.schemas.intervention import InterventionResult
from app.schemas.recommendation import Recommendation
from app.schemas.risk import RiskFactor
from app.schemas.vulnerability import VulnerabilityResponse


class MapTile(BaseModel):
    tile_id: str
    latitude: float
    longitude: float
    temperature: float
    humidity: float
    heat_index: float
    wet_bulb: float
    solar_radiation: float
    risk_score: float
    risk_level: str


class SelectedZoneAnalysis(BaseModel):
    tile_id: str
    latitude: float
    longitude: float
    temperature: float
    humidity: float
    heat_index: float
    wet_bulb: float
    solar_radiation: float

    risk_score: float
    risk_level: str

    primary_driver: str
    secondary_driver: str

    factors: list[RiskFactor]
    recommendations: list[Recommendation]
    interventions: list[InterventionResult]
    forecast: list[ForecastPoint]

    historical: HistoricalComparison
    vulnerability: VulnerabilityResponse


class AnalysisResponse(BaseModel):
    project: str
    mode: str
    location: dict
    statistics: dict

    # Fast-first cache/refresh metadata. Optional defaults preserve backwards
    # compatibility with any older frontend or saved API response.
    refreshing: bool = False
    needs_refresh: bool = False
    data_generated_at: str | None = None
    forecast_status: str = "UNAVAILABLE"

    selected_zone: SelectedZoneAnalysis
    map_tiles: list[MapTile]
    hotspots: list[HotspotResult]
