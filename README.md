# Surface code

Distance-3 rotated planar code, designed independently of any backend. We are
writing it from scratch, with IBM Quantum as the first planned hardware target.
Right now: the 9 data qubits.

## Package structure

```text
surface_code/
    ├── core/         # Pauli and stabilizer-code algebra
    ├── patches/      # Geometry and the rotated distance-3 patch definition
    ├── circuits/     # Circuit operations and syndrome extraction
    ├── decoders/     # Decoder implementations
    ├── simulation/   # Simulator backends (Aer first)
    └── __init__.py   # Stable public API
```

The concrete patch is defined once in `patches/rotated_d3.py`. Existing names
such as `Pauli`, `decode`, `STABILIZERS`, and `extract_syndrome` remain
available directly from `surface_code`.

## Run Aer

Install the simulator extra, then launch the interactive explorer:

```bash
python -m pip install -e '.[sim]'
surface-code
```

Edits build a persistent injected Pauli error; `measure` explicitly runs one ideal Aer
syndrome round. Try commands such as `x 4`, `y 2`, `xl`, `add X0 Z3`, `undo`,
`circuit`, and `info`. Run `help` inside the explorer for the complete menu.

The same tools work non-interactively:

```bash
# Run an injected error (the `run` word is optional).
surface-code X4 --shots 128 --seed 7
surface-code run 'X0 Z3' --counts
surface-code run XL --json

# Inspect the code without starting Aer.
surface-code syndrome 'X0 Z3'
surface-code decode '0000 1100'
surface-code info

# Explore generated circuits and decoder behavior.
surface-code circuit X4
surface-code sweep --axes XYZ --weight 1
surface-code sweep --weight 2 --failures-only
```

## Repeated-round memory groundwork

The `memory` command prepares logical zero, repeatedly measures and resets the
eight ancillas, retains a separate syndrome register for every round, and then
measures the data qubits in Z:

```bash
# Run the project's vendor-neutral baseline noise model.
surface-code memory --rounds 4 --shots 256

# Override circuit, readout, and reset error rates.
surface-code memory --rounds 8 --shots 1024 --seed 7 \
  --single-qubit-error 0.001 --two-qubit-error 0.01 \
  --readout-error 0.02 --reset-error 0.01

# Use the same experiment with no noise.
surface-code memory --rounds 4 --shots 256 --ideal

# Inspect the actual repeated circuit.
surface-code circuit --rounds 3
```

The baseline rates (0.1% one-qubit, 1% two-qubit, 2% readout, and 1% reset) are
fixed project parameters for reproducible comparisons, not an imitation of an
IBM device or live calibration data. The model does not yet include hardware
topology, T1/T2 idle decay, leakage, crosstalk, or a space-time decoder. Logical
zero is still prepared by the simulator-oriented synthesized Clifford rather
than a fault-tolerant protocol. Accordingly, the command reports raw syndrome
and detection-event rates plus a clearly labeled last-round-only diagnostic; it
does not claim a logical lifetime yet.

`--draw-error P [--draws N]` samples code-capacity Pauli errors on the data
qubits before the ideal circuit runs. The resulting Pauli is fixed across all
Aer shots: this is not per-shot channel sampling, gate noise, measurement
noise, or a repeated fault-tolerant syndrome experiment. Use `--seed` to
reproduce both the draw and Aer sampling.

Run `surface-code --help` for the commands and `surface-code COMMAND --help`
for command-specific options. `./sim` is a repository-local shortcut when a
`.venv` exists at the project root.
