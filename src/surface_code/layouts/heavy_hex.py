"""Offline embeddings of the package's heavy-hex patches in a device graph."""

from dataclasses import dataclass

from ..patches import get_patch


@dataclass
class HeavyHexLayout:
    distance: int
    data: dict[int, int]
    x_gauges: dict[str, tuple[int, ...]]
    z_gauges: dict[str, tuple[int, ...]]
    x_stabilizers: dict[str, tuple[int, ...]]
    z_stabilizers: dict[str, tuple[int, ...]]
    x_ancillas: dict[str, int]
    z_ancillas: dict[str, int]
    relays: tuple[int, ...]
    wires: tuple[tuple[str, int, int], ...]

    @property
    def physical_qubits(self) -> set[int]:
        return set(self.local_to_physical.values())

    @property
    def local_to_physical(self) -> dict[int, int]:
        """One-based package labels to zero-based physical device indices."""
        patch = get_patch(self.distance)
        mapping = dict(self.data)
        mapping.update((g.ancilla, self.x_ancillas[g.name]) for g in patch.x_gauges)
        mapping.update((g.ancilla, self.z_ancillas[g.name]) for g in patch.z_gauges)
        mapping.update(zip(patch.relays, self.relays))
        return mapping

    @property
    def initial_layout(self) -> tuple[int, ...]:
        """Physical indices in local Qiskit qubit order; does not route a circuit."""
        mapping = self.local_to_physical
        return tuple(mapping[q] for q in range(1, get_patch(self.distance).num_qubits + 1))


def operator_name(pauli: str, support: tuple[int, ...]) -> str:
    return "".join(f"{pauli}{q}" for q in support)


def build_layout(
    distance: int,
    coords: list[list[int]],
    edges: list[tuple[int, int]],
    *,
    first_data_position: tuple[int, int],
) -> HeavyHexLayout:
    """Embed d=3 or d=5 at a top-left data site and reject missing bonds."""
    patch = get_patch(distance)
    d, (x0, y0) = patch.distance, first_data_position
    position_to_qubit = {tuple(position): q for q, position in enumerate(coords)}
    if len(position_to_qubit) != len(coords):
        raise ValueError("device coordinates must be unique")
    bonds = {tuple(sorted(edge)) for edge in edges}

    def site(x: int, y: int) -> int:
        try:
            return position_to_qubit[x, y]
        except KeyError as error:
            raise ValueError(f"no device qubit at {(x, y)}") from error

    def cell(q: int) -> tuple[int, int]:
        return (q - 1) % d, (q - 1) // d

    data = {q: site(x0 + 2 * cell(q)[1], y0 + 2 * cell(q)[0]) for q in patch.data_qubits}
    x_gauges = {g.name: tuple(sorted(g.support)) for g in patch.x_gauges}
    z_gauges = {g.name: tuple(sorted(g.support)) for g in patch.z_gauges}
    x_stabilizers = {
        operator_name("X", tuple(sorted(s.x))): tuple(sorted(s.x)) for s in patch.x_stabilizers
    }
    z_stabilizers = {
        operator_name("Z", tuple(sorted(s.z))): tuple(sorted(s.z)) for s in patch.z_stabilizers
    }
    x_ancillas, z_ancillas = {}, {}
    wires, relays = [], []
    for name, support in x_gauges.items():
        row, col = cell(min(support))
        ancilla = site(x0 + 2 * col + 1, y0 + 2 * row)
        x_ancillas[name] = ancilla
        wires.extend(("x", data[q], ancilla) for q in support)
    for name, support in z_gauges.items():
        row, col = cell(min(support))
        y = y0 + 2 * row + 1
        if len(support) == 4:
            x = x0 + 2 * col + 1
            ancilla = site(x, y)
            wires.extend(("z", site(x, arm_y), ancilla) for arm_y in (y - 1, y + 1))
        else:
            x = x0 - 1 if col == 0 else x0 + 2 * (d - 1) + 1
            ancilla = site(x, y)
            for q, arm_y in zip(support, (y - 1, y + 1)):
                relay = site(x, arm_y)
                relays.append(relay)
                wires.extend((("z", data[q], relay), ("z", relay, ancilla)))
        z_ancillas[name] = ancilla
    assigned = [*data.values(), *x_ancillas.values(), *z_ancillas.values(), *relays]
    if len(set(assigned)) != len(assigned):
        raise ValueError("device qubit assigned to multiple patch roles")
    for _, a, b in wires:
        if tuple(sorted((a, b))) not in bonds:
            raise ValueError(f"patch requires a missing device bond: {a}-{b}")
    return HeavyHexLayout(
        d,
        data,
        x_gauges,
        z_gauges,
        x_stabilizers,
        z_stabilizers,
        x_ancillas,
        z_ancillas,
        tuple(relays),
        tuple(wires),
    )
