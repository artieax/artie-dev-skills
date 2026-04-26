# Eval review HTML viewer

After eval entries accumulate, generate a self-contained HTML viewer to browse runs and capture feedback:

```bash
cd skills/<name>/
python scripts/generate_review.py             # writes review/review.html
open review/review.html                       # Outputs + Benchmark tabs
```

Feedback typed in the viewer is stored in the browser's **localStorage** only — no backend, no network. Use it for stakeholder review before merging.
