# ML decoder (planned)

## Goal

Replace or augment `decoders/infer_logical.py` with a learned decoder:
input a shot's syndrome history plus final data bits, output the logical-flip
prediction. Same interface (`LogicalFlipPrediction`), so `sweep_n.py` and the
CLI evaluate it unchanged.

## Why

For d=3 CSS with matched independent-bit noise, exact 32-class inference is
already optimal — ML cannot beat it there. The win comes from three places:

1. **Model mismatch.** The real device has correlated, biased, drifting noise
   our three-rate model does not capture. A learned decoder fits the device,
   not the sketch.
2. **Scale.** Exact inference is intractable at d=5+. Learned decoders
   (Tanner-graph GNN, transformer on history) scale where enumeration dies.
3. **Speed.** Microsecond-scale inference matters for real-time correction;
   a distilled network beats table enumeration per shot.

It is also the decoder the heavy-hex subsystem code wants (matching struggles
with derived-stabilizer correlations; IBM's demo used matching + ML).

## Training data

Free: `record_shots.py` already generates unlimited labeled shots. One gap —
tallies aggregate counts, so per-shot fault records must be added to recover
ground-truth logical flips as labels.

## Baselines and metric

Baselines: `infer_logical` (exact), `min_weight`, PyMatching. Metric: decoded
logical failure on the existing cadence sweeps, plus wall-clock decode time
per shot. A learned decoder ships only if it beats exact inference on
device-like (mismatched) noise or runs decisively faster.

## Non-goals

No real-time FPGA work. No claim on matched-model d=3 — that fight is already
won by enumeration.
