120 outfit sample photos, auto-cropped from user-provided collages via
`scripts/crop_samples.py` (`sample_*` = first batch; `b2_*`/`b3_*`/`b4_*` =
later batches, burned-in labels trimmed). Test them from the repo root:

- Browser: `python -m uvicorn pipeline.app.main:app --port 8000` → http://localhost:8000
- CLI: `python pipeline/run_sample.py pipeline/samples/sample_r1c1.jpg --occasion "date night"`

Drop more jpg/png photos in here and they appear in the gallery automatically.
