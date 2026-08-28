from pydantic import BaseModel


class InterventionResult(BaseModel):
    name: str
    before_score: float
    after_score: float
    reduction_points: float
    reduction_percent: float


class InterventionSimulationResponse(BaseModel):
    tile_id: str
    original_risk_level: str
    simulations: list[InterventionResult]