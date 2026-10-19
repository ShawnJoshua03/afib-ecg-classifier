import { useEffect, useState } from "react"
import { Bar } from "@/components/charts/bar"
import { BarChart } from "@/components/charts/bar-chart"
import { BarXAxis } from "@/components/charts/bar-x-axis"
import { Grid } from "@/components/charts/grid"
import { ChartTooltip } from "@/components/charts/tooltip"

const NAMES: Record<string, string> = { N: "Normal", A: "AFib", O: "Other", "~": "Noisy" }
const COLORS: Record<string, string> = { N: "#2563eb", A: "#dc2626", O: "#d97706", "~": "#6b7280" }

type Results = { hist_gradient_boosting: { confusion_matrix: number[][]; label_order: string[] } }

export default function ConfusionChart() {
  const [res, setRes] = useState<Results | null>(null)
  useEffect(() => {
    fetch("results.json").then((r) => r.json()).then(setRes)
  }, [])
  if (!res) return null
  const { confusion_matrix: m, label_order: labels } = res.hist_gradient_boosting
  const data = labels.map((t, i) => ({
    true: `True ${NAMES[t]}`,
    ...Object.fromEntries(labels.map((p, j) => [NAMES[p], m[i][j]])),
  }))
  return (
    <section className="space-y-2">
      <h2 className="text-lg font-semibold">Held-out confusion matrix</h2>
      <p className="text-xs text-muted-foreground">
        All 1,705 held-out records (not only the curated ones). Each bar is a true class, split by what the model predicted.
      </p>
      <div className="rounded-lg border p-2">
        <BarChart data={data} xDataKey="true" stacked aspectRatio="2.4 / 1" margin={{ top: 20, right: 20, bottom: 30, left: 20 }}>
          <Grid horizontal />
          {labels.map((p) => (
            <Bar key={p} dataKey={NAMES[p]} fill={COLORS[p]} />
          ))}
          <BarXAxis />
          <ChartTooltip />
        </BarChart>
      </div>
      <div className="flex flex-wrap gap-4 text-xs">
        {labels.map((p) => (
          <span key={p} className="flex items-center gap-1">
            <i className="inline-block h-3 w-3 rounded-sm" style={{ background: COLORS[p] }} /> predicted {NAMES[p]}
          </span>
        ))}
      </div>
      <table className="w-full text-center text-xs tabular-nums">
        <thead>
          <tr>
            <th className="text-left font-medium">True \ predicted</th>
            {labels.map((p) => <th key={p} className="font-medium">{NAMES[p]}</th>)}
          </tr>
        </thead>
        <tbody>
          {labels.map((t, i) => (
            <tr key={t} className="border-t">
              <td className="py-1 text-left font-medium">{NAMES[t]}</td>
              {m[i].map((v, j) => <td key={j} className={i === j ? "font-bold" : ""}>{v}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  )
}
