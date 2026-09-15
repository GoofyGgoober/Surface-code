# Heavy-hex logical qubits on IBM Fez

Local models of the **distance-3 and distance-5 heavy-hex subsystem codes**,
with cached, disjoint layouts for `ibm_fez`. The eventual experiment is a
logical memory on IBM hardware and a comparison of both code distances.

| Patch | Subsystem parameters `[[n,k,r,d]]` | Data | X / Z gauges | X / Z stabilizers | Fez sites |
| --- | --- | ---: | ---: | ---: | ---: |
| d=3 | `[[9,1,2,3]]` | 9 | 6 / 4 | 4 / 2 | 23 |
| d=5 | `[[25,1,8,5]]` | 25 | 20 / 12 | 12 / 4 | 65 |

Here `k=1` is the protected logical qubit and `r` counts unprotected gauge
degrees of freedom. The Fez layouts retain 4 and 8 boundary relays,
respectively. Their combined footprint is 88 distinct sites.

## Current support

- Both patches, their gauge groups, stabilizers, logicals, and code distances.
- Ideal gauge-measurement circuits and local Aer stabilizer simulation in X or Z basis.
- A code-capacity decoder that minimizes X and Z error components separately.
- CLI error exploration, syndrome decoding, error sweeps, and both cached Fez layouts.
- Tests of all weight-1 data Paulis at d=3 and all weight-1/2 data Paulis at d=5.

The simulator uses direct data-to-gauge-ancilla interactions and ideal state
preparation. Its 23/65 local qubit slots include idle boundary relays. It does
**not** implement the flagged, routed, timed Fez circuit. Repeated rounds,
circuit-level noise, flag/history decoding, and IBM execution remain future work.
All current commands run locally; the Fez map is a bundled snapshot.

## Run locally

```bash
python -m pip install -e '.[sim]'
surface-code --distance 3 info
surface-code --distance 5 info
surface-code --distance 3 X4 --shots 128 --seed 7
surface-code --distance 5 X25 --shots 128 --seed 7
surface-code --distance 5 sweep --weight 2 --failures-only
surface-code --distance 3 syndrome 'X1 Z3'
surface-code --distance 3 decode '0000 10'
```

`--distance` accepts 3 or 5, before or after a command; the default is 3.
With no command, the CLI opens an interactive error explorer. `./sim` uses
`.venv` when present. `info`, `syndrome`, `decode`, and `sweep` need no Qiskit.
The CLI's `run` command prepares and reads logical Z; the Python API also supports X.

**Numbering:** data labels are **Q1–Q9** or **Q1–Q25**, column-major, matching
the blueprint. `X1` means data Q1, not Fez physical qubit 1. Package label Qj
uses Qiskit index `j-1`; `get_fez_layout(d).local_to_physical` provides the
separate physical-device mapping. See [the code conventions](docs/heavy-hex.md).

```python
from surface_code import Pauli, get_patch
from surface_code.simulation import run_aer, shot_success

patch = get_patch(5)
print(patch.code.parameters())  # (25, 1, 8, 5)
shots = run_aer(Pauli.z_on((25,)), patch=patch, basis="X", shots=128, seed=7)
successes = sum(
    count * shot_success(syndrome, data, patch=patch, basis="X")
    for (syndrome, data), count in shots.items()
)
print(successes)
```

`run_gauge_aer` returns joint raw gauge/data tallies; `run_aer` combines them
into stabilizer-syndrome/data tallies. Individual gauges can be random in an
error-free shot, while their stabilizer products remain deterministic.

## Layout

```text
surface_code/
├── core/         # Pauli, stabilizer, and CSS subsystem algebra
├── patches/      # Heavy-hex d=3 and d=5; one source for all code operators
├── layouts/      # Cached Fez graph and offline physical embeddings
├── circuits/     # Ideal gauge measurement and syndrome extraction
├── decoders/     # Separate X/Z minimum-weight code-capacity lookup
└── simulation/   # Local Aer runner and CLI
```

## Documentation

- [Heavy-hex code conventions and scope](docs/heavy-hex.md).
- [Fez blueprint](docs/figures/heavyhex-blueprint.png), with both physical layouts.
  After installing the package and Matplotlib, regenerate entirely offline with
  `python docs/figures/draw_blueprint.py`.
- [Planned learned decoder](docs/ml-decoder.md).
- References: [Chamberland et al., PRX 2020](https://arxiv.org/abs/1907.09528)
  and [Sundaresan et al., Nature Communications 2023](https://www.nature.com/articles/s41467-023-38247-5).

The old rotated `[[9,1,3]]` implementation and lifetime experiments are archived
on the [`lifetime-preservation` branch](https://github.com/GoofyGgoober/Surface-code/tree/lifetime-preservation).
They are no longer the default or an active code path. The import namespace
`surface_code` and CLI name `surface-code` are retained.

## Checks

```bash
python -m pip install -e '.[dev]'
python -m pytest -q
ruff check src tests docs/figures
ruff format --check src tests docs/figures
```

QPU execution requires explicit permission for a specific run or batch,
including free-quota jobs; see [AGENTS.md](AGENTS.md).
