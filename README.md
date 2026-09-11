# Logical qubit on IBM heavy-hex

Goal: a logical qubit on an IBM Heron chip (`ibm_fez`) that beats a physical
one. Built from scratch: patch, circuits, decoder, analysis.

The code is the heavy-hex subsystem code ([Chamberland et al., PRX
2020](https://arxiv.org/abs/1907.09528)), demonstrated by IBM in [Sundaresan
et al., Nat. Commun. 2023](https://arxiv.org/abs/2203.07205). d=3 runs on 23
qubits (9 data + 14 syndrome/flag); d=5 on 57. Both fit on fez's 156 at once,
so \(\Lambda = p_L(3)/p_L(5)\) gets measured on one calibration.

Status: spec phase. The simulator stack — Aer memory circuits, history
decoder, cadence sweeps, noise profiles — was built for a [[9,1,3]] rotated
surface code and is frozen in the
[`lifetime-preservation`](https://github.com/GoofyGgoober/Surface-code/tree/lifetime-preservation)
branch. It becomes the test harness for the heavy-hex patch.

## Docs

- `docs/memory-cadence.md` — the fixed-duration cadence experiment (math,
  controls, limits). Written for the old patch; the protocol carries over.
- `docs/ml-decoder.md` — planned learned decoder. Same interface as the
  current one, trained on sim shots, judged on cadence sweeps.
- `docs/heavy-hex.md` — coming: gauge set, stabilizers, logicals, round
  schedule for d=3 and d=5.

## Layout

```text
surface_code/
├── core/         # Pauli and stabilizer-code algebra
├── patches/      # Patch definitions (rotated d=3 today, heavy-hex next)
├── circuits/     # Circuit operations and syndrome extraction
├── decoders/     # Exact history decoder, min-weight lookup
├── simulation/   # Aer runners, cadence sweeps, noise profiles
```

## Run

```bash
python -m pip install -e '.[sim]'
surface-code cadence --time-us 10 --rounds 0 1 2 4 8 --shots 4096 --seed 7
```

`--profile` picks a noise set (`baseline`, `ibm-heron`, `google-willow`);
explicit rates override it. `--preparation product` starts data qubits in
|0⟩/|+⟩ as hardware runs do, instead of the synthesized encoder.
`surface-code --help` lists the rest; `./sim` works when `.venv` exists.

## What the sims say so far

With Heron-like rates and product prep, encoding beats the bare qubit at
every storage time and more rounds keep helping. Under the loud project
baseline every encoded curve sits below bare — each round adds more error
than it removes. Figures and data live in `artifacts/`.

## Checks

```bash
python -m pip install -e '.[dev]'
python -m pytest -q
ruff check src tests scripts
ruff format --check src tests scripts
```

QPU jobs need explicit per-run permission (see `AGENTS.md`). Backend
queries that cost no QPU time are fine.
