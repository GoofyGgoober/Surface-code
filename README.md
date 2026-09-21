# Heavy-hex scalability check

Does the heavy-hex code get better as it grows? The plan is to run d=3 and
d=5 side by side on IBM Heron (`ibm_fez`) and compare logical error rates,
\(\Lambda = p_L(3)/p_L(5)\). The end goal is a logical qubit that beats the
best physical qubit on the same device.

The code is the heavy-hex subsystem code ([Chamberland et al., PRX
2020](https://arxiv.org/abs/1907.09528); on hardware, [Sundaresan et al.,
Nat. Commun. 2023](https://arxiv.org/abs/2203.07205)). d=3 uses 23 qubits
(9 data, 14 syndrome/flag). d=5 uses 65 (25 data, 20 X ancillas, 12 Z
ancillas, 8 boundary relays; 57 without the relays). Both embed disjointly
on Fez.

**Done:** gauge group, stabilizers and logicals at d=3 and d=5; a Fez
embedding on existing couplers; ideal and flagged d=3 gauge schedules; a
check that every single fault in those gadgets deflags to a correctable data
error; stabilizer-simulator memory runs.

**Not done:** multi-round decoding, native-gate compilation, any QPU result.

## Docs

- [Blueprint: d=3 and d=5 on Fez](docs/figures/heavyhex-blueprint.png). d=5 is
  a connectivity-validated layout, not yet a circuit. Regenerate offline with
  `python docs/figures/draw_blueprint.py` (needs Matplotlib).
- [docs/ml-decoder.md](docs/ml-decoder.md): planned learned decoder.

## Layout

```text
heavyhex/
├── core/         # Pauli and subsystem-code algebra
├── patches/      # Heavy-hex operators (d=3, d=5) and Fez embeddings
├── circuits/     # Ideal + flagged gauge circuits, fault injection
├── decoders/     # Lookup decoder
├── simulation/   # Aer memory runners
└── cli.py        # `heavyhex` command
```

Data-qubit ids are 0-based; the paper's Q label is id + 1.

## Run

```bash
python -m pip install -e '.[sim]'
heavyhex info
heavyhex syndrome 'X0 Z3'
heavyhex sweep --weight 2 --failures-only
heavyhex run --shots 128 --seed 7 --error 'X0'
```

`heavyhex --help` lists the rest; `./sim` works when `.venv` exists.

## Checks

```bash
python -m pip install -e '.[dev]'
python -m pytest -q
ruff check .
ruff format --check .
```

QPU jobs need explicit per-run permission (see `AGENTS.md`).
