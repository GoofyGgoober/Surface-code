# Surface Code

A surface-code implementation intended to run on IBM quantum hardware. The
first milestone is a dependency-free classical reference model of the rotated
planar code: a validated distance-`d` lattice, Pauli error tracking, stabilizer
syndrome extraction, and a phenomenological noise sampler.

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e . pytest
pytest
python -m surface_code --distance 3 --shots 1000 --error-rate 0.01
```

The code currently simulates perfect stabilizer measurements. Planned next
steps are repeated noisy measurement rounds, a matching decoder, logical-error
benchmarks, Qiskit circuit generation, and execution against IBM backends.
