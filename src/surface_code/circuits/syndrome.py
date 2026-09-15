"""Ideal heavy-hex gauge measurements, without device routing or flags.

Each gauge has direct access to its data. Z gauges are measured first, then
X gauges. Individual gauge outcomes may be random even with no faults;
only their stabilizer products are deterministic on an encoded state.
These circuits establish the algebra/simulator baseline, not a fault-tolerant
Fez gate schedule. Relays are reserved but idle in this ideal model.
"""

from ..core import Pauli
from ..patches import PATCH, HeavyHexPatch
from .operations import CX, H, MeasureZ


def syndrome_circuit(patch: HeavyHexPatch = PATCH) -> tuple[H | CX | MeasureZ, ...]:
    ops = []
    for gauge in patch.z_gauges + patch.x_gauges:
        if gauge.basis == "X":
            ops.append(H(gauge.ancilla))
        for data in sorted(gauge.support):
            ops.append(CX(gauge.ancilla, data) if gauge.basis == "X" else CX(data, gauge.ancilla))
        if gauge.basis == "X":
            ops.append(H(gauge.ancilla))
        ops.append(MeasureZ(gauge.ancilla))
    return tuple(ops)


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


def abstract_syndrome(error: Pauli, *, patch: HeavyHexPatch = PATCH) -> tuple[int, ...]:
    return patch.code.syndrome(error)


def gauge_flips(error: Pauli, *, patch: HeavyHexPatch = PATCH) -> tuple[int, ...]:
    """Propagate an injected Pauli to relative gauge-bit flips, not absolute outcomes."""
    patch.code.validate_data_pauli(error, name="error")
    pauli = error
    bits = {}
    for op in syndrome_circuit(patch):
        if isinstance(op, H):
            pauli = _conjugate_h(pauli, op.qubit)
        elif isinstance(op, CX):
            pauli = _conjugate_cx(pauli, op.control, op.target)
        else:
            bits[op.qubit] = int(op.qubit in pauli.x)
    return tuple(bits[g.ancilla] for g in patch.gauges)


def extract_syndrome(error: Pauli, *, patch: HeavyHexPatch = PATCH) -> tuple[int, ...]:
    return patch.syndrome_from_gauges(gauge_flips(error, patch=patch))
