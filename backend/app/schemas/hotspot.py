from pydantic import BaseModel

from app.schemas.risk import RiskFactor


class HotspotResult(BaseModel):
    rank: int
    tile_id: str
    latitude: float
    longitude: float
    temperature: float
    risk_score: float
    risk_level: str
    factors: list[RiskFactor]