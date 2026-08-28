from pydantic import BaseModel


class HeatTile(BaseModel):
    id: str
    latitude: float
    longitude: float
    temperature: float
    humidity: float
    heat_index: float
    wet_bulb: float
    solar_radiation: float


class HeatmapStatistics(BaseModel):
    temperature_min: float
    temperature_max: float
    temperature_mean: float


class HeatmapResponse(BaseModel):
    location: dict
    generated_at: str
    statistics: HeatmapStatistics
    tiles: list[HeatTile]