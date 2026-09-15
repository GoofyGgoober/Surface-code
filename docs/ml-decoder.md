# Learned decoder (planned)

## Goal

A learned decoder for the heavy-hex code: input a shot's gauge and flag
history plus final data readout, output the protected logical-flip prediction.
Both d=3 and d=5 should use the same experiment/result interfaces.

## Current baseline

The package now supplies both subsystem models, ideal gauge simulation, and
a decoder that minimizes X and Z components independently with perfect
stabilizer measurements. It is a code-capacity baseline. It does not yet
model flags or repeated rounds, and is not the eventual hardware decoder.

The next baseline is flag-conditioned minimum-weight matching on detection
events derived from the actual extraction circuit. Compare learned models
against that baseline before making performance claims.

## Training data

A future circuit-level simulator should retain sampled fault records and
logical labels alongside measurement records. The current ideal Aer runner
retains raw gauge/data tallies but does not generate noisy fault trajectories.
Device data should be split by acquisition run or time to test robustness to
drift and avoid training/test contamination.

## Metrics

Compare decoded logical failure at matched memory durations, uncertainty,
and classical decoding time per shot. Train on one noise model and evaluate
on mismatched noise as well as held-out device data when available.

Maximum-likelihood decoding in the 2023 IBM heavy-hex demonstration is an
inference method, not itself a learned neural decoder. See
[Sundaresan et al.](https://www.nature.com/articles/s41467-023-38247-5).

## Scope

No real-time FPGA work yet. Learned decoding follows the circuit-history
simulator and matching baseline; it is not needed to complete the local
migration to the two heavy-hex codes.
