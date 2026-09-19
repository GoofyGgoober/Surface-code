# Logical qubit on IBM heavy-hex

The aim is a protected logical qubit on IBM Heron (`ibm_fez`) whose error
rate lies below that of the best physical qubit on the same device.

The encoding is the heavy-hex subsystem code of [Chamberland et al., PRX
2020](https://arxiv.org/abs/1907.09528), as implemented on hardware by
[Sundaresan et al., Nat. Commun. 2023](https://arxiv.org/abs/2203.07205).
Distance 3 occupies 23 qubits (9 data and 14 syndrome or flag qubits). The
distance-5 layout that keeps the two-hop boundary relays occupies 65 sites
(25 data, 20 X ancillas, 12 Z ancillas, 8 relays), above the idealized
count of 57. Both patches embed disjointly on Fez's 156 qubits. The figure
of merit is \(\Lambda = p_L(3)/p_L(5)\); a larger distance need not reduce
the observed logical error rate.

What is established locally: the gauge group, its center, and the logical
operators at \(d=3\) and \(d=5\); an embedding onto Fez that uses only
existing couplers; an ideal gauge-measurement schedule and the flagged
\(d=3\) schedule (ancilla reuse by reset); and that every single fault
inside those gadgets is equivalent, after deflagging, to a correctable
data error. Memory under a stabilizer simulator is consistent with that
picture. What is not established: a decoder for multi-round detector
histories, compilation to the native gate set, and any result on the QPU.

## Docs

- [Heavy-hex blueprint: d=3 and d=5 on Fez](docs/figures/heavyhex-blueprint.png) — both physical
  layouts and their gauges/stabilizers. The original d=3 placement is preserved;
  d=5 is a connectivity-validated extension, not yet an executable circuit.
  Regenerate offline with `python docs/figures/draw_blueprint.py` (requires Matplotlib).
- `docs/ml-decoder.md` — planned learned decoder for the heavy-hex code.
- `docs/heavy-hex.md` — coming: gauge set, stabilizers, logicals, round
  schedule for d=3 and d=5.

The old lifetime experiment (cadence sweeps, noise profiles, figures) is
frozen in the
[`lifetime-preservation`](https://github.com/GoofyGgoober/Surface-code/tree/lifetime-preservation)
branch, including its docs and data.

## Layout

```text
surface_code/
├── core/         # Pauli, stabilizer and subsystem-code algebra
├── patches/      # Heavy-hex operators (d=3, d=5) and Fez embeddings
├── circuits/     # Abstract + flagged gauge circuits, fault injection
├── decoders/     # Lookup decoder, shared basis validation
├── simulation/   # Aer memory runners, heavy-hex CLI
```

Data-qubit ids are 0-based; the paper's Q label is id + 1.

## Run

```bash
python -m pip install -e '.[sim]'
surface-code info
surface-code syndrome 'X0 Z3'
surface-code sweep --weight 2 --failures-only
surface-code run --shots 128 --seed 7 --error 'X0'
```

`surface-code --help` lists the rest; `./sim` works when `.venv` exists.

## Checks

```bash
python -m pip install -e '.[dev]'
python -m pytest -q
ruff check src tests scripts
ruff format --check src tests scripts
```

QPU jobs need explicit per-run permission (see `AGENTS.md`). Backend
queries that cost no QPU time are fine.
