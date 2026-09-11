# ML decoder (planned)

## Goal

A learned decoder for the heavy-hex code: input a shot's gauge history plus
final data readout, output the logical-flip prediction. It plugs into the
memory sweeps the same way any other decoder does.

## Why

Exact inference dies at d=5 — the syndrome/logical class table grows as
\(2^{n_{checks}}\) while a matching or learned decoder stays polynomial. And
the real device has correlated, biased, drifting noise no analytic model
captures. A learned decoder fits the device, not the sketch. IBM's heavy-hex
demo already needed matching + ML for this reason.

## Training data

Free once the heavy-hex sim exists: it generates unlimited labeled shots,
since the simulator knows the sampled faults. Per-shot fault records are a
requirement on the sim, not an afterthought.

## Baselines and metric

Baseline: flag-conditioned minimum-weight matching on derived stabilizers.
Metric: decoded logical failure on fixed-duration memory sweeps, plus
wall-clock decode time per shot. The learned decoder ships only if it beats
matching on device-like (mismatched) noise or runs decisively faster.

## Non-goals

No real-time FPGA work yet. No claim on small matched models — enumeration
already wins those.
