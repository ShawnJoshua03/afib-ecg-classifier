/** Successive R-R intervals (s) between detected beats in the shown window. */
export function rrIntervals(peaks: number[], fs: number) {
  const rr: { t: number; s: number }[] = []
  for (let k = 1; k < peaks.length; k++) rr.push({ t: peaks[k] / fs, s: (peaks[k] - peaks[k - 1]) / fs })
  return rr
}

/** Same definition as rr_cv in afib/features.py: SD (ddof=1) / mean. */
export function rrCv(rr: number[]) {
  if (rr.length < 2) return null
  const mean = rr.reduce((a, b) => a + b, 0) / rr.length
  const sd = Math.sqrt(rr.reduce((a, b) => a + (b - mean) ** 2, 0) / (rr.length - 1))
  return sd / mean
}
