"""CSS subsystem codes with one protected logical qubit.

Gauge operators may anticommute. Only their center is a stabilizer group;
errors differing by any gauge operator act identically on protected data.
"""

from dataclasses import dataclass
from functools import cached_property
from itertools import combinations

from .pauli import Pauli
from .stabilizer import StabilizerCode, _in_rowspace, _independent_rows


@dataclass(frozen=True)
class SubsystemCode(StabilizerCode):
    gauges: tuple[Pauli, ...]

    def __post_init__(self) -> None:
        super().__post_init__()
        for gauge in self.gauges:
            self.validate_data_pauli(gauge, name="gauge")
            if not gauge.weight() or (gauge.x and gauge.z):
                raise ValueError("CSS gauges must be nonidentity pure X or Z operators")
        if any(s.x and s.z for s in self.stabilizers):
            raise ValueError("CSS stabilizers must be pure X or Z operators")
        for stabilizer in self.stabilizers:
            if not self.in_gauge_group(stabilizer) or any(
                not stabilizer.commutes(g) for g in self.gauges
            ):
                raise ValueError("stabilizers must be central gauge products")
        commutators = [
            sum(int(not a.commutes(b)) << i for i, b in enumerate(self.gauges)) for a in self.gauges
        ]
        commutator_rank = len(_independent_rows(commutators, len(self.gauges)))
        if self.stabilizer_rank() != self.gauge_rank() - commutator_rank:
            raise ValueError("stabilizers must span the full gauge center")
        if self.n - self.stabilizer_rank() - self.gauge_qubits != 1:
            raise ValueError("the model requires exactly one protected logical qubit")
        for logical in (self.logical_x, self.logical_z):
            if self.in_gauge_group(logical) or any(not logical.commutes(g) for g in self.gauges):
                raise ValueError("bare logicals must commute with gauges and lie outside them")
        if not self.logical_x.x or self.logical_x.z or not self.logical_z.z or self.logical_z.x:
            raise ValueError("CSS logical X and Z must be pure X and Z operators")

    @cached_property
    def gauge_basis(self) -> tuple[int, ...]:
        return tuple(_independent_rows([self.to_symplectic(g) for g in self.gauges], 2 * self.n))

    def gauge_rank(self) -> int:
        return len(self.gauge_basis)

    @property
    def gauge_qubits(self) -> int:
        return (self.gauge_rank() - self.stabilizer_rank()) // 2

    def in_gauge_group(self, pauli: Pauli) -> bool:
        return _in_rowspace(self.to_symplectic(pauli), self.gauge_basis)

    def is_logical(self, pauli: Pauli) -> bool:
        """Test for a dressed logical: in the stabilizer centralizer, outside G."""
        self.validate_data_pauli(pauli, name="pauli")
        return all(pauli.commutes(s) for s in self.stabilizers) and not self.in_gauge_group(pauli)

    @cached_property
    def _distance(self) -> int:
        # A nontrivial mixed CSS logical has a nontrivial pure-X or pure-Z
        # component of no greater weight. Search those, bounded by the supplied
        # bare logicals, instead of enumerating all 4**n Pauli operators.
        checks_x = [sum(1 << self._positions[q] for q in s.x) for s in self.stabilizers if s.x]
        checks_z = [sum(1 << self._positions[q] for q in s.z) for s in self.stabilizers if s.z]
        bound = min(self.logical_x.weight(), self.logical_z.weight())
        for weight in range(1, bound + 1):
            for support in combinations(range(self.n), weight):
                mask = sum(1 << q for q in support)
                for checks, vector in ((checks_z, mask), (checks_x, mask << self.n)):
                    if all((mask & check).bit_count() % 2 == 0 for check in checks):
                        if not _in_rowspace(vector, self.gauge_basis):
                            return weight
        raise RuntimeError("no logical found within the supplied logical weight bound")

    def distance(self) -> int:
        return self._distance

    def parameters(self) -> tuple[int, int, int, int]:
        """Return [[n, k, r, d]], including the unprotected gauge qubits r."""
        return self.n, 1, self.gauge_qubits, self.distance()
