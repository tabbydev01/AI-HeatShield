from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import httpx

from app.config import settings
from app.schemas.heatmap import HeatTile, HeatmapResponse, HeatmapStatistics
from app.services.weather_service import weather_service


class FortyGuardService:
    """
    Fast-first FortyGuard adapter for AI HeatShield.

    The read path never waits for FortyGuard. `/api/analyze` serves the newest
    already-available dataset from RAM or the persisted last-known-good cache.
    Network refreshes happen only through the explicit refresh path.

    Source modes:
    - LIVE          fresh FortyGuard data fetched during this process
    - CACHED_LIVE   persisted/stale last-known-good FortyGuard data
    - DEMO          intentional demo mode (no API key or DEMO_MODE=true)
    - DEMO_FALLBACK no real cache exists yet and the live refresh failed
    """

    CURRENT_CACHE_TTL_SECONDS = 15 * 60
    FORECAST_CACHE_TTL_SECONDS = 60 * 60
    MAX_STATUS_ATTEMPTS = 60
    INITIAL_STATUS_POLL_SECONDS = 3
    MAX_STATUS_POLL_SECONDS = 6
    FORECAST_HORIZONS = (3, 6, 9, 12)

    # POST submissions are deliberately bounded. The semaphore is held only
    # while creating activities, not while those activities are processing.
    # This lets FortyGuard process the five independent heatmaps in parallel
    # without sending an uncontrolled burst of submissions.
    SUBMIT_CONCURRENCY = 2

    def __init__(self) -> None:
        self.base_url = settings.fortyguard_base_url.rstrip("/")
        self.api_key = settings.fortyguard_api_key.strip() if settings.fortyguard_api_key else ""
        self.force_demo_mode = bool(settings.demo_mode)
        self.demo_mode = self.force_demo_mode or not self.api_key

        self.last_source = "DEMO" if self.demo_mode else "DEMO_FALLBACK"
        self.last_error: str | None = None

        self._cache: HeatmapResponse | None = None
        self._cache_source: str | None = None
        self._cache_saved_at_utc: datetime | None = None
        self._cache_created_monotonic: float | None = None

        self._forecast_cache: dict[int, HeatmapResponse] = {}
        self._forecast_base_time: datetime | None = None
        self._forecast_saved_at_utc: datetime | None = None

        self._refresh_lock = asyncio.Lock()
        self._forecast_refresh_lock = asyncio.Lock()
        self._is_refreshing = False
        self._is_forecast_refreshing = False

        backend_root = Path(__file__).resolve().parents[2]
        self.demo_file = backend_root / "demo_data" / "phoenix_heatmap.json"
        self.cache_file = backend_root / "data" / "heatshield_live_cache.json"

        self._load_persisted_cache_safely()

    # ------------------------------------------------------------------
    # FAST READ PATH
    # ------------------------------------------------------------------

    async def get_heatmap(self, force_refresh: bool = False) -> HeatmapResponse:
        """Compatibility wrapper. Normal reads are fast; forced reads refresh."""
        if force_refresh:
            await self.refresh_all(force=True)
        return self.get_cached_heatmap()

    def get_cached_heatmap(self) -> HeatmapResponse:
        """Return the best immediately available heatmap without network I/O."""
        if self._cache is not None:
            if self._cache_source == "LIVE" and self._current_cache_is_fresh():
                self.last_source = "LIVE"
            elif self._cache_source in {"LIVE", "CACHED_LIVE"}:
                self.last_source = "CACHED_LIVE"
            else:
                self.last_source = self._cache_source or "DEMO_FALLBACK"
            return self._cache

        demo = self._load_demo_heatmap()
        self.last_source = "DEMO" if self.demo_mode else "DEMO_FALLBACK"
        return demo

    def get_cached_forecast_heatmaps(self) -> dict[int, HeatmapResponse]:
        """Return cached future heatmaps only while their base time is still useful."""
        if not self._forecast_cache:
            return {}
        if not self._forecast_cache_is_usable():
            return {}
        return dict(self._forecast_cache)

    def get_source(self) -> str:
        return self.last_source

    def is_refreshing(self) -> bool:
        return self._is_refreshing

    def needs_refresh(self) -> bool:
        if self.demo_mode:
            return False
        if self._cache is None:
            return True
        return not self._current_cache_is_fresh()

    def get_data_generated_at(self) -> str | None:
        if self._cache is not None:
            return self._cache.generated_at
        return None

    def get_forecast_status(self) -> str:
        if not self._forecast_cache:
            return "UNAVAILABLE"
        if self._forecast_cache_is_usable():
            return "READY"
        return "STALE"

    def clear_cache(self, include_persisted: bool = False) -> None:
        self._cache = None
        self._cache_source = None
        self._cache_saved_at_utc = None
        self._cache_created_monotonic = None
        self._forecast_cache = {}
        self._forecast_base_time = None
        self._forecast_saved_at_utc = None

        if include_persisted:
            try:
                if self.cache_file.exists():
                    self.cache_file.unlink()
            except OSError:
                pass

    # ------------------------------------------------------------------
    # EXPLICIT NETWORK REFRESH PATH
    # ------------------------------------------------------------------

    async def refresh_all(self, force: bool = False) -> dict[str, Any]:
        """
        Refresh only the CURRENT FortyGuard heatmap on the request path.

        Forecast generation is intentionally separated into
        ``refresh_forecasts`` so production deployments do not depend on an
        orphaned ``asyncio.create_task`` surviving after an HTTP response ends.
        Existing forecast data remains available until an explicit forecast
        refresh successfully replaces it.
        """
        if self.demo_mode:
            demo = self._load_demo_heatmap()
            self._store_current_cache(demo, "DEMO")
            self.last_source = "DEMO"
            self.last_error = None
            return {
                "ok": True,
                "mode": "DEMO",
                "refreshed": False,
                "forecast_horizons": [],
            }

        if not force and self._current_cache_is_fresh():
            return {
                "ok": True,
                "mode": self.get_source(),
                "refreshed": False,
                "forecast_horizons": sorted(
                    self.get_cached_forecast_heatmaps()
                ),
            }

        async with self._refresh_lock:
            # Another request may have refreshed current data while this caller
            # was waiting for the lock.
            if not force and self._current_cache_is_fresh():
                return {
                    "ok": True,
                    "mode": self.get_source(),
                    "refreshed": False,
                    "forecast_horizons": sorted(
                        self.get_cached_forecast_heatmaps()
                    ),
                }

            self._is_refreshing = True
            weather_task: asyncio.Task[dict[datetime, dict[str, Any]]] | None = None

            try:
                base_time = self._current_nyc_hour()

                weather_task = asyncio.create_task(
                    weather_service.get_environmental_batch(
                        [base_time],
                        latitude=40.712336,
                        longitude=-74.010329,
                        force_refresh=False,
                    )
                )

                timeout = httpx.Timeout(
                    connect=20.0,
                    read=60.0,
                    write=30.0,
                    pool=30.0,
                )

                async with httpx.AsyncClient(timeout=timeout) as client:
                    submission = await self._submit_heatmap_job(
                        client=client,
                        target_time=base_time,
                    )
                    current_raw = await self._resolve_submitted_job(
                        client=client,
                        submission=submission,
                    )

                environmental_contexts = await self._safe_weather_result(
                    weather_task
                )

                current = self._normalize_live_response(
                    current_raw,
                    environmental_data=environmental_contexts.get(base_time),
                )

                self._store_current_cache(current, "LIVE")
                self.last_source = "LIVE"
                self.last_error = None
                self._persist_cache_safely()

                return {
                    "ok": True,
                    "mode": "LIVE",
                    "refreshed": True,
                    "forecast_horizons": sorted(
                        self.get_cached_forecast_heatmaps()
                    ),
                }

            except Exception as exc:
                self.last_error = str(exc)

                if (
                    self._cache is not None
                    and self._cache_source in {"LIVE", "CACHED_LIVE"}
                ):
                    self.last_source = "CACHED_LIVE"
                    return {
                        "ok": False,
                        "mode": "CACHED_LIVE",
                        "refreshed": False,
                        "error": self.last_error,
                        "forecast_horizons": sorted(
                            self.get_cached_forecast_heatmaps()
                        ),
                    }

                self.last_source = "DEMO_FALLBACK"
                return {
                    "ok": False,
                    "mode": "DEMO_FALLBACK",
                    "refreshed": False,
                    "error": self.last_error,
                    "forecast_horizons": [],
                }

            finally:
                if weather_task is not None and not weather_task.done():
                    weather_task.cancel()
                    try:
                        await weather_task
                    except (asyncio.CancelledError, Exception):
                        pass

                self._is_refreshing = False

    async def refresh_forecasts(self, force: bool = False) -> dict[str, Any]:
        """
        Explicitly refresh +3/+6/+9/+12 FortyGuard forecast heatmaps.

        This coroutine is designed to be awaited by an HTTP endpoint. Keeping
        the request alive until the forecast batch finishes is production-safe
        on serverless/container platforms that may cancel detached background
        tasks after the originating request returns.

        A previous forecast generation remains active until at least one new
        horizon has completed successfully. Total upstream failure therefore
        never destroys a known-good forecast cache.
        """
        if self.demo_mode:
            return {
                "ok": True,
                "mode": "DEMO",
                "refreshed": False,
                "forecast_horizons": [],
            }

        if not force and self._forecast_cache_is_usable():
            return {
                "ok": True,
                "mode": self.get_source(),
                "refreshed": False,
                "forecast_horizons": sorted(
                    self.get_cached_forecast_heatmaps()
                ),
            }

        async with self._forecast_refresh_lock:
            # Deduplicate callers that arrived while another forecast request
            # was already running.
            if not force and self._forecast_cache_is_usable():
                return {
                    "ok": True,
                    "mode": self.get_source(),
                    "refreshed": False,
                    "forecast_horizons": sorted(
                        self.get_cached_forecast_heatmaps()
                    ),
                }

            self._is_forecast_refreshing = True
            weather_task: asyncio.Task[dict[datetime, dict[str, Any]]] | None = None

            try:
                base_time = self._current_nyc_hour()
                target_by_horizon = {
                    hours: base_time + timedelta(hours=hours)
                    for hours in self.FORECAST_HORIZONS
                }

                weather_task = asyncio.create_task(
                    weather_service.get_environmental_batch(
                        target_by_horizon.values(),
                        latitude=40.712336,
                        longitude=-74.010329,
                        force_refresh=False,
                    )
                )

                timeout = httpx.Timeout(
                    connect=20.0,
                    read=60.0,
                    write=30.0,
                    pool=30.0,
                )
                limits = httpx.Limits(
                    max_connections=8,
                    max_keepalive_connections=4,
                    keepalive_expiry=30.0,
                )

                async with httpx.AsyncClient(
                    timeout=timeout,
                    limits=limits,
                ) as client:
                    submissions = await self._submit_refresh_jobs(
                        client=client,
                        target_by_horizon=target_by_horizon,
                    )

                    result_tasks = {
                        hours: asyncio.create_task(
                            self._resolve_submitted_job(
                                client=client,
                                submission=submission,
                            )
                        )
                        for hours, submission in submissions.items()
                    }

                    environmental_contexts = await self._safe_weather_result(
                        weather_task
                    )

                    forecast_results = await self._collect_forecast_results(
                        result_tasks=result_tasks,
                        target_by_horizon=target_by_horizon,
                        environmental_contexts=environmental_contexts,
                    )

                if not forecast_results:
                    message = (
                        "No new FortyGuard forecast horizons completed; "
                        "keeping previous forecast cache."
                    )
                    self.last_error = message
                    return {
                        "ok": False,
                        "mode": self.get_source(),
                        "refreshed": False,
                        "error": message,
                        "forecast_horizons": sorted(
                            self.get_cached_forecast_heatmaps()
                        ),
                    }

                # Atomic generation swap: the UI sees the old generation until
                # this batch has finished, then receives the new set together.
                self._forecast_cache = forecast_results
                self._forecast_base_time = base_time
                self._forecast_saved_at_utc = datetime.now(timezone.utc)
                self.last_error = None
                self._persist_cache_safely()

                return {
                    "ok": True,
                    "mode": self.get_source(),
                    "refreshed": True,
                    "forecast_horizons": sorted(forecast_results),
                }

            except Exception as exc:
                self.last_error = str(exc)
                return {
                    "ok": False,
                    "mode": self.get_source(),
                    "refreshed": False,
                    "error": self.last_error,
                    "forecast_horizons": sorted(
                        self.get_cached_forecast_heatmaps()
                    ),
                }

            finally:
                if weather_task is not None and not weather_task.done():
                    weather_task.cancel()
                    try:
                        await weather_task
                    except (asyncio.CancelledError, Exception):
                        pass

                self._is_forecast_refreshing = False

    async def _submit_refresh_jobs(
        self,
        client: httpx.AsyncClient,
        target_by_horizon: dict[int, datetime],
    ) -> dict[int, dict[str, Any]]:
        """
        Submit all current/forecast activities early.

        The concurrency limit protects the upstream API only during POST
        submission. Once an activity_id has been created, the semaphore is
        released immediately so another horizon can be submitted while the
        first activity is processing on FortyGuard's side.
        """
        semaphore = asyncio.Semaphore(self.SUBMIT_CONCURRENCY)

        async def submit_one(
            hours: int,
            target_time: datetime,
        ) -> tuple[int, dict[str, Any] | None]:
            async with semaphore:
                try:
                    submission = await self._submit_heatmap_job(
                        client=client,
                        target_time=target_time,
                    )
                    return hours, submission
                except Exception as exc:
                    if hours == 0:
                        raise
                    print(
                        "[AI HeatShield] FortyGuard forecast submission failed "
                        f"for +{hours}h. Error: {exc}"
                    )
                    return hours, None

        pairs = await asyncio.gather(
            *(
                submit_one(hours, target_time)
                for hours, target_time in target_by_horizon.items()
            )
        )

        return {
            hours: submission
            for hours, submission in pairs
            if submission is not None
        }

    async def _submit_heatmap_job(
        self,
        client: httpx.AsyncClient,
        target_time: datetime,
    ) -> dict[str, Any]:
        """Create one FortyGuard heatmap activity or retain an immediate result."""
        if not self.api_key:
            raise RuntimeError("FortyGuard API key is missing.")

        response = await client.post(
            f"{self.base_url}/v1/heatmap",
            headers=self._fortyguard_headers(),
            json=self._build_heatmap_payload(target_time),
        )

        if response.status_code >= 400:
            raise RuntimeError(
                "FortyGuard heatmap request failed "
                f"with HTTP {response.status_code}: {response.text[:500]}"
            )

        try:
            submit_data = response.json()
        except ValueError as exc:
            raise RuntimeError(
                "FortyGuard returned invalid JSON on submit."
            ) from exc

        activity_id = self._extract_activity_id(submit_data)

        if activity_id:
            return {
                "activity_id": activity_id,
                "immediate": None,
            }

        if self._contains_heatmap_data(submit_data):
            return {
                "activity_id": None,
                "immediate": submit_data,
            }

        raise RuntimeError(
            "FortyGuard response did not contain an activity_id or heatmap data."
        )

    async def _resolve_submitted_job(
        self,
        client: httpx.AsyncClient,
        submission: dict[str, Any],
    ) -> dict[str, Any]:
        """Resolve an immediate response or poll one submitted activity."""
        immediate = submission.get("immediate")
        if isinstance(immediate, dict):
            return immediate

        activity_id = submission.get("activity_id")
        if not activity_id:
            raise RuntimeError("FortyGuard submission is missing activity_id.")

        return await self._poll_activity(
            client=client,
            headers=self._fortyguard_headers(),
            activity_id=str(activity_id),
        )

    async def _collect_forecast_results(
        self,
        result_tasks: dict[int, asyncio.Task[dict[str, Any]]],
        target_by_horizon: dict[int, datetime],
        environmental_contexts: dict[datetime, dict[str, Any]],
    ) -> dict[int, HeatmapResponse]:
        """Collect and normalize the four independent future heatmaps."""
        results: dict[int, HeatmapResponse] = {}

        for hours in self.FORECAST_HORIZONS:
            task = result_tasks.get(hours)
            if task is None:
                continue

            try:
                raw = await task
                target_time = target_by_horizon[hours]
                results[hours] = self._normalize_live_response(
                    raw,
                    environmental_data=environmental_contexts.get(target_time),
                )
            except Exception as exc:
                print(
                    "[AI HeatShield] FortyGuard forecast request failed "
                    f"for +{hours}h. Error: {exc}"
                )

        return results

    async def _safe_weather_result(
        self,
        weather_task: asyncio.Task[dict[datetime, dict[str, Any]]],
    ) -> dict[datetime, dict[str, Any]]:
        """Return environmental context without allowing it to break FortyGuard."""
        try:
            return await weather_task
        except Exception as exc:
            print(
                "[AI HeatShield] Open-Meteo batch context unavailable. "
                f"Continuing with FortyGuard temperature only. Error: {exc}"
            )
            return {}

    async def get_forecast_heatmaps(
        self,
        horizons: tuple[int, ...] = FORECAST_HORIZONS,
    ) -> dict[int, HeatmapResponse]:
        """Compatibility method: returns cached forecasts, never starts jobs."""
        cached = self.get_cached_forecast_heatmaps()
        return {hours: cached[hours] for hours in horizons if hours in cached}

    # ------------------------------------------------------------------
    # CACHE + PERSISTENCE
    # ------------------------------------------------------------------

    def _store_current_cache(self, heatmap: HeatmapResponse, source: str) -> None:
        self._cache = heatmap
        self._cache_source = source
        self._cache_saved_at_utc = datetime.now(timezone.utc)
        self._cache_created_monotonic = time.monotonic()

    def _current_cache_is_fresh(self) -> bool:
        if self._cache is None:
            return False

        if self._cache_created_monotonic is not None:
            return (
                time.monotonic() - self._cache_created_monotonic
                < self.CURRENT_CACHE_TTL_SECONDS
            )

        if self._cache_saved_at_utc is None:
            return False

        return (
            datetime.now(timezone.utc) - self._cache_saved_at_utc
        ).total_seconds() < self.CURRENT_CACHE_TTL_SECONDS

    def _forecast_cache_is_usable(self) -> bool:
        if not self._forecast_cache or self._forecast_base_time is None:
            return False

        now_nyc = self._current_nyc_hour()
        age = abs((now_nyc - self._forecast_base_time).total_seconds())
        return age < self.FORECAST_CACHE_TTL_SECONDS

    def _persist_cache_safely(self) -> None:
        if self._cache is None or self._cache_source not in {"LIVE", "CACHED_LIVE"}:
            return

        payload: dict[str, Any] = {
            "version": 1,
            "saved_at": datetime.now(timezone.utc).isoformat(),
            "current": self._cache.model_dump(mode="json"),
            "forecast_base_time": (
                self._forecast_base_time.isoformat()
                if self._forecast_base_time is not None
                else None
            ),
            "forecasts": {
                str(hours): heatmap.model_dump(mode="json")
                for hours, heatmap in self._forecast_cache.items()
            },
        }

        try:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            temp_file = self.cache_file.with_suffix(".tmp")
            temp_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            temp_file.replace(self.cache_file)
        except OSError as exc:
            # Some serverless filesystems may be read-only/ephemeral. RAM cache
            # still works, so persistence failure must not break the API.
            print(f"[AI HeatShield] Could not persist live cache: {exc}")

    def _load_persisted_cache_safely(self) -> None:
        if self.demo_mode or not self.cache_file.exists():
            return

        try:
            raw = json.loads(self.cache_file.read_text(encoding="utf-8"))
            current_raw = raw.get("current")
            if not isinstance(current_raw, dict):
                return

            self._cache = HeatmapResponse.model_validate(current_raw)
            self._cache_source = "CACHED_LIVE"

            saved_at_raw = raw.get("saved_at")
            if isinstance(saved_at_raw, str):
                parsed = datetime.fromisoformat(saved_at_raw.replace("Z", "+00:00"))
                self._cache_saved_at_utc = (
                    parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)
                )

            base_raw = raw.get("forecast_base_time")
            if isinstance(base_raw, str):
                self._forecast_base_time = datetime.fromisoformat(base_raw)

            forecasts_raw = raw.get("forecasts", {})
            if isinstance(forecasts_raw, dict):
                for key, value in forecasts_raw.items():
                    try:
                        hours = int(key)
                        if isinstance(value, dict):
                            self._forecast_cache[hours] = HeatmapResponse.model_validate(value)
                    except (TypeError, ValueError):
                        continue

            self.last_source = "CACHED_LIVE"
        except Exception as exc:
            print(f"[AI HeatShield] Ignoring invalid persisted cache: {exc}")
            self._cache = None
            self._cache_source = None
            self._forecast_cache = {}
            self._forecast_base_time = None

    # ------------------------------------------------------------------
    # FORTYGUARD NETWORK
    # ------------------------------------------------------------------

    async def _fetch_heatmap_for_time(
        self,
        target_time: datetime,
        environmental_data: dict[str, Any] | None = None,
    ) -> HeatmapResponse:
        """
        Compatibility helper for one-off callers.

        Full refreshes use the two-phase submit/poll pipeline above so all
        activities can overlap. This method keeps the old single-target
        behavior available without duplicating normalization logic.
        """
        timeout = httpx.Timeout(
            connect=20.0,
            read=60.0,
            write=30.0,
            pool=30.0,
        )

        async with httpx.AsyncClient(timeout=timeout) as client:
            submission = await self._submit_heatmap_job(
                client=client,
                target_time=target_time,
            )
            raw = await self._resolve_submitted_job(
                client=client,
                submission=submission,
            )

        return self._normalize_live_response(
            raw,
            environmental_data=environmental_data,
        )

    def _fortyguard_headers(self) -> dict[str, str]:
        return {
            "api-key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def _poll_activity(
        self,
        client: httpx.AsyncClient,
        headers: dict[str, str],
        activity_id: str,
    ) -> dict[str, Any]:
        status_url = f"{self.base_url}/v1/status/{activity_id}"
        delay = self.INITIAL_STATUS_POLL_SECONDS
        last_status = "UNKNOWN"

        for _ in range(self.MAX_STATUS_ATTEMPTS):
            response = await client.get(status_url, headers=headers)

            if response.status_code in {404, 429}:
                await asyncio.sleep(delay)
                delay = min(delay * 2, self.MAX_STATUS_POLL_SECONDS)
                continue

            if response.status_code >= 400:
                raise RuntimeError(
                    "FortyGuard status request failed "
                    f"with HTTP {response.status_code}: {response.text[:500]}"
                )

            try:
                data = response.json()
            except ValueError as exc:
                raise RuntimeError("FortyGuard status endpoint returned invalid JSON.") from exc

            status = self._extract_status(data)
            last_status = status
            normalized = status.strip().upper().replace(" ", "_")

            if normalized in {"COMPLETED", "COMPLETE", "SUCCESS", "SUCCEEDED", "DONE"}:
                return data

            if normalized in {"FAILED", "FAILURE", "ERROR", "CANCELLED", "CANCELED"}:
                message = data.get("message") or data.get("error") or data.get("detail") or "Unknown FortyGuard error."
                raise RuntimeError(f"FortyGuard activity failed: {message}")

            await asyncio.sleep(delay)
            delay = min(delay * 2, self.MAX_STATUS_POLL_SECONDS)

        raise TimeoutError(
            "FortyGuard heatmap activity did not complete in time. "
            f"Last status: {last_status}"
        )

    @staticmethod
    def _current_nyc_hour() -> datetime:
        return datetime.now(ZoneInfo("America/New_York")).replace(
            minute=0,
            second=0,
            microsecond=0,
        )

    def _build_heatmap_payload(self, target_time: datetime | None = None) -> dict[str, Any]:
        if target_time is None:
            target_time = self._current_nyc_hour()

        polygon_geometry = {
            "type": "Polygon",
            "coordinates": [[
                [-74.0170, 40.7050],
                [-74.0030, 40.7050],
                [-74.0030, 40.7180],
                [-74.0170, 40.7180],
                [-74.0170, 40.7050],
            ]],
        }

        return {
            "polygon_aoi": {
                "type": "FeatureCollection",
                "features": [{
                    "type": "Feature",
                    "properties": {},
                    "geometry": polygon_geometry,
                }],
            },
            "date_time": {
                "start_date": target_time.strftime("%Y-%m-%d"),
                "start_time": target_time.strftime("%H:%M"),
                "filter_type": 1,
            },
            "granularity": 100,
            "analytic_type": "tcm",
        }

    # ------------------------------------------------------------------
    # LIVE RESPONSE NORMALIZATION + DEMO/HELPERS
    # ------------------------------------------------------------------
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

    # ============================================================
    # DEMO DATA
    # ============================================================

    def _load_demo_heatmap(
        self,
    ) -> HeatmapResponse:
        if not self.demo_file.exists():
            raise FileNotFoundError(
                "AI HeatShield demo heatmap file "
                f"not found: {self.demo_file}"
            )

        with self.demo_file.open(
            "r",
            encoding="utf-8",
        ) as file:
            raw = json.load(
                file
            )

        return HeatmapResponse.model_validate(
            raw
        )

    # ============================================================
    # RESPONSE HELPERS
    # ============================================================

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