# Surface code

Distance-3 rotated planar code, aimed at IBM. We are writing it from
scratch. Right now: the 9 data qubits.

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

`--draw-error P [--draws N]` samples code-capacity Pauli errors on the data
qubits before the ideal circuit runs. The resulting Pauli is fixed across all
Aer shots: this is not per-shot channel sampling, gate noise, measurement
noise, or a repeated fault-tolerant syndrome experiment. Use `--seed` to
reproduce both the draw and Aer sampling.

Run `surface-code --help` for the commands and `surface-code COMMAND --help`
for command-specific options. `./sim` is a repository-local shortcut when a
`.venv` exists at the project root.
