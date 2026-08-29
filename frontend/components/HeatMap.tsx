"use client";

import {
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  MapContainer,
  Popup,
  Rectangle,
  TileLayer,
  Tooltip,
  useMap,
} from "react-leaflet";

import type {
  LatLngBoundsExpression,
} from "leaflet";

import "leaflet/dist/leaflet.css";

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

type SelectedZone = {
  tile_id: string;
  latitude: number;
  longitude: number;
  temperature: number;
  risk_score: number;
  risk_level: string;
};

type HeatMapProps = {
  tiles: MapTile[];
  selectedZone: SelectedZone;
  mode?: string;
  onSelect: (tileId: string) => void;
};

type LayerType =
  | "risk"
  | "temperature"
  | "heat_index";

const HALF_LAT = 0.0004;
const HALF_LNG = 0.00045;

export default function HeatMap({
  tiles,
  selectedZone,
  mode = "DEMO",
  onSelect,
}: HeatMapProps) {
  const [layer, setLayer] =
    useState<LayerType>("risk");

  const safeMode =
    typeof mode === "string"
      ? mode.trim().toUpperCase()
      : "DEMO";

  const isLive =
    safeMode === "LIVE";

  const temperatureRange =
    useMemo(() => {
      if (!tiles?.length) {
        return {
          min: 0,
          max: 1,
        };
      }

      const values =
        tiles.map(
          (tile) =>
            tile.temperature,
        );

      return {
        min: Math.min(
          ...values,
        ),
        max: Math.max(
          ...values,
        ),
      };
    }, [tiles]);

  const heatIndexRange =
    useMemo(() => {
      if (!tiles?.length) {
        return {
          min: 0,
          max: 1,
        };
      }

      const values =
        tiles.map(
          (tile) =>
            tile.heat_index,
        );

      return {
        min: Math.min(
          ...values,
        ),
        max: Math.max(
          ...values,
        ),
      };
    }, [tiles]);

  if (!tiles?.length) {
    return (
      <div className="flex h-[560px] items-center justify-center rounded-2xl border border-slate-800/70 bg-[#081018]">
        <p className="text-sm text-slate-500">
          No spatial heat data available.
        </p>
      </div>
    );
  }

  if (!selectedZone) {
    return (
      <div className="flex h-[560px] items-center justify-center rounded-2xl border border-slate-800/70 bg-[#081018]">
        <p className="text-sm text-slate-500">
          No selected zone available.
        </p>
      </div>
    );
  }

  return (
    <div className="relative overflow-hidden rounded-2xl border border-slate-800/70 bg-[#081018] shadow-2xl shadow-black/20">

      <div className="absolute left-4 top-4 z-[1000]">
        <div className="rounded-xl border border-slate-700/70 bg-[#081018]/95 px-3.5 py-3 shadow-xl backdrop-blur-xl">

          <div className="flex items-center gap-2">

            <span
              className={`h-2 w-2 rounded-full ${
                isLive
                  ? "bg-emerald-400"
                  : "bg-amber-400"
              }`}
            />

            <p
              className={`text-[10px] font-semibold uppercase tracking-[0.16em] ${
                isLive
                  ? "text-emerald-300"
                  : "text-amber-300"
              }`}
            >
              {isLive
                ? "Live Spatial Monitoring"
                : "Demo Spatial Model"}
            </p>

          </div>

          <p className="mt-1.5 text-[9px] text-slate-500">
            {isLive
              ? "FortyGuard-powered heat data"
              : "Synthetic demonstration dataset"}
          </p>

        </div>
      </div>

      <div className="absolute right-4 top-4 z-[1000]">

        <div className="flex overflow-hidden rounded-xl border border-slate-700/70 bg-[#081018]/95 p-1 shadow-xl backdrop-blur-xl">

          <LayerButton
            active={
              layer ===
              "risk"
            }
            onClick={() =>
              setLayer(
                "risk",
              )
            }
          >
            Risk
          </LayerButton>

          <LayerButton
            active={
              layer ===
              "temperature"
            }
            onClick={() =>
              setLayer(
                "temperature",
              )
            }
          >
            Temperature
          </LayerButton>

          <LayerButton
            active={
              layer ===
              "heat_index"
            }
            onClick={() =>
              setLayer(
                "heat_index",
              )
            }
          >
            Heat Index
          </LayerButton>

        </div>

      </div>

      <MapContainer
        center={[
          selectedZone.latitude,
          selectedZone.longitude,
        ]}
        zoom={14}
        scrollWheelZoom
        className="h-[560px] w-full"
        zoomControl
      >

        <TileLayer
          attribution="&copy; OpenStreetMap contributors"
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        <MapController
          latitude={
            selectedZone.latitude
          }
          longitude={
            selectedZone.longitude
          }
        />

        {tiles.map(
          (tile) => {
            const bounds =
              getBounds(
                tile,
              );

            const selected =
              tile.tile_id ===
              selectedZone.tile_id;

            const color =
              getTileColor(
                tile,
                layer,
                temperatureRange,
                heatIndexRange,
              );

            return (
              <Rectangle
                key={
                  tile.tile_id
                }
                bounds={
                  bounds
                }
                pathOptions={{
                  color:
                    selected
                      ? "#ffffff"
                      : color,

                  fillColor:
                    color,

                  fillOpacity:
                    selected
                      ? 0.82
                      : 0.66,

                  weight:
                    selected
                      ? 3
                      : 0.8,

                  opacity:
                    selected
                      ? 1
                      : 0.9,
                }}
                eventHandlers={{
                  click: () => {
                    onSelect(
                      tile.tile_id,
                    );
                  },
                }}
              >

                <Tooltip
                  direction="top"
                  opacity={0.95}
                >

                  <div className="min-w-[150px]">

                    <strong>
                      {tile.tile_id}
                    </strong>

                    <br />

                    Risk:{" "}
                    {tile.risk_score}{" "}
                    (
                    {tile.risk_level}
                    )

                    <br />

                    Temperature:{" "}
                    {tile.temperature}
                    °C

                    <br />

                    Heat Index:{" "}
                    {tile.heat_index}
                    °C

                  </div>

                </Tooltip>

                <Popup>

                  <div
                    style={{
                      minWidth:
                        "190px",
                    }}
                  >

                    <strong>
                      AI HeatShield Zone
                    </strong>

                    <br />
                    <br />

                    Zone:{" "}
                    {tile.tile_id}

                    <br />

                    Risk Score:{" "}
                    {tile.risk_score}

                    <br />

                    Risk Level:{" "}
                    {tile.risk_level}

                    <br />

                    Temperature:{" "}
                    {tile.temperature}
                    °C

                    <br />

                    Heat Index:{" "}
                    {tile.heat_index}
                    °C

                    <br />

                    Humidity:{" "}
                    {tile.humidity}
                    %

                    <br />

                    Wet Bulb:{" "}
                    {tile.wet_bulb}
                    °C

                    <br />

                    Solar:{" "}
                    {tile.solar_radiation}{" "}
                    W/m²

                    <br />
                    <br />

                    <strong>
                      Data source:
                    </strong>{" "}

                    {isLive
                      ? "FortyGuard Live"
                      : "Synthetic Demo"}

                  </div>

                </Popup>

              </Rectangle>
            );
          },
        )}

      </MapContainer>

      <MapLegend
        layer={layer}
      />

      <div className="absolute bottom-4 right-4 z-[1000]">

        <div
          className={`rounded-xl border px-3 py-2 backdrop-blur-xl ${
            isLive
              ? "border-emerald-400/15 bg-emerald-400/[0.08]"
              : "border-amber-400/15 bg-[#081018]/95"
          }`}
        >

          <p
            className={`text-[9px] font-semibold uppercase tracking-[0.16em] ${
              isLive
                ? "text-emerald-300"
                : "text-amber-300"
            }`}
          >
            {isLive
              ? "FortyGuard Live Data"
              : "Synthetic Demo Data"}
          </p>

        </div>

      </div>

    </div>
  );
}

function MapController({
  latitude,
  longitude,
}: {
  latitude: number;
  longitude: number;
}) {
  const map = useMap();

  useEffect(() => {
    if (
      Number.isFinite(latitude) &&
      Number.isFinite(longitude)
    ) {
      map.flyTo(
        [
          latitude,
          longitude,
        ],
        map.getZoom(),
        {
          duration: 0.7,
        },
      );
    }
  }, [
    latitude,
    longitude,
    map,
  ]);

  return null;
}

function LayerButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-lg px-3 py-2 text-[10px] font-medium transition ${
        active
          ? "bg-slate-700 text-slate-100"
          : "text-slate-500 hover:bg-slate-800 hover:text-slate-300"
      }`}
    >
      {children}
    </button>
  );
}

function MapLegend({
  layer,
}: {
  layer: LayerType;
}) {
  return (
    <div className="absolute bottom-4 left-4 z-[1000]">

      <div className="rounded-xl border border-slate-700/70 bg-[#081018]/95 p-3 shadow-xl backdrop-blur-xl">

        <p className="text-[9px] font-semibold uppercase tracking-[0.16em] text-slate-500">
          {layer ===
          "risk"
            ? "Heat Risk"
            : layer ===
                "temperature"
              ? "Temperature"
              : "Heat Index"}
        </p>

        {layer ===
        "risk" ? (
          <div className="mt-2 space-y-1.5">

            <LegendItem
              color="#10b981"
              label="Low"
            />

            <LegendItem
              color="#eab308"
              label="Moderate"
            />

            <LegendItem
              color="#f59e0b"
              label="High"
            />

            <LegendItem
              color="#f97316"
              label="Very High"
            />

            <LegendItem
              color="#f43f5e"
              label="Critical"
            />

          </div>
        ) : (
          <div className="mt-2">

            <div
              className="h-2 w-32 rounded-full"
              style={{
                background:
                  "linear-gradient(to right, #38bdf8, #22c55e, #eab308, #f97316, #ef4444)",
              }}
            />

            <div className="mt-1.5 flex justify-between text-[8px] text-slate-600">
              <span>
                Lower
              </span>

              <span>
                Higher
              </span>
            </div>

          </div>
        )}

      </div>

    </div>
  );
}

function LegendItem({
  color,
  label,
}: {
  color: string;
  label: string;
}) {
  return (
    <div className="flex items-center gap-2">

      <span
        className="h-2 w-2 rounded-sm"
        style={{
          backgroundColor:
            color,
        }}
      />

      <span className="text-[9px] text-slate-500">
        {label}
      </span>

    </div>
  );
}

function getBounds(
  tile: MapTile,
): LatLngBoundsExpression {
  return [
    [
      tile.latitude -
        HALF_LAT,
      tile.longitude -
        HALF_LNG,
    ],

    [
      tile.latitude +
        HALF_LAT,
      tile.longitude +
        HALF_LNG,
    ],
  ];
}

function getTileColor(
  tile: MapTile,
  layer: LayerType,
  temperatureRange: {
    min: number;
    max: number;
  },
  heatIndexRange: {
    min: number;
    max: number;
  },
) {
  if (
    layer === "risk"
  ) {
    return getRiskColor(
      tile.risk_level,
    );
  }

  if (
    layer ===
    "temperature"
  ) {
    return getGradientColor(
      tile.temperature,
      temperatureRange.min,
      temperatureRange.max,
    );
  }

  return getGradientColor(
    tile.heat_index,
    heatIndexRange.min,
    heatIndexRange.max,
  );
}

function getRiskColor(
  level: string,
) {
  const safeLevel =
    typeof level === "string"
      ? level.toUpperCase()
      : "";

  switch (
    safeLevel
  ) {
    case "LOW":
      return "#10b981";

    case "MODERATE":
      return "#eab308";

    case "HIGH":
      return "#f59e0b";

    case "VERY HIGH":
      return "#f97316";

    case "CRITICAL":
      return "#f43f5e";

    default:
      return "#64748b";
  }
}

function getGradientColor(
  value: number,
  minimum: number,
  maximum: number,
) {
  const range =
    maximum - minimum;

  if (
    range <= 0
  ) {
    return "#eab308";
  }

  const ratio =
    Math.max(
      0,
      Math.min(
        1,
        (value -
          minimum) /
          range,
      ),
    );

  if (
    ratio < 0.2
  ) {
    return "#38bdf8";
  }

  if (
    ratio < 0.4
  ) {
    return "#22c55e";
  }

  if (
    ratio < 0.6
  ) {
    return "#eab308";
  }

  if (
    ratio < 0.8
  ) {
    return "#f97316";
  }

  return "#ef4444";
}