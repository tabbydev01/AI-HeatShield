from __future__ import annotations

import asyncio
import time
from datetime import date as date_type
from datetime import datetime
from typing import Any, Iterable

import httpx


class WeatherService:
    """
    Open-Meteo environmental context adapter.

    FortyGuard remains the primary hyperlocal temperature source.
    Open-Meteo is used only for contextual variables such as humidity,
    wet-bulb temperature, apparent temperature and solar radiation.

    The service caches results by location/date/hour and can fetch several
    requested hours with one Open-Meteo request per calendar date. This keeps
    FortyGuard forecast refreshes from creating one weather request per horizon.
    """

    ARCHIVE_BASE_URL = "https://archive-api.open-meteo.com/v1/archive"
    FORECAST_BASE_URL = "https://api.open-meteo.com/v1/forecast"

    DEFAULT_LATITUDE = 40.712336
    DEFAULT_LONGITUDE = -74.010329
    DEFAULT_TIMEZONE = "America/New_York"

    HOURLY_VARIABLES = [
        "temperature_2m",
        "relative_humidity_2m",
        "wet_bulb_temperature_2m",
        "apparent_temperature",
        "shortwave_radiation",
    ]

    CACHE_TTL_SECONDS = 30 * 60

    def __init__(self) -> None:
        self.last_error: str | None = None
        self._cache: dict[tuple[float, float, str, int], dict[str, Any]] = {}
        self._cache_created_at: dict[tuple[float, float, str, int], float] = {}
        self._lock = asyncio.Lock()

    async def get_environmental_data(
        self,
        latitude: float | None = None,
        longitude: float | None = None,
        date: str | None = None,
        hour: int | None = None,
        force_refresh: bool = False,
    ) -> dict[str, Any]:
        """Return contextual environmental data for one NYC-local hour."""
        lat = latitude if latitude is not None else self.DEFAULT_LATITUDE
        lon = longitude if longitude is not None else self.DEFAULT_LONGITUDE

        now_nyc = self._get_nyc_now()
        target_date = date if date is not None else now_nyc.strftime("%Y-%m-%d")
        target_hour = hour if hour is not None else now_nyc.hour

        self._validate_date(target_date)
        self._validate_hour(target_hour)

        key = self._cache_key(lat, lon, target_date, target_hour)
        if not force_refresh and self._cache_is_valid(key):
            return self._cache[key]

        target = now_nyc.replace(
            year=int(target_date[0:4]),
            month=int(target_date[5:7]),
            day=int(target_date[8:10]),
            hour=target_hour,
            minute=0,
            second=0,
            microsecond=0,
        )

        results = await self.get_environmental_batch(
            [target],
            latitude=lat,
            longitude=lon,
            force_refresh=force_refresh,
        )

        value = results.get(target)
        if value is None:
            raise RuntimeError(
                f"Open-Meteo did not return environmental data for "
                f"{target_date} {target_hour:02d}:00."
            )
        return value

    async def get_environmental_batch(
        self,
        target_times: Iterable[datetime],
        latitude: float | None = None,
        longitude: float | None = None,
        force_refresh: bool = False,
    ) -> dict[datetime, dict[str, Any]]:
        """
        Fetch environmental context for several target hours efficiently.

        Requested hours are grouped by calendar date. Each date needs one
        Open-Meteo request because the response already contains all 24 hourly
        values. When a +12h outlook crosses midnight, the two date requests run
        concurrently instead of serially.

        Cache entries are still hour-specific so callers keep the same contract.
        """
        lat = latitude if latitude is not None else self.DEFAULT_LATITUDE
        lon = longitude if longitude is not None else self.DEFAULT_LONGITUDE

        targets = [self._normalize_target_time(value) for value in target_times]
        if not targets:
            return {}

        results: dict[datetime, dict[str, Any]] = {}
        missing_by_date: dict[str, list[datetime]] = {}

        for target in targets:
            target_date = target.strftime("%Y-%m-%d")
            key = self._cache_key(
                lat,
                lon,
                target_date,
                target.hour,
            )

            if not force_refresh and self._cache_is_valid(key):
                results[target] = self._cache[key]
            else:
                missing_by_date.setdefault(target_date, []).append(target)

        if not missing_by_date:
            return results

        async with self._lock:
            # Another refresh may have populated the cache while this caller
            # waited for the lock.
            pending_by_date: dict[str, list[datetime]] = {}

            for target_date, date_targets in missing_by_date.items():
                for target in date_targets:
                    key = self._cache_key(
                        lat,
                        lon,
                        target_date,
                        target.hour,
                    )

                    if not force_refresh and self._cache_is_valid(key):
                        results[target] = self._cache[key]
                    else:
                        pending_by_date.setdefault(
                            target_date,
                            [],
                        ).append(target)

            if not pending_by_date:
                return results

            now_nyc = self._get_nyc_now().replace(
                minute=0,
                second=0,
                microsecond=0,
            )
            timeout = httpx.Timeout(
                connect=10.0,
                read=30.0,
                write=10.0,
                pool=10.0,
            )
            limits = httpx.Limits(
                max_connections=4,
                max_keepalive_connections=2,
                keepalive_expiry=30.0,
            )

            async with httpx.AsyncClient(
                timeout=timeout,
                limits=limits,
            ) as client:

                async def fetch_date(
                    target_date: str,
                    date_targets: list[datetime],
                ) -> tuple[str, list[datetime], dict[str, Any] | None]:
                    first_target = min(date_targets)
                    source_type = (
                        "historical_reanalysis"
                        if first_target < now_nyc
                        else "forecast_model"
                    )
                    base_url = (
                        self.ARCHIVE_BASE_URL
                        if source_type == "historical_reanalysis"
                        else self.FORECAST_BASE_URL
                    )

                    params = self._build_params(
                        latitude=lat,
                        longitude=lon,
                        target_date=target_date,
                    )

                    try:
                        payload = await self._request(
                            client,
                            base_url,
                            params,
                        )
                        return target_date, date_targets, payload
                    except Exception as exc:
                        self.last_error = (
                            f"Open-Meteo request failed for {target_date}: {exc}"
                        )
                        return target_date, date_targets, None

                date_payloads = await asyncio.gather(
                    *(
                        fetch_date(target_date, date_targets)
                        for target_date, date_targets in pending_by_date.items()
                    )
                )

                for target_date, date_targets, payload in date_payloads:
                    if payload is None:
                        continue

                    for target in date_targets:
                        try:
                            value = self._extract_hour(
                                payload=payload,
                                target_date=target_date,
                                target_hour=target.hour,
                                requested_latitude=lat,
                                requested_longitude=lon,
                                source_type=(
                                    "historical_reanalysis"
                                    if target < now_nyc
                                    else "forecast_model"
                                ),
                            )
                        except Exception as exc:
                            self.last_error = (
                                f"Open-Meteo processing failed: {exc}"
                            )
                            continue

                        key = self._cache_key(
                            lat,
                            lon,
                            target_date,
                            target.hour,
                        )
                        self._cache[key] = value
                        self._cache_created_at[key] = time.monotonic()
                        results[target] = value

            if len(results) == len(targets):
                self.last_error = None

        return results

    async def _request(
        self,
        client: httpx.AsyncClient,
        base_url: str,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        response = await client.get(base_url, params=params)
        response.raise_for_status()
        return response.json()

    def _build_params(
        self,
        latitude: float,
        longitude: float,
        target_date: str,
    ) -> dict[str, Any]:
        return {
            "latitude": latitude,
            "longitude": longitude,
            "start_date": target_date,
            "end_date": target_date,
            "hourly": ",".join(self.HOURLY_VARIABLES),
            "temperature_unit": "celsius",
            "timezone": self.DEFAULT_TIMEZONE,
        }

    def _extract_hour(
        self,
        payload: dict[str, Any],
        target_date: str,
        target_hour: int,
        requested_latitude: float,
        requested_longitude: float,
        source_type: str,
    ) -> dict[str, Any]:
        hourly = payload.get("hourly")
        if not isinstance(hourly, dict):
            raise ValueError("Open-Meteo response does not contain hourly data.")

        times = hourly.get("time")
        if not isinstance(times, list):
            raise ValueError("Open-Meteo hourly response does not contain a time array.")

        target_time = f"{target_date}T{target_hour:02d}:00"
        try:
            index = times.index(target_time)
        except ValueError as exc:
            raise ValueError(
                f"Requested hour {target_time} was not found in Open-Meteo response."
            ) from exc

        return {
            "source": "OPEN_METEO",
            "source_type": source_type,
            "requested_location": {
                "latitude": round(requested_latitude, 6),
                "longitude": round(requested_longitude, 6),
            },
            "model_location": {
                "latitude": payload.get("latitude"),
                "longitude": payload.get("longitude"),
                "elevation": payload.get("elevation"),
            },
            "timezone": payload.get("timezone", self.DEFAULT_TIMEZONE),
            "date_time": target_time,
            "temperature": self._round(self._value_at(hourly, "temperature_2m", index)),
            "humidity": self._round(
                self._value_at(hourly, "relative_humidity_2m", index)
            ),
            "wet_bulb": self._round(
                self._value_at(hourly, "wet_bulb_temperature_2m", index)
            ),
            "apparent_temperature": self._round(
                self._value_at(hourly, "apparent_temperature", index)
            ),
            "solar_radiation": self._round(
                self._value_at(hourly, "shortwave_radiation", index)
            ),
            "units": {
                "temperature": "°C",
                "humidity": "%",
                "wet_bulb": "°C",
                "apparent_temperature": "°C",
                "solar_radiation": "W/m²",
            },
        }

    def _cache_is_valid(self, key: tuple[float, float, str, int]) -> bool:
        created_at = self._cache_created_at.get(key)
        if key not in self._cache or created_at is None:
            return False
        return (time.monotonic() - created_at) < self.CACHE_TTL_SECONDS

    @staticmethod
    def _cache_key(
        latitude: float,
        longitude: float,
        target_date: str,
        target_hour: int,
    ) -> tuple[float, float, str, int]:
        return (round(latitude, 5), round(longitude, 5), target_date, target_hour)

    @staticmethod
    def _normalize_target_time(value: datetime) -> datetime:
        if value.tzinfo is None:
            from zoneinfo import ZoneInfo

            return value.replace(tzinfo=ZoneInfo("America/New_York"))
        return value

    @staticmethod
    def _get_nyc_now() -> datetime:
        try:
            from zoneinfo import ZoneInfo

            return datetime.now(ZoneInfo("America/New_York"))
        except Exception as exc:
            raise RuntimeError(
                "Unable to load America/New_York timezone. Install the tzdata package."
            ) from exc

    @staticmethod
    def _validate_date(value: str) -> None:
        try:
            date_type.fromisoformat(value)
        except ValueError as exc:
            raise ValueError("date must use YYYY-MM-DD format.") from exc

    @staticmethod
    def _validate_hour(value: int) -> None:
        if value < 0 or value > 23:
            raise ValueError("hour must be between 0 and 23.")

    @staticmethod
    def _value_at(
        hourly: dict[str, Any],
        key: str,
        index: int,
    ) -> float | None:
        values = hourly.get(key)
        if not isinstance(values, list) or index >= len(values):
            return None

        value = values[index]
        if value is None:
            return None

        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _round(value: float | None, digits: int = 2) -> float | None:
        if value is None:
            return None
        return round(value, digits)


weather_service = WeatherService()
