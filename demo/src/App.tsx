import { useEffect, useMemo, useState } from "react"
import ConfusionChart, { type Results } from "./ConfusionChart"
import EcgStrip from "./EcgStrip"
import { rrCv, rrIntervals } from "./rr"
import { CLASS_COLOR, NAMES } from "./classes"

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
type Filter = "all" | "afib" | "mistakes"

const REPO = "https://github.com/ShawnJoshua03/afib-ecg-classifier"
// Opening strip: a correctly classified reference-AFib recording with clearly irregular beat spacing.
const OPENING_ID = "A03497"

const FILTERS: { key: Filter; label: string; test: (r: Rec) => boolean }[] = [
  { key: "all", label: "All", test: () => true },
  { key: "afib", label: "AFib", test: (r) => r.true === "A" },
  { key: "mistakes", label: "Mistakes", test: (r) => !r.correct },
]

function caption(rec: Rec, rrMs: number[], seconds: number) {
  const span = rrMs.length >= 2 ? `In the ${seconds} s shown, the gaps between beats range from ${Math.min(...rrMs)} to ${Math.max(...rrMs)} ms.` : "Fewer than three beats were detected in this window, too few to judge R-R variation."
  if (rec.true === "A" && rec.correct) return `${span} Irregular beat spacing is the classic sign of AFib, and it is what the model's R-R features measure.`
  if (rec.true === "A") return `${span} The reference label is AFib, but the model said ${NAMES[rec.pred]}. Compare the R-R dots with a correctly caught AFib case.`
  if (rec.pred === "A") return `${span} The model called AFib, but the reference label is ${NAMES[rec.true]}: a false alarm.`
  if (!rec.correct) return `${span} The model said ${NAMES[rec.pred]}; the reference label is ${NAMES[rec.true]}.`
  return `${span} Model and reference agree: ${NAMES[rec.true]}.`
}

export default function App() {
  const [demo, setDemo] = useState<Demo | null>(null)
  const [res, setRes] = useState<Results | null>(null)
  const [error, setError] = useState(false)
  const [filter, setFilter] = useState<Filter>("all")
  const [id, setId] = useState<string | null>(null)
  const [dark, setDark] = useState(() => window.matchMedia("(prefers-color-scheme: dark)").matches)
  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark)
    document.documentElement.dataset.theme = dark ? "dark" : "light"
  }, [dark])
  useEffect(() => {
    const get = (u: string) => fetch(u).then((r) => {
      if (!r.ok) throw new Error(`Could not load ${u}`)
      return r.json()
    })
    get("demo_data.json").then((d: Demo) => {
      setDemo(d)
      const fromHash = decodeURIComponent(window.location.hash.slice(1))
      setId((d.records.find((r) => r.id === fromHash) ?? d.records.find((r) => r.id === OPENING_ID) ?? d.records.find((r) => r.true === "A" && r.correct) ?? d.records[0])?.id ?? null)
    }).catch(() => setError(true))
    get("results.json").then(setRes).catch(() => setError(true))
  }, [])

  const list = useMemo(() => demo ? demo.records.filter(FILTERS.find((f) => f.key === filter)!.test) : [], [demo, filter])
  const rec = demo?.records.find((r) => r.id === id) ?? list[0]
  const pos = rec ? list.findIndex((r) => r.id === rec.id) : -1
  const step = (dir: number) => {
    if (!list.length) return
    const k = pos < 0 ? 0 : (pos + dir + list.length) % list.length
    setId(list[k].id)
  }
  const choose = (f: Filter) => {
    setFilter(f)
    const next = demo?.records.filter(FILTERS.find((x) => x.key === f)!.test) ?? []
    if (next.length && !next.some((r) => r.id === id)) setId(next[0].id)
  }

  const rr = rec ? rrIntervals(rec.peaks, rec.fs) : []
  const rrMs = rr.map((r) => Math.round(r.s * 1000))
  const cv = rrCv(rr.map((r) => r.s))

  const hgb = res?.hist_gradient_boosting
  const aIdx = hgb ? hgb.label_order.indexOf("A") : -1
  const aRecall = hgb && aIdx >= 0 ? hgb.confusion_matrix[aIdx][aIdx] / hgb.confusion_matrix[aIdx].reduce((a, b) => a + b, 0) : null

  return (
    <main className="explorer">
      <header className="masthead">
        <div className="masthead-top">
          <p className="eyebrow">Single-lead ECG, PhysioNet/CinC Challenge 2017, classical ML</p>
          <nav className="top-links" aria-label="Project links">
            <a href={REPO}>GitHub repo</a>
            <a href={`${REPO}#results`}>README results</a>
            <button className="theme-control" aria-pressed={dark} onClick={() => setDark(!dark)}>{dark ? "Light" : "Dark"}</button>
          </nav>
        </div>
        <h1>ECG rhythm explorer</h1>
        <div className="disclaimer" role="note">
          <strong>Not a medical device.</strong> No clinical validation. Not for clinical use, diagnosis or decisions about anyone's
          health. A research demo on public data.
        </div>
        <p className="lede">
          A model sorts short single-lead heart recordings (about 9 to 61 s) into Normal, AFib, Other rhythm or Noisy. Below are {demo ? demo.records.length : "curated"} recordings
          it never saw in training, picked to include its mistakes. Start with the AFib strip: watch the uneven gaps between
          beats, then tap <em>Mistakes</em>.
        </p>
        <dl className="stat-strip" aria-label="Held-out results">
          <div className="stat stat-hero">
            <dt>Official mean F1 (N, A, O)</dt>
            <dd>{hgb ? hgb.official_mean_f1.toFixed(3) : "…"}</dd>
          </div>
          <div className="stat">
            <dt>Majority-class baseline</dt>
            <dd>{res ? res.majority.official_mean_f1.toFixed(3) : "…"}</dd>
          </div>
          <div className="stat">
            <dt>AFib recall</dt>
            <dd>{aRecall !== null ? `${(aRecall * 100).toFixed(1)}%` : "…"}</dd>
          </div>
          <div className="stat">
            <dt>Held-out recordings</dt>
            <dd>{res ? res.n_test.toLocaleString("en-US") : "…"}<span className="stat-unit"> in 4 classes</span></dd>
          </div>
        </dl>
        <p className="stat-note">
          Held-out 20% of the public training data, never used for tuning; not the challenge's private test set or leaderboard.
          From <code>artifacts/results.json</code>.
        </p>
      </header>

      {!demo || !rec ? (
        <section className="load-state" aria-live="polite">
          <h2>Recordings</h2>
          <p>{error ? "Could not load the recordings. Reload the page to try again." : demo ? "No recordings are available. Reload the page to try again." : "Loading recordings…"}</p>
          {(error || demo) && <button onClick={() => window.location.reload()}>Reload page</button>}
        </section>
      ) : (
        <section className="recording-section" aria-labelledby="recording-title">
          <div className="recording-toolbar">
            <div className="chips" role="group" aria-label="Filter recordings">
              {FILTERS.map((f) => {
                const n = demo.records.filter(f.test).length
                return (
                  <button key={f.key} className={`chip chip-${f.key}`} aria-pressed={filter === f.key} onClick={() => choose(f.key)}>
                    {f.label} <span className="chip-n">{n}</span>
                  </button>
                )
              })}
            </div>
            <div className="picker">
              <label htmlFor="recording" className="visually-hidden">Recording</label>
              <select id="recording" value={rec.id} onChange={(e) => setId(e.target.value)}>
                {pos < 0 && <option value={rec.id}>{rec.id}</option>}
                {list.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.id}, ref {NAMES[r.true]}{r.correct ? "" : `, model said ${NAMES[r.pred]}`}
                  </option>
                ))}
              </select>
              <button onClick={() => step(-1)} aria-label="Previous recording">←</button>
              <button className="next-control" onClick={() => step(1)} aria-label="Next recording">→</button>
              <span className="pos">{pos >= 0 ? `${pos + 1} / ${list.length}` : ""}</span>
            </div>
          </div>

          <div className="recording-layout">
            <section className={`verdict ${rec.correct ? "is-correct" : "is-wrong"}`} aria-labelledby="verdict-title" aria-live="polite">
              <h2 id="verdict-title" className="verdict-kicker">Model says</h2>
              <div className="verdict-row">
                <span className="class-chip" style={{ background: CLASS_COLOR[rec.pred] }}>{NAMES[rec.pred]}</span>
                <span className={`status ${rec.correct ? "status-ok" : "status-bad"}`}>{rec.correct ? "✓ Correct" : "✕ Wrong"}</span>
              </div>
              <p className="reference">Reference label: <strong>{NAMES[rec.true]}</strong></p>
              {!rec.correct && (
                <p className="mistake-note"><strong>Model mistake.</strong> It predicted {NAMES[rec.pred]} on a recording labelled {NAMES[rec.true]}.</p>
              )}
              <h3>Model probabilities</h3>
              <div className="probabilities">
                {Object.entries(rec.probs).map(([k, p]) => (
                  <div key={k} className={k === rec.pred ? "probability-row is-predicted" : "probability-row"}>
                    <span><i className="swatch" style={{ background: CLASS_COLOR[k] }} aria-hidden="true" />{NAMES[k]}</span>
                    <span className="probability-value">{(p * 100).toFixed(1)}%</span>
                    <div className="probability-track" aria-hidden="true">
                      <div className="probability-fill" style={{ width: `${p * 100}%`, background: CLASS_COLOR[k] }} />
                    </div>
                  </div>
                ))}
              </div>
              <p className="small-note">Uncalibrated model outputs, not clinical certainty.</p>
              <div className="rr-readout">
                <h3>Beat-spacing irregularity</h3>
                <p className="rr-big">{cv !== null ? cv.toFixed(2) : "n/a"}<span> R-R CV</span></p>
                <p className="small-note">
                  {cv !== null ? `SD ÷ mean of the ${rr.length} R-R intervals in the ${demo.seconds_shown} s shown; higher means more uneven spacing.` : `Needs at least two R-R intervals in the ${demo.seconds_shown} s shown.`}
                  The model uses this statistic (<code>rr_cv</code>) over the full recording, among 34 features.
                </p>
              </div>
              <p className="verdict-disclaimer">Not a medical device. Not for clinical use.</p>
            </section>

            <figure className="trace-figure" aria-labelledby="recording-title" aria-describedby="trace-notes">
              <div className="trace-header">
                <h2 id="recording-title">{rec.id}</h2>
                <ul className="trace-key" aria-label="Legend">
                  <li><i className="key-tick" aria-hidden="true" />Detected beat</li>
                  <li><i className="key-rr regular" aria-hidden="true" />R-R in ms, near median</li>
                  <li><i className="key-rr irregular" aria-hidden="true" />R-R ≥15% off median</li>
                </ul>
              </div>
              <p className="trace-caption">{caption(rec, rrMs, demo.seconds_shown)}</p>
              <EcgStrip key={rec.id} id={rec.id} signal={rec.signal} peaks={rec.peaks} fs={rec.fs} seconds={demo.seconds_shown} />
              <figcaption id="trace-notes" className="trace-notes">
                <p>
                  <strong>Reading the strip.</strong> Grey hairlines are beat times found by the detector (algorithmic, not expert
                  annotation). It times each beat at the strongest filtered deflection, which can be the S wave just after the R
                  peak, so a line may sit a few milliseconds right of the tallest spike. Brackets above give each R-R interval in
                  ms; the dot plot below shows the same intervals, so a flat row of dots means regular beats.
                </p>
                <p>
                  Grid: small squares 0.04 s × 0.1 mV, large squares 0.2 s × 0.5 mV, stretched to fit your screen (not printed
                  25 mm/s scale). First {demo.seconds_shown} s shown; shorter recordings leave a gap. The model used the whole
                  recording. The 15% colour threshold is a display aid only.
                </p>
              </figcaption>
            </figure>
          </div>
        </section>
      )}

      <section className="how" aria-labelledby="how-title">
        <h2 id="how-title">How it works</h2>
        <ol className="flow">
          <li><span className="flow-n">1</span><strong>Filter</strong><span>Convert to mV, 5–20 Hz band-pass</span></li>
          <li><span className="flow-n">2</span><strong>Detect beats</strong><span>Energy envelope + peak finding</span></li>
          <li><span className="flow-n">3</span><strong>{res ? res.n_features : 34} features</strong><span>R-R statistics, signal quality, morphology, duration</span></li>
          <li><span className="flow-n">4</span><strong>Boosted trees</strong><span>Class-balanced gradient boosting, chosen by 5-fold CV on training data only</span></li>
        </ol>
        <p className="how-links">
          No deep learning. Details: <a href={`${REPO}#how-it-works`}>README</a>, <a href={`${REPO}/blob/main/FEATURES.md`}>FEATURES.md</a>, <a href={`${REPO}/blob/main/SPEC.md`}>frozen evaluation spec</a> and <a href={`${REPO}#limitations`}>limitations</a>
        </p>
      </section>

      {res ? <ConfusionChart res={res} /> : (
        <section className="confusion-section" aria-live="polite">
          <h2>Where the model is right and wrong</h2>
          <p>{error ? "Could not load the held-out results. Reload the page to try again." : "Loading held-out results…"}</p>
        </section>
      )}

      <footer>
        <p className="disclaimer footer-disclaimer"><strong>Not a medical device.</strong> No clinical validation; not for clinical use. The curated recordings are a demonstration, not an evaluation.</p>
        <p>
          <a href={REPO}>Source on GitHub</a>. Data: PhysioNet/CinC Challenge 2017 (ODC-By). Recording IDs are the challenge’s own.
        </p>
      </footer>
    </main>
  )
}
