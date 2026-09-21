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
embedding on existing couplers; ideal and flagged d=3/d=5 gauge schedules;
gadget-local single-fault propagation checks; stabilizer-simulator memory runs.
The d=5 circuit uses 65 reused qubits and its CX bonds match the saved blueprint.
Noiseless logical-frame and check consistency are tested in both bases across
multiple rounds. These checks do not establish full circuit-level distance five.

**Not done:** d=5 decoding, multi-round decoding, native-gate compilation, any QPU result.

## Docs

- [Blueprint: d=3 and d=5 on Fez](docs/figures/heavyhex-blueprint.png). The flagged circuits
  follow these layouts. Regenerate the figure offline with
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

## Local d=5 circuit

```bash
heavyhex --distance 5 circuit
heavyhex --distance 5 --json run --shots 128 --seed 7
```

The CLI runs one round. For repeated rounds, use
`memory_circuit_flagged(D5, rounds=3, basis="X")` from `heavyhex.circuits.flagged`
with `D5` from `heavyhex.patches.operators`, or call `run_memory_flagged` from
`heavyhex.simulation.aer` with the same arguments. The schedule exposes abstract
qubit roles through `schedule.roles` and records each measurement's round,
kind, gauge and classical-bit index. Data qubits are first, then X ancillas,
Z ancillas and boundary relays; physical placement is a separate mapping.

At d=5, `success` (CLI: `successes`) is `None`/JSON `null`: the lookup decoder
supports only d=3. The returned syndrome still describes round zero; full
history decoding and circuit-noise flag conditioning are the next MWPM stage.
The current virtual back-action subtraction supports noiseless validation and
post-preparation data-error checks, not general noisy decoding.
