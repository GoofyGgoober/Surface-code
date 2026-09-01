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

```bash
./sim
```

Then choose physical \(X_i\) or \(Z_i\), logical \(X\) or \(Z\), or measure.
