"""Heavy-hex patch roles, independent of a particular device embedding."""

from dataclasses import dataclass
from functools import cached_property
from typing import Literal

from .._validation import validate_binary_bits
from ..core import Pauli, SubsystemCode


@dataclass(frozen=True)
class Gauge:
    basis: Literal["X", "Z"]
    support: frozenset[int]
    ancilla: int

    def __post_init__(self) -> None:
        if self.basis not in ("X", "Z") or not self.support:
            raise ValueError("a gauge needs an X/Z basis and nonempty support")

    @property
    def pauli(self) -> Pauli:
        return Pauli.x_on(self.support) if self.basis == "X" else Pauli.z_on(self.support)

    @property
    def name(self) -> str:
        return "".join(f"{self.basis}{q}" for q in sorted(self.support))


@dataclass(frozen=True)
class HeavyHexPatch:
    distance: int
    data_qubits: tuple[int, ...]
    gauges: tuple[Gauge, ...]
    x_stabilizers: tuple[Pauli, ...]
    z_stabilizers: tuple[Pauli, ...]
    logical_x: Pauli
    logical_z: Pauli
    relays: tuple[int, ...]

    def __post_init__(self) -> None:
        if type(self.distance) is not int or self.distance not in (3, 5):
            raise ValueError("supported heavy-hex distances are 3 and 5")
        if self.data_qubits != tuple(range(1, self.distance**2 + 1)):
            raise ValueError("data labels must be Q1 through Q(d squared), column-major")
        roles = self.data_qubits + self.ancillas + self.relays
        if len(set(roles)) != len(roles):
            raise ValueError("data, gauge ancillas, and relays must be distinct")
        if roles != tuple(range(1, len(roles) + 1)):
            raise ValueError("local qubit labels must be contiguous from 1")
        if any(not g.support <= set(self.data_qubits) for g in self.gauges):
            raise ValueError("gauge support must contain only data qubits")
        self.code
        self.stabilizer_gauge_indices

    @property
    def x_gauges(self) -> tuple[Gauge, ...]:
        return tuple(g for g in self.gauges if g.basis == "X")

    @property
    def z_gauges(self) -> tuple[Gauge, ...]:
        return tuple(g for g in self.gauges if g.basis == "Z")

    @property
    def x_ancillas(self) -> tuple[int, ...]:
        return tuple(g.ancilla for g in self.x_gauges)

    @property
    def z_ancillas(self) -> tuple[int, ...]:
        return tuple(g.ancilla for g in self.z_gauges)

    @property
    def ancillas(self) -> tuple[int, ...]:
        return tuple(g.ancilla for g in self.gauges)

    @property
    def num_qubits(self) -> int:
        """Sites in the relay-preserving embedding, including idle simulator relays."""
        return len(self.data_qubits + self.ancillas + self.relays)

    @property
    def stabilizers(self) -> tuple[Pauli, ...]:
        return self.x_stabilizers + self.z_stabilizers

    @cached_property
    def code(self) -> SubsystemCode:
        return SubsystemCode(
            self.data_qubits,
            self.stabilizers,
            self.logical_x,
            self.logical_z,
            tuple(g.pauli for g in self.gauges),
        )

    def data_qubit(self, row: int, column: int) -> int:
        """Q label at zero-based (row, column), matching the blueprint."""
        if any(type(v) is not int or not 0 <= v < self.distance for v in (row, column)):
            raise ValueError("row and column must lie inside the patch")
        return column * self.distance + row + 1

    @cached_property
    def stabilizer_gauge_indices(self) -> tuple[tuple[int, ...], ...]:
        # Eliminate while carrying provenance to express each stabilizer as a
        # product of measured gauges without searching all gauge subsets.
        pivots: dict[int, tuple[int, int]] = {}
        for i, gauge in enumerate(self.gauges):
            vector, used = self.code.to_symplectic(gauge.pauli), 1 << i
            while vector:
                pivot = vector.bit_length() - 1
                if pivot not in pivots:
                    pivots[pivot] = vector, used
                    break
                basis, indices = pivots[pivot]
                vector, used = vector ^ basis, used ^ indices
        products = []
        for stabilizer in self.stabilizers:
            vector, used = self.code.to_symplectic(stabilizer), 0
            while vector:
                pivot = vector.bit_length() - 1
                if pivot not in pivots:
                    raise ValueError("stabilizer cannot be reconstructed from gauges")
                basis, indices = pivots[pivot]
                vector, used = vector ^ basis, used ^ indices
            products.append(tuple(i for i in range(len(self.gauges)) if used & (1 << i)))
        return tuple(products)

    def syndrome_from_gauges(self, bits: tuple[int, ...]) -> tuple[int, ...]:
        """X stabilizers then Z stabilizers; gauge bits are in patch.gauges order."""
        validate_binary_bits("gauge readout", bits, len(self.gauges))
        return tuple(sum(bits[i] for i in indices) % 2 for indices in self.stabilizer_gauge_indices)
