import ConfusionChart from "./ConfusionChart"
import { useEffect, useId, useMemo, useState } from "react"
import { MotionConfig } from "motion/react"
import { curveLinear } from "@visx/curve"
import { useChart } from "@/components/charts/chart-context"
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

function ChartPaper() {
  const id = useId()
  const { innerWidth, innerHeight, yScale } = useChart()
  return (
    <g aria-hidden="true">
      <defs>
        <pattern id={id} width="12" height="12" patternUnits="userSpaceOnUse">
          <path d="M 12 0 H 0 V 12" fill="none" stroke="var(--paper-grid)" strokeWidth="0.6" />
        </pattern>
      </defs>
      <rect width={innerWidth} height={innerHeight} fill={`url(#${id})`} />
      {yScale.ticks(4).map((value) => (
        <g key={value}>
          <line x2={innerWidth} y1={yScale(value)} y2={yScale(value)} stroke="var(--paper-grid)" />
          <text x={-9} y={yScale(value)} dy="0.35em" textAnchor="end" fill="var(--muted-foreground)" fontSize="12">{value}</text>
        </g>
      ))}
    </g>
  )
}

export default function App() {
  const [demo, setDemo] = useState<Demo | null>(null)
  const [error, setError] = useState(false)
  const [i, setI] = useState(0)
  const [dark, setDark] = useState(() => window.matchMedia("(prefers-color-scheme: dark)").matches)
  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark)
  }, [dark])
  useEffect(() => {
    fetch("demo_data.json").then((r) => {
      if (!r.ok) throw new Error("Could not load recordings")
      return r.json()
    }).then(setDemo).catch(() => setError(true))
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
  return (
    <MotionConfig reducedMotion="user" transition={{ duration: 0 }}>
    <main className="explorer">
      <header className="page-header">
        <h1>ECG rhythm explorer</h1>
        <button className="theme-control" aria-pressed={dark} onClick={() => setDark(!dark)}>
          {dark ? "Light mode" : "Dark mode"}
        </button>
      </header>
      <div className="research-context">
        <p>Curated held-out recordings (PhysioNet/CinC 2017), including model mistakes. A demonstration,
        not an evaluation: headline scores are in the README.</p>
        <p className="research-limit"><strong>Not a medical device;</strong> no clinical validation.</p>
      </div>
      {!demo || !rec ? (
        <section className="load-state" aria-live="polite">
          <h2>Recordings</h2>
          <p>{error ? "Could not load the recordings. Reload the page to try again." : demo ? "No recordings are available. Reload the page to try again." : "Loading recordings…"}</p>
          {(error || demo) && <button onClick={() => window.location.reload()}>Reload page</button>}
        </section>
      ) : <>
      <section className="recording-section" aria-labelledby="recording-title">
      <div className="recording-toolbar">
        <div className="recording-field">
        <label htmlFor="recording">Recording</label>
        <select
          id="recording"
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
        </div>
        <div className="recording-navigation">
          <button onClick={() => setI((i + demo.records.length - 1) % demo.records.length)}>Prev</button>
          <button className="next-control" onClick={() => setI((i + 1) % demo.records.length)}>Next</button>
        </div>
      </div>
      {!rec.correct && (
        <div role="status" className="model-warning">
          <strong>Model wrong.</strong> Predicted {NAMES[rec.pred]}; reference label: {NAMES[rec.true]}.
        </div>
      )}
      <div className="recording-layout">
      <figure className="trace-figure" aria-labelledby="recording-title" aria-describedby="trace-limitations">
        <div className="trace-header">
          <h2 id="recording-title">{rec.id}</h2>
          <span className="peak-key"><i aria-hidden="true" />Detected peaks</span>
        </div>
        <div className="trace-paper">
        <span className="axis-unit">mV</span>
        <div className="trace-reveal" key={rec.id}>
        <LineChart data={data} xDomain={[new Date(T0), new Date(T0 + demo.seconds_shown * 1000)]} aspectRatio="" className="trace-chart" animationDuration={0} yDomainTween={false} margin={{ top: 12, right: 16, bottom: 8, left: 48 }} style={{ touchAction: "pan-y" }}>
          <ChartPaper />
          <Line dataKey="ecg" stroke="var(--trace)" strokeWidth={1.5} curve={curveLinear} animate={false} fadeEdges={false} />
          <PeakMarkers dataKey="peak" color="var(--peak)" />
          <ChartTooltip showDatePill={false} rows={(p) => [{ color: "var(--trace)", label: "mV", value: (p.ecg as number).toFixed(2) }]} />
        </LineChart>
        </div>
        <div className="time-axis">
          {Array.from({ length: 7 }, (_, k) => (
            <span key={k}>{Math.round((k * demo.seconds_shown) / 6)} s</span>
          ))}
        </div>
        </div>
      <figcaption id="trace-limitations" className="trace-notes">
        <p>Up to the first {demo.seconds_shown} s shown; shorter recordings leave a gap at the right. Prediction uses the full recording.</p>
        <p>Markers are <em>detected</em> peaks (algorithmic, not expert annotations).
        {" "}Markers follow the strongest absolute filtered extremum, so they can sit on an S wave rather than an R wave.</p>
      </figcaption>
      </figure>
      <section className="model-panel" aria-labelledby="model-title">
        <h2 id="model-title">Model call</h2>
        <div className="model-result" aria-live="polite" aria-atomic="true">
          <p className="prediction">{NAMES[rec.pred]}</p>
          <p>True: <strong>{NAMES[rec.true]}</strong></p>
          <p className={rec.correct ? "result-correct" : "result-wrong"}>{rec.correct ? "Correct" : "Wrong"}</p>
        </div>
        <h3>Model probabilities</h3>
        <div className="probabilities">
          {Object.entries(rec.probs).map(([k, p]) => (
            <div key={k} className="probability-row">
              <span>{NAMES[k]}</span>
              <span className="probability-value">{(p * 100).toFixed(1)}%</span>
              <div className="probability-track" aria-hidden="true">
                <div className={k === rec.pred ? "probability-fill is-predicted" : "probability-fill"} style={{ width: `${p * 100}%` }} />
              </div>
            </div>
          ))}
        </div>
        <p className="probability-note">Probabilities are uncalibrated model outputs, not clinical certainty.</p>
      </section>
      </div>
      </section>
      <ConfusionChart />
      </>}
      <footer><a href="https://github.com/ShawnJoshua03/afib-ecg-classifier">Source and methods</a></footer>
    </main>
    </MotionConfig>
  )
}
