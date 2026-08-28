from pydantic import BaseModel


class RiskFactor(BaseModel):
    name: str
    contribution: float


class HeatRiskResult(BaseModel):
    tile_id: str
    risk_score: float
    risk_level: str
    factors: list[RiskFactor]