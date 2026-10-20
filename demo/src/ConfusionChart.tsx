import { useEffect, useState } from "react"
import { Bar } from "@/components/charts/bar"
import { BarChart } from "@/components/charts/bar-chart"
import { BarXAxis } from "@/components/charts/bar-x-axis"
import { Grid } from "@/components/charts/grid"
import { ChartTooltip } from "@/components/charts/tooltip"
import { useChart } from "@/components/charts/chart-context"

const NAMES: Record<string, string> = { N: "Normal", A: "AFib", O: "Other", "~": "Noisy" }
const COLORS: Record<string, string> = { N: "var(--class-normal)", A: "var(--class-afib)", O: "var(--class-other)", "~": "var(--class-noisy)" }

type Results = { hist_gradient_boosting: { confusion_matrix: number[][]; label_order: string[] } }

function CountAxis() {
  const { yScale } = useChart()
  return <g aria-hidden="true">{yScale.ticks(4).map((value) => (
    <text key={value} x={-8} y={yScale(value)} dy="0.35em" textAnchor="end" fontSize="12" fill="var(--muted-foreground)">{value}</text>
  ))}</g>
}

export default function ConfusionChart() {
  const [res, setRes] = useState<Results | null>(null)
  const [error, setError] = useState(false)
  useEffect(() => {
    fetch("results.json").then((r) => {
      if (!r.ok) throw new Error("Could not load results")
      return r.json()
    }).then(setRes).catch(() => setError(true))
  }, [])
  if (!res) return <section className="confusion-section" aria-live="polite">
    <h2>Held-out confusion matrix</h2>
    <p>{error ? "Could not load the held-out results. Reload the page to try again." : "Loading held-out results…"}</p>
    {error && <button onClick={() => window.location.reload()}>Reload page</button>}
  </section>
  const { confusion_matrix: m, label_order: labels } = res.hist_gradient_boosting
  const data = labels.map((t, i) => ({
    true: `True ${NAMES[t]}`,
    ...Object.fromEntries(labels.map((p, j) => [NAMES[p], m[i][j]])),
  }))
  return (
    <section className="confusion-section" aria-labelledby="confusion-title">
      <h2 id="confusion-title">Held-out confusion matrix</h2>
      <p>
        All 1,705 held-out records (not only the curated ones). Each bar is a true class, split by what the model predicted.
      </p>
      <div className="confusion-layout">
      <figure className="confusion-figure" aria-label="Held-out counts by true and predicted class; exact counts in the adjacent table">
        <div className="chart-legend">
          {labels.map((p) => (
            <span key={p}><i aria-hidden="true" style={{ background: COLORS[p] }} /> predicted {NAMES[p]}</span>
          ))}
        </div>
        <BarChart data={data} xDataKey="true" stacked className="confusion-chart" animationDuration={0} margin={{ top: 20, right: 12, bottom: 30, left: 44 }}>
          <Grid horizontal numTicksRows={4} strokeDasharray="" fadeHorizontal={false} />
          <CountAxis />
          {labels.map((p) => (
            <Bar key={p} dataKey={NAMES[p]} fill={COLORS[p]} animate={false} lineCap="butt" />
          ))}
          <BarXAxis />
          <ChartTooltip />
        </BarChart>
      </figure>
      <table className="confusion-table">
        <caption>Held-out recording counts</caption>
        <thead>
          <tr>
            <th scope="col">True \ predicted</th>
            {labels.map((p) => <th key={p} scope="col">{NAMES[p]}</th>)}
          </tr>
        </thead>
        <tbody>
          {labels.map((t, i) => (
            <tr key={t}>
              <th scope="row">{NAMES[t]}</th>
              {m[i].map((v, j) => <td key={j} className={i === j ? "diagonal" : ""}>{v}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
      </div>
    </section>
  )
}
