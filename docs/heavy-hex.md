# Heavy-hex code conventions

The package defines two CSS subsystem codes, following the gauge convention
of [Sundaresan et al. (2023)](https://www.nature.com/articles/s41467-023-38247-5)
and the odd-distance construction of
[Chamberland et al. (2020)](https://arxiv.org/abs/1907.09528).
Only distances 3 and 5 are currently exposed.

## Labels and parameters

`get_patch(3)` and `get_patch(5)` select immutable patch definitions. `PATCH`
is a convenience alias for d=3, not mutable global selection. Library functions
accept `patch=...`; the decoder accepts `code=patch.code`. Calling d=5 does not
change subsequent d=3 calls.

Data labels are one-based and column-major:

```text
d=3               d=5
1  4  7           1  6  11  16  21
2  5  8           2  7  12  17  22
3  6  9           3  8  13  18  23
                  4  9  14  19  24
                  5 10  15  20  25
```

`patch.data_qubit(row, column)` takes zero-based grid coordinates and returns
one of these Q labels. Local ancilla labels follow the data labels, with X
ancillas first, Z ancillas next, then the boundary relays. Qiskit uses index
`label - 1`. These local labels are distinct from physical Fez indices.

Subsystem parameters are `[[n,k,r,d]]`: data count, protected logical count,
gauge-qubit count, and dressed logical distance. They are `[[9,1,2,3]]` and
`[[25,1,8,5]]`. The code's `distance()` computes the minimum weight of an
operator that commutes with the stabilizers but lies outside the gauge group.
For CSS codes it suffices to search pure X and pure Z operators.

## Gauges, stabilizers, and logicals

The gauges need not commute with gauges of the opposite basis. Stabilizers
span the center of the gauge group and commute with every gauge. A residual
error in the gauge group is harmless to the protected logical qubit, even if
it is not a stabilizer.

At d=3 the gauges are:

- X: `X1X4`, `X2X5`, `X3X6`, `X4X7`, `X5X8`, `X6X9`.
- Z: `Z1Z2`, `Z2Z3Z5Z6`, `Z4Z5Z7Z8`, `Z8Z9`.

The X stabilizers have supports `{1,2,4,5}`, `{5,6,8,9}`, `{3,6}`, `{4,7}`;
the Z stabilizers have supports `{1,2,4,5,7,8}` and `{2,3,5,6,8,9}`.
Bare logical X is the first column and bare logical Z is the first row.
They commute with the full gauge group and anticommute with one another.
The package generates both distances from the same construction.

Ordering is part of the API:

- `patch.gauges`: X gauges then Z gauges, in the generator's deterministic order.
- `patch.stabilizers`: X stabilizers then Z stabilizers.
- A syndrome has **6 bits at d=3** and **16 bits at d=5**.
- A raw gauge record has **10 bits at d=3** and **32 bits at d=5**.
- `patch.stabilizer_gauge_indices` identifies the gauge bits to XOR for each
  stabilizer. `patch.syndrome_from_gauges(bits)` performs that conversion.

Use `surface-code --distance D info --json` to inspect exact ordered operators,
ancilla assignments, stabilizer products, and the cached physical placement.

## Ideal local circuit

The Aer model prepares a +1 eigenstate of all stabilizers and the selected
logical X or Z, with a fixed gauge state. It injects a specified data Pauli,
measures all Z gauges followed by all X gauges, and reads all data in the
selected basis. The gauge register retains canonical X-then-Z ordering even
though the execution order is Z then X. Individual gauge outcomes can be
random; their stabilizer products are the error syndrome.

`gauge_flips(error)` reports changes in gauge bits under Pauli propagation,
not absolute gauge outcomes. `extract_syndrome(error)` propagates the Pauli
through the ideal circuit and combines those flips. It agrees with the
independent commutation calculation `patch.code.syndrome(error)`.

The simulator allocates 23 or 65 qubit slots to match the embedding's roles,
but leaves boundary relays idle and uses direct gauge interactions. It does
not implement flags, routed gauge extraction, calibrated timing, repeated
rounds, or a circuit-level noise model. Its synthesized initial state is also
an ideal preparation, not a hardware preparation protocol.

`run_gauge_aer` retains the joint `(gauge_bits, data_bits)` distribution.
`run_aer` aggregates to `(stabilizer_syndrome, data_bits)` for ideal decoding.
The same injected error is used for all shots. CLI random-error draws sample
a Pauli once before execution; shots do not independently resample that error.

## Decoder

The decoder finds a minimum-weight X correction from the Z stabilizers and
a minimum-weight Z correction from the X stabilizers. Breadth-first search
builds small syndrome tables (at most 4096 entries per sector for these patches).
It minimizes each component independently; it is not a joint minimum-Pauli-weight
or maximum-likelihood decoder.

This baseline assumes perfect stabilizer measurements. Tests cover all
single-qubit X/Y/Z errors at d=3 and all weight-1 and weight-2 X/Y/Z errors
at d=5, checking the residual modulo the gauge group. Both protected logical
bases are supported. A hardware decoder must additionally handle measurement
history, flags, boundary conditions, and faults propagated by the actual circuit.

## Fez embeddings and next stage

The bundled graph is `surface_code/layouts/fez_map.json`.
`get_fez_layout(distance)` checks the embedding against that snapshot entirely
locally. The original d=3 placement and relay-preserving d=5 extension use
23 and 65 sites, with no shared sites or direct couplings between patches.
The saved documentation manifests test that these placements remain stable.

`layout.local_to_physical` maps package Q labels to Fez indices;
`layout.initial_layout` lists Fez indices in local Qiskit order. These describe
placement only: applying a layout to the ideal circuit does not produce a
validated fault-tolerant circuit. The next stage is the explicit flagged
extraction schedule, repeated-round preparation/readout protocol, realistic
noise simulation, and a decoder derived from that circuit.

## Migration from the rotated code

The old rotated patch, its eight-bit syndrome, fixed circuit constant, and
minimum-weight lookup have been removed from the active package. Use
`get_patch(distance)` and instance properties instead of the former root-level
`X_CHECKS`, `STABILIZERS`, or `SYNDROME_CIRCUIT` constants. Use
`syndrome_circuit(patch)` to build the ideal gauge operations.

Data Q1 replaces the old convention starting at Q0, with column-major grid
ordering. Saved rotated-code syndromes/results cannot be reinterpreted as
heavy-hex data. The old implementation remains on `lifetime-preservation`.
