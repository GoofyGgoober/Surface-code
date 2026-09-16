"""Ideal-syndrome CSS decoder for the two heavy-hex patches.

Find minimum-weight X and Z components independently. The largest sector
at d=5 has 12 checks (4096 syndromes), so this stays small without enumerating
4**25 physical Paulis. This is a code-capacity baseline, not a history or
flag-conditioned circuit-noise decoder, nor a joint minimum-Pauli-weight decoder.
"""

from collections import deque
from functools import cache

from .._validation import validate_binary_bits
from ..core import Pauli, SubsystemCode
from ..patches import PATCH
from .basis import normalize_measurement_basis

Syndrome = tuple[int, ...]


@cache
def _sector_table(
    data_qubits: tuple[int, ...], checks: tuple[frozenset[int], ...]
) -> dict[int, frozenset[int]]:
    if len(checks) > 16:
        raise ValueError("lookup decoding supports at most 16 checks per CSS sector")
    columns = [(q, sum((q in check) << i for i, check in enumerate(checks))) for q in data_qubits]
    corrections = {0: frozenset()}
    pending = deque([0])
    while pending:
        syndrome = pending.popleft()
        for qubit, column in columns:
            candidate = syndrome ^ column
            if candidate not in corrections:
                corrections[candidate] = corrections[syndrome] ^ {qubit}
                pending.append(candidate)
    return corrections


def decode(syndrome: Syndrome, code: SubsystemCode | None = None) -> Pauli:
    code = PATCH.code if code is None else code
    validate_binary_bits("syndrome", syndrome, code.syndrome_size)
    x_checks, z_checks = [], []
    x_bits, z_bits = [], []
    for check, bit in zip(code.stabilizers, syndrome):
        if check.x:
            x_checks.append(check.x)
            x_bits.append(bit)
        elif check.z:
            z_checks.append(check.z)
            z_bits.append(bit)
        elif bit:
            raise ValueError("syndrome is inconsistent with the stabilizers")
    try:
        x = _sector_table(code.data_qubits, tuple(z_checks))[
            sum(bit << i for i, bit in enumerate(z_bits))
        ]
        z = _sector_table(code.data_qubits, tuple(x_checks))[
            sum(bit << i for i, bit in enumerate(x_bits))
        ]
    except KeyError:
        raise ValueError("syndrome is inconsistent with the stabilizers") from None
    return Pauli(x, z)


def basis_success(error: Pauli, code: SubsystemCode | None = None, *, basis: str = "Z") -> int:
    code = PATCH.code if code is None else code
    basis = normalize_measurement_basis(basis)
    residual = decode(code.syndrome(error), code) * error
    logical = code.logical_z if basis == "Z" else code.logical_x
    return int(residual.commutes(logical))
