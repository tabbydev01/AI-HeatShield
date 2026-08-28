"use client";

import dynamic from "next/dynamic";

const HeatMap = dynamic(
  () => import("./HeatMap"),
  {
    ssr: false,
    loading: () => (
      <div className="flex h-[560px] items-center justify-center rounded-2xl border border-slate-800/70 bg-[#081018]">
        <div className="text-center">
          <div className="mx-auto h-8 w-8 animate-spin rounded-full border-2 border-slate-800 border-t-amber-400" />

          <p className="mt-3 text-xs text-slate-500">
            Loading spatial heat map...
          </p>
        </div>
      </div>
    ),
  },
);

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

type HeatMapLoaderProps = {
  tiles: MapTile[];
  selectedZone: SelectedZone;
  mode?: string;
  onSelect: (tileId: string) => void;
};

export default function HeatMapLoader({
  tiles,
  selectedZone,
  mode = "DEMO",
  onSelect,
}: HeatMapLoaderProps) {
  const safeMode =
    typeof mode === "string" && mode.trim()
      ? mode
      : "DEMO";

  return (
    <HeatMap
      tiles={tiles}
      selectedZone={selectedZone}
      mode={safeMode}
      onSelect={onSelect}
    />
  );
}