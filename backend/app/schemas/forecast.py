from pydantic import BaseModel


class ForecastPoint(BaseModel):
    hours_ahead: int
    temperature: float
    heat_index: float
    solar_radiation: float
    risk_score: float
    risk_level: str


class ForecastResponse(BaseModel):
    tile_id: str
    forecast: list[ForecastPoint]
