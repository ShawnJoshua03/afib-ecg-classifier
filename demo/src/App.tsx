import { useEffect, useMemo, useState } from "react"
import { Grid } from "@/components/charts/grid"
import { Line } from "@/components/charts/line"
import { LineChart } from "@/components/charts/line-chart"
import { ChartTooltip } from "@/components/charts/tooltip"
import { PeakMarkers } from "@/components/charts/peak-markers"

type Rec = {
  id: string
  true: string
  pred: string
  correct: boolean
  probs: Record<string, number>
  fs: number
  signal: number[]
  peaks: number[]
}
type Demo = { seconds_shown: number; records: Rec[] }

const NAMES: Record<string, string> = { N: "Normal", A: "AFib", O: "Other rhythm", "~": "Noisy" }
const T0 = Date.UTC(2000, 0, 1)

export default function App() {
  const [demo, setDemo] = useState<Demo | null>(null)
  const [i, setI] = useState(0)
  const [dark, setDark] = useState(() => window.matchMedia("(prefers-color-scheme: dark)").matches)
  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark)
  }, [dark])
  useEffect(() => {
    fetch("demo_data.json").then((r) => r.json()).then(setDemo)
  }, [])
  const rec = demo?.records[i]
  const data = useMemo(() => {
    if (!rec) return []
    const peaks = new Set(rec.peaks)
    return rec.signal.map((v, k) => ({
      date: new Date(T0 + (k / rec.fs) * 1000),
      ecg: v,
      peak: peaks.has(k) ? v : null,
    }))
  }, [rec])
  if (!demo || !rec) return <p className="p-8">Loading…</p>

  return (
    <main className="mx-auto max-w-4xl space-y-4 p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h1 className="text-2xl font-bold">ECG rhythm explorer</h1>
        <button className="rounded border px-3 py-1 text-sm" aria-pressed={dark} onClick={() => setDark(!dark)}>
          {dark ? "Light mode" : "Dark mode"}
        </button>
      </div>
      <p className="text-sm text-muted-foreground">
        Curated held-out recordings (PhysioNet/CinC 2017), including model mistakes. A demonstration,
        not an evaluation: headline scores are in the README. Not a medical device; no clinical validation.
      </p>
      <div className="flex flex-wrap items-center gap-2">
        <select
          aria-label="Recording"
          className="min-w-0 max-w-full rounded border bg-background px-2 py-1"
          value={i}
          onChange={(e) => setI(+e.target.value)}
        >
          {demo.records.map((r, k) => (
            <option key={r.id} value={k}>
              {r.id} ({r.true}
              {r.correct ? "" : ", model wrong"})
            </option>
          ))}
        </select>
        <button className="rounded border px-3 py-1" onClick={() => setI((i + demo.records.length - 1) % demo.records.length)}>Prev</button>
        <button className="rounded border px-3 py-1" onClick={() => setI((i + 1) % demo.records.length)}>Next</button>
      </div>
      {!rec.correct && (
        <div role="status" className="rounded-lg border-2 border-red-600 bg-red-50 p-3 text-sm text-red-950 dark:border-red-400 dark:bg-red-950 dark:text-red-100">
          <strong>Model wrong.</strong> Predicted {NAMES[rec.pred]}; reference label: {NAMES[rec.true]}.
        </div>
      )}
      <div className="min-w-0 rounded-lg border p-2" aria-label={`ECG trace for ${rec.id}`}>
        <LineChart data={data} xDomain={[new Date(T0), new Date(T0 + demo.seconds_shown * 1000)]} aspectRatio="3 / 1" margin={{ top: 20, right: 20, bottom: 30, left: 20 }}>
          <Grid horizontal />
          <Line dataKey="ecg" stroke={dark ? "#60a5fa" : "#2563eb"} strokeWidth={1.5} fadeEdges={false} />
          <PeakMarkers dataKey="peak" />
          <ChartTooltip showDatePill={false} rows={(p) => [{ color: "#2563eb", label: "mV", value: (p.ecg as number).toFixed(2) }]} />
        </LineChart>
        <div className="flex justify-between px-5 pb-1 text-xs text-muted-foreground">
          {Array.from({ length: 7 }, (_, k) => (
            <span key={k}>{Math.round((k * demo.seconds_shown) / 6)} s</span>
          ))}
        </div>
      </div>
      <p className="text-xs text-muted-foreground">
        Up to the first {demo.seconds_shown} s shown; shorter recordings leave a gap at the right. Prediction uses the full recording.
        {" "}Markers are <em>detected</em> peaks (algorithmic, not expert annotations).
        {" "}Markers follow the strongest absolute filtered extremum, so they can sit on an S wave rather than an R wave.
      </p>
      <div className="flex flex-wrap gap-6">
        <span>True: <b>{NAMES[rec.true]}</b></span>
        <span>Predicted: <b>{NAMES[rec.pred]}</b></span>
        <b className={rec.correct ? "text-green-600" : "text-red-600"}>{rec.correct ? "Correct" : "Wrong"}</b>
      </div>
      <div className="space-y-1">
        {Object.entries(rec.probs).map(([k, p]) => (
          <div key={k} className="flex items-center gap-2 text-sm">
            <span className="w-24">{NAMES[k]}</span>
            <div className="h-3 flex-1 rounded bg-muted">
              <div className="h-3 rounded bg-blue-600" style={{ width: `${p * 100}%` }} />
            </div>
            <span className="w-14 text-right tabular-nums">{(p * 100).toFixed(1)}%</span>
          </div>
        ))}
      </div>
      <p className="text-xs text-muted-foreground">
        Probabilities are uncalibrated model outputs, not clinical certainty.
      </p>
      <a className="underline" href="https://github.com/ShawnJoshua03/afib-ecg-classifier">Source and methods</a>
    </main>
  )
}
