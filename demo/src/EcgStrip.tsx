import { useEffect, useRef, useState } from "react"
import { rrIntervals } from "./rr"

type Props = {
  id: string
  signal: number[]
  peaks: number[]
  fs: number
  seconds: number
}

const LEFT = 40
const RIGHT = 10
const LANE = 30 // R-R bracket lane above the trace
const TRACE_TOP = LANE + 6
const AXIS = 22
const TACHO = 74

export default function EcgStrip({ id, signal, peaks, fs, seconds }: Props) {
  const ref = useRef<HTMLDivElement>(null)
  const [w, setW] = useState(800)
  useEffect(() => {
    const el = ref.current
    if (!el) return
    const ro = new ResizeObserver(([e]) => setW(Math.max(280, Math.round(e.contentRect.width))))
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  const narrow = w < 600
  const traceH = narrow ? 190 : 250
  const innerW = w - LEFT - RIGHT
  const x = (t: number) => LEFT + (t / seconds) * innerW

  let lo = Infinity
  let hi = -Infinity
  for (const v of signal) { if (v < lo) lo = v; if (v > hi) hi = v }
  lo = Math.floor((lo - 0.05) / 0.5) * 0.5
  hi = Math.ceil((hi + 0.05) / 0.5) * 0.5
  if (hi - lo < 1.5) { const mid = (hi + lo) / 2; lo = Math.floor((mid - 0.75) / 0.5) * 0.5; hi = lo + 1.5 }
  const y = (v: number) => TRACE_TOP + ((hi - v) / (hi - lo)) * traceH

  // Decimate to ~2 points per pixel (min/max per bucket keeps QRS spikes).
  const perPx = (fs * seconds) / innerW
  let d = ""
  if (perPx > 2) {
    const bucket = Math.max(1, Math.floor(perPx))
    for (let s = 0; s < signal.length; s += bucket) {
      let mi = s, ma = s
      for (let k = s; k < Math.min(signal.length, s + bucket); k++) {
        if (signal[k] < signal[mi]) mi = k
        if (signal[k] > signal[ma]) ma = k
      }
      for (const k of mi < ma ? [mi, ma] : [ma, mi]) d += `${d ? "L" : "M"}${x(k / fs).toFixed(1)},${y(signal[k]).toFixed(1)}`
    }
  } else {
    signal.forEach((v, k) => { d += `${k ? "L" : "M"}${x(k / fs).toFixed(1)},${y(v).toFixed(1)}` })
  }

  // ECG paper grid in data units: minor 0.04 s x 0.1 mV, major 0.2 s x 0.5 mV.
  const pxPerMinorX = innerW / (seconds / 0.04)
  const pxPerMinorY = traceH / ((hi - lo) / 0.1)
  const showMinor = pxPerMinorX >= 4 && pxPerMinorY >= 4
  const vx: { p: number; major: boolean }[] = []
  for (let k = 0; k <= Math.round(seconds / 0.04); k++) {
    const major = k % 5 === 0
    if (major || showMinor) vx.push({ p: x(k * 0.04), major })
  }
  const hy: { p: number; major: boolean; v: number }[] = []
  for (let k = 0; k <= Math.round((hi - lo) / 0.1); k++) {
    const major = k % 5 === 0
    if (major || showMinor) hy.push({ p: y(lo + k * 0.1), major, v: lo + k * 0.1 })
  }
  const mvStep = hi - lo > 4 ? 1 : 0.5
  const traceBottom = TRACE_TOP + traceH

  const rr = rrIntervals(peaks, fs)
  const med = rr.length ? [...rr.map((r) => r.s)].sort((a, b) => a - b)[Math.floor(rr.length / 2)] : 0
  const dev = (s: number) => (med ? Math.abs(s - med) / med : 0)
  const rrColor = (s: number) => (dev(s) >= 0.15 ? "var(--rr-irregular)" : "var(--rr-regular)")

  // Tachogram lane under the time axis.
  const tTop = traceBottom + AXIS + 18
  const rrVals = rr.map((r) => r.s)
  const rLo = rrVals.length ? Math.max(0, Math.floor((Math.min(...rrVals) - 0.05) * 10) / 10) : 0
  const rHi = rrVals.length ? Math.ceil((Math.max(...rrVals) + 0.05) * 10) / 10 : 1
  const ty = (s: number) => tTop + (1 - (s - rLo) / (rHi - rLo || 1)) * (TACHO - 12) + 6
  const H = tTop + TACHO + 4
  const tStep = narrow ? 2 : 1

  return (
    <div ref={ref} className="ecg-strip">
      <svg width={w} height={H} role="img" aria-label={`ECG ${id}: first ${seconds} seconds with ${peaks.length} detected beats, R-R interval brackets and an R-R interval plot`}>
        <rect x={LEFT} y={TRACE_TOP} width={innerW} height={traceH} fill="var(--ecg-paper)" />
        {vx.map((g, k) => <line key={`v${k}`} x1={g.p} x2={g.p} y1={TRACE_TOP} y2={traceBottom} stroke={g.major ? "var(--grid-major)" : "var(--grid-minor)"} strokeWidth={g.major ? 1 : 0.6} />)}
        {hy.map((g, k) => <line key={`h${k}`} x1={LEFT} x2={LEFT + innerW} y1={g.p} y2={g.p} stroke={g.major ? "var(--grid-major)" : "var(--grid-minor)"} strokeWidth={g.major ? 1 : 0.6} />)}
        {hy.filter((g) => g.major && Math.abs(g.v / mvStep - Math.round(g.v / mvStep)) < 1e-6).map((g) => (
          <text key={`yl${g.v}`} x={LEFT - 6} y={g.p} dy="0.35em" textAnchor="end" className="axis-text">{(Math.round(g.v * 10) / 10).toString()}</text>
        ))}
        <text x={LEFT - 6} y={TRACE_TOP - 8} textAnchor="end" className="axis-text">mV</text>

        {/* Detected beat ticks: full-height hairlines so they never read as a point on the wave. */}
        {peaks.map((p) => <line key={`t${p}`} x1={x(p / fs)} x2={x(p / fs)} y1={LANE - 4} y2={traceBottom} className="beat-tick" />)}

        <path d={d} fill="none" stroke="var(--trace)" strokeWidth={narrow ? 1.2 : 1.4} strokeLinejoin="round" />

        {/* R-R brackets between successive detected beats. */}
        {rr.map((r, k) => {
          const x1 = x(peaks[k] / fs) + 1.5
          const x2 = x(peaks[k + 1] / fs) - 1.5
          const c = rrColor(r.s)
          const label = `${Math.round(r.s * 1000)}`
          return (
            <g key={`b${k}`}>
              <path d={`M${x1},${LANE - 2} V${LANE - 8} H${x2} V${LANE - 2}`} fill="none" stroke={c} strokeWidth={2} />
              {x2 - x1 >= 24 && (
                <text x={(x1 + x2) / 2} y={LANE - 12} textAnchor="middle" className="rr-label" fill={c}>{label}</text>
              )}
            </g>
          )
        })}

        {Array.from({ length: Math.floor(seconds / tStep) + 1 }, (_, k) => k * tStep).map((t) => (
          <text key={`x${t}`} x={x(t)} y={traceBottom + 16} textAnchor={t === 0 ? "start" : t === seconds ? "end" : "middle"} className="axis-text">{t} s</text>
        ))}

        {/* Tachogram: each dot is one R-R interval, plotted at the time of the beat that ends it. */}
        <rect x={LEFT} y={tTop} width={innerW} height={TACHO} fill="var(--tacho-bg)" />
        <text x={LEFT + 6} y={tTop - 5} className="axis-text tacho-title">R-R interval (s), beat by beat</text>
        {[rLo, rHi].map((v) => (
          <g key={`ry${v}`}>
            <line x1={LEFT} x2={LEFT + innerW} y1={ty(v)} y2={ty(v)} stroke="var(--grid-minor)" />
            <text x={LEFT - 6} y={ty(v)} dy="0.35em" textAnchor="end" className="axis-text">{v.toFixed(1)}</text>
          </g>
        ))}
        {rr.length > 1 && <path d={rr.map((r, k) => `${k ? "L" : "M"}${x(r.t).toFixed(1)},${ty(r.s).toFixed(1)}`).join("")} fill="none" stroke="var(--muted-foreground)" strokeWidth={1} />}
        {rr.map((r, k) => <circle key={`c${k}`} cx={x(r.t)} cy={ty(r.s)} r={3.5} fill={rrColor(r.s)} />)}
        {rr.length === 0 && <text x={LEFT + innerW / 2} y={tTop + TACHO / 2} textAnchor="middle" className="axis-text">Fewer than two beats detected in this window</text>}
      </svg>
    </div>
  )
}
