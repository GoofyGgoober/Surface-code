# ML decoder (planned)

**Goal.** Map a shot's gauge history and final data readout to a logical-flip
prediction, as a drop-in alternative to the lookup decoder.

**Why.** Lookup tables grow as \(2^{n_{checks}}\) and stop at d=5, and real
device noise is correlated, biased and drifting. A learned decoder can fit it.

**Training data.** Simulated shots labelled by their sampled faults, so the
simulator must record per-shot faults.

**Baseline and metric.** Flag-conditioned minimum-weight matching on the
derived stabilizers. Compare decoded logical failure and decode time per
shot; ship only if it beats matching on mismatched noise or is decisively
faster.

**Non-goals.** Real-time FPGA decoding; small matched models, where
enumeration already wins.
