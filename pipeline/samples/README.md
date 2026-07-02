30 outfit sample photos, auto-cropped from the user-provided collage
(`scripts/crop_samples.py`). Test them via:

- Browser: `python -m uvicorn app.main:app --port 8000` → http://localhost:8000
- CLI: `python run_sample.py samples/sample_r1c1.jpg --occasion "date night"`

Drop more jpg/png photos in here and they appear in the gallery automatically.
