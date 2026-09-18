"""d=3 stabilizer readout over real ibm_fez bonds.

A weight-4 Z stabilizer cannot reach its four data qubits directly, so each is
read through the two X ancillas tiling its support; weight-2 stabilizers read
through two boundary relays. Z-type gauges go first, X-type second. The 8
intermediate outcomes are flag measurements: a hook error mid-circuit flips a
flag instead of spreading silently to two data qubits. d=5 is not covered.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..core import Pauli
from ..patches import PATCH, HeavyHexPatch
from .operations import CX, H, MeasureZ, Reset

if TYPE_CHECKING:
    from qiskit import QuantumCircuit


@dataclass(frozen=True)
class MeasuredQubits:
    """Qubits measured in each group, in order."""

    z_syndrome: tuple[int, ...]
    flags: tuple[int, ...]
    x_gauge: tuple[int, ...]


@dataclass(frozen=True)
class ExtractionCircuit:
    ops: tuple[H | CX | MeasureZ | Reset, ...]
    measured: MeasuredQubits
    mediated_gauges: tuple[tuple[int, tuple[int, int, int], tuple[int, int, int]], ...]
    relay_arms: tuple[tuple[int, int, int], ...]


def _mediated_gauges(
    patch: HeavyHexPatch,
) -> tuple[tuple[int, tuple[int, int, int], tuple[int, int, int]], ...]:
    """(syndrome, (ancilla, data, data), (ancilla, data, data)) per weight-4 Z gauge."""
    mediated = []
    for gauge in patch.z_gauges:
        if len(gauge.support) != 4:
            continue
        groups = sorted(
            (g.ancilla, *sorted(g.support)) for g in patch.x_gauges if g.support <= gauge.support
        )
        if len(groups) != 2 or set(groups[0][1:]) | set(groups[1][1:]) != set(gauge.support):
            raise ValueError(f"Z gauge {gauge.name} is not tiled by two X gauges")
        mediated.append((gauge.ancilla, groups[0], groups[1]))
    if len(mediated) != 2:
        raise ValueError("d=3 needs exactly two weight-4 Z gauges")
    return tuple(mediated)


def _weight2_relay_arms(patch: HeavyHexPatch) -> tuple[tuple[int, int, int], ...]:
    """(syndrome ancilla, relay, data) arms; first support qubit takes the first relay."""
    weight2 = [g for g in patch.z_gauges if len(g.support) == 2]
    if len(weight2) != 2 or len(patch.relays) != 4:
        raise ValueError("d=3 needs exactly two weight-2 Z gauges and four relays")
    arms = []
    relays = iter(patch.relays)
    for gauge in weight2:
        for data in sorted(gauge.support):
            arms.append((gauge.ancilla, next(relays), data))
    return tuple(arms)


def extraction_circuit(patch: HeavyHexPatch = PATCH) -> ExtractionCircuit:
    """One d=3 stabilizer-readout round over device bonds."""
    if patch.distance != 3:
        raise ValueError("the routed readout is validated for distance 3 only")
    mediated = _mediated_gauges(patch)
    arms = _weight2_relay_arms(patch)

    ops: list[H | CX | MeasureZ | Reset] = []
    # Load data parities into mediators.
    for _, first, second in mediated:
        ops.append(CX(first[1], first[0]))
        ops.append(CX(second[1], second[0]))
        ops.append(CX(first[2], first[0]))
        ops.append(CX(second[2], second[0]))
    for _, relay, data in arms:
        ops.append(CX(data, relay))
    # Collect mediator parities onto syndromes.
    for syndrome, first, second in mediated:
        ops.append(CX(first[0], syndrome))
        ops.append(CX(second[0], syndrome))
    for syndrome, relay, _ in arms:
        ops.append(CX(relay, syndrome))

    z_syndrome = tuple(g.ancilla for g in patch.z_gauges)
    flags = (
        tuple(first[0] for _, first, _ in mediated)
        + tuple(second[0] for _, _, second in mediated)
        + tuple(relay for _, relay, _ in arms)
    )
    for qubit in z_syndrome + flags:
        ops.append(MeasureZ(qubit))
    for qubit in z_syndrome + flags:
        ops.append(Reset(qubit))
    # X-type gauges read out directly.
    for gauge in patch.x_gauges:
        (d1, d2) = sorted(gauge.support)
        ops.append(H(gauge.ancilla))
        ops.append(CX(gauge.ancilla, d1))
        ops.append(CX(gauge.ancilla, d2))
        ops.append(H(gauge.ancilla))
        ops.append(MeasureZ(gauge.ancilla))
    return ExtractionCircuit(
        ops=tuple(ops),
        measured=MeasuredQubits(
            z_syndrome=z_syndrome,
            flags=flags,
            x_gauge=tuple(g.ancilla for g in patch.x_gauges),
        ),
        mediated_gauges=mediated,
        relay_arms=arms,
    )


def _conjugate_h(pauli: Pauli, qubit: int) -> Pauli:
    x, z = set(pauli.x), set(pauli.z)
    x.discard(qubit)
    z.discard(qubit)
    if qubit in pauli.z:
        x.add(qubit)
    if qubit in pauli.x:
        z.add(qubit)
    return Pauli(frozenset(x), frozenset(z))


def _conjugate_cx(pauli: Pauli, control: int, target: int) -> Pauli:
    x, z = set(pauli.x), set(pauli.z)
    if control in x:
        x.symmetric_difference_update((target,))
    if target in z:
        z.symmetric_difference_update((control,))
    return Pauli(frozenset(x), frozenset(z))


def expected_outcomes(error: Pauli, *, patch: HeavyHexPatch = PATCH) -> dict[str, tuple[int, ...]]:
    """Noise-free measurement record for a data Pauli."""
    circuit = extraction_circuit(patch)
    patch.code.validate_data_pauli(error, name="error")
    pauli = error
    shots: list[tuple[int, int]] = []
    for op in circuit.ops:
        if isinstance(op, H):
            pauli = _conjugate_h(pauli, op.qubit)
        elif isinstance(op, CX):
            pauli = _conjugate_cx(pauli, op.control, op.target)
        elif isinstance(op, MeasureZ):
            shots.append((op.qubit, int(op.qubit in pauli.x)))
        elif isinstance(op, Reset):
            x, z = set(pauli.x), set(pauli.z)
            x.discard(op.qubit)
            z.discard(op.qubit)
            pauli = Pauli(frozenset(x), frozenset(z))
        else:  # pragma: no cover - exhaustive over the op union
            raise TypeError(f"unsupported op {op!r}")
    by_qubit: dict[int, list[int]] = {}
    for qubit, bit in shots:
        by_qubit.setdefault(qubit, []).append(bit)
    return {
        "z_syndrome": tuple(by_qubit[q][0] for q in circuit.measured.z_syndrome),
        "flags": tuple(by_qubit[q][0] for q in circuit.measured.flags),
        "x_gauge": tuple(by_qubit[q][-1] for q in circuit.measured.x_gauge),
    }


def routed_gauge_flips(error: Pauli, *, patch: HeavyHexPatch = PATCH) -> tuple[int, ...]:
    """Gauge bits in ``patch.gauges`` order from the routed readout."""
    record = expected_outcomes(error, patch=patch)
    x_by_ancilla = dict(zip([g.ancilla for g in patch.x_gauges], record["x_gauge"]))
    z_by_ancilla = dict(zip([g.ancilla for g in patch.z_gauges], record["z_syndrome"]))
    return tuple(
        (x_by_ancilla if g.basis == "X" else z_by_ancilla)[g.ancilla] for g in patch.gauges
    )


def to_qiskit_routed(error: Pauli | None = None, *, patch: HeavyHexPatch = PATCH) -> QuantumCircuit:
    """Routed d=3 circuit on |0> data with an optional injected Pauli."""
    from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister

    error = Pauli() if error is None else error
    patch.code.validate_data_pauli(error, name="error")
    circuit = extraction_circuit(patch)
    qubits = QuantumRegister(patch.num_qubits, "q")
    zsynd = ClassicalRegister(len(circuit.measured.z_syndrome), "zsynd")
    flags = ClassicalRegister(len(circuit.measured.flags), "flags")
    xg = ClassicalRegister(len(circuit.measured.x_gauge), "xg")
    qc = QuantumCircuit(qubits, zsynd, flags, xg, name=f"routed_d{patch.distance}")
    qc.metadata = {
        "code": "heavy_hex",
        "distance": patch.distance,
        "model": "routed_d3",
        "hardware_compiled": False,
    }
    for q in sorted(error.x | error.z):
        if q in error.x and q in error.z:
            qc.y(q - 1)
        elif q in error.x:
            qc.x(q - 1)
        else:
            qc.z(q - 1)
    qc.barrier()
    z_index = {q: i for i, q in enumerate(circuit.measured.z_syndrome)}
    flag_index = {q: i for i, q in enumerate(circuit.measured.flags)}
    x_index = {q: i for i, q in enumerate(circuit.measured.x_gauge)}
    post_reset = False
    for op in circuit.ops:
        if isinstance(op, H):
            qc.h(op.qubit - 1)
        elif isinstance(op, CX):
            qc.cx(op.control - 1, op.target - 1)
        elif isinstance(op, MeasureZ):
            if not post_reset and op.qubit in z_index:
                qc.measure(op.qubit - 1, zsynd[z_index[op.qubit]])
            elif not post_reset:
                qc.measure(op.qubit - 1, flags[flag_index[op.qubit]])
            else:
                qc.measure(op.qubit - 1, xg[x_index[op.qubit]])
        elif isinstance(op, Reset):
            post_reset = True
            qc.reset(op.qubit - 1)
        else:  # pragma: no cover - exhaustive over the op union
            raise TypeError(f"unsupported op {op!r}")
    return qc
