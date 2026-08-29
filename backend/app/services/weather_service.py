from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx


class WeatherService:
    """
    Environmental weather context for AI HeatShield.

    FortyGuard remains the primary source for hyperlocal temperature.

    Open-Meteo is used only for environmental variables that are not
    available in the current FortyGuard TCM heatmap response:
    - Relative humidity
    - Wet-bulb temperature
    - Solar radiation
    - Apparent temperature

    Historical demo alignment:
    New York City
    2024-07-15 at 14:00 America/New_York
    """

    BASE_URL = "https://archive-api.open-meteo.com/v1/archive"

    DEFAULT_LATITUDE = 40.712336
    DEFAULT_LONGITUDE = -74.010329

    DEFAULT_DATE = "2024-07-15"
    DEFAULT_HOUR = 14

    DEFAULT_TIMEZONE = "America/New_York"

    def __init__(self) -> None:
        self.last_error: str | None = None

    async def get_environmental_data(
        self,
        latitude: float | None = None,
        longitude: float | None = None,
        date: str | None = None,
        hour: int | None = None,
    ) -> dict[str, Any]:
        """
        Fetch environmental context from Open-Meteo.

        Returns values for one requested hour.

        The returned data is contextual weather-model/reanalysis data.
        It must not be described as FortyGuard hyperlocal measurements.
        """

        lat = (
            latitude
            if latitude is not None
            else self.DEFAULT_LATITUDE
        )

        lon = (
            longitude
            if longitude is not None
            else self.DEFAULT_LONGITUDE
        )

        target_date = (
            date
            if date is not None
            else self.DEFAULT_DATE
        )

        target_hour = (
            hour
            if hour is not None
            else self.DEFAULT_HOUR
        )

        if target_hour < 0 or target_hour > 23:
            raise ValueError(
                "hour must be between 0 and 23."
            )

        params = {
            "latitude": lat,
            "longitude": lon,
            "start_date": target_date,
            "end_date": target_date,
            "hourly": ",".join(
                [
                    "temperature_2m",
                    "relative_humidity_2m",
                    "wet_bulb_temperature_2m",
                    "apparent_temperature",
                    "shortwave_radiation",
                ]
            ),
            "temperature_unit": "celsius",
            "timezone": self.DEFAULT_TIMEZONE,
        }

        try:
            timeout = httpx.Timeout(
                connect=10.0,
                read=30.0,
                write=10.0,
                pool=10.0,
            )

            async with httpx.AsyncClient(
                timeout=timeout
            ) as client:
                response = await client.get(
                    self.BASE_URL,
                    params=params,
                )

                response.raise_for_status()

                payload = response.json()

            result = self._extract_hour(
                payload=payload,
                target_date=target_date,
                target_hour=target_hour,
                requested_latitude=lat,
                requested_longitude=lon,
            )

            self.last_error = None

            return result

        except httpx.HTTPStatusError as exc:
            self.last_error = (
                "Open-Meteo HTTP error: "
                f"{exc.response.status_code} "
                f"{exc.response.text[:300]}"
            )
            raise RuntimeError(
                self.last_error
            ) from exc

        except httpx.RequestError as exc:
            self.last_error = (
                "Open-Meteo request error: "
                f"{exc}"
            )
            raise RuntimeError(
                self.last_error
            ) from exc

        except Exception as exc:
            self.last_error = (
                "Open-Meteo processing error: "
                f"{exc}"
            )
            raise

    def _extract_hour(
        self,
        payload: dict[str, Any],
        target_date: str,
        target_hour: int,
        requested_latitude: float,
        requested_longitude: float,
    ) -> dict[str, Any]:
        hourly = payload.get("hourly")

        if not isinstance(hourly, dict):
            raise ValueError(
                "Open-Meteo response does not contain hourly data."
            )

        times = hourly.get("time")

        if not isinstance(times, list):
            raise ValueError(
                "Open-Meteo hourly response does not contain a time array."
            )

        target_time = (
            f"{target_date}T{target_hour:02d}:00"
        )

        try:
            index = times.index(target_time)
        except ValueError as exc:
            raise ValueError(
                f"Requested hour {target_time} "
                "was not found in Open-Meteo response."
            ) from exc

        temperature = self._value_at(
            hourly,
            "temperature_2m",
            index,
        )

        humidity = self._value_at(
            hourly,
            "relative_humidity_2m",
            index,
        )

        wet_bulb = self._value_at(
            hourly,
            "wet_bulb_temperature_2m",
            index,
        )

        apparent_temperature = self._value_at(
            hourly,
            "apparent_temperature",
            index,
        )

        solar_radiation = self._value_at(
            hourly,
            "shortwave_radiation",
            index,
        )

        return {
            "source": "OPEN_METEO",
            "source_type": "historical_reanalysis",
            "requested_location": {
                "latitude": round(
                    requested_latitude,
                    6,
                ),
                "longitude": round(
                    requested_longitude,
                    6,
                ),
            },
            "model_location": {
                "latitude": payload.get(
                    "latitude"
                ),
                "longitude": payload.get(
                    "longitude"
                ),
                "elevation": payload.get(
                    "elevation"
                ),
            },
            "timezone": payload.get(
                "timezone",
                self.DEFAULT_TIMEZONE,
            ),
            "date_time": target_time,
            "temperature": self._round(
                temperature
            ),
            "humidity": self._round(
                humidity
            ),
            "wet_bulb": self._round(
                wet_bulb
            ),
            "apparent_temperature": self._round(
                apparent_temperature
            ),
            "solar_radiation": self._round(
                solar_radiation
            ),
            "units": {
                "temperature": "°C",
                "humidity": "%",
                "wet_bulb": "°C",
                "apparent_temperature": "°C",
                "solar_radiation": "W/m²",
            },
        }

    @staticmethod
    def _value_at(
        hourly: dict[str, Any],
        key: str,
        index: int,
    ) -> float | None:
        values = hourly.get(key)

        if not isinstance(values, list):
            return None

        if index >= len(values):
            return None

        value = values[index]

        if value is None:
            return None

        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _round(
        value: float | None,
        digits: int = 2,
    ) -> float | None:
        if value is None:
            return None

        return round(
            value,
            digits,
        )


weather_service = WeatherService()