import asyncio
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from app.config import settings
from app.services.weather_service import weather_service
from app.schemas.heatmap import (
    HeatTile,
    HeatmapResponse,
    HeatmapStatistics,
)


class FortyGuardService:
    """
    FortyGuard data adapter for AI HeatShield.

    Data source modes:
    - LIVE          -> Real FortyGuard response
    - DEMO          -> Synthetic local demonstration dataset
    - DEMO_FALLBACK -> Live API was attempted but failed,
                       therefore synthetic demo data was returned

    The service also caches the latest heatmap so clicking multiple
    map cells does not create a new FortyGuard API task each time.
    """

    CACHE_TTL_SECONDS = 15 * 60

    MAX_STATUS_ATTEMPTS = 60
    STATUS_POLL_INTERVAL_SECONDS = 3

    def __init__(self) -> None:
        self.base_url = settings.fortyguard_base_url.rstrip("/")

        self.api_key = (
            settings.fortyguard_api_key.strip()
            if settings.fortyguard_api_key
            else ""
        )

        self.force_demo_mode = bool(settings.demo_mode)

        self.demo_mode = (
            self.force_demo_mode
            or not self.api_key
        )

        self.last_source = (
            "DEMO"
            if self.demo_mode
            else "LIVE"
        )

        self.last_error: str | None = None

        self._cache: HeatmapResponse | None = None
        self._cache_created_at: float | None = None
        self._cache_source: str | None = None

        self._request_lock = asyncio.Lock()

        self.demo_file = (
            Path(__file__).resolve().parents[2]
            / "demo_data"
            / "phoenix_heatmap.json"
        )

    # ============================================================
    # PUBLIC METHODS
    # ============================================================

    async def get_heatmap(
        self,
        force_refresh: bool = False,
    ) -> HeatmapResponse:
        """
        Return the latest heatmap.

        Important:
        - Cached data is reused for 15 minutes.
        - Demo mode never contacts FortyGuard.
        - Live failures automatically fall back to demo data.
        - last_source tells the API/UI exactly where data came from.
        """

        if (
            not force_refresh
            and self._cache_is_valid()
        ):
            self.last_source = (
                self._cache_source
                or "DEMO"
            )

            return self._cache  # type: ignore[return-value]

        async with self._request_lock:

            # Another request may have populated cache while
            # this request was waiting for the lock.
            if (
                not force_refresh
                and self._cache_is_valid()
            ):
                self.last_source = (
                    self._cache_source
                    or "DEMO"
                )

                return self._cache  # type: ignore[return-value]

            # ----------------------------------------------------
            # DEMO MODE
            # ----------------------------------------------------

            if self.demo_mode:
                result = self._load_demo_heatmap()

                self.last_source = "DEMO"
                self.last_error = None

                self._store_cache(
                    result,
                    "DEMO",
                )

                return result

            # ----------------------------------------------------
            # LIVE MODE
            # ----------------------------------------------------

            try:
                result = await self._get_live_heatmap()

                self.last_source = "LIVE"
                self.last_error = None

                self._store_cache(
                    result,
                    "LIVE",
                )

                return result

            except Exception as exc:
                self.last_error = str(exc)

                print(
                    "[AI HeatShield] FortyGuard live request failed. "
                    f"Using demo fallback. Error: {exc}"
                )

                result = self._load_demo_heatmap()

                self.last_source = "DEMO_FALLBACK"

                # Do not cache a failed live request. This allows the
                # next request to retry FortyGuard immediately instead of
                # serving a 15-minute DEMO_FALLBACK cache.
                return result

    def get_source(self) -> str:
        """
        Returns the actual source of the currently served data.
        """

        return self.last_source

    def clear_cache(self) -> None:
        """
        Clear the heatmap cache manually.
        """

        self._cache = None
        self._cache_created_at = None
        self._cache_source = None

    # ============================================================
    # CACHE
    # ============================================================

    def _cache_is_valid(self) -> bool:
        if self._cache is None:
            return False

        if self._cache_created_at is None:
            return False

        age_seconds = (
            time.monotonic()
            - self._cache_created_at
        )

        return (
            age_seconds
            < self.CACHE_TTL_SECONDS
        )

    def _store_cache(
        self,
        heatmap: HeatmapResponse,
        source: str,
    ) -> None:
        self._cache = heatmap
        self._cache_created_at = time.monotonic()
        self._cache_source = source

    # ============================================================
    # LIVE FORTYGUARD API
    # ============================================================

    async def _get_live_heatmap(
        self,
    ) -> HeatmapResponse:
        if not self.api_key:
            raise RuntimeError(
                "FortyGuard API key is missing."
            )

        payload = self._build_heatmap_payload()

        headers = {
            "api-key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        timeout = httpx.Timeout(
            connect=20.0,
            read=60.0,
            write=30.0,
            pool=30.0,
        )

        async with httpx.AsyncClient(
            timeout=timeout,
        ) as client:

            submit_response = await client.post(
                f"{self.base_url}/v1/heatmap",
                headers=headers,
                json=payload,
            )

            if submit_response.status_code >= 400:
                raise RuntimeError(
                    "FortyGuard heatmap request failed "
                    f"with HTTP {submit_response.status_code}: "
                    f"{submit_response.text[:500]}"
                )

            try:
                submit_data = submit_response.json()

            except ValueError as exc:
                raise RuntimeError(
                    "FortyGuard returned invalid JSON "
                    "while submitting heatmap request."
                ) from exc

            activity_id = self._extract_activity_id(
                submit_data
            )

            if not activity_id:
                # Some APIs may return completed data directly.
                if self._contains_heatmap_data(
                    submit_data
                ):
                    environmental_data = await self._get_environmental_context()

                    return self._normalize_live_response(
                        submit_data,
                        environmental_data=environmental_data,
                    )

                raise RuntimeError(
                    "FortyGuard response did not contain "
                    "an activity_id."
                )

            completed_data = await self._poll_activity(
                client=client,
                headers=headers,
                activity_id=activity_id,
            )

            environmental_data = await self._get_environmental_context()

            return self._normalize_live_response(
                completed_data,
                environmental_data=environmental_data,
            )

    async def _get_environmental_context(
        self,
    ) -> dict[str, Any]:
        """
        Fetch environmental context aligned with the deterministic
        FortyGuard NYC historical request.

        FortyGuard remains the source of every tile's hyperlocal
        temperature. Open-Meteo supplies contextual humidity,
        wet-bulb temperature and solar radiation for the same
        location/date/hour.

        If Open-Meteo is temporarily unavailable, FortyGuard data
        still remains usable and the legacy placeholders are retained.
        """

        try:
            return await weather_service.get_environmental_data(
                latitude=40.712336,
                longitude=-74.010329,
                date="2024-07-15",
                hour=14,
            )
        except Exception as exc:
            print(
                "[AI HeatShield] Open-Meteo environmental context "
                f"unavailable. Continuing with FortyGuard only. Error: {exc}"
            )
            return {}

    async def _poll_activity(
        self,
        client: httpx.AsyncClient,
        headers: dict[str, str],
        activity_id: str,
    ) -> dict[str, Any]:
        """
        Poll FortyGuard asynchronous activity until completion.

        A temporary 404 is tolerated because the activity may not
        be immediately visible after submission.
        """

        status_url = (
            f"{self.base_url}/v1/status/{activity_id}"
        )

        last_status = "UNKNOWN"

        for attempt in range(
            self.MAX_STATUS_ATTEMPTS
        ):
            response = await client.get(
                status_url,
                headers=headers,
            )

            # Newly created activity may briefly return 404.
            if response.status_code == 404:
                await asyncio.sleep(
                    self.STATUS_POLL_INTERVAL_SECONDS
                )

                continue

            if response.status_code == 429:
                await asyncio.sleep(
                    self.STATUS_POLL_INTERVAL_SECONDS
                    * 2
                )

                continue

            if response.status_code >= 400:
                raise RuntimeError(
                    "FortyGuard status request failed "
                    f"with HTTP {response.status_code}: "
                    f"{response.text[:500]}"
                )

            try:
                data = response.json()

            except ValueError as exc:
                raise RuntimeError(
                    "FortyGuard status endpoint "
                    "returned invalid JSON."
                ) from exc

            status = self._extract_status(
                data
            )

            last_status = status

            normalized_status = (
                status.strip()
                .upper()
                .replace(" ", "_")
            )

            if normalized_status in {
                "COMPLETED",
                "COMPLETE",
                "SUCCESS",
                "SUCCEEDED",
                "DONE",
            }:
                return data

            if normalized_status in {
                "FAILED",
                "FAILURE",
                "ERROR",
                "CANCELLED",
                "CANCELED",
            }:
                error_message = (
                    data.get("message")
                    or data.get("error")
                    or data.get("detail")
                    or "Unknown FortyGuard error."
                )

                raise RuntimeError(
                    "FortyGuard activity failed: "
                    f"{error_message}"
                )

            await asyncio.sleep(
                self.STATUS_POLL_INTERVAL_SECONDS
            )

        raise TimeoutError(
            "FortyGuard heatmap activity did not "
            "complete in time. "
            f"Last status: {last_status}"
        )

    # ============================================================
    # FORTYGUARD PAYLOAD
    # ============================================================

    def _build_heatmap_payload(
        self,
    ) -> dict[str, Any]:
        """
        Build a deterministic FortyGuard heatmap request using the
        documentation example AOI/time that has already returned real
        heatmap cells during integration testing.
        """

        polygon_geometry = {
            "type": "Polygon",
            "coordinates": [
                [
                    [-74.0170, 40.7050],
                    [-74.0030, 40.7050],
                    [-74.0030, 40.7180],
                    [-74.0170, 40.7180],
                    [-74.0170, 40.7050],
                ]
            ],
        }

        polygon_aoi = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {},
                    "geometry": polygon_geometry,
                }
            ],
        }

        return {
            "polygon_aoi": polygon_aoi,
            "date_time": {
                "start_date": "2024-07-15",
                "start_time": "14:00",
                "filter_type": 1,
            },
            "granularity": 100,
            "analytic_type": "tcm",
        }

    # ============================================================
    # LIVE RESPONSE NORMALIZATION
    # ============================================================

    def _normalize_live_response(
        self,
        raw: dict[str, Any],
        environmental_data: dict[str, Any] | None = None,
    ) -> HeatmapResponse:
        """
        Normalize FortyGuard async/status responses and GeoJSON
        FeatureCollection heatmap cells into HeatmapResponse.
        """

        map_data = self._extract_map_data(raw)
        stats_data = self._extract_stats_data(raw)

        if not map_data:
            raise RuntimeError(
                "FortyGuard completed successfully but no usable "
                "map_data/features were found in the response."
            )

        tiles: list[HeatTile] = []

        environmental_data = environmental_data or {}

        context_humidity = self._to_float(
            environmental_data.get("humidity")
        )
        context_wet_bulb = self._to_float(
            environmental_data.get("wet_bulb")
        )
        context_solar = self._to_float(
            environmental_data.get("solar_radiation")
        )

        for index, item in enumerate(map_data):
            if not isinstance(item, dict):
                continue

            latitude, longitude = self._extract_coordinates(item)
            if latitude is None or longitude is None:
                continue

            temperature = self._extract_number(
                item,
                [
                    "temperature",
                    "temp",
                    "air_temperature",
                    "average_temperature",
                    "temperature_c",
                    "tcm",
                    "value",
                ],
            )

            if temperature is None:
                continue

            humidity = self._extract_number(
                item,
                ["humidity", "relative_humidity", "rh"],
            )
            heat_index = self._extract_number(
                item,
                [
                    "heat_index",
                    "heatindex",
                    "apparent_temperature",
                ],
            )
            wet_bulb = self._extract_number(
                item,
                [
                    "wet_bulb",
                    "wet_bulb_temperature",
                    "wetbulb",
                ],
            )
            solar = self._extract_number(
                item,
                [
                    "solar_radiation",
                    "solar_irradiance",
                    "solar",
                ],
            )

            # FortyGuard values take precedence whenever the API supplies
            # them. Open-Meteo fills only variables missing from TCM.
            if humidity is None:
                humidity = context_humidity

            if wet_bulb is None:
                wet_bulb = context_wet_bulb

            if solar is None:
                solar = context_solar

            # The current FortyGuard TCM response does not provide heat
            # index. Calculate it from each hyperlocal FortyGuard
            # temperature and the contextual relative humidity.
            if heat_index is None and humidity is not None:
                heat_index = self._calculate_heat_index_celsius(
                    temperature_c=temperature,
                    relative_humidity=humidity,
                )

            tiles.append(
                HeatTile(
                    id=self._extract_tile_id(item, index),
                    latitude=round(latitude, 6),
                    longitude=round(longitude, 6),
                    temperature=round(temperature, 2),
                    humidity=round(
                        humidity if humidity is not None else 0.0,
                        2,
                    ),
                    heat_index=round(
                        heat_index if heat_index is not None else temperature,
                        2,
                    ),
                    wet_bulb=round(
                        wet_bulb if wet_bulb is not None else 0.0,
                        2,
                    ),
                    solar_radiation=round(
                        solar if solar is not None else 0.0,
                        2,
                    ),
                )
            )

        if not tiles:
            raise RuntimeError(
                "FortyGuard returned map cells, but none could be "
                "normalized. Expected GeoJSON Polygon features with "
                "properties.average_temperature."
            )

        temperatures = [tile.temperature for tile in tiles]

        minimum = self._first_number(
            stats_data,
            ["temperature_min", "min_temperature", "min"],
        )
        maximum = self._first_number(
            stats_data,
            ["temperature_max", "max_temperature", "max"],
        )
        mean = self._first_number(
            stats_data,
            [
                "temperature_mean",
                "mean_temperature",
                "average_temperature",
                "average",
                "mean",
                "avg",
            ],
        )

        if minimum is None:
            minimum = min(temperatures)
        if maximum is None:
            maximum = max(temperatures)
        if mean is None:
            mean = sum(temperatures) / len(temperatures)

        center_latitude = (
            sum(tile.latitude for tile in tiles) / len(tiles)
        )
        center_longitude = (
            sum(tile.longitude for tile in tiles) / len(tiles)
        )

        return HeatmapResponse(
            location={
                "city": "New York City",
                "state": "New York",
                "country": "USA",
                "latitude": round(center_latitude, 6),
                "longitude": round(center_longitude, 6),
            },
            generated_at=datetime.now(timezone.utc).isoformat(),
            statistics=HeatmapStatistics(
                temperature_min=round(minimum, 2),
                temperature_max=round(maximum, 2),
                temperature_mean=round(mean, 2),
            ),
            tiles=tiles,
        )

    def _extract_activity_id(
        self,
        data: dict[str, Any],
    ) -> str | None:
        candidates = [
            data.get("activity_id"),
            data.get("activityId"),
            data.get("id"),
        ]

        nested = data.get(
            "data"
        )

        if isinstance(
            nested,
            dict,
        ):
            candidates.extend(
                [
                    nested.get(
                        "activity_id"
                    ),
                    nested.get(
                        "activityId"
                    ),
                    nested.get(
                        "id"
                    ),
                ]
            )

        for candidate in candidates:
            if candidate is not None:
                return str(
                    candidate
                )

        return None

    def _extract_status(
        self,
        data: dict[str, Any],
    ) -> str:
        candidates = [
            data.get("status"),
            data.get("state"),
            data.get("activity_status"),
        ]

        nested = data.get(
            "data"
        )

        if isinstance(
            nested,
            dict,
        ):
            candidates.extend(
                [
                    nested.get(
                        "status"
                    ),
                    nested.get(
                        "state"
                    ),
                    nested.get(
                        "activity_status"
                    ),
                ]
            )

        for candidate in candidates:
            if candidate:
                return str(
                    candidate
                )

        # Some completed responses may not include explicit status.
        if self._contains_heatmap_data(
            data
        ):
            return "COMPLETED"

        return "UNKNOWN"

    def _contains_heatmap_data(
        self,
        data: dict[str, Any],
    ) -> bool:
        payload = self._unwrap_result(
            data
        )

        return bool(
            self._extract_map_data(
                payload
            )
        )

    def _unwrap_result(
        self,
        raw: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Return the nearest nested dictionary that contains heatmap data.
        """
        found = self._find_heatmap_container(raw)
        return found if found is not None else raw

    def _find_heatmap_container(
        self,
        value: Any,
    ) -> dict[str, Any] | None:
        if isinstance(value, dict):
            if any(
                key in value
                for key in (
                    "map_data",
                    "mapData",
                    "tiles",
                    "features",
                )
            ):
                return value

            for key in (
                "data",
                "result",
                "output",
                "response",
            ):
                child = value.get(key)
                found = self._find_heatmap_container(child)
                if found is not None:
                    return found

            for child in value.values():
                found = self._find_heatmap_container(child)
                if found is not None:
                    return found

        elif isinstance(value, list):
            for child in value:
                found = self._find_heatmap_container(child)
                if found is not None:
                    return found

        return None

    def _extract_map_data(
        self,
        payload: Any,
    ) -> list[Any]:
        """
        Extract FortyGuard cells from:
        - map_data: [ ... ]
        - map_data: {type: FeatureCollection, features: [...]}
        - features: [...]
        - tiles: [...]
        - nested data/result/output/response wrappers
        """
        if isinstance(payload, list):
            # A list of GeoJSON features / tiles is already usable.
            if any(isinstance(item, dict) for item in payload):
                return payload
            return []

        if not isinstance(payload, dict):
            return []

        for key in ("map_data", "mapData", "tiles", "features"):
            candidate = payload.get(key)

            if isinstance(candidate, list):
                return candidate

            if isinstance(candidate, dict):
                features = candidate.get("features")
                if isinstance(features, list):
                    return features

                for inner_key in ("data", "values", "items", "tiles"):
                    inner = candidate.get(inner_key)
                    if isinstance(inner, list):
                        return inner

                nested = self._extract_map_data(candidate)
                if nested:
                    return nested

        for key in ("data", "result", "output", "response"):
            nested = self._extract_map_data(payload.get(key))
            if nested:
                return nested

        for child in payload.values():
            nested = self._extract_map_data(child)
            if nested:
                return nested

        return []

    def _extract_stats_data(
        self,
        payload: Any,
    ) -> dict[str, Any]:
        if not isinstance(payload, dict):
            return {}

        for key in (
            "stats_data",
            "statsData",
            "statistics",
            "stats",
        ):
            candidate = payload.get(key)
            if isinstance(candidate, dict):
                return candidate

        for key in ("data", "result", "output", "response"):
            candidate = self._extract_stats_data(payload.get(key))
            if candidate:
                return candidate

        for child in payload.values():
            candidate = self._extract_stats_data(child)
            if candidate:
                return candidate

        return {}

    def _extract_coordinates(
        self,
        item: dict[str, Any],
    ) -> tuple[float | None, float | None]:
        latitude = self._extract_number(
            item,
            ["latitude", "lat"],
        )
        longitude = self._extract_number(
            item,
            ["longitude", "lon", "lng"],
        )

        if latitude is not None and longitude is not None:
            return latitude, longitude

        geometry = item.get("geometry")
        if isinstance(geometry, dict):
            coordinates = geometry.get("coordinates")
            geometry_type = str(
                geometry.get("type", "")
            ).lower()

            if (
                geometry_type == "point"
                and isinstance(coordinates, list)
                and len(coordinates) >= 2
                and isinstance(coordinates[0], (int, float))
                and isinstance(coordinates[1], (int, float))
            ):
                return (
                    float(coordinates[1]),
                    float(coordinates[0]),
                )

            pairs = self._collect_coordinate_pairs(coordinates)
            if pairs:
                longitudes = [pair[0] for pair in pairs]
                latitudes = [pair[1] for pair in pairs]
                return (
                    sum(latitudes) / len(latitudes),
                    sum(longitudes) / len(longitudes),
                )

        center = item.get("center")
        if isinstance(center, dict):
            latitude = self._extract_number(
                center,
                ["latitude", "lat"],
            )
            longitude = self._extract_number(
                center,
                ["longitude", "lon", "lng"],
            )
            if latitude is not None and longitude is not None:
                return latitude, longitude

        return None, None

    def _collect_coordinate_pairs(
        self,
        value: Any,
    ) -> list[tuple[float, float]]:
        pairs: list[tuple[float, float]] = []

        if not isinstance(value, list):
            return pairs

        if (
            len(value) >= 2
            and isinstance(value[0], (int, float))
            and isinstance(value[1], (int, float))
        ):
            return [(float(value[0]), float(value[1]))]

        for child in value:
            pairs.extend(self._collect_coordinate_pairs(child))

        return pairs

    def _extract_tile_id(
        self,
        item: dict[str, Any],
        index: int,
    ) -> str:
        for key in ("id", "tile_id", "cell_id", "grid_id"):
            value = item.get(key)
            if value is not None:
                return str(value)

        properties = item.get("properties")
        if isinstance(properties, dict):
            for key in ("id", "tile_id", "cell_id", "grid_id"):
                value = properties.get(key)
                if value is not None:
                    return str(value)

        return f"FG-{index + 1:04d}"

    def _extract_number(
        self,
        data: dict[str, Any],
        keys: list[str],
    ) -> float | None:
        for key in keys:
            if key not in data:
                continue

            value = data.get(
                key
            )

            parsed = (
                self._to_float(
                    value
                )
            )

            if parsed is not None:
                return parsed

        properties = data.get(
            "properties"
        )

        if isinstance(
            properties,
            dict,
        ):
            for key in keys:
                value = (
                    properties.get(
                        key
                    )
                )

                parsed = (
                    self._to_float(
                        value
                    )
                )

                if parsed is not None:
                    return parsed

        return None

    @staticmethod
    def _calculate_heat_index_celsius(
        temperature_c: float,
        relative_humidity: float,
    ) -> float:
        """
        Calculate heat index using the NOAA/NWS Rothfusz regression.

        The regression is principally intended for warm/humid
        conditions. For conditions below its standard screening
        threshold, return the air temperature rather than inventing
        additional apparent heat stress.
        """

        temperature_f = (
            temperature_c * 9.0 / 5.0
        ) + 32.0

        rh = max(
            0.0,
            min(float(relative_humidity), 100.0),
        )

        # Standard NWS screening: below roughly 80 F, heat index
        # is effectively represented by air temperature.
        if temperature_f < 80.0:
            return round(temperature_c, 2)

        heat_index_f = (
            -42.379
            + 2.04901523 * temperature_f
            + 10.14333127 * rh
            - 0.22475541 * temperature_f * rh
            - 0.00683783 * temperature_f * temperature_f
            - 0.05481717 * rh * rh
            + 0.00122874
            * temperature_f
            * temperature_f
            * rh
            + 0.00085282
            * temperature_f
            * rh
            * rh
            - 0.00000199
            * temperature_f
            * temperature_f
            * rh
            * rh
        )

        # NWS low-humidity adjustment.
        if (
            rh < 13.0
            and 80.0 <= temperature_f <= 112.0
        ):
            adjustment = (
                (13.0 - rh) / 4.0
            ) * (
                (
                    (17.0 - abs(temperature_f - 95.0))
                    / 17.0
                )
                ** 0.5
            )
            heat_index_f -= adjustment

        # NWS high-humidity adjustment.
        elif (
            rh > 85.0
            and 80.0 <= temperature_f <= 87.0
        ):
            adjustment = (
                (rh - 85.0) / 10.0
            ) * (
                (87.0 - temperature_f) / 5.0
            )
            heat_index_f += adjustment

        heat_index_c = (
            heat_index_f - 32.0
        ) * 5.0 / 9.0

        return round(heat_index_c, 2)

    def _first_number(
        self,
        data: dict[str, Any],
        keys: list[str],
    ) -> float | None:
        for key in keys:
            if key not in data:
                continue

            parsed = (
                self._to_float(
                    data.get(
                        key
                    )
                )
            )

            if parsed is not None:
                return parsed

        return None

    @staticmethod
    def _to_float(
        value: Any,
    ) -> float | None:
        if value is None:
            return None

        if isinstance(
            value,
            bool,
        ):
            return None

        try:
            return float(
                value
            )

        except (
            TypeError,
            ValueError,
        ):
            return None


fortyguard_service = FortyGuardService()