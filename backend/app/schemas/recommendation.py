from pydantic import BaseModel


class Recommendation(BaseModel):
    priority: int
    category: str
    title: str
    action: str
    reason: str


class RecommendationResponse(BaseModel):
    tile_id: str
    risk_score: float
    risk_level: str
    primary_driver: str
    secondary_driver: str
    recommendations: list[Recommendation]