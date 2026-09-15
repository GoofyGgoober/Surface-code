# Logical qubit on IBM heavy-hex

Goal: a logical qubit on an IBM Heron chip (`ibm_fez`) that beats a physical
one. Built from scratch: patch, circuits, decoder, analysis.

The code is the heavy-hex subsystem code ([Chamberland et al., PRX
2020](https://arxiv.org/abs/1907.09528)), demonstrated by IBM in [Sundaresan
et al., Nat. Commun. 2023](https://arxiv.org/abs/2203.07205). d=3 runs on 23
qubits (9 data + 14 syndrome/flag). The relay-preserving d=5 layout uses 65
sites (25 data + 20 X ancillas + 12 Z ancillas + 8 boundary relays), rather
than the idealized 57-site count. Both layouts fit disjointly on fez's 156
sites. The planned comparison is \(\Lambda = p_L(3)/p_L(5)\); larger distance
is not guaranteed to improve the measured error rate.

Status: spec phase. The simulator stack — Aer memory circuits, history
decoder, cadence sweeps, noise profiles — was built for a [[9,1,3]] rotated
surface code and is frozen in the
[`lifetime-preservation`](https://github.com/GoofyGgoober/Surface-code/tree/lifetime-preservation)
branch. It becomes the test harness for the heavy-hex patch.

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
├── core/         # Pauli and stabilizer-code algebra
├── patches/      # Patch definitions (rotated d=3 today, heavy-hex next)
├── circuits/     # Circuit operations and syndrome extraction
├── decoders/     # Min-weight lookup, shared basis validation
├── simulation/   # Aer runner, one-round explorer CLI
```

## Run

```bash
python -m pip install -e '.[sim]'
surface-code X4 --shots 128 --seed 7
surface-code sweep --weight 2 --failures-only
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
