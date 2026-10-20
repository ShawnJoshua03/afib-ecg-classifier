"""Build demo/public/demo_data.json: curated held-out records incl. errors (not an evaluation)."""

import json
from pathlib import Path

import numpy as np
import pandas as pd

from afib.data import load_recording
from afib.signal import detect_r_peaks

SEED = 2017
# (true label, correct count, wrong count)
QUOTA = {"N": (5, 2), "A": (5, 2), "O": (4, 4), "~": (3, 3)}
MAX_SECONDS = 12


def main(raw_dir=Path("data/raw/training2017"), out=Path("demo/public/demo_data.json")):
    pred = pd.read_csv("artifacts/test_predictions.csv")
    rng = np.random.default_rng(SEED)
    chosen = []
    for label, (n_ok, n_bad) in QUOTA.items():
        sub = pred[pred.true_label == label]
        for ok, n in ((True, n_ok), (False, n_bad)):
            pool = sub[(sub.model_prediction == sub.true_label) == ok].record_id.tolist()
            chosen += sorted(rng.choice(pool, size=min(n, len(pool)), replace=False))
    rows = pred.set_index("record_id")
    records = []
    for rid in chosen:
        rec = load_recording(raw_dir / f"{rid}.mat")
        fs = rec.sampling_rate
        n = int(MAX_SECONDS * fs)
        sig = rec.signal[:n]
        peaks = detect_r_peaks(rec.signal, fs)
        peaks = peaks[peaks < n]
        row = rows.loc[rid]
        records.append(
            {
                "id": rid,
                "true": row.true_label,
                "pred": row.model_prediction,
                "correct": bool(row.true_label == row.model_prediction),
                "probs": {k: round(float(row[f"probability_{k}"]), 4) for k in QUOTA},
                "fs": fs,
                "signal": [round(float(x), 3) for x in sig],
                "peaks": [int(p) for p in peaks],
            }
        )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"seconds_shown": MAX_SECONDS, "records": records}))
    print(f"Wrote {len(records)} records to {out}")


if __name__ == "__main__":
    main()
