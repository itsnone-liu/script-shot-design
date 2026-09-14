# Hua Chenyu reference-pack QA rejection

- Source: 2024-07-21 Nanchang live fan recording, BV1dZvdePEyp
- Checked ranges: 300–380s scan, 366–375s at 1 fps, 416–425s at 1 fps
- Result: **0/20 exact-review frames provide a clear physical face suitable for identity conditioning.**
- Failure mode: distant physical performer, silhouette, or LED-screen imagery. LED-screen faces must not be treated as physical identity references.
- Action: quarantined the initial H1–H5 guesses under `rejected_far_or_led/`; they are prohibited from generation.
- Salvageable asset: the source remains valid for authentic live audio, lighting, stage energy and same-event costume context.
- Required replacement: official 2024 Mars Concert close-up footage or official stills matching the selected Nanchang-era hair/makeup.
