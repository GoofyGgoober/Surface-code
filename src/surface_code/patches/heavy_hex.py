"""Distance-3 and distance-5 heavy-hex subsystem codes.

Column-major Q1-based convention of Sundaresan et al. (2023), generalized
as in Chamberland et al. (2020). Device placement lives in layouts/.
"""

from functools import lru_cache

from ..core import Pauli
from .base import Gauge, HeavyHexPatch


@lru_cache(maxsize=None, typed=True)
def get_patch(distance: int = 3) -> HeavyHexPatch:
    if type(distance) is not int or distance not in (3, 5):
        raise ValueError("supported heavy-hex distances are 3 and 5")
    d = distance

    def q(row: int, column: int) -> int:
        return column * d + row + 1

    gx = [(q(row, col), q(row, col + 1)) for col in range(d - 1) for row in range(d)]
    gz, sx, sz = [], [], []
    for row in range(d - 1):
        for col in range(d - 1):
            block = tuple(q(r, c) for c in (col, col + 1) for r in (row, row + 1))
            (sx if (row + col) % 2 == 0 else gz).append(block)
        col = 0 if row % 2 == 0 else d - 1
        gz.append((q(row, col), q(row + 1, col)))
        sz.append(tuple(q(r, c) for c in range(d) for r in (row, row + 1)))
    for col in range(d - 1):
        row = d - 1 if col % 2 == 0 else 0
        sx.append((q(row, col), q(row, col + 1)))
    gauges = tuple(
        Gauge(basis, frozenset(support), d * d + i + 1)
        for i, (basis, support) in enumerate(
            [("X", support) for support in gx] + [("Z", support) for support in gz]
        )
    )
    first_relay = d * d + len(gauges) + 1
    return HeavyHexPatch(
        distance=d,
        data_qubits=tuple(range(1, d * d + 1)),
        gauges=gauges,
        x_stabilizers=tuple(Pauli.x_on(s) for s in sx),
        z_stabilizers=tuple(Pauli.z_on(s) for s in sz),
        logical_x=Pauli.x_on(q(row, 0) for row in range(d)),
        logical_z=Pauli.z_on(q(0, col) for col in range(d)),
        relays=tuple(range(first_relay, first_relay + 2 * (d - 1))),
    )


HEAVY_HEX_D3 = get_patch(3)
HEAVY_HEX_D5 = get_patch(5)
