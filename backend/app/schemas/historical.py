from pydantic import BaseModel


class HistoricalPoint(BaseModel):
    label: str
    temperature: float
    heat_index: float
    risk_score: float


class HistoricalComparison(BaseModel):
    tile_id: str

    current_temperature: float
    baseline_temperature: float
    temperature_difference: float

    current_heat_index: float
    baseline_heat_index: float
    heat_index_difference: float

    current_risk_score: float
    baseline_risk_score: float
    risk_difference: float

    trend: str

    history: list[HistoricalPoint]