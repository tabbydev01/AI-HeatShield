"use client";

import { useEffect, useState } from "react";
import HeatMapLoader from "../components/HeatMapLoader";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  "http://127.0.0.1:8000";

type RiskFactor = {
  name: string;
  contribution: number;
};

type Recommendation = {
  priority: number;
  category: string;
  title: string;
  action: string;
  reason: string;
};

type Intervention = {
  name: string;
  before_score: number;
  after_score: number;
  reduction_points: number;
  reduction_percent: number;
};

type ForecastPoint = {
  hours_ahead: number;
  temperature: number;
  heat_index: number;
  solar_radiation: number;
  risk_score: number;
  risk_level: string;
};

type HistoricalPoint = {
  label: string;
  temperature: number;
  heat_index: number;
  risk_score: number;
};

type HistoricalComparison = {
  tile_id: string;

  current_temperature: number;
  baseline_temperature: number;
  temperature_difference: number;

  current_heat_index: number;
  baseline_heat_index: number;
  heat_index_difference: number;

  current_risk_score: number;
  baseline_risk_score: number;
  risk_difference: number;

  trend: string;
  history: HistoricalPoint[];
};

type PersonaRisk = {
  persona: string;
  risk_score: number;
  risk_level: string;
  sensitivity_multiplier: number;
  primary_reason: string;
  recommended_action: string;
};

type VulnerabilityResponse = {
  tile_id: string;
  base_risk_score: number;
  base_risk_level: string;
  most_vulnerable_persona: string;
  personas: PersonaRisk[];
};

type MapTile = {
  tile_id: string;
  latitude: number;
  longitude: number;
  temperature: number;
  humidity: number;
  heat_index: number;
  wet_bulb: number;
  solar_radiation: number;
  risk_score: number;
  risk_level: string;
};

type Hotspot = {
  rank: number;
  tile_id: string;
  latitude: number;
  longitude: number;
  temperature: number;
  risk_score: number;
  risk_level: string;
};

type SelectedZone = {
  tile_id: string;

  latitude: number;
  longitude: number;

  temperature: number;
  humidity: number;
  heat_index: number;
  wet_bulb: number;
  solar_radiation: number;

  risk_score: number;
  risk_level: string;

  primary_driver: string;
  secondary_driver: string;

  factors: RiskFactor[];
  recommendations: Recommendation[];
  interventions: Intervention[];
  forecast: ForecastPoint[];

  historical: HistoricalComparison;
  vulnerability: VulnerabilityResponse;
};

type AnalysisData = {
  project: string;
  mode?: string;
  refreshing?: boolean;
  needs_refresh?: boolean;
  data_generated_at?: string | null;
  forecast_status?: string;

  location: {
    city: string;
    state: string;
    country: string;
  };

  statistics: {
    temperature_min: number;
    temperature_max: number;
    temperature_mean: number;
  };

  selected_zone: SelectedZone;

  map_tiles: MapTile[];
  hotspots: Hotspot[];
};

export default function Home() {
  const [data, setData] =
    useState<AnalysisData | null>(null);

  const [loading, setLoading] =
    useState(true);

  const [error, setError] =
    useState("");

  const [lastUpdated, setLastUpdated] =
    useState("");

  const [backgroundRefreshing, setBackgroundRefreshing] =
    useState(false);

  useEffect(() => {
    void initializeDashboard();
  }, []);

  async function initializeDashboard() {
    const initial = await loadAnalysis(
      undefined,
      true,
    );

    if (initial?.needs_refresh) {
      void refreshData(
        initial.selected_zone.tile_id,
        false,
      );
    }
  }

  async function loadAnalysis(
    tileId?: string,
    showLoading = true,
  ): Promise<AnalysisData | null> {
    try {
      if (showLoading) {
        setLoading(true);
      }

      const url = tileId
        ? `${API_BASE_URL}/api/analyze?tile_id=${encodeURIComponent(
            tileId,
          )}`
        : `${API_BASE_URL}/api/analyze`;

      const response = await fetch(
        url,
        {
          cache: "no-store",
        },
      );

      if (!response.ok) {
        throw new Error(
          `Backend request failed with status ${response.status}.`,
        );
      }

      const result: AnalysisData =
        await response.json();

      setData(result);
      setError("");

      setLastUpdated(
        new Date().toLocaleTimeString(
          [],
          {
            hour: "2-digit",
            minute: "2-digit",
          },
        ),
      );

      return result;
    } catch (err) {
      console.error(
        "AI HeatShield API error:",
        err,
      );

      setError(
        "Unable to connect to AI HeatShield backend.",
      );
      return null;
    } finally {
      if (showLoading) {
        setLoading(false);
      }
    }
  }

  async function refreshData(
    tileId?: string,
    force = true,
  ) {
    if (backgroundRefreshing) {
      return;
    }

    setBackgroundRefreshing(true);

    try {
      const response = await fetch(
        `${API_BASE_URL}/api/refresh?force=${force ? "true" : "false"}`,
        {
          method: "POST",
          cache: "no-store",
        },
      );

      if (!response.ok) {
        throw new Error(
          `Refresh request failed with status ${response.status}.`,
        );
      }

      await loadAnalysis(
        tileId,
        false,
      );
    } catch (err) {
      console.error(
        "AI HeatShield background refresh error:",
        err,
      );
    } finally {
      setBackgroundRefreshing(false);
    }
  }

  if (loading && !data) {
    return <LoadingScreen />;
  }

  if (error && !data) {
    return (
      <ErrorScreen
        message={error}
      />
    );
  }

  if (!data) {
    return null;
  }

  const zone =
    data.selected_zone;

  const safeMode =
    typeof data.mode === "string" &&
    data.mode.trim()
      ? data.mode
          .trim()
          .toUpperCase()
      : "DEMO";

  const isLive =
    safeMode === "LIVE" ||
    safeMode === "CACHED_LIVE";

  return (
    <main className="min-h-screen bg-transparent text-slate-100">
      <div className="mx-auto max-w-[1480px] px-4 py-4 md:px-6 lg:px-8">

        <TopHeader
          data={data}
          mode={safeMode}
          lastUpdated={lastUpdated}
          onRefresh={() =>
            void refreshData(
              zone.tile_id,
              true,
            )
          }
          refreshing={backgroundRefreshing}
        />

        <section className="mt-5 grid gap-5 xl:grid-cols-[1.55fr_0.45fr]">

          <HeroOverview
            data={data}
            mode={safeMode}
          />

          <RiskCard
            score={
              zone.risk_score
            }
            level={
              zone.risk_level
            }
            primaryDriver={
              zone.primary_driver
            }
          />

        </section>

        <section className="mt-5">

          <div className="mb-3 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">

            <div>

              <p className="text-[9px] font-semibold uppercase tracking-[0.2em] text-sky-300/70">
                Spatial Intelligence
              </p>

              <h2 className="mt-1 text-base font-semibold tracking-[-0.02em]">
                Interactive Urban Heat Map
              </h2>

              <p className="mt-1 text-xs text-slate-500">
                Explore{" "}
                {
                  data
                    .map_tiles
                    .length
                }{" "}
                hyperlocal heat cells and
                select any zone to update
                the complete analysis.
              </p>

            </div>

            <div className="flex items-center gap-3">

              <div className="rounded-xl border border-slate-800/70 bg-[#0c1620]/80 px-3 py-2">

                <p className="text-[8px] uppercase tracking-[0.15em] text-slate-600">
                  Heat Cells
                </p>

                <p className="mt-0.5 text-xs font-medium text-slate-300">
                  {
                    data
                      .map_tiles
                      .length
                  }
                </p>

              </div>

              <div className="rounded-xl border border-slate-800/70 bg-[#0c1620]/80 px-3 py-2">

                <p className="text-[8px] uppercase tracking-[0.15em] text-slate-600">
                  Selected
                </p>

                <p className="mt-0.5 text-xs font-medium text-slate-300">
                  {
                    zone.tile_id
                  }
                </p>

              </div>

            </div>

          </div>

          <HeatMapLoader
            tiles={
              data.map_tiles
            }
            selectedZone={{
              tile_id:
                zone.tile_id,

              latitude:
                zone.latitude,

              longitude:
                zone.longitude,

              temperature:
                zone.temperature,

              risk_score:
                zone.risk_score,

              risk_level:
                zone.risk_level,
            }}
            mode={safeMode}
            onSelect={(
              tileId,
            ) =>
              loadAnalysis(
                tileId,
              )
            }
          />

        </section>

        <section className="mt-5 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">

          <MetricCard
            label="Temperature"
            value={`${zone.temperature}°C`}
            subtitle={
              isLive
                ? `FortyGuard hyperlocal • ${signed(
                    zone.temperature -
                      data.statistics.temperature_mean,
                  )}°C vs area mean`
                : `${signed(
                    zone.temperature -
                      data.statistics.temperature_mean,
                  )}°C vs area mean`
            }
            badge={isLive ? "FORTYGUARD" : "TEMP"}
          />

          <MetricCard
            label="Heat Index"
            value={`${zone.heat_index}°C`}
            subtitle={
              isLive
                ? "Calculated from FortyGuard temperature + contextual humidity"
                : "Perceived thermal stress"
            }
            badge={isLive ? "CALCULATED" : "HEAT"}
          />

          <MetricCard
            label="Humidity"
            value={`${zone.humidity}%`}
            subtitle={
              isLive
                ? `Open-Meteo contextual data • ${
                    zone.humidity < 35
                      ? "dry conditions"
                      : "elevated moisture"
                  }`
                : zone.humidity < 35
                  ? "Dry conditions"
                  : "Elevated moisture"
            }
            badge={isLive ? "OPEN-METEO" : "HUM"}
          />

          <MetricCard
            label="Solar Radiation"
            value={`${zone.solar_radiation} W/m²`}
            subtitle={
              isLive
                ? "Open-Meteo contextual solar exposure"
                : "Local solar exposure"
            }
            badge={isLive ? "OPEN-METEO" : "SUN"}
          />

        </section>

        {isLive && (
          <div className="mt-3 rounded-xl border border-sky-400/10 bg-sky-400/[0.025] px-4 py-3">
            <p className="text-[10px] leading-5 text-slate-500">
              FortyGuard-backed analysis fuses hyperlocal temperature cells with
              Open-Meteo environmental context aligned to the same NYC location,
              date and hour. Humidity, wet-bulb temperature and solar radiation
              are contextual weather-model values rather than FortyGuard hyperlocal
              measurements. Heat index is calculated from the fused temperature
              and humidity inputs.
            </p>
          </div>
        )}

        <section className="mt-5">

          <HistoricalPanel
            historical={
              zone.historical
            }
          />

        </section>

        <section className="mt-5">

          <VulnerabilityPanel
            vulnerability={
              zone.vulnerability
            }
          />

        </section>

        <section className="mt-5 grid gap-5 xl:grid-cols-[1.15fr_0.85fr]">

          <ForecastPanel
            forecast={
              zone.forecast
            }
            mode={safeMode}
          />

          <DecisionPanel
            recommendations={
              zone.recommendations
            }
            riskLevel={
              zone.risk_level
            }
          />

        </section>

        <section className="mt-5 grid gap-5 xl:grid-cols-3">

          <HotspotPanel
            hotspots={
              data.hotspots
            }
            selectedTile={
              zone.tile_id
            }
            onSelect={(
              tileId,
            ) =>
              loadAnalysis(
                tileId,
              )
            }
          />

          <RiskDriverPanel
            factors={
              zone.factors
            }
            mode={safeMode}
          />

          <ClimateSummary
            data={data}
            mode={safeMode}
          />

        </section>

        <section className="mt-5">

          <InterventionSimulator
            interventions={
              zone.interventions
            }
          />

        </section>

        <footer className="mt-8 flex flex-col gap-2 border-t border-slate-800/60 py-5 text-xs text-slate-600 md:flex-row md:items-center md:justify-between">

          <p>
            AI HeatShield • Hyperlocal
            Heat Risk & Urban Decision
            Intelligence
          </p>

          <p>
            {
              data
                .location
                .city
            }
            ,{" "}
            {
              data
                .location
                .state
            }{" "}
            • {safeMode} Mode
          </p>

        </footer>

      </div>
    </main>
  );
}

function TopHeader({
  data,
  mode,
  lastUpdated,
  onRefresh,
  refreshing,
}: {
  data: AnalysisData;
  mode: string;
  lastUpdated: string;
  onRefresh: () => void;
  refreshing: boolean;
}) {
  const isLive =
    mode === "LIVE" ||
    mode === "CACHED_LIVE";

  const modeLabel =
    mode === "LIVE"
      ? "Live Data"
      : mode === "CACHED_LIVE"
        ? "Cached Live"
        : mode === "DEMO_FALLBACK"
          ? "Demo Fallback"
          : "Demo Mode";

  return (
    <header className="rounded-2xl border border-slate-800/70 bg-[#0c1620]/85 px-4 py-4 backdrop-blur-xl md:px-5">

      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">

        <div className="flex items-center gap-3">

          <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-amber-400/20 bg-amber-400/10">

            <span className="text-sm font-bold text-amber-300">
              AH
            </span>

          </div>

          <div>

            <div className="flex flex-wrap items-center gap-2.5">

              <h1 className="text-lg font-semibold tracking-[-0.02em]">
                AI HeatShield
              </h1>

              <span
                className={`flex items-center gap-2 rounded-full border px-2.5 py-1 text-[10px] font-medium ${
                  isLive
                    ? "border-emerald-400/15 bg-emerald-400/[0.07] text-emerald-300"
                    : "border-amber-400/15 bg-amber-400/[0.07] text-amber-300"
                }`}
              >

                <span
                  className={`h-1.5 w-1.5 rounded-full ${
                    isLive
                      ? "bg-emerald-400"
                      : "bg-amber-400"
                  }`}
                />

                {refreshing
                  ? "Updating Live Data"
                  : modeLabel}

              </span>

            </div>

            <p className="mt-1 text-xs text-slate-500">
              Hyperlocal Heat Risk &
              Urban Decision Intelligence
            </p>

          </div>

        </div>

        <div className="flex flex-wrap items-center gap-2.5">

          <HeaderInfo
            label="Location"
            value={`${data.location.city}, ${data.location.state}`}
          />

          <HeaderInfo
            label="Source Mode"
            value={mode}
          />

          <HeaderInfo
            label="Heat Cells"
            value={`${data.map_tiles.length}`}
          />

          <HeaderInfo
            label="Last Update"
            value={
              lastUpdated ||
              "--"
            }
          />

          <button
            type="button"
            onClick={
              onRefresh
            }
            disabled={
              refreshing
            }
            className="h-[42px] rounded-xl border border-slate-700 bg-slate-800/70 px-4 text-xs font-medium text-slate-300 transition hover:border-slate-600 hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {refreshing
              ? "Updating..."
              : "Refresh Data"}
          </button>

        </div>

      </div>

    </header>
  );
}

function HeroOverview({
  data,
  mode,
}: {
  data: AnalysisData;
  mode: string;
}) {
  const zone =
    data.selected_zone;

  const isLive =
    mode === "LIVE" ||
    mode === "CACHED_LIVE";

  return (
    <section className="relative overflow-hidden rounded-2xl border border-slate-800/70 bg-[#0c1620]/78 p-6 backdrop-blur-xl md:p-7">

      <div className="absolute right-0 top-0 h-52 w-52 rounded-full bg-sky-400/[0.045] blur-3xl" />

      <div className="relative">

        <div className="flex flex-wrap items-center gap-2">

          <span className="rounded-full border border-sky-400/15 bg-sky-400/[0.06] px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-sky-300">
            Climate Intelligence
          </span>

          <span className="text-xs text-slate-600">
            Selected zone:{" "}
            {zone.tile_id}
          </span>

        </div>

        <h2 className="mt-5 max-w-3xl text-3xl font-semibold leading-[1.15] tracking-[-0.04em] text-slate-100 md:text-[38px]">

          Hyperlocal heat intelligence

          <span className="block text-slate-400">
            for safer urban decisions.
          </span>

        </h2>

        <p className="mt-4 max-w-2xl text-[14px] leading-7 text-slate-400">
          Monitor urban heat, identify
          priority hotspots, predict
          thermal risk, understand
          environmental drivers and
          evaluate cooling interventions
          from one intelligent
          decision-support platform.
        </p>

        <div className="mt-7 grid max-w-3xl grid-cols-2 gap-3 md:grid-cols-4">

          <MiniInfo
            label="Latitude"
            value={zone.latitude.toFixed(
              4,
            )}
          />

          <MiniInfo
            label="Longitude"
            value={zone.longitude.toFixed(
              4,
            )}
          />

          <MiniInfo
            label={
              isLive
                ? "Wet Bulb • Open-Meteo"
                : "Wet Bulb"
            }
            value={`${zone.wet_bulb}°C`}
          />

          <MiniInfo
            label="Country"
            value={
              data
                .location
                .country
            }
          />

        </div>

      </div>

    </section>
  );
}

function RiskCard({
  score,
  level,
  primaryDriver,
}: {
  score: number;
  level: string;
  primaryDriver: string;
}) {
  const radius = 54;

  const circumference =
    2 *
    Math.PI *
    radius;

  const progress =
    (Math.min(
      Math.max(
        score,
        0,
      ),
      100,
    ) /
      100) *
    circumference;

  return (
    <section className="rounded-2xl border border-amber-400/10 bg-[#0c1620]/85 p-6 backdrop-blur-xl">

      <div className="flex items-center justify-between">

        <div>

          <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-500">
            Current Risk
          </p>

          <h3 className="mt-1 text-lg font-semibold">
            Heat Risk Score
          </h3>

        </div>

        <RiskBadge
          level={level}
        />

      </div>

      <div className="mt-5 flex justify-center">

        <div className="relative h-40 w-40">

          <svg
            viewBox="0 0 130 130"
            className="h-full w-full -rotate-90"
          >

            <circle
              cx="65"
              cy="65"
              r={radius}
              fill="none"
              stroke="rgba(148,163,184,0.10)"
              strokeWidth="9"
            />

            <circle
              cx="65"
              cy="65"
              r={radius}
              fill="none"
              stroke="#f59e0b"
              strokeWidth="9"
              strokeLinecap="round"
              strokeDasharray={`${progress} ${circumference}`}
            />

          </svg>

          <div className="absolute inset-0 flex flex-col items-center justify-center">

            <span className="text-4xl font-semibold tracking-[-0.05em]">
              {score}
            </span>

            <span className="mt-1 text-[10px] uppercase tracking-[0.2em] text-slate-600">
              / 100
            </span>

          </div>

        </div>

      </div>

      <div className="mt-4 rounded-xl border border-slate-800 bg-[#081018]/60 p-4">

        <p className="text-[10px] uppercase tracking-[0.18em] text-slate-600">
          Main driver
        </p>

        <p className="mt-1.5 text-sm font-medium text-amber-200">
          {primaryDriver}
        </p>

      </div>

    </section>
  );
}

function MetricCard({
  label,
  value,
  subtitle,
  badge,
}: {
  label: string;
  value: string;
  subtitle: string;
  badge: string;
}) {
  return (
    <section className="group rounded-2xl border border-slate-800/70 bg-[#0c1620]/75 p-5 backdrop-blur-lg transition duration-200 hover:-translate-y-0.5 hover:border-slate-700">

      <div className="flex items-center justify-between">

        <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-500">
          {label}
        </p>

        <span className="rounded-lg border border-slate-800 bg-slate-900/60 px-2 py-1 text-[9px] font-semibold tracking-wider text-slate-500">
          {badge}
        </span>

      </div>

      <p className="mt-5 text-2xl font-semibold tracking-[-0.03em] text-slate-100">
        {value}
      </p>

      <p className="mt-1.5 text-xs text-slate-500">
        {subtitle}
      </p>

    </section>
  );
}

function HistoricalPanel({
  historical,
}: {
  historical: HistoricalComparison;
}) {
  const history =
    historical?.history || [];

  const maxRisk =
    Math.max(
      ...history.map(
        (item) =>
          item.risk_score,
      ),
      100,
    );

  return (
    <Panel
      eyebrow="Historical Intelligence"
      title="Historical Heat Comparison"
      subtitle="Estimated historical baseline and recent trend for the currently selected heat cell."
    >

      <div className="mt-5 grid gap-4 lg:grid-cols-[0.9fr_1.1fr]">

        <div className="grid gap-3 sm:grid-cols-3 lg:grid-cols-1">

          <HistoricalMetric
            label="Temperature"
            current={`${historical.current_temperature}°C`}
            baseline={`${historical.baseline_temperature}°C`}
            difference={
              historical.temperature_difference
            }
            suffix="°C"
          />

          <HistoricalMetric
            label="Heat Index"
            current={`${historical.current_heat_index}°C`}
            baseline={`${historical.baseline_heat_index}°C`}
            difference={
              historical.heat_index_difference
            }
            suffix="°C"
          />

          <HistoricalMetric
            label="Risk Score"
            current={`${historical.current_risk_score}`}
            baseline={`${historical.baseline_risk_score}`}
            difference={
              historical.risk_difference
            }
            suffix=" pts"
          />

        </div>

        <div className="rounded-xl border border-slate-800/70 bg-[#081018]/45 p-4">

          <div className="flex flex-wrap items-center justify-between gap-3">

            <div>

              <p className="text-xs font-medium text-slate-300">
                Risk Trend
              </p>

              <p className="mt-1 text-[10px] text-slate-600">
                Relative risk progression
                across the demo historical
                window.
              </p>

            </div>

            <span
              className={`rounded-full border px-3 py-1 text-[9px] font-semibold uppercase tracking-wider ${
                historical.trend ===
                "WARMING"
                  ? "border-rose-400/20 bg-rose-400/[0.08] text-rose-300"
                  : historical.trend ===
                      "COOLING"
                    ? "border-emerald-400/20 bg-emerald-400/[0.08] text-emerald-300"
                    : "border-slate-700 bg-slate-800/50 text-slate-400"
              }`}
            >
              {
                historical.trend
              }
            </span>

          </div>

          <div className="mt-6 flex h-[180px] items-end gap-3">

            {history.map(
              (point) => {
                const height =
                  Math.max(
                    14,
                    (point.risk_score /
                      maxRisk) *
                      100,
                  );

                return (
                  <div
                    key={
                      point.label
                    }
                    className="flex h-full flex-1 flex-col justify-end"
                  >

                    <div className="mb-2 text-center">

                      <p className="text-[10px] font-medium text-slate-300">
                        {
                          point.risk_score
                        }
                      </p>

                    </div>

                    <div className="flex flex-1 items-end">

                      <div
                        className="w-full rounded-t-lg bg-gradient-to-t from-amber-500/40 to-rose-400/90 transition-all duration-700"
                        style={{
                          height: `${height}%`,
                        }}
                      />

                    </div>

                    <p className="mt-2 text-center text-[9px] leading-4 text-slate-600">
                      {
                        point.label
                      }
                    </p>

                  </div>
                );
              },
            )}

          </div>

          <div className="mt-4 grid grid-cols-2 gap-2 border-t border-slate-800/70 pt-4 md:grid-cols-3">

            {history.map(
              (point) => (
                <div
                  key={`${point.label}-detail`}
                  className="rounded-lg bg-slate-900/40 px-3 py-2"
                >

                  <p className="text-[9px] text-slate-600">
                    {
                      point.label
                    }
                  </p>

                  <p className="mt-1 text-[11px] font-medium text-slate-300">
                    {
                      point.temperature
                    }
                    °C
                  </p>

                  <p className="mt-0.5 text-[9px] text-slate-600">
                    Heat index{" "}
                    {
                      point.heat_index
                    }
                    °C
                  </p>

                </div>
              ),
            )}

          </div>

        </div>

      </div>

      <div className="mt-4 rounded-xl border border-amber-400/10 bg-amber-400/[0.025] px-4 py-3">

        <p className="text-[10px] leading-5 text-slate-600">
          Historical values are
          currently generated from an
          estimated demo baseline for
          product demonstration. They
          should not be interpreted as
          observed FortyGuard historical
          measurements.
        </p>

      </div>

    </Panel>
  );
}

function HistoricalMetric({
  label,
  current,
  baseline,
  difference,
  suffix,
}: {
  label: string;
  current: string;
  baseline: string;
  difference: number;
  suffix: string;
}) {
  const increasing =
    difference > 0;

  const decreasing =
    difference < 0;

  return (
    <div className="rounded-xl border border-slate-800/70 bg-[#081018]/45 p-4">

      <p className="text-[9px] font-semibold uppercase tracking-[0.18em] text-slate-600">
        {label}
      </p>

      <div className="mt-3 flex items-end justify-between gap-3">

        <div>

          <p className="text-[9px] uppercase tracking-wider text-slate-600">
            Current
          </p>

          <p className="mt-1 text-xl font-semibold text-slate-200">
            {current}
          </p>

        </div>

        <div className="text-right">

          <p className="text-[9px] uppercase tracking-wider text-slate-600">
            Baseline
          </p>

          <p className="mt-1 text-sm font-medium text-slate-400">
            {baseline}
          </p>

        </div>

      </div>

      <div className="mt-4 flex items-center justify-between border-t border-slate-800 pt-3">

        <span className="text-[10px] text-slate-600">
          Difference
        </span>

        <span
          className={`text-xs font-semibold ${
            increasing
              ? "text-rose-300"
              : decreasing
                ? "text-emerald-300"
                : "text-slate-400"
          }`}
        >
          {difference > 0
            ? "+"
            : ""}
          {difference.toFixed(
            1,
          )}
          {suffix}
        </span>

      </div>

    </div>
  );
}

function VulnerabilityPanel({
  vulnerability,
}: {
  vulnerability: VulnerabilityResponse;
}) {
  if (!vulnerability) {
    return null;
  }

  return (
    <Panel
      eyebrow="Human Vulnerability Intelligence"
      title="Persona Heat Risk Assessment"
      subtitle="Decision-support estimate of how the same thermal conditions may affect different population groups."
    >

      <div className="mt-5 rounded-xl border border-amber-400/10 bg-amber-400/[0.03] p-4">

        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">

          <div>

            <p className="text-[9px] font-semibold uppercase tracking-[0.18em] text-slate-600">
              Most Vulnerable Persona
            </p>

            <p className="mt-1.5 text-lg font-semibold text-amber-200">
              {
                vulnerability
                  .most_vulnerable_persona
              }
            </p>

          </div>

          <div className="flex items-center gap-5">

            <div>

              <p className="text-[9px] uppercase tracking-[0.16em] text-slate-600">
                Base Risk
              </p>

              <p className="mt-1 text-sm font-semibold text-slate-300">
                {
                  vulnerability
                    .base_risk_score
                }
              </p>

            </div>

            <div>

              <p className="text-[9px] uppercase tracking-[0.16em] text-slate-600">
                Base Level
              </p>

              <p className="mt-1 text-sm font-semibold text-rose-300">
                {
                  vulnerability
                    .base_risk_level
                }
              </p>

            </div>

          </div>

        </div>

      </div>

      <div className="mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-4">

        {(vulnerability.personas || []).map(
          (persona) => (
            <PersonaCard
              key={
                persona.persona
              }
              persona={
                persona
              }
            />
          ),
        )}

      </div>

      <div className="mt-4 rounded-xl border border-slate-800/60 bg-slate-900/30 px-4 py-3">

        <p className="text-[10px] leading-5 text-slate-600">
          Persona vulnerability scores
          are heuristic decision-support
          estimates. They are not
          medical, clinical, or
          individual health-risk
          predictions.
        </p>

      </div>

    </Panel>
  );
}

function PersonaCard({
  persona,
}: {
  persona: PersonaRisk;
}) {
  return (
    <article className="rounded-xl border border-slate-800/70 bg-[#081018]/45 p-4 transition duration-200 hover:-translate-y-0.5 hover:border-slate-700">

      <div className="flex items-start justify-between gap-3">

        <div>

          <p className="text-sm font-semibold text-slate-200">
            {
              persona.persona
            }
          </p>

          <p className="mt-1 text-[9px] uppercase tracking-[0.16em] text-slate-600">
            Sensitivity ×
            {persona.sensitivity_multiplier.toFixed(
              2,
            )}
          </p>

        </div>

        <RiskBadge
          level={
            persona.risk_level
          }
        />

      </div>

      <div className="mt-5 flex items-end gap-2">

        <span className="text-3xl font-semibold tracking-[-0.04em] text-slate-100">
          {
            persona.risk_score
          }
        </span>

        <span className="pb-1 text-[10px] uppercase tracking-[0.14em] text-slate-600">
          / 100
        </span>

      </div>

      <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-slate-800">

        <div
          className={`h-full rounded-full transition-all duration-700 ${riskBarClass(
            persona.risk_level,
          )}`}
          style={{
            width: `${Math.min(
              persona.risk_score,
              100,
            )}%`,
          }}
        />

      </div>

      <div className="mt-4 border-t border-slate-800/70 pt-4">

        <p className="text-[9px] font-semibold uppercase tracking-[0.16em] text-slate-600">
          Why this group is vulnerable
        </p>

        <p className="mt-2 text-[11px] leading-5 text-slate-400">
          {
            persona.primary_reason
          }
        </p>

      </div>

      <div className="mt-4 rounded-lg border border-sky-400/10 bg-sky-400/[0.025] p-3">

        <p className="text-[9px] font-semibold uppercase tracking-[0.16em] text-sky-300/70">
          Recommended Action
        </p>

        <p className="mt-2 text-[11px] leading-5 text-slate-400">
          {
            persona.recommended_action
          }
        </p>

      </div>

    </article>
  );
}

function RiskBadge({
  level,
}: {
  level?: string;
}) {
  const normalized =
    typeof level === "string"
      ? level.toUpperCase()
      : "LOW";

  if (
    normalized ===
    "CRITICAL"
  ) {
    return (
      <span className="rounded-full border border-rose-400/25 bg-rose-400/[0.09] px-2.5 py-1 text-[9px] font-semibold uppercase tracking-wider text-rose-300">
        Critical
      </span>
    );
  }

  if (
    normalized ===
    "VERY HIGH"
  ) {
    return (
      <span className="rounded-full border border-orange-400/20 bg-orange-400/[0.08] px-2.5 py-1 text-[9px] font-semibold uppercase tracking-wider text-orange-300">
        Very High
      </span>
    );
  }

  if (
    normalized ===
    "HIGH"
  ) {
    return (
      <span className="rounded-full border border-amber-400/20 bg-amber-400/[0.08] px-2.5 py-1 text-[9px] font-semibold uppercase tracking-wider text-amber-300">
        High
      </span>
    );
  }

  if (
    normalized ===
    "MODERATE"
  ) {
    return (
      <span className="rounded-full border border-yellow-400/20 bg-yellow-400/[0.08] px-2.5 py-1 text-[9px] font-semibold uppercase tracking-wider text-yellow-300">
        Moderate
      </span>
    );
  }

  return (
    <span className="rounded-full border border-emerald-400/20 bg-emerald-400/[0.08] px-2.5 py-1 text-[9px] font-semibold uppercase tracking-wider text-emerald-300">
      Low
    </span>
  );
}

function riskBarClass(
  level?: string,
) {
  const normalized =
    typeof level === "string"
      ? level.toUpperCase()
      : "LOW";

  switch (
    normalized
  ) {
    case "CRITICAL":
      return "bg-rose-500";

    case "VERY HIGH":
      return "bg-orange-500";

    case "HIGH":
      return "bg-amber-400";

    case "MODERATE":
      return "bg-yellow-400";

    default:
      return "bg-emerald-400";
  }
}

function ForecastPanel({
  forecast,
  mode,
}: {
  forecast: ForecastPoint[];
  mode: string;
}) {
  return (
    <Panel
      eyebrow="Predictive Intelligence"
      title="12-Hour Risk Outlook"
      subtitle="Projected heat-risk trajectory for the currently selected zone."
    >

      <div className="mt-5 grid gap-3">

        {(forecast || []).map(
          (point) => (
            <div
              key={
                point.hours_ahead
              }
              className="rounded-xl border border-slate-800/70 bg-[#081018]/45 px-4 py-3.5"
            >

              <div className="flex items-center gap-4">

                <div className="w-[76px] shrink-0">

                  <p className="text-sm font-medium">
                    {point.hours_ahead ===
                    0
                      ? "Now"
                      : `+${point.hours_ahead} hr`}
                  </p>

                  <p className="mt-0.5 text-[11px] text-slate-600">
                    {
                      point.temperature
                    }
                    °C
                  </p>

                </div>

                <div className="min-w-0 flex-1">

                  <div className="h-1.5 overflow-hidden rounded-full bg-slate-800">

                    <div
                      className="h-full rounded-full bg-amber-400 transition-all duration-700"
                      style={{
                        width: `${Math.min(
                          point.risk_score,
                          100,
                        )}%`,
                      }}
                    />

                  </div>

                </div>

                <div className="w-[78px] shrink-0 text-right">

                  <p className="text-sm font-semibold">
                    {
                      point.risk_score
                    }
                  </p>

                  <p className="mt-0.5 text-[9px] font-medium uppercase tracking-wider text-rose-300">
                    {
                      point.risk_level
                    }
                  </p>

                </div>

              </div>

            </div>
          ),
        )}

      </div>

      <div className="mt-4 rounded-xl border border-slate-800/60 bg-slate-900/30 px-4 py-3">

        <p className="text-[10px] leading-5 text-slate-600">
          {mode === "LIVE" || mode === "CACHED_LIVE"
            ? "Future temperature points shown here come from cached FortyGuard forecast heatmaps for +3/+6/+9/+12 hours. Open-Meteo supplies environmental forecast-model context aligned to each hour, and AI HeatShield recalculates the risk score from the nearest future heat cell. Risk scores are AI HeatShield outputs, not FortyGuard risk predictions."
            : "Future forecast points are unavailable until a successful FortyGuard refresh. The current point remains available from the active dashboard dataset."}
        </p>

      </div>

    </Panel>
  );
}

function DecisionPanel({
  recommendations,
  riskLevel,
}: {
  recommendations: Recommendation[];
  riskLevel: string;
}) {
  return (
    <Panel
      eyebrow="Decision Intelligence"
      title="Recommended Actions"
      subtitle={`Prioritized response actions for ${riskLevel.toLowerCase()} thermal conditions.`}
    >

      <div className="mt-5 space-y-3">

        {(recommendations || [])
          .slice(0, 5)
          .map((item) => (
            <article
              key={`${item.priority}-${item.title}`}
              className="rounded-xl border border-slate-800/70 bg-[#081018]/45 p-4 transition hover:border-slate-700"
            >

              <div className="flex gap-3.5">

                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-amber-400/15 bg-amber-400/[0.07] text-xs font-semibold text-amber-300">
                  {
                    item.priority
                  }
                </div>

                <div className="min-w-0">

                  <div className="flex flex-wrap items-center gap-2">

                    <p className="text-sm font-medium text-slate-200">
                      {
                        item.title
                      }
                    </p>

                    <span className="rounded-full bg-slate-800/60 px-2 py-0.5 text-[9px] font-medium uppercase tracking-wider text-slate-500">
                      {
                        item.category
                      }
                    </span>

                  </div>

                  <p className="mt-2 text-xs leading-5 text-slate-500">
                    {
                      item.action
                    }
                  </p>

                  {item.reason && (
                    <p className="mt-2 text-[10px] leading-4 text-slate-600">
                      Why:{" "}
                      {
                        item.reason
                      }
                    </p>
                  )}

                </div>

              </div>

            </article>
          ))}

      </div>

    </Panel>
  );
}

function HotspotPanel({
  hotspots,
  selectedTile,
  onSelect,
}: {
  hotspots: Hotspot[];
  selectedTile: string;
  onSelect: (
    tileId: string,
  ) => void;
}) {
  return (
    <Panel
      eyebrow="Spatial Intelligence"
      title="Priority Hotspots"
      subtitle="Highest-risk zones detected across the active analysis area."
    >

      <div className="mt-5 space-y-2.5">

        {(hotspots || []).map(
          (hotspot) => {
            const selected =
              hotspot.tile_id ===
              selectedTile;

            return (
              <button
                type="button"
                key={
                  hotspot.tile_id
                }
                onClick={() =>
                  onSelect(
                    hotspot.tile_id,
                  )
                }
                className={`w-full rounded-xl border p-3.5 text-left transition ${
                  selected
                    ? "border-sky-400/25 bg-sky-400/[0.06]"
                    : "border-slate-800/70 bg-[#081018]/45 hover:border-slate-700"
                }`}
              >

                <div className="flex items-center justify-between gap-3">

                  <div className="flex items-center gap-3">

                    <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-slate-800/70 text-xs font-semibold text-slate-300">
                      #
                      {
                        hotspot.rank
                      }
                    </span>

                    <div>

                      <p className="text-sm font-medium">
                        {
                          hotspot.tile_id
                        }
                      </p>

                      <p className="mt-0.5 text-[11px] text-slate-600">
                        {
                          hotspot.temperature
                        }
                        °C
                      </p>

                    </div>

                  </div>

                  <div className="text-right">

                    <p className="text-sm font-semibold">
                      {
                        hotspot.risk_score
                      }
                    </p>

                    <p className="mt-0.5 text-[9px] uppercase tracking-wider text-rose-300">
                      {
                        hotspot.risk_level
                      }
                    </p>

                  </div>

                </div>

              </button>
            );
          },
        )}

      </div>

    </Panel>
  );
}

function RiskDriverPanel({
  factors,
  mode,
}: {
  factors: RiskFactor[];
  mode: string;
}) {
  const sorted = [
    ...(factors || []),
  ].sort(
    (a, b) =>
      b.contribution -
      a.contribution,
  );

  const max =
    Math.max(
      ...sorted.map(
        (factor) =>
          factor.contribution,
      ),
      1,
    );

  return (
    <Panel
      eyebrow="Explainable Intelligence"
      title="Risk Drivers"
      subtitle="Environmental contribution behind the current risk assessment."
    >

      <div className="mt-5 space-y-4">

        {sorted.map(
          (factor) => (
            <div
              key={
                factor.name
              }
            >

              <div className="mb-1.5 flex justify-between gap-3">

                <span className="text-xs text-slate-400">
                  {
                    factor.name
                  }
                </span>

                <span className="text-xs font-medium text-slate-300">
                  {factor.contribution.toFixed(
                    1,
                  )}
                </span>

              </div>

              <div className="h-1.5 overflow-hidden rounded-full bg-slate-800">

                <div
                  className="h-full rounded-full bg-sky-400/80 transition-all duration-700"
                  style={{
                    width: `${
                      (factor.contribution /
                        max) *
                      100
                    }%`,
                  }}
                />

              </div>

            </div>
          ),
        )}

      </div>

      {(mode === "LIVE" || mode === "CACHED_LIVE") && (
        <div className="mt-4 rounded-xl border border-slate-800/60 bg-slate-900/30 px-4 py-3">
          <p className="text-[10px] leading-5 text-slate-600">
            Driver contributions use FortyGuard hyperlocal temperature,
            Open-Meteo contextual humidity/wet-bulb/solar inputs, and a
            calculated heat index. They are explainable model contributions,
            not separate sensor measurements.
          </p>
        </div>
      )}

    </Panel>
  );
}

function ClimateSummary({
  data,
  mode,
}: {
  data: AnalysisData;
  mode: string;
}) {
  const spread =
    data
      .statistics
      .temperature_max -
    data
      .statistics
      .temperature_min;

  return (
    <Panel
      eyebrow="Thermal Summary"
      title="Area Climate Profile"
      subtitle="Temperature statistics for the active geographic analysis."
    >

      <div className="mt-5 space-y-2.5">

        <SummaryRow
          label="Minimum Temperature"
          value={`${data.statistics.temperature_min}°C`}
        />

        <SummaryRow
          label="Mean Temperature"
          value={`${data.statistics.temperature_mean}°C`}
        />

        <SummaryRow
          label="Maximum Temperature"
          value={`${data.statistics.temperature_max}°C`}
        />

        <SummaryRow
          label="Temperature Spread"
          value={`${spread.toFixed(
            1,
          )}°C`}
        />

        <SummaryRow
          label="Total Heat Cells"
          value={`${data.map_tiles.length}`}
        />

        <SummaryRow
          label="Analysis Mode"
          value={mode}
        />

        {(mode === "LIVE" || mode === "CACHED_LIVE") && (
          <>
            <SummaryRow
              label="Hyperlocal Temperature"
              value="FortyGuard"
            />

            <SummaryRow
              label="Environmental Context"
              value="Open-Meteo"
            />

            <SummaryRow
              label="Heat Index"
              value="Calculated"
            />
          </>
        )}

      </div>

      {(mode === "LIVE" || mode === "CACHED_LIVE") && (
        <div className="mt-4 rounded-xl border border-sky-400/10 bg-sky-400/[0.025] px-4 py-3">
          <p className="text-[10px] leading-5 text-slate-600">
            FortyGuard provides the spatial temperature field. Open-Meteo
            provides aligned area-level environmental context; those contextual
            variables should not be interpreted as 100 m FortyGuard
            measurements.
          </p>
        </div>
      )}

    </Panel>
  );
}

function InterventionSimulator({
  interventions,
}: {
  interventions: Intervention[];
}) {
  return (
    <Panel
      eyebrow="Urban Intervention Simulator"
      title="Estimated Cooling Impact"
      subtitle="Scenario-based comparison between current risk and possible heat mitigation strategies."
    >

      <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-4">

        {(interventions || []).map(
          (item) => (
            <article
              key={
                item.name
              }
              className="rounded-xl border border-slate-800/70 bg-[#081018]/45 p-4 transition duration-200 hover:border-slate-700"
            >

              <p className="min-h-10 text-sm font-medium text-slate-200">
                {item.name}
              </p>

              <div className="mt-4 flex items-end gap-2">

                <span className="text-xl font-medium text-slate-600 line-through">
                  {
                    item.before_score
                  }
                </span>

                <span className="pb-0.5 text-slate-700">
                  →
                </span>

                <span className="text-2xl font-semibold text-emerald-300">
                  {
                    item.after_score
                  }
                </span>

              </div>

              <div className="mt-4 border-t border-slate-800 pt-3">

                <div className="flex items-center justify-between">

                  <span className="text-[11px] text-slate-600">
                    Risk reduction
                  </span>

                  <span className="text-xs font-medium text-emerald-300">
                    −
                    {
                      item.reduction_percent
                    }
                    %
                  </span>

                </div>

                <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-slate-800">

                  <div
                    className="h-full rounded-full bg-emerald-400/80"
                    style={{
                      width: `${Math.min(
                        Math.max(
                          item.reduction_percent,
                          0,
                        ),
                        100,
                      )}%`,
                    }}
                  />

                </div>

                <p className="mt-2 text-[10px] text-slate-600">
                  −
                  {
                    item.reduction_points
                  }{" "}
                  risk points
                </p>

              </div>

            </article>
          ),
        )}

      </div>

      <div className="mt-4 rounded-xl border border-slate-800/60 bg-slate-900/30 px-4 py-3">

        <p className="text-[10px] leading-5 text-slate-600">
          Intervention outcomes are
          scenario-based
          decision-support estimates
          and are not validated causal
          predictions.
        </p>

      </div>

    </Panel>
  );
}

function Panel({
  eyebrow,
  title,
  subtitle,
  children,
}: {
  eyebrow: string;
  title: string;
  subtitle: string;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-2xl border border-slate-800/70 bg-[#0c1620]/75 p-5 backdrop-blur-lg">

      <p className="text-[9px] font-semibold uppercase tracking-[0.2em] text-sky-300/70">
        {eyebrow}
      </p>

      <h3 className="mt-1.5 text-base font-semibold tracking-[-0.02em] text-slate-100">
        {title}
      </h3>

      <p className="mt-1.5 max-w-2xl text-xs leading-5 text-slate-500">
        {subtitle}
      </p>

      {children}

    </section>
  );
}

function HeaderInfo({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div className="min-w-[100px] rounded-xl border border-slate-800/70 bg-[#081018]/55 px-3 py-2">

      <p className="text-[8px] font-semibold uppercase tracking-[0.16em] text-slate-600">
        {label}
      </p>

      <p className="mt-0.5 text-[11px] font-medium text-slate-300">
        {value}
      </p>

    </div>
  );
}

function MiniInfo({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-xl border border-slate-800/60 bg-[#081018]/45 px-3 py-3">

      <p className="text-[8px] font-semibold uppercase tracking-[0.16em] text-slate-600">
        {label}
      </p>

      <p className="mt-1 text-xs font-medium text-slate-300">
        {value}
      </p>

    </div>
  );
}

function SummaryRow({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div className="flex items-center justify-between gap-4 rounded-xl border border-slate-800/60 bg-[#081018]/40 px-3.5 py-3">

      <span className="text-xs text-slate-500">
        {label}
      </span>

      <span className="text-xs font-medium text-slate-300">
        {value}
      </span>

    </div>
  );
}

function LoadingScreen() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-[#081018] text-slate-100">

      <div className="text-center">

        <div className="mx-auto h-9 w-9 animate-spin rounded-full border-2 border-slate-800 border-t-amber-400" />

        <p className="mt-4 text-sm font-medium">
          AI HeatShield
        </p>

        <p className="mt-1 text-xs text-slate-600">
          Loading climate
          intelligence...
        </p>

      </div>

    </main>
  );
}

function ErrorScreen({
  message,
}: {
  message: string;
}) {
  return (
    <main className="flex min-h-screen items-center justify-center bg-[#081018] px-4 text-slate-100">

      <div className="w-full max-w-md rounded-2xl border border-rose-400/15 bg-[#0c1620] p-6 text-center">

        <div className="mx-auto flex h-10 w-10 items-center justify-center rounded-xl bg-rose-400/[0.08] text-sm font-semibold text-rose-300">
          !
        </div>

        <h2 className="mt-4 text-base font-semibold">
          Backend unavailable
        </h2>

        <p className="mt-2 text-xs leading-5 text-slate-500">
          {message}
        </p>

        <p className="mt-3 break-all text-[10px] text-slate-600">
          API:{" "}
          {API_BASE_URL}
        </p>

      </div>

    </main>
  );
}

function signed(
  value: number,
) {
  if (value > 0) {
    return `+${value.toFixed(
      1,
    )}`;
  }

  return value.toFixed(
    1,
  );
}