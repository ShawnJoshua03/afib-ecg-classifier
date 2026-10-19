"use client";

import { useChart } from "./chart-context";

export interface PeakMarkersProps {
  /** Data key holding the y value at detected peaks (null elsewhere). */
  dataKey: string;
  color?: string;
}

/** Draws a dot at each non-null row of `dataKey` (used for detected R-peaks). */
export function PeakMarkers({ dataKey, color = "#e53935" }: PeakMarkersProps) {
  const { data, xScale, yScale } = useChart();
  return (
    <g>
      {data.map((row, k) => {
        const v = row[dataKey];
        if (typeof v !== "number") return null;
        return (
          <circle
            key={k}
            cx={xScale(row.date as Date) ?? 0}
            cy={yScale(v) ?? 0}
            r={4}
            fill={color}
            stroke="white"
            strokeWidth={1}
          />
        );
      })}
    </g>
  );
}

PeakMarkers.displayName = "PeakMarkers";
(PeakMarkers as unknown as Record<string, boolean>).__isPostOverlay = true;

export default PeakMarkers;
