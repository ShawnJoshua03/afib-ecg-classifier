import { CLASS_COLOR, SHORT } from "./classes"

export type Results = {
  n_test: number
  n_train: number
  n_features: number
  majority: { official_mean_f1: number }
  rr_logistic: { official_mean_f1: number }
  hist_gradient_boosting: {
    official_mean_f1: number
    confusion_matrix: number[][]
    label_order: string[]
  }
}

const pct = (v: number) => `${(v * 100).toFixed(1)}%`

export default function ConfusionChart({ res }: { res: Results }) {
  const { confusion_matrix: m, label_order: labels } = res.hist_gradient_boosting
  const ai = labels.indexOf("A")
  const aRow = m[ai]
  const aTotal = aRow.reduce((a, b) => a + b, 0)
  let worst = -1
  aRow.forEach((v, j) => { if (j !== ai && (worst < 0 || v > aRow[worst])) worst = j })
  return (
    <section className="confusion-section" aria-labelledby="confusion-title">
      <div className="section-head">
        <h2 id="confusion-title">Where the model is right and wrong</h2>
        <p>
          All {res.n_test.toLocaleString("en-US")} held-out recordings, not only the curated ones. Each row is the reference
          label; shading is the share of that row the model predicted in each column. The diagonal is recall.
        </p>
      </div>
      <div className="confusion-layout">
        <div className="matrix-scroll">
          <table className="confusion-table">
            <caption>Rows: reference label. Columns: model prediction. Count, then row share.</caption>
            <thead>
              <tr>
                <th scope="col">Reference ↓ / predicted →</th>
                {labels.map((p) => <th key={p} scope="col"><i className="swatch" style={{ background: CLASS_COLOR[p] }} aria-hidden="true" />{SHORT[p]}</th>)}
                <th scope="col" className="recall-col">Recall</th>
              </tr>
            </thead>
            <tbody>
              {labels.map((t, i) => {
                const total = m[i].reduce((a, b) => a + b, 0)
                return (
                  <tr key={t}>
                    <th scope="row"><i className="swatch" style={{ background: CLASS_COLOR[t] }} aria-hidden="true" />{SHORT[t]} <span className="row-n">n={total}</span></th>
                    {m[i].map((v, j) => {
                      const r = total ? v / total : 0
                      return (
                        <td key={j} className={i === j ? "cell diagonal" : "cell"} style={{ background: `color-mix(in srgb, var(--heat) ${Math.round(r * 55)}%, var(--paper))`, color: "var(--foreground)" }}>
                          <span className="cell-count">{v}</span>
                          <span className="cell-rate">{pct(r)}</span>
                        </td>
                      )
                    })}
                    <td className="recall-col">
                      <span className="recall-value">{pct(total ? m[i][i] / total : 0)}</span>
                      <span className="recall-track" aria-hidden="true"><span style={{ width: pct(total ? m[i][i] / total : 0), background: CLASS_COLOR[t] }} /></span>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
        <aside className="matrix-takeaway">
          <p className="takeaway-label">AFib, read across the row</p>
          <p className="takeaway-big"><strong>{aRow[ai]}</strong> of {aTotal}</p>
          <p>AFib recordings were called AFib ({pct(aRow[ai] / aTotal)} recall). Most misses went to {SHORT[labels[worst]]} ({aRow[worst]}).</p>
          <p className="takeaway-muted">The largest single confusion overall is Other called Normal ({m[labels.indexOf("O")][labels.indexOf("N")]}): "Other" is a mixed bag of rhythms.</p>
        </aside>
      </div>
    </section>
  )
}
