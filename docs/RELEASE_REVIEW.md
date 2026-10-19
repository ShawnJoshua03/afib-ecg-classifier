# Release and security review — 2026-10-19

The `/security-review` command is not exposed in this session. The manual fallback
review covered the two commits named by the handoff: `ce55958` (pipeline/artifacts)
and `29968c1` (React demo/CI), plus the follow-up diff. This does not claim that the
earlier automatic review that returned HTTP 429 later succeeded.

## Findings and scope

- **Open — high-severity dependency advisory:** `demo/package-lock.json:2857`
  installs `braces@3.0.3` through shadcn -> fast-glob -> micromatch.
  `npm audit --omit=dev --json` reports seven affected dependency entries, all
  tracing to [GHSA-vfj7-8cjw-p6xm](https://github.com/advisories/GHSA-vfj7-8cjw-p6xm).
  The advisory lists no patched version; npm's proposed shadcn downgrade to 1.0.0
  is a breaking change, so it was not applied blindly. This is a stack-exhaustion
  denial of service on malicious nested glob patterns. The static demo exposes
  no visitor-supplied glob/CLI input; the dependency remains an installation and
  tooling risk. No claim of a clean dependency audit is made.
- No suspicious execution or exfiltration path was found in the reviewed
  application code. The demo reads its same-origin static JSON and renders text
  through React; it has no ECG upload or server inference endpoint. Source scans
  found no `eval`, `new Function`, or `dangerouslySetInnerHTML` in the app/chart
  source. This is a scoped review, not an audit of every dependency's internals.
- Download URLs and archive/reference hashes are fixed. Extraction checks member
  paths remain under the raw-data directory. Python model loading is local;
  joblib/pickle files must be trusted before loading, and the demo does not accept
  user-supplied models.
- CI checks pull requests with read-only repository permissions; deployment
  requires the checks job, a main-branch non-PR event, and Pages/OIDC permissions.
  No `pull_request_target` or untrusted event-string shell interpolation is used.
- Pattern-scanned every `git ls-files` entry for common GitHub/OpenAI/Slack tokens,
  AWS access-key IDs, private-key headers, and literal credential assignments.
  No matches were found. Pattern scanning cannot prove the absence of every secret.
  `data/`, `.venv/`, and all `node_modules/` directories are untracked.

## Model and repository identity

- Shawn explicitly chose to keep `artifacts/model.joblib` in Git during this review.
  The released file is 1,343,692 bytes. Its measured SHA-256 is
  `fbea1c12f0fb7c10d86e5a819e664210ba619cd61cb1b7d537914a0e6680da7a`.
- All hashes listed in `selected_model.json` match their referenced files. The
  joblib bundle's embedded selection, feature order and estimator parameters match
  that JSON. The JSON contains no model-file checksum and hashes the original
  split rather than the exclusion-adjusted split; see [review findings](REVIEW_FINDINGS.md).
- GitHub API confirmed the repository description, homepage, and topics are set.
  Homepage: https://shawnjoshua03.github.io/afib-ecg-classifier/ . Topics:
  atrial-fibrillation, ecg, machine-learning, physionet, reproducible-research,
  scikit-learn. No metadata mutation was necessary.

## Action release sources

The workflow majors were checked against official releases on the review date:
[checkout v7.0.1](https://github.com/actions/checkout/releases/tag/v7.0.1),
[setup-python v7.0.0](https://github.com/actions/setup-python/releases/tag/v7.0.0),
[setup-node v7.1.0](https://github.com/actions/setup-node/releases/tag/v7.1.0),
[configure-pages v6.0.0](https://github.com/actions/configure-pages/releases/tag/v6.0.0),
[upload-pages-artifact v5.0.0](https://github.com/actions/upload-pages-artifact/releases/tag/v5.0.0),
[deploy-pages v5.0.1](https://github.com/actions/deploy-pages/releases/tag/v5.0.1).
